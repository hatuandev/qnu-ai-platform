"""Source reconstruction succeeds without relaxing source/hash/header/role checks."""
import hashlib
from copy import deepcopy
from io import BytesIO

import pytest
from docx import Document

from app.core.exceptions import AppException
from app.modules.knowledge.compilation_runtime_schemas import (
    PacketCheck,
    PacketCoverage,
    PacketDraft,
    SynthesisDraft,
    TopicSelection,
)
from app.modules.knowledge.services.compilation_columns import (
    ColumnRole,
    TableFields,
    native_tables,
    table_records,
    validate_record_packet,
    verified_columns,
)
from app.modules.knowledge.services.compilation_contracts import evidence_catalog
from app.modules.knowledge.services.compilation_grounding import (
    PROTOCOL,
    materialize_packet,
    materialize_section_reviews,
    materialize_synthesis,
    span_catalog,
)
from app.modules.knowledge.services.compilation_structure import decorate, structural_catalog
from app.modules.knowledge.services.compilation_validation import check_packet, validate_result
from app.modules.knowledge.services.wiki_compiler import digest
from tests.test_compilation_engine_603 import ACTOR, Model
from tests.test_compilation_metrics_615 import no_network  # noqa: F401
from tests.test_compilation_structure_614 import by_unit, structured_source


def source_fixture(*, bold=True, duplicate=False, context_mode='matching'):
    source = structured_source(blank_header=True)
    document = Document()
    if context_mode!='foreign':
        document.add_paragraph(('\t' if context_mode=='indent' else '')+'Đây là kết quả phản hồi.')
        if context_mode=='duplicate':
            document.add_paragraph('Đây là kết quả phản hồi.')
    else:
        document.add_paragraph('Một bảng khác với ý nghĩa khác.')
    grid = source.parse_provenance['structured_artifact']['tables'][0]['rows']
    for _ in range(2 if duplicate else 1):
        table = document.add_table(rows=0, cols=4)
        for ri, values in enumerate(grid):
            for cell, value in zip(table.add_row().cells, values, strict=True):
                cell.text = value
                for run in cell.paragraphs[0].runs:
                    run.bold = bold and ri == 0
    stream = BytesIO()
    document.save(stream)
    source._compiler_raw_bytes = stream.getvalue()
    source.origin_file_hash = hashlib.sha256(source._compiler_raw_bytes).hexdigest()
    catalog = evidence_catalog([source], 'c603')
    structure = structural_catalog([source], catalog)
    return source, catalog, structure, by_unit(catalog)


def selected(catalog, pid, value):
    return {'span_id':next(q for q,s in span_catalog(catalog).items() if s['evidence_id']==pid and s['literal']==value)}


def claims(ids, catalog):
    def span(uid, value):
        return selected(catalog,ids[uid],value)

    return {'claims': [{'id': 'a', 'subject': span('r1', 'Alpha'), 'metric': span('r0', 'Nhập học'),
        'column': span('r0', 'Nhập học'), 'scalar': span('r1', '416'), 'value_state': 'present'}],
        'deferred_evidence_ids': []}


def ledger(native, catalog, *, second='column_headers'):
    return {pid: {'native_proof': proof, 'reviews': [{'role': role,
        'columns': ['Nhóm', 'Nhập học', 'Khảo sát', '2027'] if role=='column_headers' else [],
        'evidence_ids': [pid, *proof['body_evidence_ids']], 'reason': 'Raw column labels and two records agree.'}
        for role in ('column_headers', second)]} for pid, proof in native.items()}


def test_native_grid_and_two_independent_roles_resolve_only_compiler_interpretation():
    source, catalog, structure, ids = source_fixture()
    before = deepcopy(source.parse_provenance)
    native = native_tables([source], catalog, structure)
    assert set(native) == {ids['r0']}
    roles = verified_columns(ledger(native, catalog), native, catalog)
    draft = materialize_packet(claims(ids,catalog), {'evidence': catalog})
    review = PacketCheck(items=[{'id': 'a', 'verdict': 'supported', 'entity_scope': True,
        'temporal_roles': True, 'conditions_complete': True, 'evidence_ids': draft['assertions'][0]['evidence_ids'],
        'reason': 'Exact row, population and column interpretation agree.'}])
    offered = decorate(catalog, structure)
    assert check_packet(draft, review, [ids['r1']], offered, column_roles=roles)['complete']
    assert not check_packet(draft, review, [ids['r1']], offered, column_roles={})['complete']
    assert source.parse_provenance == before
    assert structure[ids['r1']]['header_status'] == 'unresolved'


@pytest.mark.parametrize('mode', ['no_format', 'duplicate_native', 'hash_mismatch', 'cell_mismatch'])
def test_missing_or_ambiguous_native_evidence_never_certifies_a_header(mode):
    source, catalog, structure, _ = source_fixture(bold=mode!='no_format', duplicate=mode=='duplicate_native')
    if mode == 'hash_mismatch':
        source.origin_file_hash = '0'*64
        with pytest.raises(AppException):
            native_tables([source], catalog, structure)
        return
    if mode == 'cell_mismatch':
        pid = next(p for p in catalog if 'Alpha' in catalog[p]['quote'])
        catalog[pid]['quote'] = catalog[pid]['quote'].replace('416', '417')
    assert native_tables([source], catalog, structure) == {}


@pytest.mark.parametrize('role', ['data', 'unresolved'])
def test_first_bold_row_cannot_be_promoted_when_blind_witness_disagrees(role):
    source, catalog, structure, _ = source_fixture()
    native = native_tables([source], catalog, structure)
    assert verified_columns(ledger(native, catalog, second=role), native, catalog) == {}


@pytest.mark.parametrize('mutation', ['invented_label', 'wrong_reference', 'cross_source', 'missing_scalar', 'unknown_without_proof'])
def test_literal_materialization_rejects_hallucinated_or_unproved_bindings(mutation):
    _, catalog, _, ids = source_fixture()
    value = claims(ids,catalog)
    claim = value['claims'][0]
    if mutation == 'invented_label':
        claim['metric']['span_id'] = 'invented_planned_admission_quota'
    elif mutation == 'wrong_reference':
        claim['column']['span_id'] = 'a_reference_from_another_request'
    elif mutation == 'cross_source':
        catalog[ids['r0']]['source_revision_id'] = 'other'
    elif mutation == 'missing_scalar':
        claim['scalar'] = None
    else:
        claim.update(scalar=None, value_state='source_unspecified')
    with pytest.raises(AppException):
        materialize_packet(value, {'evidence': catalog})


def test_server_builds_labels_scopes_and_section_text_from_selected_literals_only():
    _, catalog, _, ids = source_fixture()
    packet = materialize_packet(claims(ids,catalog), {'evidence': catalog})
    item = packet['assertions'][0]
    assert packet['entities'][0]['label'] == 'Alpha' and item['attribute'] == 'Nhập học'
    assert item['value'] == '416' and {s['dimension'] for s in item['scope']} == {'source_subject', 'source_metric', 'source_column'}
    plan = {'sections': [{'heading': selected(catalog,ids['r0'],'Nhập học'), 'assertion_ids': ['a']}], 'relations': []}
    result = materialize_synthesis(plan, {'draft': packet, 'evidence': catalog})
    assert result['sections'][0]['text'] == 'Alpha — Nhập học; Nhập học: 416.'


def test_wire_contract_and_budget_measure_the_actual_grounded_schema():
    from app.modules.knowledge.services.compilation_catalog import dependency_catalog
    from app.modules.knowledge.services.compilation_engine import DRAFT, packet_payload
    from app.modules.knowledge.services.compilation_transport import (
        TRANSPORT_NOTE,
        prepare,
        request_budget,
        wire_instruction,
    )
    from app.modules.knowledge.services.wiki_budget import request_usage
    from app.modules.knowledge.wiki_schemas import WikiPolicy

    source, catalog, structure, ids = source_fixture()
    payload = packet_payload('Nguồn báo cáo', [ids['r1']], decorate(catalog, structure), dependency_catalog([source], catalog))
    shape, wire, reverse = prepare(PacketDraft, payload)
    assert 'claims' in shape.model_fields and 'entities' not in shape.model_fields
    assert reverse[wire['metric_binding_targets'][0]['evidence_id']] == ids['r1']
    policy = WikiPolicy()
    assert request_budget(PacketDraft, DRAFT, payload, policy) == request_usage(shape, wire_instruction(PacketDraft,DRAFT,payload)+TRANSPORT_NOTE,wire,policy)
    shape, _, _ = prepare(SynthesisDraft, {**payload, 'draft':materialize_packet(claims(ids,catalog), {'evidence':catalog})})
    assert 'heading' in shape.model_fields['sections'].annotation.__args__[0].model_fields


def test_grounded_review_compacts_instructions_without_cutting_source_or_review_contract():
    from app.modules.knowledge.services.compilation_engine import REVIEW as LEGACY_REVIEW
    from app.modules.knowledge.services.compilation_engine import compact_evidence
    from app.modules.knowledge.services.compilation_review import packet_review_payload
    from app.modules.knowledge.services.compilation_transport import (
        prepare,
        request_budget,
        wire_instruction,
    )
    from app.modules.knowledge.wiki_schemas import WikiPolicy

    _,catalog,structure,ids=source_fixture()
    catalog['narrative']={**catalog[ids['u2']],'quote':'Mô tả nguồn cần giữ nguyên. '*70}
    payload={'evidence':compact_evidence(decorate(catalog,structure),catalog),'primary_evidence_ids':[ids['r1']],
             'source_grounding_protocol':PROTOCOL}
    draft=materialize_packet(claims(ids,catalog),payload)
    review=packet_review_payload(payload,draft,{})
    assert review['evidence']==payload['evidence'] and review['draft']==draft
    assert review['temporal_review_targets'] and 'bound_qualifiers' in review
    shape,wire,_=prepare(PacketCheck,review)
    assert {'entity_validity','temporal_validity','qualifier_validity','verdict','counter_evidence_ids'}<=set(
        shape.model_fields['items'].annotation.__args__[0].model_fields)
    assert len(wire_instruction(PacketCheck,LEGACY_REVIEW,review))<len(LEGACY_REVIEW)
    assert request_budget(PacketCheck,LEGACY_REVIEW,review,WikiPolicy(max_output_tokens=8192,context_budget_tokens=24000))['fits']
    assert len(wire['evidence'])==len(catalog)


def test_long_context_remains_raw_evidence_without_becoming_an_unrelated_label_menu():
    from app.modules.knowledge.services.compilation_grounding import offered_spans
    from app.modules.knowledge.services.compilation_transport import prepare

    _,catalog,structure,ids=source_fixture()
    catalog['context']={**catalog[ids['u2']],'quote':'Phạm vi cần giữ đầy đủ để kiểm chứng. '*20}
    payload={'evidence':decorate(catalog,structure),'primary_evidence_ids':[ids['r1']],
             'source_grounding_protocol':PROTOCOL}
    all_spans=span_catalog(payload['evidence'])
    offered=offered_spans(payload)
    assert not any(v['evidence_id']=='context' for v in offered.values())
    _,wire,_=prepare(PacketDraft,payload)
    assert any(v['quote']==catalog['context']['quote'] for v in wire['evidence'].values())
    value=claims(ids,catalog)
    value['claims'][0]['metric']={'span_id':next(q for q,v in all_spans.items() if v['evidence_id']=='context')}
    with pytest.raises(AppException) as failure:
        materialize_packet(value,payload)
    assert failure.value.details['reason']=='unoffered_source_span'


@pytest.mark.parametrize('state,passed',[('valid',True),('invalid',False),('not_checked',False)])
def test_explicit_validity_is_correctness_not_presence_and_never_passes_unchecked(state,passed):
    from app.modules.knowledge.services.compilation_grounding import materialize_packet_review

    value={'items':[{'id':'a','verdict':'supported','entity_validity':'valid','temporal_validity':state,
                    'qualifier_validity':'valid','counter_evidence_ids':[],'reason':'Independent validity assessment.'}],
           'missed_evidence_ids':[]}
    payload={'draft':{'assertions':[{'id':'a','evidence_ids':['p','time','caption']}]},'evidence':{'p':{},'time':{},'caption':{}}}
    checked=PacketCheck.model_validate(materialize_packet_review(value,payload))
    assert checked.items[0].temporal_roles is passed and checked.items[0].entity_scope
    assert checked.items[0].evidence_ids==['p','time','caption']


def test_additional_review_proof_handles_roundtrip_to_canonical_source_ids():
    from app.modules.knowledge.services.compilation_grounding import (
        REVIEW_PROTOCOL,
        materialize_packet_review,
    )
    from app.modules.knowledge.services.compilation_transport import prepare, restore

    payload={'source_grounded_review_protocol':REVIEW_PROTOCOL,
             'evidence':{'source-proof':{},'counter-proof':{}},
             'draft':{'assertions':[{'id':'assertion','evidence_ids':['source-proof']}]}}
    shape,_,reverse=prepare(PacketCheck,payload)
    raw={'items':[{'id':'claim0','verdict':'contradicted','entity_validity':'invalid',
                   'temporal_validity':'valid','qualifier_validity':'valid',
                   'counter_evidence_ids':['u1'],'reason':'Additional source evidence contradicts the assertion.'}],
         'missed_evidence_ids':[]}
    restored=restore(shape.model_validate(raw).model_dump(),reverse)
    checked=PacketCheck.model_validate(materialize_packet_review(restored,payload))
    assert checked.items[0].id=='assertion' and checked.items[0].evidence_ids==['source-proof','counter-proof']
    assert checked.items[0].verdict=='contradicted' and not checked.items[0].entity_scope


@pytest.mark.parametrize('mode',['duplicate','foreign'])
def test_caption_requires_a_unique_native_paragraph_before_its_table(mode):
    source,catalog,structure,ids=source_fixture(context_mode=mode)
    # Rebuild native evidence from this hash-matched file, not from equal caption text elsewhere.
    native=native_tables([source],catalog,structure)
    checks=ledger(native,catalog)
    checks[ids['r0']]['field_plan']={'identity_columns':[0],'value_columns':[1],
                                   'context_evidence_id':ids['u2'],'temporal':[]}
    assert not native[ids['r0']]['native_preamble']
    assert table_records([ids['r1']],checks,native,catalog,structure)=={}


def test_native_indentation_keeps_raw_text_and_exact_literal_offset():
    source,catalog,structure,ids=source_fixture(context_mode='indent')
    native=native_tables([source],catalog,structure)
    block=native[ids['r0']]['native_preamble'][0]
    assert block['evidence_id']==ids['u2'] and block['raw_native_text'].startswith('\t')
    span=block['native_literal_span'];canonical=block['canonical_literal_span']
    assert block['raw_native_text'][span['start']:span['end']]==catalog[ids['u2']]['quote'][canonical['start']:canonical['end']]


def test_duplicate_canonical_caption_does_not_borrow_a_native_locator():
    source,catalog,structure,ids=source_fixture()
    catalog['other-caption']={**catalog[ids['u2']]}
    structure['other-caption']={'role':'paragraph'}
    native=native_tables([source],catalog,structure)
    assert native[ids['r0']]['native_preamble']==[]


@pytest.mark.parametrize('mode,excluded', [('both_unrelated',True),('missing',False),('disagree',False),('overlap',False)])
def test_refinement_excludes_only_two_explicit_unrelated_primary_decisions(mode,excluded):
    from app.modules.knowledge.services.compilation_engine import refinement_exclusions

    first = TopicSelection(unrelated_evidence_ids=['row'],relevant_evidence_ids=['heading'])
    second = first.model_copy(deep=True)
    if mode=='missing':
        second.unrelated_evidence_ids=[]
    elif mode=='disagree':
        second=TopicSelection(relevant_evidence_ids=['row','heading'])
    elif mode=='overlap':
        second.relevant_evidence_ids.append('row')
    result=refinement_exclusions(first,second,['row'],{'row':{},'heading':{}})
    assert result==({'row'} if excluded else set())


def field_case(value_columns=None):
    source,catalog,structure,ids=source_fixture()
    native=native_tables([source],catalog,structure)
    checks=ledger(native,catalog)
    checks[ids['r0']]['field_plan']={'identity_columns':[0],'value_columns':value_columns or [1,2],
        'context_evidence_id':ids['u2'],'temporal':[]}
    return source,catalog,structure,ids,native,checks


def test_frame_and_column_metric_are_distinct_and_records_cannot_be_renamed():
    _,catalog,structure,ids,native,checks=field_case()
    records=table_records([ids['r1']],checks,native,catalog,structure)
    record=next(v for v in records.values() if v['assertion']['value']=='416')
    scopes={s['dimension']:s['value'] for s in record['assertion']['scope']}
    assert scopes['source_metric']=='Nhập học' and scopes['source_table_context']=='Đây là kết quả phản hồi.'
    assert record['entity']['label']=='Alpha'
    packet={'primary_evidence_ids':[ids['r1']],'column_role_reviews':checks,
            'draft':{'entities':[deepcopy(record['entity'])],'assertions':[deepcopy(record['assertion'])]}}
    validate_record_packet(packet,native,catalog,structure)
    packet['draft']['assertions'][0]['attribute']='planned_quota'
    with pytest.raises(AppException):
        validate_record_packet(packet,native,catalog,structure)


def test_composite_identity_is_an_exact_contiguous_source_span():
    _,catalog,structure,ids,native,checks=field_case([2])
    checks[ids['r0']]['field_plan']['identity_columns']=[0,1]
    records=table_records([ids['r1']],checks,native,catalog,structure)
    assert len(records)==1
    record=next(iter(records.values()))
    assert record['entity']['label']=='Alpha | 416' and record['assertion']['value']=='272'
    assert record['entity']['label'] in catalog[ids['r1']]['quote']
    checks[ids['r0']]['field_plan']['identity_columns']=[0,3]
    assert table_records([ids['r1']],checks,native,catalog,structure)=={}


@pytest.mark.parametrize('mode',['quantity_as_subject','context_as_value'])
def test_free_claims_cannot_use_a_quantity_as_subject_or_context_as_primary_value(mode):
    _,catalog,_,ids=source_fixture()
    value=claims(ids,catalog)
    if mode=='quantity_as_subject':
        value['claims'][0]['subject']=selected(catalog,ids['r1'],'416')
        payload={'evidence':catalog,'primary_evidence_ids':[ids['r1']]}
    else:
        payload={'evidence':catalog,'primary_evidence_ids':[ids['u2']]}
    with pytest.raises(AppException) as failure:
        materialize_packet(value,payload)
    assert failure.value.details['reason']=='claim_outside_primary_content_role'


def test_header_is_supporting_context_only_with_its_actual_record_row_and_assertion():
    from app.modules.knowledge.services.compilation_columns import header_coverage, header_support

    _,catalog,structure,ids,native,checks=field_case()
    records=table_records([ids['r1']],checks,native,catalog,structure)
    support=header_support([ids['r0'],ids['r1']],records,structure)
    assert support=={ids['r0']:[ids['r1']]}
    assert header_support([ids['r0']],records,structure)=={}
    assert header_coverage(support,[])[ids['r0']]['assertion_ids']==[]
    assert header_coverage(support,[r['assertion'] for r in records.values()])[ids['r0']]['assertion_ids']


def test_section_verdict_is_bound_to_complete_server_scope_without_overriding_verdict():
    from pydantic import ValidationError

    from app.modules.knowledge.compilation_runtime_schemas import SynthesisCheck
    from app.modules.knowledge.services.compilation_transport import prepare

    payload={'source_grounding_protocol':PROTOCOL,'evidence':{},
             'draft':{'assertions':[{'id':'a'},{'id':'b'}]},
             'synthesis':{'sections':[{'assertion_ids':['a','b']}],'relations':[]}}
    shape,_,_=prepare(SynthesisCheck,payload)
    value={'sections':[{'index':0,'verdict':'unresolved','reason':'One assertion lacks its scope.'}],'relations':[]}
    shape.model_validate(value)
    checked=materialize_section_reviews(value,payload)
    assert checked['sections'][0]['assertion_ids']==['a','b'] and checked['sections'][0]['verdict']=='unresolved'
    with pytest.raises(ValidationError):
        shape.model_validate({'sections':[{**value['sections'][0],'assertion_ids':['a']}],'relations':[]})
    with pytest.raises(AppException):
        materialize_section_reviews({'sections':[],'relations':[]},payload)


def test_note_blocks_only_its_own_field_and_unknown_is_never_zero():
    _,catalog,structure,ids,native,checks=field_case([1,2,3])
    alpha=table_records([ids['r1']],checks,native,catalog,structure)
    assert {r['assertion']['value'] for r in alpha.values()}=={'416','272'}
    structure[ids['r2']]['explicit_context_evidence_ids'].append(ids['u4'])  # Same explicit field note, also in row context.
    beta=table_records([ids['r2']],checks,native,catalog,structure)
    assert {r['assertion']['value'] for r in beta.values()}=={'200','100'}  # c4 note needs interpretation.
    structure[ids['r2']].pop('field_notes')
    structure[ids['r2']]['explicit_context_evidence_ids'].remove(ids['u4'])
    beta=table_records([ids['r2']],checks,native,catalog,structure)
    zero=next(r for r in beta.values() if r['assertion']['value']=='0')
    assert zero['assertion']['value_state']=='present'


@pytest.mark.parametrize('invalid', ['sibling_year','other_context','bad_column'])
def test_field_plan_cannot_inherit_sibling_year_or_foreign_context(invalid):
    _,catalog,structure,ids,native,checks=field_case([1])
    plan=checks[ids['r0']]['field_plan']
    if invalid=='sibling_year':
        plan['temporal']=[{'role':'data','years':[2027],'evidence_ids':[ids['r0']]}]
    elif invalid=='other_context':
        plan['context_evidence_id']=ids['u7']
    else:
        plan['value_columns']=[99]
    with pytest.raises(AppException):
        table_records([ids['r1']],checks,native,catalog,structure)


def test_pure_record_wire_cannot_add_an_unsupported_unknown_or_free_label():
    from pydantic import ValidationError

    from app.modules.knowledge.services.compilation_transport import prepare

    _,catalog,structure,ids,native,checks=field_case()
    records=table_records([ids['r1']],checks,native,catalog,structure)
    payload={'source_grounding_protocol':PROTOCOL,'records_only':True,'table_records':records,
             'evidence':decorate(catalog,structure)}
    shape,wire,_=prepare(PacketDraft,payload)
    assert 'source_spans' not in wire
    with pytest.raises(ValidationError):
        shape.model_validate({'record_ids':[],'claims':[{'invented':'planned target unknown'}]})
    rid=next(iter(records))
    good=materialize_packet({'record_ids':[rid]},payload)
    assert good['entities'][0]['label']=='Alpha'
    with pytest.raises(AppException):
        materialize_packet({'record_ids':[rid,rid]},payload)


def test_synthesis_even_supported_by_model_cannot_edit_the_server_statement():
    from app.modules.knowledge.compilation_runtime_schemas import SynthesisCheck
    from app.modules.knowledge.services.compilation_validation import check_synthesis

    _,catalog,structure,ids,native,checks=field_case()
    records=table_records([ids['r1']],checks,native,catalog,structure)
    rid=next(r for r,v in records.items() if v['assertion']['value']=='416')
    draft=materialize_packet({'record_ids':[rid]},{'evidence':catalog,'table_records':records})
    plan={'relations':[],'sections':[{'heading':selected(catalog,ids['r0'],'Nhập học'),'assertion_ids':[rid]}]}
    synthesis=materialize_synthesis(plan,{'draft':draft,'evidence':catalog})
    review=SynthesisCheck(sections=[{'index':0,'verdict':'supported','assertion_ids':[rid],'reason':'A model approved this.'}])
    assert check_synthesis(draft,synthesis,review,decorate(catalog,structure))['complete']
    synthesis['sections'][0]['text']+=' Planned admission quota.'
    assert not check_synthesis(draft,synthesis,review,decorate(catalog,structure))['complete']


@pytest.mark.asyncio
@pytest.mark.parametrize('repair_required',[False,True])
async def test_complete_compiler_and_storage_readback_contract_with_grounded_candidates(repair_required):
    from app.modules.knowledge.services.compilation_engine import compile_topic

    source, _, _, ids = source_fixture()

    class GroundedModel(Model):
        reviewed=0

        async def __call__(self, contract, instruction, payload):
            if contract is PacketCheck and repair_required:
                self.reviewed+=1
                assert 'candidate_correction' not in payload and 'topic' not in payload
                if self.reviewed==1:
                    assertion=payload['draft']['assertions'][0]
                    return contract(items=[{'id':assertion['id'],'verdict':'unresolved','entity_scope':False,
                        'temporal_roles':True,'conditions_complete':True,'evidence_ids':assertion['evidence_ids'],
                        'reason':'Recheck the candidate entity scope against the raw table.'}])
            if contract is PacketCoverage:
                assert payload['topic'] == 'Số liệu báo cáo'
                return contract(missed_evidence_ids=[],reason='Every relevant raw primary proof is represented.')
            if contract is ColumnRole:
                return ColumnRole(role='column_headers', columns=['Nhóm','Nhập học','Khảo sát','2027'],
                    evidence_ids=list(payload['evidence']), reason='Column labels describe both following records.')
            if contract is TableFields:
                metric = next(p for p,r in payload['evidence'].items() if r['quote'].startswith('Đây'))
                return contract(identity_columns=[0],value_columns=[1,2],context_evidence_id=metric,temporal=[])
            if contract is TopicSelection:
                chosen_ids = [p for p in payload['evidence'] if p == ids['r1']]
                return contract(relevant_evidence_ids=chosen_ids, unrelated_evidence_ids=sorted(set(payload['evidence'])-set(chosen_ids)))
            if contract is PacketDraft:
                assert payload['source_grounding_protocol'] == PROTOCOL
                record = next(rid for rid,r in payload['table_records'].items() if r['assertion']['value']=='416')
                return contract.model_validate(materialize_packet({'record_ids':[record],'claims':[]}, payload))
            if contract is SynthesisDraft:
                plan = {'relations': [], 'sections':[{'heading':selected(payload['evidence'],ids['r0'],'Nhập học'),
                    'assertion_ids':[payload['draft']['assertions'][0]['id']]}]}
                return contract.model_validate(materialize_synthesis(plan,payload))
            return await super().__call__(contract, instruction, payload)

    result = await compile_topic([source], 'c603', 'Số liệu báo cáo', ACTOR, GroundedModel(), 'ground616')
    assert result['machine_complete'] is not repair_required
    assert result['publication'] == 'unpublished'
    assert result['native_table_evidence']
    assert len(result['packet_results'][0]['column_role_reviews']) == 1
    validate_result(result, [source], 'c603')
    if repair_required:
        repaired=result['packet_results'][0]['semantic_repair']
        assert repaired['outcome']=='unchanged' and not repaired['initial']['review']['complete']
        assert repaired['candidate']['review']['complete']  # A later passing vote cannot approve the same failed fact.
        assert repaired['initial']['draft']==result['packet_results'][0]['draft']
        changed=deepcopy(result)
        changed['packet_results'][0]['semantic_repair']['initial']['review']['complete']=True
        changed['sha256']=digest({k:v for k,v in changed.items() if k!='sha256'})
        with pytest.raises(AppException):
            validate_result(changed,[source],'c603')
    from app.modules.knowledge.services.compilation_validation import validate_grounded_coverage

    for mutation in ('missing_audit','missing_assertion','missing_primary','reduced_offer','wrong_hash'):
        packet=deepcopy(result['packet_results'][0])
        audit=packet['coverage_review']
        if mutation=='missing_audit':
            audit['reviews']=[]
        elif mutation=='missing_assertion':
            audit['assertion_ids']=[]
            audit['assertions_hash']=digest([])
        elif mutation=='missing_primary':
            audit['reviews'][0]['primary_evidence_ids']=[]
        elif mutation=='reduced_offer':
            audit['reviews'][0]['offered']=[]
        else:
            audit['assertions_hash']='0'*64
        with pytest.raises(AppException):
            validate_grounded_coverage(packet,result['binding']['evidence'])
    changed=deepcopy(result)
    changed['topic_selection']['selected']=[]
    changed['sha256']=digest({k:v for k,v in changed.items() if k!='sha256'})
    with pytest.raises(AppException) as failure:
        validate_result(changed,[source],'c603')
    assert failure.value.details['reason']=='topic_refinement_coverage'


@pytest.mark.asyncio
@pytest.mark.parametrize('valid,missed',[(True,False),(False,False),(True,True)])
async def test_truth_is_blind_to_question_but_coverage_retains_it_and_both_can_block(valid,missed):
    from app.modules.knowledge.services.compilation_grounding import REVIEW
    from app.modules.knowledge.services.compilation_review import review_packet

    _,catalog,structure,ids=source_fixture()
    draft=materialize_packet(claims(ids,catalog),{'evidence':catalog})
    payload={'topic':'An unproved hypothesis in the question','evidence':decorate(catalog,structure),
             'primary_evidence_ids':[ids['r1']],'source_grounding_protocol':PROTOCOL}
    calls=[]

    async def bounded(contract,instruction,offered):
        calls.append(contract)
        assert offered['evidence']==payload['evidence']
        if contract is PacketCheck:
            assert 'topic' not in offered
            assert offered['draft']==draft
            return contract(items=[{'id':'a','verdict':'supported' if valid else 'unresolved',
                'entity_scope':valid,'temporal_roles':valid,'conditions_complete':valid,
                'evidence_ids':draft['assertions'][0]['evidence_ids'],'reason':'Independent source truth audit.'}])
        assert contract is PacketCoverage and offered['topic']==payload['topic']
        return contract(missed_evidence_ids=[ids['r1']] if missed else [],reason='Separate topic coverage audit.')

    audit={}
    check=await review_packet(payload,draft,{},bounded,REVIEW,record_coverage=audit.update)
    assert calls==[PacketCheck,PacketCoverage]
    assert check.items[0].entity_scope is valid
    assert bool(check.missed_evidence_ids) is missed
    assert audit['primary_evidence_ids']==payload['primary_evidence_ids']
    assert audit['offered_evidence_ids']==list(payload['evidence'])
    if not valid or missed:
        assert not check_packet(draft,check,payload['primary_evidence_ids'],payload['evidence'])['complete']


@pytest.mark.parametrize('role',['column_headers','data','unresolved'])
def test_blind_column_verdict_binds_fixed_native_scope_without_model_copying_labels(role):
    from app.modules.knowledge.services.compilation_columns import materialize_column_review
    from app.modules.knowledge.services.compilation_transport import prepare

    source,catalog,structure,ids=source_fixture()
    native=native_tables([source],catalog,structure)
    pid=ids['r0']
    payload={'candidate':{'evidence_id':pid},'native_proof':native[pid],'evidence':catalog}
    shape,_,_=prepare(ColumnRole,payload)
    assert 'columns' not in shape.model_fields and 'evidence_ids' not in shape.model_fields
    result=materialize_column_review({'role':role,'counter_evidence_ids':[],
        'reason':'Semantic role audited against both raw following rows.'},payload)
    assert result['role']==role
    assert result['evidence_ids']==[pid,*native[pid]['body_evidence_ids']]
    assert result['columns']==(['Nhóm','Nhập học','Khảo sát','2027'] if role=='column_headers' else [])


@pytest.mark.parametrize('quantity',['124/256','1.240/2.480','48,44%','2025'])
def test_prose_quantity_never_becomes_subject_and_lexical_role_is_offered(quantity):
    from app.modules.knowledge.services.compilation_grounding import extraction_choices

    _,catalog,_,ids=source_fixture()
    pid=ids['r1']
    catalog[pid]['quote']=f'Tổng số phản hồi là {quantity} đạt tỷ lệ.'
    choices=span_catalog({pid:catalog[pid]})
    subjects,metrics,_=extraction_choices({'evidence':{pid:catalog[pid]}},choices)
    numeric=next(q for q,v in choices.items() if v['literal']==quantity)
    lexical=next(q for q,v in choices.items() if v['literal']=='Tổng số phản hồi là')
    assert numeric not in subjects and numeric not in metrics
    assert lexical in subjects and lexical in metrics


def test_synthesis_and_packet_retain_raw_native_header_witnesses_without_promoting_canonical_role():
    from app.modules.knowledge.services.compilation_catalog import dependency_catalog
    from app.modules.knowledge.services.compilation_columns import compact_native_context
    from app.modules.knowledge.services.compilation_engine import packet_payload, synthesis_payload

    source,catalog,structure,ids=source_fixture()
    native=native_tables([source],catalog,structure)
    offered=decorate(catalog,structure)
    offered[ids['r0']]['compiler_native_context']=compact_native_context(native[ids['r0']])
    draft=materialize_packet(claims(ids,catalog),{'evidence':catalog})
    context=dependency_catalog([source],catalog,structure)
    payloads=[packet_payload('Report',[ids['r1']],offered,context),
              synthesis_payload('Report',draft,draft['assertions'],offered,context)]
    for payload in payloads:
        proof=payload['native_table_context'][0]
        assert proof['native_format_contrast']==native[ids['r0']]['native_format_contrast']
        assert set(proof['body_evidence_ids'])<=set(payload['evidence'])
        assert proof['candidate_evidence_id']==ids['r0']
        assert payload['evidence'][ids['r0']]['structural_evidence']['header_status']=='unresolved'
    relevance=packet_payload('Report',[ids['r1']],offered,context,native_witnesses=False)
    assert 'native_format_contrast' not in relevance['native_table_context'][0]
    assert 'body_evidence_ids' not in relevance['native_table_context'][0]
    assert relevance['native_table_context'][0]['native_preamble']
    from app.modules.knowledge.services.compilation_structure import offered_refs

    assert set(relevance['evidence'])==set(offered_refs([ids['r1']],offered,context))


@pytest.mark.asyncio
@pytest.mark.parametrize('fits',[True,False])
async def test_semantic_repair_rejected_or_not_run_never_changes_the_effective_candidate(monkeypatch,fits):
    from app.modules.knowledge.services import compilation_candidate_repair as repair
    from app.modules.knowledge.wiki_schemas import WikiPolicy

    _,catalog,_,ids=source_fixture()
    draft=materialize_packet(claims(ids,catalog),{'evidence':catalog})
    initial={'key':'initial','draft':draft,'primary_evidence_ids':[ids['r1']],
        'review':{'complete':False,'items':[{'id':'a','verdict':'unresolved','entity_scope':False,
            'temporal_roles':True,'conditions_complete':True,'evidence_ids':draft['assertions'][0]['evidence_ids'],
            'reason':'The semantic role remains unproved.'}],'missed_evidence_ids':[]}}
    monkeypatch.setattr(repair,'planned_request_budget',lambda *a,**k:{'fits':fits})
    calls=[]

    async def extract(payload,key):
        assert payload['evidence']==catalog and payload['candidate_correction']['rejected_items']
        calls.append(key)
        return {**deepcopy(initial),'key':key}

    result=await repair.repair_semantics({'topic':'Report','evidence':catalog},initial,extract,'original',WikiPolicy())
    assert {k:v for k,v in result.items() if k!='semantic_repair'}==initial
    assert not result['review']['complete']
    assert len(calls)==int(fits)
    assert result['semantic_repair']['outcome']==('unchanged' if fits else 'not_run')


@pytest.mark.asyncio
async def test_only_a_changed_source_binding_with_fresh_complete_review_can_replace_a_failed_candidate():
    from app.modules.knowledge.services.compilation_candidate_repair import repair_semantics
    from app.modules.knowledge.services.compilation_review import review_packet
    from app.modules.knowledge.services.compilation_validation import validate_semantic_repair
    from app.modules.knowledge.wiki_schemas import WikiPolicy

    _,catalog,_,ids=source_fixture()
    pid=ids['r1']
    evidence={pid:{**catalog[pid],'quote':'Khoa Alpha có 416 sinh viên.','structural_evidence':{'role':'paragraph'}}}
    payload={'topic':'Số sinh viên','primary_evidence_ids':[pid],'evidence':evidence}

    async def candidate(subject,valid,key):
        value={'claims':[{'id':'a','subject':selected(evidence,pid,subject),
            'metric':selected(evidence,pid,'Khoa Alpha có'),'scalar':selected(evidence,pid,'416'),
            'value_state':'present'}]}
        draft=materialize_packet(value,payload)

        async def bounded(contract,instruction,offered):
            assert 'topic' not in offered if contract is PacketCheck else offered['topic']==payload['topic']
            if contract is PacketCoverage:
                return contract(missed_evidence_ids=[],reason='The primary statement is represented.')
            return contract(items=[{'id':'a','verdict':'supported' if valid else 'unresolved','entity_scope':valid,
                'temporal_roles':True,'conditions_complete':True,'evidence_ids':[pid],
                'reason':'The measured population is the faculty, not the unit noun.'}])

        audit={}
        check=await review_packet(payload,draft,{},bounded,'Independent review',record_coverage=audit.update)
        return {'key':key,'draft':draft,'primary_evidence_ids':[pid],'column_role_reviews':{},
                'coverage_review':audit,'review':check_packet(draft,check,[pid],evidence,column_roles={})}

    initial=await candidate('sinh viên',False,'original')

    async def extract(corrected,key):
        assert corrected['candidate_correction']['rejected_items']
        return await candidate('Khoa Alpha có',True,key)

    result=await repair_semantics(payload,initial,extract,'original',WikiPolicy())
    assert result['semantic_repair']['outcome']=='accepted' and result['review']['complete']
    assert not result['semantic_repair']['initial']['review']['complete']
    validate_semantic_repair(result,evidence,{'native_table_evidence':{},'source_structure':{}})


def test_synthesis_cannot_repeat_an_assertion_in_multiple_sections():
    _,catalog,_,ids=source_fixture()
    draft=materialize_packet(claims(ids,catalog),{'evidence':catalog})
    section={'heading':selected(catalog,ids['r0'],'Nhập học'),'assertion_ids':['a']}
    with pytest.raises(AppException) as failure:
        materialize_synthesis({'sections':[section,deepcopy(section)],'relations':[]},{'draft':draft,'evidence':catalog})
    assert failure.value.details['reason']=='grounded_section_assertion_partition'


def test_synthesis_planner_splits_for_rendered_review_even_when_generation_alone_fits(monkeypatch):
    from app.modules.knowledge.compilation_runtime_schemas import SynthesisCheck
    from app.modules.knowledge.services import compilation_engine as engine

    _,catalog,structure,ids=source_fixture()
    value=claims(ids,catalog)
    other=deepcopy(value['claims'][0])
    other.update(id='b',metric=selected(catalog,ids['r0'],'Khảo sát'),
        column=selected(catalog,ids['r0'],'Khảo sát'),scalar=selected(catalog,ids['r1'],'272'))
    value['claims'].append(other)
    draft=materialize_packet(value,{'evidence':catalog})
    checks=[]

    def budget(contract,instruction,payload,policy):
        count=len(payload['draft']['assertions'])
        checks.append((contract,count))
        return {'fits':contract is not SynthesisCheck or count==1}

    monkeypatch.setattr(engine,'plan_usage',budget)
    batches=engine.synthesis_batches('Report',draft,decorate(catalog,structure))
    assert len(batches)==2
    assert {a['id'] for batch in batches for a in batch['draft']['assertions']}=={'a','b'}
    assert (SynthesisCheck,2) in checks
