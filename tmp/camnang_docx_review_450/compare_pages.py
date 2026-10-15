from pathlib import Path
import json
import re
import difflib
import unicodedata
import sys

sys.stdout.reconfigure(encoding='utf-8')
out = Path(__file__).parent
blocks = json.loads((out / 'docx_content.json').read_text(encoding='utf-8'))
original = json.loads((out.parent / 'pdf_conversion_2025/source_analysis.json').read_text(encoding='utf-8'))
pages = {}
page = None
for b in blocks:
    text = b.get('text', '')
    marker = re.match(r'^Trang (\d+)\b', text)
    if b.get('style') == 'Heading 2' and marker:
        page = int(marker[1])
        pages[page] = []
    elif page is not None:
        pages[page].append(text)
results = []
for source in original[3:106]:
    number = source['page']
    lines = [l['text'] for l in source['lines']]
    cleaned = []
    for line in lines:
        if not cleaned or line != cleaned[-1]:
            cleaned.append(line)
    a = '\n'.join(cleaned)
    b = '\n'.join(pages[number])
    numbers = lambda s: set(re.findall(r'\d+(?:[.,]\d+)*',s))
    atokens, btokens = [re.findall(r'\w+', unicodedata.normalize('NFC',s).casefold()) for s in (a,b)]
    changes = []
    for tag,i,j,k,l in difflib.SequenceMatcher(None, atokens, btokens, autojunk=False).get_opcodes():
        if tag != 'equal':
            changes.append({'kind':tag,'pdf':' '.join(atokens[i:j]),'docx':' '.join(btokens[k:l])})
    item = {'page':number,'pdf_only_numbers':sorted(numbers(a)-numbers(b)),
        'docx_only_numbers':sorted(numbers(b)-numbers(a)), 'changes': changes}
    if item['pdf_only_numbers'] or item['docx_only_numbers'] or changes:
        results.append(item)
(out / 'page_differences.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
old = json.loads((out.parent / 'camnang_docx_review_2025/docx_content.json').read_text(encoding='utf-8'))
table = next(b['rows'][1:] for b in old if b['kind']=='table')
records = [b['text'] for b in blocks if b['kind']=='paragraph' and '— Mã ngành:' in b['text']]
def normalize(text):
    text = unicodedata.normalize('NFC',text).casefold().replace('kt và pl','kt&pl')
    return re.sub(r'[^\w]', '',text)
table_changes = []
for row,record in zip(table,records):
    parsed = re.match(r'(.*?) — Mã ngành: (.*?)\. Tổ hợp môn xét tuyển: (.*)',record)
    if not parsed:
        table_changes.append({'row':row[0],'invalid_format':record})
        continue
    name,code,value = parsed.groups()
    if normalize(name+code+value) != normalize(row[2]+row[1]+row[3]):
        table_changes.append({'row':row[0],'old':row,'new':record})
print(json.dumps({'page_count_markers':len(pages),'missing_page_markers':sorted(set(range(1,109))-set(pages)),
    'non_nfc_paragraphs':sum(b.get('text','') != unicodedata.normalize('NFC',b.get('text','')) for b in blocks),
    'source_table_records':len(records),'table_changed_vs_previous_word':table_changes,
    'page_content_differences':results},ensure_ascii=False,indent=2))
