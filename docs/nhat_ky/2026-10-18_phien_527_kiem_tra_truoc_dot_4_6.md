# Phiên 527 — Kiểm tra điều kiện trước đợt 4–6

Người dùng yêu cầu tiếp tục dọn kho tuyển sinh, chọn tài liệu, bóc tách chuẩn,
nạp vector và xuất bản theo kế hoạch. Phạm vi không gồm xóa Kho tài liệu,
file gốc, cấu hình hay các collection khác. Người dùng đã chọn tự tạo full
backup trên UI và giữ mật khẩu; chưa có xác nhận hoàn thành.

## Kiểm tra thực tế

- Đọc context, trạng thái Git, hướng dẫn ingestion/RAG/backend/clean-code,
  ModelOps và quy định bảo mật, kiểm chứng, memory. Giữ nguyên worktree bẩn.
- Đọc catalogue bằng `list_records()` (không gọi service catalogue có thể
  đổi trạng thái tác vụ cũ): trả danh sách rỗng, exit0.
- Cấu hình local giải quyết thư mục backup thành `backend/storage/backups`:
  0 archive `.qnubak`, 0 metadata `bkp_*.json`. Không có archive để kiểm hash,
  decrypt hoặc đối soát thành phần. Không kết luận về bản lưu ở máy khác.
- Chạy từ backend: `.venv/Scripts/python.exe -m
  scripts.standard_migration_inventory --collection col_admissions --save-report`.
  Exit0: 22 bindings, 33 revisions đều legacy, 0 queued/running job.
  Báo cáo readback: `snapshots/migration-inventory/7d55cc0cf8594d8c8d1497d0a6093682.json`.
  `backup_verified=false`; `purge_authorized=false` là trạng thái gate của
  công cụ, không phủ nhận yêu cầu thực hiện của người dùng.

## Quyết định và bước tiếp

Chưa đủ điều kiện an toàn để purge. Không pause/purge/import/reindex/publish,
không gọi OCR/model, không đổi cấu hình, restart, migration, commit hay push.
Chỉ ghi báo cáo kiểm kê và nhật ký; không thay mã ứng dụng.

Người dùng cần tạo full backup trên UI, chạy chức năng **Kiểm tra** cho bản đó
và giữ mật khẩu riêng (không gửi vào chat). Nếu backup nằm ngoài catalogue local,
cần chỉ rõ bản lưu để kiểm tra thay vì giả định không tồn tại. Sau khi xác minh
bản lưu phù hợp mới tiếp tục đợt4, xử lý sidecar khi purge, rồi đợt5–6.

NOT RUN: pytest/build, live OCR/inference/vector/publication, decrypt/restore drill.
Không gọi điều kiện backup PASS hoặc tuyên bố đợt4–6 hoàn thành.
