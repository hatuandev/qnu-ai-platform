# Phiên 423 — Gỡ năm bản sao lưu thất bại cũ

## Yêu cầu

Người dùng yêu cầu xóa đúng năm bản thất bại trong ảnh để tự sao lưu một bản mới. Thực hiện gỡ khỏi catalogue bằng chuyển metadata vào thư mục phục hồi, không xóa vĩnh viễn, không tạo backup mới và không sửa code/DB/Redis.

## Xác minh và thao tác

Đọc danh sách thực ở `D:\DuAnPhanMem\qnu-ai-platform\backend\storage\backups`, xác nhận năm record create/failed/size_bytes0/sha256null tương ứng ảnh:

- `bkp_1c628bbeb7564396abb5eebfbdfb04d2`: 20:27:12 13/10/2026.
- `bkp_7430df87ffca495186b2287e8e4a0211`: 20:19:12.
- `bkp_55bebfc93e3e4a278da4703c3b3f567c`: 19:41:07.
- `bkp_dc854385660e413ebdf6b589edb98eaf`: 19:40:57.
- `bkp_8613ba2b17dc44ec8759686d9de81945`: 19:40:55.

Không có `.qnubak` hoặc `.qnubak.partial` cho các ID này; lần 20:27 cũng là blocker workflow cũ, đã xử lý ở phiên 422. Không xóa bản backup hợp lệ hay dữ liệu nguồn.

Thao tác bằng PowerShell native end-to-end, exact literal paths. Xác minh root/source/destination nằm đúng thư mục backup và không phải reparse point, destination mới `.removed-423` chưa tồn tại; mở exclusive handle trên `.reservation.lock` và `.operation.lock` để dừng nếu có thao tác backup chạy và ngăn thao tác mới trong lúc di chuyển. Kiểm tra lại metadata trước ghi.

Chuyển duy nhất năm tệp `<id>.json` vào `backend/storage/backups/.removed-423/`; không recursive delete/move, không ghi đè, không đụng lock files. Đối chiếu SHA-256 trước/sau từng file đạt. Catalogue chỉ glob top-level nên các record này không còn hiển thị.

## Kết quả và bàn giao

- Gỡ khỏi catalogue **5/5** record; remaining top-level backup records **0** tại thời điểm kiểm tra.
- Năm metadata được giữ nguyên, có thể phục hồi từ `.removed-423` bằng đưa đúng tệp trở lại root khi không có backup đang chạy. Không tự hoàn nguyên lịch sử hoặc giả bản backup thành công.
- Không reset DB, không xóa Redis/tài liệu, không chạy lại chatbot, không tự sao lưu mới.
- Không thay đổi source; không chạy Ruff/Pytest/Vite. Kiểm chứng bằng trạng thái file trước thao tác, locking, checksum và inventory sau thao tác.
- Người dùng F5/Làm mới để thấy danh sách trống và tự tạo bản mới bằng mật khẩu tự giữ; việc dọn catalogue không thay cho kiểm tra backup corpus thật.

Đã cập nhật nhật ký README, PROJECT_CONTEXT và WORK_LOG.
