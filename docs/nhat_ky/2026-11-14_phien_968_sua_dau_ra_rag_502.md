# Phiên 968 — 2026-11-14 — Sửa lỗi kiểm tra đầu ra RAG gây 502

## Thay đổi

- Cấp mã ô đầy đủ trong danh mục gửi model và giới hạn JSON schema theo danh mục. Backend vẫn kiểm ô, nguồn và phạm vi rồi lấy giá trị và dẫn chứng từ ô đã xác minh.
- Gộp mã dẫn chứng trùng trong phần đánh giá độ đầy đủ. Ý có mã ngoài phạm vi được đánh dấu thiếu căn cứ và không xuất mã đó. Trace ghi vị trí và loại lỗi.
- Dùng chung một lần đánh giá lại cho trường hợp thiếu căn cứ hoặc lỗi chọn ô/giá trị có thể sửa khi đủ phần nguồn bắt buộc. Giữ nguyên bằng chứng, tính lại ngân sách, kiểm lại quyền, nguồn, model và đầu ra. Khi lần sửa thất bại, giữ lỗi kiểm tra ban đầu. Lỗi hạ tầng và timeout theo chính sách ModelOps.

## Kiểm chứng

- Ruff và kiểm tra whitespace trên tệp mã đạt. 72 unit trọng tâm, 13 ca API cô lập và 2 ca kiểm chứng dẫn chứng khi model báo thiếu căn cứ đạt.
- Suite unit qua harness DB cô lập có 1169 đạt, 2 lỗi ngoài phạm vi: `test_legacy_source_deletion_718.py::test_deleted_source_can_request_new_permanent_preview_but_other_deletes_stay_blocked` và `test_migration_baseline_661.py::test_initial_schema_offline_sql_creates_v1_without_touching_legacy`. Full suite riêng đã khởi động, chưa có kết luận.
- Hai lượt đo tuần tự 8 câu từng lỗi 502 tại API dev tạm, cùng `qwen3.8-27b-q4`, cùng revision trợ lý và chỉ mục. Cả hai lượt 8/8 HTTP 200. Lượt đầu sửa Q26 sau `answer_table_value_not_extractive`. Lượt mã cuối v30/payload v4 qua 8/8 ngay lần đầu; trace ghi mã trùng đã được gộp ở Q33 và Q44.
- Mã cuối: Q26/Q28/Q33/Q40/Q45/Q73 trả được ý chính, Q41 lạc khỏi yêu cầu liệt kê, Q44 đúng ý hỏi nhưng phần liệt kê bổ sung thiếu hai tổ hợp. Trung vị 14,8 giây so với 11,9 giây ở tám lượt lỗi gốc; prompt sinh câu trả lời khoảng 10.332 so với 9.246 token. Kết quả thô ở thư mục tạm `qnu_g3_repair_v30_final_df2736e7f65e.json`.
- Cấu hình ModelOps đọc được là context 163.840 và đầu ra 32.768. Endpoint trả 404 ở `/props`; phản hồi `/metrics` chưa có chỉ số hàng đợi llama.cpp cần đối chiếu. Chưa xác minh ngữ cảnh theo slot hoặc tải đồng thời của GPU.
- Đính chính G3: 8 lỗi 502 và 1 lỗi 409. Q99 cùng trạng thái thiếu căn cứ ở hai lần, nên theo danh sách 84 câu đúng cũ còn 7 ca lệch đã xác định. Kết quả nhóm 8 câu chưa thay thế phép đo 100 câu. Q2 và chất lượng liệt kê cần xử lý riêng.
- Đã dừng API tạm. API dev thường dùng vẫn chạy phiên cũ. Không thay cấu hình ModelOps, migration ứng dụng hoặc chỉ mục.
