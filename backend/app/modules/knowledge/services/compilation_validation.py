"""Exact binding and complete independent review ledgers before any human decision."""
import html
import re

from app.modules.knowledge.compilation_runtime_schemas import (
    PacketCheck,
    RelationDirections,
    SynthesisCheck,
)
from app.modules.knowledge.services.compilation_catalog import invalid
from app.modules.knowledge.services.compilation_semantics import (
    assertion_guards,
    check_directions,
    section_guards,
)
from app.modules.knowledge.services.wiki_compiler import digest


def check_packet(draft: dict, review: PacketCheck, primary: list[str], offered: dict) -> dict:
    assertions = draft['assertions']
    ids = [item['id'] for item in assertions]
    checks = [item.id for item in review.items]
    if len(set(checks)) != len(checks) or set(checks) != set(ids):
        raise invalid('incomplete_item_review', 422)
    used = {ref for item in assertions for ref in item['evidence_ids']}
    deferred = draft['deferred_evidence_ids']
    if (len(deferred) != len(set(deferred)) or not set(deferred) <= set(primary)
            or set(primary) - used - set(deferred) or set(deferred) & used):
        raise invalid('packet_coverage', 422)
    if not set(review.missed_evidence_ids) <= set(offered):
        raise invalid('unknown_review_evidence', 422)
    for item, checked in zip(sorted(assertions, key=lambda x: x['id']), sorted(review.items, key=lambda x: x.id), strict=True):
        if not set(item['evidence_ids']) <= set(checked.evidence_ids) <= set(offered):
            raise invalid('review_not_bound_to_item', 422)
    issues = assertion_guards(assertions, offered, draft.get('entities', []))
    return {'items': [item.model_dump() for item in review.items],
        'missed_evidence_ids': review.missed_evidence_ids,
        **({'mechanical_issues': issues} if issues else {}),
        'complete': not issues and not review.missed_evidence_ids and all(supported(item.model_dump()) for item in review.items)}


def supported(check: dict) -> bool:
    return check['verdict'] == 'supported' and all(check[key] for key in
        ('entity_scope', 'temporal_roles', 'conditions_complete'))


def check_synthesis(draft: dict, synthesis: dict, review: SynthesisCheck, catalog: dict) -> dict:
    relations = {item['id']: item for item in synthesis['relations']}
    relation_ids = [item.id for item in review.relations]
    if len(relation_ids) != len(set(relation_ids)) or set(relation_ids) != set(relations):
        raise invalid('incomplete_relation_review', 422)
    for item in review.relations:
        if not set(relations[item.id]['evidence_ids']) <= set(item.evidence_ids) <= set(catalog):
            raise invalid('relation_review_proof', 422)
    indices = [item.index for item in review.sections]
    if len(indices) != len(set(indices)) or set(indices) != set(range(len(synthesis['sections']))):
        raise invalid('incomplete_section_review', 422)
    covered = set()
    for item in review.sections:
        refs = synthesis['sections'][item.index]['assertion_ids']
        if set(item.assertion_ids) != set(refs) or len(item.assertion_ids) != len(set(item.assertion_ids)):
            raise invalid('section_review_proof', 422)
        covered.update(refs)
    if covered != {item['id'] for item in draft['assertions']}:
        raise invalid('synthesis_dropped_assertion', 422)
    issues = section_guards(draft, synthesis, catalog)
    return {'relations': [item.model_dump() for item in review.relations],
        'sections': [item.model_dump() for item in review.sections],
        **({'mechanical_issues': issues} if issues else {}),
        'complete': not issues and all(supported(item.model_dump()) for item in review.relations)
            and all(item.verdict == 'supported' for item in review.sections)}


def dependencies(proposal: dict, catalog: dict, context: dict) -> dict:
    reverse = {pid: {'assertions': [], 'relations': [], 'sections': []} for pid in catalog}
    assertions = {item['id']: item for item in proposal['assertions']}
    for category in ('assertions', 'relations'):
        for item in proposal[category]:
            refs = set(item['evidence_ids'] + item['condition_ids'] + item['exception_ids'])
            refs.update(pid for pid in list(refs) for pid in context.get(pid, []))
            for pid in refs:
                reverse[pid][category].append(item['id'])
    for index, section in enumerate(proposal['sections']):
        refs = {pid for aid in section['assertion_ids'] for pid in assertions[aid]['evidence_ids']}
        refs.update(pid for pid in list(refs) for pid in context.get(pid, []))
        for pid in refs:
            reverse[pid]['sections'].append(index)
    return reverse


def escaped(value: str) -> str:
    return re.sub(r'([\\`*{}\[\]()#+.!_|>~-])', r'\\\1', html.escape(value))


def render(proposal: dict, catalog: dict, topic: str) -> str:
    lines = ['# ' + escaped(topic), '', '> Bản biên soạn thử nghiệm; chưa xuất bản.', '']
    by_id = {item['id']: item for item in proposal['assertions']}
    for section in proposal['sections']:
        lines.extend(['## ' + escaped(section['heading']), '', escaped(section['text']), ''])
        for aid in section['assertion_ids']:
            item = by_id[aid]
            years = ', '.join(scope['role'] + ':' + '/'.join(map(str, scope['years'])) for scope in item['temporal'])
            lines.extend([f"- {escaped(aid)} — {escaped(item['value_state'])}; {escaped(years)}"])
            for pid in dict.fromkeys(item['evidence_ids'] + item['condition_ids'] + item['exception_ids']):
                ref = catalog[pid]
                lines.extend(['', '> ' + escaped(ref['quote']).replace('\n', '\n> '),
                    f"\n  Nguồn: {escaped(ref['source_revision_id'])}; {ref['start']}:{ref['end']}; {escaped(pid)}", ''])
    return '\n'.join(lines).strip() + '\n'


def validate_result(bundle: dict, sources: list, collection_id: str, actor=None) -> None:
    from app.modules.knowledge.services.compilation_contracts import _bind_draft

    if bundle.get('compiler') != 'qnu-topic-compiler/v1' or bundle.get('policy_version') not in {
            'qnu-compilation-review/v1', 'qnu-compilation-review/v2', 'qnu-compilation-review/v3'}:
        raise invalid('compiler_policy_version')
    if _bind_draft(bundle['binding']['proposal'], sources, collection_id) != bundle['binding']:
        raise invalid('binding_drift')
    if bundle['markdown'] != render(bundle['binding']['proposal'], bundle['binding']['evidence'], bundle['topic']):
        raise invalid('render_drift')
    if bundle['sha256'] != digest({k: v for k, v in bundle.items() if k != 'sha256'}):
        raise invalid('bundle_hash')
    if bundle['policy_version'] in {'qnu-compilation-review/v2', 'qnu-compilation-review/v3'}:
        validate_machine_verdict(bundle)


def validate_machine_verdict(bundle: dict) -> None:
    """Do not trust a persisted machine_complete flag over the versioned review ledgers."""
    catalog, proposal = bundle['binding']['evidence'], bundle['binding']['proposal']
    ready = True
    for packet in bundle['packet_results']:
        review = packet['review']
        check = check_packet(packet['draft'], PacketCheck(items=review['items'],
            missed_evidence_ids=review['missed_evidence_ids']), packet['primary_evidence_ids'], catalog)
        if check != review:
            raise invalid('packet_review_drift')
        ready = ready and check['complete']
    review = bundle['synthesis_review']
    check = check_synthesis(proposal, proposal, SynthesisCheck(relations=review['relations'], sections=review['sections']), catalog)
    if check != review:
        raise invalid('synthesis_review_drift')
    directions = RelationDirections(items=[item for r in bundle['direction_reviews'] for item in r['items']])
    direction_check = check_directions(proposal, directions, catalog)
    if bundle['machine_complete'] != (ready and check['complete'] and direction_check['complete']):
        raise invalid('machine_verdict_drift')
