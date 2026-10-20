"""Conservative section roles from independent typography, geometry and numbering."""
import re
from collections import Counter

NUMBER = re.compile(r'^\s*((?:\d+\.)+|\d+[)]|[IVXLCDM]+[.)])\s+(\S.*)$')


def _bold(item: dict) -> bool:
    spans = [s for line in item.get('raw', {}).get('lines', []) for s in line.get('spans', []) if s.get('text', '').strip()]
    total = sum(len(s['text'].strip()) for s in spans)
    return bool(total and sum(len(s['text'].strip()) for s in spans if s.get('flags', 0) & 16
                             or 'bold' in s.get('font', '').casefold()) / total >= 0.8)


def heading_decisions(pages: list[list[dict]], body_size: float) -> dict[str, dict]:
    """No content dictionary; unproved numbered candidates retain their original role."""
    margins = Counter(' '.join(i.get('text', '').split()) for page in pages for i in page
                      if i.get('bbox') and (i['bbox'][1] < 8 or i['bbox'][3] > 92))
    result = {}
    sizes = sorted({i.get('font_size', 0) for page in pages for i in page if i.get('font_size', 0) > body_size}, reverse=True)
    for page_index, page in enumerate(pages):
        for index, item in enumerate(page):
            value, box = item.get('text', '').strip(), item.get('bbox')
            if not value or not box or item.get('kind') in {'table', 'header', 'footer', 'footnote', 'signature', 'stamp', 'formula', 'equation'}:
                continue
            if margins[' '.join(value.split())] > 1 and (box[1] < 8 or box[3] > 92):
                continue
            number = NUMBER.match(value)
            short = len(value) <= 180 and len(value.splitlines()) <= 2
            if not any(char.isalpha() for char in value) or re.fullmatch(r'[IVXLCDM]+', value) or '=' in value:
                continue
            larger = item.get('font_size', 0) > body_size > 0
            # Numbering alone is never evidence: actual bold glyphs and a following
            # body in this column establish the independent role.
            following = next((n for n in page[index + 1:] if n.get('bbox') and n['bbox'][1] >= box[3]
                              and min(box[2], n['bbox'][2]) > max(box[0], n['bbox'][0])), None)
            next_page = False
            if following is None and page_index + 1 < len(pages):
                following = next((n for n in pages[page_index + 1] if n.get('text', '').strip() and n.get('bbox')
                    and min(box[2], n['bbox'][2]) > max(box[0], n['bbox'][0])
                    and margins[' '.join(n.get('text', '').split())] < 2), None)
                next_page = following is not None
            isolated = next_page or following is not None and following['bbox'][1] - box[3] > 0.15 * (box[3] - box[1])
            numbered = bool(number and short and _bold(item) and isolated and not value.endswith(('.', ';', ':')))
            if numbered or larger and short and item.get('kind') not in {'figure', 'image', 'chart'}:
                label = number[1] if number else None
                level = sizes.index(item['font_size']) + 1 if larger else 1
                if label:
                    level = label.rstrip('.)').count('.') + 1
                result[item['locator']] = {'level': level, 'source_label': label,
                    'basis': ['numbering', 'bold_glyphs', 'vertical_separation', 'following_page_body' if next_page else 'following_column_body'] if numbered else ['font_size'],
                    'status': 'inferred'}
            elif number and short:
                result[item['locator']] = {'status': 'unresolved', 'basis': ['numbering_only']}
    return result
