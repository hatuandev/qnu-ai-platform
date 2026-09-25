# NHẬT KÝ LÀM VIỆC — PHIÊN #223
**Ngày**: 2026-09-25 | **Thời gian**: 23:55 (UTC+7)
**Tiêu đề**: Thêm start_period 180s Cho Backend Healthcheck Dokploy

---

## 1. Bối Cảnh
- Sau fix README (#222), cả 3 images build xong nhưng `qnu_backend is unhealthy` → worker/frontend bị chặn (`depends_on: service_healthy`).
- Chuỗi boot: `entrypoint.sh` (migrate → seed `--all` → uvicorn 4 workers) + lifespan `_verify_db_schema()` fail-fast ở production.
- Healthcheck cũ không có grace period (5 retries × 15s ≈ 75–90s) trong khi boot lạnh (migrate, seed 5 trợ lý/DAG/taxonomy, verify Qdrant/MinIO, import torch × 4 workers) dễ vượt quá → Docker kết luận unhealthy khi app còn đang boot.

## 2. Thay Đổi
- `docker-compose.yml`: thêm `start_period: 180s` cho healthcheck backend.
- Verify: YAML parse hợp lệ, diff đúng 1 dòng.
- Chưa loại trừ nghi phạm hạ tầng ngoài (postgres/redis/qdrant/minio qua hostname) — cần `docker logs qnu_backend` nếu vẫn unhealthy sau redeploy.
