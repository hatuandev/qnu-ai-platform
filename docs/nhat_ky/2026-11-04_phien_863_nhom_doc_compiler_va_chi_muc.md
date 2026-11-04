# Phiên 863 — Nhóm đọc Compiler và chỉ mục

- Bản nhanh và bản AI dùng chung nhóm mở/đóng trong trang lượt biên soạn và trang phiên bản. API đọc tùy chọn tạo nhóm từ snapshot đã ghim. Nhóm dùng tiêu đề nguồn hoặc số trang; đoạn dẫn từ nhiều mục giữ tiêu đề của bản biên soạn. Vị trí chỉnh sửa và artifact gốc độc lập với nhóm đọc.
- Chỉ mục v4 gắn tiêu đề nguồn chung cho hai chế độ và giữ quan hệ đoạn, bảng, ô, trang, dẫn chứng. Tiêu đề bảng chỉ đưa vào chuỗi tìm kiếm nếu đủ chỗ; metadata vẫn giữ tiêu đề và ID nguồn. Worker đọc được lượt v3 đã chuẩn bị sẵn.
- PASS Biome có phạm vi, typecheck, build và 34 Vitest. Lint toàn frontend còn lỗi ngoài phạm vi sửa. PASS Ruff và 23 unit test backend trọng tâm.
- PASS hai GET qua FastAPI TestClient với dữ liệu local thật. Bản AI có 11 nhóm, bản nhanh có 12 nhóm, đều giữ 13 bảng. PASS Chrome desktop/mobile mở nhóm, bảng và dẫn chứng với dữ liệu nhóm đã xác minh.
- So sánh ba câu cùng nguồn bằng BGE-M3 1024 chiều, xếp cosine trong bộ nhớ. Ô đúng trong top 3 trên cả hai bản. Phép đo từ khóa PostgreSQL đưa hai ca quy đổi vào top 5; ca phụ lục ở hạng 23 và 31. Chưa đo sinh câu trả lời, chưa đổi chỉ mục đang phục vụ.
- PASS 34 ca tích hợp Compiler, phát hành và chỉ mục trên PostgreSQL thử riêng. Bộ backend tổng dừng trước khi chạy hết sau khi tái hiện hai lỗi đã ghi nhận ở `test_auto_extraction_710` (bảng DOCX) và `test_chat_shared_admission_751` (Redis). Bộ unit tổng có 759 đạt, 1 lỗi fixture có sẵn `test_window_zero_records_bounded_bytes_and_keeps_whole_evidence` do actor là None.
- API dev cổng 8002 vẫn phục vụ mã cũ tại thời điểm kiểm tra. Khởi động lại phiên dev để giao diện lấy nhóm đọc từ API mới. Các lượt biên soạn cũ có thể đọc qua endpoint mới.
