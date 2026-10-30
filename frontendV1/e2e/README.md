# V1 E2E theo từng chặng

Luồng model QNU thật đến upload/purge: [Hướng dẫn tổng hợp lệnh theo thứ tự](../../docs/quy_trinh/V1_TEST_TOAN_LUONG_MODEL_QNU.md).

Hướng dẫn chính: [Chạy V1 E2E từng bước](../../docs/quy_trinh/V1_E2E_TUNG_BUOC.md).

Model thật: [QNU discovery/chat/embedding/rerank/OCR](../../docs/quy_trinh/V1_TEST_MODEL_QNU.md).

Từ thư mục gốc: `test-v1-e2e.ps1 init`, `serve`, rồi `run <stage>` ở cửa sổ khác.

`run provider-setup --headed` kiểm nhà cung cấp/khóa/kết nối/đăng ký model trước model-discovery; khóa nhập ẩn qua terminal, chỉ lưu ModelOps DB. Sidebar Nhà cung cấp mở trực tiếp `/providers`.

Suite nghiệp vụ lấy `e2e/stages/workflow.spec.ts`; chặng `model-*` lấy `e2e/stages/models.spec.ts`. `E2E_STAGE` chọn đúng một bài; nhóm model chỉ chạy trong phiên live.
Runner giữ checkpoint và báo cáo riêng. Các spec `01_...09_...` là bản khung cũ,
không phải bằng chứng đã kiểm chứng. Không gọi trực tiếp suite khung để nghiệm thu.

Chế độ mặc định dùng upstream giả lập, kết hợp UI smoke và API/worker/storage thật.
Không có xác nhận chất lượng model thật khi chỉ chạy chế độ workflow.
