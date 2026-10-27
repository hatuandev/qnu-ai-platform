# Phiên637 — Kho tri thức backendV1: collection và upload trực tiếp

Người dùng yêu cầu batch tiếp theo cho `backendV1`: kho tri thức theo workspace và upload tài liệu
trực tiếp vào collection, hoàn thành luồng kiểm chứng được
`xác thực → chọn workspace → tạo collection → upload → lưu nguồn/phiên bản → xem chi tiết → tải lại đúng file gốc`.
Phạm vi loại trừ OCR/parser/worker/chunk/embedding/index/publication/RAG/frontend; `backend/` chỉ đọc
làm tham chiếu nghiệp vụ và giữ nguyên mã/dữ liệu.

## Mô hình và chính sách đã chốt

- Bốn bảng v1-owned mới, tên `kb_*` để không đụng `knowledge_*` legacy:
  `kb_collections`, `kb_sources`, `kb_source_revisions`, `kb_upload_requests`.
- Quan hệ `workspace → collection → source → revision` kiểm ba lớp: `resolve_workspace_access`,
  filter workspace trong mọi truy vấn, và khóa ngoại tổ hợp ở DB.
- Bytes và metadata chứng cứ chỉ nằm trên revision; `kb_sources` chỉ giữ `latest_revision_no`.
- Dedupe: `(collection_id, sha256)` unique — cùng nội dung không vào một collection hai lần,
  kể cả hai request đồng thời. Không dedupe chéo workspace.
- Idempotency: `(workspace_id, actor_ref, idempotency_key)` unique + `request_hash`; cùng khóa
  cùng yêu cầu trả lại kết quả cũ (200), khác yêu cầu trả 409.
- Lưu trữ content-addressed `v1/workspaces/{ws}/collections/{col}/blobs/{sha[:2]}/{sha}`; tên tệp
  của client không quyết định object bị ghi. DB commit sau khi ghi blob; blob mồ côi chỉ có thể là
  object content-addressed mà lần thử lại sẽ ghi đè đúng cùng nội dung.

## Đã triển khai

- `knowledge/artifacts/files.py`: làm sạch tên tệp, chứng minh định dạng từ bytes (PDF magic,
  ZIP có `word/`/`xl/`, text UTF-8 không NUL), giới hạn kích thước khi đọc luồng, khóa lưu trữ,
  header `Content-Disposition` RFC 5987.
- `knowledge/policies/access.py`: `load_collection/load_source/load_revision` theo workspace và
  collection; sai phạm vi trả 404, không lộ tồn tại.
- `knowledge/collections/`: tạo, liệt kê phân trang, chi tiết, cập nhật metadata; tên unique trong
  workspace; audit qua `workspace_events`.
- `knowledge/sources/`: upload tạo nguồn, thêm phiên bản mới (khóa dòng nguồn), liệt kê, chi tiết,
  danh sách phiên bản, tải lại bytes gốc kèm kiểm tra checksum và `ETag`.
- `api/dependencies.get_blob_store` lấy adapter từ container; storage lỗi trả 503, thiếu blob trả
  502 `blob_missing`, blob bị sửa trả 502 `blob_integrity_failed` — không bao giờ trả file rỗng giả.
- Migration `0005_knowledge_collections`; `ownership.V1_TABLES` và `docs/migration-ownership.yaml`
  thêm 4 bảng; `alembic/env.py` import model knowledge.
- Thêm dependency `python-multipart` (bắt buộc cho multipart upload) và cập nhật `uv.lock`.

## Kiểm chứng thực chạy

| Kiểm tra | Kết quả |
|---|---|
| Unit toàn v1 (gồm 12 ca file intake mới) | **45 PASS**, exit0 |
| Focused knowledge + migration (PostgreSQL thật) | **33 PASS**, 18,90 giây, exit0 |
| Full backendV1 cuối qua harness cô lập | **104 PASS / 0 FAIL / 0 SKIP**, 32,49 giây, exit0 |
| Ruff toàn `backendV1/` | **PASS**, exit0 |
| Migration thật + ORM diff (`compare_metadata`) | **PASS**, không còn diff |
| Legacy sentinel/version trong DB test | Giữ nguyên; `db_dropped=true` |
| OpenAPI export | **PASS**, 31 path (thêm 6 path collection/source/revision) |

Lệnh cuối, cwd `backendV1`:

```
.venv\Scripts\python.exe -m ruff check .
.venv\Scripts\python.exe scripts/run_isolated_tests.py tests -q
```

Harness tạo DB loopback `qnu_v1_test_6ab100000863450c`, chạy `alembic upgrade head`, chạy pytest rồi
xóa đúng DB đó; receipt ghi `db_dropped=true`, `legacy_sentinel_preserved=true`, tổng 37,99 giây.
Lượt focused trước đó chạy cùng harness trên 4 file knowledge/migration và cũng đã dọn DB.
Hai warning deprecation của `TestClient`/`anyio`, không phải failure.

## Giới hạn

- Nguồn chỉ ở `stored`. Không có job, không có trạng thái `queued/processed/ready`, không progress.
- Chưa parse/OCR/chunk/embedding/index/publication/RAG/frontend; không tạo placeholder cho các phần này.
- `kb_sources.status` chỉ cho `stored`; thêm trạng thái xử lý phải kèm migration mới.
- Chưa chạy migration trên DB đang phục vụ và chưa bật API/worker v1; DB ứng dụng không bị đổi.
- Chưa có GC cho blob mồ côi khi một transaction DB thất bại sau khi đã ghi object; object đó
  content-addressed nên lần thử lại dùng lại đúng khóa, nhưng cần job đối soát ở batch vận hành.

## Bước tiếp theo

Nối Jobs/worker ingestion sau `source_service.upload`, thêm trạng thái xử lý có migration, rồi mới
tới parser/OCR qua ModelOps. Trước đó cần quyết định có cho phép revert nội dung cũ thành phiên bản
mới hay giữ chính sách "trùng nội dung là 409" như hiện tại.
