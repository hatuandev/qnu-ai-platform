# Phiên 1000 — Liên kết JSON và Markdown, giảm ngữ cảnh rà soát

## Triển khai

- Markdown bóc tách dùng mã dẫn chứng sẵn có cho khối và ô bảng. Lượt OCR mới ghim định dạng trong cấu hình. Khi lưu sửa chữ, JSON và Markdown phiên bản mới đều có mã phiên bản. Backend kiểm hash của bản đã lưu và giữ cách đọc Markdown v1.
- Markdown biên soạn dùng mã lượt hoặc phần, mã đoạn và vị trí ô giống báo cáo rà soát. Dẫn chứng dùng mã nguồn của đúng bản JSON. Chỉ mục và tài liệu gốc dùng cùng phiên bản đã phát hành.
- Rà soát dùng mã khối để kiểm bản sao văn bản của bảng. Chỉ xác nhận cục bộ khi bảng đã bóc tách đủ, nguồn không có cờ cần xem lại, văn bản khớp từng phần và cấu trúc bảng giống JSON đã ghim. Các ô vẫn có phần kiểm độ phủ riêng. Đoạn viết lại tiếp tục dùng hợp đồng rà soát hiện hành.
- Tái dùng cơ chế đối chiếu metadata và kiểm ngân sách ModelOps. PostgreSQL giữ đoạn, cấu trúc và dẫn chứng. Qdrant chứa vector từng đoạn cùng khóa liên kết.

## Kết quả chạy Qwen qua ModelOps

| Mẫu | Thời gian rà soát | Lượt gọi | Token | Kết quả |
| --- | ---: | ---: | ---: | --- |
| Word phức tạp, lượt trước `rvw_77d788329f36` | 118,55 giây | 5 | 102.050 | 840 mục nguồn, 862 mục nháp, 2 mục cần đối chiếu |
| Cùng bản nháp và cấu hình, lượt `rvw_f83a7d3d34d7` | 56,72 giây | 1 | 10.094 | Giữ nguyên độ phủ và bytes bản nháp. Còn 1 mục về tiêu đề |
| Word nhỏ, lượt `rvw_84df0fd3dda4` | 5,28 giây | 1 | 1.692 | 57 mục nguồn, 59 mục nháp, 0 mục cần đối chiếu |
| PDF scan 2 trang, lượt `rvw_747dff1a230e` | 28,69 giây | 1 | 6.550 | 484 mã nguồn liên kết với Markdown. Rà soát 482 mục nguồn, 487 mục nháp, 1 mục cần đối chiếu |
| PDF tổng hợp 120 trang, lượt `rvw_302121a7ab7e` | 7,05 giây | 1 | 1.863 | Bóc tách 44,17 giây. Rà soát 601 mục nguồn, 609 mục nháp, 0 mục cần đối chiếu |

Tệp tổng hợp đi từ upload qua lưu sửa chữ, biên soạn, rà soát, duyệt và phát hành ở kho thử `col_fa3be8a6b5ec`. Bản chưa phát hành trả 409 khi tìm kiếm. Bản đã phát hành `cver_01ed4604918e` có 601 đoạn trong chỉ mục Qdrant `idx_7f76ec910d17`. Tìm kiếm trả đúng đoạn sửa và phiên bản văn bản dùng để lập chỉ mục. Một câu hỏi kiểm tra qua API trả đúng mã sửa và dẫn chứng gắn đúng phiên bản văn bản. Con số thời gian trên chỉ áp dụng cho các mẫu đã chạy.

## Kiểm chứng mã

- Ruff trên các file Python sửa đạt, exit 0.
- Pytest theo phạm vi OCR, rà soát, ngân sách và metadata đạt 132 ca, exit 0. Dùng `--basetemp` riêng vì thư mục pytest mặc định trên Windows báo lỗi quyền.
- Hồi quy tích hợp OCR, Markdown, biên soạn, rà soát, phát hành và index đạt 74 ca. Ca tương thích Markdown v1 chạy riêng đạt 1 ca. DB thử nghiệm cô lập đã được dọn.
- Bộ backend `uv run --env-file ../.env python scripts/run_isolated_tests.py -q -x` dừng sau 8 ca đạt, 1 ca lỗi. Lặp lỗi nền `tests/integration/test_answer_review_p6.py::test_review_keeps_insufficient_evidence_truthful` đã ghi ở phiên 999, exit 1.
