# Phiên599 — Sửa P06/X09 và kiểm chứng điều kiện nguồn

Ngày22/10/2026, nhánh v1.0.1. Người dùng yêu cầu sửa ngay sau phân tích598.
Giữ model/nguồn/index/gate; không parser/reindex/publish/restart/commit/push.

## Thay đổi

- Repair tách ý trả lời còn thiếu khỏi điều kiện; tối đa2 vòng, feedback mới nhất,
  giữ claim an toàn và kiểm lại. Sau copy điều kiện, qualifier chưa đạt được chọn
  lại nguồn. Trace có lý do dừng, không tự duyệt verdict chưa đạt.
- Audit phân biệt nội dung ô với nhãn cột và kiểm đúng scope/ngoại lệ.
- Điều kiện mới đang bất đồng được đối chiếu source-only trước khi ghi nghĩa vụ;
  proof gắn clause/question/plan/nguồn/target. Giữ nghĩa vụ đã xác nhận, chặn ID,
  revision/target sai hoặc unresolved. Tối đa1 lượt đối chiếu thêm, ngoài2 review
  sẵn có; không thêm vòng để chạy đến khi model đồng ý.
- Không whitelist số trong query, không gán thiếu=0 hoặc tạo Q khi thiếu input.
- Chỉ5 file app RAG khác baseline trước599; thêm2 file test và cập nhật adapter
  một test597, giữ assertion cũ. Các thay đổi chưa commit ngoài phạm vi được giữ.

## Kiểm chứng thực chạy

| Kiểm tra | Kết quả | Exit |
|---|---|---:|
| Baseline ban đầu | 2 lỗi mất facet,1 fixture lexical,5 API chưa có;8 FAIL | 1 |
| Baseline hành vi hồi cứu trên mã cũ đã seal | 1 FAIL đúng vì latching điều kiện thừa,1 PASS giữ tiền đề | 1 |
| Focused mã bàn giao | 784 PASS,1 warning version-check bị endpoint test từ chối | 0 |
| Ruff8 file | PASS | 0 |
| Full mã bàn giao | 3294 PASS,18 FAIL nền,17 SKIP,23 subtest PASS | 1 |
| ExactID/cause so full597 | 0 lỗi mới/đổi cause/mất test;19 test mới PASS | 0 |
| Live6 câu bàn giao | P06/P07/P10/P12/P16/X09:6/6,39/39 citations,40 Luna/0fallback | 0 |
| Postcheck nguồn/model/code/vector/publication | Giữ nguyên;2943point/0retrievable | 0 |
| Cleanup DB sở hữu riêng | Đã xóa và kiểm không tồn tại | 0 |

Giữ probe trung gian5/6 (lỗi hợp đồng P06) và4/6 (audit P12, budget P16) riêng.
Đã sửa hợp đồng lặp, proof cache qua vòng và chọn lại qualifier; không ghép điểm.
Source-rubric được chấm theo actual response có hash, kiểm canonical/span độc lập,
không gọi judge LLM. Đây là candidate service integration, không HTTP/browser E2E.

Full/Focused chạy bằng Python venv trong DB test có nonce, local Storage riêng,
endpoint ngoài `127.0.0.1:1`; kiểm loopback DB/MinIO/Qdrant trước chạy. Không schema
change trên DB ứng dụng. Lệnh/cwd/exit/test IDs nằm trong receipt của
[báo cáo](../bao_cao/context599/IMPLEMENTATION_AND_VALIDATION.md).

DB599 đã dọn; Storage runtime/evidence giữ theo policy bảo vệ đã có. Không thử lại
xóa đệ quy từng bị auto-review chặn. Không tạo chat/message/gap; giữ usage audit.
Full64/FE build/published E2E NOT RUN;58/60 của597 vẫn là lịch sử. Chưa nghiệm thu
toànRAG hoặc ưu tiên wiki4–6. LLM vẫn có thể bất đồng, cần báo lỗi thật và giữ gate.
