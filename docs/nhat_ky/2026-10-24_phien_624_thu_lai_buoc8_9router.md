# Phiên624 — Thử lại bước8

Yêu cầu: thử lại đúng bước8 vì người dùng đã kiểm tra 9router. Đã dùng luồng ModelOps hiện có, cùng request, model và timeout; một retry riêng được người dùng cho phép.

PASS/exit0: 10,734giây, gh/gpt-5.6-luna, stop/0fallback; 52relevant+12unrelated, đủ64proof. 18.713input/1.247output. Hash request/config khớp gốc; Storage readback và seals đạt. Không gọi lại1–7, không sửa checkpoint uncertain hoặc mã ứng dụng.

[Báo cáo và giới hạn](../bao_cao/context624/RETRY_STAGE8.md). Artifact `backend/storage/context624/stage8/`; lệnh từ root: `backend/.venv/Scripts/python.exe .antigravity-bridge/validation/context624_retry_stage8.py`, exit0. Không test lại full/64, index/publish/Git hoặc đổi config.

Chưa chạy tiếp bước9. Receipt retry độc lập không đồng nghĩa job cũ đã resume hoặc toàn compiler đã được nghiệm thu.
