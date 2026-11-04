# Phiên 864 — Xóa nguồn đã biên soạn

- Nút xóa nguồn trả `409 purge_dependency_unsupported` khi đồ thị gặp `kb_compilation_outputs`. Truy vấn chỉ đọc xác nhận lỗi trên nguồn người dùng báo. Bản xem trước dừng trước khi xóa dữ liệu.
- Bổ sung bản nháp toàn phần hoặc một phần và các nhóm Compiler/Review vào phạm vi xóa đã xác nhận. Kiểm tra nhóm con thuộc đúng lượt, dọn bản ghi từ con đến cha, ghim khóa và hash tệp, kiểm tra tệp dùng chung. Điều kiện thu hồi bản đang phát hành vẫn áp dụng.
- PASS Ruff và format trên bốn file Python. PASS 28 ca vòng đời, xóa nguồn và xóa mềm cũ trên DB riêng. PASS lại bốn ca tích hợp xóa nguồn trên mã cuối, gồm hai chế độ Compiler, tệp bản nháp một phần, hai cây nhóm và thao tác lặp cùng biên nhận. Harness dọn DB thử và xác nhận sentinel giữ nguyên.
- Kiểm tra lại đồ thị trên DB ứng dụng trong giao dịch chỉ đọc. Hai lượt biên soạn và 122 tệp thuộc phạm vi xem trước, kiểm tra tệp dùng chung đạt. Để thực thi từ giao diện, khởi động lại phiên dev rồi xác nhận xóa.
- Từ root, harness `backendV1/scripts/run_isolated_tests.py tests -q -x --tb=short` trả exit 1 sau 39 ca đạt và lỗi nền `tests/integration/test_auto_extraction_710.py::test_docx_table_has_real_structure_and_original_is_unchanged`. Các ca sau điểm dừng chưa chạy trong lượt này. Harness dọn DB thử và xác nhận sentinel giữ nguyên.
