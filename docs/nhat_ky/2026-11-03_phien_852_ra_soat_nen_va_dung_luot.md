# Phiên 852 — Rà soát nền và dừng lượt

- Tab Rà soát & Đánh giá lưu lượt thủ công và trả ID trước khi gọi model. Worker ARQ hiện có tiếp nhận và có thể giao lại các lượt còn chờ khi Redis gián đoạn. Lượt đã nhận thực thi được khóa theo trạng thái. API đồng bộ vẫn phục vụ các caller hiện hữu.
- Nút **Dừng rà soát** gọi API có kiểm tra quyền workspace và ghi audit. Lượt dừng giữ các phần đã hoàn tất và không gửi thêm nhóm. Worker hủy việc chờ cục bộ. Kết quả và usage phía nhà cung cấp có thể chưa xác định đối với yêu cầu đã gửi.
- Backend sửa module `knowledge/compilation/review`, worker compilation và thêm migration `0013_queued_review`. Frontend cập nhật API, polling và panel tiến độ.
- Ruff có phạm vi đạt. Vitest chạy 4 bộ liên quan, 46 ca đạt. Biome 7 tệp và `npm run build` đạt.
- Full Pytest qua `tmp/full-backend-852.py` với PostgreSQL và Redis cô lập trả exit 1, gồm 1309 ca đạt và 23 ca lỗi. Sau khi sửa chốt khóa nhóm và cập nhật kiểm thử đăng ký worker, chạy lại các bộ queue, migration, budget, refinement, worker timeout và review nhiều nhóm bằng harness DB cô lập. Cả 37 ca đạt, gồm toàn bộ 22 ca lỗi liên quan thay đổi mới. Lỗi nền `test_auto_extraction_710.py::test_docx_table_has_real_structure_and_original_is_unchanged` nằm ngoài phạm vi. Chưa chạy lại full suite sau lần sửa cuối.
- Chưa chạy model thật. Áp dụng migration bằng `./make.ps1 migrate` trên DB đích rồi khởi động lại API và worker để bật luồng mới.
