# Vòng đời ngược của tài liệu và chatbot — backendV1

Tệp dẫn xuất mồ côi có [luồng dọn riêng](storage-cleanup.md); phục hồi DB/tệp/vector
vào đích mới theo [recovery v1](recovery.md). Những luồng này không purge nguồn
gốc. Ngoại lệ xóa vĩnh viễn tài liệu nguồn được người dùng xác nhận ngày 2026-10-29.

Phạm vi: chỉ `backendV1/`; workspace là biên quyền theo ADR v1. Mọi thao tác
được kiểm tra bằng actor thật và membership/role ở server. Không áp dụng cho `backend/`.

## Thao tác hỗ trợ

Hợp đồng thao tác thông thường cho FE gồm bốn nút: **Dừng xử lý** (hủy
`PreparationIntent` hoặc `job/cancel`), **Ngừng dùng cho trợ lý** (`withdraw`),
**Cập nhật tài liệu** (`document/replace`) và **Xóa vĩnh viễn** (`source/delete`,
`collection/delete`).
`archive` vẫn được API hỗ trợ cho dữ liệu cũ, khôi phục và tác vụ vận hành nhưng
không còn là thao tác chuẩn trong luồng người dùng thường.

| Tài nguyên (`kind`) | Thao tác (`action`) | Kết quả |
|---|---|---|
| `collection`, `source`, `document` | `withdraw` | Thu hồi mọi bản `published` liên quan khỏi RAG/dẫn chứng ngay; giữ file, revision và lịch sử; chỉ admin |
| `collection` | `archive`, `restore` | Lưu trữ hoặc khôi phục kho còn tồn tại; giữ nguồn và lịch sử |
| `document` | `archive`, `delete`, `restore` | Lưu trữ, đưa vào thùng rác hoặc khôi phục; giữ nguồn và lịch sử |
| `source` | `archive`, `restore` | Lưu trữ hoặc khôi phục nguồn còn tồn tại |
| `source`, `collection` | `delete` | Xóa vĩnh viễn sau một lần xem trước và một lần xác nhận; tự thu hồi bản `published` liên quan khi nhận lệnh. `collection/delete` xóa cascade mọi nguồn, thư mục, bằng chứng OCR/Compiler, chunk/vector và object lưu trữ của kho; kho đang được trợ lý dùng trả `409 collection_in_use_by_assistants` |
| `assistant` | `pause`, `resume`, `archive`, `delete`, `restore` | Ngừng/bật phục vụ hoặc đưa vào thùng rác; khôi phục xong vẫn tắt, cần bật riêng |
| `conversation` | `archive`, `delete`, `restore` | Chỉ chủ hội thoại được thao tác, kể cả khi người khác là quản trị |
| `job` | `cancel` + `job_kind` | Hủy OCR, Compiler, index, review tự động, review ngữ nghĩa, kiểm chính tả hoặc lượt hỏi |
| `index` | `cleanup` | Xóa collection vector v1 và chunk DB của generation đã ngừng dùng |
| `document` | `replace` + `replacement_version_id` | Chuẩn bị chỉ mục cho bản đã duyệt, rồi chuyển publication và index trong một transaction |

Ngoại trừ `source/delete` và `collection/delete`, `delete` là **xóa có thể khôi phục**, không xóa vĩnh viễn file gốc, raw OCR,
Markdown/JSON đã lưu, quyết định duyệt hay lịch sử hội thoại. Tài nguyên bị xóa/lưu
trữ bị chặn trên API đọc nội dung, tải tệp, tác vụ và RAG; kết quả hỏi đáp cũ phải
kiểm lại nguồn trước khi trả về. Tài nguyên con vẫn bị chặn nếu kho cha bị lưu trữ/xóa.

`source/delete` xử lý được nguồn đang `active`, đã lưu trữ (`archived`) hoặc đã xóa
mềm (`deleted`); preview dùng cùng một hợp đồng và không cần khôi phục trước. Khôi
phục tài nguyên đã xóa mềm (trừ hội thoại) cần admin. Kiểm tra trùng nội dung theo
checksum vẫn áp dụng cho mọi trạng thái; sau khi xóa vĩnh viễn hoàn tất mới cho phép
tải lại cùng nội dung.

## Thu hồi phát hành và kho trống

`withdraw` chỉ admin và chỉ trên nguồn/tài liệu/kho đang `active`. Server thu hồi mọi
`CompiledVersion` đang `published` thuộc phạm vi trong một transaction, tăng
`state_version` của phiên bản và `change_sequence` của document, ghi audit và đánh
thức outbox `kb_index_sync`. Đường đọc RAG, tìm kiếm và dẫn chứng ẩn bản đã thu hồi
ngay ở request kế tiếp; tệp gốc, revision, OCR/Compiler và history vẫn còn. `impact`
trả `withdraw_keeps_originals=true` và `restore_available=true`.

Khi bản phát hành cuối cùng bị thu hồi, lần đồng bộ nền kế tiếp nhận
`index_no_published_documents` và xác nhận không còn nội dung đã phát hành nhưng tạm
thời không đọc được. Khi đó generation đang phục vụ được retire: xóa collection
vector, xóa vector khỏi chunk DB, đặt generation `is_active=false`, ghi
`vectors_retired_at`/`deactivated_at`, chuyển `kb_index_sync.status` sang `empty`,
và phát sự kiện `index.vectors_retired` (`reason=collection_empty`) cùng
`index.collection_empty`. Manifest, chunk ID, raw receipt và dẫn chứng lịch sử được
giữ để audit. Nếu vẫn còn bản `published` nhưng nội dung tạm không đọc được, server
giữ generation cũ và không tuyên bố kho trống.

`GET /sources/{source_id}/summary` trả ba revision tách biệt trong `serving`:
`served_revision_no` (bản trợ lý thực dùng), `preparing_revision_no` (bản mới hơn
đang chuẩn bị, nếu có) và `published_revision_no` (bản mới nhất đã phát hành), kèm
`served_version_id`/`served_document_id`. Ba giá trị có thể khác nhau; không suy
đoán lẫn nhau. `GET .../search-readiness` trả trạng thái outbox của kho
(`not_requested`, `pending`, `building`, `ready`, `empty`, `failed`, `uncertain`).
`GET .../index-readiness` của document vẫn dùng `ready|not_indexed|outdated|unavailable`;
`empty` không phải là "sẵn sàng cho trợ lý".

## API dùng cho giao diện quản trị

Prefix: `/platform/v1alpha1/workspaces/{workspace_id}/lifecycle`.

1. `POST /previews`: gửi `kind`, `resource_id`, `action`, `reason` và tham số riêng
   nếu có. Trả `impact`, `id`, `preview_sha256`, thời hạn. Bản xem trước chưa đổi trạng thái tài nguyên.
2. `POST /actions`: gửi `preview_id`, `preview_sha256` cùng header
   `Idempotency-Key`. Server kiểm lại người xác nhận, quyền, thời hạn, trạng thái
   và phạm vi ảnh hưởng. Thay đổi sau preview trả `409`, cần xem trước lại.
3. `GET /actions/{action_id}`: trạng thái và biên nhận. Actor xem được bản preview
   của chính mình; admin workspace xem thêm biên nhận `source/delete` đã xác nhận,
   kể cả lượt xóa đang kẹt, nhưng không xem preview của người khác. Biên nhận hội
   thoại và tác vụ của lượt chat vẫn chỉ thuộc chủ sở hữu.
4. `GET /resources?limit=50&offset=0`: các tài nguyên đang lưu trữ/thùng rác.
   Hội thoại của người khác không xuất hiện. API có `Cache-Control: private, no-store`.
5. `GET /source-deletions?collection_id=...`: các yêu cầu xóa nguồn đang chờ của chính
   quản trị viên hiện tại, để tiếp tục ngay trong kho tri thức sau khi tải lại trang.
6. `GET /source-deletions/active?limit=20&offset=0`: admin workspace xem mọi lượt xóa
   nguồn đang `pending`, sắp theo `last_error_at` mới nhất, dùng để phát hiện lượt bị kẹt.
7. `POST /actions/{action_id}/takeover`: admin workspace tiếp quản một lượt xóa nguồn
   đang kẹt. Chỉ nhận khi lượt còn `pending` và không có lease hiệu lực; giữ nguyên
   `confirmed_by`, ghi `takeover_by`/`takeover_at` và audit `source.purge_takeover`.
   Trả cùng biên nhận `id`; không tạo hàng đợi hay phạm vi xóa mới.
8. `GET /source-deletions/legacy?collection_id=...&limit=20&offset=0`: nguồn đã xóa
   mềm nhưng vẫn còn tệp/bản ghi, chưa có yêu cầu xóa đang chờ. Chỉ admin workspace
   được xem; kiểm quyền/collection, phân trang và không tự tạo thao tác ghi.

Mọi phản hồi biên nhận (`ActionResponse`) gồm `status`
(`preview|pending|completed|failed`), `phase`, `progress` (`step`, `percent` có thể
`null`), `attempt_count`, `error_code`, `last_error_at`, `lease_expires_at`,
`confirmed_by`, `takeover_by`, `takeover_at`, `result` (đã lọc các khóa kế hoạch nội
bộ) và mốc `expires_at`/`accepted_at`/`finished_at`. FE lấy tiến độ từ biên nhận này
nên trạng thái tồn tại khi chuyển trang hoặc mở lại app; hiển thị `progress.step`
khi `percent` chưa đo được, chỉ báo **Đã xóa** khi `status=completed` và
`impact.permanent=true`. Chi tiết kỹ thuật (`error_code`, `last_error_at`,
`attempt_count`, `lease_expires_at`) và nút tiếp quản chỉ dành cho admin.

Tiến trình dọn nền đi theo `phase`/`progress`: `waiting_for_workers` (đang chờ tác vụ
đã dừng), `deleting_vectors` (25), `deleting_objects` (55), `resealing` (80),
`deleting_rows` (95), `completed` (100, bước "Đã xóa vĩnh viễn"). Lỗi giữ nguyên
biên nhận ở trạng thái `pending` với bước tạm dừng do lỗi; chạy lại worker sẽ tiếp tục
từ checkpoint trên cùng biên nhận.

## Tài liệu đã xóa bằng phiên bản V1 cũ

API/worker đang chạy từ trước khi cập nhật mã có thể vẫn xử lý `source/delete`
thành xóa mềm: nguồn bị ẩn nhưng checksum/tệp còn, upload cùng nội dung trả409.
Runtime đó cũng chưa có endpoint `/source-deletions`, nên FE báo không đọc được trạng thái.
FE chặn xác nhận xóa vĩnh viễn nếu preview chưa khai báo `impact.permanent=true`;
không coi receipt `completed` là purge thành công khi thiếu bằng chứng không giữ
nguồn và không thể restore. Vì vậy FE mới không tiếp tục báo thành công nhầm trên API cũ.

1. Dừng phiên `v1-dev` cũ rồi chạy lại `./make.ps1 v1-dev` để cả API và worker
   nạp mã mới. Chỉ làm mới trình duyệt hoặc chỉ restart FE không giải quyết phần BE.
2. Tại kho, đóng hộp tải lên và xem **Tài liệu đã xóa còn giữ tệp**.
3. Chọn `⋯ → Hoàn tất xóa`, xem trước/xác nhận **Xóa vĩnh viễn** một lần mới.
   Không dùng biên nhận xóa mềm `completed` làm bằng chứng đã purge hoặc tự chuyển
   biên nhận cũ thành yêu cầu phá hủy dữ liệu. Không cần restore để hiện lại nguồn.
4. Runtime cũ vẫn chặn xác nhận khi còn version `published` vì chưa tự thu hồi; runtime
   mới thu hồi trong cùng transaction nhận lệnh, nên chỉ cần xem trước/xác nhận theo
   hợp đồng hiện hành. Nguồn có purge pending được theo dõi bằng biên nhận đang có,
   không xuất hiện thêm trong danh sách cần xác nhận.
5. Chờ hoàn tất rồi upload lại. Giữ kiểm tra checksum và ràng buộc unique; không bỏ
   nguồn đã ẩn khỏi truy vấn chống trùng hoặc tự xóa dữ liệu khi upload.

Upload phân biệt `duplicate_content`, `duplicate_content_deleted`, `source_purge_pending`
và `revision_unchanged`; thông báo không lộ ID nguồn nội bộ.

## Xóa vĩnh viễn tài liệu nguồn — ngoại lệ có phạm vi

- Chỉ quản trị viên workspace hoặc quản trị nền tảng được xem trước/xác nhận.
  Tác vụ nền xác minh lại quyền từ membership DB hoặc cầu dev-admin hiện có;
  không lưu quyền JWT vào hàng đợi. Nếu không phân giải được quyền nền, từ chối nhận tác vụ.
- Không cần thu hồi phát hành trước khi xóa: khi nhận lệnh, server thu hồi mọi bản
  `published` liên quan trong cùng transaction, đánh dấu nguồn `deleted` và mới giao
  việc dọn nền, nên trợ lý ngừng dùng nguồn trước khi tệp bị xóa. Preview vẫn liệt kê
  các bản sẽ bị thu hồi. Nếu phát sinh bản phát hành hoặc dữ liệu mới sau preview,
  accept trả `409 lifecycle_preview_stale` và yêu cầu xem trước lại; phạm vi đã xác
  nhận không tự mở rộng.
- Preview ghim đồ thị phụ thuộc và hash tệp. Accept lưu biên nhận `pending` với
  `phase`/`progress`, hủy tác vụ liên quan và chặn sử dụng nguồn; chưa tuyên bố xóa
  xong. Không còn cơ chế chờ cứng 30 phút: biên nhận giữ checkpoint các job đã hủy
  (`result.checkpoint.jobs`) và worker chỉ chuyển sang dọn khi các job đó không còn
  `queued`/`running`. Mỗi lượt dọn nhận lease 120 giây (`lease_expires_at`) và tăng
  `attempt_count`; lease hết hạn cho phép worker khác hoặc admin tiếp quản tiếp tục
  trên **cùng biên nhận**. Reconciler gửi lại việc còn `pending` mỗi 5 phút; dùng
  cùng biên nhận/idempotency key để tiếp tục. Chỉ nhận thêm tệp hoàn tất muộn thuộc
  đúng lượt hoặc nhóm xử lý đã xác nhận; nguồn, phiên bản và tác vụ mới cần một phạm
  vi xóa riêng.
- Worker dọn toàn bộ revision của nguồn, raw OCR đã đăng ký, MD/JSON hậu OCR,
  lượt Compiler/Review phụ thuộc, các bản nháp toàn phần hoặc một phần và tệp
  kết quả của từng nhóm xử lý, kết quả hội thoại đã lưu có nguồn đó,
  chunk và đúng point vector liên quan. Bản nháp gộp nhiều nguồn cũng bị xóa nếu
  phụ thuộc nguồn này; giữ tệp nguồn khác và phiên bản không phụ thuộc.
- Kho dữ liệu dạng S3/MinIO xóa cả version và delete marker của **đúng object key**.
  Cần quyền liệt kê/xóa version; storage không cho xóa thì biên nhận còn `pending`.
  Không dùng xóa theo prefix hoặc xóa toàn collection vector.
- Index dùng chung được ghi manifest dẫn xuất cho phần còn lại, giữ chuỗi hash
  manifest gốc làm dấu vết. Không gọi model, không re-embed/reindex tài liệu khác.
  Object dùng chung với nguồn ngoài phạm vi trả `409 purge_shared_object`; không xóa
  tệp mà tài liệu khác còn tham chiếu.
- Lô embedding dùng chung được đối chiếu với manifest hoặc với chunk, thứ tự và
  vector đã lưu trong PostgreSQL khi chưa có manifest. Lô chỉ chứa chunk của
  nguồn bị xóa thì xóa tệp raw. Lô còn chunk khác thì
  ghi tệp dẫn xuất đã lọc, đánh số lại `index` và cập nhật hash, giữ nguyên vector
  của nguồn còn lại. Nếu lô đang dang dở đã ghi phản hồi raw trước khi commit,
  đối chiếu phạm vi chunk của lô và thu hồi đúng tệp raw chưa được tham chiếu.
  Thiếu ánh xạ đã xác minh hoặc gặp lỗi lưu trữ thì biên nhận ở lại `pending`.
  Cập nhật manifest, biên nhận embedding và danh sách `_purge_cleanup` trong
  cùng giao dịch có kiểm tra lease. Worker còn lease thực hiện dọn theo danh
  sách khóa tệp đã lưu.
- Giới hạn 10.000 hàng trong đồ thị; phụ thuộc ngoài allowlist, đổi target storage/vector
  hoặc đổi lineage sau xác nhận đều chặn dọn. Lỗi giữa chừng giữ kế hoạch bền vững;
  tác vụ có thể đã xóa một phần tệp, không thể restore.
- Lỗi giữa PostgreSQL, lưu trữ và Qdrant không tạo biên nhận mới: biên nhận ở lại
  `pending`, ghi `error_code`/`last_error_at`, xóa lease và giữ bước tiến độ để admin
  biết đang kẹt. Chạy lại worker (hoặc takeover) với cùng biên nhận sẽ tiếp tục.
- Chỉ báo `completed` sau khi storage/vector và SQL hoàn tất. API biên nhận không
  trả kế hoạch nội bộ/đường dẫn object. Giữ audit/idempotency, metadata/hash lịch sử
  và các bundle backup đã tạo theo chính sách sao lưu riêng; đây không phải purge
  cả backup hay dữ liệu ngoài kho QNU. Không khôi phục nguồn đã xóa vĩnh viễn bằng `restore`.

### Xóa vĩnh viễn cả kho

`collection/delete` dùng đúng một biên nhận và cùng worker với `source/delete`, nhưng
phạm vi là toàn kho: mọi nguồn/revision, thư mục (kể cả thư mục đã xóa mềm), bằng
chứng OCR/Compiler/Review, bản phát hành, chunk DB, các `IndexRun` cùng generation
vector và object `v1/workspaces/{workspace_id}/index/{run_id}/` đều bị xóa; upload
ledger của kho cũng bị dọn để không phát lại id đã xóa. Generation vector được xóa
nguyên collection thay vì reseal, vì không còn nội dung nào cần giữ; object nguồn
vẫn phải nằm trong workspace và không được tài liệu khác tham chiếu. Kho còn trợ lý
tham chiếu bị chặn ngay ở preview/accept bằng `409 collection_in_use_by_assistants`;
admin phải gỡ kho khỏi trợ lý trước. Preview trả `sources_to_delete`,
`folders_to_delete`, `files_to_delete`, `published_versions_to_withdraw` và
`restore_available=false`; biên nhận hoàn tất trả thêm `sources_deleted`/`folders_deleted`.
Sau khi hoàn tất, kho và mọi tài nguyên con trả `404`; không có `restore`.
- Admin workspace xem lượt kẹt qua `GET /source-deletions/active` và tiếp quản qua
  `POST /actions/{action_id}/takeover`. Biên nhận giữ `confirmed_by` của người xác
  nhận ban đầu và `takeover_by`/`takeover_at` của người tiếp quản; cả hai được ghi
  trong audit `source.purge_takeover` và `source.purged`. Nguồn đang xóa vẫn bị chặn
  sử dụng trong suốt quá trình.
- FE xác nhận ngay trong kho hoặc chi tiết tài liệu; hoàn tất ở danh sách hoặc
  quay về kho cha, không đưa sang trang Tài nguyên. Trang Tài nguyên bỏ khỏi menu;
  URL cũ chuyển sang biên nhận vận hành. Thành viên chỉ xem được biên nhận hội
  thoại của chính mình qua API đã kiểm quyền, không mở quyền xem tác vụ vận hành.

Worker V1 đăng ký sẵn `source_purge_job`. Migration `0020_reverse_flow` bổ sung cột
biên nhận (`phase`, `progress`, `worker_id`, `lease_expires_at`, `attempt_count`,
`last_error_at`, `confirmed_by`, `takeover_by`, `takeover_at`) và mở rộng ràng buộc
`kb_index_sync.status` với `empty`. Sau khi cập nhật mã cần khởi động lại phiên
`v1-dev` để worker nạp hàm mới. Đợt này đã kiểm trên PostgreSQL/storage/Qdrant cô
lập; chưa chạy migration hay xóa tài liệu thật trên môi trường ứng dụng.

Ví dụ thân yêu cầu xem trước, không chứa quyền hay trạng thái do client tự cấp:

```json
{"kind":"source","resource_id":"<source_id>","action":"delete","reason":"Thay tài liệu cũ"}
```

`impact` cho biết số phiên bản xuất bản, tác vụ và phạm vi chatbot/hội thoại có thể
bị ảnh hưởng; việc giữ nguồn gốc; có cần index mới sau khôi phục; và có ngừng index
đang active khi dọn hay không. Với `source/delete`, `impact.permanent=true`,
`originals_and_raw_evidence="permanently_deleted"`, `restore_available=false` và
`published_versions_to_withdraw` liệt kê bản sẽ bị thu hồi. Duyệt/thu hồi publication
hiện có vẫn dùng API riêng.

Quyền: admin cho xóa tài liệu/kho, thu hồi phát hành, quản trị chatbot, thay
publication và dọn index; admin/editor cho lưu trữ tri thức, cập nhật tài liệu và
hủy tác vụ xử lý. Khôi phục tài nguyên đã xóa cũng cần admin. Chủ hội thoại tự quản
lý hội thoại/lượt hỏi của mình.

## Thay bản mới khi bản cũ vẫn phục vụ

1. `POST .../sources/{source_id}/revisions` mặc định `staged=true` (kể cả khi FE
   không gửi trường này). Revision mới được lưu làm **ứng viên**:
   `current_revision_no`/`revision_count` cho biết bản mới nhất đã tải lên nhưng
   `serving_revision_no` không đổi. Tệp cũ giữ nguyên. Chỉ khi gọi tường minh
   `staged=false` mới giữ hành vi cũ (bản mới làm bản đang phục vụ thành stale).
2. Chạy OCR → sửa văn bản nếu cần → Compiler → review → đăng ký phiên bản mới.
3. Duyệt (`approve`) phiên bản mới bằng luồng publication có sẵn.
4. Preview/accept `document/replace`, chọn `replacement_version_id` đã duyệt.
   Người thực hiện phải có membership admin của đơn vị để worker kiểm lại quyền;
   quyền quản trị nền tảng ở request không được sao chép thành quyền worker.
5. Action trả `pending` và `result.index_run_id`. Worker hiện có xây generation mới,
   kiểm lại bundle, nguồn, quyết định duyệt, model và quyền qua từng checkpoint.
6. Khi vector/manifest sẵn sàng, transaction cuối chuyển serving revision, xuất bản
   phiên bản mới, supersede bản cũ và đổi active index. Sau đó action `completed`.

Lỗi bóc tách, biên soạn, phát hành hoặc lập chỉ mục trước khi hoàn tất giữ nguyên
publication/index cũ và `serving_revision_no` cũ; trợ lý tiếp tục dùng bản cũ. Lỗi
storage/vector có thể retry theo chính sách index hiện có; embedding đã lưu không bị
gửi lại. Lỗi model hoặc trạng thái không rõ không tự gửi lại. Action `failed` cần
yêu cầu mới sau khi xử lý nguyên nhân; không tự sửa thành công hay reset run cũ.

Nếu bản cũ bị chủ động thu hồi trong lúc generation thay thế đang chờ, worker tôn
trọng quyết định đó: run chuyển `failed`, biên nhận `replace` chuyển `failed`,
`/published` trả `404`, phiên bản ứng viên vẫn `approved`, không có hit tìm kiếm và
serving không bị chuyển. Cần xử lý nguyên nhân rồi thực hiện lượt thay thế mới.

Nếu một revision nguồn dùng chung còn được văn bản khác xuất bản, chuyển serving
revision có thể làm văn bản đó cũ đi. Server trả `replacement_shared_source` và
yêu cầu thu hồi hoặc chuẩn bị thay thế đồng bộ trước. API `replace` hiện thay một
compiled document mỗi lần, chưa hỗ trợ batch nhiều document dùng chung nguồn.

## Khôi phục thư mục

`POST .../folders/{folder_id}/restore` kiểm theo thứ tự: kho phải còn khả dụng
(`404 resource_unavailable` nếu kho đã lưu trữ/xóa), thư mục phải đang xóa mềm
(`409 folder_not_deleted`), thư mục cha phải tồn tại và hiển thị trong cùng kho
(`409 folder_parent_unavailable`), và tên không được trùng anh-em cùng cấp theo
kiểu không phân biệt hoa thường (`409 folder_name_exists`). Khôi phục giữ nguyên
`parent_id` đã lưu; xóa thư mục chỉ nhận khi thư mục rỗng (`409 folder_not_empty`).

## Xóa model hoặc nhà cung cấp đang được tham chiếu

`DELETE /platform/v1alpha1/modelops/connections/{id}` và
`DELETE .../connections/{id}/models/{model_id}` trả `409 model_provider_in_use` khi
còn tham chiếu, kèm `detail` nêu loại tham chiếu cần xử lý: cấu hình mặc định hệ
thống, trợ lý, lịch sử lập chỉ mục, lịch sử biên soạn, lịch sử phản biện hoặc lịch
sử sử dụng model. Lịch sử sử dụng model được giữ và có khóa ngoại chặn xóa. Cấu
hình mặc định hệ thống đang trỏ vào provider/model bị chặn xóa; chuyển mặc định
sang provider/model khác trước khi xóa.

## Dừng, khôi phục và dọn

- Hủy có trạng thái `cancelled` bền vững. Worker không nhận lại job đó và không
  nhận kết quả đến muộn thành đầu ra hoàn tất. Hủy auto-review cũng hủy lượt review
  con đang chạy. Tạm dừng/xóa chatbot hủy lượt hỏi đang chạy của chatbot.
- Hủy `PreparationIntent` dùng fencing ở mọi bước: worker kiểm lại quyền và trạng
  thái trước khi giao việc, nhận việc hoặc lưu kết quả; liên kết `OcrRun`/
  `CompilationRun` con chỉ ghi khi intent còn active. Lượt con dùng chung hoặc chạy
  độc lập không bị hủy theo intent khác; chỉ lượt con độc quyền đặt dưới khóa
  `prep:<intent_id>` bị dừng. Kết quả đến sau khi dừng bị bỏ, không ghi đè
  `cancelled`. Reconciler chỉ phục hồi intent còn hiệu lực theo lease/checkpoint;
  khởi động lại worker không làm intent `cancelled` chạy lại. Lời gọi model chưa xác
  định kết quả giữ trạng thái `uncertain` thay vì tự nhận thành công.
- Không bảo đảm server AI ngừng tính toán yêu cầu HTTP đã gửi. Token có số đo vẫn
  được ghi nhận; usage chưa rõ giữ reservation, không coi là miễn phí. Đầu ra đến
  sau khi mất quyền thực thi bị loại bỏ; artifact đã lưu trước đó được giữ nguyên.
- Pause/resume không đổi revision cấu hình nên hội thoại cũ dùng lại được. Sửa
  persona/model/cấu hình thực sự vẫn làm đổi revision và yêu cầu hội thoại mới.
- Các API cập nhật hiện hữu cũng dùng cùng quy tắc hủy: `PUT .../assistants/{id}`
  với `is_active=false` hủy lượt đang chạy của mọi hội thoại thuộc trợ lý đó;
  `PUT .../conversations/{id}` với `status=archived` chỉ hủy lượt của hội thoại
  do người gọi sở hữu. Trạng thái, việc hủy và audit được commit cùng transaction.
  Bật/mở lại không khôi phục lượt đã hủy; replay key cũ vẫn báo cancelled, cần gửi
  lượt mới với sequence hiện hành. Cập nhật đang active hoặc chỉ đổi tên hội thoại
  không hủy lượt đang chạy. Lịch sử đã hoàn tất được giữ; audit ghi số lượt bị hủy.
- Restore không tự chạy lại job đã hủy và không tự bật chatbot. Publication cũ có
  thể phục vụ lại nếu nguồn còn current và generation còn phù hợp; preview báo
  `restore_requires_new_index` khi cần tạo generation mới.
- Cleanup không xóa generation đang phục vụ nội dung hợp lệ. Nếu kho đã lưu
  trữ/xóa, hoặc generation active không còn tài liệu khả dụng, preview có thể đề
  nghị retire generation trước khi dọn. Việc retire và intent được commit trước
  I/O xóa. Lỗi Qdrant giữ action `pending` với `error_code`; gửi lại **cùng key và
  body** để hoàn tất. Không xóa namespace/vector target khác.
- Cleanup giữ manifest, raw embedding receipts, nguồn/OCR/Compiler và lịch sử.
  Khôi phục sau khi index bị dọn cần tạo index mới; không tự dựng lại từ lịch sử.

Migration hiện hành: `0001_initial_schema` … `0020_reverse_flow` (bổ sung cột biên
nhận vòng đời ngược và trạng thái `empty` của `kb_index_sync`; các migration trước
đó đã gộp vòng đời đến `0019`). Xem [hướng dẫn migration](migrations.md). Thay đổi
mã/migration không tự áp dụng lên DB đang phục vụ, không restart worker/API, không
dọn corpus hiện có.
