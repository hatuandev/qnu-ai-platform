# Context637 — Kho tri thức backendV1: collection và upload trực tiếp

Yêu cầu: batch tiếp theo cho `backendV1` — kho tri thức theo workspace, upload tài liệu trực tiếp vào
collection, hoàn thành luồng `xác thực → chọn workspace → tạo collection → upload → lưu nguồn/phiên bản
→ xem chi tiết → tải lại đúng file gốc`. Loại trừ OCR/parser/worker/chunk/embedding/index/publication/
RAG/frontend. `backend/` chỉ đọc tham chiếu, giữ nguyên mã và dữ liệu.

## Kết quả

- Bốn bảng v1-owned mới với tiền tố `kb_` để không đụng `knowledge_*` legacy: `kb_collections`,
  `kb_sources`, `kb_source_revisions`, `kb_upload_requests`. Quan hệ workspace → collection → source →
  revision được giữ bằng khóa ngoại tổ hợp, nên một revision không thể trỏ sang collection/đơn vị khác
  ngay cả khi service bị lỗi.
- Collection: tạo, liệt kê phân trang, chi tiết, cập nhật metadata. Tên unique trong workspace; admin/editor
  được ghi, reviewer/member chỉ đọc; mọi thao tác qua `resolve_workspace_access` và ghi audit
  `collection.created/updated` vào `workspace_events`.
- Nguồn: upload tạo nguồn mới hoặc thêm phiên bản cho nguồn đã có; liệt kê, chi tiết, danh sách phiên bản;
  tải lại đúng bytes gốc. `created_by` lấy từ actor đã xác thực, body/header không có tác dụng.
- Chính sách: bytes và metadata chứng cứ chỉ nằm trên revision (bất biến); `kb_sources` chỉ giữ
  `latest_revision_no`. Dedupe `(collection_id, sha256)` chặn cùng nội dung vào một collection hai lần,
  kể cả hai request đồng thời; không dedupe chéo workspace và không tiết lộ nguồn của đơn vị khác.
- Idempotency `(workspace_id, actor_ref, idempotency_key)` + `request_hash`: cùng khóa cùng yêu cầu trả lại
  đúng nguồn/phiên bản (HTTP 200), khác yêu cầu trả 409. Request thua trong đua đồng thời rollback rồi đọc
  lại sổ và replay.
- Storage: `BlobStore` hiện có (local/S3), khóa content-addressed
  `v1/workspaces/{ws}/collections/{col}/blobs/{sha[:2]}/{sha}`; tên tệp client không quyết định object bị ghi.
  DB commit sau khi ghi blob; blob mồ côi chỉ có thể là object content-addressed mà lần thử lại ghi đè đúng
  cùng nội dung. Tải xuống kiểm lại checksum trước khi trả bytes.
- Lỗi trung thực: storage hỏng → 503 `storage_unavailable` và không tạo nguồn; thiếu blob → 502 `blob_missing`;
  blob bị sửa → 502 `blob_integrity_failed`. Không có nhánh nào trả file rỗng hay "thành công giả".
- Định dạng: `.pdf/.docx/.xlsx/.txt/.md`, chứng minh bằng chữ ký bytes (PDF magic, ZIP có `word/`/`xl/`,
  text UTF-8 không NUL); giới hạn `MAX_UPLOAD_BYTES` đọc theo luồng; tên tệp được làm sạch.
- Migration `0005_knowledge_collections`; `ownership.V1_TABLES` và `docs/migration-ownership.yaml` thêm 4 bảng;
  `alembic/env.py` import model knowledge. Thêm `python-multipart` (bắt buộc cho multipart) và cập nhật lock.
- OpenAPI xuất lại: 31 path, thêm 6 path collection/source/revision.

## Kiểm chứng thật

| Kiểm tra | Kết quả |
|---|---|
| Unit toàn v1 (gồm 12 ca file intake mới) | **45 PASS**, exit0 |
| Focused knowledge + migration, PostgreSQL thật | **33 PASS**, 18,90 giây, exit0 |
| Full backendV1 cuối, harness cô lập | **104 PASS / 0 FAIL / 0 SKIP**, 32,49 giây, exit0 |
| Ruff toàn `backendV1/` | **PASS**, exit0 |
| Migration thật + ORM diff | **PASS**, không còn schema diff |
| Legacy sentinel + `alembic_version` trong DB test | Giữ nguyên |
| OpenAPI export | **PASS**, 31 path |
| DB test dọn sau lượt chạy | `db_dropped=true`; không còn `qnu_v1_test_*` |

Lệnh cuối, cwd `backendV1`:

```
.venv\Scripts\python.exe -m ruff check .
.venv\Scripts\python.exe scripts/run_isolated_tests.py tests -q
```

Harness tạo database loopback `qnu_v1_test_6ab100000863450c`, chạy `alembic upgrade head`, chạy pytest rồi
xóa đúng database đó; receipt `db_dropped=true`, `legacy_sentinel_preserved=true`, tổng 37,99 giây.
Lượt focused chạy cùng harness trên 4 file knowledge/migration và cũng đã dọn DB.

Số test khớp: 60 ca của batch636 + 44 ca mới (10 collection, 15 nguồn, 7 đồng thời/idempotency, 12 file
intake) = 104. Hai warning deprecation `TestClient`/`anyio` không phải failure.

## Giới hạn

- Nguồn chỉ ở `stored`. Không job, không `queued/processed/ready`, không progress; không có placeholder
  cho parse/OCR/chunk/embedding/index/publication/RAG.
- `kb_sources.status` mới chỉ cho `stored`; thêm trạng thái xử lý phải kèm migration mới.
- Chưa áp migration v1 lên database đang phục vụ; DB ứng dụng không đổi. Không restart API/worker v1.
- Chưa có GC/đối soát cho blob mồ côi khi transaction DB thất bại sau khi đã ghi object; cần job vận hành
  ở batch sau. Chưa có quota dung lượng theo workspace.
- Giới hạn upload là giới hạn nghiệp vụ ở handler; Starlette vẫn spool body vào file tạm trước đó, nên
  môi trường thật cần giới hạn body ở reverse proxy.
- Chính sách hiện tại coi "nội dung trùng" là 409, nên chưa hỗ trợ revert nội dung cũ thành phiên bản mới;
  nếu nghiệp vụ cần, phải nới ràng buộc `(collection_id, sha256)` bằng migration có chủ đích.
- `backendV1/` vẫn là thư mục chưa được Git theo dõi; batch này không commit/push.
- Artifact/log của harness ghi vào `backendV1/storage/context636/` (đường dẫn cố định của harness), đã Git ignore.

## Điểm nối batch sau

- `source_service.upload` là điểm duy nhất để enqueue job ingestion sau khi có worker.
- Trạng thái xử lý phải là cột + migration, không suy từ sự tồn tại của file.
- `knowledge/policies/access.py` là nơi thêm kiểm tra quyền mịn hơn (theo collection) nếu nghiệp vụ cần.
- Cần job đối soát blob mồ côi trước khi bật upload dung lượng lớn trên môi trường thật.

[API và luồng dùng](../../../backendV1/docs/knowledge-collections.md). [Kết quả JSON](result.json).
