"""Deterministic semantic boundaries; literal anchors do not certify entailment."""
from app.modules.knowledge.services.compilation_catalog import invalid
from app.modules.rag.evidence_validation import YEAR

SYMMETRIC = {'same_entity', 'alias', 'contradicts'}
DIRECTION_RULES = {
    'supports': 'source provides support for target',
    'supersedes': 'source is the REPLACING/new assertion; target is the REPLACED/old assertion',
    'prerequisite': 'source is a prerequisite FOR target',
    'exception': 'source is an exception TO target',
}


def assertion_guards(assertions: list[dict], offered: dict, entities: list[dict] = ()) -> list[dict]:
    issues = []
    entity_refs = {entity['id']: entity['evidence_ids'] for entity in entities}
    for assertion in assertions:
        owner = {offered[pid]['source_revision_id'] for pid in assertion['evidence_ids']}
        if assertion['entity_id'] in entity_refs and {
                offered[pid]['source_revision_id'] for pid in entity_refs[assertion['entity_id']]} != owner:
            issues.append({'id': assertion['id'], 'path': 'entity_id', 'reason': 'entity_crosses_assertion_source'})
        for index, scope in enumerate(assertion.get('scope', [])):
            # No normalized label/dictionary may stand in for literal source evidence.
            if not any(scope['value'] in offered[pid]['quote'] for pid in scope['evidence_ids']):
                issues.append({'id': assertion['id'], 'path': f'scope/{index}/value',
                               'reason': 'scope_value_without_literal_anchor'})
    return issues


def section_guards(draft: dict, synthesis: dict, catalog: dict) -> list[dict]:
    assertions = {a['id']: a for a in draft['assertions']}
    issues = []
    for index, section in enumerate(synthesis['sections']):
        selected = [assertions[aid] for aid in section['assertion_ids']]
        sources = {catalog[pid]['source_revision_id'] for a in selected for pid in a['evidence_ids']}
        profiles = {tuple(sorted((t['role'], tuple(sorted(t['years']))) for t in a['temporal']
                                if t['role'] in {'data', 'effective'})) for a in selected}
        profiles.discard(())  # Source publication assertions need not invent a data year.
        years = {y for a in selected for t in a['temporal'] for y in t['years']}
        reasons = []
        if len(sources) != 1:
            reasons.append('section_crosses_sources')
        if len(profiles) > 1:
            reasons.append('section_crosses_temporal_scopes')
        if not {int(y) for y in YEAR.findall(section['heading'])} <= years:
            reasons.append('heading_year_outside_assertion_scope')
        issues.extend({'index': index, 'reason': reason} for reason in reasons)
    return issues


def direction_payload(draft: dict, synthesis: dict, evidence: dict) -> dict:
    """Blind reconstruction: offer unordered endpoint pairs, never proposed orientation."""
    return {'assertions': draft['assertions'], 'entities': draft.get('entities', []), 'evidence': evidence,
        'direction_rules': DIRECTION_RULES,
        'pairs': [{'id': r['id'], 'kind': r['kind'],
                   'endpoint_set': {aid: True for aid in sorted({r['source_id'], r['target_id']})}}
                  for r in synthesis['relations'] if r['kind'] not in SYMMETRIC]}


def check_directions(synthesis: dict, witness, catalog: dict) -> dict:
    directed = {r['id']: r for r in synthesis['relations'] if r['kind'] not in SYMMETRIC}
    items = {item.id: item.model_dump() for item in witness.items}
    if len(items) != len(witness.items) or set(items) != set(directed):
        raise invalid('incomplete_direction_review', 422)
    issues = []
    for rid, relation in directed.items():
        item = items[rid]
        if len(item['evidence_ids']) != len(set(item['evidence_ids'])) or not set(item['evidence_ids']) <= set(catalog):
            raise invalid('direction_review_proof', 422)
        if (item['verdict'] != 'supported' or not item['evidence_ids']
                or not set(relation.get('evidence_ids', [])) <= set(item['evidence_ids'])):
            issues.append({'id': rid, 'reason': 'direction_unresolved'})
        elif (item['source_id'], item['target_id']) != (relation['source_id'], relation['target_id']):
            issues.append({'id': rid, 'reason': 'direction_disagrees_with_blind_witness'})
        if relation['source_id'] == relation['target_id']:
            issues.append({'id': rid, 'reason': 'directed_self_relation'})
    return {'items': list(items.values()), 'issues': issues, 'complete': not issues}
