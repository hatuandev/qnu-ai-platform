# Phiên 584 — Phân tích 6 lỗi PDF sau benchmark

Đối chiếu PDF/MD/JSON thật và trace583; nội dung cần cho 6 câu vẫn còn. P01 phân loại heading/candidate; P05 bị chặn sau khi đã lấy đúng chú thích (thiếu raw audit nên chưa quy chính xác predicate); P07 mất khoản điều kiện vì K5/closure; P09/P10 guard ambiguous gây lỗi catalog, CT-05 còn khoảng hở grammar chú giải; P16 ReadTimeout, provider15giây. 19 probe chẩn đoán PASS, exact loader/catalog reprod không LLM; source pair và 7 trang visual kiểm tra. Import Qdrant compatibility bị network guard chặn, không coi là service PASS. Không sửa app hoặc knowledge. Người dùng sau đó giao đổi timeout, ghi riêng585.

Cwd repository; Python `backend/.venv/Scripts/python.exe`; helpers thực thi trong `.antigravity-bridge/validation/`: context584_readonly.py; context584_source.py; context584_probes.py. Các lần chốt exit0; chi tiết probe/API/runner/giới hạn ở báo cáo. Context584 còn chạy Poppler render7trang; Context585 postcheck/adjudication offline exit0. Helpers/raw evidence ignored, báo cáo không chứa key/private prompt.

Chỉ ghi báo cáo, nhật ký, snapshot và mục lục. Ngoại lệ cấu hình được người dùng giao trong585: timeout provider Luna15→30giây; không mở rộng sang model/nguồn khác. Full Pytest/FE/build hiện tại NOT RUN; full582FAIL18 vẫn lịch sử.

[Báo cáo](../bao_cao/context584/SIX_FAILURE_ROOT_CAUSE.md).
