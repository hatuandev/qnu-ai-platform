# Phiên 834 — Docling trong bóc tách DOCX V1

Tệp gặp lỗi có năm section, một tham chiếu footer và mười bảng. Gotenberg cục bộ đã dàn trang được. Bước phục hồi bảng gọi lại Story và bị chặn bởi kiểm tra header/footer.

Khóa Docling Slim với hỗ trợ DOCX. Nhánh Gotenberg đọc bảng gốc qua Docling và ghép cấu trúc khi khớp duy nhất với bảng trên PDF. PDF vẫn cung cấp trang và tọa độ. Story giữ giới hạn cũ.

Ruff và kiểm tra lock đạt. Sau khi tăng thời gian tải PyPI, môi trường cài được Docling. `uv run --locked --extra dev pytest -q tests/unit/test_native_extraction_710.py tests/unit/test_ocr_docx_html.py` đạt 23 ca. Tệp thật chạy trực tiếp qua renderer Gotenberg và native extraction cục bộ, ra 18 trang. Docling đọc được 10 bảng gốc. Chưa chạy lại lượt cũ qua UI.

Full backend khởi động từ root bằng `uv run --project backendV1 --locked --extra dev python backendV1/scripts/run_isolated_tests.py`, đã thu 1.307 ca trên DB cô lập và chưa có kết quả cuối tại thời điểm bàn giao.
