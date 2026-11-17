# Phiên 995 — Rà soát một khối văn bản vượt ngân sách model

## Phạm vi và cách giải quyết

Trong luồng giữ nguyên nguồn, bản nháp có thể tách một khối dài theo giới hạn ký tự trong khi lượt rà soát vẫn phải đọc toàn bộ khối nguồn liên kết. Hệ thống đã tái hiện `compilation_review_segment_too_large` với một khối giả lập 45.000 ký tự và ngân sách đầu vào 32.000 token.

Luồng rà soát có cấu trúc thử lập kế hoạch bình thường. Nếu vượt ngân sách, hệ thống xác minh các đoạn đang dẫn một khối nguồn có ghép lại khớp nguyên văn hay không. Với khối khớp, hệ thống chia hai phía thành các mảnh có cùng phạm vi, ưu tiên dấu kết câu và khoảng trắng gần mép ngân sách. Khối liền không có dấu ngắt được chia theo vị trí ký tự. Kích thước dự kiến tính từ ngân sách ModelOps, phần dành cho schema, hướng dẫn và ngữ cảnh lân cận. Kế hoạch dùng phép kiểm ngân sách hiện hành trên từng request thực tế được dựng.

Mã khối gốc, phiên bản, trang và khoảng ký tự được giữ trong kết quả. Vị trí mảnh đã lưu được kiểm tra lại khi worker chạy. Dữ liệu nguồn, bản nháp đã lưu và các dẫn chứng dùng cho xuất bản được giữ nguyên. Đoạn đã sửa hoặc dẫn nhiều khối cần tiếp tục đi qua hợp đồng rà soát thông thường nếu không xác lập được cặp nguồn–bản nháp chính xác.

## Kiểm chứng

- PASS, exit 0. `uv run ruff check` cho module review và hai tệp test liên quan. `uv run pytest -q tests/unit/test_compilation_review_parts_744.py tests/unit/test_compiler_review_refinement_755.py tests/unit/test_compiler_review_budget_757.py` đạt 50 ca.
- PASS, exit 0. Chạy `uv run --env-file ../.env python scripts/run_isolated_tests.py -q tests/integration/test_compiler_review_segments_750.py` đạt 6 ca. Sau thay đổi bỏ ngữ cảnh trùng chữ đã có ở phía nguồn, chạy lại ca `test_source_first_review_splits_single_over_budget_text_block` và `test_source_first_review_repairs_only_missing_and_uncited_units`, cả hai đạt và DB test được dọn.
- Ca mới kiểm khối tiếng Việt 45.000 ký tự liền dòng. Mỗi request gồm hướng dẫn, schema và phần đầu ra dành trước vừa giới hạn context giả lập 36.096 token (32.000 đầu vào + 4.096 đầu ra). Ghép các mảnh ở cả hai phía đủ nguyên văn và các khoảng ký tự nối tiếp nhau. Ca âm tính từ chối bản nháp đã đổi và khoảng ký tự lưu thiếu phần cuối.

Phạm vi kiểm thử dùng dữ liệu giả lập và cơ sở dữ liệu cô lập. Chưa gọi Qwen thật, chưa chạy lại bộ tài liệu tuyển sinh và chưa chạy toàn bộ Backend V1 trong phiên này.
