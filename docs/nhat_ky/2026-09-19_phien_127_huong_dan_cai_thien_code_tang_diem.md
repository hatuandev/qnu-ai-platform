# NHẬT KÝ PHIÊN #127 — HƯỚNG DẪN CẢI THIỆN CODE ĐỂ TĂNG ĐIỂM ĐÁNH GIÁ

## 1. Thông tin phiên

- **Thời gian**: 2026-09-19 22:45 (UTC+7)
- **Mục tiêu**: Tạo hướng dẫn thực thi chi tiết để đưa QNU AI Platform từ Internal Beta mạnh lên Production Candidate 8,5+/10 bằng cải thiện có bằng chứng.
- **Phạm vi**: Chỉ cập nhật tài liệu; không sửa code, schema, runtime, seed data hoặc dữ liệu Provider của session khác.

## 2. Thay đổi chính

| Tệp | Hành động | Mô tả |
| :--- | :--- | :--- |
| `docs/ke_hoach/08_huong_dan_cai_thien_code_tang_diem_danh_gia.md` | Tạo mới | Hướng dẫn 19 phần: score target, thứ tự sửa an toàn, migration, secret, RAG, trusted actor/HITL, streaming/accounting, workflow durability, storage, refactor, testing/CI, observability/deployment và Definition of Done. |
| `docs/ke_hoach/README.md` | Cập nhật | Bổ sung tài liệu 08 vào mục lục kế hoạch. |
| `docs/memory/PROJECT_CONTEXT.md` | Cập nhật | Ghi nhận phiên #127 và ba phiên kỹ thuật được khuyến nghị tiếp theo. |
| `docs/memory/snapshots/2026-09-19_session_127.md` | Tạo mới | Snapshot trạng thái sau khi hoàn thành hướng dẫn. |
| `docs/WORK_LOG.md` | Cập nhật | Bổ sung phiên #127 vào bảng tổng hợp. |

## 3. Quyết định kỹ thuật quan trọng

- Không viết lại kiến trúc; giữ Modular Monolith và sửa theo lát cắt nhỏ.
- Ưu tiên Schema Truth trước Seed/Reindex để tránh làm sai dữ liệu lần nữa.
- Điểm chỉ tăng khi có bằng chứng live: migration, payload/revision parity, encryption migration, approval atomic, streaming/accounting exactly-once và CI/restore drill.
- Không sửa chồng các tệp seed/provider khi session khác còn hoạt động.
- Không cập nhật `docs/quy_trinh/` vì phiên này không thay đổi logic runtime hoặc lifecycle; tài liệu chỉ mô tả cách triển khai trong tương lai.

## 4. Kiểm tra

- Đọc lại tệp bằng UTF-8: đạt.
- Kiểm tra ký tự Mojibake trên các tệp tài liệu thay đổi: đạt.
- `git diff --check` trên các tệp tài liệu của phiên: đạt.
- Không chạy Backend/Frontend test vì không có thay đổi code/runtime.
