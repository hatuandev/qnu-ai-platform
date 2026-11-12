# Rà soát và sửa văn bản sau OCR

Người dùng cần đọc đoạn văn, thấy chỗ nghi sai, sửa theo gợi ý hoặc tự nhập lại,
rồi lưu. Màn hình nghiệp vụ phải hiển thị văn bản, trang và vị trí ô bảng;
không bắt người dùng đọc JSON, evidence ID hoặc đường dẫn lưu trữ.

## Trạng thái triển khai

Từ Context654, [workflow Compiler](compiler-workflow.md) cho chọn số phiên bản
đã lưu qua `text_versions`; omission/0 vẫn là OCR gốc, không tự dùng latest.
Compiler/review/publication/index/citation cùng ghim đúng bản đã chọn.

Đợt Context651 chỉ làm API backendV1; giao diện được nối ở các đợt sau.
Không dùng role demo của frontendV1 làm quyền thật. Schema ban đầu đã nằm trong
`0001_initial_schema`; xem [migration](migrations.md). Đợt đó chỉ áp trên DB test;
từ Context929, migration áp lên DB dev có kiểm soát và `SCHEMA_HEAD` cập nhật theo.

Từ 2026-11-11, người dùng chốt quy trình **duyệt một lần ngay sau khi up tài liệu**:
giao diện V2 chỉ làm việc với bản văn bản mới nhất và không hiển thị số phiên bản.
Mỗi lần lưu vẫn tạo `ocr_text_versions` bất biến và mỗi lần duyệt ghi
`ocr_spelling_reviews` (migration `0024_spelling_reviews`) để audit và truy vết RAG;
version là dữ liệu nội bộ, không phải bước người dùng phải lặp lại.

## Trải nghiệm cần nối vào giao diện

1. Mở tài liệu OCR đã hoàn tất. Hiển thị các đoạn văn theo trang và các ô trong bảng.
2. Sau khi OCR hoàn tất, lượt soát tự động trên toàn văn bản chạy nền; người dùng
   cũng có thể chọn đoạn rồi bấm **Kiểm tra chính tả**. Chỉ rõ phạm vi đã kiểm tra;
   không nói đã kiểm tra toàn bộ nếu mới gửi một nhóm đoạn.
3. Tô sáng cụm nghi sai trong nguyên đoạn. Hiện cách sửa gợi ý và lý do ngắn.
   Các hành động là **Sửa theo gợi ý**, **Bỏ qua** và **Tự sửa**. **Bỏ qua** được
   ghi lên server theo đúng lượt kiểm tra và vị trí gợi ý, nên tải lại vẫn giữ
   trạng thái; có thể hoàn tác. Bỏ qua không sửa văn bản, không đánh dấu đã duyệt.
4. Tự sửa cho phép chỉnh cả đoạn hoặc nội dung ô. Chỉ thay text, không thay
   cấu trúc bảng/trang và mapping nguồn. Có thể sửa thủ công khi model không hoạt động.
5. Gợi ý chỉ thay nội dung đang soạn trên màn hình. **Hoàn tất duyệt** gửi nội dung
   trước/sau, phiên bản/hash đã mở và `review_check_id` của lượt soát hiện tại tới
   server; giao diện không còn bước lưu nháp riêng. Dùng cùng Idempotency-Key nếu
   gửi lại cùng yêu cầu do mất kết nối; giữ bản soạn khi có lỗi, không tự gửi lại model.
6. Mọi gợi ý và gợi ý bị withheld phải được **Sửa theo gợi ý**/**Tự sửa** hoặc
   **Bỏ qua** trước khi hoàn tất; **Bỏ qua tất cả còn lại** ghi nhận hàng loạt để
   giữ thao tác nhanh. Không thể duyệt khi lượt soát chưa `completed`, chưa phủ hết
   đoạn, chưa thuộc nội dung hiện tại hoặc đã được duyệt. Lượt đã duyệt là chỉ đọc;
   muốn sửa tiếp phải soát lại và duyệt lượt mới.
7. Chỉ báo **Đã duyệt** khi server xác nhận. Tải lại phải thấy nội dung đã lưu và
   trạng thái duyệt; nút tải Markdown/JSON ghim đúng bản đang xem.

Vị trí start/end trong gợi ý tính bằng Unicode code point, không phải UTF-16 offset
của JavaScript. UI phải dùng `Array.from(text)` khi cắt span để giữ đúng vị trí khi
có ký tự ngoài BMP. Sau khi người dùng sửa đoạn, hủy các gợi ý cũ của đoạn đó hoặc
kiểm tra lại text/span trước khi áp dụng; không thay thế chuỗi trên toàn tài liệu.

## API

Tiền tố dưới đây nối sau `/platform/v1alpha1`:

`/workspaces/{workspace_id}/collections/{collection_id}/sources/{source_id}/revisions/{revision_id}/processing-runs/{run_id}/text-review`

| Method | Phần sau tiền tố | Chức năng |
|---|---|---|
| GET | rỗng | Văn bản hiện tại, text gốc, đơn vị sửa, version và hashes |
| POST | rỗng | Lưu các thay đổi người dùng đã xem và chấp nhận |
| GET | `/document` | Tệp JSON tương ứng bản đã chọn |
| GET | `/markdown` | Tệp Markdown tương ứng bản đã chọn |
| GET | `/versions` | Lịch sử phiên bản đã lưu, mới nhất trước, kèm bản OCR gốc `0` |
| GET | `/checks` | Danh sách lượt kiểm tra cha, lọc theo `version` tùy chọn |
| POST | `/checks` | Gọi ModelOps một lần để đề xuất lỗi chính tả trong các đoạn đã chọn |
| POST | `/checks/rerun` | Xếp hàng soát lại toàn văn một version; `retry=true` chỉ khi lượt gần nhất failed/uncertain |
| GET | `/checks/{check_id}` | Đọc kết quả/trạng thái của lượt kiểm tra |
| POST | `/checks/{check_id}/dispositions` | Ghi nhận/hoàn tác **Bỏ qua** cho đúng một gợi ý đã có trong lượt |
| POST | `/checks/{check_id}/dispositions/bulk` | Ghi nhận **Bỏ qua tất cả còn lại** cho danh sách gợi ý đã có trong lượt |

GET văn bản và hai download nhận `version` tùy chọn: `0` là OCR gốc, bỏ trống
là bản sửa mới nhất. Chọn một version cụ thể để hai lượt download không lấy
hai lần lưu khác nhau nếu có người đang chỉnh sửa. Không có version trả 404.

POST lưu và kiểm tra bắt buộc `Idempotency-Key`. Request lưu gồm
`expected_version`, `expected_sha256`, và `changes` chứa `evidence_id`, `before`,
`after`; `review_check_id` tùy chọn đánh dấu đây là thao tác duyệt chính tả gắn với
một lượt soát. Request kiểm tra gồm version/hash, `evidence_ids` đã chọn, provider
tùy chọn và output budget. Không nhận URL, secret, trang/bảng hoặc actor do client gửi.

GET `/checks` trả các lượt cha (không gồm lô con) theo thời gian giảm dần; bỏ trống
`version` để thấy kết quả của mọi phiên bản văn bản. POST `/checks/rerun` nhận
`{version, retry}`: version phải tồn tại; lượt `running`/`completed`/`cancelled`
hoặc `retry=false` trả trạng thái hiện tại mà không gọi model; `retry=true` chỉ xếp
hàng mới khi lượt gần nhất `failed`/`uncertain` và giữ lượt cũ làm lịch sử. Lượt mới
kế thừa kết quả các nhóm đã xong nếu phiên bản, SHA-256, model, cấu hình và prompt
còn khớp, kể cả khi worker dừng trước khi tổng hợp nhóm vào lượt cha. Model chỉ nhận
các đoạn còn thiếu. Job id gồm version và check id khi thử lại nên request lặp
không tạo job trùng; hàng đợi
chưa sẵn sàng trả 503. Lưu vẫn chỉ chấp nhận version/hash mới nhất, nên bản lịch sử
là chỉ đọc qua API này. GET `/versions` trả mọi bản đã lưu kèm `change_count`,
`is_current` và bản `0` (OCR gốc); API giữ cho tương thích và audit, giao diện
duyệt một lần không hiển thị selector phiên bản.

POST `/checks/{check_id}/dispositions` nhận `{evidence_id, start, end, ignored}`.
Server chỉ chấp nhận đúng một gợi ý đã có trong `suggestions` hoặc
`withheld_suggestions` của lượt đã `completed`; `ignored=false` hoàn tác. Bản ghi
chỉ giữ tọa độ, không sao chép văn bản hay lời model, và không thay đổi
`ocr_spelling_runs`/`ocr_text_versions`. `POST /checks/{check_id}/dispositions/bulk`
nhận `{suggestions: [...]}` và ghi nhận hàng loạt theo cùng điều kiện; mọi phần tử
phải có trong lượt, request lặp không tạo bản ghi trùng. Danh sách lượt kiểm tra trả
kèm `ignored_suggestions` để giao diện khôi phục trạng thái sau khi tải lại. "Bỏ qua"
không phải phê duyệt văn bản và không làm giảm coverage đã kiểm tra.

### Duyệt chính tả và `ocr_spelling_reviews`

Lưu kèm `review_check_id` là thao tác duyệt: server kiểm tra lượt soát thuộc đúng
run/workspace/collection, là lượt cha độc lập (không phải lô con tự động), đã
`completed`, chưa được duyệt và có `(version, canonical_sha256)` trùng nội dung hiện
tại. Mỗi gợi ý phải được bỏ qua hoặc xử lý tại đúng tọa độ. Với `spelling_edits`,
client gửi `{start, end, replacement}` cho từng vị trí trong `changes` và server
áp lại các vị trí trên `before` để đối chiếu với `after`. Client cũ có thể gửi
`after` khớp chính xác với kết quả áp dụng các gợi ý còn lại trong đoạn. Tọa độ
không khớp trả `ocr_spelling_edit_invalid`; còn gợi ý chưa xử lý trả
`ocr_spelling_suggestions_pending`. Khi đã
bỏ qua hết, `changes` rỗng vẫn được chấp nhận và **không** tạo `ocr_text_versions`
mới; `reviewed_version` là bản đang duyệt. Khi có thay đổi, lưu tạo text version
`N+1` như cũ và `reviewed_version` là `N+1`. Bản ghi `ocr_spelling_reviews` chỉ thêm
mới, ghim check, version/hash/version_id đã duyệt, số thay đổi, người duyệt,
Idempotency-Key và request hash; gửi lặp cùng key/body trả lại kết quả cũ, dùng key
khác cho nội dung khác trả conflict. Sự kiện audit `ocr.spelling_reviewed` chỉ ghi
run/check/version/change_count.

`DetectionResponse` trả `reviewed_version`, `reviewed_sha256`, `reviewed_at`,
`reviewed_by` để giao diện nhận biết lượt đã duyệt và chặn sửa. Duyệt chính tả không
tự xuất bản hay đổi bản đang phục vụ; giao diện V2 chỉ gửi yêu cầu chuẩn bị nội dung
khi thao tác duyệt thực sự tạo text version mới.

API đọc yêu cầu membership/role hợp lệ. Tạo gợi ý và lưu cần admin/editor.
Server kiểm đầy đủ workspace → collection → source → revision → OCR run.
Quy tắc workspace chỉ áp dụng backendV1, không đổi phạm vi của backend cũ.

## Lưu đồng bộ và lịch sử

- OCR raw, canonical/Markdown gốc và manifest cũ giữ nguyên bytes.
- Mỗi lần lưu tạo một `ocr_text_versions` bất biến. Server sửa leaf text trong
  canonical, đồng bộ block text khi sửa ô và tạo Markdown từ chính JSON đó.
- Cấu trúc ô/hàng/cột, spans, header, evidence ID, bbox và revision/hash nguồn
  không được sửa từ client. Công thức/hình và bảng chưa tái dựng không sửa như prose.
- Lưu cả hai blob và đọc kiểm hash trước khi commit phiên bản. Một tệp lỗi thì
  không có phiên bản mới hiển thị. Blob ghi dở có thể còn mồ côi; chưa có GC.
- Khóa và kiểm version/hash chống ghi đè sửa đổi mới. Lưu cùng key/body trả bản
  đã tạo; key khác với version cũ trả conflict, không tự merge.
- JSON có `text_review` ghi parent, hashes trước/gốc, các thay đổi và người lưu.
  Mapping OCR vẫn là đối chiếu với nguồn gốc; text mới là dẫn xuất do người dùng sửa,
  không được tuyên bố đã xác minh ảnh chỉ vì bấm lưu.

## Gợi ý từ model

Runtime chat dùng ModelOps DB, quyền/grant, key được bảo vệ, capacity và quota
hiện có. Không có từ điển gõ tay, credential trong .env hoặc fallback giả.
Provider/đầu vào lỗi trả lỗi thật, không giả là không có lỗi chính tả.

Lượt kiểm tra được lưu trước HTTP trong `ocr_spelling_runs`, có request hash,
usage, phiên bản, phạm vi và trace. Cùng key không tự gọi model lần nữa kể cả
khi failed/uncertain. Request mất kết nối có thể xem lại cùng key; lượt quá hạn
được đánh dấu uncertain khi đọc. Không có background retry.

Server kiểm schema, ID thuộc tập đã gửi, span khớp nguyên văn, không chồng lấn và
không thay chuỗi chữ số. Sau HTTP kiểm lại quyền, provider và version hiện tại.
Raw model giữ trong BlobStore; không ghi văn bản hay credential vào log/audit.
Token không quan sát được giữ unknown/reservation, không bịa 0.

Model chỉ thấy text và có thể bỏ sót hoặc gợi ý sai. Mảng gợi ý rỗng nghĩa là
model không đề xuất lỗi trong phạm vi đã kiểm tra, không chứng minh văn bản đúng.
Chưa thử chất lượng chính tả với model thật hoặc đối chiếu ảnh nguồn.

### Lượt soát tự động trên toàn văn bản

- Lô được lập theo thứ tự đoạn, gói theo ngân sách input còn lại của runtime ModelOps
  (system prompt, dữ liệu đoạn và schema output) và trần `BATCH_SIZE`; thiếu token
  limits thì quay về lát cắt cố định như trước.
- Các lô chạy song song có giới hạn `SPELLING_BATCH_CONCURRENCY` (mặc định 3, tối đa 8)
  và không vượt `MODEL_CHAT_CONCURRENCY`; mỗi lô mở session riêng, giữ khóa
  idempotency theo offset/kích thước. Lỗi limit/context/output bị cắt chỉ chia lại
  đúng phần lỗi; lỗi khác dừng khởi động lô mới nhưng không hủy lô đang chạy.
- Kết quả ghép theo offset, không theo thứ tự hoàn tất; coverage, gợi ý bị withheld
  và gợi ý bị từ chối giữ nguyên thứ tự đoạn.
- Ảnh nhúng trên cùng một trang được OCR song song có giới hạn
  `OCR_IMAGE_CONCURRENCY` (mặc định 3, tối đa 8); ảnh trùng hash chỉ gọi provider
  một lần, checkpoint và alias ghi dưới khóa dòng để không mất cập nhật song song.

## Ranh giới Compiler và dữ liệu đang phục vụ

Các API OCR cũ vẫn chỉ phục vụ bằng chứng gốc đã ghim. Bản đã sửa được đọc/tải qua
API text-review. Yêu cầu chuẩn bị nội dung nhận `ocr_run_id` và `text_version`, kiểm
`TextVersion` tồn tại đúng run/workspace/collection (`preparation_text_version_not_ready`
hoặc `preparation_text_version_not_found` khi thiếu) rồi ghim
`CompilationInput.text_version_id` và canonical hash. Compiler, publication, index và
citation đọc đúng bản đã ghim, không tự chuyển sang bản mới nhất. Duyệt chính tả chỉ
tạo bản sửa và bản ghi duyệt; không tự tạo lại bản biên soạn, corpus hay chỉ mục đang
phục vụ. Muốn đưa bản sửa vào phục vụ phải chạy chuẩn bị nội dung → xuất bản theo
luồng hiện có và kiểm chứng provenance.

Hướng dẫn kiểm tra và giới hạn đợt này: [báo cáo651](../../docs/bao_cao/context651/REVIEW.md).
