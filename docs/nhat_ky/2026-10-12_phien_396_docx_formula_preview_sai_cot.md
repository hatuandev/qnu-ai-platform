# Phiên #396 — Công thức DOCX đổi số khi tạo PDF xem trước

## Phạm vi

Chẩn đoán hàng Tổng chỉ tiêu tuyển sinh trình độ thạc sĩ trong Phuong huong tuyen sinh 2024_DHQN_final.docx. Chỉ đọc DOCX OOXML, PDF preview đang lưu, code và DB trong transaction READ ONLY. Không sửa tài liệu, runtime, nguồn, review, vector hay xuất bản.

## Bằng chứng

- DOCX word/document.xml không có w:ins/w:del. Hàng tổng thạc sĩ có ô nhãn gridSpan=3, tiếp theo bốn ô tổng.
- Bốn ô tổng là complex field w:fldChar begin/separate/end với instrText =SUM(ABOVE), cached visible results lần lượt1070/451/402/351.
- Cộng 25 bản ghi thạc sĩ từ các ô nguồn cho ra1070/451/402/351; tổng mã ngành cùng25dòng=208561309. Không coi mã ngành là đại lượng cộng hợp.
- PDF preview thực đang lưu qua storage_service.get có7trang; text trang7 chứa67502118,208561309,1070,451. Khớp ảnh người dùng, không chỉ lệch khung overlay. Số rất lớn bị xuống dòng do tràn ô.
- _convert_office_to_pdf gọi Gotenberg /forms/libreoffice/convert trực tiếp với DOCX gốc; không freeze/materialize cached formula results trước chuyển đổi. Docling đọc dữ liệu nguồn riêng; source_extraction.align_office_markdown dùng token alignment tổng thể, không có kiểm tra equality từng ô số liệu.
- Source ks_rev_4bc724ca302b thuộc binding bnd_c4590dbac505 hiện ready sau người dùng duyệt; quality_report overall_status=warning, structured_issues TABLE_HEADER_UNRESOLVED table_6 trang5 và table_7 trang6. ocr_engine=docling+native. Chưa có warning riêng cho formula recalculation mismatch.

## Kết luận

Hai biểu diễn bất nhất: DOCX/Docling giữ cached field results đúng với tổng các dòng, còn LibreOffice khi chuyển PDF đánh giá SUM(ABOVE) với cấu trúc ô gộp sai cột, đưa cả mã ngành vào phép cộng. Việc tổng mã ngành208561309 xuất hiện trong ô tổng là bằng chứng mạnh của lỗi tính lại/ánh xạ cột, không phải OCR nhận nhầm ký tự. Cần duyệt thực tế đến từ header bảng unresolved, không khẳng định guard đã phát hiện sai số PDF.

## Đề xuất chưa triển khai

Giữ nguyên snapshot DOCX; tạo bản sao chỉ phục vụ preview, materialize các field công thức dữ liệu về cached visible text theo parser OOXML field-stack và nested-field boundaries; không hardcode tên văn bản/từ khóa ngành/numeric values. Không flatten PAGE/NUMPAGES/TOC và các field có ngữ nghĩa hiển thị riêng tùy tiện. Không có cached result thì cảnh báo và yêu cầu kiểm tra, không đoán số. Ghi provenance preview là bản bảo toàn kết quả đã lưu, không phải phép tính lại nghiệp vụ.

Đối chiếu DOCX logical grid/gridSpan với bảng PDF/Markdown theo từng ô số liệu và header scope; mismatch tạo cảnh báo review có vị trí. Khôi phục header bảng nối trang5–7 là vấn đề riêng cần xử lý, không bỏ warning. Test merged3cells+SUM(ABOVE), nested fields, no cached value, cache stale, multi-page table và normal PAGE numbering; cached totals là dữ liệu nguồn, không tự coi mọi cached result là đúng nếu chưa đối soát.

## Xác minh và bàn giao

Đã đối chiếu trực tiếp OOXML, cộng lại hàng dữ liệu, đọc PDF đang dùng và quality_report thật. Không chạy Ruff/Pytest/build vì không sửa mã nguồn. Nguồn/tệp gốc/key/worker/DB trạng thái không đổi. Chưa tạo preview mới hoặc reparse. Cập nhật nhật ký, README, PROJECT_CONTEXT và WORK_LOG.
