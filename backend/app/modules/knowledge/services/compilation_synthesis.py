"""Independently size synthesis reviews while retaining all raw group evidence."""
from app.modules.knowledge.compilation_runtime_schemas import SynthesisCheck
from app.modules.knowledge.services.compilation_catalog import invalid
from app.modules.knowledge.services.compilation_manifest import capacity
from app.modules.knowledge.services.compilation_transport import (
    planned_request_budget as request_budget,
)
from app.modules.knowledge.services.compilation_validation import check_synthesis


def review_envelope(payload: dict) -> dict:
    """Bound all section partitions using exact rendered facts and longest offered heading."""
    from app.modules.knowledge.services.compilation_grounding import heading_spans, source_statement
    from app.modules.knowledge.services.compilation_review import grounded

    if not grounded(payload['draft']):
        return {}
    headings=heading_spans(payload)
    if not headings:
        raise capacity('synthesis',reason='no_source_bound_heading')
    heading=max((s['literal'] for s in headings.values()),key=lambda s:len(s.encode('utf-8')))
    entities={e['id']:e for e in payload['draft']['entities']}
    sections=[{'heading':heading,'text':source_statement(a,entities,payload['evidence']),
               'assertion_ids':[a['id']]} for a in payload['draft']['assertions']]
    return {**{k:v for k,v in payload.items() if k!='topic'},'synthesis':{'sections':sections,'relations':[]}}


def review_fragment(payload: dict, synthesis: dict, section_ids: list[int], relation_ids: list[int]) -> dict:
    sections = [synthesis['sections'][i] for i in section_ids]
    relations = [synthesis['relations'][i] for i in relation_ids]
    aids = {aid for section in sections for aid in section['assertion_ids']}
    endpoints = {r[key] for r in relations for key in ('source_id', 'target_id')}
    assertions = [a for a in payload['draft']['assertions'] if a['id'] in aids | endpoints]
    eids = {a['entity_id'] for a in assertions} | endpoints
    draft = {**payload['draft'], 'assertions': assertions,
             'entities': [e for e in payload['draft']['entities'] if e['id'] in eids]}
    return {**payload, 'draft': draft, 'synthesis': {'sections': sections, 'relations': relations}}


async def review_group(payload: dict, synthesis: dict, bounded, instruction: str, transport) -> SynthesisCheck:
    from app.modules.knowledge.services.compilation_review import grounded

    if grounded(payload['draft']):
        payload={k:v for k,v in payload.items() if k!='topic'}
    whole = {**payload, 'synthesis': synthesis}
    if request_budget(SynthesisCheck, instruction, whole, transport)['fits']:
        return SynthesisCheck.model_validate(await bounded(SynthesisCheck, instruction, whole))
    units = [([i], []) for i in range(len(synthesis['sections']))]
    # A relation-only review carries an existing section as an anchor because
    # the existing review contract requires sections; a failed anchor is never ignored.
    units += [([0], [i]) for i in range(len(synthesis['relations']))]
    batches, sections, relations = [], [], []
    for sids, rids in units:
        proposed_s = list(dict.fromkeys([*sections, *sids]))
        proposed_r = list(dict.fromkeys([*relations, *rids]))
        candidate = review_fragment(payload, synthesis, proposed_s, proposed_r)
        if request_budget(SynthesisCheck, instruction, candidate, transport)['fits']:
            sections, relations = proposed_s, proposed_r
            continue
        if not sections:
            raise capacity('synthesis_review', reason='single_review_item_budget')
        batches.append((sections, relations))
        sections, relations = sids, rids
        if not request_budget(SynthesisCheck, instruction,
                review_fragment(payload, synthesis, sections, relations), transport)['fits']:
            raise capacity('synthesis_review', reason='single_review_item_budget')
    if sections:
        batches.append((sections, relations))
    section_checks, relation_checks = {}, {}
    for sids, rids in batches:
        fragment = review_fragment(payload, synthesis, sids, rids)
        result = SynthesisCheck.model_validate(await bounded(SynthesisCheck, instruction, fragment))
        section_aids = {aid for s in fragment['synthesis']['sections'] for aid in s['assertion_ids']}
        draft = {**fragment['draft'], 'assertions': [a for a in fragment['draft']['assertions'] if a['id'] in section_aids]}
        check_synthesis(draft, fragment['synthesis'], result, fragment['evidence'])
        for item in result.sections:
            value = {**item.model_dump(), 'index': sids[item.index]}
            old = section_checks.get(value['index'])
            if old and (old['verdict'] != 'supported' or value['verdict'] != 'supported'):
                raise invalid('repeated_section_review_unresolved', 422)
            section_checks[value['index']] = value
        for item in result.relations:
            if item.id in relation_checks:
                raise invalid('duplicate_relation_batch_review', 422)
            relation_checks[item.id] = item.model_dump()
    return SynthesisCheck(sections=sorted(section_checks.values(), key=lambda x: x['index']),
                          relations=list(relation_checks.values()))
