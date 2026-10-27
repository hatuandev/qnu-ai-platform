"""Exact binding and complete independent review ledgers before any human decision."""
import html
import re
from copy import deepcopy

from app.modules.knowledge.compilation_runtime_schemas import (
    ManifestDirections,
    ManifestSynthesisCheck,
    PacketCheck,
    RelationDirections,
    SynthesisCheck,
)
from app.modules.knowledge.services.compilation_catalog import invalid
from app.modules.knowledge.services.compilation_metrics import metric_guards, section_metric_guards
from app.modules.knowledge.services.compilation_semantics import (
    assertion_guards,
    check_directions,
    section_guards,
)
from app.modules.knowledge.services.wiki_compiler import digest


def check_packet(draft: dict, review: PacketCheck, primary: list[str], offered: dict, *, metric_bindings: bool = True, column_roles=None) -> dict:
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
    if metric_bindings:
        issues.extend(metric_guards(draft, offered, column_roles))
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
    issues.extend(section_metric_guards(draft, synthesis))
    from app.modules.knowledge.services.compilation_grounding import grounded_section_issues

    issues.extend(grounded_section_issues(draft,synthesis,catalog))
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
            'qnu-compilation-review/v1', 'qnu-compilation-review/v2', 'qnu-compilation-review/v3', 'qnu-compilation-review/v4', 'qnu-compilation-review/v5'}:
        raise invalid('compiler_policy_version')
    if bundle['policy_version'] == 'qnu-compilation-review/v4' and 'metric_protocol' not in bundle:
        raise invalid('metric_protocol_missing')
    if bundle['policy_version'] == 'qnu-compilation-review/v5':
        from app.modules.knowledge.services.compilation_columns import FIELD_PROTOCOL, native_tables
        from app.modules.knowledge.services.compilation_columns import PROTOCOL as COLUMN_PROTOCOL
        from app.modules.knowledge.services.compilation_grounding import (
            PROTOCOL as GROUNDING_PROTOCOL,
        )

        if (bundle.get('source_grounding_protocol')!=GROUNDING_PROTOCOL or bundle.get('column_role_protocol')!=COLUMN_PROTOCOL
                or bundle.get('table_field_protocol')!=FIELD_PROTOCOL):
            raise invalid('source_grounding_protocol_drift')
        if 'source_structure' not in bundle or 'metric_protocol' not in bundle or 'column_role_ledger' not in bundle:
            raise invalid('grounding_provenance_missing')
        if bundle.get('native_table_evidence')!=native_tables(sources,bundle['binding']['evidence'],bundle['source_structure']):
            raise invalid('native_table_evidence_drift')
        validate_topic_refinement(bundle)
    if _bind_draft(bundle['binding']['proposal'], sources, collection_id) != bundle['binding']:
        raise invalid('binding_drift')
    if 'structure_protocol' in bundle or 'source_structure' in bundle:
        from app.modules.knowledge.services.compilation_catalog import dependency_catalog
        from app.modules.knowledge.services.compilation_structure import (
            PROTOCOL,
            structural_catalog,
        )

        structure = structural_catalog(sources, bundle['binding']['evidence'])
        if bundle.get('structure_protocol') != PROTOCOL or bundle.get('source_structure') != structure:
            raise invalid('source_structure_drift')
        if bundle.get('source_context') != dependency_catalog(sources, bundle['binding']['evidence'], structure):
            raise invalid('source_context_drift')
    if 'metric_protocol' in bundle:
        from app.modules.knowledge.services.compilation_metrics import PROTOCOL as METRIC_PROTOCOL

        if bundle['metric_protocol'] != METRIC_PROTOCOL or 'source_structure' not in bundle:
            raise invalid('metric_protocol_drift')
    if bundle['markdown'] != render(bundle['binding']['proposal'], bundle['binding']['evidence'], bundle['topic']):
        raise invalid('render_drift')
    if bundle['sha256'] != digest({k: v for k, v in bundle.items() if k != 'sha256'}):
        raise invalid('bundle_hash')
    if bundle['policy_version'] in {'qnu-compilation-review/v2', 'qnu-compilation-review/v3', 'qnu-compilation-review/v4', 'qnu-compilation-review/v5'}:
        validate_machine_verdict(bundle)


def validate_topic_refinement(bundle: dict) -> None:
    from app.modules.knowledge.compilation_runtime_schemas import TopicSelection
    from app.modules.knowledge.services.compilation_columns import (
        header_coverage,
        header_support,
        table_records,
    )
    from app.modules.knowledge.services.compilation_engine import (
        TOPIC_REFINEMENT,
        refinement_exclusions,
        selected_ids,
    )

    selection = bundle.get('topic_selection', {})
    catalog = bundle['binding']['evidence']
    if selection.get('protocol') != TOPIC_REFINEMENT:
        raise invalid('topic_refinement_protocol')
    selected = set()
    for review in selection['reviews']:
        offered = {p:catalog[p] for p in review['offered']}
        first, second = (TopicSelection.model_validate(review[k]) for k in ('first','independent'))
        selected.update((selected_ids(first,offered)|selected_ids(second,offered))&set(review['primary_evidence_ids']))
    if selected != set(selection['before_refinement']):
        raise invalid('topic_initial_selection_drift')
    visited = set()
    for review in selection['refinements']:
        primary = set(review['primary_evidence_ids'])
        if visited & primary or not primary <= set(selection['before_refinement']):
            raise invalid('topic_refinement_partition')
        visited.update(primary)
        offered = {p:catalog[p] for p in review['offered']}
        first, second = (TopicSelection.model_validate(review[k]) for k in ('first','independent'))
        excluded = refinement_exclusions(first,second,list(primary),offered)
        if excluded != set(review['excluded']):
            raise invalid('topic_exclusion_drift')
        selected.difference_update(excluded)
    records=table_records(sorted(selected),bundle['column_role_ledger'],bundle['native_table_evidence'],catalog,bundle['source_structure'])
    support=header_support(sorted(selected),records,bundle['source_structure'])
    if selection.get('supporting_headers')!=header_coverage(support,bundle['binding']['proposal']['assertions']):
        raise invalid('header_context_coverage_drift')
    if (selection['refinements'] and visited != set(selection['before_refinement'])
            or selected != set(selection['selected'])
            or selected-set(support) != {p for packet in bundle['packet_results'] for p in packet['primary_evidence_ids']}):
        raise invalid('topic_refinement_coverage')


def validate_machine_verdict(bundle: dict) -> None:
    """Do not trust a persisted machine_complete flag over the versioned review ledgers."""
    catalog, proposal = bundle['binding']['evidence'], bundle['binding']['proposal']
    metric_bindings = 'metric_protocol' in bundle
    if metric_bindings:
        from app.modules.knowledge.services.compilation_structure import decorate

        catalog = decorate(catalog, bundle['source_structure'])
    ready = True
    for packet in bundle['packet_results']:
        review = packet['review']
        roles = None
        if bundle['policy_version']=='qnu-compilation-review/v5':
            from app.modules.knowledge.services.compilation_columns import validate_record_packet

            if any(bundle['column_role_ledger'].get(p)!=entry for p,entry in packet.get('column_role_reviews',{}).items()):
                raise invalid('packet_column_role_ledger_drift')
            validate_record_packet(packet,bundle['native_table_evidence'],catalog,bundle['source_structure'])
            validate_grounded_coverage(packet,catalog)
            validate_semantic_repair(packet,catalog,bundle)
        if bundle.get('native_table_evidence') or any(s['dimension']=='source_subject' for a in packet['draft']['assertions'] for s in a['scope']):
            from app.modules.knowledge.services.compilation_columns import verified_columns

            roles = verified_columns(packet.get('column_role_reviews', {}),bundle['native_table_evidence'],catalog)
        check = check_packet(packet['draft'], PacketCheck(items=review['items'],
            missed_evidence_ids=review['missed_evidence_ids']), packet['primary_evidence_ids'], catalog,
            metric_bindings=metric_bindings,column_roles=roles)
        if check != review:
            raise invalid('packet_review_drift')
        ready = ready and check['complete']
    review = bundle['synthesis_review']
    manifest = proposal['version'] == 'qnu-knowledge-compilation/v2'
    review_type = ManifestSynthesisCheck if manifest else SynthesisCheck
    check = check_synthesis(proposal, proposal, review_type(relations=review['relations'], sections=review['sections']), catalog)
    if check != review:
        raise invalid('synthesis_review_drift')
    direction_type = ManifestDirections if manifest else RelationDirections
    directions = direction_type(items=[item for r in bundle['direction_reviews'] for item in r['items']])
    direction_check = check_directions(proposal, directions, catalog)
    cross_complete = True
    if 'cross_source_review' in bundle:
        from app.modules.knowledge.services.compilation_cross_source import validate_cross_ledger

        cross_complete = validate_cross_ledger(proposal, catalog, bundle['cross_source_review'])
    headers_complete = all(v['assertion_ids'] for v in bundle.get('topic_selection',{}).get('supporting_headers',{}).values())
    if bundle['machine_complete'] != (ready and check['complete'] and direction_check['complete'] and cross_complete and headers_complete):
        raise invalid('machine_verdict_drift')


def validate_grounded_coverage(packet: dict, catalog: dict) -> None:
    from app.modules.knowledge.compilation_runtime_schemas import PacketCoverage
    from app.modules.knowledge.services.compilation_review import GROUNDING_AUDIT_PROTOCOL, grounded

    if not grounded(packet['draft']) and packet.get('coverage_review',{}).get('mode')!='empty_draft_all_primary_debt':
        return
    ledger=packet.get('coverage_review',{})
    if ledger.get('protocol')!=GROUNDING_AUDIT_PROTOCOL:
        raise invalid('grounded_coverage_review_missing')
    assertions={a['id']:a for a in packet['draft']['assertions']}
    ids=ledger['assertion_ids']
    initial=packet.get('coverage_reconciliation',{}).get('initial_review',packet['review'])
    initial_ids=[item['id'] for item in initial['items']]
    if (len(ids)!=len(set(ids)) or set(ids)!=set(initial_ids) or not set(ids)<=set(assertions)
            or digest([assertions[p] for p in ids])!=ledger['assertions_hash']):
        raise invalid('coverage_assertion_scope_drift')
    primary=ledger['primary_evidence_ids']
    offered=ledger['offered_evidence_ids']
    if (primary!=packet['primary_evidence_ids'] or len(offered)!=len(set(offered))
            or not set(primary)<=set(offered)<=set(catalog)):
        raise invalid('coverage_proof_scope_drift')
    missed=set()
    reviewed=[]
    for entry in ledger['reviews']:
        check=PacketCoverage.model_validate(entry['review'])
        if (entry['offered']!=offered or not set(entry['primary_evidence_ids'])<=set(primary)
                or not set(check.missed_evidence_ids)<=set(entry['offered'])):
            raise invalid('coverage_proof_scope_drift')
        reviewed.extend(entry['primary_evidence_ids'])
        missed.update(check.missed_evidence_ids)
    empty_debt=ledger.get('mode')=='empty_draft_all_primary_debt'
    if empty_debt:
        if ids or initial['items'] or ledger['reviews'] or set(ledger['missed_evidence_ids'])!=set(primary):
            raise invalid('empty_coverage_debt_drift')
        missed=set(primary)
    elif len(reviewed)!=len(set(reviewed)) or set(reviewed)!=set(primary):
        raise invalid('coverage_primary_partition_drift')
    expected=initial['missed_evidence_ids']
    if (not empty_debt and not ledger['reviews']) or missed!=set(ledger['missed_evidence_ids']) or missed!=set(expected):
        raise invalid('coverage_verdict_drift')
    repair=packet.get('coverage_reconciliation',{}).get('repair')
    if repair:
        validate_grounded_coverage(repair,catalog)
    repaired={a['id'] for a in repair['draft']['assertions']} if repair else set()
    if set(ids)&repaired or set(ids)|repaired!=set(assertions):
        raise invalid('coverage_assertion_scope_drift')


def before_coverage_reconciliation(packet: dict) -> dict:
    """Recover the semantic stage without ignoring or mutating coverage-added facts."""
    reconciliation=packet.get('coverage_reconciliation')
    if not reconciliation:
        return packet
    result=deepcopy({k:v for k,v in packet.items() if k not in {'sha256','coverage_reconciliation'}})
    repair=reconciliation.get('repair')
    if repair:
        for category in ('assertions','entities'):
            added=repair['draft'][category]
            if added:
                if result['draft'][category][-len(added):]!=added:
                    raise invalid('coverage_added_candidate_drift')
                result['draft'][category]=result['draft'][category][:-len(added)]
    original=reconciliation['initial_review']
    if ({a['id'] for a in result['draft']['assertions']}!={c['id'] for c in original['items']}
            or result['review']['items'][:len(original['items'])]!=original['items']):
        raise invalid('coverage_original_candidate_drift')
    result['review']=deepcopy(original)
    used={p for a in result['draft']['assertions'] for p in a['evidence_ids']}
    result['draft']['deferred_evidence_ids']=sorted(set(result['primary_evidence_ids'])-used)
    return result


def validate_semantic_repair(packet: dict, catalog: dict, bundle: dict) -> None:
    from app.modules.knowledge.services.compilation_candidate_repair import (
        LEGACY_PROTOCOL,
        PROTOCOL,
        assertion_signature,
        repeats_failed_assertion,
    )
    from app.modules.knowledge.services.compilation_columns import (
        validate_record_packet,
        verified_columns,
    )

    ledger=packet.get('semantic_repair')
    if not ledger:
        return
    packet=before_coverage_reconciliation(packet)
    if ledger.get('protocol') not in {PROTOCOL,LEGACY_PROTOCOL} or ledger.get('outcome') not in {'accepted','rejected','unchanged','not_run'}:
        raise invalid('semantic_repair_protocol_drift')
    initial=ledger.get('initial',packet)
    failed=any(not supported(item) for item in initial['review']['items']) or initial['review'].get('mechanical_issues')
    if initial['review']['complete'] or not failed:
        raise invalid('semantic_repair_without_failed_candidate')
    if ledger['outcome']=='not_run':
        if ledger['capacity']['status']!='NOT_RUN' or ledger['capacity']['budget']['fits']:
            raise invalid('semantic_repair_capacity_drift')
        return
    if ledger['outcome']=='accepted' and not packet['review']['complete']:
        raise invalid('semantic_repair_accepted_without_complete_review')
    if ledger['outcome']=='accepted' and repeats_failed_assertion(initial,packet):
        raise invalid('semantic_repair_repeated_failed_assertion')
    if 'selection' in ledger:
        from app.modules.knowledge.services.compilation_repair_selection import validate_selection

        validate_selection(packet,catalog,
            verified_columns(packet.get('column_role_reviews',{}),bundle['native_table_evidence'],catalog),assertion_signature)
    if ledger['outcome'] in {'rejected','unchanged'}:
        active={k:v for k,v in packet.items() if k not in {'sha256','semantic_repair'}}
        previous={k:v for k,v in initial.items() if k!='sha256'}
        unchanged=repeats_failed_assertion(initial,ledger['candidate'])
        if (active!=previous or (ledger['outcome']=='rejected' and ledger['candidate']['review']['complete'] and 'selection' not in ledger)
                or (ledger['outcome']=='unchanged')!=unchanged):
            raise invalid('semantic_repair_rejected_candidate_effective')
    for previous in [initial,*([ledger['candidate']] if 'candidate' in ledger else [])]:
        if previous['primary_evidence_ids']!=packet['primary_evidence_ids'] or 'semantic_repair' in previous:
            raise invalid('semantic_repair_scope_or_attempt_drift')
        validate_record_packet(previous,bundle['native_table_evidence'],catalog,bundle['source_structure'])
        validate_grounded_coverage(previous,catalog)
        roles=verified_columns(previous.get('column_role_reviews',{}),bundle['native_table_evidence'],catalog)
        review=previous['review']
        if check_packet(previous['draft'],PacketCheck(items=review['items'],missed_evidence_ids=review['missed_evidence_ids']),
                        previous['primary_evidence_ids'],catalog,column_roles=roles)!=review:
            raise invalid('semantic_repair_initial_review_drift')
