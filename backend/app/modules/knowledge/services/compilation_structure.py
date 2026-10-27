"""Read-only structural navigation over exact canonical units, never semantic approval."""
import re
from collections.abc import Iterator
from typing import Any

from app.modules.knowledge.normalization.retrieval_models import SourceUnit
from app.modules.knowledge.parsers.markdown_parser import _split_gfm_row
from app.modules.knowledge.services.source_artifact import get_source_artifact
from app.modules.knowledge.services.wiki_compiler import source_units

PROTOCOL = 'source-section-table-column-field-note/v1'
GUIDE = """\nstructural_evidence is navigation, NOT semantic verification. Read values with their section/table/header/column and field_notes.
section_candidates/header_candidates are hypotheses: verify against raw proofs or keep unresolved. A blank header never makes the first data row a header; retain all rows.
Cite headings/headers establishing metric, entity, year and scope. Never infer metric from topic or numeric appearance, or extend a field note to other rows/tables.
Position alone proves neither applicability nor document-wide absence. cell_columns names tuple positions; values stay in the original pipe-row quote (zero-based column_index). header_evidence_ids links shared column paths/candidates; declared layout is not a semantic verdict."""
OUTLINE = re.compile(r'^((?:[IVXLCDM]+|\d+(?:\.\d+)*|[a-zA-Z])[.)])\s+\S')


def _outline_level(unit: SourceUnit) -> int | None:
    if unit.kind != 'paragraph' or '\n' in unit.text or len(unit.text) > 240:
        return None
    match = OUTLINE.match(unit.text)
    if not match:
        return None
    label = match[1][:-1]
    if re.fullmatch('[IVXLCDM]+', label):
        return 1
    return 2 + label.count('.') if label[0].isdigit() else 10


def _section_links(units: list[SourceUnit], ids: dict[str, str]) -> dict[str, dict]:
    active, candidates, result = [], [], {}
    by_proof = {ids[u.id]:u for u in units if u.id in ids}
    for unit in sorted(units, key=lambda u: (u.start, -u.end, u.id)):
        if unit.is_container:
            continue
        pid = ids[unit.id]
        path = unit.heading_path
        if unit.kind == 'heading':
            depth = len(path) or len(unit.text)-len(unit.text.lstrip('#')) or 1
            active = [(d, p) for d, p in active if d < depth]
            active.append((depth, pid))
            candidates = []
        level = _outline_level(unit)
        if level is not None:
            candidates = [(d,p) for d,p in candidates if d < level]
            candidates.append((level,pid))
        declared = [p for _,p in active if p != pid]
        # A declared path disambiguates repeated headings; never search globally by label.
        if path:
            declared = [p for p in declared if by_proof[p].text.lstrip('# ').strip() in path]
        result[pid] = {'section_evidence_ids': declared,
                       'section_candidates': [{'evidence_id':p,'basis':'numbered_outline_candidate'}
                                              for _,p in candidates if p != pid]}
    return result


def structural_catalog(sources: list[Any], catalog: dict[str, dict]) -> dict[str, dict]:
    result = {}
    for source in sources:
        units = source_units(source)
        ids = {ref['unit_id']:pid for pid,ref in catalog.items() if ref['source_revision_id']==source.id}
        by_id = {u.id:u for u in units}
        sections = _section_links(units, ids)
        tables = {t['id']:t for t in get_source_artifact(source).get('tables', []) if isinstance(t,dict) and 'id' in t}
        for unit in units:
            if unit.id not in ids:
                continue
            pid = ids[unit.id]
            section = sections[pid]
            own = {'role':unit.kind, **{k:v for k,v in section.items() if v}}
            if unit.heading_path:
                own['declared_section_path'] = unit.heading_path
            if unit.parent_id in by_id and by_id[unit.parent_id].kind == 'heading':
                own.setdefault('section_evidence_ids',[])
                own['section_evidence_ids'] = list(dict.fromkeys([*own['section_evidence_ids'], ids[unit.parent_id]]))
            table = tables.get(unit.parent_id)
            if table:
                own.update(_table_context(unit, table, units, ids, by_id))
            if unit.context_refs:
                own['explicit_context_evidence_ids'] = [ids[uid] for uid in unit.context_refs if uid in ids]
            if unit.field_context_refs:
                own['field_notes'] = [{'column_id':key,'evidence_ids':[ids[uid] for uid in refs if uid in ids],
                                      'basis':'explicit_field_link'} for key,refs in unit.field_context_refs.items()]
            if len(own)>1 or unit.kind=='heading':
                result[pid] = own
    return result


def _table_context(unit: SourceUnit, table: dict, units: list[SourceUnit],
                   ids: dict[str, str], by_id: dict[str, SourceUnit]) -> dict:
    row_ids = table.get('row_unit_ids',[])
    table_id = unit.parent_id
    parent = by_id[table_id]
    emitted_header = '\n'.join(parent.text.splitlines()[:2])
    header_ids = [ids[u.id] for u in units if u.parent_id==table_id and u.start==parent.start
                  and u.text==emitted_header and u.id in ids]
    headers = table.get('headers') or []
    declared = (len(header_ids)==1 and any(str(h).strip() for h in headers)
                and _split_gfm_row(emitted_header.splitlines()[0])==headers)
    role = 'table_header' if ids[unit.id] in header_ids else ('table_row' if unit.id in row_ids else 'table_fragment_unresolved')
    info = {'role':role,
            'table_id':table_id, 'header_evidence_ids':header_ids,
            'header_status':'declared' if declared else 'unresolved',
            'header_paths':table.get('header_paths') or [[h] if h else [] for h in headers]}
    if not declared and row_ids and row_ids[0] in ids:
        info['header_candidates'] = [{'evidence_id':ids[row_ids[0]],'basis':'first_body_row_candidate_only'}]
    # Positional preamble is raw supporting context, not an automatically applicable condition.
    preceding = sorted((u for u in units if u.end <= parent.start),key=lambda u:u.end)
    info['table_preamble_evidence_ids'] = [ids[u.id] for u in preceding[-2:] if u.id in ids and u.kind!='table']
    if unit.id in row_ids:
        row = row_ids.index(unit.id)
        info['row_index'] = row
        info['row_locator_status'] = 'exact' if row_ids.count(unit.id)==1 else 'unresolved'
        fields = table.get('row_fields') or []
        raw_cells = _split_gfm_row(unit.text)
        row_fields = fields[row] if row<len(fields) else []
        info['cells'] = []
        for i,raw in enumerate(raw_cells):
            field = row_fields[i] if i<len(row_fields) and isinstance(row_fields[i],dict) else {}
            aligned = field.get('raw') == raw
            info['cells'].append({'column_index':i,'column_id':field.get('column_id',str(i)),
                'raw':raw, 'state':field.get('state','ambiguous') if aligned else 'ambiguous',
                'field_alignment':'exact' if aligned else 'unresolved',
                'header_path':field.get('header_path') or (info['header_paths'][i] if i<len(info['header_paths']) else [])})
    return info


def decorate(catalog: dict[str, dict], structure: dict[str, dict]) -> dict[str, dict]:
    return {pid:{**ref, **({'structural_evidence':structure[pid]} if pid in structure else {})}
            for pid,ref in catalog.items()}


def compact_structure(node: dict) -> dict:
    """Lossless positional cells; table-wide metadata is emitted once on its header proof."""
    result = dict(node)
    if node.get('role')=='table_row' and len(node.get('header_evidence_ids',[]))==1:
        for key in ('header_paths','header_candidates','table_preamble_evidence_ids'):
            result.pop(key,None)
    if 'cells' in node:
        columns = ['column_index','column_id','state','field_alignment']
        if 'header_paths' in result:
            columns.append('header_path')
        result['cell_columns'] = columns
        result['cells'] = [[cell[key] for key in columns] for cell in node['cells']]
        overrides = [{'column_index':cell['column_index'],'header_path':cell['header_path']}
                     for cell in node['cells'] if cell['column_index']<len(node.get('header_paths',[]))
                     and cell['header_path']!=node['header_paths'][cell['column_index']]]
        if overrides:
            result['cell_header_path_overrides'] = overrides
    return result


def navigation_refs(value: Any) -> Iterator[str]:
    if isinstance(value,dict):
        for key,item in value.items():
            if key=='evidence_id' and isinstance(item,str):
                yield item
            elif key.endswith('evidence_ids') and isinstance(item,list):
                yield from item
            else:
                yield from navigation_refs(item)
    elif isinstance(value,list):
        for item in value:
            yield from navigation_refs(item)


def offered_refs(primary: list[str] | set[str], catalog: dict[str, dict],
                 context: dict[str, list[str]] | None = None, *, include_native: bool = False) -> list[str]:
    refs, pending = set(primary), list(primary)
    while pending:
        pid = pending.pop()
        linked = [*(context or {}).get(pid,[]), *navigation_refs(catalog[pid].get('structural_evidence',{}))]
        native=catalog[pid].get('compiler_native_context',{}) if include_native else {}
        linked.extend(native.get('body_evidence_ids',[]))
        if native.get('candidate_evidence_id'):
            linked.append(native['candidate_evidence_id'])
        for ref in linked:
            if ref not in catalog or catalog[ref]['source_revision_id']!=catalog[pid]['source_revision_id']:
                raise ValueError('Structural evidence crosses a source or has no canonical proof')
            if ref not in refs:
                refs.add(ref)
                pending.append(ref)
    return sorted(refs)
