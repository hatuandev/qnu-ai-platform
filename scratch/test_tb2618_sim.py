import sys
sys.path.insert(0, 'backend')

from app.modules.knowledge.services.ingestion_service import IngestionService
from app.modules.ocr.adapters.gemini_adapter import GeminiOCRAdapter

# Read PDF content
pdf_path = 'docs/tai_lieu/tuyen_sinh/vua_lam_vua_hoc/TB2618_Tuyen_sinh_dai_hoc_vua_lam_vua_hoc_GDTX_Gia_Lai.pdf'
with open(pdf_path, 'rb') as f:
    pdf_bytes = f.read()

print(f"Read PDF: {len(pdf_bytes)} bytes")

# Test 1: Check what Semantic Markdown Partition produces if we give it the Markdown of TB2618
sample_page_1_md = """BỘ GIÁO DỤC VÀ ĐÀO TẠO
TRƯỜNG ĐẠI HỌC QUY NHƠN
Số: 2618/TB-ĐHQN

CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM
Độc lập - Tự do - Hạnh phúc
Gia Lai, ngày 25 tháng 08 năm 2025

THÔNG BÁO
Về việc tuyển sinh đại học, hình thức đào tạo vừa làm vừa học năm 2025 liên kết đào tạo với Trung tâm Giáo dục thường xuyên tỉnh Gia Lai

Trường Đại học Quy Nhơn thông báo tuyển sinh đại học, hình thức đào tạo vừa làm vừa học tại Trung tâm giáo dục thường xuyên tỉnh Gia Lai như sau:

1. Các ngành đào tạo

| STT | Mã ngành | Tên ngành | Ghi chú |
|:---:|:---:|:---|:---:|
| 1 | 7140202 | Giáo dục Tiểu học | |
| 2 | 7140201 | Giáo dục Mầm non | |

2. Đối tượng tuyển sinh
- Đối với thí sinh đã trúng tuyển hoặc đã tốt nghiệp các ngành đào tạo giáo viên (sư phạm) trước ngày 07 tháng 5 năm 2020: thí sinh có bằng tốt nghiệp trung cấp, cao đẳng, đại học nhóm ngành đào tạo giáo viên (sư phạm) được xét tuyển.
- Đối với thí sinh đã trúng tuyển hoặc đã tốt nghiệp các ngành đào tạo giáo viên (sư phạm) sau ngày 07 tháng 5 năm 2020 áp dụng ngưỡng đầu vào là một trong các tiêu chí sau:
+ Học lực lớp 12 đạt loại giỏi trở lên hoặc điểm trung bình chung các môn văn hóa cấp THPT đạt từ 8,0 trở lên;
+ Tốt nghiệp THPT loại giỏi trở lên hoặc học lực lớp 12 đạt loại khá và có 3 năm kinh nghiệm công tác đúng với chuyên môn đào tạo;
+ Tốt nghiệp trung cấp, cao đẳng, đại học đạt loại giỏi trở lên;
+ Tốt nghiệp trình độ trung cấp, hoặc trình độ cao đẳng hoặc trình độ đại học đạt loại khá và có 3 năm kinh nghiệm công tác đúng với chuyên môn đào tạo.

3. Phương thức tuyển sinh: Xét tuyển

4. Thời gian, phương thức đào tạo
Phương thức đào tạo: theo Tín chỉ.
Thời gian học tập: Học vào các buổi tối trong tuần, ngày nghỉ cuối tuần.
Thời gian nhận hồ sơ: đến hết ngày 20/9/2025
Thời gian xét tuyển và nhập học: dự kiến ngày 11/10/2025
Thời gian khai giảng và học môn đầu tiên: dự kiến ngày 18/10/2025

5. Địa điểm học
- Địa điểm học: Tại Trung tâm Giáo dục thường xuyên tỉnh Gia Lai, 61 Lý Thái Tổ, Phường Diên Hồng, tỉnh Gia Lai.
"""

blocks = GeminiOCRAdapter._semantic_markdown_partition(sample_page_1_md, 1)
print(f"\nGenerated {len(blocks)} blocks for Page 1 via _semantic_markdown_partition:")
for i, b in enumerate(blocks, 1):
    print(f"  [{i}] type={b['type']:10s} coords={b['coordinates']} text={repr(b['content_snippet'][:50])}")

service = IngestionService()
pages = service.build_studio_pages(
    chunks=[],
    page_blocks={"1": blocks},
    document_id="doc_test_123",
    page_markdowns={1: sample_page_1_md},
    page_dimensions={1: {"width": 1240, "height": 1754, "orientation": "portrait"}},
)

print(f"\nStudio pages built: {len(pages)} pages")
for p in pages:
    boxes = p["bounding_boxes"]
    print(f"Page {p['page_number']}: {len(boxes)} bounding boxes")
    for b in boxes:
        print(f"  Box: id={b['id']} type={b['type']:10s} label={b['label']:20s} coords={b['coordinates']}")
