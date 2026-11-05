# Phiên876 — PDF Inspector trong luồng bóc tách tự động

PDF tự động mới ghim PDF Inspector 1.25.2. DOCX đi qua Docling trực tiếp.
Worker lưu Markdown theo trang của Inspector cùng artifact native. PyMuPDF
đo vị trí dòng, ảnh và lưới ô. Vùng ô được ưu tiên trước dòng để tránh bỏ
chữ khi các vùng chồng nhau. Khi chữ của một vùng sai khác ngoài khoảng
trắng, giữ lớp chữ gốc của vùng đó và ghi số vùng phục hồi vào cảnh báo trang.
PDF xoay chưa xác nhận được phép chiếu tọa độ đi qua OCR trang.

MinerU nhận tập con các trang cần OCR, ánh xạ số trang trả về theo số trang
gốc. Với trang có chữ và ảnh tách vùng, gửi ảnh nhúng theo cơ chế ảnh hiện có.
Lượt mới ghim phiên bản engine. Lượt PDF cũ giữ đường đọc đã ghim và các
artifact trước đó vẫn truy cập được.

## Kiểm chứng

- Pytest trực tiếp trong `backendV1` cho `test_native_extraction_710.py`,
  `test_native_source_870.py`, `test_mineru_823.py` đạt 44 PASS.
- `make.ps1 test-be` với `PYTEST_ADDOPTS=-k` chọn `auto_extraction_710`,
  `image_ocr_870`, `ocr_processing_api`, `ocr_observability_644`,
  `compiler_source_first_854` và `index_budget_869` đạt 55 PASS. Ca PDF
  trộn xác nhận bản gửi chỉ có trang scan và kết quả về đúng trang gốc.
  Các ca dùng MinerU giả lập.
- Hai PDF có chữ 8 và 14 trang không có trang cần OCR toàn trang. Mỗi tài liệu
  có một trang với ba ảnh nhúng cần OCR riêng. Canonical chữ, biên soạn nhanh
  và chia đoạn thử giữ lần lượt 7/13 bảng, 488/955 ô khớp với lớp chữ trong
  lưới đo khi bỏ khác biệt khoảng trắng, sinh 86/182 đoạn thử.
- PDF Quy chế 363 có đủ 32 trang được phân loại cần OCR. Chưa gọi MinerU
  thật cho các tệp trong phép kiểm này.
- Ruff vùng OCR và `git diff --check` đạt. Full gate `make.ps1 test-be`
  với `-x --failed-first` dừng tại lỗi nền Redis namespace của
  `test_chat_shared_admission_751.py::test_real_redis_enforces_shared_limit_and_releases_own_leases`.
  Có 1 FAIL, chưa chạy 1.443 ca còn lại, DB test đã được dọn.

Để áp dụng với tệp đã lưu, đồng bộ phụ thuộc, khởi động lại API/worker V1
và tạo lượt bóc tách mới. Phiên này chưa khởi động lại app, phát hành hay
tạo chỉ mục live.
