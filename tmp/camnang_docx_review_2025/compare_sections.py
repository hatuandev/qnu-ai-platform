from pathlib import Path
import json
import re
import unicodedata
import difflib
import sys
import pypdfium2 as pdfium

sys.stdout.reconfigure(encoding='utf-8')
out = Path(__file__).parent
blocks = json.loads((out / 'docx_content.json').read_text(encoding='utf-8'))
source = json.loads((out.parent / 'pdf_conversion_2025/source_analysis.json').read_text(encoding='utf-8'))
headings = [(i, b['text']) for i, b in enumerate(blocks) if b['kind'] == 'paragraph' and re.match(r'^\d+\. ', b['text']) and b['text'].upper() == b['text'] and i > 10]
print('HEADINGS', len(headings))
docsections = []
for j, (idx, title) in enumerate(headings):
    end = headings[j+1][0] if j+1 < len(headings) else next(i for i,b in enumerate(blocks) if b.get('text','').startswith('IV. '))
    text = '\n'.join(b['text'] for b in blocks[idx:end] if b['kind'] == 'paragraph')
    docsections.append((title, text))
def norm(s):
    return re.sub(r'\W+', '', unicodedata.normalize('NFKC', s).casefold())
for page in source:
    seen = []
    for line in page['lines']:
        if not seen or norm(line['text']) != norm(seen[-1]):
            seen.append(line['text'])
    page['text'] = '\n'.join(seen)
results = []
for j, (title, text) in enumerate(docsections):
    titleonly = re.sub(r'^\d+\. ', '', title)
    best = source[3 + j * 2]
    pageidx = best['page'] - 1
    orig = source[pageidx]['text'] + '\n' + source[pageidx+1]['text']
    numbers = lambda s: sorted(set(re.findall(r'\d+(?:[.,]\d+)*(?:\s*[%$])?', s)))
    dnums, pnums = numbers(re.sub(r'^\d+\. ', '', text)), numbers(orig)
    item = {'title': title, 'source_page': best['page'], 'doc_only_numbers': sorted(set(dnums)-set(pnums)), 'pdf_only_numbers': sorted(set(pnums)-set(dnums)), 'doc_text': text, 'pdf_text': orig}
    results.append(item)
    print(json.dumps({k:v for k,v in item.items() if k not in ('doc_text','pdf_text')}, ensure_ascii=False))
(out / 'section_comparison.json').write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding='utf-8')
print('SOURCE FINAL', source[105]['text'])
sourcepath = Path('C:/Users/AnhTuan/Downloads/TUYỂN SINH - HẰNG-20261012T083111Z-1-001/TUYỂN SINH - HẰNG/BÁO CÁO TUYỂN SINH/Cẩm Nang Tuyển Sinh Đại Học Năm 2025 (1).pdf')
pdf = pdfium.PdfDocument(str(sourcepath))
for p in [39, 70, 71, 72, 73, 79, 81, 106, 108]:
    page = pdf[p-1]
    page.render(scale=1.9).to_pil().save(out / f'source-{p:03}.png')
    page.close()
pdf.close()
