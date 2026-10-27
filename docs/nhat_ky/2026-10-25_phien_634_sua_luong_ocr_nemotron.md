# Phiên634 — Sửa luồng OCR Nemotron từ kho tài liệu đến kho tri thức

Ngày 2026-10-25. User nhấn mạnh cần OCR, không dùng kết quả native thay thế. Áp dụng qnu-clean-code-architect, qnu-backend-architect và các quy tắc ingestion/ModelOps đã đọc; sửa đúng đường truyền engine, bảng HTML, đối chiếu DOCX và giữ raw OCR.

Đã thêm ocr_engine cho request batch, giữ qua job/retry/direct processor; tương thích request hash cũ khi null. Chuẩn hóa HTML table thành GFM trên dẫn xuất, giữ raw. DOCX đối chiếu chữ đã đọc HTML với cùng ngưỡng, giữ chặn unrelated. Raw OCR DOCX lưu cùng archive Office; giữ file/ảnh gốc, source/preview hash, bbox/span. Extraction version v24 chỉ áp dụng lần parse mới, không backfill.

Kết quả thật: cả DOCX/PDF có chữ/PDF scan đều có raw Nemotron, 16/16 ô khớp, hash/raw/bbox/span PASS; native không được dùng thay ca OCR. DOCX/PDF ready_with_limitations; scan review_required do ảnh toàn trang và cấp heading chưa rõ. Giữ Quality Gate; 0 index, chưa publish/Compiler/UI. Defaults toàn cục giữ nguyên, credential qua ModelOps hiện có. Worker được nạp lại khi không có job đang chạy; API tự reload.

Baseline riêng: 4 lỗi trong 7 test đầu, entity FAIL và archive OCR FAIL được tái hiện. Focused cuối 134 PASS +23 subtest, 9 ca mới; Ruff7 PASS. Full cuối 3.835 PASS/14 FAIL/57 SKIP, exit1,439,24s; vẫn FAIL. 13 ID/cause khớp baseline; một lỗi do thiếu defaults test đã recheck1PASS với seed chuẩn trong DB test riêng. 40 ca cũ thêm SKIP vì whitelist DB cũ; không coi là PASS. Lượt test hạn chế mạng kẹt Redis đã dừng đúng tiến trình; full trung gian partial không tính PASS. Full cuối dùng DB634 riêng, Redis DB14, temp workspace/storage local và chặn mạng ngoài loopback. Hai preflight dừng an toàn và DB đã xóa; lượt full thiếu cô lập/TEMP lỗi được ghi riêng, không dùng nghiệm thu.

Cwd backend: `.venv\Scripts\python.exe -m pytest` với bảy file focused và `--tb=short -o faulthandler_timeout=30` exit0; Ruff bảy file exit0. Full `-v --tb=short --junitxml=storage/context634/full-isolated.xml`, log ở storage/context634. Live scripts `live_ocr.py --final`, `verify_live.py` exit0. Không commit/push; giữ các sửa đổi đồng thời.

[Báo cáo](../bao_cao/context634/REVIEW.md), [receipt](../bao_cao/context634/result.json), [snapshot](../memory/snapshots/2026-10-25_session_634.md).

Chốt: 9/9 ca mới634 và29/29 Nemotron631 đều PASS trong full. Catalog riêng1PASS; API tải9artifact200; source/test seal7file giữ. Toàn bộ database test tạo trong phiên đã dọn, ứng dụng chính ready200/defaults/binding giữ. Báo cáo/receipt ghi đầy đủ giới hạn, không tự bỏ cảnh báo scan.
