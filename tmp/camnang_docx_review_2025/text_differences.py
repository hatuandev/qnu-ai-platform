import json
import re
import difflib
import sys
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')
root = Path(__file__).parent
sections = json.loads((root / 'section_comparison.json').read_text(encoding='utf-8'))
output = []
for s in sections:
    a = re.findall(r'\w+', s['pdf_text'].casefold())
    b = re.findall(r'\w+', s['doc_text'].casefold())
    changes = []
    for tag, i, j, k, l in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes():
        if tag != 'equal' and max(j-i,l-k) >= 5:
            changes.append({'kind':tag,'pdf':' '.join(a[i:j]),'docx':' '.join(b[k:l]),'context_pdf':' '.join(a[max(0,i-5):min(len(a),j+5)])})
    if changes:
        output.append({'title':s['title'],'page':s['source_page'],'changes':changes})
(root / 'text_differences.json').write_text(json.dumps(output,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(output,ensure_ascii=False,indent=2))
