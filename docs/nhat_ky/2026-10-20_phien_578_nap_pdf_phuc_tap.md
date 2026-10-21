# Phiên 578 — Dọn kho tuyển sinh và nạp PDF phức tạp

Người dùng yêu cầu dọn kho tri thức rồi nạp bản PDF vừa export. Phạm vi: toàn col_admissions theo xác nhận trước; giữ Repository, nguồn local, kho khác và audit lịch sử. Nhánh hiện tại v1.0.1; không sửa app hoặc commit/push.

Đã dùng skill ingestion và đọc hướng dẫn PDF. Preflight xác minh DB/MinIO/Qdrant local, actor/quyền server; cleanup qua API chính thức completed, vector cũ về 0. Upload HTTP202, import HTTP201, worker xử lý xong đến review_required. PDF 18 trang, binding bnd_12190866d5ec, revision ks_rev_1071c152fab0. Hash nguồn và cặp MD/JSON, cú pháp và projection binding PASS; nội dung NEEDS_ATTENTION, chưa nạp vector hoặc xuất bản. Bảng 1 nguồn 12 cột bị nhận 34 cột; 1541 mục chặn gồm nhiều cờ lặp theo cột, không phải 1541 lỗi độc lập. Giữ Quality Gate.

Lệnh/script từ root: backend/.venv/Scripts/python.exe backend/storage/context578/preflight.py; clean_upload.py; observe.py; validate_pdf.py; handoff.py. Công cụ tạm ban đầu gặp lỗi tên field/kiểu fields và encoding console; đã sửa chỉ trong Storage, không sửa app hoặc coi các lượt lỗi đó là PASS. Các lượt hoàn tất cuối dùng để đối soát. Không chạy regression/full pytest vì không sửa code; không gọi benchmark. Browser chỉ tới login, không chứng nhận frontend E2E.

Đã đối chiếu hash row ngoài phạm vi và Repository cũ sau thao tác; giữ nguyên. Giữ source PDF untracked trên ổ đĩa và evidence trong Storage ignored. Không tạo DB test hoặc hội thoại test cần dọn. Không xóa Storage cũ.

[Báo cáo chi tiết](../bao_cao/context578/PDF_INGESTION_REPORT.md).
