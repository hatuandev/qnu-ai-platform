"""Source structure and scope regressions; names occur only in fixtures."""

from unittest.mock import AsyncMock, patch

import pytest

from app.modules.rag.evidence_blocks import pack_context, split_source_blocks
from app.modules.rag.evidence_schemas import QueryPlan


def handbook():
    text = ('## Handbook 2025\n\n### Page 1\n\n#### ALPHA PROGRAM\n\n'
            '- Duration: 4 years\n- Credits: 120\n\n#### DESCRIPTION\n\nAlpha description.\n\n'
            '#### CAREERS\n\nTeaching mathematics.\n\n### Page 2\n\n'
            '#### SCHOLARSHIPS\n\nOverseas research grants.\n\n'
            '### Page 3\n\n#### BETA PROGRAM\n\n- Duration: 4.5 years\n- Credits: 150\n\n'
            '#### DESCRIPTION\n\nBeta description.\n\n#### CAREERS\n\nSoftware engineering.\n\n'
            '#### SCHOLARSHIPS\n\nCorporate grants.')
    return split_source_blocks(text, binding_id='b', index_id='i', source_id='s', title='Handbook')


def test_repeated_record_heading_survives_same_level_subheading_and_page_label():
    source = handbook()
    from app.modules.rag.evidence_hierarchy import enrich_hierarchy
    enriched = enrich_hierarchy(source)
    scholarship = next(b for b in enriched if b.text == 'Overseas research grants.')
    assert scholarship.record_label == 'ALPHA PROGRAM'
    career = next(b for b in enriched if b.text == 'Software engineering.')
    assert career.record_label == 'BETA PROGRAM'
    assert [(b.id, b.text, b.start, b.end) for b in enriched] == [(b.id, b.text, b.start, b.end) for b in source]


def test_wrong_record_claim_is_rejected_even_with_matching_other_reference():
    from app.modules.rag.evidence_hierarchy import enrich_hierarchy, scope_error
    source = enrich_hierarchy(handbook())
    wrong = next(b for b in source if b.text == 'Software engineering.')
    correct = next(b for b in source if b.text == '- Duration: 4 years\n- Credits: 120')
    claim = {'references': [{'block_id': wrong.id}, {'block_id': correct.id}]}
    assert scope_error(claim, source, QueryPlan(query='Alpha careers?', entity='ALPHA PROGRAM'))
    assert not scope_error(claim, source, QueryPlan(query='Beta careers?', entity='BETA PROGRAM'))


def test_record_context_recovers_sibling_duration_and_stays_in_own_record():
    from app.modules.rag.evidence_hierarchy import enrich_hierarchy, record_candidates
    source = enrich_hierarchy(handbook())
    plan = QueryPlan(query='Beta duration and careers?', entity='BETA PROGRAM',
                     requested_topics=['Duration', 'CAREERS'])
    selected = record_candidates(source, plan, 10)
    assert any('4.5 years' in b.text for b in selected)
    assert not any(b.record_label == 'ALPHA PROGRAM' for b in selected)
    assert any('Software engineering' in b.text for b in selected)


def test_summary_heading_packs_complete_adjacent_numbered_list():
    source = split_source_blocks('## Handbook 2025\n\n**3 ROUTES**\n\n'
        '1. Examination\n2. School record\n3. Direct admission',
        binding_id='b', index_id='i', source_id='s', title='Official')
    summary = source[1]
    selected = pack_context(source, [summary], [2025], 8, 12000,
                            atomic_lists=True, enumeration_subject='ROUTES')
    assert any('3. Direct admission' in b.text for b in selected)


def test_query_topics_are_optional_and_backward_compatible():
    plan = QueryPlan(query='Question?')
    assert plan.requested_topics == [] and plan.education_level is None


def test_compound_legacy_plan_keeps_two_subsections_and_priority_body():
    from app.modules.rag.evidence_hierarchy import record_candidates
    source=handbook()
    plan=QueryPlan(query='Beta duration and careers?',entity='BETA PROGRAM',attribute='Duration and CAREERS')
    hits=record_candidates(source,plan,10)
    assert any('4.5 years' in b.text for b in hits) and any('Software engineering' in b.text for b in hits)
    other=next(b for b in source if b.text=='Alpha description.')
    chosen=pack_context(source,[other,*hits],[],2,16000,coverage_goals=['Alpha description'],
                        priority_ids={b.id for b in hits})
    assert any('Software engineering' in b.text for b in chosen)
    assert other.id not in {b.id for b in chosen}


def test_unknown_outline_does_not_invent_record_scope():
    from app.modules.rag.evidence_hierarchy import enrich_hierarchy
    source = split_source_blocks('## Chapter A\n\nGeneral policy.\n\n## Chapter B\n\nAnother policy.',
        binding_id='b', index_id='i', source_id='s', title='Official')
    assert all(b.record_label is None for b in enrich_hierarchy(source))


def test_unrecognized_unique_heading_ends_inferred_record_scope():
    from app.modules.rag.evidence_hierarchy import enrich_hierarchy
    source = handbook()
    end = max(b.end for b in source)
    unknown = source[-1].model_copy(update={'id':'new','start':end+2,'end':end+28,
        'text':'#### UNCLASSIFIED SUBJECT','record_label':None})
    body = unknown.model_copy(update={'id':'tail','start':end+30,'end':end+44,'text':'Unknown facts.'})
    assert enrich_hierarchy([*source,unknown,body])[-1].record_label is None


def test_bold_identifier_before_scalar_fields_does_not_inherit_previous_record():
    from app.modules.rag.evidence_hierarchy import enrich_hierarchy
    source = split_source_blocks('## Handbook\n\n#### ALPHA\n\n- Duration: 4 years\n- Credits: 120\n\n'
        '#### BETA\n\n**Code: 1234567**\n\nDuration: 4.5 years\n\nCredits: 150',
        binding_id='b',index_id='i',source_id='s',title='A')
    assert enrich_hierarchy(source)[-1].record_label == 'BETA'


def test_metadata_fields_are_not_an_unrequested_career_enumeration():
    from app.modules.rag.evidence_lists import matches_subject
    source=handbook()
    fields=next(b for b in source if b.text.startswith('- Duration: 4 years'))
    group=[fields.model_copy(update={'id':str(i),'text':text}) for i,text in enumerate(
        ['- Duration: 4 years','- Credits: 120','- Degree: Bachelor'])]
    assert not matches_subject(group,'CAREERS')
    unclassified=[b.model_copy(update={'record_label':None,'record_path':[]}) for b in group]
    assert matches_subject(unclassified,'CAREERS')


def test_no_record_hit_when_requested_attribute_is_absent():
    from app.modules.rag.evidence_hierarchy import record_candidates
    plan=QueryPlan(query='Beta admission combinations?',entity='BETA PROGRAM',requested_topics=['admission combinations'])
    assert record_candidates(handbook(),plan,10)==[]


def test_bold_scalar_values_remain_citable_without_publishing_bare_year_titles():
    from app.modules.rag.evidence_claims import bind_claims
    from app.modules.rag.evidence_passages import context_only, source_grounded_claims
    from app.modules.rag.evidence_schemas import AnswerProposal, EvidenceClaim, QuoteReference
    source=split_source_blocks('**Program 2025**\n\n**Code: 7440122**\n\n**5 routes — 5800 places**',
        binding_id='b',index_id='i',source_id='s',title='A')
    assert context_only(source[0]) and not context_only(source[1]) and not context_only(source[2])
    proposal=AnswerProposal(status='supported',claims=[EvidenceClaim(id='c',text=source[1].text,
        references=[QuoteReference(block_id=source[1].id,quote=source[1].text)])])
    claims,errors=bind_claims(proposal,source)
    assert not errors and source_grounded_claims(claims,source)[0]['text']=='**Code: 7440122**'


def test_decorated_individual_row_is_not_mistaken_for_group_scope():
    from app.modules.rag.evidence_verification import row_scope_entity
    claims=[{'references':[{'origin':'reviewed_fact','entity_name':'Alpha Program'}]}]
    individual=QueryPlan(query='Combinations?',entity='Major Alpha Program',enumeration_subject='admission combinations')
    assert row_scope_entity(individual,claims)=='Alpha Program'
    group=QueryPlan(query='Programs?',entity='Alpha programs',enumeration_subject='programs')
    assert row_scope_entity(group,claims)=='Alpha programs'


def test_same_spans_in_another_revision_never_inherit_record():
    from app.modules.rag.evidence_hierarchy import enrich_hierarchy
    source = handbook()
    other = source[-1].model_copy(update={'id': 'other', 'source_revision_id': 'other',
                                         'index_revision_id': 'other', 'record_label': None})
    assert enrich_hierarchy([*source, other])[-1].record_label is None


def test_fact_location_uses_row_page_not_last_document_section():
    from app.modules.rag.evidence_facts import fact_location
    source = split_source_blocks('<!-- Page 1 -->\n## Undergraduate\n\nAdmissions.\n\n'
        '<!-- Page 2 -->\n## Doctorate\n\nResearch.', binding_id='b', index_id='i', source_id='s', title='Official')
    section, _, locations = fact_location(source, 'i', {'page_number': 1})
    assert 'Undergraduate' in section and 'Doctorate' not in section
    assert locations
    assert fact_location(source, 'i', {}) == ('', '', [])


def test_mixed_source_passages_split_without_borrowing_scope():
    from app.modules.rag.evidence_claims import bind_claims
    from app.modules.rag.evidence_passages import (
        PassageClaim,
        PassageProposal,
        passage_catalog,
        resolve_proposal,
    )
    source = split_source_blocks('Alpha row.', binding_id='b', index_id='i', source_id='s', title='A')
    other = split_source_blocks('## Admissions 2025', binding_id='c', index_id='j', source_id='t', title='B')
    blocks = [*source, *other]
    catalog = passage_catalog(blocks)
    proposal = resolve_proposal(PassageProposal(status='supported', claims=[PassageClaim(
        id='claim', text='Label only', evidence_ids=['e1','e2'])]), catalog, blocks)
    claims, errors = bind_claims(proposal, blocks)
    assert not errors and len(claims) == 2
    assert all(len({ref['source_revision_id'] for ref in claim['references']}) == 1 for claim in claims)
    assert not any('2025' in ref['quote'] for ref in claims[0]['references'])


@pytest.mark.asyncio
async def test_wrong_record_cannot_pass_even_when_model_would_accept_it():
    from app.modules.rag.evidence_hierarchy import enrich_hierarchy
    from app.modules.rag.evidence_verification import verify_bound_answer
    from app.modules.rag.schemas import AskRequest
    source = enrich_hierarchy(handbook())
    wrong = next(b for b in source if b.text == 'Software engineering.')
    plan = QueryPlan(query='Alpha careers?', entity='ALPHA PROGRAM')
    claims = [{'id':'bad','text':wrong.text,'references':[{'block_id':wrong.id}]}]
    with patch('app.modules.rag.evidence_verification.structured_call', AsyncMock(side_effect=AssertionError('must not call'))) as model:
        result = await verify_bound_answer(None, AskRequest(question=plan.query,collection_id='c'), {}, claims, source, plan, [])
    assert not result.claims and not result.complete and result.errors
    model.assert_not_called()


@pytest.mark.asyncio
async def test_missing_topic_stays_partial_despite_numeric_audit_acceptance():
    from app.modules.rag.evidence_claims import bind_claims
    from app.modules.rag.evidence_indexed_audit import AuditedClaim, IndexedAudit
    from app.modules.rag.evidence_schemas import (
        AnswerProposal,
        ClaimVerdict,
        EvidenceClaim,
        QuoteReference,
        VerificationResult,
    )
    from app.modules.rag.evidence_verification import verify_bound_answer
    from app.modules.rag.schemas import AskRequest
    source = split_source_blocks('Duration: 4 years.', binding_id='b',index_id='i',source_id='s',title='A')
    claims,_ = bind_claims(AnswerProposal(status='supported',claims=[EvidenceClaim(id='c',text=source[0].text,
        references=[QuoteReference(block_id=source[0].id,quote=source[0].text)])]),source)
    plan = QueryPlan(query='Duration and careers?',requested_topics=['Duration','Careers'])
    verdict = VerificationResult(complete=True,topic_coverage={'Duration':True},verdicts=[ClaimVerdict(
        claim_id='c',entailed=True,relevant=True,scope_compatible=True,reason='Source')])
    audit = IndexedAudit(complete=True,claims=[AuditedClaim(claim_id='c',all_assertions_supported=True,reason='Source')])
    with patch('app.modules.rag.evidence_verification.structured_call',AsyncMock(side_effect=[verdict,audit])):
        result = await verify_bound_answer(None,AskRequest(question=plan.query,collection_id='c'),{},claims,source,plan,[])
    assert result.claims and not result.complete and 'Careers' in result.missing


@pytest.mark.asyncio
async def test_contract_repair_reports_length_constraint_without_truncating_evidence():
    from types import SimpleNamespace

    from pydantic import Field

    from app.modules.rag.evidence_model import structured_call
    from app.modules.rag.evidence_schemas import StrictContract
    from app.modules.rag.schemas import AskRequest
    class Label(StrictContract):
        label: str = Field(max_length=5)
    response = lambda content: SimpleNamespace(content=content,provider='custom',model='configured')
    model = AsyncMock(side_effect=[response('{"label":"too long label"}'), response('{"label":"Short"}')])
    with patch('app.modules.rag.evidence_model.modelops_service.generate',model):
        result = await structured_call(None,AskRequest(question='Q?',collection_id='c'),Label,'Instruction',{},max_tokens=100)
    assert result.label == 'Short'
    feedback = model.call_args_list[1].args[1].messages[-1].content
    assert 'string_too_long' in feedback and 'max_length' in feedback
    assert 'NEVER truncate' in feedback


@pytest.mark.asyncio
async def test_invalid_model_contract_stays_real_error_after_one_repair():
    from types import SimpleNamespace

    from pydantic import Field

    from app.core.exceptions import AppException
    from app.modules.rag.evidence_model import structured_call
    from app.modules.rag.evidence_schemas import StrictContract
    from app.modules.rag.schemas import AskRequest
    class Label(StrictContract):
        label: str = Field(max_length=5)
    model = AsyncMock(return_value=SimpleNamespace(content='{"label":"too long label"}',provider='custom',model='configured'))
    with patch('app.modules.rag.evidence_model.modelops_service.generate',model), pytest.raises(AppException) as error:
        await structured_call(None,AskRequest(question='Q?',collection_id='c'),Label,'Instruction',{},max_tokens=100)
    assert error.value.code == 'EVIDENCE_MODEL_CONTRACT_INVALID' and model.await_count == 2


@pytest.mark.asyncio
async def test_historical_failure_records_where_it_stopped_and_keeps_current_year():
    from app.core.evidence_policy import EvidencePolicy
    from app.modules.rag.evidence_historical import try_historical_reference
    from app.modules.rag.evidence_pipeline import decision_response
    from app.modules.rag.schemas import AskRequest, RetrievalSnapshot
    req=AskRequest(question='Alpha 2026?',collection_id='c')
    snapshot=RetrievalSnapshot(snapshot_id='snap',collection_id='c')
    plan=QueryPlan(query=req.question,years=[2026])
    original=decision_response(req,snapshot,'missing','reason',plan)
    progress={}
    with patch('app.modules.rag.evidence_historical.discover_reference_year',AsyncMock(return_value=2025)):
        result=await try_historical_reference(None,req,snapshot,EvidencePolicy(),original,0,False,
                                              progress,AsyncMock(return_value=[]),decision_response)
    assert result is original and result.answer_decision['requested']['years']==[2026]
    assert progress['historical_outcome']=='no_reference_evidence'
    assert progress['historical_reference_year']==2025 and progress['historical_reference_ms']>=0
