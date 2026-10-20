# Phiên576 — Sửa N18/B03 và regression theo nguyên nhân chung

Context576: ranh giới thuật nguồn/giả định/đánh giá hồ sơ; 44 regression mới PASS, focused 393 PASS, Ruff 15 file PASS; frozen64 59/60 = 98.33% (baseline 59/60), social 4/4; N18 PASS, B03 PASS trên code chốt; còn P06. Full 2949 PASS / 18 FAIL / 17 SKIP, không có lỗi pytest mới theo ID/nguyên nhân. Dọn: DB_REMOVED_STORAGE_POLICY_BLOCKED; model/nguồn/index giữ nguyên; không commit/push/reindex/publish/restart/deploy.

- [Nguyên nhân và mã](../bao_cao/context576/ROOT_CAUSE_AND_IMPLEMENTATION.md)
- [Kiểm chứng](../bao_cao/context576/VALIDATION_REPORT.md)
- [Đối chiếu64](../bao_cao/context576/CASE_COMPARISON.md)
- [Test mới](../bao_cao/context576/REGRESSION_CASES.md)

Lệnh thật dùng Python từ `backend/.venv/Scripts/python.exe`: `-B backend/storage/context576/checks.py run --label full-position tests`; `-B backend/storage/context576/position64/run.py`; `-B backend/storage/context576/position-probe/run.py`; `-m ruff check` trên13 file ứng dụng được liệt kê tại `changed-app-files-position.json` và test575/576. Cwd repo; pytest chạy cwd backend, receipts có exit code và test ID.

Các lần ngắt và lỗi batch trước giữ nguyên log, không lấy retry làm kết quả cũ. Source parser/Markdown/JSON không sửa trong576. Tiếp tục đo trên tài liệu/câu hỏi chưa tham gia phát triển trước khi kết luận tổng quát; không tự restart backend đang chạy.
