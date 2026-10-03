from app.modules.ocr.adapters.gemini_adapter import GeminiOCRAdapter
from app.modules.ocr.adapters.openai_vision_adapter import QwenOCRAdapter
from app.modules.ocr.service import OCRService

# Test 1: layout_json parsing in Gemini & Qwen
sample_ocr_output = """<!-- Trang 1 -->
```layout_json
[
  {"label": "header", "box_2d": [40, 80, 160, 920], "snippet": "BỘ GIÁO DỤC VÀ ĐÀO TẠO"},
  {"label": "title", "box_2d": [180, 180, 240, 820], "snippet": "THÔNG BÁO TUYỂN SINH"},
  {"label": "table", "box_2d": [320, 80, 480, 920], "snippet": "STT | Mã ngành | Chỉ tiêu"},
  {"label": "signature", "box_2d": [750, 550, 900, 920], "snippet": "HIỆU TRƯỞNG"}
]
```
# BỘ GIÁO DỤC VÀ ĐÀO TẠO
## THÔNG BÁO TUYỂN SINH

| STT | Mã ngành | Tên ngành | Chỉ tiêu |
|:---|:---|:---|:---|
| 1 | 7480201 | CNTT | 100 |

KT. HIỆU TRƯỞNG
"""

clean_txt, blocks = GeminiOCRAdapter._parse_page_layout_and_markdown(sample_ocr_output, 1)
print(f"Gemini parsed blocks count: {len(blocks)}")
for b in blocks:
    print(f"  Block: {b['type']} {b['coordinates']} {b['content_snippet']}")
assert len(blocks) == 4, "Expected 4 blocks from Gemini"

clean_qwen_txt, qwen_blocks = QwenOCRAdapter._parse_page_layout_and_markdown(sample_ocr_output, 1)
print(f"Qwen parsed blocks count: {len(qwen_blocks)}")
assert len(qwen_blocks) == 4, "Expected 4 blocks from Qwen"

# Test 2: Semantic Markdown partition fallback
sample_plain_md = """BỘ GIÁO DỤC VÀ ĐÀO TẠO
TRƯỜNG ĐẠI HỌC QUY NHƠN

THÔNG BÁO TUYỂN SINH ĐẠI HỌC

Trường Đại học Quy Nhơn thông báo tuyển sinh năm 2026.

| STT | Mã ngành | Chỉ tiêu |
|:---|:---|:---|
| 1 | 7480201 | 150 |

- Hồ sơ gồm có phiếu đăng ký
- Bản sao học bạ

HIỆU TRƯỞNG ĐÃ KÝ
"""
sem_blocks = GeminiOCRAdapter._semantic_markdown_partition(sample_plain_md, 1)
print(f"Semantic partition blocks count: {len(sem_blocks)}")
for b in sem_blocks:
    print(f"  Semantic block: {b['type']} {b['coordinates']} {b['content_snippet'][:40]}")
assert any(b["type"] == "header" for b in sem_blocks), "Expected header block"
assert any(b["type"] == "title" for b in sem_blocks), "Expected title block"
assert any(b["type"] == "table" for b in sem_blocks), "Expected table block"
assert any(b["type"] == "list" for b in sem_blocks), "Expected list block"
assert any(b["type"] == "signature" for b in sem_blocks), "Expected signature block"

# Test 3: OCRService engines catalog
svc = OCRService()
engines = [e.name for e in svc.list_engines()]
print(f"OCRService registered engines: {engines}")
assert "qwen_ocr" in engines, "qwen_ocr not in engines!"
assert "gemini_ocr" in engines, "gemini_ocr not in engines!"
print(">>> ALL CHECKS PASSED 100%! <<<")
