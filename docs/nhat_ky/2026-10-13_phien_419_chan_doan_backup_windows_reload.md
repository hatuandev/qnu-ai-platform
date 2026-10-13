# Phiên 419 — Chẩn đoán backup 503 trên Windows reload

## Yêu cầu

Người dùng gửi ảnh POST `/platform/v1alpha1/backups` trả503, toast `Không thể khởi động tiến trình sao lưu độc lập.` và hỏi vì sao không được. Phiên này chỉ chẩn đoán và đề xuất; chưa sửa runtime, restart, tạo backup, khôi phục hoặc reset dữ liệu.

## Bằng chứng

- `service.launch()` dùng `asyncio.create_subprocess_exec()` trong event loop của request; exception bị chuyển thành BACKUP_LAUNCH_FAILED503, không ghi error type gốc.
- `make.ps1` chạy uvicorn với `--reload` trên Windows. Read-only process check xác nhận BE hiện có hai tiến trình uvicorn với reload=true.
- Code thư viện uvicorn được cài: `Config.use_subprocess = bool(self.reload or self.workers > 1)`; `asyncio_loop_factory(use_subprocess=True)` trả SelectorEventLoop trên Windows.
- Phép thử đọc/diagnostic mở Python child chỉ in `1`, không đọc DB/file app: WindowsSelectorEventLoop gây `NotImplementedError ''`; ProactorEventLoop exit0/output1.
- Python3.12 chính thức xác nhận SelectorEventLoop trên Windows không hỗ trợ asyncio subprocess; Proactor có hỗ trợ. [Python subprocess](https://docs.python.org/3.12/library/asyncio-subprocess.html), [Uvicorn event loop](https://uvicorn.dev/concepts/event-loop/).
- Lỗi `react-modal ... daily-companion-app` trong ảnh thuộc bundle companion, không giải thích BACKUP_LAUNCH_FAILED của POST backup.

## Kết luận và hướng sửa

Launch backup chưa tương thích Windows+Uvicorn reload. Test418 dùng pytest/default Proactor và standalone runner nên không phủ loop request thật; không có căn cứ quy lỗi cho mật khẩu, Redis hoặc hỏng database. Nhánh generic exception hiện che loại lỗi khiến thông báo khó chẩn đoán.

Đề xuất launch bằng subprocess.Popen trong worker thread (giữ hidden window, không shell, passphrase qua stdin, async offload/reap), hoặc một launcher có Proactor loop riêng. Không đổi event-loop policy toàn app/không buộc người dùng bỏ reload chỉ để né lỗi. Cần regression trên SelectorEventLoop và HTTP202 + independent runner; vẫn giữ khóa/catalogue và xử lý lỗi launch/pipe, không lộ secret trong diagnostics. Các subprocess trong runner standalone đang chạy Proactor nên cần phân biệt boundary request/runner khi sửa.

Chưa triển khai vì yêu cầu mới là giải thích lỗi. Không chạy Ruff/fullpytest/FE build cho diagnostic-only; phép thử runtime nêu trên là bằng chứng, không thay cho nghiệm thu fix.
