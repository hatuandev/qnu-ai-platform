# Context622 — Sửa việc giữ chỉ tiêu2026=5.173 trong compiler

Ngày24/10/2026. Đã sửa và kiểm chứng **trường hợp dữ liệu2026 theo DOCX kiểm thử**. Chưa nghiệm thu toàn compiler nhiều nguồn; không thay nguồn đang phục vụ.

## Thay đổi

- Phân biệt giá trị thực sự chưa được nguồn nêu với giới hạn phạm vi. Giới hạn mùa/năm/đối tượng đặt trong scope hoặc điều kiện của giá trị đã nêu; không dùng nó tạo một factunknown trùng chỉ số.
- Repairv3 giữ các fact cũ đã được kiểm chứng, lấy đúng các fact mới đã qua truth review và cách ly phần candidate chưa đạt. Chỉ nhận tập giữ lại khi một audit độc lập xác nhận **mapping từng target→assertion thay thế** và kiểm đủ primary evidence, scope, điều kiện/ngoại lệ. Thiếu mapping, sai nguồn, thiếu coverage, lặp lại chính fact thất bại hoặc request không vừa đều chặn. Không đổi verdict contradicted thành supported.
- Gói có cả giá trị đúng và unknown sai không còn bị loại máy móc toàn bộ. Candidate gốc và danh sách fact cách ly vẫn nằm trong ledger. Đọc lại tái dựng tập giữ, mapping, coverage và review; phát hiện sửa ledger hoặc thêm lại fact sai.
- Đoạn văn không được tự tạo tên cột từ một năm. Menu span, schema gửi model và materialization cùng chặn cột trên gói có nội dung prose và không có cấu trúc bảng. Không sửa các bảng/header thật hoặc DOCX/parser.
- Instruction/schema/protocol mới tham gia configuration hash. Ledgerv2 cũ vẫn được đọc theo guard trước đây; không sửa checkpoint gốc.

Tám file ứng dụng trong `backend/storage/context622/task-scope.json`, thêm `backend/tests/test_compilation_repair_622.py`. Không thay defaults ModelOps hoặc nguồn. Route thử riêng giữ `gh/gpt-5.6-luna`, thinkingmedium và capacity động của endpoint.

## Kết quả trước/sau

| Kiểm tra | Kết quả thực tế |
|---|---|
| Baseline mới, app trước sửa | 7FAIL/2PASS, exit1; fail đúng việc cả gói bị loại và machine_complete=false |
| Regression mới bản cuối | 14/14PASS trong full cuối; gồm số/năm khác, mã có số0 đầu, unknown thật, candidate lặp fact sai, thiếu mapping/coverage, budgetNOTRUN, enum/role và ledger bị sửa |
| Focused | 98PASS, exit0; bộ rộng trước đó161PASS giữ riêng |
| Ruff | 9filePASS, exit0 |
| Full cuối | 3778PASS/18FAIL/17SKIP, exit1; vẫn là **FAIL** |
| So baseline620 | Exact18 IDs và nguyên nhân khớp, 0regression/0ID cũ bị mất; 14ID mớiPASS |
| Replay candidate62 đã lưu | PASS/exit0: giữ5.173/data2026, cách ly unknown sai, giữ verdict gốc. Mapping là fixture tất định; 0LLM/DB/network, không coi đây là live semanticPASS |

Danh sách từng ID và lỗi trước/sau: `backend/storage/context622/test-id-comparison.json`. Full lượt đầu đã dừng có chủ đích khi rà soát bổ sung guard, exit4294967295; giữ log và không tính là fullPASS. Full-stable là lượt chốt sau khi app ổn định.

## Thử thật đúng gói2026

Giữ raw hash của ba DOCX2024–2026 và catalog381proof như620; chỉ xử lý gói2026 đã lưu, với câu hỏi trực tiếp về chỉ tiêu2026. Không chạy64câu hoặc toàn tài liệu.

1. Lượt đầu6Luna calls: trích cả5.173/4.500; draft đầu gán2026thành cột prose nên reviewer từ chối, lượt sửa loại binding sai và đạt. Bằng chứng giữ tại `backend/storage/context622/live`.
2. Bản cuối sau guardprose:3calls, truth review xác nhận5.173/data2026 và giới hạn nguồn. Coverage ban đầu còn yêu cầu đối soát bối cảnh thay4.500; trạng thái này được giữ **FAIL**, không đổi nhãn hoặc gọi lại3stage.
3. Tiếp tục từ checkpoint3 đã completed, chạy đúng luồng `reconcile` hiện có bằng2CoverageAudit độc lập. Cả hai gắn proof thông báo/cập nhật vào chính assertion5.173, giữ nguyên đoạn nguồn đầy đủ với mức4.500 và số/thời điểm thông báo trong source links. Không cần tạo thêm scalar cho các số ngành/chương trình không thuộc câu hỏi.

**Kết quả gói cuối: PASS, packet_complete=true;5.173present với data2026, không có unknown giả.** Một assertion hiện hành; phần4.500 là bối cảnh cập nhật truy vết trong cùng raw proof, không phải giá trị hiện hành hoặc fact thay thế được suy từ ngày. Lưu/đọc JSON qua LocalStorage và kiểm lại coverage/repair ledger đạt. Chặng cuối là3+2calls đã hoàn tất, không resend stage; tổng toàn phiên11calls, cùngLuna/0fallback/allstop. Không ghép các lượt thử thành điểm benchmark.

Đây là kiểm chứng engine/helper thật với ModelOps được bảo vệ và Storage; **không phải HTTP/UI E2E hoặc toàn compiler ba nguồnPASS**. Hai blocker toàn compiler đã biết từ619–620 không được kiểm lại/xóa trong nhiệm vụ này.

## An toàn và giới hạn

Preflight DB/MinIO/Qdrant xác minh cấu hình local; regression dùng hai database nonce riêng, Storage local tạm, endpoint test127.0.0.1:1 và guard egress. Không migration DB thật, không ghi nguồn/index hoặc publish. ModelOps dùng credential bảo vệ đang có, không lưu secret trong docs/env.

Seals trước/sau khớp: collections, bindings, revisions, indexes, assistants, provider/default rows. Chỉ8file ứng dụng đúng scope đổi; phần app còn lại giữ nguyên. Hai DB test đã được xóa sau kiểm nonce. Storage bằng chứng giữ theo chính sách bảo vệ hiện có, không bypass xóa hàng loạt.

Không reindex, phê duyệt dữ liệu nguồn, publish, restart, deploy, stage, commit hoặc push. Chưa chạy lại64câu và chưa làm mới dữ liệu production. Backend đã tải trong process cũ không tự nhận mã mới; task này không restart dịch vụ.
