# Phiên 915 — Đồng bộ migration V1

Người dùng yêu cầu tinh gọn migration và nhận prompt xử lý các lỗi luồng ngược còn lại. Giữ chuỗi lịch sử và dùng revision `0020_reverse_flow` cho thay đổi đã có trong working tree.

- Gom khai báo cột biên nhận, đồng bộ `SCHEMA_HEAD` dùng bởi API, worker và kiểm tra lúc khởi động.
- Khi hạ về 0019, ánh xạ chỉ mục `empty` sang `ready` theo quy ước cũ. Chặn hạ phiên bản nếu còn lượt xóa nguồn đang chờ mà worker cũ không thể tiếp tục.
- Khai báo lại chỉ mục biểu thức `ix_compilation_reuse_key` trong ORM cho khớp migration 0018. Test baseline kiểm tra revision và SQL cần có theo nội dung, bỏ số lượng tệp cố định.

## Kiểm chứng

- Trong `backendV1`, Ruff check và format check trên bốn tệp Python đã sửa đạt. `git diff --check` đạt.
- `python -m pytest tests/unit ../scripts/tests/test_check_v1_runtime.py -q --tb=short --basetemp=<thư mục test riêng>` đạt 892 ca, exit 0. Lượt unit đầu gặp WinError 5 tại thư mục tạm mặc định của Windows. Chuyển thư mục tạm của pytest sang workspace.
- `scripts/test_database.py` với `tests/migrations/test_workspace_model_schema.py`, `tests/integration/test_readiness_666.py` và một ca migration tạm đạt 5 ca, exit 0. Kiểm tra schema mới, nâng từ 0019 có dữ liệu, từ chối downgrade khi lượt xóa mới còn pending, giữ dữ liệu khi downgrade hợp lệ và giữ bảng phiên bản legacy. DB cô lập đã được dọn.
- Full backend tích hợp và model thật chưa chạy trong phiên này. Chưa áp migration lên DB ứng dụng hoặc push. Xử lý lỗi luồng ngược còn lại là batch tiếp theo.
