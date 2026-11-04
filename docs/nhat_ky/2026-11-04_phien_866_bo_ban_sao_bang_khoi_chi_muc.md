# Phiên 866 — Bỏ bản sao chữ của bảng khi lập chỉ mục

## Phạm vi

Sửa điểm 2 trong kết quả rà soát biên soạn nhanh. Bảng từ bộ bóc tách có thể xuất hiện dưới dạng đoạn chữ phân cách bằng `|` và bảng có cấu trúc. Cả hai biểu diễn từng được chia thành đoạn để tìm kiếm.

## Cách xử lý

- Chỉ mục v5 đối chiếu đoạn có một dẫn chứng với biểu diễn chữ của đúng bảng đã bóc tách. Nếu trùng nguyên văn và đoạn không có metadata riêng, lưu các đoạn chỉ mục từ bảng có cấu trúc. Đối chiếu được cả khi bản biên soạn đã chia bản sao chữ thành nhiều đoạn.
- Đoạn diễn giải, đoạn có dẫn chứng bổ sung, đoạn có metadata riêng và bảng chưa bóc tách được vẫn được lập chỉ mục. Các lượt chỉ mục v3 và v4 đã tạo tương thích với worker hiện tại.
- Giữ bản nháp, tệp gốc, ô bảng, dẫn chứng, và metadata. Thay đổi chỉ áp dụng lúc tạo generation mới.

## Kiểm chứng

- Pytest `tests/unit/test_index_chunking_647.py` trong `backendV1` tái hiện lỗi trước sửa với 1 lỗi, 5 đạt. Sau sửa có 7 đạt, exit 0. Ruff check và format check trên 4 tệp Python đạt, exit 0.
- Từ root, chạy harness `backendV1/scripts/run_isolated_tests.py tests/integration/test_index_api_647.py -q` bằng Python của `backendV1/.venv`. Có 19 đạt, exit 0. Harness đã dọn DB kiểm thử. `make.ps1 test-be` đang chạy trên DB riêng lúc ghi nhận và đã gặp lại lỗi nền `test_auto_extraction_710.py::test_docx_table_has_real_structure_and_original_is_unchanged`. Kết quả cuối và exit code còn chờ.
- So sánh cùng snapshot của bản nhanh qua `build_chunks`, tại ngân sách 3.000 byte. Đoạn văn giảm từ 174 xuống 161. Cả 56 đoạn bảng của 13 bảng và bản nháp giữ nguyên khi đối chiếu. Chỉ đọc cơ sở dữ liệu ứng dụng và kho tệp. Không gọi model, phát hành hay lập chỉ mục thật.
