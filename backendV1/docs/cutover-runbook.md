# Runbook cutover (từng bước, có rollback)

1. Kiểm `docs/PORT_BASELINE.sha256` → `python scripts/verify_port_baseline.py` PASS.
2. So OpenAPI: `python scripts/export_openapi.py` rồi `oasdiff` với `backend/` (phạm vi đã duyệt).
3. Chạy parity harness: legacy `:8001` vs v1 `:8002`, cùng token, cùng request corpus.
4. Bật nginx location cho **một** prefix duy nhất, chỉ GET.
5. Theo dõi `/health/ready`, tỷ lệ 5xx, độ trễ p95 trong 24h.
6. Rollback: xoá location nginx (1 dòng) — không cần restart backend.

Điều kiện dừng: bất kỳ diff không giải thích được, hoặc p95 tăng > 20%.
