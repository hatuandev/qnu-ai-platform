# Phiên566 — Benchmark RAG 85% trên nguồn xuất bản hiện tại

Ngày 20/10/2026. Người dùng cho chạy benchmark, giữ model/source/index/publication; không reindex, xuất bản lại, commit/push. Không thay đổi mã ứng dụng.

Áp dụng skill qnu-rag-evaluation và benchmark contract. Bộ benchmark tuyển sinh cũ không khớp nguồn nên không dùng gold cũ. Đọc canonical/JSON/facts cùng published revision trong transaction READ ONLY; chốt 60 câu tri thức (50 có đáp án, 10 negative), 4 xã giao riêng, rubric và source spans trước inference. Nhãn source-checked bởi Codex, chưa có human signoff, không phải holdout.

Kết quả thực tế: **34/60 PASS = 56,67%, mục tiêu85% FAIL**; positive28/50=56%, negative6/10 theo toàn câu/lý do, social4/4 ngoài mẫu số. 9/10 negative từ chối không tạo đáp số nhưng X07/X09 thiếu lý do đúng, X08 có giải thích sai; kể cả cho10negativePASS tổng chỉ38/60=63,33%. Không đổi gold sau chạy.

64/64 actual TCP requests, HTTP200,0client exceptions/timeouts,0missing/duplicate IDs. 57/57 citation exact source hash/span, không đồng nghĩa correctness: F03 sai metric, M04 thiếu chỉ số, X05 sai đơn vị.20positive bị insufficient_context; các bảng phụ, tổng, liệt kê, tên nguồn và scope/followup vẫn có lỗi. Mọi ID và nhãn nằm trong báo cáo.

Primary Qwen giữ nguyên; 131 observed usage success,128Qwen/3Luna fallback theo policy có sẵn (M05/P12/P13). Không đổi model config, không gọi judge LLM. 361832prompt/28737completiontokens, maxprompt7495; không có MODEL_CONTEXT_EXCEEDED/EVIDENCE_CONTEXT_MISSING HTTP response. Không quy fail thành thiếu32K. p50tri thức2414,07ms/p9533939,47ms, concurrency1/cachegiữ.

Các lệnh từ root repo dùng `backend/.venv/Scripts/python.exe` và script private Context566: preflight/export_source/freeze/run_benchmark/adjudicate/verify_cleanup exit0; score cuối exit1 vì qualityFAIL. Runner exit0 chỉ là hoàn thành đo. Fullpytest/Ruff ứng dụng NOTRUN vì không sửa code; full565 lịch sử vẫn FAIL18nền, không thay nhãn.

Seals nguồn/index/assistant/provider, relevantcode, vectorgeneration và262point/payloadhash trước/sau giống nhau. DB/MinIO/Qdrant configlocal đã xác minh; không migration/schema/sourcewrite/restart/deploy. Dọn58threads/messages/29gaps mới, kiểm READONLY không còn dữ liệu chat/gap thử; oldthreads/gapfrequency giữ,131usageaudit giữ. Artifact benchmark cố ý lưu riêng `backend/storage/context566/`; không đưa rawcorpus/secret vào docsGit. Không đụng runtime cũ bị policy chặn.

Tài liệu mới: [Benchmark](../bao_cao/context566/BENCHMARK_REPORT.md), [Phương pháp](../bao_cao/context566/BENCHMARK_METHOD.md), [Từng ca](../bao_cao/context566/CASE_RESULTS.md). Cập nhật WORK_LOG, index nhật ký, PROJECT_CONTEXT và snapshot566, giữ lịch sử.

Bước tiếp: ưu tiên hiểu metric/đơn vị trong câu tự nhiên và nhiều chỉ số, identity theo nguồn thay catalog cũ, scope của bảng phụ/tổng/ngoại lệ và lời giải thích từ chối. Chưa sửa các lỗi này trong task benchmark. Không suy production readiness hoặc chất lượng mọi tài liệu từ bộ mô phỏng này.
