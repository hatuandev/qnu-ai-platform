# Nhật Ký Phiên #299 — Hardening Quy Trình Kho Tài Liệu → Kho Tri Thức V2

- **Thời gian**: 2026-10-08
- **Mục tiêu**: Rà soát độc lập toàn bộ 12 phiên triển khai Kế hoạch 11, sửa các sai lệch giữa thiết kế ADR-011 và code thực tế, sau đó xác minh lại toàn hệ thống.
- **Phạm vi**: Backend FastAPI/PostgreSQL/Qdrant/Redis/ARQ, Hybrid RAG, ModelOps, OCR layout, frontend React/TypeScript và migration Alembic.

---

## 1. Kết Quả Chính

1. **Vòng đời tài liệu và kiểm soát đồng thời**
   - Tách đúng thời điểm tiếp nhận revision khỏi thời điểm đưa revision thành bản hiện hành; chỉ bản vượt Quality Gate hoặc được cán bộ duyệt mới được promote.
   - Bổ sung Compare-and-Swap bằng `expected_lock_version` cho hiệu đính và thẩm định revision.
   - Chuẩn hóa trạng thái revision, lỗi Quality Gate và dữ liệu provenance; loại bỏ việc cập nhật nhầm tài liệu hiện hành khi revision mới còn đang xử lý.

2. **Job outbox và tính idempotent**
   - Lưu job trước khi phát sang ARQ, dùng broker job ID xác định, request hash và idempotency key theo tenant/workspace.
   - Bổ sung trạng thái dispatch, heartbeat, attempt, cancellation hợp tác và tác vụ reconciliation cho job chưa phát thành công.
   - Worker không còn nuốt lỗi ingestion/indexing; lỗi thật được đẩy về trạng thái thất bại để retry/failover đúng cơ chế.

3. **Xuất bản tri thức và cô lập tenant**
   - Tất cả truy vấn binding/document/revision/chunk được ràng buộc theo tenant, workspace, collection và binding.
   - Parity Gate kiểm tra chính xác số point, ID và content hash giữa PostgreSQL và Qdrant; loại bỏ mọi nhánh pass giả theo môi trường test.
   - Activation/rollback dùng đúng `index_revision_id`, kiểm tra epoch CAS và cập nhật con trỏ phục vụ theo snapshot nhất quán.
   - Vector Generation được phân giải động từ ModelOps; khi cấu hình embedding đổi, hệ thống yêu cầu migration thay vì trộn vector khác không gian.

4. **RAG snapshot, cache và chống rò phiên bản**
   - `RetrievalSnapshot` pin chính xác active binding/index/source revision và được kiểm tra tenant/workspace.
   - Dense, sparse, facts và neighbor expansion cùng dùng một snapshot; không còn đọc lẫn revision legacy hoặc revision chưa active.
   - Cache key mang collection epoch và snapshot fingerprint; invalidation dùng `SCAN`, không dùng lệnh `KEYS` chặn Redis.
   - Fact Layer lọc theo bất biến hình thái/cụm danh từ hoặc mã định danh, không bổ sung từ điển hardcode.

5. **Canary, backfill và garbage collection**
   - Backfill dựng lại canonical Markdown thật rồi chạy staging build, parity và promote; không gắn nhãn V2 giả cho dữ liệu legacy.
   - Shadow retrieval tách rõ chế độ legacy và revisioned.
   - Garbage collection xóa chính xác point Qdrant trước, xác minh kết quả rồi mới xóa artifact PostgreSQL; bảo toàn rollback window.

6. **ModelOps, OCR và frontend contracts**
   - Reranker và embedding không còn model/endpoint hardcode trong runtime; cấu hình được truyền từ ModelOps.
   - Layout detector dùng nhận diện marker danh sách theo cấu trúc cú pháp/hình thái, không vá bằng danh sách từ vựng.
   - Bổ sung `opencv-python-headless` vào dependency chính thức.
   - Frontend gửi đúng `expected_lock_version`/`expected_epoch`, dùng đúng các trường `canonical_markdown`, `parse_provenance`, `quality_report` và xác định revision hiện hành từ `current_revision_id`.

---

## 2. Nhóm Tệp Thay Đổi

- **Documents & jobs**: `backend/app/modules/documents/`, `backend/app/modules/jobs/`, `backend/app/workers/`.
- **Knowledge publishing & RAG**: `backend/app/modules/knowledge/`, `backend/app/modules/rag/`.
- **Workflow & assistants**: `backend/app/modules/workflows/nodes/rag_answer_node.py`, `backend/app/modules/assistants/services/assistant_chat_service.py`.
- **ModelOps & OCR**: `backend/app/modules/modelops/`, `backend/app/modules/ocr/layout_detector.py`, `backend/pyproject.toml`, `backend/uv.lock`.
- **Database**: `backend/alembic/versions/20261007_document_revisions.py`, `20261007_knowledge_publishing_v2.py`, `20261008_publishing_v2_hardening.py`.
- **Frontend**: API/types và các trang chi tiết trong `frontend/src/features/documents/` và `frontend/src/features/knowledge/`.
- **Tests**: các suite documents, jobs, publishing V2, retrieval/RAG, workflows, OCR layout và export.
- **Tooling cũ**: chuẩn hóa import, I/O bất đồng bộ và lỗi lint trong các script chẩn đoán/scratch để toàn repository đạt Ruff sạch.

---

## 3. Kết Quả Xác Minh

- **Backend test suite**: `598 passed, 1 skipped, 1 warning` trong 26.97 giây.
  - Test bị skip là kiểm thử tích hợp thật `test_admissions_agentic_flow.py`; chỉ chạy khi đặt `QNU_RUN_LIVE_INTEGRATION=1` và có PostgreSQL, ModelOps provider cùng dữ liệu tuyển sinh V2 thực tế.
  - Cảnh báo còn lại đến từ SQLAlchemy về `datetime.utcnow()` trong dependency nội bộ của schema test, không phải lỗi chức năng.
- **Backend Ruff toàn repository**: `All checks passed!` — 0 lỗi.
- **Alembic**: một head duy nhất `20261008_publishing_v2_hardening`.
- **Frontend**: `npm run build` thành công — Vite build và TypeScript `tsc --noEmit` đều đạt.

---

## 4. Quyết Định Kiến Trúc & Bài Học

- Bản tài liệu mới chưa vượt Quality Gate không được làm thay đổi bản đang phục vụ.
- Mọi thao tác promote/rollback/review phải có CAS; ID nghiệp vụ không được thay thế bằng số revision hiển thị.
- Không gian vector là bất biến theo generation; đổi model/dimension phải tạo generation mới và migration có kiểm soát.
- Snapshot là biên nhất quán duy nhất của một lượt RAG; mọi retriever con và cache phải mang cùng fingerprint.
- Không dùng test shortcut, dữ liệu giả hay adapter fallback giả để biến lỗi hạ tầng thành kết quả thành công.
- Script chẩn đoán vẫn là một phần chất lượng repository: phải sạch lint và không chặn event loop khi thực hiện I/O.
