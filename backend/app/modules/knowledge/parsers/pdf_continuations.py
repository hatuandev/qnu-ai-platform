"""Source-bound continuation headers, without consuming unlabelled data rows."""
from copy import deepcopy
from itertools import pairwise

from app.modules.knowledge.parsers.pdf_tables import table_blocks


def _projection_cells(block, table) -> list[dict]:
    box = (block.source_data or {}).get('raw', {}).get('bbox')
    raw = table.source_data['table'].get('raw_native') or {}
    bounds = raw.get('bbox')
    if (not box or not bounds or not table.attributes.get('native_literal_coverage')
            or any(box[i] < bounds[i] - .1 for i in (0, 1))
            or any(box[i] > bounds[i] + .1 for i in (2, 3))):
        return []
    target = ''.join(block.body.split())
    paths, seen = {0: [[]]}, set()
    matrix = raw.get('glyph_matrix') or raw.get('matrix') or []
    for ri, row in enumerate(raw.get('cell_boxes', [])):
        for ci, cell in enumerate(row):
            if (not cell or tuple(cell) in seen
                    or min(box[2], cell[2]) <= max(box[0], cell[0])
                    or min(box[3], cell[3]) <= max(box[1], cell[1])):
                continue
            seen.add(tuple(cell))
            value = ''.join(str(matrix[ri][ci] or '').split())
            if not value:
                continue
            additions = {}
            for offset, candidates in list(paths.items()):
                if target.startswith(value, offset):
                    additions.setdefault(offset + len(value), []).extend(
                        [*path, {'row': ri, 'column': ci, 'bbox': cell}] for path in candidates)
            for offset, candidates in additions.items():
                paths[offset] = [*paths.get(offset, []), *candidates][:2]
    matches = paths.get(len(target), [])
    return matches[0] if target and len(matches) == 1 else []


def retain_native_projections(blocks: list) -> None:
    """Move proven duplicate projections into table provenance; raw layout stays saved."""
    tables = [b for b in blocks if b.type == 'table']
    for block in list(blocks):
        if block.type != 'text' or block.attributes.get('engine_used') != 'native':
            continue
        matches = [(table, _projection_cells(block, table)) for table in tables
                   if table.source_locations[0].page == block.source_locations[0].page]
        matches = [(table, cells) for table, cells in matches if cells]
        if len(matches) != 1:
            continue
        table, cells = matches[0]
        table.source_data.setdefault('native_text_projections', []).append({
            'source_locations': [loc.model_dump() for loc in block.source_locations],
            'raw': block.source_data['raw'], 'cells': cells, 'basis': 'unique_complete_cell_sequence_in_native_region'})
        blocks.remove(block)


def aligned_columns(previous, current) -> bool:
    def axes(table):
        raw = (table.source_data or {}).get('table', {}).get('raw_native', {})
        box = raw.get('bbox')
        cells = [c for row in raw.get('cell_boxes', []) for c in row if c]
        return [(x - box[0]) / (box[2] - box[0])
            for x in sorted({c[i] for c in cells for i in (0, 2)})] if box and box[2] > box[0] else []

    a, b = axes(previous), axes(current)
    return bool(a and len(a) == len(b) and all(abs(x - y) <= .005 for x, y in zip(a, b, strict=True)))


def _adjacent_fragments(previous, current, blocks) -> bool:
    a, b = previous.source_locations[0], current.source_locations[0]
    left, right = previous.attributes.get('comparison_bbox'), current.attributes.get('comparison_bbox')
    if (a.page is None or b.page != a.page + 1 or not left or not right
            or left[3] < 90 or right[1] > 15 or previous.section_path != current.section_path):
        return False
    if (abs(left[0] - right[0]) > 2 or abs(left[2] - right[2]) > 2
            or len(previous.attributes['columns']) != len(current.attributes['columns'])
            or not aligned_columns(previous, current)):
        return False
    between = blocks[blocks.index(previous) + 1:blocks.index(current)]
    return not any(b.type != 'table_row' and b.body.strip()
        and b.attributes.get('source_role') not in {'header', 'footer'} for b in between)


def _sequence_witness(previous, current, blocks) -> list[dict]:
    before = [b for b in blocks if b.parent_id == previous.id and b.type == 'table_row'][-2:]
    after = [b for b in blocks if b.parent_id == current.id and b.type == 'table_row'][:2]
    if len(before) != 2 or len(after) != 2:
        return []
    witness = []
    for row in [*before, *after]:
        key = next(iter(row.attributes['fields']))
        raw = row.attributes['fields'][key]['raw'].strip()
        # Canonical integer sequence only: leading-zero identifiers stay identifiers.
        if not raw.isascii() or not raw.isdecimal() or str(int(raw)) != raw:
            return []
        if key in row.attributes.get('field_origins', {}) or row.attributes.get('row_role'):
            return []
        witness.append({'block_id': row.id, 'column_id': key, 'raw': raw})
    return witness if all(int(b['raw']) == int(a['raw']) + 1 for a, b in pairwise(witness)) else []


def inherit_headers(blocks: list) -> None:
    tables = [b for b in blocks if b.type == 'table']
    for index in range(1, len(tables)):
        previous, current = tables[index - 1:index + 1]
        data = current.source_data['table']
        if (data.get('header_depth') or data.get('external_headers')
                or not all(c['header_path'] for c in previous.attributes['columns'])
                or any(b.attributes.get('engine_used') != 'native'
                       or not b.attributes.get('native_literal_coverage') for b in (previous, current))
                or not _adjacent_fragments(previous, current, blocks)):
            continue
        witness = _sequence_witness(previous, current, blocks)
        if not witness:
            continue
        inherited = {'block_id': previous.id, 'status': 'verified',
            'basis': 'adjacent_page_aligned_grid_contiguous_row_sequence',
            'columns': deepcopy(previous.attributes['columns']), 'sequence_witness': witness,
            'source_locations': [loc.model_dump() for loc in previous.source_locations]}
        # Rebuild the fields from their untouched cells; do not repair values or
        # change header_depth, as this fragment has no printed header to remove.
        derived = {**deepcopy(data), 'inherited_header': inherited}
        rows = [b for b in blocks if b.type == 'table_row' and b.parent_id == current.id]
        definitions = {entry['symbol']: entry for row in rows
                       for entry in row.attributes.get('symbol_definitions', {}).values()}
        emitted = table_blocks(derived, block_id=current.id, parent_id=current.parent_id,
            location=current.source_locations[0], section_path=current.section_path,
            engine='native', symbol_definitions=definitions)
        emitted[0].attributes['comparison_bbox'] = current.attributes['comparison_bbox']
        emitted[0].context_refs = list(dict.fromkeys([*current.context_refs, previous.id]))
        replaced = {'native_header_needs_review', 'table_header_unresolved'}
        emitted[0].quality_flags.extend(f for f in current.quality_flags
            if f.code not in replaced and f not in emitted[0].quality_flags)
        emitted[0].source_data = {**current.source_data, 'table': derived}
        first = blocks.index(current)
        blocks[first:first + len(rows) + 1] = emitted
        tables[index] = emitted[0]
