# Vòng đời ngược của tài liệu và chatbot — backendV1

Tệp dẫn xuất mồ côi có [luồng dọn riêng](storage-cleanup.md); phục hồi DB/tệp/vector
vào đích mới theo [recovery v1](recovery.md). Các thao tác này không purge nguồn
gốc hoặc đổi ý nghĩa thùng rác của lifecycle bên dưới.

Phạm vi: chỉ `backendV1/`; workspace là biên quyền theo ADR v1. Mọi thao tác
được kiểm tra bằng actor thật và membership/role ở server. Không áp dụng cho `backend/`.

## Thao tác hỗ trợ

| Tài nguyên (`kind`) | Thao tác (`action`) | Kết quả |
|---|---|---|
| `collection`, `source`, `document` | `archive`, `delete`, `restore` | Lưu trữ, đưa vào thùng rác hoặc khôi phục; giữ nguồn và lịch sử |
| `assistant` | `pause`, `resume`, `archive`, `delete`, `restore` | Ngừng/bật phục vụ hoặc đưa vào thùng rác; khôi phục xong vẫn tắt, cần bật riêng |
| `conversation` | `archive`, `delete`, `restore` | Chỉ chủ hội thoại được thao tác, kể cả khi người khác là quản trị |
| `job` | `cancel` + `job_kind` | Hủy OCR, Compiler, index, review tự động, review ngữ nghĩa, kiểm chính tả hoặc lượt hỏi |
| `index` | `cleanup` | Xóa collection vector v1 và chunk DB của generation đã ngừng dùng |
| `document` | `replace` + `replacement_version_id` | Chuẩn bị chỉ mục cho bản đã duyệt, rồi chuyển publication và index trong một transaction |

`delete` là **xóa có thể khôi phục**, không xóa vĩnh viễn file gốc, raw OCR,
Markdown/JSON đã lưu, quyết định duyệt hay lịch sử hội thoại. Tài nguyên bị xóa/lưu
trữ bị chặn trên API đọc nội dung, tải tệp, tác vụ và RAG; kết quả hỏi đáp cũ phải
kiểm lại nguồn trước khi trả về. Tài nguyên con vẫn bị chặn nếu kho cha bị lưu trữ/xóa.

## API dùng cho giao diện quản trị

Prefix: `/platform/v1alpha1/workspaces/{workspace_id}/lifecycle`.

1. `POST /previews`: gửi `kind`, `resource_id`, `action`, `reason` và tham số riêng
   nếu có. Trả `impact`, `id`, `preview_sha256`, thời hạn. Bản xem trước chưa đổi trạng thái tài nguyên.
2. `POST /actions`: gửi `preview_id`, `preview_sha256` cùng header
   `Idempotency-Key`. Server kiểm lại người xác nhận, quyền, thời hạn, trạng thái
   và phạm vi ảnh hưởng. Thay đổi sau preview trả `409`, cần xem trước lại.
3. `GET /actions/{action_id}`: trạng thái và biên nhận của thao tác do chính actor tạo.
4. `GET /resources?limit=50&offset=0`: các tài nguyên đang lưu trữ/thùng rác.
   Hội thoại của người khác không xuất hiện. API có `Cache-Control: private, no-store`.

Ví dụ thân yêu cầu xem trước, không chứa quyền hay trạng thái do client tự cấp:

```json
{"kind":"source","resource_id":"<source_id>","action":"delete","reason":"Thay tài liệu cũ"}
```

`impact` cho biết số phiên bản xuất bản, tác vụ và phạm vi chatbot/hội thoại có thể
bị ảnh hưởng; việc giữ nguồn gốc; có cần index mới sau khôi phục; và có ngừng index
đang active khi dọn hay không. Duyệt/thu hồi publication hiện có vẫn dùng API riêng.

Quyền: admin cho xóa tài liệu/kho, quản trị chatbot, thay publication và dọn index;
admin/editor cho lưu trữ tri thức và hủy tác vụ xử lý. Khôi phục tài nguyên đã xóa
cũng cần admin. Chủ hội thoại tự quản lý hội thoại/lượt hỏi của mình.

## Thay bản mới khi bản cũ vẫn phục vụ

1. Nạp vào `POST .../sources/{source_id}/revisions` với form `staged=true`.
   `current_revision_no`/`revision_count` vẫn cho biết bản mới nhất được tải lên;
   `serving_revision_no` chỉ bản được phép phục vụ. Tệp cũ giữ nguyên.
2. Chạy OCR → sửa văn bản nếu cần → Compiler → review → đăng ký phiên bản mới.
3. Duyệt (`approve`) phiên bản mới bằng luồng publication có sẵn.
4. Preview/accept `document/replace`, chọn `replacement_version_id` đã duyệt.
   Người thực hiện phải có membership admin của đơn vị để worker kiểm lại quyền;
   quyền quản trị nền tảng ở request không được sao chép thành quyền worker.
5. Action trả `pending` và `result.index_run_id`. Worker hiện có xây generation mới,
   kiểm lại bundle, nguồn, quyết định duyệt, model và quyền qua từng checkpoint.
6. Khi vector/manifest sẵn sàng, transaction cuối chuyển serving revision, xuất bản
   phiên bản mới, supersede bản cũ và đổi active index. Sau đó action `completed`.

Lỗi trước khi hoàn tất giữ publication/index cũ. Lỗi storage/vector có thể retry
theo chính sách index hiện có; embedding đã lưu không bị gửi lại. Lỗi model hoặc
trạng thái không rõ không tự gửi lại. Action `failed` cần yêu cầu mới sau khi xử lý
nguyên nhân; không tự sửa thành công hay reset run cũ.

Nếu một revision nguồn dùng chung còn được văn bản khác xuất bản, chuyển serving
revision có thể làm văn bản đó cũ đi. Server trả `replacement_shared_source` và
yêu cầu thu hồi hoặc chuẩn bị thay thế đồng bộ trước. API `replace` hiện thay một
compiled document mỗi lần, chưa hỗ trợ batch nhiều document dùng chung nguồn.

Không truyền `staged=true` thì giữ hành vi cũ: nạp revision mới làm bản cũ thành
stale; người vận hành cần biên soạn/duyệt/index lại. Không có tự động OCR hoặc xuất
bản ngay khi upload.

## Dừng, khôi phục và dọn

- Hủy có trạng thái `cancelled` bền vững. Worker không nhận lại job đó và không
  nhận kết quả đến muộn thành đầu ra hoàn tất. Hủy auto-review cũng hủy lượt review
  con đang chạy. Tạm dừng/xóa chatbot hủy lượt hỏi đang chạy của chatbot.
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

Migration hiện hành: `0001_initial_schema`, đã bao gồm vòng đời đến0015 cũ.
Xem [hướng dẫn migration](migrations.md). Thay đổi mã/migration không tự
áp dụng lên DB đang phục vụ, không restart worker/API, không dọn corpus hiện có.
