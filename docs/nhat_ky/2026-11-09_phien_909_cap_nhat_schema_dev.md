# Phiên909 — Cập nhật schema local để chạy dev

Người dùng chạy `make.ps1 dev` bị chặn PostgreSQL schema cũ. Kiểm `v1-db-check` xác nhận DB local ở `0017_answer_review`, code có migration `0018_preparation_auto`. Đọc migration: mở rộng check mode cho chuẩn bị tự động và thêm expression index cho reuse key; không xóa dữ liệu.

Xác minh cấu hình trỏ PostgreSQL loopback5432. Sao lưu DB app qua `pg_dump -Fc`, chép vào `storage/backups/qnu_pre_0018_20261109_090840.dump` (251.945 byte), kiểm danh sách bằng `pg_restore --list` đạt trước thay đổi. Không ghi thông tin đăng nhập vào tài liệu/log.

Chạy từ root repo:

- `.\make.ps1 v1-migrate`: PASS, exit0, upgrade0017→0018.
- `.\make.ps1 v1-db-check`: PASS, exit0, `0018_preparation_auto (head)`.
- `.\make.ps1 v1-check`: PASS, exit0; Redis/PostgreSQL/Qdrant/storage/frontend đạt. Storage chỉ kiểm read-only, không chứng minh quyền ghi hay chất lượng model.

Không sửa source, không clear/reset/seed/reindex, không mở dev thay người dùng. Có thể chạy lại `.\make.ps1 dev` và mở cổng3001. Không chạy lại unit/build/model vì tác vụ chỉ áp migration đã có và kiểm môi trường. Giữ các giới hạn RAG/F13 của phiên908.
