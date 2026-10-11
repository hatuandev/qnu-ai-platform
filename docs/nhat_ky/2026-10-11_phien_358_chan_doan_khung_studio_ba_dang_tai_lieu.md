# Phiên #358 — Chẩn đoán khung Studio và ba dạng tài liệu

## Mục tiêu và phạm vi

Kiểm tra DOCX, PDF xuất từ Word và PDF ảnh scan trong luồng Kho tri thức. Chỉ chẩn đoán: không sửa runtime, không reset, không gọi OCR lại tài liệu người dùng, không thay đổi provider hoặc qnu-sso.

## Bằng chứng

- PDF người dùng cung cấp có 14 trang, metadata Microsoft Word 2024, tất cả trang có lớp chữ và không có ảnh nhúng. Đây là PDF số, không phải bản scan.
- Chạy parser thật trên file: 74 khối hình học, 4 bảng, 14 trang. Khi đưa kết quả qua nhánh normalize hiện tại không truyền pages/layout, manifest còn 0 khối.
- Đọc DB nguồn tương ứng: revision `ks_rev_a157a9974bc8`, binding `bnd_63f2518d6518`, ready, parser_profile standard, ocr_engine native, reused_artifact false. Manifest 14 trang, 0 khối, không kích thước; Markdown 24689 ký tự.
- Nhánh standard trong import và reparse chỉ giữ raw_text/page_count/tables, bỏ ParsedContent.blocks. Studio đọc manifest đã lưu, không tự tái tạo geometry.
- Geometry native dùng x/y và content_snippet; contract Studio/Paddle dùng left/top và text. Cần chuẩn hóa contract trước khi lưu, không chuyển thẳng blocks hiện tại.
- DOCX qua Docling/fallback có Markdown nhưng chưa có layout vật lý. Endpoint ảnh trang Knowledge hỗ trợ PDF/ảnh, từ chối DOCX với UNSUPPORTED_PAGE_IMAGE. Ép DOCX trực tiếp sang Paddle không thay thế bước chuyển định dạng.
- Fallback OCR standard chỉ chạy khi cả raw_text rỗng. Probe PDF hỗn hợp hai trang (chữ + ảnh) xác nhận có chữ toàn tài liệu khiến điều kiện fallback không kích hoạt dù trang ảnh không có chữ.
- Profile layout_analysis vẫn gọi OCR auto; OCR auto/combo có native fast-path trên PDF có chữ, nên không bảo đảm thực sự chạy Paddle để phân tích layout.

## Hướng đề xuất, chưa triển khai

1. Hợp nhất block/page contract với tọa độ phần trăm, kích thước thật, nội dung và provenance. Giữ geometry native trong cả import/reparse; không bịa confidence.
2. Phân loại PDF theo từng trang; đọc native trang có chữ, OCR trang ảnh, ghép đúng thứ tự.
3. Với DOCX, tạo PDF preview dẫn xuất bằng bộ render Office, lưu độc lập trong Knowledge; không giả lập phân trang/bbox.
4. Tách yêu cầu layout rõ ràng khỏi OCR auto, bổ sung thao tác bóc tách lại trong Studio và hiển thị engine thực tế.

## Kiểm chứng

- `tests/test_source_page_provenance.py`, `tests/test_docling_office_parser.py`, `tests/test_paddleocr_adapter.py`: **15 passed (4.75s)**.
- Kiểm tra PDF bằng PyMuPDF/parser thật và DB read-only như trên. Probe PDF hỗn hợp tạo trong bộ nhớ, không nạp vào hệ thống.
- Không chạy full pytest/Ruff/build vì không thay đổi mã nguồn. Các test đạt chưa chứng minh import native giữ bbox hay DOCX có preview; cần regression bổ sung khi sửa.

## Tệp thay đổi

Chỉ nhật ký này, mục lục nhật ký, PROJECT_CONTEXT, WORK_LOG và snapshot phiên #358. Không thay đổi dữ liệu nghiệp vụ.
