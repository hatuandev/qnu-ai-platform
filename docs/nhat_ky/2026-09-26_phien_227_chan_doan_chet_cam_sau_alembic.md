# NHẬT KÝ LÀM VIỆC — PHIÊN #227
**Ngày**: 2026-09-26 | **Thời gian**: 00:35 (UTC+7)
**Tiêu đề**: Chẩn Đoán Chết Câm Sau Alembic Context — Phép Chia Đôi

---

## 1. Phát Hiện Mới
- Vòng 16:53 (DB fresh): migrate chạy đủ 8 upgrades rồi mới chết ở seed.
- Vòng hiện tại (DB đã ở head): chết ngay sau `Will assumeTransactional DDL`, đều như vắt chanh, không traceback.
- Đo local: `import app.cli` chỉ ~122MB → loại OOM lúc import; import nặng (torch/cv2) không nằm trong đường migrate.
- Kết luận trung gian: killer nằm trong/sau `command.upgrade` no-op hoặc lúc connect async — cần chia đôi bằng thực nghiệm.

## 2. Phép Chia Đôi (chạy trên server, không đổi code)
```bash
docker inspect qnu_backend --format 'ExitCode={{.State.ExitCode}} OOMKilled={{.State.OOMKilled}}'
docker run --rm --network qnu_network demo-ai-platform-9hzwjj-backend python -m app.cli db check
```
- `db check` chỉ SELECT (không qua alembic env): nếu cũng chết câm → killer ở tầng connect async (asyncpg/uvloop/event loop).
- Nếu `db check` in được revision + bảng → killer nằm riêng trong đường `command.upgrade` no-op.
- ExitCode 137 = OOM (tăng limit RAM), 139 = segfault lib C, 0 = tự thoát sạch.

## 3. Trạng Thái
- Chưa đổi code phiên này (chờ kết quả chia đôi để sửa trúng).
