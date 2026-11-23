# Phiên 1020 — Giữ cây đề mục và bóc tách PowerPoint

## Phạm vi

- Backend V1 ghi `structure.context.heading_path` cho đoạn, bảng và row card có căn cứ. Mỗi nút có `level`, `text`, `citation`. Giữ tiêu đề gần nhất trong trường cũ. Dùng cấp Markdown có sẵn và cấp Word do Docling trả. PDF dùng dấu hiệu đề mục nguồn nhận diện được. Với Excel và PowerPoint, `source_scope` định danh sheet hoặc slide.
- Phân biệt bảng độc lập của Excel/PowerPoint với mảnh bảng nối trang. Nhánh tạo row card, facts và metadata không dùng nhãn cột của bảng khác cho bảng độc lập.
- Backend nhận và bóc tách PPTX bằng bản `python-pptx` đã khóa trong dự án. Dữ liệu canonical giữ chữ, ô gộp, ghi chú và vị trí slide/shape. Đồ họa chưa đọc được có cờ đối chiếu. Slide chỉ có đồ họa chưa đọc trả `pptx_slide_requires_review`. Cấp đề mục Word dùng profile v2 cho lượt mới.
- `heading_path` là metadata cho các chunk được tạo mới. Chỉ mục đang phục vụ và dữ liệu đang phát hành không được lập lại trong phiên này. Bộ chọn tệp FE V2 chưa được cập nhật.

## Kiểm chứng

Các lệnh Python chạy từ `backendV1`.

- `uv run --no-sync pytest -q --tb=short --show-capture=no --basetemp <thư mục cô lập> <các tệp unit liên quan>` exit 0, **363 đạt**. Phạm vi gồm chunking, Markdown, Excel, PowerPoint, DOCX/PDF, OCR, metadata và RAG context, row cards, fact query, căn cứ bảng. Lần mở rộng đầu gặp 8 lỗi tạo thư mục tạm mặc định của Windows. Dùng `--basetemp` trong vùng test của dự án đã xử lý trở ngại đó.
- `uv run --no-sync python scripts/run_isolated_tests.py` với `test_auto_extraction_710.py::test_powerpoint_upload_extracts_slides_with_no_ocr_provider` và `::test_docx_table_has_real_structure_and_original_is_unchanged` exit 0, **2 đạt**. Upload qua API, chạy worker, đọc native JSON và Markdown, không cần provider OCR cho PPTX có chữ. Harness xác nhận xóa DB thử và giữ sentinel.
- Tích hợp `test_contextual_scope_790.py::test_new_recipe_preserves_body_and_scope_before_topk[True]` exit 1 với `KeyError: 'search_context'`. Lượt thử với `index/service.py` từ `35e43332` nạp trong tiến trình test riêng tái hiện cùng lỗi. Ở cả hai phiên bản, row card được tạo sau khi áp dụng làm giàu ngữ cảnh cho các chunk khác. Harness đã dọn các DB thử.
- `ruff check` exit 0. `ruff format --check` exit 1 trên toàn bộ phạm vi vì bảy tệp đã lệch định dạng từ commit `35e43332`. Đối chiếu từng hunk định dạng trước và sau xác nhận không có hunk định dạng mới. 12 tệp còn lại đạt kiểm tra.
- Không chạy toàn bộ backend trong phiên này. Lượt rộng phiên 1019 đã có lỗi nền xác nhận và được dừng.
