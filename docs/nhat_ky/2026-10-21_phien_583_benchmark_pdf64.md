# Phiên583 — Benchmark PDF frozen64

Người dùng yêu cầu chạy benchmark, tiếp theo phần so sánh DOCX/PDF. Dùng staging hiện có; không sửa ứng dụng, model, nguồn, index hay publication.

Kết quả **54/60=90.0%**, answerable 44/50, negative 10/10, social 4/4; 85% **ĐẠT**. DOCX576 lịch sử59/60; gains P06, losses P01, P05, P07, P09, P10, P16. 64/64 ID, citation 119/119 resolve; 105 Luna usage, 0 fallback/model ngoài Luna. Mọi source/config/code/vector seal giữ nguyên, 327 staging points/0 retrievable, chưa publish.

Phương pháp: authenticated server candidate snapshot, RAG service thật, persisted assistant profile/history; không phải assistant HTTP/UI E2E. 124 gold mappings hoàn tất trước inference, rubric/values giữ; draft labels chưa human holdout. Lượt harness read-only ban đầu FAIL/exit1, 0 usage ghi nhận, lưu riêng; runner được chỉnh cho ModelOps lease/audit bình thường, không sửa app.

Lệnh thật (cwd root): Python `backend/.venv/Scripts/python.exe` chạy các helper `.antigravity-bridge/validation/context583_prepare.py`, `context583_freeze.py`, `context583_run.py`, `context583_score.py`, `context583_postcheck.py`, `context583_report.py`. Preflight/freeze cuối PASS; runner exit 0; scorer exit 0; postcheck PASS. Hai script đầu có assertion thất bại khi phát hiện metadata model lịch sử stale và list split/bullet; giữ log/mapping, không gọi LLM cho phần chuẩn bị. Current full pytest NOT RUN; full58218FAIL là lịch sử.

File ghi: báo cáo583, nhật ký/snapshot/index memory; helpers và raw benchmark artifacts ignored. Không tạo dữ liệu hội thoại/gap/DB/Storage runtime cần xóa; giữ usage audit, không bypass Storage protection. Không app fix/Git writes/reindex/publish/restart/deploy.

[Báo cáo và từng ID](../bao_cao/context583/PDF_BENCHMARK64_REPORT.md).
