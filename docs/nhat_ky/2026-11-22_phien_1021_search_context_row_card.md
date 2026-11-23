# Phiên 1021 — Kiểm chứng nội dung row card trong chỉ mục có ngữ cảnh

## Phạm vi và kết quả sửa mã

- Bước 2 phiên 1020 thêm cây đề mục có mã nguồn và phạm vi sheet/slide. Tích hợp kiểm tra `contextual_search` phát hiện row card được thêm sau khi tạo `search_context` cho các chunk khác. Các bản ghi thẻ trong generation mới thiếu bản văn và hash theo hợp đồng của recipe.
- Chuyển bước tạo lớp kiểm chứng xuống sau khi đã tập hợp cả đoạn, bảng và row card. Với row card, dùng nguyên văn thẻ vì thẻ đã có thông tin nguồn trong tiêu đề. Prefix rỗng, hash khớp phần văn bản đã gửi embedding. Giữ phạm vi, kích thước và mã dẫn chứng theo ô của thẻ.
- Tích hợp đi qua lỗi trên rồi bộc lộ kỳ vọng năm đã cũ. Phiên bản planner từ `2e113749` cho phép tra cứu nhiều năm dữ liệu trong cùng một bản phát hành. Kiểm thử bây giờ kiểm tra cả truy vấn tổng quan cùng một bản phát hành, bộ lọc năm xung đột phải trả 409 trước embedding, và unit kiểm tra yêu cầu làm rõ khi có nhiều năm ban hành. Mã planner không thay đổi.
- Áp dụng khi tạo generation có bật `contextual_search`. Compatibility với generation cũ theo đường đọc có sẵn, không tự lập lại chỉ mục hay đổi trạng thái phát hành.

## Kiểm chứng

- Tái hiện trước sửa bằng `uv run --no-sync pytest -q --tb=short tests/unit/test_contextual_scope_790.py::test_row_card_is_sealed_without_duplicating_its_rendered_breadcrumb`. Exit 1 vì prefix làm thẻ vượt đúng ngân sách đã cấp.
- Sau sửa, chạy pytest cho contextual scope, chunking, row card, fact query, RAG context và PPTX. Exit 0, **81 unit đạt**.
- `uv run --no-sync python scripts/run_isolated_tests.py tests/integration/test_contextual_scope_790.py -q --tb=short --show-capture=no` exit 0, **4 tích hợp đạt**. Ca lỗi trước đây đi qua bước tạo chỉ mục, xác minh bản văn/hash, lọc năm trước TopK trong dense/hybrid, chặn xung đột và kiểm tra quyền truy cập. Harness xác nhận đã dọn DB test và giữ sentinel.
- `ruff check` đạt ở bốn tệp Python chạm trong phiên. `ruff format --check` đạt ở contextual và hai tệp test. Hunk cần format của `index/service.py` trùng baseline `35e43332`. `git diff --check` đạt.
- Toàn bộ suite chưa được chạy lại. Các kiểm tra tích hợp sử dụng Postgres cô lập và adapter embedding giả.
