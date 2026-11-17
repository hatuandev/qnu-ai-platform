# Phiên 1001 — Kiểm chứng metadata và chuyển phiên bản trên bốn tài liệu

Kiểm bước 4–5 trên kho thử `col_752acb8f8c45`. Dùng API và worker thật với Qwen `qwen3.8-27b-q4` qua ModelOps, cùng embedding và rerank đã cấu hình. Đối chiếu PDF trang đầu, lịch và bảng với bản gốc. Đọc Word theo nội dung và cấu trúc bảng. Mọi tệp đi qua upload, liên kết JSON–Markdown, rà soát, duyệt theo đúng báo cáo và phát hành trong kho thử.

## Mã đã sửa

- Metadata v9 xác định cột con của ô năm gộp khi hình học chứng minh được tiêu đề nhiều tầng, kể cả khi nguồn đã đánh dấu sẵn các hàng tiêu đề. Trình gợi ý và bộ kiểm chứng dùng chung điều kiện.
- Bộ lập kế hoạch rà soát đưa đoạn nguồn khớp tiêu đề vào ngữ cảnh của phần cần xét tên bản nháp, kể cả khi phần đó đồng thời xét dữ liệu khác. PDF cập nhật 2026 trên cùng bản nháp từ 1 mục nghi vấn về tiêu đề xuống 0, vẫn kiểm 1.116 mục nguồn và 1.133 mục bản nháp.
- Khi cột mã nằm giữa tên nhóm gộp dọc và tên riêng của một dòng, câu trả lời giữ cả nhóm và tên. Mã vẫn truy được như một ô riêng. Bản sửa chạy trên cùng chỉ mục, việc lập chỉ mục lần hai phục vụ đổi phiên bản PDF.

## Bước 4 — Đăng ký metadata

| Mẫu | Mã nguồn đối chiếu được với Markdown | Metadata đã lưu | Rà soát bằng Qwen |
| --- | ---: | --- | ---: |
| PDF thông tin tuyển sinh 2025, bản ký | 1.143 | 49 mục. Phân biệt năm trong bảng lịch sử với năm tuyển sinh, ghi hai cửa sổ đăng ký trên hệ thống Trường và Bộ | 48,30 giây · 7.774 token |
| PDF thông tin cập nhật 2026 v1 | 1.129 | 49 mục. Bảng lịch sử gắn đúng năm 2024 và 2025. Lượt đầu bỏ trống năm ban hành vì ngày bị tách qua các khối PDF | 28,56 giây · 5.119 token |
| Word thuyết minh 2026 | 57 | 19 mục. Qwen đọc đúng quan hệ điểm chuẩn lịch sử 2025 với mùa tuyển sinh 2026 | 13,94 giây · 1.650 token |
| Word phức tạp | 850 | 29 mục, tăng từ 20. Có thêm 9 cột dữ liệu của các năm 2025–2027, mỗi năm 3 cột dẫn về ô năm tương ứng | 62,28 giây · 10.325 token |
| PDF thông tin cập nhật 2026 v2 | 1.129 | 50 mục, thêm năm ban hành 2026 dẫn về ngày đã sửa ở trang 1 | 35,41 giây · 5.282 token |

Các giá trị gửi lúc đăng ký khớp bản xem trước và được ghim vào phiên bản trả về. Hai tệp Word thực hiện một lượt bổ sung AI mỗi tệp, lần lượt 1.453 và 2.941 token. Hai lượt này ghi nhận 0 đề xuất metadata có nguồn `model` được giữ. Bảng trên phản ánh metadata từ quy tắc xác định. Nhãn ngày bắt đầu áp dụng mô phỏng 01/11/2026 của Word phức tạp chưa được tự đưa vào `effective_from`. Lịch thi năng khiếu 01–03/07/2025 trả đúng khi hỏi từ văn bản nguồn, nhưng chưa thành sự kiện trong phần metadata đã lưu của PDF 2025.

## Bước 5 — Tìm kiếm và chuyển phiên bản

- PDF cập nhật dùng cùng tệp gốc cho hai phiên bản. V2 sửa dòng ngày ban hành sang 31/5/2026 theo hình ảnh trang 1 và liên kết bản sửa `txt_f711e78e728a`. V2 được đăng ký làm phiên bản thứ hai của cùng tài liệu.
- Khi v2 còn nháp, Qwen trả đúng 20,3 trong câu về Kế toán năm 2025. Dẫn chứng trang 12, hàng mã 7340301, ô `ev_p012_b001_c02_08` thuộc v1 `cver_9ea51e807d4f`. Chỉ mục `idx_2f3e3c79a50f`, thế hệ 1.
- Sau duyệt và phát hành v2 `cver_6fe37ab0027e`, công việc lập chỉ mục hoàn tất với 643 đoạn, 1.024 chiều, thế hệ 2 `idx_eca81d20a0ae`. Cùng câu hỏi trả 20,3 và dẫn ô tương ứng trong v2. Câu hỏi ngày ban hành trả 31/5/2026, dẫn khối `ev_p001_b009` của bản sửa.
- Nhóm kiểm thử có 10 câu khác nhau, một câu chạy ở cả hai phiên bản và hai câu chạy lại sau khi sửa tên dòng. PDF 2025 trả đúng hai khoảng đăng ký và các ngày thi. Word phức tạp trả tổng 1.233 chỉ tiêu và 1.149 ghi nhận, tỷ lệ 93,3% với tên An toàn thông tin, dự kiến 108 sinh viên năm 2027 và ô CT-02 chưa nhập. Các phép đo dùng phạm vi từng tài liệu đã chốt và được chấm theo nguồn.
- Tệp log kiểm thử chỉ lưu cục bộ. Không tác động bản phát hành hoặc chỉ mục của kho người dùng.

## Kiểm chứng mã

- Ruff theo tệp sửa và 188 ca unit về năm bảng, metadata, rà soát, sự kiện và dẫn chứng bảng đạt. Ba ca mới tái hiện thiếu năm, thiếu tiêu đề nguồn và thiếu tên dòng tương ứng trong phần thay đổi có liên quan.
- Harness DB cô lập chạy `tests/integration/test_automatic_metadata_896.py` và `tests/integration/test_compiler_review_652.py`: 27 đạt, exit 0. Mô hình giả trong fixture duyệt phiên bản đã được chỉnh để xử lý phần có nguồn chỉ dùng làm ngữ cảnh và phản hồi JSON theo hợp đồng được yêu cầu.
- Bộ backend toàn phần `uv run --env-file ../.env python scripts/run_isolated_tests.py -q -x`: exit 1 sau 8 đạt và 1 lỗi. Lặp lỗi nền `tests/integration/test_answer_review_p6.py::test_review_keeps_insufficient_evidence_truthful`, fixture đọc thiếu trường `evidence`. Các ca sau dừng theo `-x`. DB kiểm thử được dọn.
