# Phiên 390 — Vì sao restart backend vẫn EMPTY_OCR_PAGE

## Phạm vi

Chẩn đoán read-only đợt mới `imp_batch_9442e88b7abb`. Không sửa code, restart/kill worker, retry item, reset, duyệt hoặc xuất bản dữ liệu.

## Bằng chứng

- Item `imp_item_30daa5203df8` failed EMPTY_OCR_PAGE trang8; created 2026-10-12 14:58:35 UTC, updated14:58:42 UTC (21:58 giờ Bangkok).
- SHA256 origin và bản gốc cùng `9ce217e5ba3c43d4c083f59a3f080b98fadb10e1f5e8bb665e3796cd76688db8`; không phải tệp khác.
- Worker state tại backend/storage/worker_logs/local-worker.json trỏ PID10008; Get-Process và CIM xác nhận chính backend/.venv python -m arq app.workers.arq_worker.WorkerSettings của repo, start19:41:01.
- blank_pages.py bản sửa có LastWriteTime20:07:49, sau lúc worker khởi động. Worker không reload module khi backend riêng restart.
- scripts/start-worker.ps1 dòng15–17 kiểm PID/startTicks còn sống thì in Worker already running và return; make dev/make worker đều dùng script này nên không thay worker cũ.
- Gọi bộ nhận diện hiện tại trên đúng SHA của PDF: is_blank=true, raster-components-v2, foreground221/largest33. Code hiện tại giữ manifest blank và không ném EMPTY_OCR_PAGE cho trang này.

## Kết luận và bước tiếp theo

Nguyên nhân tác vụ mới vẫn lỗi là worker giữ bản guard cũ trong bộ nhớ, không phải restart backend làm tải lại worker. Cần dừng đúng worker repo rồi start worker mới, sau đó user retry mục lỗi. Chưa thao tác vì yêu cầu hiện tại là hỏi nguyên nhân; không có quyền suy diễn dừng tiến trình. Đề xuất launcher có restart rõ ràng/check phiên bản trong dev để tránh hiểu nhầm ở lần sau.

## Kiểm tra

SELECT PostgreSQL READ ONLY, đối chiếu SHA256, process identity/start time, mtime, launcher và chạy trực tiếp blank classifier. Không chạy full Ruff/Pytest/Vite do không sửa code ứng dụng. Lượt kiểm thử trước bị user ngắt không coi là kết quả xác nhận mới.
