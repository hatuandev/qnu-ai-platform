"""Lossless group inventories with global integrity independent of request capacity."""
from collections import Counter

from app.modules.knowledge.compilation_schemas import CompilationDraft, CompilationManifest
from app.modules.knowledge.services.compilation_catalog import invalid
from app.modules.knowledge.services.wiki_compiler import digest


def inventory(payload: dict, maximum: int) -> dict:
    count = sum(len(payload.get(name, [])) for name in ('entities', 'assertions', 'relations', 'sections'))
    if count > maximum:
        raise capacity('manifest', count=count, limit=maximum)
    legacy = all(len(payload.get(name, [])) <= limit for name, limit in
                 (('entities', 64), ('assertions', 128), ('relations', 128), ('sections', 64)))
    contract = CompilationDraft if legacy and payload.get('version') != 'qnu-knowledge-compilation/v2' else CompilationManifest
    return contract.model_validate({**payload, **({'version': 'qnu-knowledge-compilation/v2'}
                                                 if contract is CompilationManifest else {})}).model_dump(mode='json')


def capacity(stage: str, **details):
    from app.core.exceptions import AppException

    return AppException('Nhóm dữ liệu vượt dung lượng xử lý; chưa gửi request tiếp theo.',
        code='KNOWLEDGE_COMPILATION_CAPACITY', status_code=422,
        details={'stage': stage, **details, 'automatic_retry': False})


def group_descriptor(payload: dict, synthesis: dict, offset: int, catalog: dict) -> dict:
    draft = payload['draft']
    group = {'source_revision_ids': sorted({catalog[p]['source_revision_id']
        for a in draft['assertions'] for p in a['evidence_ids']}),
        'entity_ids': [e['id'] for e in draft['entities']],
        'assertion_ids': [a['id'] for a in draft['assertions']],
        'relation_ids': [r['id'] for r in synthesis['relations']],
        'section_indices': list(range(offset, offset + len(synthesis['sections'])))}
    return {'id': 'group_' + digest([draft['snapshot_hash'], group])[:24], **group}


def validate_groups(proposal: dict, catalog: dict) -> None:
    if proposal.get('version') != 'qnu-knowledge-compilation/v2':
        return
    groups = proposal['groups']
    assertions = {a['id']: a for a in proposal['assertions']}
    entities = {e['id']: e for e in proposal['entities']}
    relations = {r['id']: r for r in proposal['relations']}
    sections = proposal['sections']
    if not groups or len({g['id'] for g in groups}) != len(groups):
        raise invalid('manifest_groups_missing_or_duplicate', 422)
    seen_sections, seen_relations, seen_assertions = [], [], []
    for group in groups:
        body = {k: v for k, v in group.items() if k != 'id'}
        if group['id'] != 'group_' + digest([proposal['snapshot_hash'], body])[:24]:
            raise invalid('manifest_group_hash', 422)
        aids, eids, rids, indices = (group[name] for name in
            ('assertion_ids', 'entity_ids', 'relation_ids', 'section_indices'))
        if any(len(values) != len(set(values)) for values in (aids, eids, rids, indices)):
            raise invalid('manifest_duplicate_members', 422)
        if not set(aids) <= assertions.keys() or not set(eids) <= entities.keys() or not set(rids) <= relations.keys():
            raise invalid('manifest_foreign_members', 422)
        if any(i < 0 or i >= len(sections) for i in indices):
            raise invalid('manifest_section_index', 422)
        sources = {catalog[p]['source_revision_id'] for aid in aids for p in assertions[aid]['evidence_ids']}
        if set(group['source_revision_ids']) != sources or not {assertions[a]['entity_id'] for a in aids} <= set(eids):
            raise invalid('manifest_source_or_entity_binding', 422)
        if any(not set(sections[i]['assertion_ids']) <= set(aids) for i in indices):
            raise invalid('manifest_section_membership', 422)
        if any(not {relations[r]['source_id'], relations[r]['target_id']} <= set(aids) | set(eids) for r in rids):
            raise invalid('manifest_relation_membership', 422)
        seen_sections.extend(indices)
        seen_relations.extend(rids)
        seen_assertions.extend(aids)
    if (set(seen_assertions) != set(assertions)
            or Counter(seen_sections) != Counter(range(len(sections)))
            or Counter(seen_relations) != Counter(list(relations))):
        raise invalid('manifest_incomplete_coverage', 422)
