# Context611 — Compiler thật và kiểm chứng checkpoint

Thực chạy trên ba DOCX 2024–2026, canonical/hash từ parser602,381proof. Chỉ override route trong harness thử qua ModelOps/9router; gh/gpt-6-luna vẫn là primary đang cấu hình. Server policy thử: medium/output8192/context24000,12primary/gói,30gói,64calls/600s mỗi lần thực thi,tổng128calls. Không thay source/Quality Gate/index/publication.

## Kết quả

**Phần request budget/checkpoint hoạt động; toàn compiler FAIL, chưa có bundle hoặc Markdown cuối.** Không coi usage thành công là semantic approval.

| Quan sát | Kết quả |
|---|---|
| Native inference qua ModelOps |96 lượt, cùng gpt-oss:120b,0fallback |
| Payload thực |Cả96 lượt gửi reasoning_effort=medium,max_tokens=8192 |
| Kết thúc output |96/96 finish=stop;0length exhaustion |
| Usage |482.090input/151.499output tokens |
| Max output/input |5.295/6.244tokens |
| Tổng dự phòng request đã gửi lớn nhất |24.000/24.000, không bỏ guard |
| Lượt đầu |54calls,346.327,61ms;HTTP422 complete_request_budget trước coverage kế tiếp |
| Tiếp tục |Dùng lại nguyên54stage cũ, chỉ42calls mới,310.829,08ms |
| Checkpoint cuối |96ordinal duy nhất,91completed và5JSON/schema rejected;0started/uncertain inference stage |
| Kiểm object/audit |Đọc lại91object và chuỗi audit đúnghash/identity/actor; parent references giữ nguyên |
| Chặn cuối |92entities>64,145assertions>128 ở CompilationDraft.model_validate;HTTP502/generic failure receipt |

Upstream không echo effort hoặc reasoning-token details. Đã chứng minh app gửi medium trong request thật và nhận response model đúng; chưa có chứng cứ độc lập 9router/upstream đã thực thi mức đó. Không lưu/log nội dung reasoning.

Lượt đầu dừng ở coverage request có24existingassertions, dự phòng25.459>24K; chặn trước inference. Sau thu gọn **không mất dữ liệu**, payload này còn23.076, có feedback ngắn là23.128, đều gồm8192output. Giữ24assertions và toànraw evidence; repeated attribute/state/scope/time/qualifier fields dùng bảng chia sẻ, mở rộng ngược khớp chính xác. Những payload đã chạy trước thay đổi này không đổi identity; replay ngoại tuyến đọc lại52completed/2rejected cũ,0inference mới, rồi tiếp tục ở request chưa từng gửi.

## Checkpoint khác retry không xác định

Job đầu kc_5e5a7328b0ba42fbbf9150601303b8eb dừng khi **chưa bắt đầu** call tiếp theo; tất cả54stage đều có trạng thái xác định. Server kiểm prefix/hash/config/source/quyền/version rồi cấp job tiếp tục kc_182025997c28481f83f32890cc2ce77f. Không gửi lại bất kỳ stage started/uncertain nào, không import debug output610 thành checkpoint, không lặp selection24calls.

Job cuối uncertain tại lỗi ghép xác định, toàn96stage vẫn bền vững. Đọc lại ở process mới tái hiện lỗi mà không gọiLLM;91valid responses được dùng lại,5rejections có feedback giữ riêng. Không tiếp tục lần nữa vì lỗi cardinality được tái hiện xác định; retry model không giải quyết được bước ghép này.

Receipt run-complete.json kế thừa ở thư mục live-oss-resume1 từng chọn nhầm job cha vì thứ tự JSON registry không là thời gian. Không dùng ID đó để kết luận hoặc gửi lại. Đối soát read-only chọn max(created_at) xác nhận job mới ở **latest-job.json**, checkpoint-durable-summary.json và live-summary.json. Giữ receipt ban đầu để truy vết, không sửa DB để làm khớp báo cáo.

## Giới hạn còn lại

Giới hạn64entities/128assertions của hợp đồng tổng vẫn giữ nguyên. Tất cả92entity và145assertion khác nhau theo so sánh chính xác cả nội dung/bằng chứng/entity liên quan; không có duplicate tuyệt đối để gộp cơ học. Điều này không chứng minh chúng đều là fact đúng hoặc đúng topic; cần review scope/relevance và thiết kế bản biên soạn phân cấp/nhóm kết quả có kiểm chứng nếu muốn xử lý dung lượng lớn hơn. Không tăng cap, tự bỏ bớt hoặc gộp ngữ nghĩa để đạt PASS.

Các bước selection/extraction/item review/coverage đã thực chạy. Chưa đến synthesis/direction review hoặc Quality Gate cuối. Chưa kiểm chatbot64câu, source parser mới, browser E2E hoặc publication. Compiler code chưa được dùng để duyệt nguồn cũ.

## Evidence

Artifacts local dưới backend/storage/context611, không đưa corpus private vào Git: live-oss và live-oss-resume1 chứa wire request/response shapes, phase summary, intents/receipts; live-summary.json, latest-job.json, checkpoint-durable-summary.json, exact-duplicate-check.json và live-oss/offline-replay.json là đối soát cuối. merged-draft-private.json chỉ để phân tích giới hạn; không approval. packing-preflight.json dùng selection610 chỉ để xem dung lượng, không tái sử dụng vào live inference.

Hai vòng ModelOps dùng DB local qnu_test_context611_d27c688eeb4b và LocalStorage riêng. SharedDB không migration/source writes; credentials chỉ giải quyết trong ModelOps, không sao chép sangDBthử. Postcheck và cleanup nằm trong báo cáo kiểm chứng cuối, không suy từ báo cáo thiết kế.
