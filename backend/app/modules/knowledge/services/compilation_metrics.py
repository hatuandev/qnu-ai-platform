"""Bind table scalars to literal metric/column labels, not the requested topic."""
from app.modules.knowledge.parsers.markdown_parser import _split_gfm_row

PROTOCOL = 'literal-table-metric-and-column/v1'
GUIDE = """\nNumeric table assertions: use metric_binding_targets as navigation, not verification.
Bind scope source_metric to a literal population/event phrase in metric_context (or descriptive column candidate); source_column to that cell's leaf header. Cite each phrase's own evidence_id in scope AND assertion, plus metric refs in entity; a numeric row cannot prove header/preamble words absent there.
entity.label MUST equal source_metric.value; attribute MUST equal source_column.value, verbatim. Never rename a metric to match the topic: actual results are not planned targets.
Copy one unique cell value exactly. Unreviewed candidate headers remain unresolved. A verified column-role review requires a native grid match and two blind witnesses; it is compiler interpretation, not a change to the source or author-declared header. Preserve qualifiers and unknown/null.
Synthesis text must retain source_metric, source_column and value verbatim; do not introduce another metric role. Literal bindings do not certify entailment or approval."""
GUIDE += """\nA source_table_context is the verbatim frame/caption introducing a table, not the metric/unit shared by all its columns. Verify its local association separately; source_metric/source_column identify the selected field. Different measures can coexist under one table frame."""


def numeric_table_rows(assertion: dict, evidence: dict) -> list[str]:
    value = assertion.get('value')
    if assertion.get('value_state') != 'present' or not isinstance(value, str):
        return []
    if not any(c.isdigit() for c in value):
        return []
    return [pid for pid in assertion['evidence_ids']
            if evidence[pid].get('structural_evidence', {}).get('role') == 'table_row']


def _scope(assertion: dict, dimension: str) -> dict | None:
    values = [s for s in assertion.get('scope', []) if s['dimension'] == dimension]
    return values[0] if len(values) == 1 else None


def binding_targets(primary: list[str], evidence: dict) -> list[dict]:
    targets = []
    for pid in primary:
        node = evidence[pid].get('structural_evidence', {})
        if node.get('role') != 'table_row':
            continue
        headers = [p for p in node.get('header_evidence_ids', []) if p in evidence]
        related = [node, *(evidence[p].get('structural_evidence', {}) for p in headers)]
        preamble = list(dict.fromkeys(p for h in related for p in h.get('table_preamble_evidence_ids', [])))
        candidates = list(dict.fromkeys([*headers, *(c['evidence_id'] for h in related for c in h.get('header_candidates', []))]))
        columns = []
        for index, value in enumerate(_split_gfm_row(evidence[pid]['quote'])):
            if not value or not any(c.isdigit() for c in value):
                continue
            labels = []
            for ref in candidates:
                if ref not in evidence:
                    continue
                cells = _split_gfm_row(evidence[ref]['quote'].splitlines()[0])
                if index < len(cells) and cells[index]:
                    labels.append({'evidence_id': ref, 'value': cells[index]})
            columns.append({'column_index': index, 'value': value, 'column_candidates': labels})
        if columns:
            targets.append({'evidence_id': pid, 'header_status': node.get('header_status', 'unresolved'),
                'metric_context': [{'evidence_id': ref, **({'quote': evidence[ref]['quote']}
                    if len(evidence[ref]['quote']) <= 200 else {})} for ref in preamble if ref in evidence],
                'cells': columns})
    return targets


def _literal(scope: dict, allowed: set[str], evidence: dict) -> bool:
    refs = scope['evidence_ids']
    return bool(refs) and set(refs) <= allowed and all(scope['value'] in evidence[p]['quote'] for p in refs)


def _row_binding(assertion: dict, pid: str, metric: dict, column: dict, evidence: dict, column_roles=None) -> str | None:
    node = evidence[pid]['structural_evidence']
    headers = set(node.get('header_evidence_ids', []))
    header_nodes = [evidence[p].get('structural_evidence', {}) for p in headers if p in evidence]
    preamble = set(node.get('table_preamble_evidence_ids', []))
    preamble.update(p for h in header_nodes for p in h.get('table_preamble_evidence_ids', []))
    candidates = {c['evidence_id'] for h in [node, *header_nodes] for c in h.get('header_candidates', [])}
    local = {p for p in headers | preamble | candidates if p in evidence
             and evidence[p]['source_revision_id'] == evidence[pid]['source_revision_id']}
    if not _literal(metric, local, evidence) or not _literal(column, local & (headers | candidates), evidence):
        return 'metric_label_outside_table_context'
    cells = _split_gfm_row(evidence[pid]['quote'])
    matches = [i for i, value in enumerate(cells) if value == assertion['value']]
    if len(matches) != 1:
        return 'metric_value_without_unique_cell'
    index = matches[0]
    paths = node.get('header_paths') or next((h['header_paths'] for h in header_nodes if h.get('header_paths')), [])
    overrides = {c['column_index']: c['header_path'] for c in node.get('cells', []) if isinstance(c, dict)}
    overrides.update({c['column_index']: c['header_path'] for c in node.get('cell_header_path_overrides', [])})
    path = overrides.get(index, paths[index] if index < len(paths) else [])
    if node.get('header_status') != 'declared' and column_roles:
        reviewed = [column_roles[p] for p in column['evidence_ids'] if p in column_roles and p in candidates]
        if len(reviewed)==1 and index<len(reviewed[0]):
            path = [reviewed[0][index]]
            if column['value']==path[-1]:
                return None
    if node.get('header_status') != 'declared' or not path:
        return 'metric_column_role_unresolved'
    if column['value'] != path[-1]:
        return 'metric_column_does_not_match_value_cell'
    return None


def metric_guards(draft: dict, evidence: dict, column_roles=None) -> list[dict]:
    entities = {e['id']: e for e in draft.get('entities', [])}
    issues = []
    for assertion in draft['assertions']:
        rows = numeric_table_rows(assertion, evidence)
        if not rows:
            continue
        metric, column = _scope(assertion, 'source_metric'), _scope(assertion, 'source_column')
        reason = None
        if metric is None or column is None:
            reason = 'metric_binding_missing_or_ambiguous'
        elif not set(metric['evidence_ids'] + column['evidence_ids']) <= set(assertion['evidence_ids']):
            reason = 'metric_binding_not_cited'
        elif column_roles is None and not set(metric['evidence_ids']) <= set(entities.get(assertion['entity_id'], {}).get('evidence_ids', [])):
            reason = 'metric_entity_binding_not_cited'
        elif assertion['attribute'] != column['value'] or (column_roles is None
                and entities.get(assertion['entity_id'], {}).get('label') != metric['value']):
            reason = 'metric_label_changed_from_source'
        else:
            owners = [pid for pid in rows if assertion['value'] in _split_gfm_row(evidence[pid]['quote'])]
            reason = (_row_binding(assertion, owners[0], metric, column, evidence, column_roles) if len(owners) == 1
                      else 'metric_value_without_unique_row')
            if column_roles is not None:
                subject = _scope(assertion, 'source_subject')
                entity = entities.get(assertion['entity_id'], {})
                if (subject is None or entity.get('label')!=subject['value']
                        or not set(subject['evidence_ids'])<=set(entity.get('evidence_ids', []))
                        or not _literal(subject, set(owners), evidence)):
                    reason = 'metric_subject_without_literal_row_binding'
        if reason:
            issues.append({'id': assertion['id'], 'path': 'source_metric', 'reason': reason})
    return issues


def section_metric_guards(draft: dict, synthesis: dict) -> list[dict]:
    assertions = {a['id']: a for a in draft['assertions']}
    issues = []
    for index, section in enumerate(synthesis['sections']):
        for aid in section['assertion_ids']:
            assertion = assertions[aid]
            metric, column = _scope(assertion, 'source_metric'), _scope(assertion, 'source_column')
            if metric and column and any(value not in section['text']
                                         for value in (metric['value'], column['value'], assertion['value'] or '')):
                issues.append({'index': index, 'reason': 'metric_source_role_dropped_in_synthesis'})
                break
    return issues
