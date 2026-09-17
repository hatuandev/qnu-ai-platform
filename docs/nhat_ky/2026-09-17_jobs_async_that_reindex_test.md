# Nhật Ký Làm Việc — 17/09/2026

## Tiêu đề: Jobs Async Thật — Module Jobs, Tasks ARQ Thật, Reindex/Test, Collection PUT/DELETE (Việc 4/5)

### 1. Bối cảnh
3 task ARQ cũ toàn stub trả số cứng (`indexed_chunks: 42`), FE `getIngestionTasks` mock thuần, thiếu reindex/test retrieval và collection update/delete. Mục tiêu: jobs có record DB, worker thật, cooperative cancel.

### 2. Các Thay Đổi Kỹ Thuật Đã Thực Hiện
**Backend:**
1. Module mới `app/modules/jobs/` (4 files chuẩn): `JobRecord` (queued/running/completed/failed/cancelled + progress/payload/result/error), service enqueue (ghi DB + dispatch ARQ, worker offline thì giữ `queued` trung thực), cancel (cooperative), retry (chỉ failed/cancelled), stats; router 6 endpoints mount tại `/platform/v1alpha1/jobs`; `__init__` model có defaults eager để object hợp lệ trước flush.
2. `app/workers/tasks.py` viết lại thật: `task_document_ingestion` (nạp bytes từ storage → prepare → thay chunks/facts → pending, checkpoint cancel 2 điểm), `task_reindex_collection` (embed + upsert uuid5 thật), `task_export_document` (render `.docx` thật bằng python-docx vào storage).
3. `knowledge/service.py`: tách `prepare_ingestion` + `persist_chunks_facts` + `replace_document_content` dùng chung cho upload sync và task nền (hành vi cũ giữ nguyên); thêm `update_collection`/`delete_collection`.
4. `knowledge/router.py`: thêm `PUT`/`DELETE /collections/{id}`, `POST /collections/{id}/reindex` (enqueue job), `POST /collections/{id}/test` (hybrid retrieval thật, không ghi DB).

**Frontend:**
5. `getIngestionTasks` gọi `GET /jobs` map sang `IngestionTask` (tên việc, trạng thái, tiến độ, thời lượng từ timestamps, log từ error/result); chỉ fallback mock khi backend unreachable.

**Tests:** viết lại `test_workers.py` (5 tests với DB mock: happy/cancel/missing/docx-PK-bytes) + mới `test_jobs.py` (10 tests: unknown-type-400, enqueue online/offline, cancel terminal-409, retry, 404, stats, API enqueue). Trong lúc làm phát hiện `JobRecord` cần defaults eager (mock flush không populate) và 5 lỗi ruff unused (đã dọn).

### 3. Kết Quả Kiểm Thử (Verification)
- `uv run ruff check .`: 0 lỗi.
- `uv run --extra dev pytest -q`: **105/105 passed** (93 cũ + 12 mới).
- FE: biome lint 0, typecheck 0, build ✓ (6.05s); Playwright Suite 09: **4/4 passed**.
