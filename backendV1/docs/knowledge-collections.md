# Kho tri thức v1 — collection, nguồn và phiên bản file

Từ Context710, upload PDF/DOCX mặc định ghi thêm yêu cầu bóc tách native-first
trong cùng transaction, rồi giao worker sau commit. Tệp gốc vẫn `stored`; trạng
thái nằm trong `source.processing`. Có thể gửi `auto_extract=false` để chỉ lưu.
Xem [quy trình43](../../docs/quy_trinh/43_boc_tach_tu_dong_backend_v1.md).
Phần intake bên dưới mô tả nền lưu tệp; các ghi chú “chưa OCR/job” là phạm vi
batch khởi tạo trước khi nối luồng tự động, không phải hiện trạng Context710.

Prefix: `/platform/v1alpha1`. DTO/router thực tế là nguồn OpenAPI; bản xuất tại
[openapi-v1.json](openapi-v1.json).

Batch này chỉ **lưu tệp**. Không parse, không OCR, không tạo job, không index và không
xuất bản tri thức. Trạng thái nguồn duy nhất là `stored`; không có tiến trình giả.

## Mô hình dữ liệu

| Bảng | Vai trò | Khóa/ràng buộc chính |
|---|---|---|
| `kb_collections` | Kho tri thức thuộc một workspace | `(workspace_id, name)` unique; `(id, workspace_id)` unique làm đích FK |
| `kb_sources` | Nguồn logic (một tài liệu) | FK tổ hợp `(collection_id, workspace_id)`; `latest_revision_no` |
| `kb_source_revisions` | Phiên bản file bất biến | FK tổ hợp `(source_id, collection_id, workspace_id)`; `(source_id, revision_no)` unique; `(collection_id, sha256)` unique |
| `kb_upload_requests` | Sổ idempotency của upload | `(workspace_id, actor_ref, idempotency_key)` unique |

Quan hệ `workspace → collection → source → revision` được kiểm ở cả ba lớp: resolver
quyền, filter trong service, và khóa ngoại tổ hợp ở DB. Một `source_id` của đơn vị khác
trả 404, không phải 403.

Bytes và metadata chứng cứ (tên tệp, `content_type`, `size_bytes`, `sha256`,
`storage_key`) chỉ nằm trên revision. `kb_sources` không giữ bản sao để tránh lệch.

## Chính sách nội dung và phiên bản

- **Content-addressed**: khóa lưu trữ là
  `v1/workspaces/{ws}/collections/{col}/blobs/{sha[:2]}/{sha}`. Tên tệp của client
  không bao giờ quyết định object nào bị ghi đè.
- **Ghi local an toàn**: ghi đầy đủ vào file tạm cùng thư mục, đóng file rồi
  `os.replace` để xuất bản nguyên vẹn. Lỗi ghi giữa chừng không cắt file đã commit;
  file tạm được dọn khi thao tác kết thúc. Nếu Windows từ chối đổi tên khi có writer
  đồng thời, chỉ chấp nhận thành công khi đọc lại file đích có bytes khớp hoàn toàn.
  Kiểm tra phạm vi đường dẫn dùng quan hệ thư mục, có chuẩn hóa tiền tố đường dẫn dài
  Windows; không dùng so sánh chuỗi tiền tố. Đây không phải bảo đảm trước mất điện.
- **Dedupe trong collection**: `(collection_id, sha256)` unique. Upload lại đúng nội dung
  vào cùng collection trả `409 duplicate_content` (kèm id nguồn đang giữ nội dung, trong
  cùng workspace). Thêm phiên bản trùng nội dung hiện tại trả `409 revision_unchanged`.
- **Không dedupe chéo workspace**: cùng nội dung ở đơn vị khác là object khác; không tiết
  lộ và không tái dùng quyền của đơn vị đó.
- **Phiên bản bất biến**: revision cũ không bị sửa; thêm phiên bản chỉ tăng
  `latest_revision_no` dưới khóa `FOR UPDATE` trên dòng nguồn.

## Idempotency

Header `Idempotency-Key` (8–128 ký tự, tùy chọn). Khóa được scope theo
`(workspace, actor_ref, key)`.

- Cùng khóa + cùng yêu cầu → trả lại đúng nguồn/phiên bản đã tạo, HTTP `200`.
- Cùng khóa + yêu cầu khác → `409 idempotency_conflict`.
- Đua đồng thời: cả hai request cùng ghi; DB unique quyết định người thắng, người thua
  rollback rồi đọc lại sổ idempotency và replay.

Fingerprint mới là SHA-256 của JSON chuẩn hóa (khóa sắp xếp, không khoảng trắng),
gồm `version=2`, workspace, collection, source, tên tệp đã làm sạch, sha256,
kích thước và **title hiệu lực**. Title được trim, mặc định bằng tên tệp khi rỗng,
giới hạn 255 ký tự như dữ liệu lưu; các cách biểu diễn cùng title hiệu lực replay
được. Cùng key/file nhưng đổi title hiệu lực trả `409 idempotency_conflict`.

Sổ upload cũ vẫn replay khi fingerprint cũ khớp và title hiệu lực khớp title đã
lưu trên nguồn; không viết lại sổ cũ. Endpoint thêm revision chỉ nhận file, không
thay title nguồn: gửi trường `title` trả `422 revision_title_not_supported`.

## Quyền

| Hành động | admin | editor | reviewer | member |
|---|---|---|---|---|
| Đọc collection/nguồn/tải tệp | ✓ | ✓ | ✓ | ✓ |
| Tạo/sửa collection, upload, thêm phiên bản | ✓ | ✓ | — | — |

Platform admin đi qua resolver như mọi actor khác. Workspace `suspended` chặn toàn bộ
nội dung (403). `created_by` lấy từ actor đã xác thực; body/header không có tác dụng.

## Định dạng và giới hạn

- Hỗ trợ `.pdf`, `.docx`, `.xlsx`, `.txt`, `.md`; kiểm tra chữ ký thật của bytes, không
  tin `Content-Type` của client.
- Giới hạn `MAX_UPLOAD_BYTES` (mặc định 60 MB), đọc theo luồng và cắt ngay khi vượt. Lưu ý: Starlette
  spool phần body vào file tạm trước khi handler chạy, nên môi trường thật cần thêm giới hạn body ở
  reverse proxy; đây là giới hạn nghiệp vụ, không phải chặn ở tầng mạng.
- Tên tệp được làm sạch (bỏ đường dẫn, ký tự điều khiển), lưu tên hiển thị; tên tệp
  không tham gia khóa lưu trữ.
- Tải xuống trả `Content-Disposition: attachment; filename*=UTF-8''…`,
  `ETag` = sha256 và kiểm tra lại checksum trước khi trả bytes.

## Luồng API

```bash
BASE=http://127.0.0.1:8002/platform/v1alpha1
WS=ws_xxx

# 1. Tạo collection (admin/editor)
curl -X POST "$BASE/workspaces/$WS/collections" \
  -H 'Content-Type: application/json' \
  -d '{"name":"Tuyển sinh 2026","description":"Đề án và điểm chuẩn"}'

# 2. Liệt kê có phân trang
curl "$BASE/workspaces/$WS/collections?page=1&page_size=20"

# 3. Upload trực tiếp vào collection
curl -X POST "$BASE/workspaces/$WS/collections/col_xxx/sources" \
  -H "Idempotency-Key: upload-2026-0001" \
  -F 'file=@de-an-2026.pdf' -F 'title=Đề án tuyển sinh 2026'

# 4. Xem nguồn và danh sách phiên bản
curl "$BASE/workspaces/$WS/collections/col_xxx/sources/src_xxx"
curl "$BASE/workspaces/$WS/collections/col_xxx/sources/src_xxx/revisions"

# 5. Thêm phiên bản mới (không ghi đè bản cũ)
curl -X POST "$BASE/workspaces/$WS/collections/col_xxx/sources/src_xxx/revisions" \
  -F 'file=@de-an-2026-v2.pdf'

# 6. Tải lại đúng tệp gốc của một phiên bản
curl -OJ "$BASE/workspaces/$WS/collections/col_xxx/sources/src_xxx/revisions/rev_xxx/content"
```

| Nhóm | Endpoint |
|---|---|
| Collection | `POST/GET /workspaces/{ws}/collections`; `GET/PATCH /workspaces/{ws}/collections/{id}` |
| Nguồn | `POST/GET /workspaces/{ws}/collections/{id}/sources`; `GET .../sources/{source_id}` |
| Phiên bản | `GET/POST .../sources/{source_id}/revisions` |
| Tệp gốc | `GET .../sources/{source_id}/revisions/{revision_id}/content` |

## Kiểm thử

Từ `backendV1`:

```powershell
.venv\Scripts\python.exe scripts/run_isolated_tests.py tests -q
```

Harness tạo database loopback `qnu_v1_test_*`, chạy `alembic upgrade head`, chạy pytest
rồi xóa đúng database đó; không sao chép dữ liệu ứng dụng. Không có `TEST_DATABASE_URL`
thì test tích hợp báo SKIP (NOT RUN), không phải PASS.

Ca chính: upload rồi tải lại cùng sha256/bytes; thêm phiên bản vẫn tải được bản cũ; thiếu
xác thực/thiếu role/membership thu hồi/workspace suspended bị chặn; đổi
workspace/collection/source/revision id không truy cập được tài nguyên đơn vị khác;
không giả mạo `created_by`; trùng nội dung và idempotency (kể cả đồng thời); lỗi
DB/storage không trả thành công giả; migration khớp ORM.

Baseline `0001_initial_schema` từ chối downgrade tường minh để giữ chứng cứ.
Lệnh thất bại trước khi version đổi; upgrade head tiếp theo vẫn chạy được và file
gốc vẫn đọc được. Muốn rollback cần kế hoạch bảo toàn dữ liệu riêng, không dùng
downgrade rỗng hoặc xóa bảng chứng cứ.

## Điểm nối cho batch sau

- `KBSource.status` hiện chỉ cho `stored`; thêm trạng thái xử lý phải kèm migration.
- `source_service.upload` là điểm vào duy nhất để enqueue job parse/OCR sau khi có worker;
  chưa có job, chưa có progress.
- `knowledge/policies/access.py` là nơi thêm kiểm tra quyền mịn hơn (theo collection) nếu
  nghiệp vụ yêu cầu.
