# Phiên 979 — Kiểm tra tạm dừng chatbot công khai

Người dùng yêu cầu kiểm chứng và sửa các ảnh hưởng từ tạm dừng trợ lý, landing và xác định IP qua proxy.

- API công khai tải cờ hoạt động cùng bản phát hành theo đúng đơn vị. Cache danh sách và chi tiết gồm cờ này. Trợ lý tạm dừng trả `409 public_chatbot_unavailable` khi tạo phiên hoặc gửi câu, với kiểm tra lại trước khi gọi RAG. Cache sẵn sàng của kho vẫn dùng cho lượt bình thường.
- Landing chỉ chọn slug khả dụng. Thẻ đang tạm ngưng hiện trạng thái và dùng nút HTML đã vô hiệu hóa.
- Compose chỉ truyền cấu hình tin proxy vào backend và mặc định tin loopback. Mẫu môi trường và hướng dẫn Dokploy mô tả cách đặt IP thực tế của các proxy. Nếu thiếu cấu hình sau proxy, backend vẫn nhận địa chỉ của proxy.

## Kiểm chứng

- `python scripts/run_isolated_tests.py -q tests/integration/test_publication_channel.py::test_ready_assistant_can_enable_and_serve` trước sửa **FAIL**. Sau tạm dừng, POST vẫn trả 200.
- `python scripts/run_isolated_tests.py -q tests/integration/test_publication_channel.py` sau sửa **12 PASS**. Ca chính giữ cache nóng, kiểm API danh sách và chi tiết, chặn tạo phiên và hỏi, rồi bật lại và dùng tiếp phiên cũ. DB cô lập đã dọn.
- Ruff theo hai tệp backend và Biome theo hai tệp frontend **PASS**. `npm run build` ban đầu lỗi `tsc` ở tệp `assistant-advanced-fields.tsx` đang sửa song song. Chạy lại sau khi workspace cập nhật, **PASS** cả Vite và TypeScript. Vite còn cảnh báo kích thước một bundle.
- Chrome với artifact Vite và API mô phỏng **PASS** trên viewport 390 và 1280 px. Thẻ tạm ngưng bị vô hiệu hóa, thẻ sẵn sàng dẫn sang chat, hai lần gửi nhanh chỉ có một POST câu hỏi.
- `docker compose --env-file .env.dokploy.example --profile frontend config --format json` **PASS** với mặc định loopback và khi ghi đè bằng địa chỉ proxy thử. Traefik/nginx môi trường triển khai thật, full suite, G3 và deploy **NOT RUN** trong phiên.
- Kiểm middleware Uvicorn cục bộ **PASS** với hop được cấu hình và mặc định loopback. Ba ca pause/resume, đồng thời phiên và token cũng **PASS** sau chuyển sang `Row._tuple()`.

Trạng thái production vẫn cần cấu hình IP proxy và thử qua chuỗi triển khai thực. Thay đổi nằm trong workspace. [Hướng dẫn triển khai](../trien_khai/06_kenh_chatbot_cong_khai.md)
