# Phiên 925 — Worker chạy riêng xử lý xóa tài liệu

- Kho Demo1 hiện trống vì API ẩn nguồn khi nhận lệnh. Sáu biên nhận còn `pending` với `source_purge_failed`. Tải cùng nội dung trả HTTP 409 `source_purge_pending` cho đến khi xóa xong.
- Đọc DB với giao dịch chỉ đọc, rồi tái hiện từ entrypoint ARQ trong tiến trình mới. Đồ thị dọn nguồn dừng với `KeyError` do ba bảng duyệt tài liệu chưa được đăng ký trong worker. Test API chạy cùng tiến trình đã nạp các bảng nên bỏ sót lỗi.
- Đăng ký module model duyệt tài liệu trong `qnu/workers/settings.py`. Thêm ca kiểm tra entrypoint worker trong tiến trình Python riêng. Schema và giao thức xóa dùng phiên bản hiện có.
- Từ `backendV1`, chạy `python -m pytest tests/unit/test_source_purge_716.py -k standalone_worker -q --tb=short`. Trước sửa, 1 ca lỗi đúng vì thiếu ba bảng. Sau sửa, cùng nhóm `test_worker_model_timeout_819.py` đạt 15 ca, exit 0. Ruff check và format trên hai tệp đạt.
- Từ root, `backendV1/scripts/run_isolated_tests.py tests/integration/test_source_purge_716.py -q --tb=short --show-capture=no` đạt 16 ca, exit 0, dọn DB thử thành công. Full gate `backendV1/scripts/run_isolated_tests.py tests -x -q --tb=short --show-capture=no` chưa có kết quả cuối khi bàn giao.
- Cả sáu biên nhận thật qua bước đối chiếu đồ thị, checkpoint và tệp tham chiếu trong truy vấn chỉ đọc sau sửa. DB app ở `0021_index_system_embedding`. Worker đang chạy cần khởi động lại để nạp bản sửa. Lịch gửi lại biên nhận đang bật và chạy theo mốc 5 phút.
