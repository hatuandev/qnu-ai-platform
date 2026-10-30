# Phiên 727 — Cấu hình capacity cho model con

## Yêu cầu và bằng chứng

Người dùng cung cấp log năm chặng model live đạt, embedding quan sát 1024 chiều; navigation BLOCKED vì Qwen chưa khai báo capacity. Đây là kết quả do người dùng chạy, không phải lượt agent chạy lại. Đọc mã live-defaults xác nhận guard còn yêu cầu capacity cho cả bốn model, dimension embedding và ngân sách OCR/prompt. Kiểm tra API chỉ đọc trong phiên hiện có xác nhận cả bốn model còn capacity unknown, token_limits null và dimension chưa khai báo.

Các cURL gửi thêm là ví dụ request inference. Request OCR có tham số output 8192 và ảnh mẫu; không chứa giới hạn phục vụ thực tế hoặc cận trên token ảnh. Không coi max_tokens của request là capacity. Không chạy request ảnh đính kèm, không sao chép ảnh/credential vào repo. Cần người vận hành cung cấp cấu hình khởi chạy model đã bỏ credential.

## Thay đổi

- `frontendV1/src/features/modelops/connections/connection-detail.tsx`: nút sửa model dùng ProviderFormDialog đầy đủ thay modal chỉ sửa capability/endpoint; bỏ state/handler/import không còn dùng. Giữ nguyên thao tác thêm model và cấu hình chạy hiện tại.
- `frontendV1/src/features/modelops/provider-form-dialog.tsx`: tiêu đề và hướng dẫn riêng cho model con, yêu cầu test lại sau lưu. Tái dùng validation, PATCH chỉ trường đổi và query invalidation connections đã có; không viết thêm luồng lưu.
- `frontendV1/tests/connection-model-capacity-727.test.tsx`: bốn test tích hợp trang chi tiết + form thật với mutation giả lập, kiểm đúng model con, giữ nhiều capability/endpoint, dimension không bịa token limits, thiếu OCR bị chặn và đủ OCR được lưu.
- `docs/quy_trinh/V1_TEST_TOAN_LUONG_MODEL_QNU.md`: chỉ đường cấu hình, bảng thông tin cần cho bốn model, phân biệt cURL/request với capacity và lệnh tính hash prompt nội bộ.

## Kiểm chứng

Tại frontendV1:

- `node_modules/.bin/vitest.cmd run tests/connection-model-capacity-727.test.tsx`: exit 0, 4 PASS trước format.
- `node_modules/.bin/vitest.cmd run tests/connection-model-capacity-727.test.tsx tests/v1-contract.test.ts`: exit 0, 18 PASS/2 file sau thay đổi.
- Biome check ba file sửa: exit 0, không error/warning; còn một info noUselessSwitchCase có sẵn tại switch chat trong connection-detail, giữ ngoài phạm vi.
- `npm run build`: exit 0, Vite + tsc đạt; còn cảnh báo import extension configLoader native và chunk lớn có sẵn.
- Browser phiên live: mở chi tiết nhà cung cấp/Qwen, form hiển thị đầy đủ trường token/dimension/OCR; quan sát bố cục màn nhỏ và cuộn tới capacity. Hủy form, không lưu.
- Lệnh Python tính SHA-256 prompt hiện hành: exit 0, không gọi model.

Full FE suite, live inference và navigation sau sửa: NOT RUN. Không thay cấu hình ModelOps DB, không tự điền capacity, không sửa guard, không restart/migrate/push. Pipeline vẫn BLOCKED cho đến khi có giới hạn phục vụ thật; sau khai báo cần test lại model liên quan rồi navigation/upload/extraction. Giữ các diff trước phiên.
