# Context651 — Rà soát và sửa văn bản hậu OCR

## Yêu cầu và phạm vi

Người dùng muốn thấy cả đoạn có lỗi, chọn sửa tự động theo gợi ý hoặc tự sửa,
rồi lưu cập nhật Markdown/JSON. Không dùng danh sách toàn mã thay cho văn bản.
Đợt này đã làm contract và luồng backendV1. Người dùng xác nhận chỉ làm
backendV1 trước, giao diện làm sau. FrontendV1 hiện là khung KTX mẫu. Không đổi egress,
auth/demo hoặc sửa UI trong đợt này. Không migrate DB phục vụ hoặc restart.

## Kết quả mã

`backendV1/qnu/domains/ocr/review/` chứa schemas, leaf projection, append-only
text versions, lưu đồng bộ và spelling inspection. `0011_ocr_text_review` tạo
hai bảng v1 riêng. Routes, ownership, migration env/test fixture được đăng ký.
Tham chiếu [API/UX](../../../backendV1/docs/ocr-text-review.md).

- GET trả text, text gốc, trang/ô, bbox và phiên bản; không buộc UI đọc JSON thô.
- Gợi ý model có span và nguyên văn; không ghi text. Dùng ModelOps hiện có,
  reserve/settle usage, raw giữ trong BlobStore, không fallback/auto resend.
- POST lưu là chấp nhận chính xác các thay đổi trước/sau trên version/hash đã mở.
  Sinh đồng thời hai artifact có hash; chỉ commit khi lưu/đọc kiểm cả hai đạt.
- Bảng chỉ sửa leaf, đồng bộ text ở block, giữ ô số, empty, spans và nguồn.
- Workspace authorization áp dụng riêng v1. Read có membership; save/check cần
  editor/admin. Có kiểm lại membership, provider và version sau HTTP.
- Idempotency cho cả lưu/kiểm tra; optimistic concurrency + khóa, từ chối ghi đè.
- Lượt kiểm tra có running/completed/failed/uncertain, expiry/fence, không resume HTTP.

## Kiểm chứng đã chạy

Từ `D:/DuAnPhanMem/qnu-ai-platform/backendV1`, wrapper ignored
`storage/context651/run_checks.py` gọi harness DB test riêng. Các lượt đầu dùng
suffix650 rồi đổi tên test/artifact sang651 khi phát hiện Context650 đã dùng
cho bản sao FE. Giữ nguyên log/XML cũ và không sửa báo cáo Context650.

| Lượt | Kết quả |
|---|---|
| Baseline `tests/integration/test_ocr_text_review_650.py -q` | 1 FAIL đúng API thiếu/404; 5,61s, exit1 |
| Smoke API + ORM/migration | 2 PASS, 5,36s, exit0 |
| Focused review + ORM | 18 PASS, 46,51s, exit0 |
| Concurrency/revocation/provider | 4 PASS, 17 deselected, 13,87s, exit0 |
| Race baseline: hai check cùng key | 1 FAIL, 21 deselected, 6,35s, exit1; tái hiện khe hở sau commit quota |
| Race sau sửa | 1 PASS, 21 deselected, 5,79s, exit0; chỉ một lượt model/quota |
| Full đầu | Dừng sau khi phát hiện race mới; progress có F chưa chẩn đoán, exit4294967295, harness508,69s; không PASS |
| Full tuần tự tiếp theo | 435 ca đã chạy, 434 PASSED/1 FAILED ở mức case; kẹt shutdown Proactor/TestClient sau100%, dừng đúng pytest child, exit4294967295/harness983,92s; không PASS |
| Regression downgrade sau sửa | 1 PASS/7,69s/exit0; giữ nguyên test, sửa thông báo migration thành `evidence must be preserved` |
| Full cuối, sáu nhóm độc lập | **435 PASS/0 FAIL/0 ERROR/0 SKIP**, tất cả exit0; 413 ca cũ giữ đủ,22 ca mới,0 trùng/0 mất |
| Ruff scoped + format check | PASS, 14 files; lỗi biến thừa ở lượt đầu đã sửa |
| Hash legacy | 475 file `backend/app` khớp baseline649 |

22 ca review mới gồm round-trip MD/JSON/gốc/lịch sử/replay, ô bảng, stale version,
key/body conflict, sai span/before/extra/duplicate, quyền và sai scope, tệp thứ hai
lỗi, gợi ý sai/overlap/đổi số, provider lỗi, quyền/model/text đổi giữa HTTP và cùng
key đồng thời. Tạo durable unique request trước khi reserve quota để không mở
khe hở do usage service tự commit. Không đổi usage service hoặc guard/quota cũ.
Model và OCR là HTTP loopback giả lập, persistence/BlobStore là thật trên DB riêng.
Các ca có gợi ý kiểm chữ hoa chỉ kiểm contract, không chứng minh chất lượng chính tả.

Một lượt baseline đầu trong môi trường hạn chế bị kẹt trước kết nối DB; đã dừng
đúng bốn process được xác minh. Lượt chạy có quyền kết nối test tái hiện404 và
dọn DB thành công. Không tự bật/restart hạ tầng.

Full cuối chia file integration thành3nhóm65/78/79ca; unit+migration210ca,
contract2ca và invariant1ca trên DB riêng. Không deselect/skip ca nào; union XML
đối chiếu với413nodeID649 và có đủ22nodeID mới. Ba nhóm integration và nhóm
unit/migration chạy đồng thời trong293,28s; tổng thời gian case của sáu nhóm849,62s.
Không phải một process full PASS: đó là toàn bộ suite qua các nhóm độc lập.
Lượt tuần tự trước có lỗi thông báo downgrade của migration0011 (test639 không đổi)
đã sửa và tái hiện PASS. Windows shutdown hang cùng dạng stack648 chưa sửa nguyên
nhân; không che lượt bị dừng bằng kết quả nhóm sau.

Kiểm tra cuối: Ruff/format14file PASS, OpenAPI70path/95operation và65path cũ giữ
nguyên contract; UTF-8 không BOM/LF và local links mới PASS. 475file legacy khớp649.
16 tên DB của phiên được kiểm lại,0còn;0collection vector v1 quan sát. Receipt giữ
sentinel/version legacy, không dọn hoặc reset dữ liệu chung. Bằng chứng ignored
ở `backendV1/storage/context651/{test-summary,cleanup-verification,scope-verification}.json`
và sáu `full-final-*.xml`; danh sách file bốn nhóm đầu ở `full-final-partitions.json`.
Hai lệnh bổ sung là `tests/contract -q` và `tests/invariants -q`, cùng wrapper.

## Giới hạn và phần cần tiếp tục

- Theo phạm vi đã chốt, giao diện làm sau; chưa chạy browser/build FE.
- Chưa gọi model thật, đánh giá lỗi tiếng Việt hoặc đối chiếu ảnh. Không công bố
  accuracy/recall hay khả năng sửa đúng. Tên riêng/thuật ngữ vẫn có thể bị gợi ý sai.
- Compiler/publication/index vẫn ghim OCR gốc; chưa chọn bản text review mới.
  Cần nối version/hash và provenance tường minh nếu người dùng muốn dùng tiếp.
- Ghi blob thành công một phần nhưng DB không commit có thể để blob mồ côi; chưa GC.
- Chưa lưu trạng thái Bỏ qua trên server hoặc background resume; gợi ý đã chọn chưa
  được lưu vào text cho đến khi POST lưu. Chưa giới hạn lưu text theo số trang UI.
- Hai cảnh báo Starlette/AnyIO đã có trước; không thay dependency trong đợt này.

Không commit/push, không thay ModelOps/secret/default, không publish/reindex hoặc
chạm dữ liệu thật. Giữ mọi sửa đổi trước phiên trong backend và frontendV1.
