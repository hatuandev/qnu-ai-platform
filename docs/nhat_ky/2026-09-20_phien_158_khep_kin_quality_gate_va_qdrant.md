# Nhật Ký Làm Việc — Phiên #158
# Ngày: 2026-09-20 | Khép Kín Quality Gate, Làm Sạch Bảng PDF Và Bảo Vệ Qdrant

## Mục Tiêu

Đưa các lớp canonical normalization, kiểm định dữ liệu, record-aware chunking và structured facts vào runtime ingestion thực tế; ngăn dữ liệu sai, trùng hoặc mâu thuẫn đi vào Qdrant.

## Thay Đổi Kỹ Thuật

| Tệp | Thay đổi | Nội dung |
| :--- | :--- | :--- |
| `backend/app/modules/knowledge/normalization/table_reconstructor.py` | MODIFY | Nối các bảng PDF tiếp diễn thiếu header, loại cột spacer và loại trùng theo khóa nghiệp vụ. |
| `backend/app/modules/knowledge/normalization/quality_gate.py` | MODIFY | Chặn header vô danh, trùng bản ghi ngành/nhiệm vụ và mâu thuẫn chéo bảng. |
| `backend/app/modules/knowledge/services/ingestion_service.py` | MODIFY | Đưa Quality Gate, typed records, atomic chunks/facts vào ingest; chuyển lỗi blocking sang `review_pending`; tái tạo Facts từ Markdown đã hiệu đính. |
| `backend/app/modules/knowledge/services/reconciliation_service.py` | MODIFY | Không reindex tài liệu đang chờ hiệu đính; cho phép retry sau xác nhận `human_verified`. |
| `backend/app/modules/knowledge/facts.py` | MODIFY | Đọc GFM hợp lệ của cán bộ để tái tạo Facts mà không suy đoán bảng lỗi. |
| `backend/tests/test_table_reconstructor.py` | MODIFY | Bổ sung kiểm thử bảng tiếp nối và cột đệm. |
| `backend/tests/test_domain_records_and_quality_gate.py` | MODIFY | Kiểm thử chặn trước chunks/facts, sinh atomic chunks/facts và tái tạo Facts từ GFM đã xác nhận. |
| `docs/quy_trinh/02_nap_tri_thuc_minio.md` | MODIFY | Đồng bộ luồng kiểm định trước Qdrant và quy tắc phê duyệt có trách nhiệm. |

## Đối Chiếu Tài Liệu Gốc

- PDF Kế hoạch triển khai nhiệm vụ 2025–2026: 1 bảng đa trang đã tái dựng thành 7 cột, 88 hàng nguồn, chuẩn hóa thành 76 nhiệm vụ duy nhất; Quality Gate đạt.
- PDF Thông tin tuyển sinh 2026: 53 ngành được tái dựng đúng nhưng Quality Gate phát hiện mâu thuẫn mã ngành; không có chunks, facts hoặc Qdrant points được tạo cho tới khi cán bộ hiệu đính/xác nhận.

## Kiểm Thử

- `uv run ruff check .`: 0 lỗi.
- `uv run --extra dev pytest -v`: 322/322 passed trong 59.85 giây.
