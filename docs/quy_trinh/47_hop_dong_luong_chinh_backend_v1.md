# 47 — Hợp đồng luồng chính backend V1 cho FE mới

Tài liệu này chốt các API mà frontend mới dùng cho luồng người dùng thường:

**Tải tài liệu → Chuẩn bị nội dung → Xem và chỉnh sửa → Duyệt và phát hành → Sẵn sàng cho trợ lý**.

Người dùng thường **không chọn** công cụ OCR, model/context/output, chunking hay thế hệ chỉ mục.
Backend tự chọn theo loại tài liệu, cấu hình ModelOps được phép và trạng thái dữ liệu thật. Các API
từng bước (compiler, review, index thủ công, OCR run) vẫn tồn tại cho quản trị/tích hợp nhưng không
thuộc luồng này. Vòng đời ngược — dừng xử lý, ngừng dùng cho trợ lý, cập nhật, xóa vĩnh viễn — được
chốt ở mục 6.

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
- `GET /compilation-runs/{run_id}/markdown` và `GET /compilation-runs/{run_id}/draft.json` — tệp đã lưu nguyên byte, kèm `ETag` là SHA-256. Dùng các đường dẫn này để tải tệp.
- `GET /compilation-runs/{run_id}/progress` — trạng thái từng phần và token quan sát được.
- Khi lượt đọc tệp hoàn tất, worker xếp hàng soát chính tả trên phiên bản văn bản gốc. Trang chi tiết đọc `GET .../text-review/checks/summary?version={version}` theo lượt OCR và phiên bản đang xem. Kết quả gồm trạng thái, số đoạn đã soát và số gợi ý. Sau khi người dùng mở màn rà soát, giao diện mới đọc gợi ý chi tiết qua `GET .../text-review/checks`. Chỉ báo soát xong toàn bộ khi lượt hoàn tất và số đoạn đã soát khớp `total_evidence_count`. Lượt cũ có thể thiếu trường tổng này.
- Nếu phản hồi của một nhóm không qua kiểm tra gợi ý (`ocr_spelling_invalid`), worker tiếp tục các nhóm chưa gửi. Nhóm lỗi không được tính vào số đoạn đã soát và lượt chung báo chưa hoàn tất. Các lỗi quyền, phiên bản, cấu hình, quota hoặc lỗi hạ tầng vẫn dừng lượt.
- Khi người dùng bấm soát lại sau lỗi, worker giữ kết quả các nhóm đã xong nếu phiên bản, SHA-256, model, cấu hình và prompt vẫn khớp. Model chỉ nhận các đoạn chưa có kết quả.
- Người dùng xác nhận sửa qua `POST .../text-review` theo phiên bản và SHA-256 đã xem. Khi duyệt chính tả, API đối chiếu từng vị trí trong `spelling_edits` với gợi ý và văn bản đã gửi. Sau khi lưu bản sửa mới, gửi yêu cầu chuẩn bị lại với đúng lượt đọc và phiên bản văn bản vừa lưu. Nếu bước chuẩn bị gặp lỗi mạng, dùng lại khóa của bước đó.
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
   - Đoạn dẫn cả bảng vượt ngân sách có thể xuất hiện với trạng thái **Cần đối chiếu**. Báo cáo giữ đoạn biên soạn và vị trí bảng trong đúng bản tệp gốc. Trong hộp duyệt, mở vị trí để đối chiếu nguồn, rồi xử lý phát hiện như các mục khác.
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
- Backend truy vấn Qdrant ngoài đoạn giữ khóa đơn vị. Trước khi dùng kết quả, backend kiểm lại quyền,
  generation, manifest, model embedding và phạm vi nguồn. Thay đổi phạm vi trong lúc chờ trả lỗi
  xung đột hoặc trạng thái không còn nguồn khả dụng, tùy kết quả kiểm tra.
- Nếu model yêu cầu làm rõ tham chiếu nguồn ở lượt đầu, Backend tra cứu theo câu gốc trong phạm vi
  trợ lý. Khi kết quả có nhiều tài liệu, Backend yêu cầu người dùng chọn văn bản. Với lượt nối tiếp
  chưa rõ chủ thể, Backend vẫn yêu cầu làm rõ trước khi tra cứu.
- Đoạn văn đã xác minh liền nhau có thể đi cùng một đoạn đọc nối và dẫn chứng của cả hai đoạn.
  Danh sách tiếp qua trang được nối khi có quan hệ hàng đã kiểm chứng. Khi câu hỏi liệt kê,
  Backend cấp mã cho ô tên để model có thể chọn từng dòng có dẫn chứng.
- Với câu trả lời từ bảng, model chọn mã ô Backend cấp. Backend kiểm tra ô, lấy giá trị từ nguồn và
  gắn dẫn chứng. Mã dẫn chứng trùng trong phần đánh giá được gộp. Ý có mã ngoài phạm vi được đánh
  dấu thiếu căn cứ; các ý có dẫn chứng hợp lệ vẫn được kiểm tra độc lập.
- Khi lỗi chọn ô hoặc giá trị số có thể sửa và kế hoạch bằng chứng không thiếu phần bắt buộc,
  Backend có thể gọi lại bước sinh câu trả lời một lần với cùng nguồn và chỉ dẫn sửa lỗi. Lượt này dùng
  chung giới hạn một lần với nhánh đánh giá lại khi model báo thiếu căn cứ. Backend kiểm lại quyền,
  nguồn, model, ngân sách và đầu ra. Lỗi hạ tầng và timeout theo chính sách ModelOps.


## 6. Vòng đời ngược: dừng, thu hồi, cập nhật, xóa

Các thao tác dưới đây dùng prefix riêng `/platform/v1alpha1/workspaces/{workspace_id}/lifecycle`
(không nằm dưới collection). Mọi preview/accept đều kiểm lại actor, quyền, trạng thái và phạm vi
ở server; FE không tự suy quyền từ việc đã hiển thị nút.

### 6.1 Đọc trạng thái nguồn

`GET /sources/{source_id}/summary` trả thêm:

- `serving`: `served_revision_no` (bản trợ lý thực dùng), `preparing_revision_no` (bản
  đang xử lý, đang chờ chỉ mục sau phát hành hoặc bản mới hơn đang chờ trong khi bản cũ
  còn phục vụ), `published_revision_no` (bản mới nhất đã phát hành, có thể
  `null`), `served_version_id`, `served_document_id`. Ba số revision có thể khác nhau; không suy
  giá trị này từ giá trị kia. `served_*` chỉ có khi generation đang hoạt động thực sự chứa đúng
  version/state/bundle; riêng con trỏ publication không đủ để báo **Đang phục vụ**.
  Khi bản cũ đã thu hồi và bản thay thế thất bại, `preparing_revision_no` là `null`
  nếu không còn lượt chuẩn bị hoặc bóc tách nào đang chạy.
- `actions`: `can_stop`, `can_withdraw`, `can_update`, `can_delete` — chỉ hiện nút tương ứng khi
  `true`; server vẫn kiểm lại khi nhận lệnh.
- `preparation`: `intent_id`, `status`, `step`, `error_code` của lượt chuẩn bị gần nhất. Hiển thị
  `step` ("Đã nhận yêu cầu", "Đang đọc nội dung", "Đang biên soạn", "Đã chuẩn bị xong",
  "Xử lý lỗi", "Chưa xác định kết quả", "Đã dừng xử lý").

### 6.2 Bốn nút thao tác

| Nút | API | Quyền/điều kiện | Hành vi |
| :--- | :--- | :--- | :--- |
| **Dừng xử lý** | `POST /sources/{source_id}/preparation-intents/{intent_id}/cancel` hoặc lifecycle `job/cancel` + `job_kind` | admin/editor, lượt còn hiệu lực | Dừng bền vững; kết quả muộn bị bỏ; giữ tệp gốc, phần đã xong và usage |
| **Ngừng dùng cho trợ lý** | lifecycle `withdraw` cho `source`, `document` hoặc `collection` | admin, tài nguyên `active` | Ẩn ngay bản `published` khỏi RAG/tìm kiếm/dẫn chứng; giữ tệp và lịch sử |
| **Cập nhật tài liệu** | `POST /sources/{source_id}/revisions` (mặc định `staged=true`) rồi publish, sau đó lifecycle `document/replace` | admin/editor tải revision; admin duyệt/phát hành/thay | Bản mới là ứng viên; chỉ chuyển serving/index khi sẵn sàng |
| **Xóa vĩnh viễn** | lifecycle `source/delete` | admin | Một preview + một xác nhận; thu hồi bản liên quan, chặn nguồn, dọn nền |

**Dừng xử lý**: sau khi nhận, FE dừng poll và hiện **Đã dừng xử lý**; không tự gửi lại lượt đã
dừng bằng khóa cũ. Lượt OCR dùng chung hoặc chạy độc lập không bị hủy theo intent khác.

**Ngừng dùng cho trợ lý**: preview/accept theo hợp đồng lifecycle. `impact` trả
`withdraw_keeps_originals=true`, `restore_available=true`. Ở cấp kho, thu hồi áp cho mọi bản
`published` thuộc kho, đồng bộ lại chỉ mục và giữ toàn bộ tệp nguồn. Thu hồi bản cuối làm
`GET .../search-readiness` chuyển `empty` và backend dọn generation nền; `empty` **không** phải
"Sẵn sàng cho trợ lý". Không dùng thao tác này thay cho xóa.

**Cập nhật tài liệu**: revision tải lên mặc định `staged=true` (kể cả khi FE bỏ trường này):
`current_revision_no` tăng nhưng `serving_revision_no` giữ nguyên, bản cũ vẫn phục vụ. Sau khi
duyệt/phát hành bản mới, preview/accept `document/replace` với `replacement_version_id`; biên nhận
`pending` kèm `result.index_run_id`, chỉ `completed` khi serving/index đã chuyển. Mọi lỗi trước đó
giữ bản cũ phục vụ. Nếu bản cũ bị thu hồi trong lúc chờ, replace chuyển `failed` và `/published`
trả `404`; FE báo lỗi và yêu cầu lượt thay thế mới, không tự chạy lại.

**Xóa vĩnh viễn**: preview phải có `impact.permanent=true`; thiếu thì FE không cho xác nhận
(runtime cũ). Accept trả `409 lifecycle_preview_stale` khi phạm vi đổi sau preview — tạo preview
mới. Hỗ trợ nguồn `active`, `archived` hoặc `deleted`. Chỉ báo **Đã xóa** khi biên nhận
`status=completed` và `impact.permanent=true`. Upload lại cùng nội dung chỉ được sau khi biên nhận
hoàn tất; trong lúc chờ backend trả `source_purge_pending`/`duplicate_content_deleted`.

### 6.3 Biên nhận và tiến độ

Poll `GET /lifecycle/actions/{action_id}`; trạng thái nằm ở backend nên tồn tại khi chuyển trang
hoặc mở lại app. `status` là `preview|pending|completed|failed`; `phase`/`progress.step` cho biết
bước (khi `progress.percent` null chỉ hiện tên bước); `attempt_count`, `error_code`,
`last_error_at`, `lease_expires_at`, `confirmed_by`, `takeover_by`, `takeover_at` chỉ hiện cho
admin. Phase dọn: `waiting_for_workers`, `deleting_vectors` (25), `deleting_objects` (55),
`resealing` (80), `deleting_rows` (95), `completed` (100). Lỗi giữ biên nhận `pending` để tiếp tục;
admin xem lượt kẹt qua `GET /lifecycle/source-deletions/active` và tiếp quản qua
`POST /lifecycle/actions/{action_id}/takeover` (audit giữ người xác nhận ban đầu và người tiếp quản).
Chủ sở hữu luôn đọc được biên nhận của mình; admin workspace chỉ đọc thêm biên nhận
`source/delete` đã xác nhận để tiếp quản, còn biên nhận hội thoại/tác vụ chat vẫn chỉ thuộc chủ
sở hữu. Chỉ lượt xóa đã xác nhận còn `pending` mới khóa `can_update`/`can_delete`; preview đang
mở, preview hết hạn hoặc biên nhận đã kết thúc không thu hẹp quyền thao tác.

### 6.4 Khôi phục thư mục và xóa model

- `POST .../folders/{folder_id}/restore` kiểm theo thứ tự: `404 resource_unavailable` (kho bị lưu
  trữ/xóa), `409 folder_not_deleted`, `409 folder_parent_unavailable`, `409 folder_name_exists`.
  Xóa thư mục chỉ nhận khi rỗng (`409 folder_not_empty`).
- Xóa cả kho là xóa vĩnh viễn (`collection/delete`): preview + xác nhận admin, cascade nguồn/thư mục/
  bằng chứng/chunk/vector/object của kho; kho còn trợ lý tham chiếu trả `409 collection_in_use_by_assistants`.
  Sau khi hoàn tất không còn `restore`; không còn `409 collection_not_empty`.
- `DELETE /platform/v1alpha1/modelops/connections/{id}` và
  `DELETE .../connections/{id}/models/{model_id}` trả `409 model_provider_in_use` kèm `detail` nêu
  loại tham chiếu (mặc định hệ thống, trợ lý, lịch sử lập chỉ mục/biên soạn/phản biện/sử dụng
  model). Lịch sử được giữ; cấu hình mặc định hệ thống đang trỏ vào provider/model bị chặn xóa.
- **Lưu trữ tài liệu** không còn là thao tác chuẩn của FE; `archive` chỉ dùng cho dữ liệu cũ/khôi
  phục.

## 7. Không thuộc luồng chính (quản trị/tích hợp)

Vẫn giữ hợp đồng và quyền riêng, nhưng FE thường không hiển thị mặc định:

- `POST /compilation-runs` cùng các cờ `source_first`/`ai_supplement`/`selective_supplement`,
  `provider_id`, `max_output_tokens`, `structured_output`, review tùy chọn.
- `POST /compilation-runs/{run_id}/reviews` và đọc report/markdown/raw/segment.
- `POST /indexing-runs`, `GET /indexing-runs`, manifest; retry readiness.
- `GET/POST /ocr-processing-runs...` và sửa văn bản hậu OCR chi tiết.
- `PUT /workspaces/{workspace_id}/quota` là shim deprecated: nhận body nhưng không áp giới hạn.
  FE mới chỉ đọc thống kê sử dụng; không dùng endpoint này để điều kiện hóa gọi model.

## 8. Trạng thái và lỗi

- Lỗi trả RFC 7807 có `code`, `detail`, `correlation_id`; UI hiển thị mã và hướng xử lý, không
  biến lỗi provider/hạ tầng thành "không có dữ liệu".
- `uncertain` là trạng thái thật: không tự chuyển thành thành công, không tự xóa dấu vết.
- Mọi retry ghi (upload/chuẩn bị/sửa/phát hành) dùng lại đúng `Idempotency-Key`; khóa đã dùng cho
  nội dung khác trả `idempotency_conflict`.
- Không đổi model/provider/fallback hay bật reasoning từ client; model do ModelOps và policy đã
  ghim quyết định.
