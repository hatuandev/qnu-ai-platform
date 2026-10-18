# Phiên 509 — Mẫu chuẩn hóa DOCX sang Markdown

## Phạm vi

Người dùng gửi một DOCX và yêu cầu bản Markdown mẫu giữ cấu trúc. Chỉ tạo artifact local tại `backend/storage/md509/output/`; không sửa app, DB, canonical revision, nguồn gốc, vector hoặc publication. Không commit/push/restart, không gọi model/OCR hay dịch vụ ngoài.

## Phương pháp

- Đọc trực tiếp OOXML theo thứ tự body, đoạn và bảng; giữ nội dung, điều kiện, số và ô trống. Unicode NFC/khoảng trắng là biến đổi hình thức, không xác minh OCR hay sửa dữ kiện.
- Bảng nhiều tầng trải phẳng header kèm đúng năm; phụ lục kế thừa chỉ từ vMerge thật; hai thang chứng chỉ tách tại cột trang trí trống. Không gán năm tiêu đề cho dữ liệu lịch sử.
- Artifact gồm Markdown, ghi chú cần duyệt và JSON hash/source-unit/OOXML mapping. Không đưa corpus vào nhật ký hoặc memory; artifact chưa được đưa Git.
- Các vấn đề nguồn gồm mã không nhất quán, ô thiếu và lỗi chữ/nhãn được ghi trong ghi chú artifact, không tự sửa.

## Kiểm chứng thực chạy

Runtime Python dùng bản đóng gói được xác định bởi workspace dependency loader.

Lệnh: `backend/storage/md509/validate_example.py` qua runtime đó, cwd repo, exit 0. PASS: hash nguồn không đổi, hash MD khớp, UTF-8 không BOM/LF/NFC, 5 bảng đầu ra có 53/5/5/52/38 dòng dữ liệu, đối chiếu 924 giá trị với OOXML, giữ khác biệt ô trống/số 0, đúng header năm. Sidecar ghi 1.035 source units.

NOT RUN: render nguồn DOCX vì runtime Windows không có LibreOffice đóng gói; không dùng phần mềm desktop người dùng thay thế. Chưa có số trang/bbox vật lý đã xác minh. Các shape trang trí không biểu diễn trong Markdown; nguồn không có media ảnh nhúng hoặc công thức OMML. Không cần pytest/build/model/benchmark cho artifact tài liệu này.

Đã yêu cầu mở file Markdown trong panel; công cụ trả queued, không coi là kiểm tra UI thành công.

## Giới hạn và bước sau

Bản mẫu DRAFT_REQUIRES_SOURCE_REVIEW, chưa đủ để khẳng định nội dung chính thức hoặc RAG tốt hơn qua benchmark. Sidecar minh họa không tự được app nhập khi upload MD. Duyệt lỗi nguồn trước; tích hợp revision/provenance vào app là công việc khác cần yêu cầu riêng. Không nạp thêm bản song song gây trùng nguồn.
