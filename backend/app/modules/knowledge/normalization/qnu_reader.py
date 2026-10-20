"""Deterministic human view of a verified QNU document; never a serving input."""
import hashlib
import re
import textwrap
from collections import defaultdict
from typing import Any

from app.modules.knowledge.normalization.qnu_markdown import (
    QnuBlock,
    QnuStructuredDocument,
    parse_qnu_gfm_table,
)

READER_VERSION = 'qnu-reader/v1'


def anchor(value: str) -> str:
    return 'qnu-' + hashlib.sha256(value.encode()).hexdigest()[:20]


def _literal(value: str) -> str:
    return re.sub(r'([\\`*_{}\[\]<>|])', r'\\\1', value).replace('\r\n', '\n').replace('\n', ' / ')


def _note_text(body: str) -> str:
    # OOXML note tabs separate the reference glyph and body. Raw QnuBlock stays intact.
    return '\n\n'.join(textwrap.dedent(part.expandtabs(4)).strip('\n') for part in body.split('\n\n'))


def _table(block: QnuBlock, children: list[QnuBlock]) -> dict[str, Any]:
    columns = block.attributes.get('columns', [])
    headers = [' / '.join(c['header_path']) for c in columns]
    if block.attributes.get('representation') == 'records':
        rows = [[r.attributes['fields'][c['id']]['raw'] for c in columns] for r in children]
    else:
        _, rows = parse_qnu_gfm_table(block.body)
    layout = _source_layout(block.source_data or {})
    if layout and not _matches_layout(layout, rows, len(headers)):
        layout = None
    return {'headers': headers, 'column_ids': [c['id'] for c in columns], 'rows': rows,
            'row_ids': [r.id for r in children] or [f'{block.id}:row:{i}' for i in range(len(rows))], 'layout': layout}


def _source_layout(data: dict) -> dict | None:
    cells = data.get('cells')
    depth = data.get('header_rows', 0)
    if cells and data.get('num_rows') and data.get('num_cols'):
        return {'rows': data['num_rows'], 'columns': data['num_cols'], 'header_rows': depth,
            'cells': [{k: cell[k] for k in ('text', 'row_start', 'row_end', 'col_start', 'col_end')} for cell in cells]}
    elif data.get('grid'):
        grid, drawn, positions = data['grid'], [], defaultdict(list)
        depth = data.get('header_depth', 0)
        for ri, row in enumerate(grid):
            for ci, cell in enumerate(row):
                positions[tuple(cell['origin'])].append((ri, ci))
        for places in positions.values():
            rs, cs = zip(*places, strict=True)
            if len(places) != (max(rs) - min(rs) + 1) * (max(cs) - min(cs) + 1):
                return None
            drawn.append({'text': grid[min(rs)][min(cs)]['raw'], 'row_start': min(rs), 'row_end': max(rs) + 1,
                          'col_start': min(cs), 'col_end': max(cs) + 1})
        return {'rows': len(grid), 'columns': len(grid[0]), 'header_rows': depth, 'cells': drawn}
    return None


def _matches_layout(layout: dict, rows: list[list[str]], columns: int) -> bool:
    depth = layout['header_rows']
    if layout['rows'] != depth + len(rows) or layout['columns'] != columns or depth < 0:
        return False
    grid = [[None] * columns for _ in range(layout['rows'])]
    for cell in layout['cells']:
        r0, r1, c0, c1 = (cell[k] for k in ('row_start', 'row_end', 'col_start', 'col_end'))
        if not (0 <= r0 < r1 <= len(grid) and 0 <= c0 < c1 <= columns):
            return False
        for ri in range(r0, r1):
            for ci in range(c0, c1):
                if grid[ri][ci] is not None:
                    return False
                grid[ri][ci] = cell['text']
    return all(all(v is not None for v in row) for row in grid) and grid[depth:] == rows


def _note_catalog(document: QnuStructuredDocument) -> list[dict]:
    by_id = {b.id: b for b in document.blocks}
    notes = []
    for block in document.blocks:
        if block.type != 'note' or block.attributes.get('role') not in {'footnote', 'endnote'}:
            continue
        anchors = []
        for index, source in enumerate(block.attributes.get('source_anchors', [])):
            target = by_id.get(source['block_id'])
            if target is not None:
                anchors.append({**source, 'label': str(len(notes) + 1), 'id': anchor(f'{block.id}:{index}'), 'target_id': anchor(block.id),
                                'block_anchor': anchor(target.parent_id if target.type == 'table_row' else target.id)})
        notes.append({'id': block.id, 'anchor': anchor(block.id), 'label': str(len(notes) + 1),
            'markdown': _note_text(block.body), 'anchors': anchors, 'source_locations': [l.model_dump() for l in block.source_locations],
            'unresolved': bool(block.quality_flags)})
    return notes


def reader_document(document: QnuStructuredDocument) -> dict[str, Any]:
    """One derivation powers download and preview. Source values and IDs are unchanged."""
    notes, blocks, parts = _note_catalog(document), [], []
    note_ids = {n['id'] for n in notes}
    for block in document.blocks:
        if block.type in {'table_row', 'derived_index'} or block.id in note_ids:
            continue
        refs = [{**a, 'label': note['label'], 'note_id': note['id']} for note in notes for a in note['anchors'] if a['block_id'] == block.id]
        item = {'id': block.id, 'anchor': anchor(block.id), 'type': block.type,
                'markdown': block.body, 'references': [r for r in refs if not (block.type == 'table' and r.get('table'))],
                'source_locations': [l.model_dump() for l in block.source_locations]}
        export = block.body
        if block.type == 'table':
            children = [r for r in document.blocks if r.parent_id == block.id and r.type == 'table_row']
            table = _table(block, children)
            table['references'] = [{**a, 'label': n['label'], 'note_id': n['id']} for n in notes for a in n['anchors']
                                   if a['block_id'] in table['row_ids'] or a['block_id'] == block.id]
            item['table'] = table
            headers = [_literal(h) or f'Cột {i + 1} (chưa xác định tên)' for i, h in enumerate(table['headers'])]
            for ref in table['references']:
                if ref['block_id'] == block.id and ref.get('table'):
                    column = ref['table']['column'] - 1
                    if 0 <= column < len(headers):
                        headers[column] += f"[^{ref['target_id']}]"
            lines = ['| ' + ' | '.join(headers) + ' |', '| ' + ' | '.join('---' for _ in headers) + ' |']
            for ri, row in enumerate(table['rows']):
                values = [_literal(v) for v in row]
                for ref in table['references']:
                    if ri < len(table['row_ids']) and ref['block_id'] == table['row_ids'][ri]:
                        ci = (ref.get('table') or {}).get('column', 1) - 1
                        if 0 <= ci < len(values):
                            values[ci] += f"[^{ref['target_id']}]"
                lines.append('| ' + ' | '.join(values) + ' |')
            export = '\n'.join(lines)
            if table['layout']:
                merged = [c for c in table['layout']['cells'] if c['row_end'] - c['row_start'] > 1 or c['col_end'] - c['col_start'] > 1]
                if merged:
                    export += '\n\nBố cục ô gộp trong nguồn (tọa độ hàng/cột bắt đầu từ 1): ' + '; '.join(
                        f"hàng {c['row_start'] + 1}–{c['row_end']}, cột {c['col_start'] + 1}–{c['col_end']}" for c in merged) + '.'
        if block.type == 'list' and block.attributes.get('list_items'):
            from app.modules.knowledge.parsers.docx_numbering import render_list_items

            item['list_items'] = block.attributes['list_items']
            embedded = [ref for ref in refs if ref.get('item_id')]
            item['embedded_references'] = embedded
            item['references'] = [ref for ref in refs if not ref.get('item_id')]
            visible_items, export_items = [], []
            for entry in item['list_items']:
                selected_refs = [ref for ref in embedded if ref['item_id'] == entry['id']]
                links = ''.join(f"[{ref['label']}](#{ref['target_id']}--ref--{ref['id']})" for ref in selected_refs)
                footnotes = ''.join(f"[^{ref['target_id']}]" for ref in selected_refs)
                visible_items.append({**entry, 'text': entry['text'] + links})
                export_items.append({**entry, 'text': entry['text'] + footnotes})
            item['markdown'] = render_list_items(visible_items)
            export = render_list_items(export_items)
        else:
            item['markdown'] = export
        for ref in refs:
            if not ref.get('item_id') and not (block.type == 'table' and ref.get('table')):
                export += f"[^{ref['target_id']}]"
        blocks.append(item)
        parts.append(export)
    for note in notes:
        if not note['anchors']:
            parts.append(f"### Chú thích {note['label']} (chưa xác định vị trí tham chiếu)\n\n" + note['markdown'])
            continue
        lines = note['markdown'].splitlines() or ['[Chú thích chưa đọc được]']
        parts.append(f"[^{note['anchor']}]: " + lines[0] + ''.join('\n    ' + line for line in lines[1:]))
    return {'version': READER_VERSION, 'title': document.title, 'blocks': blocks, 'notes': notes,
            'limitations': [{'block_id': b.id, 'code': flag.code, 'detail': flag.detail} for b in document.blocks
                            for flag in b.quality_flags if flag.code.startswith('source_note_')],
            'markdown': '\n\n'.join(parts).strip() + '\n', 'source_sha256': document.source.sha256}
