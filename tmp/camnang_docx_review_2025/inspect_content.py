from pathlib import Path
from collections import Counter
import json
import sys
import hashlib
from docx import Document
from docx.table import Table
from docx.text.paragraph import Paragraph

sys.stdout.reconfigure(encoding="utf-8")
src = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('C:/Users/AnhTuan/Downloads/Cam_Nang_Tuyen_Sinh_Dai_Hoc_2025_QNU.docx')
out = Path(sys.argv[2]) if len(sys.argv) > 2 else Path(__file__).parent
out.mkdir(parents=True, exist_ok=True)
doc = Document(src)
blocks = []
for i, element in enumerate(doc.element.body):
    tag = element.tag.rsplit('}', 1)[-1]
    if tag == 'p':
        p = Paragraph(element, doc)
        blocks.append({'block': i, 'kind': 'paragraph', 'style': p.style.name, 'text': p.text})
    elif tag == 'tbl':
        t = Table(element, doc)
        blocks.append({'block': i, 'kind': 'table', 'rows': [[c.text for c in r.cells] for r in t.rows]})
(out / 'docx_content.json').write_text(json.dumps(blocks, ensure_ascii=False, indent=2), encoding='utf-8')
lines = []
for b in blocks:
    if b['kind'] == 'paragraph':
        lines.append(f"[{b['block']} {b['style']}] {b['text']}")
    else:
        lines.extend(f"[{b['block']} row {i}] {' | '.join(row)}" for i, row in enumerate(b['rows']))
(out / 'docx_content.txt').write_text('\n'.join(lines), encoding='utf-8')
print(json.dumps({'sha256': hashlib.sha256(src.read_bytes()).hexdigest(), 'blocks': len(blocks), 'paragraph_styles': dict(Counter(p.style.name for p in doc.paragraphs)), 'tables': [len(t.rows) for t in doc.tables], 'images': len(doc.inline_shapes)}, ensure_ascii=False))
print('\n'.join(lines[:26]))
print('\n---last---\n' + '\n'.join(lines[-26:]))
