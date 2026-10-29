# V1 E2E theo từng chặng

Hướng dẫn chính: [Chạy V1 E2E từng bước](../../docs/quy_trinh/V1_E2E_TUNG_BUOC.md).

Từ thư mục gốc: `test-v1-e2e.ps1 init`, `serve`, rồi `run <stage>` ở cửa sổ khác.

Suite mặc định chỉ lấy `e2e/stages/workflow.spec.ts`; `E2E_STAGE` chọn một chặng.
Runner giữ checkpoint và báo cáo riêng. Các spec `01_...09_...` là bản khung cũ,
không phải bằng chứng đã kiểm chứng. Không gọi trực tiếp suite khung để nghiệm thu.

Chế độ mặc định dùng upstream giả lập, kết hợp UI smoke và API/worker/storage thật.
Không có xác nhận chất lượng model thật khi chỉ chạy chế độ workflow.
