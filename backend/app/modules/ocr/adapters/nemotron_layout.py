"""Decode Nemotron located blocks without changing OCR spelling or numeric values."""

import math
import re
from html import escape
from typing import Any

from app.core.exceptions import AppException

_BLOCK = re.compile(
    r'<x_([^>]+)><y_([^>]+)>(.*?)<x_([^>]+)><y_([^>]+)><class_([^>]+)>', re.DOTALL,
)
_CLASSES = {
    'Text': 'text', 'Title': 'title', 'Section-header': 'title',
    'Page-header': 'header', 'Page-footer': 'footer', 'Table': 'table',
    'Picture': 'figure', 'Figure': 'figure', 'Caption': 'caption',
    'Footnote': 'footnote', 'Formula': 'formula', 'List-item': 'text',
}


def _invalid() -> AppException:
    return AppException('Phản hồi Nemotron thiếu cấu trúc hoặc tọa độ hợp lệ.',
                        code='OCR_RESPONSE_INVALID', status_code=502)


def _split_tex(text: str, separator: str) -> list[str]:
    """Split only outside braces, preserving escaped ampersands and line breaks."""
    pieces, start, depth, i = [], 0, 0, 0
    while i < len(text):
        if not depth and text.startswith(separator, i):
            pieces.append(text[start:i])
            i += len(separator)
            start = i
            continue
        if text[i] == '\\':
            i += 2
            continue
        if text[i] == '{':
            depth += 1
        elif text[i] == '}':
            depth -= 1
        if depth < 0:
            raise ValueError('Unbalanced table braces')
        i += 1
    if depth:
        raise ValueError('Unbalanced table braces')
    pieces.append(text[start:])
    return pieces


def _cell_text(raw: str) -> str:
    text = re.sub(r'\\(?:linebreak|newline)(?:\{\})?', '\n', raw.strip())
    for _ in range(8):
        reduced = re.sub(r'\\(?:thead|textbf|textit|emph)\{([^{}]*)\}', r'\1', text)
        if reduced == text:
            break
        text = reduced
    text = re.sub(r'\\([&%_$#{}])', r'\1', text)
    if '\\' in text or '{' in text or '}' in text:
        raise ValueError('Unsupported LaTeX command')
    return escape(text).replace('\n', '<br>')


def _table_html(raw: str) -> str:
    """Project simple explicit tabular cells; complex spans remain raw for review."""
    match = re.fullmatch(r'\s*\\begin\{tabular\}\{([clr|\s]+)\}(.*?)\\end\{tabular\}\s*',
                         raw, re.DOTALL)
    if not match:
        raise ValueError('Unsupported table layout')
    width = sum(char in 'clr' for char in match[1])
    rows = [row.strip() for row in _split_tex(match[2], '\\\\') if row.strip()]
    if not 0 < width <= 128 or not 0 < len(rows) <= 1024:
        raise ValueError('Invalid table dimensions')
    output = []
    for row in rows:
        cells = _split_tex(re.sub(r'\\hline\b', '', row), '&')
        if len(cells) != width:
            raise ValueError('Inconsistent table width')
        # Only provider-explicit \thead establishes header role. Bold/data do not.
        tag = 'th' if all(re.fullmatch(r'\s*\\thead\{.*\}\s*', cell, re.DOTALL)
                          for cell in cells) else 'td'
        output.append('<tr>' + ''.join(f'<{tag}>{_cell_text(cell)}</{tag}>' for cell in cells) + '</tr>')
    return '<table>' + ''.join(output) + '</table>'


def parse_layout(raw: str, page_number: int) -> dict[str, Any]:
    """Keep response order, raw spans and normalized bbox; reject unparsed content."""
    blocks, parts, cursor = [], [], 0
    for index, match in enumerate(_BLOCK.finditer(raw)):
        if raw[cursor:match.start()].strip():
            raise _invalid()
        try:
            x0, y0, x1, y1 = [float(match[i]) for i in (1, 2, 4, 5)]
        except ValueError as exc:
            raise _invalid() from exc
        if not all(math.isfinite(v) for v in (x0, y0, x1, y1)) or not (
            0 <= x0 < x1 <= 1 and 0 <= y0 < y1 <= 1
        ):
            raise _invalid()
        kind, source = match[6], match[3]
        text = source
        needs_review = kind not in _CLASSES
        status = None
        if kind == 'Table':
            try:
                text = _table_html(source)
                status = 'parsed_explicit_cells'
            except ValueError:
                needs_review, status = True, 'unsupported'
        coords = {'left': x0 * 100, 'top': y0 * 100, 'width': (x1 - x0) * 100,
                  'height': (y1 - y0) * 100, 'is_valid': True,
                  'coordinate_system': 'normalized_percent', 'raw_bbox': [x0, y0, x1, y1]}
        blocks.append({'id': f'nemotron_{page_number}_{index}', 'order': index,
            'type': _CLASSES.get(kind, 'unknown'), 'label': kind, 'raw_class': kind,
            'text': text, 'raw_content': source, 'source_span': list(match.span(3)),
            'coordinates': coords, 'layout_confidence': None, 'text_confidence': None,
            'confidence_source': 'unavailable', 'requires_review': needs_review,
            'table_parse_status': status, **{k: coords[k] for k in ('left', 'top', 'width', 'height')}})
        parts.append(text)
        cursor = match.end()
    if not blocks or raw[cursor:].strip():
        raise _invalid()
    return {'page_number': page_number, 'extracted_text': '\n\n'.join(parts), 'blocks': blocks,
            'has_tables': any(b['type'] == 'table' for b in blocks), 'confidence': 0.0,
            'confidence_source': 'unavailable', 'word_count': sum(len(p.split()) for p in parts),
            'line_count': sum(len(p.splitlines()) for p in parts)}
