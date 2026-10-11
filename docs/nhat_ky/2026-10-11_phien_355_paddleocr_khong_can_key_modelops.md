# Phiên #355 — PaddleOCR không cần khóa trong ModelOps

## Mục tiêu và phạm vi

- PaddleOCR tự triển khai không yêu cầu API key; vLLM giữ yêu cầu khóa thật.
- Không sửa qnu-sso, không reset DB, không thay khóa hay cấu hình đã có, không chạy OCR lại tài liệu người dùng.

## Thay đổi

- `frontend/src/components/modelops/provider-modal.tsx`: thêm lựa chọn PaddleOCR, yêu cầu URL và ẩn trường khóa; vLLM có chú thích cần khóa trước khi sử dụng.
- `frontend/src/features/modelops/provider-detail-page.tsx` và `modelops-page.tsx`: không truy vấn/hiển thị Key Pool cho PaddleOCR; thông báo kiểm tra health không phải kiểm thử OCR.
- `frontend/src/types/modelops.ts`: khai báo các loại PaddleOCR đúng kiểu.
- `backend/app/modules/modelops/schemas.py`: preset PaddleOCR không cần khóa.
- `backend/app/modules/modelops/services/provider_service.py`: kiểm tra PaddleOCR qua GET /health không Authorization; kết nối lỗi không báo thành công. vLLM thiếu key không được báo model khả dụng; kiểm tra vLLM qua HTTP thay vì shortcut test.
- `backend/scripts/seed_ai_server_providers.py`: seed riêng hai provider AI server còn thiếu; giữ nguyên cấu hình hiện hữu. Không ghi secret vào source/.env, không tự thêm key giả.
- `backend/tests/test_paddle_provider_no_key.py`: regression cho health keyless, lỗi kết nối/503, vLLM thiếu key/401 và seed không chứa credential.

## Kiểm chứng

- Trước sửa: 2 regression thất bại đúng nguyên nhân (Paddle bị chặn thiếu key, vLLM model thiếu key bị báo thành công).
- Sau sửa: 19 test trọng tâm đạt; Ruff toàn backend đạt với cảnh báo quyền đọc thư mục runtime Windows.
- Frontend: Biome 4 file đạt, build + TypeScript đạt. Lint toàn frontend còn 15 lỗi ngoài phạm vi.
- Chạy seed riêng trên DB hiện tại: cả hai provider đã có và được giữ nguyên.
- Live Tailscale: GET http://100.105.13.53:8080/health không key trả 200, errorCode=0, errorMsg=Healthy.
- Full Pytest: 849 passed, 13 failed, 2 skipped. Cùng 13 lỗi nền phiên #354: consulting export, legacy publishing/canary/GC, reconciliation, facts lookup phụ thuộc seed live, auth session claims. Không coi health là kiểm thử OCR/embedding end-to-end.

## Lưu ý

- Seed vLLM chỉ chứa endpoint/model, không chứa khóa thật. Khóa phải nhập qua ModelOps; không lấy lại key đã từng xuất hiện trong chat.
- OCR runtime hiện có đã lấy URL/model/timeout từ DB và không yêu cầu khóa; không thay thuật toán OCR.
