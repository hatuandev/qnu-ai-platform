# Phiên875 — Bóc tách DOCX trực tiếp bằng Docling

Người dùng yêu cầu DOCX lấy nội dung trực tiếp từ tệp Word. Phiên874 đã xác định
bộ chuyển PDF tính lại trường công thức ở bảng nguồn và thay đổi số hiển thị trước
khi Compiler đọc canonical.

## Thay đổi

- `docling_source.py` đọc bằng backend Word của Docling đã ghim. Tắt bộ chuyển
  Office của Docling, lấy vị trí OOXML và giữ bytes gốc của ảnh raster nhúng.
- `direct_docx.py` giữ cấu trúc bảng, ô gộp, vị trí ô khuyết và giá trị trường
  đã lưu. Canonical lưu `source_locator` và `pagination=document`. Bbox của
  chữ OCR ảnh nhúng quy chiếu theo ảnh. Hình vẽ chưa đọc được có cảnh báo.
- Worker xử lý DOCX bằng Docling theo định dạng tệp và chỉ gọi MinerU cho ảnh
  raster nhúng. PDF tiếp tục theo luồng xử lý trang. Tệp gốc và artifact của các
  lượt cũ được bảo toàn. Tạo lượt bóc tách mới để áp dụng thay đổi.
- Trang nguồn mở Word gốc và hiển thị văn bản theo đơn vị tài liệu. Lượt cũ vẫn
  đọc được theo hợp đồng trang của artifact đã lưu.

## Kiểm chứng

- Bóc tách và kiểm tra canonical trực tiếp ba DOCX ở phiên874. Kết quả có lần
  lượt 9, 0 và 4 bảng. Báo cáo2025 và Phương hướng2024 còn cảnh báo hình vẽ.
- Biên soạn nhanh cục bộ Phương hướng2024 giữ đủ 4 bảng, dòng tổng khớp cả bốn
  giá trị lưu trong Word, dẫn chứng bảng và ô trỏ `word/document.xml`.
- `make.ps1 test-be` với `PYTEST_ADDOPTS=-k` chọn `auto_extraction_710`,
  `image_ocr_870`, `ocr_processing_api`, `ocr_observability_644`,
  `native_extraction_710` hoặc `compiler_source_first_854` đạt 61 PASS, exit 0.
  Hợp đồng không có PDF dàn trang trả 409 `run_not_ready`.
- Full gate `make.ps1 test-be` tái hiện ca lỗi đã ghi nhận trong
  `test_chat_shared_admission_751.py`. Dừng riêng tiến trình pytest cô lập sau
  khi thấy lỗi. Harness exit 1 và xác nhận đã xóa DB test, giữ sentinel legacy.
  Bộ tổng chưa chạy hết 1.442 ca. Ca bảng DOCX từng lỗi ở phiên872 đã đạt.
- Ruff trong phạm vi sửa, Biome và `npm run build` đạt. Vitest ba tệp về xem
  bản gốc, polling và API OCR đạt 23 PASS. Build còn cảnh báo Vite sẵn có.
- Test tích hợp ảnh Word dùng adapter giả lập. Chưa gửi lại tài liệu thật qua
  MinerU trong phiên này. Các phép thử dùng tệp cục bộ và DB kiểm thử cô lập.

## Áp dụng

Khởi động lại API và worker bằng mã mới, mở nguồn Word đã lưu và chọn **Bóc tách
lại**. Biên soạn từ lượt mới sau khi đối chiếu các ô quan trọng với tệp Word.
Lượt đã hoàn tất trước khi thay mã vẫn đọc được để đối chiếu lịch sử.
