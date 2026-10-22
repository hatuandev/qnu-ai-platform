# Phiên 588 — PDF revision 5, wiki và benchmark 64

## Yêu cầu và phạm vi

Tạo revision mới từ PDF phức tạp đã dùng, nạp vector staging, kiểm trang tri thức
và chạy lại đúng bộ 64 câu; giữ nguyên model, chưa xuất bản, không commit/push.
Giữ toàn bộ thay đổi chưa commit từ Context587 trên nhánh `v1.0.1`.
Áp dụng skills knowledge-ingestion và rag-evaluation; không tạo agent phụ.

## Kết quả

- Đúng PDF 648.851 bytes, hash `082c412e145a9ef39ae50110ae16cc80c17d612e2f0e00f9d16ee78c7c1c3b02`.
- Revision 5 `ks_rev_697bfdc3de8e`, job `job_41be9eb5a86c`, READY_WITH_LIMITATIONS,
  0 blocker; Markdown/JSON/source fidelity PASS. Canonical 51.531 ký tự trùng
  hoàn toàn Context583; 327 block/12 bảng.
- Index staging `idx_rev_bb4c3f1a91d0`, 327 chunks/415 facts. Giữ 327 points cũ,
  tổng namespace 654 points/0 retrievable; không active publication pointer.
- **Wiki FAIL/unavailable**, 0 trang; API GET thật HTTP200 trả đúng trạng thái.
  Luna analysis thành công 35.591 prompt tokens rồi generation timeout; fallback
  Qwen HTTP400 context overflow. Không nâng timeout/context hoặc sửa mã để retry.
- Offline đo gói đầu: 23.891 ký tự text thành 107.136 JSON, gồm heading_path
  15.707 và temporal 55.540 ký tự. Compiler budget chỉ tính text, thiếu metadata,
  schema/analysis/output. Cần sửa request budgeting trong lượt triển khai riêng.
- Frozen64: **55/60 tri thức = 91,67%**, positive45/50, negative10/10, social4/4;
  mục tiêu85% ĐẠT. So58354/60: gainsP01/P16, lossF04, commonFAILP05/P07/P09/P10.
- 105 Luna success/0fallback trong benchmark; 124/124 citations resolve. 2 runtime
  errors P09/P10 ROW_ANSWER_SOURCE_INVALID; không timeout trong64. Không coi citation
  đúng là nội dung đủ đúng hoặc dùng điểm tăng để kết luận wiki có hiệu quả.
- Model/config/source ngoài phạm vi và mã app/test/FE giữ nguyên qua seals.
  Postcheck0 thread/0message/0testgap, không tạoDBtest hoặc cần xóa dữ liệu thật.

## Lệnh, bằng chứng và giới hạn

Từ root repo: `backend/.venv/Scripts/python.exe -X utf8` với các helper
`.antigravity-bridge/validation/context588_{preflight,revision,vector,prepare,run,score,postcheck}.py`.
Preflight/revision/vector/prepare/runner/scorer/postcheck exit0; vector helper
hoàn thành indexing nhưng **wiki feature FAIL**, không đánh đồng exit0 với mọi bước PASS.

Queue reparse và worker task chính thức chạy inline, ModelOps và Qdrant thật;
không restart. Kế thừa bản chép hình đã có xác nhận người dùng vì source/image
hash giữ nguyên, không ghi semantic approval mới. Benchmark qua authenticated
candidate service, không HTTP E2E chatbot đã xuất bản; nguồn/queries/rubric/spans
giữ, chỉ remap33fact IDs. Timeout30s hiện tại khác15s của583; không suy mọi gain
từ wiki (snapshot wiki_enabled=false). Không gọi judge LLM; nhãn chưa human holdout.

Không sửa app hoặc chạy full Pytest lần này; full5873026PASS/18FAIL/17SKIP là lịch
sử. Không commit/push/publish/restart/deploy, không xóa revision/vector cũ.

[Báo cáo và bảng lỗi](../bao_cao/context588/VALIDATION_REPORT.md) ·
[Kết quả](../../backend/storage/context588/summary.json) ·
[Đối chiếu đủ 64 IDs](../../backend/storage/context588/comparison.json) ·
[Postcheck](../../backend/storage/context588/postcheck.json).

Bước cần tiếp tục: sửa đóng gói wiki theo toàn payload/token budget, khử metadata
lặp bằng references, giữ validation/source evidence; rồi kiểm lại wiki trên PDF.
Chưa thực hiện việc sửa đó trong task chỉ thử nghiệm này.
