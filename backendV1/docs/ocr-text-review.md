# Rà soát và sửa văn bản sau OCR

Người dùng cần đọc đoạn văn, thấy chỗ nghi sai, sửa theo gợi ý hoặc tự nhập lại,
rồi lưu. Màn hình nghiệp vụ phải hiển thị văn bản, trang và vị trí ô bảng;
không bắt người dùng đọc JSON, evidence ID hoặc đường dẫn lưu trữ.

## Trạng thái triển khai

Từ Context654, [workflow Compiler](compiler-workflow.md) cho chọn số phiên bản
đã lưu qua `text_versions`; omission/0 vẫn là OCR gốc, không tự dùng latest.
Compiler/review/publication/index/citation cùng ghim đúng bản đã chọn.

Đã có API backendV1 cho văn bản đọc được, gợi ý chính tả, lưu và tải hai tệp đồng bộ.
Theo xác nhận người dùng, đợt này chỉ làm backendV1; giao diện sẽ làm sau.
Không dùng role demo của frontendV1 làm quyền thật. Schema đã nằm trong
`0001_initial_schema`; xem [migration](migrations.md). Chỉ áp trên DB test trong đợt này.

## Trải nghiệm cần nối vào giao diện

1. Mở tài liệu OCR đã hoàn tất. Hiển thị các đoạn văn theo trang và các ô trong bảng.
2. Chọn đoạn rồi bấm **Kiểm tra chính tả**. Chỉ rõ phạm vi đã kiểm tra;
   không nói đã kiểm tra toàn bộ nếu mới gửi một nhóm đoạn.
3. Tô sáng cụm nghi sai trong nguyên đoạn. Hiện cách sửa gợi ý và lý do ngắn.
   Các hành động là **Sửa theo gợi ý**, **Bỏ qua** và **Tự sửa**.
4. Tự sửa cho phép chỉnh cả đoạn hoặc nội dung ô. Chỉ thay text, không thay
   cấu trúc bảng/trang và mapping nguồn. Có thể sửa thủ công khi model không hoạt động.
5. Gợi ý chỉ thay nội dung đang soạn trên màn hình. **Lưu thay đổi** mới gửi nội dung
   trước/sau và phiên bản đã mở tới server. Dùng cùng Idempotency-Key nếu gửi lại
   cùng yêu cầu do mất kết nối; giữ bản soạn khi có lỗi, không tự gửi lại model.
6. Chỉ báo **Đã lưu** khi server xác nhận. Tải lại phải thấy nội dung đã lưu;
   nút tải Markdown/JSON phải ghim cùng version của bản đang xem.

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
| POST | `/checks` | Gọi ModelOps một lần để đề xuất lỗi chính tả trong các đoạn đã chọn |
| GET | `/checks/{check_id}` | Đọc kết quả/trạng thái của lượt kiểm tra |

GET văn bản và hai download nhận `version` tùy chọn: `0` là OCR gốc, bỏ trống
là bản sửa mới nhất. Chọn một version cụ thể để hai lượt download không lấy
hai lần lưu khác nhau nếu có người đang chỉnh sửa. Không có version trả 404.

POST lưu và kiểm tra bắt buộc `Idempotency-Key`. Request lưu gồm
`expected_version`, `expected_sha256`, và `changes` chứa `evidence_id`, `before`,
`after`. Request kiểm tra gồm version/hash, `evidence_ids` đã chọn, provider
tùy chọn và output budget. Không nhận URL, secret, trang/bảng hoặc actor do client gửi.

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

## Ranh giới Compiler và dữ liệu đang phục vụ

Các API OCR cũ vẫn chỉ phục vụ bằng chứng gốc đã ghim. Bản đã sửa được đọc/tải qua
API text-review. Compiler/publication/index hiện có chưa chọn text version này;
không tự thay đổi bản biên soạn đã tạo, corpus, citation hoặc chỉ mục đang phục vụ.
Muốn Compiler dùng bản sửa cần thêm binding version/hash tường minh và kiểm chứng
provenance qua publication/index; không đổi đường đọc ngầm sang bản mới nhất.

Hướng dẫn kiểm tra và giới hạn đợt này: [báo cáo651](../../docs/bao_cao/context651/REVIEW.md).
