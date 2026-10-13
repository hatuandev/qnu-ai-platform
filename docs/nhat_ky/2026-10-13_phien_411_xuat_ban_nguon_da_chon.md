# Phiên #411 — Xuất bản nguồn đã chọn

## Mục tiêu và giải thích

Người dùng đồng ý xuất bản linh hoạt một/vài tài liệu mà không yêu cầu duyệt, nạp toàn kho; đồng thời hỏi về đổi model embedding. Model embedding là model chuyển văn bản thành vector tìm kiếm, khác model chat. Đổi embedding cần generation riêng vì vector spaces khác nhau; phải chuyển đủ các nguồn đang phục vụ để không làm mất chúng, nhưng không bắt buộc các tài liệu chưa xuất bản tham gia. Luồng sử dụng Markdown đã lưu, không OCR lại.

## Triển khai

- Thêm DTO `PublishVectorItem` pin exact binding/source/index IDs và request chọn 1–500 nguồn.
- Endpoint `publish-selected` riêng giữ tương thích `/activate` toàn generation và rollback cũ.
- Service giới hạn collection/tenant/workspace/active sources; chống duplicate, stale source/index, review-required, parity chưa đạt và generation retired.
- Chỉ kiểm tra review/fact parity trên tập chọn; nguồn không chọn đang serving giữ nguyên pointers/epoch, nguồn chưa nạp không được xuất bản.
- Generation đầu tiên cho phép partial. Cùng generation cho phép thêm/cập nhật incremental. Chuyển generation chỉ được khi chọn đủ tất cả nguồn đang serving; tài liệu chưa publish có thể để sau.
- Release transaction trước Qdrant I/O; sau remote activation khóa collection/bindings, kiểm epoch, source/pointer fingerprint, generation và review state; commit pointers/audit atomically. Remote fail/CAS conflict giữ serving state; giữ old artifacts cho in-flight snapshots.
- Retry đúng tập đã active trả idempotent epoch, không tạo thêm audit.
- FE truyền exact selected indexes, enable nút theo targets thay vì toàn kho; confirmation nêu số nguồn và phạm vi, dùng Dialog/Button có sẵn.
- Candidate preview dùng selected snapshot hợp nhất targets với nguồn đang phục vụ; reset kết quả khi selected index IDs đổi.
- Worker không cần thay đổi vì vector-load đã xử lý theo nguồn chọn.

## Tệp chính

- `backend/app/modules/knowledge/services/selected_vector_publish.py`
- `backend/app/modules/knowledge/services/generation_candidate.py`
- `backend/app/modules/knowledge/{schemas.py,router.py}`
- `backend/tests/test_selected_vector_publish.py`
- `backend/tests/test_selected_publish_postgres.py`
- `frontend/src/features/knowledge/components/{vector-load-controls.tsx,candidate-rag-preview.tsx}`
- `frontend/src/features/knowledge/utils/{vector-workflow.ts,vector-workflow.test.ts}`
- `frontend/src/{services/knowledge-api.ts,types/knowledge.ts}`

## Kiểm chứng

- Backend focused ban đầu 21 passed; thêm ca đổi generation đủ serving sources cuối: module selected `12 passed`.
- PostgreSQL thật: publish nguồn1, rồi nguồn2, expire/reload ORM pointers vẫn giữ cả hai, nguồn3 chưa nạp không publish, snapshot1 giữ nguyên, snapshot2 đọc cả hai; retry epoch/audit không tăng. Qdrant remote mocked trong ca DB này; transaction outer rollback toàn bộ fixture, không thay dữ liệu người dùng.
- FE utility `8 passed`: partial bỏ qua nguồn không chọn chưa review/index, bảo vệ nguồn serving khi chuyển model và stale/review gate.
- Ruff toàn backend đạt, Biome6files đạt, Vite+TypeScript build đạt.
- Full backend chạy trước ca đổi generation bổ sung: `1001 passed, 11 failed, 9 errors, 4 skipped`; failure/error cùng baseline từ phiên409 (temp Windows, permissions/role, consulting/exporter/reconciliation). Ca bổ sung chạy riêng đã đạt.
- Runtime OpenAPI có endpoint mới; probe nonexistent source trả RFC7807 `SOURCE_NOT_FOUND` 404 nhanh, không publish tài liệu thật.

## Giới hạn

Đã kiểm server state/persistence/snapshot và FE build; chưa thực hiện toàn bộ UI partial publish bằng trình duyệt hoặc chạy lại embedding/Qdrant trên fixture mới. Các kiểm tra Qdrant activation/count có sẵn được giữ nguyên. Không tự xuất bản hay đổi model của kho thật trong phiên này.
