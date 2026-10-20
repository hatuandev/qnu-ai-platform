# Phiên567 — Sửa RAG và đối chiếu benchmark 85%

## Yêu cầu và giới hạn

Sửa các lỗi Context566, chạy lại đúng bộ 64 câu gồm 60 tri thức và 4 xã giao; giữ nguyên gold/rubric, model/provider, nguồn đã xuất bản và index. Không reindex, republish, restart thủ công, deploy, stage, commit hoặc push. Giữ các thay đổi Context564–566 có sẵn trong worktree.

Dùng skill qnu-clean-code-architect, qnu-rag-pipeline, qnu-rag-evaluation và qnu-backend-architect. Không tạo agent phụ. Rà soát mã/diff thực tế và kiểm môi trường trước chạy. Các test dùng DB nonce/Storage riêng; DB/MinIO/Qdrant development được kiểm loopback, source/config audit READ ONLY. ModelOps credential chỉ copy bản mã hóa vào DB test, không ghi docs/log.

## Thay đổi

- Đọc nhiều đại lượng và đơn vị từ câu hỏi; ràng buộc mới thắng scope cũ ở follow-up.
- Giải tên/mã/hàng tổng bằng raw JSON và canonical source coordinates, giữ leading zero và trường chưa rõ; không dùng catalog cũ làm proof.
- Giữ câu hỏi gốc khi đổi riêng năm; chỉ sửa địa chỉ literal user quote duy nhất, không tạo fact từ lịch sử trợ lý.
- Bảng phụ hỗ trợ text/date/state; danh sách identity phải đầy đủ và đúng từng hàng nguồn.
- Khôi phục caption/figure/formula và điều kiện, giữ nhóm dependency nguyên vẹn theo budget hiện có. Table summary không được ép lên trước full rule theo thứ hạng.
- Search excerpts ánh xạ duy nhất về source unit trước audit/citation. Body ngắn dùng source-owned proof IDs; body dài giữ exact-subquote contract. Từng atomic negative và scope/conflict guard vẫn chặn; model không được ghi đè verdict bằng summary.
- Cache namespace của code lên verified-answer-v5 để không tái dùng câu trả lời trước sửa proof contract; không xóa hay đổi cấu hình Redis.
- Unit orchestration doubles khai báo ranh giới canonical mới; giữ assertion/giá trị câu hỏi. Wire fixture507 cập nhật theo private contract mới, vẫn kiểm cả verdict âm và dương.

## Benchmark thực chạy

Frozen gold SHA256 `44f56799e5a07ccba7e8711c1a1cd66e99beec18a60458e1ee509cde2167d235`; snapshot published giữ nguyên. Ba lượt riêng biệt, không ghép từng response tốt:

| Lượt | Tri thức | Có đáp án | Negative |
|---|---:|---:|---:|
| Context566 | 34/60 (56,67%) | 28/50 | 6/10 |
| Context567 Run1 | 51/60 (85%) | 45/50 | 6/10 |
| Context567 Run2 | 52/60 (86,67%) | 45/50 | 7/10 |
| **Context567 Run3 cuối** | **51/60 (85%)** | **44/50 (88%)** | **7/10** |

Cuối 64/64 HTTP200, social4/4 ngoài mẫu số, citation93/93 giải đúng canonical hash/span/quote. 109 usage calls đều qwen3.5-9b thành công, không fallback; cấu hình chuỗi fallback giữ nguyên. Max prompt8650 tokens, không lỗi context window trong lượt cuối.

X05/X08 của hai lượt đầu được đối soát lại theo rubric có sẵn: từ chối chung chưa đủ lý do đơn vị/đại lượng, nên chuyển PASS→FAIL; initial grading giữ riêng, gold/rubric không đổi. Không dùng điểm chấm sơ bộ đã cao hơn để nghiệm thu.

Còn 9 FAIL: P03, P06, P07, P08, P11, P15, X05, X08, X09. Gồm thiếu điều kiện, từ chối quá mức, diễn giải thừa mâu thuẫn và lý do từ chối chưa rõ. Đạt ngưỡng không đồng nghĩa sửa hết hoặc APPROVED toàn hệ thống. Bộ đã dùng để sửa mã, chưa có human gold signoff độc lập và chưa phải holdout.

## Kiểm chứng và cleanup

Red snapshot bất biến: 10FAIL/1PASS. Focused intermediate349PASS; audit stable118PASS; wire-contract-final49PASS; Ruff36filePASS. Các lượt full giữa còn lỗi fixture mới và 18 lỗi nền; không coi là PASS. Gate cuối: **2785PASS/18FAIL/17SKIP,23subtestsPASS,exit1**, đúng18ID/nguyên nhân nền Context565;38case thêmPASS,0ID cũ mất/đổi status,0newFAIL. Lượt full trước20FAIL gồm2wire fixtures507 đã cập nhật và kiểm lại49PASS trước full cuối. DB test đã drop và xác minh ownership. Xóa runtime567 riêng bị kiểm duyệt tự động chặn với lý do “blocked by policy”; giữ2969file/43.855.156byte,0tracked/0reparse, không retry hoặc bypass. Evidence/usage giữ. Chuẩn hóa CRLF của test_rag.py sang LF sau khi kiểm byte UTF-8 hợp lệ, không đổi logic.

Exact commands, exit codes, JUnit, code/source/config/vector seals và response/proof records giữ ignored dưới `backend/storage/context567/`. Benchmark đã dọn 58 threads mỗi lượt, 13/10/12 gaps tương ứng; 0 test threads/messages/gaps còn lại, dữ liệu trước đó giữ, usage audit giữ.

Không kiểm frontend, tải/SLA, retrieval ablation hoặc production. Báo cáo đối chiếu cuối: [BENCHMARK_REPORT](../bao_cao/context567/BENCHMARK_REPORT.md), [CASE_COMPARISON](../bao_cao/context567/CASE_COMPARISON.md), [VALIDATION_REPORT](../bao_cao/context567/VALIDATION_REPORT.md).
