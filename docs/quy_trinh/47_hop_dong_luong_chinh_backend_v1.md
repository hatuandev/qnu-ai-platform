# 47 — Hợp đồng luồng chính backend V1 cho FE mới

Tài liệu này chốt các API mà frontend mới dùng cho luồng người dùng thường:

**Tải tài liệu → Chuẩn bị nội dung → Xem và chỉnh sửa → Duyệt và phát hành → Sẵn sàng cho trợ lý**.

Người dùng thường **không chọn** công cụ OCR, model/context/output, chunking hay thế hệ chỉ mục.
Backend tự chọn theo loại tài liệu, cấu hình ModelOps được phép và trạng thái dữ liệu thật. Các API
từng bước (compiler, review, index thủ công, OCR run) vẫn tồn tại cho quản trị/tích hợp nhưng không
thuộc luồng này.

Mọi đường dẫn dưới đây nằm dưới `/platform/v1alpha1/workspaces/{workspace_id}/collections/{collection_id}`.
Mọi thao tác đều kiểm quyền workspace ở server; `workspace_id`/`collection_id` trên URL chỉ là đối
tượng cần kiểm tra, không phải bằng chứng quyền.

## 1. Tải tài liệu

`POST /sources` — multipart, quyền admin/editor.

- Trường: `file` (bắt buộc), `title` (tùy chọn), `folder_id` (tùy chọn).
- Giữ `auto_extract=true` (mặc định). Không cần chọn OCR hay parser.
- Header `Idempotency-Key` tùy chọn cho retry mạng.
- Kết quả: `source` (id, status, revision hiện tại, `processing`) và `revision` (id, số, sha256).

Không cần chờ bóc tách xong mới được chuẩn bị: bước 2 tự chờ OCR nếu cần. Nếu muốn hiển thị tiến
trình, đọc `GET /sources/{source_id}` hoặc `GET /sources/{source_id}/summary`.

## 2. Chuẩn bị nội dung

`POST /sources/{source_id}/preparation-intents` — header `Idempotency-Key` bắt buộc.

Body tối giản:

```json
{}
```

- `mode` mặc định `auto`. Server chọn policy theo cấu hình được phép; caller **không gửi**
  `provider_id`, `max_output_tokens` hay cờ compiler trong luồng này.
- Có thể gửi `topic` nếu người dùng đặt tiêu đề chủ đề; bỏ trống thì lấy tiêu đề nguồn.
- Nếu người dùng đã sửa bản văn bản OCR và chọn đúng bản đó, gửi `ocr_run_id` + `text_version`
  (đây là lựa chọn nội dung, không phải lựa chọn kỹ thuật).
- Kết quả: `201` (mới) hoặc `200` (replay cùng khóa) với `intent`; lưu `intent.id`.
  `intent.policy` giải thích an toàn policy đã ghim (`supplement`, `reason`), không chứa credential.

Theo dõi `GET /preparation-intents/{intent_id}` (poll có backoff, dừng khi terminal):

| status | Ý nghĩa cho UI |
| :--- | :--- |
| `queued`, `waiting_ocr`, `compiling` | Đang chạy; hiển thị tiến trình trung thực, không giả %. |
| `ready` | Xong; dùng `compilation_run_id` cho bước 3. |
| `failed` | Đọc `error_code` và thông điệp; cho phép thử lại bằng khóa mới sau khi xử lý. |
| `uncertain` | Không chắc kết quả; không tự coi là xong, cho phép hủy/thử lại theo hướng dẫn. |
| `cancelled` | Người dùng đã hủy. |

Hủy: `POST /preparation-intents/{intent_id}/cancel`. Danh sách gần nhất:
`GET /sources/{source_id}/preparation-intents?limit=20`.

Lỗi cần hiển thị nguyên mã: thiếu cấu hình chat tùy chọn không làm hỏng luồng (policy chuyển
source-only và ghi `reason`, kể cả khi provider mặc định chưa có adapter chat); thiếu dữ liệu bắt
buộc trả lỗi có mã; model/policy đổi giữa chừng trả `preparation_policy_changed` và cần chuẩn bị
lại. Khi caller chọn `mode="ai"` hoặc `provider_id` tường minh, lỗi cấu hình/provider phải hiện
đúng mã thay vì âm thầm chuyển source-only.

## 3. Xem và chỉnh sửa

- `GET /compilation-runs/{run_id}/draft` — bản nháp có cấu trúc, kèm `ETag` là sha256.
  `?group_by_source=true` để nhóm theo nguồn; `?partial=true` để xem phần đã xong.
- `GET /compilation-runs/{run_id}/markdown` — bản đọc/dễ hiển thị.
- `GET /compilation-runs/{run_id}/progress` — trạng thái từng phần và token quan sát được.
- Chỉnh sửa có kiểm soát:
  1. `GET /compilation-runs/{run_id}/edit-context` — nội dung hiện tại, citations, nguồn, bảng và
     `bundle_sha256`.
  2. `POST /compilation-runs/{run_id}/edit-previews` — gửi `expected_bundle_sha256`, `reason`,
     `content` đã sửa; server kiểm citation thuộc nguồn đã ghim và trả preview kèm sha256/hạn.
  3. `POST /compilation-runs/{run_id}/edits` — header `Idempotency-Key`, body
     `{preview_id, preview_sha256}`; server tạo **run con** đã hoàn tất. Dùng `run.id` mới cho
     bước 4. Không sửa trực tiếp artifact gốc.

Hoàn tất chuẩn bị/duyệt draft **không** đồng nghĩa đã duyệt hay phát hành.

## 4. Duyệt và phát hành

Đăng ký, duyệt và phát hành là **ba quyết định khác nhau**. Đăng ký chỉ tạo phiên bản `draft`;
hoàn tất bước này hoặc bước duyệt **không** có nghĩa tài liệu đã được phát hành hay đã sẵn sàng
cho trợ lý.

1. Đăng ký tài liệu biên soạn:
   `POST /compiled-documents` — header `Idempotency-Key`, body tối thiểu
   `{document_key, title, compilation_run_id}`. Với tài liệu đã có:
   `POST /compiled-documents/{document_id}/versions` với `{compilation_run_id}`.
   `document_key` là khóa ổn định do người dùng/đơn vị đặt (chữ thường, số, `_ . -`), không phải ID
   kỹ thuật. Kết quả `201` (mới) hoặc `200` (replay) gồm `document` và `version`; lưu
   `version.id`, `version.status` (`draft`), `version.bundle_sha256` và `version.state_version`.

2. Đọc cổng duyệt: `GET .../versions/{version_id}/review-gate`.
   - `200` trả `review_id`, `report_sha256`, `bundle_sha256`, `verdict` và `findings`
     (`finding_id`, `finding`). Chỉ review **đã hoàn tất** của đúng phiên bản mới xuất hiện ở đây.
   - `409 publication_review_required` khi chưa có review hoàn tất khớp phiên bản. Đây không phải
     lỗi hệ thống: UI cho phép chọn bỏ qua review có xác nhận nếu người dùng có quyền duyệt.

3. Tạo preview duyệt: `POST .../versions/{version_id}/decision-preview` với
   `{"action": "approve", "reason": "..."}` (`reason` 1–1000 ký tự) và **một trong hai** xác nhận:
   - `review_ack` khi đã chạy review thật:
     `{review_id, report_sha256 (64 hex), confirmed_reviewed: true, resolutions: [...]}`.
     `resolutions` phải chứa **đúng một lần** mỗi `finding_id` trong `review-gate`, mỗi mục
     `{finding_id (64 hex), decision: "accepted_risk" | "not_an_issue", reason (10–2000 ký tự)}`.
     Nếu phiên bản có retrieval metadata, gửi thêm `retrieval_metadata_sha256` (64 hex).
   - `review_skip` khi người dùng đủ quyền xác nhận bỏ qua review cho **đúng phiên bản và hash**:
     `{confirmed_skip: true, version_id, bundle_sha256 (64 hex)}`, thêm
     `retrieval_metadata_sha256` nếu phiên bản có metadata. `reason` phải dài ít nhất 10 ký tự.
     `review_skip` chỉ dùng cho `approve`; gửi ở bước `publish` bị từ chối `422`.
   - Không gửi đồng thời `review_ack` và `review_skip`; không tự tạo "đã review" giả.
   Kết quả preview gồm `id`, `preview_sha256`, `expires_at` và `review_ack` đã ghim. Preview hết hạn
   hoặc nội dung phiên bản/bản đang hiệu lực đổi thì phải tạo preview mới
   (`publication_preview_stale`).

4. Cam kết duyệt: `POST .../versions/{version_id}/decisions` — header `Idempotency-Key` bắt buộc,
   body `{preview_id, preview_sha256}`. Preview chỉ dùng một lần. Thành công chuyển phiên bản sang
   `approved`; `GET .../published` vẫn `404` và chỉ mục chưa phục vụ bản này. Retry sau lỗi mạng
   phải dùng **đúng khóa và đúng body cũ**; server trả lại quyết định đã ghi. Khóa cũ gửi nội dung
   khác trả `409 idempotency_conflict`.

5. Tạo preview phát hành **mới**: `POST .../versions/{version_id}/decision-preview` với
   `{"action": "publish", "reason": "..."}`. Không gửi `review_ack`/`review_skip`; server tự kiểm
   lại biên nhận duyệt khớp đúng bundle và trạng thái phiên bản. Phát hành trực tiếp từ `draft` trả
   `409 publication_transition_invalid`; thiếu biên nhận duyệt trả `409 publication_approval_required`.

6. Cam kết phát hành: `POST .../versions/{version_id}/decisions` — header `Idempotency-Key`.
   **Dùng khóa khác với quyết định duyệt**; mỗi quyết định có khóa riêng. Thành công chuyển phiên
   bản sang `published`, ghi quyết định vào `history` và backend tự đánh thức đồng bộ chỉ mục; FE
   không gọi index thủ công.

Quyền theo backend: `approve` cho admin/reviewer (từ `draft`, `superseded`, `withdrawn`);
`publish` và `withdraw` chỉ admin (`publish` từ `approved`, `withdraw` từ `approved`/`published`);
đăng ký phiên bản cho admin/editor; đọc `summary`, `published`, `history`, `review-gate` cho
admin/editor/reviewer/member. FE không gộp hai bước thành một lần gọi: chỉ hiện nút **Duyệt** cho
người có quyền duyệt; sau khi duyệt hiển thị trạng thái **Đã duyệt** và chỉ admin thấy nút **Phát
hành**. Hộp xác nhận nêu phiên bản/hash đang thao tác và chế độ review (đã review hay bỏ qua có xác
nhận), không hiện ID kỹ thuật trong luồng thường.

Phục hồi khi lỗi mạng:
- Lỗi ở bước cam kết duyệt: đọc lại phiên bản; nếu còn `draft`, retry đúng khóa/body cũ (hoặc tạo
  preview mới nếu preview đã hết hạn). Nếu đã `approved`, không duyệt lại.
- Đã duyệt nhưng phát hành thất bại: đọc lại phiên bản/`summary`, giữ trạng thái **Đã duyệt** và
  cho người có quyền tiếp tục bằng một preview `publish` mới cùng khóa phát hành mới. Không tạo
  phiên bản mới và không chạy lại bước duyệt.
- Phát hành đã thành công nhưng phản hồi bị mất: không gửi lại quyết định phát hành; đọc lại
  `summary`/`published` rồi chờ chỉ mục.

Đọc lại: `GET /compiled-documents/{document_id}/summary` (observed_at, bản đã chuẩn bị/đã phát
hành/đang phục vụ, `readiness`, `serving_matches_published`), `GET .../published` khi cần nội dung
đã phát hành, `GET .../history` cho lịch sử quyết định. `GET .../versions/{version_id}/draft` và
`.../published` vẫn trả bản ghim gốc; không sửa trực tiếp artifact đã phát hành.

Sau `publish`, chỉ báo **Sẵn sàng cho trợ lý** khi `summary.readiness.status == "ready"` và
`serving_matches_published == true` (đúng `version.id`, `state_version`, `bundle_sha256` và
`publication_decision_id` của bản vừa phát hành). Các trạng thái `not_indexed`, `outdated`,
`unavailable` phải hiển thị trung thực; không suy "đã phát hành" thành "đã sẵn sàng". Poll
`summary` hoặc `GET .../index-readiness` có backoff trong lúc backend đồng bộ chỉ mục.

## 5. Sẵn sàng cho trợ lý

- `GET /compiled-documents/{document_id}/summary` → `readiness.status`:
  `ready` (đang phục vụ đúng bản phát hành), `not_indexed`, `outdated`, `unavailable`.
- Hoặc `GET /compiled-documents/{document_id}/index-readiness` → cùng `status`, `version_id`,
  `publication_decision_id`, `bundle_sha256`, `version_state` khi `ready`.
- Chỉ khi `ready` và `serving_matches_published=true` mới báo tài liệu sẵn sàng cho trợ lý. Không
  suy từ việc publish thành công.
- Trợ lý đọc phạm vi tri thức/binding theo cấu hình của trợ lý; không đưa ID kỹ thuật vào UI thường.


## 6. Không thuộc luồng chính (quản trị/tích hợp)

Vẫn giữ hợp đồng và quyền riêng, nhưng FE thường không hiển thị mặc định:

- `POST /compilation-runs` cùng các cờ `source_first`/`ai_supplement`/`selective_supplement`,
  `provider_id`, `max_output_tokens`, `structured_output`, review tùy chọn.
- `POST /compilation-runs/{run_id}/reviews` và đọc report/markdown/raw/segment.
- `POST /indexing-runs`, `GET /indexing-runs`, manifest; retry readiness.
- `GET/POST /ocr-processing-runs...` và sửa văn bản hậu OCR chi tiết.
- `PUT /workspaces/{workspace_id}/quota` là shim deprecated: nhận body nhưng không áp giới hạn.
  FE mới chỉ đọc thống kê sử dụng; không dùng endpoint này để điều kiện hóa gọi model.

## 7. Trạng thái và lỗi

- Lỗi trả RFC 7807 có `code`, `detail`, `correlation_id`; UI hiển thị mã và hướng xử lý, không
  biến lỗi provider/hạ tầng thành "không có dữ liệu".
- `uncertain` là trạng thái thật: không tự chuyển thành thành công, không tự xóa dấu vết.
- Mọi retry ghi (upload/chuẩn bị/sửa/phát hành) dùng lại đúng `Idempotency-Key`; khóa đã dùng cho
  nội dung khác trả `idempotency_conflict`.
- Không đổi model/provider/fallback hay bật reasoning từ client; model do ModelOps và policy đã
  ghim quyết định.
