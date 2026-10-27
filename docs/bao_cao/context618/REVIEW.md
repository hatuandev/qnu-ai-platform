# Context618 — Bổ sung span_id tường minh cho compiler

Ngày 24/10/2026. Đã triển khai và thử đúng gói từng lỗi; full regression hoàn tất, không có regression mới. Chưa nghiệm thu toàn compiler.

## Đã bổ sung gì

`span_id` đã tồn tại trong output schema. Điểm thiếu ở lượt617 là menu gửi model dùng khóa `q…` với mảng `[evidence_id, literal]`, không thể hiện ngay vai trò nào được chọn. Bản này gửi mỗi trích đoạn thành một object rõ ràng:

| Trường | Ý nghĩa |
|---|---|
| `span_id` | ID do server sinh, bằng khóa của entry; chỉ có hiệu lực trong request hiện tại |
| `evidence_id` | Handle của proof nguồn hiện tại; ánh xạ về canonical proof khi server materialize |
| `literal` | Nội dung nguyên văn của trích đoạn |
| `start`, `end` | Vị trí ký tự Unicode trong `evidence.quote`, end không bao gồm ký tự cuối; không phải offset byte hoặc bbox toàn trang |
| `allowed_roles` | Các trường được phép chọn trích đoạn này: subject/metric/column/scalar/limitation/unit/scope.anchor hoặc heading |

Role eligibility được lấy từ chính quy tắc đã dùng để tạo enum/kiểm chứng server. Không thêm từ điển header, không mở rộng quyền dùng span để vượt lỗi. Một span được phép chọn vẫn phải qua kiểm chứng nguồn/ngữ nghĩa.

Model chỉ trả `{"span_id":"q…"}`. Không được tự gửi literal, proof, offsets hay role để sửa binding. Prompt phân biệt span ID, proof ID và record ID; record bảng có sẵn phải được chọn qua `record_ids`. Thiếu trích đoạn chứng minh vai trò thì giữ unresolved/deferred, không tạo ID hoặc giá trị giả.

Khi sai role, phản hồi JSON cho correction ghi trường yêu cầu, ID đã chọn và các role thật sự được phép. ID/chuỗi ngoài menu không được phản chiếu vào log/error; chỉ báo unoffered. Giữ giới hạn correction hiện có.

Protocol `explicit-source-span-id-offsets-and-eligible-roles/v1` tham gia fingerprint. Checkpoint cũ không bị sửa hoặc tái sử dụng dưới hợp đồng mới. Các ID `q…` không được đưa thành ID bền vững trong kho; source revision/hash và canonical proof/scopes tiếp tục là căn cứ truy vết.

## Phạm vi mã

- Mới `compilation_span_menu.py`: tạo menu và phản hồi lỗi an toàn.
- `compilation_transport.py`: gửi object rõ trường và offset basis, giữ enum role hiện có.
- `compilation_grounding.py`: hướng dẫn chọn span/record đúng loại và đúng request.
- `wiki_build.py`: bổ sung chi tiết lỗi span khi có menu, giữ hành vi của các contract khác.
- `compilation_modelops.py`: thêm version menu vào configuration hash.
- `test_compilation_span_menu_618.py`: 15 regression tests, bao gồm request builder thực với model mock.

Không sửa parser DOCX/PDF, nguồn Markdown, Structured JSON canonical, schema database, model mặc định, Quality Gate hoặc publication.

## Đối chiếu gói lỗi thật

Gói PacketDraft số28 từ Context617 giữ nguyên 24 raw proofs, 139 span lựa chọn và các record bảng đã được tạo. Đã kiểm lại raw hashes cả ba DOCX cùng snapshot381proof `59eb474ad57dc88b943504a46bc9cce8c718a302072b309c5c87022bd7f6ef66`.

- `q7` là “Số lượng”, chỉ được dùng làm column/unit/scope.anchor trong gói ấy; không phải metric được chọn cho claim.
- `q84` là “5.081”, thuộc dòng đã có table record. Nó không được dùng làm scalar của một free claim để viết lại record ấy.

Không thêm hai ID vào enum sai role. Thử lại bằng protected ModelOps, cùng GPT-OSS120B medium và capacity động: **1 lượt draft, 22.341 input / 2.234 output, stop, 0 fallback**. Model chọn một record có sẵn. Đối chiếu độc lập xác nhận entity và assertion khớp nguyên object record server; giá trị5.081 giữ frame nguồn về thí sinh nam/nữ trúng tuyển đã nhập học.

Preflight đầu thiếu collection/binding fixture khi tái dựng namespace nên dừng trước intent/inference (0 lượt gọi). Đã bổ sung đúng identity của fixture cũ và đối chiếu canonical proof trước khi gửi lượt có kết quả trên. Không gửi lại một inference uncertain.

PASS ở đây là **schema/span selection và materialization của một gói**. Semantic review, coverage review và whole compiler chưa chạy lại, không suy thành APPROVED hoặc câu trả lời cuối đã nghiệm thu. Không chạy benchmark64.

## Kiểm chứng

- Baseline trước sửa: **10 FAIL**, exit1, đúng các thiếu hụt explicit menu/role/feedback; giữ XML và ID.
- Sau batch đầu: **79 PASS**, exit0, gồm các test grounding và ModelOps compiler liên quan.
- Focused rộng: **232 PASS**, exit0; thêm checkpoint/group packing/wiki budget/JSON contract.
- Chốt sau bổ sung negative cases: **92 PASS**, exit0, gồm **15 test mới**. Giữ kiểm tra duplicate literal khác proof, Unicode offsets, heading role, ID giả/proof handle, client metadata override và fingerprint.
- Ruff6file: **PASS**, exit0.
- Full cuối: **3.759 PASS / 18 FAIL nền / 17 SKIP**, exit **1**, thời gian840,58giây trên DB/Storage test riêng. Toàn suite vẫn **FAIL**; log không thống kê riêng subtests.
- Đối chiếu với Context617 (3744PASS/18FAIL nền/17SKIP): **cùng18 test ID lỗi và cùng nguyên nhân**, không lỗi mới, không test mất,15ID thêm đềuPASS. Các lỗi nền được liệt kê tại [báo cáo617](../context617/REVIEW.md); XML và `test-id-comparison.json` giữ bằng chứng hiện tại.

Artifact riêng trong `backend/storage/context618`: baseline/focused XML, exit receipts, `live-span/preflight.json`, metrics/result và `independent-record-check.json`. Input/output có nội dung nguồn lưu bằng LocalStorageDriver dưới thư mục test có nonce, không đưa vào Git.

## Bảo toàn và bàn giao

DB/MinIO/Qdrant đã tiền kiểm loopback; pytest dùng DB mới có nonce, LocalStorage riêng, endpoint ngoài DB bị guard về127.0.0.1:1. Không migration shared/production DB. Live probe dùng đường ModelOps được phép, chỉ ghi lease/usage bình thường; không thay cấu hình hay model mặc định.

Đã dọn **hai database thử nghiệm Context618** theo nonce sở hữu. Storage chứng cứ giữ theo policy hiện có, không vô hiệu bảo vệ hoặc thử lại thao tác xóa bị chặn trước đây. Sáu nhóm shared domain seals (collection/binding/source/index/assistant/provider-defaults) khớp từ Context617; fingerprint6file đã kiểm Ruff giữ nguyên. Hash vector payload không đo lại, không tuyên bố vector audit PASS. Không reindex, publish, restart, commit hoặc push.
