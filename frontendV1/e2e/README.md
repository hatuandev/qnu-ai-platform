# V1 E2E theo từng chặng

Luồng model QNU thật đến upload/purge: [Hướng dẫn tổng hợp lệnh theo thứ tự](../../docs/quy_trinh/V1_TEST_TOAN_LUONG_MODEL_QNU.md).

Test lại từ đầu sau thay đổi capacity: [Bản lệnh ngắn và bước lấy metadata server](../../docs/quy_trinh/V1_QUY_TRINH_TEST_LAI.md). provider-setup tự đồng bộ metadata capacity/dimension và áp dụng timeout/OCR từ profile QNU, sau PASS có thể chạy ngay nhóm model; không còn bước GUI bắt buộc.

Hướng dẫn chính: [Chạy V1 E2E từng bước](../../docs/quy_trinh/V1_E2E_TUNG_BUOC.md).

PDF thật `TB điểm sàn 26.pdf`: [kịch bản 5 chặng riêng và 19 câu hỏi](../../docs/quy_trinh/V1_TEST_TB_DIEM_SAN_26.md). Sau 6 chặng model và navigation, dùng `admissions-upload` → `admissions-extraction` → `admissions-compilation` → `admissions-publication` → `admissions-chat`; không thay bộ dữ liệu giả cũ.

Model thật: [QNU discovery/chat/embedding/rerank/OCR](../../docs/quy_trinh/V1_TEST_MODEL_QNU.md).

Từ thư mục gốc: `test-v1-e2e.ps1 init`, `serve`, rồi `run <stage>` ở cửa sổ khác.

`run provider-setup --headed` kiểm nhà cung cấp/khóa/kết nối/đăng ký model trước model-discovery; khóa nhập ẩn qua terminal, chỉ lưu ModelOps DB. Sidebar Nhà cung cấp mở trực tiếp `/providers`.

Suite nghiệp vụ lấy `e2e/stages/workflow.spec.ts`; chặng `model-*` lấy `e2e/stages/models.spec.ts`. `E2E_STAGE` chọn đúng một bài; nhóm model chỉ chạy trong phiên live.
Runner giữ checkpoint và báo cáo riêng. Các spec `01_...09_...` là bản khung cũ,
không phải bằng chứng đã kiểm chứng. Không gọi trực tiếp suite khung để nghiệm thu.

Thông báo review ghi giới hạn chờ tối đa của model (ví dụ 300s); khi server xử lý xong sẽ trả ngay. Sau khi review hoàn tất, terminal hiển thị thời gian xử lý tính từ thời điểm bắt đầu/kết thúc lưu ở server, kể cả khi đọc lại review đã có. Thay đổi thông báo chỉ áp dụng từ lượt chạy test tiếp theo.

Runner lưu hash mã backend lúc khởi động API/worker. Nếu mã đã đổi hoặc phiên serve cũ chưa có dấu xác nhận, `run` chặn trước khi gọi model và hướng dẫn Ctrl+C rồi chạy lại `serve`. Giữ phiên, không cleanup/init. Compilation có thể phục hồi bản trung gian chưa review bằng finding gốc trong lịch sử cùng tài liệu, bằng khóa sửa mới; không thay bản đang có review chưa được ghi vào checkpoint.

Chế độ mặc định dùng upstream giả lập, kết hợp UI smoke và API/worker/storage thật.
Không có xác nhận chất lượng model thật khi chỉ chạy chế độ workflow.
