"""Compiler receives source-bound structure without changing canonical evidence."""
import hashlib
from copy import deepcopy

import pytest

from app.modules.knowledge.normalization.retrieval_models import SourceUnit, UnitManifest
from app.modules.knowledge.normalization.retrieval_units import manifest_digest
from app.modules.knowledge.services.compilation_catalog import dependency_catalog
from app.modules.knowledge.services.compilation_contracts import evidence_catalog
from app.modules.knowledge.services.wiki_compiler import digest
from tests.test_compilation_engine_603 import ACTOR, Model, sample


def structured_source(*, blank_header=False, number=1):
    source = sample(number)
    heading = 'II. Báo cáo khảo sát'
    subheading = '1. Sinh viên tham gia'
    header = '| Nhóm | Nhập học | Khảo sát | 2027 |'
    emitted = '|  |  |  |  |' if blank_header else header
    separator = '| --- | --- | --- | --- |'
    rows = ([header] if blank_header else []) + ['| Alpha | 416 | 272 | ? |', '| Beta | 200 | 100 | 0 |']
    table = '\n'.join([emitted, separator, *rows])
    note = '(*) Chỉ áp dụng nhóm A; ngoại lệ nhóm B.'
    pieces = [heading, subheading, 'Đây là kết quả phản hồi.', table, note, 'III. Kết quả khác', '1. Sinh viên tham gia', 'Nội dung khác.']
    source.canonical_markdown = '\n\n'.join(pieces)
    source.canonical_hash = hashlib.sha256(source.canonical_markdown.encode()).hexdigest()
    units = []
    cursor = 0
    for index, text in enumerate(pieces):
        uid = f'u{index}'
        unit = SourceUnit(id=uid, qnu_block_id=uid, kind='paragraph', text=text, start=cursor, end=cursor+len(text))
        units.append(unit)
        cursor += len(text)+2
    parent = units[3]
    parent.kind, parent.is_container = 'table', True
    header_unit = parent.model_copy(deep=True, update={'id': 'h', 'parent_id': parent.id,
        'text': emitted+'\n'+separator, 'end': parent.start+len(emitted+'\n'+separator), 'is_container': False})
    units.append(header_unit)
    row_ids = []
    offset = parent.start+len(emitted+'\n'+separator)+1
    for index, text in enumerate(rows):
        uid = f'r{index}'
        row_ids.append(uid)
        units.append(SourceUnit(id=uid, qnu_block_id=uid, kind='table', parent_id=parent.id,
            text=text, start=offset, end=offset+len(text), context_refs=['h'],
            field_context_refs={'c4': ['u4']} if index == len(rows)-1 else {}))
        offset += len(text)+1
    manifest = UnitManifest(canonical_hash=source.canonical_hash, units=units)
    artifact = {'content_hash':source.canonical_hash, 'retrieval_units':manifest.model_dump(),
        'unit_manifest_hash':manifest_digest(manifest), 'tables':[{'id':'u3',
        'headers':['','','',''] if blank_header else ['Nhóm','Nhập học','Khảo sát','2027'],
        'header_paths':[[],[],[],[]] if blank_header else [['Nhóm'],['Nhập học'],['Khảo sát'],['2027']],
        'row_unit_ids':row_ids, 'rows':[[v.strip() for v in row.strip('|').split('|')] for row in rows],
        'row_fields':[[{'column_id':f'c{i+1}', 'raw':v.strip(), 'state':'ambiguous' if v.strip()=='?' else 'present'}
                       for i,v in enumerate(row.strip('|').split('|'))] for row in rows]}]}
    source.parse_provenance = {'structured_artifact':artifact}
    return source


def by_unit(catalog):
    return {v['unit_id']:pid for pid,v in catalog.items()}


def test_numbered_section_candidates_and_table_header_reach_row_without_crossing_branch():
    source = structured_source()
    original = deepcopy(vars(source))
    catalog = evidence_catalog([source], 'c603')
    ids = by_unit(catalog)
    context = dependency_catalog([source], catalog)
    assert {ids['u0'], ids['u1'], ids['u2'], ids['h']} <= set(context[ids['r0']])
    assert not {ids['u5'], ids['u6'], ids['u7']} & set(context[ids['r0']])
    assert ids['u5'] in context[ids['u7']] and ids['u0'] not in context[ids['u7']]
    assert vars(source) == original


def test_blank_header_keeps_raw_candidate_and_first_data_row_instead_of_promoting_role():
    from app.modules.knowledge.services.compilation_engine import packet_payload
    from app.modules.knowledge.services.compilation_structure import decorate, structural_catalog

    source = structured_source(blank_header=True)
    catalog = evidence_catalog([source], 'c603')
    ids = by_unit(catalog)
    context = dependency_catalog([source], catalog)
    structure = structural_catalog([source],catalog)
    offered = packet_payload('Khảo sát', [ids['r1']], decorate(catalog,structure), context)
    assert ids['r0'] in offered['evidence']
    node = offered['evidence'][ids['r1']]['structural_evidence']
    assert node['header_status']=='unresolved'
    assert structure[ids['r1']]['header_candidates']==[{'evidence_id':ids['r0'],'basis':'first_body_row_candidate_only'}]
    assert offered['evidence'][ids['h']]['structural_evidence']['header_candidates']==structure[ids['r1']]['header_candidates']
    assert ids['r0'] not in context[ids['r1']]  # Candidate navigation is not an established dependency.
    assert 'Alpha' in catalog[ids['r1']]['quote']
    assert len(catalog) == 11  # All canonical proofs survive, including candidate header and data.


def test_field_note_is_not_attached_to_other_row_or_other_revision():
    sources = [structured_source(number=1), structured_source(number=2)]
    catalog = evidence_catalog(sources, 'c603')
    context = dependency_catalog(sources, catalog)
    for source in sources:
        own = {pid:ref for pid,ref in catalog.items() if ref['source_revision_id']==source.id}
        ids = by_unit(own)
        assert ids['u4'] in context[ids['r1']]
        assert ids['u4'] not in context[ids['r0']]
        assert all(catalog[pid]['source_revision_id']==source.id for pid in context[ids['r1']])


def test_cell_coordinates_preserve_column_year_unknown_zero_and_metric_distinction():
    from app.modules.knowledge.services.compilation_structure import structural_catalog

    source = structured_source()
    catalog = evidence_catalog([source],'c603')
    ids = by_unit(catalog)
    structure = structural_catalog([source],catalog)
    alpha, beta = structure[ids['r0']], structure[ids['r1']]
    assert [cell['raw'] for cell in alpha['cells']]==['Alpha','416','272','?']
    assert [cell['header_path'] for cell in alpha['cells']]==[['Nhóm'],['Nhập học'],['Khảo sát'],['2027']]
    assert alpha['cells'][3]['state']=='ambiguous' and beta['cells'][3]['raw']=='0'
    assert 'field_notes' not in alpha
    assert beta['field_notes']==[{'column_id':'c4','evidence_ids':[ids['u4']],'basis':'explicit_field_link'}]


def test_corrupt_field_metadata_cannot_replace_literal_cell_value():
    from app.modules.knowledge.services.compilation_structure import structural_catalog

    source = structured_source()
    source.parse_provenance['structured_artifact']['tables'][0]['row_fields'][0][2]['raw']='9999'
    catalog = evidence_catalog([source],'c603')
    cell = structural_catalog([source],catalog)[by_unit(catalog)['r0']]['cells'][2]
    assert cell['raw']=='272' and cell['state']=='ambiguous' and cell['field_alignment']=='unresolved'


def test_header_candidate_does_not_consume_alpha_north_data_or_infer_numeric_role():
    from app.modules.knowledge.services.compilation_structure import structural_catalog

    source = structured_source(blank_header=True)
    table = source.parse_provenance['structured_artifact']['tables'][0]
    table['row_unit_ids']=table['row_unit_ids'][1:]  # Missing header locator must remain visible as uncertainty.
    catalog = evidence_catalog([source],'c603')
    ids = by_unit(catalog)
    node = structural_catalog([source],catalog)[ids['r1']]
    assert node['header_status']=='unresolved'
    assert 'Alpha' in catalog[node['header_candidates'][0]['evidence_id']]['quote']
    assert len(catalog)==11 and catalog[ids['r1']]['quote'].startswith('| Alpha')


def test_multilevel_header_paths_and_escaped_pipes_keep_positional_cells():
    from app.modules.knowledge.parsers.markdown_parser import _split_gfm_row
    from app.modules.knowledge.services.compilation_structure import structural_catalog

    assert _split_gfm_row('| A\\|B | 0 | ? |')==['A|B','0','?']
    source = structured_source()
    source.parse_provenance['structured_artifact']['tables'][0]['header_paths'][2]=['Kết quả','Khảo sát']
    catalog = evidence_catalog([source],'c603')
    cell = structural_catalog([source],catalog)[by_unit(catalog)['r0']]['cells'][2]
    assert cell['column_index']==2 and cell['header_path']==['Kết quả','Khảo sát']


def test_request_handles_map_all_structural_proofs_without_rewriting_raw_text():
    from app.modules.knowledge.compilation_runtime_schemas import PacketDraft
    from app.modules.knowledge.services.compilation_engine import packet_payload
    from app.modules.knowledge.services.compilation_structure import (
        decorate,
        navigation_refs,
        structural_catalog,
    )
    from app.modules.knowledge.services.compilation_transport import prepare

    source = structured_source(blank_header=True)
    catalog = evidence_catalog([source],'c603')
    structure = structural_catalog([source],catalog)
    payload = packet_payload('Khảo sát',[by_unit(catalog)['r2']],decorate(catalog,structure),dependency_catalog([source],catalog))
    _,wire,reverse = prepare(PacketDraft,payload)
    for ref in wire['evidence'].values():
        assert set(navigation_refs(ref.get('structural_evidence',{}))) <= set(wire['evidence'])
    for pid,ref in wire['evidence'].items():
        assert ref['quote']==catalog[reverse[pid]]['quote']


def test_missing_or_foreign_structural_reference_fails_closed():
    from app.modules.knowledge.services.compilation_structure import offered_refs

    catalog={'p':{'source_revision_id':'s','structural_evidence':{'section_evidence_ids':['foreign']}},
             'foreign':{'source_revision_id':'other'}}
    with pytest.raises(ValueError):
        offered_refs(['p'],catalog)
    del catalog['foreign']
    with pytest.raises(ValueError):
        offered_refs(['p'],catalog)


def test_large_structural_context_is_blocked_without_dropping_qualifier_evidence():
    from app.core.exceptions import AppException
    from app.modules.knowledge.compilation_runtime_schemas import CompilerPolicy
    from app.modules.knowledge.services.compilation_engine import plan_packets

    catalog={'row':{'binding_id':'b','start':100,'source_revision_id':'s','quote':'| A | 1 |',
                    'structural_evidence':{'header_evidence_ids':['h']}},
             'h':{'binding_id':'b','start':0,'source_revision_id':'s','quote':'Đơn vị '*10000}}
    before=deepcopy(catalog)
    with pytest.raises(AppException):
        plan_packets('Metric',catalog,{},CompilerPolicy(),['row'])
    assert catalog==before


@pytest.mark.asyncio
async def test_engine_persists_revalidates_structure_and_invalidates_changed_field_link_cache():
    from app.core.exceptions import AppException
    from app.modules.knowledge.services.compilation_engine import compile_topic
    from app.modules.knowledge.services.compilation_validation import validate_result

    source=structured_source()
    calls=[]
    model=Model()
    async def generate(contract,instruction,payload):
        calls.append(deepcopy(payload))
        return await model(contract,instruction,payload)
    bundle=await compile_topic([source],'c603','Kết quả khảo sát',ACTOR,generate,'614')
    assert bundle['source_structure'] and any('structural_evidence' in ref for payload in calls for ref in payload.get('evidence',{}).values())
    assert bundle['publication']=='unpublished' and bundle['usage']=='review_only'
    validate_result(bundle,[source],'c603')
    corrupted=deepcopy(bundle)
    next(iter(corrupted['source_structure'].values()))['role']='fabricated'
    corrupted['sha256']=digest({k:v for k,v in corrupted.items() if k!='sha256'})
    with pytest.raises(AppException) as error:
        validate_result(corrupted,[source],'c603')
    assert error.value.details['reason']=='source_structure_drift'
    cache={p['key']:p for p in [*bundle['packet_results'],*bundle['topic_results']]}
    artifact=source.parse_provenance['structured_artifact']
    unit=next(u for u in artifact['retrieval_units']['units'] if u['id']=='r1')
    unit['field_context_refs']={'c3':['u4']}
    artifact['unit_manifest_hash']=manifest_digest(UnitManifest.model_validate(artifact['retrieval_units']))
    changed=await compile_topic([source],'c603','Kết quả khảo sát',ACTOR,model,'614',cache)
    assert changed['reused_packets']==0 and changed['reused_topic_packets']==0
    assert changed['binding']['snapshot_hash']==bundle['binding']['snapshot_hash']
    assert changed['source_structure']!=bundle['source_structure']


@pytest.mark.parametrize('damage',['duplicate_header','header_text_disagrees'])
def test_header_role_needs_unique_literal_layout_evidence(damage):
    from app.modules.knowledge.services.compilation_structure import structural_catalog

    source=structured_source()
    artifact=source.parse_provenance['structured_artifact']
    if damage=='duplicate_header':
        header=deepcopy(next(u for u in artifact['retrieval_units']['units'] if u['id']=='h'))
        header['id']='h-duplicate'
        artifact['retrieval_units']['units'].append(header)
        artifact['unit_manifest_hash']=manifest_digest(UnitManifest.model_validate(artifact['retrieval_units']))
    else:
        artifact['tables'][0]['headers'][2]='Một tên cột không có trong nguồn'
    catalog=evidence_catalog([source],'c603')
    assert structural_catalog([source],catalog)[by_unit(catalog)['r0']]['header_status']=='unresolved'


def test_compact_structure_preserves_column_overrides_and_temporal_authority_once():
    from app.modules.knowledge.compilation_runtime_schemas import PacketDraft
    from app.modules.knowledge.services.compilation_engine import (
        navigation_temporal,
        packet_payload,
    )
    from app.modules.knowledge.services.compilation_structure import (
        compact_structure,
        decorate,
        structural_catalog,
    )
    from app.modules.knowledge.services.compilation_transport import prepare

    source=structured_source()
    source.parse_provenance['structured_artifact']['tables'][0]['row_fields'][0][2]['header_path']=['Riêng nhóm A']
    catalog=evidence_catalog([source],'c603')
    ids=by_unit(catalog)
    structure=structural_catalog([source],catalog)
    compact=compact_structure(structure[ids['r0']])
    assert compact['cell_header_path_overrides']==[{'column_index':2,'header_path':['Riêng nhóm A']}]
    payload=packet_payload('Khảo sát',[ids['r0']],decorate(catalog,structure),dependency_catalog([source],catalog))
    hints={pid:{'data_years':[2027],'status':'proposed','role':'data'} for pid in payload['evidence']}
    payload['temporal_context']=navigation_temporal(hints,hints)
    _,wire,reverse=prepare(PacketDraft,payload)
    assert wire['temporal_navigation_policy']['authority']=='not_source_authored_status_or_legal_verification'
    assert {reverse[pid]:value for pid,value in wire['temporal_context'].items()}==hints


def test_planner_measures_complete_source_and_temporal_metadata_without_fixed_correction_reserve():
    from app.modules.knowledge.compilation_runtime_schemas import CompilerPolicy
    from app.modules.knowledge.services import compilation_engine as engine
    from app.modules.knowledge.wiki_schemas import WikiPolicy

    catalog={'p':{'source_revision_id':'s','binding_id':'b','start':0,'quote':'Nguồn '*40}}
    proofs={'s':{'origin_file_hash':'a'*64,'artifact_hash':'b'*64}}
    temporal={'p':{'role':'unknown','issued_date':'2024-01-01'}}
    payload=engine.packet_payload('Chủ đề',['p'],catalog,{},proofs,temporal)
    budget=engine.packet_budget(payload,WikiPolicy(max_output_tokens=8192,context_budget_tokens=64000))
    policy=WikiPolicy(max_output_tokens=8192,context_budget_tokens=budget['total_reserved']+20)
    assert engine.packet_budget(payload,policy)['fits']
    assert not engine.request_usage(engine.PacketDraft,engine.DRAFT,payload,policy,feedback_reserve=1500)['fits']
    planned=engine.plan_packets('Chủ đề',catalog,{},CompilerPolicy(),transport=policy,source_proofs=proofs,temporal=temporal)
    assert planned==[payload]
    assert planned[0]['source_proofs']==proofs and planned[0]['temporal_context']


def test_topic_planner_budgets_independent_selection_with_full_prior_result():
    from app.modules.knowledge.services import compilation_engine as engine
    from app.modules.knowledge.wiki_schemas import WikiPolicy

    catalog={f'p{i}':{'binding_id':'b','start':i,'source_revision_id':'s','quote':'Dữ liệu '*40} for i in range(80)}
    policy=WikiPolicy(max_output_tokens=8192,context_budget_tokens=24000)
    batches=engine.topic_batches('Chủ đề',catalog,policy)
    assert set().union(*(set(b['evidence']) for b in batches))==set(catalog)
    for payload in batches:
        prior={'relevant_evidence_ids':[list(payload['evidence'])[-1]]*128,
               'unrelated_evidence_ids':[list(payload['evidence'])[-1]]*128}
        assert engine.request_usage(engine.TopicSelection,engine.VERIFY_TOPIC,{**payload,'prior_selection':prior},policy)['fits']


def test_operational_packet_count_can_scale_without_changing_default_or_evidence():
    from app.modules.knowledge.compilation_runtime_schemas import CompilerPolicy
    from app.modules.knowledge.services.compilation_engine import plan_packets

    assert CompilerPolicy().max_packets==30
    policy=CompilerPolicy(max_packets=64,max_primary_per_packet=1,max_total_calls=256)
    catalog={f'p{i}':{'binding_id':'b','start':i,'source_revision_id':'s','quote':f'Giá trị {i}'} for i in range(40)}
    packets=plan_packets('Chủ đề',catalog,{},policy)
    assert len(packets)==40 and {pid for p in packets for pid in p['primary_evidence_ids']}==set(catalog)


@pytest.mark.asyncio
async def test_oversized_optional_repair_remains_visible_unresolved_without_source_trimming():
    from app.modules.knowledge.compilation_runtime_schemas import CoverageAudit, PacketDraft
    from app.modules.knowledge.services.compilation_coverage import reconcile
    from app.modules.knowledge.services.compilation_engine import DRAFT
    from app.modules.knowledge.services.compilation_transport import request_budget
    from app.modules.knowledge.wiki_schemas import WikiPolicy

    assertion={'id':'a','entity_id':'e','attribute':'Metric','value':'old '*700,'value_state':'present',
        'evidence_ids':['p'],'scope':[],'temporal':[],'condition_ids':[],'exception_ids':[]}
    payload={'topic':'Missing metric','primary_evidence_ids':['p','missing'],
        'evidence':{'p':{'source_revision_id':'s','quote':assertion['value']},
                    'missing':{'source_revision_id':'s','quote':'Missing requested fact. '*150}}}
    draft={'entities':[{'id':'e','label':'Entity','evidence_ids':['p']}],'assertions':[assertion],
           'deferred_evidence_ids':['missing']}
    check={'id':'a','verdict':'supported','entity_scope':True,'temporal_roles':True,'conditions_complete':True,
           'evidence_ids':['p'],'reason':'Existing evidence retained.'}
    initial={'draft':draft,'review':{'items':[check],'missed_evidence_ids':['missing'],'complete':False}}
    base=request_budget(PacketDraft,DRAFT,payload,WikiPolicy(context_budget_tokens=64000,max_output_tokens=8192))
    policy=WikiPolicy(context_budget_tokens=base['total_reserved']+100,max_output_tokens=8192)
    original=deepcopy((payload,initial))
    async def bounded(contract,instruction,offered):
        assert contract is CoverageAudit
        return CoverageAudit(items=[{'evidence_id':'missing','role':'required_assertion','assertion_ids':[],
                                    'reason':'Required missing scalar.'}])
    async def extract(*args):
        pytest.fail('Over-budget optional repair must not dispatch inference or discard source evidence')
    result=await reconcile(payload,initial,bounded,extract,'key',transport=policy)
    assert result['draft']==initial['draft'] and result['review']['complete'] is False
    assert result['review']['missed_evidence_ids']==['missing']
    deferred=result['coverage_reconciliation']['repair_capacity']
    assert deferred['status']=='NOT_RUN' and deferred['retained_evidence_ids']==['missing']
    assert deferred['budget']['fits'] is False
    assert (payload,initial)==original


def test_long_review_explanation_does_not_change_scope_or_completeness_verdict():
    from app.modules.knowledge.compilation_runtime_schemas import ItemCheck
    from app.modules.knowledge.services.compilation_validation import supported

    item=ItemCheck(id='a',verdict='supported',entity_scope=False,temporal_roles=True,
        conditions_complete=True,evidence_ids=['p'],reason='Bằng chứng phạm vi vẫn chưa được xác nhận. '*35)
    assert len(item.reason)>400 and supported(item.model_dump()) is False
    with pytest.raises(ValueError):
        ItemCheck.model_validate({**item.model_dump(),'reason':'x'*4097})


def test_planned_request_reserves_exact_minimal_correction_without_reserving_a_third_call():
    from app.modules.knowledge.compilation_runtime_schemas import PacketDraft
    from app.modules.knowledge.services.compilation_engine import DRAFT
    from app.modules.knowledge.services.compilation_transport import (
        TRANSPORT_NOTE,
        planned_request_budget,
        prepare,
        request_budget,
    )
    from app.modules.knowledge.services.wiki_budget import request_usage
    from app.modules.knowledge.wiki_schemas import WikiPolicy

    payload={'evidence':{'p':{'source_revision_id':'s','quote':'Raw source ? and 0.'}},'primary_evidence_ids':['p']}
    policy=WikiPolicy(max_output_tokens=8192,context_budget_tokens=64000)
    prepared,wire,_=prepare(PacketDraft,payload)
    initial=request_usage(prepared,DRAFT+TRANSPORT_NOTE,wire,policy)
    planned=planned_request_budget(PacketDraft,DRAFT,payload,policy)
    corrected={**payload,'output_format_feedback':{'reason':'json_contract'}}
    actual_correction=request_budget(PacketDraft,DRAFT,corrected,policy)
    assert planned['initial_request_total_reserved']==initial['total_reserved']
    assert planned['total_reserved']==actual_correction['total_reserved']>initial['total_reserved']
    assert 'minimal_format_correction_reserved' not in actual_correction
    assert payload['evidence']['p']['quote']=='Raw source ? and 0.'


@pytest.mark.asyncio
async def test_oversized_coverage_audit_keeps_all_debt_without_dispatch_or_fake_classification():
    from app.modules.knowledge.compilation_runtime_schemas import PacketDraft
    from app.modules.knowledge.services.compilation_coverage import reconcile
    from app.modules.knowledge.services.compilation_engine import DRAFT
    from app.modules.knowledge.services.compilation_transport import request_budget
    from app.modules.knowledge.wiki_schemas import WikiPolicy

    payload={'topic':'Metrics','primary_evidence_ids':['p','missing'],
        'evidence':{'p':{'source_revision_id':'s','quote':'Known '*100},
                    'missing':{'source_revision_id':'s','quote':'Missing evidence.'}}}
    assertions=[{'id':f'a{i}','entity_id':'e','attribute':f'Metric {i}','value':'Known '*100,
                 'value_state':'present','evidence_ids':['p'],'scope':[],'temporal':[],
                 'condition_ids':[],'exception_ids':[]} for i in range(32)]
    initial={'draft':{'entities':[{'id':'e','label':'Entity','evidence_ids':['p']}],
                     'assertions':assertions,'deferred_evidence_ids':['missing']},
             'review':{'items':[{'id':a['id'],'verdict':'unresolved','entity_scope':False,'temporal_roles':True,
                                'conditions_complete':True,'evidence_ids':['p'],'reason':'Not certified.'} for a in assertions],
                       'missed_evidence_ids':['missing'],'complete':False}}
    base=request_budget(PacketDraft,DRAFT,payload,WikiPolicy(context_budget_tokens=64000,max_output_tokens=8192))
    policy=WikiPolicy(context_budget_tokens=base['total_reserved']+100,max_output_tokens=8192)
    original=deepcopy((payload,initial))
    async def forbidden(*args):
        pytest.fail('An over-budget optional coverage request must remain NOT_RUN')
    result=await reconcile(payload,initial,forbidden,forbidden,'key',transport=policy)
    assert result['draft']==initial['draft'] and result['review']==initial['review']
    debt=result['coverage_reconciliation']
    assert debt['classifications']==[] and debt['remaining_evidence_ids']==['missing']
    assert debt['audit_capacity']['status']=='NOT_RUN' and debt['audit_capacity']['budget']['fits'] is False
    assert (payload,initial)==original
