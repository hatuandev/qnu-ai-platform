# Phiên #359 — Đánh giá chiến lược parser và layout

## Phạm vi

Tư vấn, đối chiếu code và nguồn chính thức; không sửa runtime, dữ liệu hoặc provider. Dùng skill qnu-knowledge-ingestion để ưu tiên phân luồng theo cấu trúc và chất lượng, không từ điển vá lỗi.

## Kết luận

Giữ Docling cho DOCX, PDF Inspector/native cho PDF số và PaddleOCR-VL cho scan. Không cần thay toàn bộ bằng một engine. PDF Inspector vừa phân loại vừa trích xuất; repo hiện phối hợp PyMuPDF tạo Markdown/geometry với Inspector metadata và fallback Markdown.

Khung nhận diện là output layout, không đồng nghĩa phải OCR. PDF số dùng native bbox; scan dùng bbox Paddle. DOCX backend Docling khai báo supports_pagination=False, cần render PDF dẫn xuất nếu yêu cầu Studio có trang và khung thật. Không tự gán bbox DOCX hoặc ánh xạ Markdown/PDF không được xác minh.

Đề xuất kiểm tra từng trang PDF, không chỉ toàn tài liệu; trang scan hoặc lớp chữ hỏng cần OCR. Không tự OCR trang trống chỉ vì thiếu chữ. Bảng/multi-column khó cần nhánh layout nâng cao theo quality gate; giữ native text tốt, tránh OCR mọi tài liệu. Chuẩn hóa page/block provenance, lưu layout JSON riêng Markdown, giữ ánh xạ nội dung sau normalization để Studio đối chiếu. OCR/parse một lần, tái sử dụng cho các model embedding.

## Nguồn đối chiếu

- https://github.com/docling-project/docling/blob/main/docling/backend/msword_backend.py — supports_pagination False.
- https://github.com/firecrawl/pdf-inspector — phân loại, trích xuất, per-page routing; tùy phiên bản và scan strategy.
- https://pymupdf.readthedocs.io/en/latest/app1.html — text block bounding boxes.
- https://github.com/PaddlePaddle/PaddleOCR/blob/main/docs/version3.x/pipeline_usage/PaddleOCR-VL.en.md — block_bbox/label/content/order và layout detection.

## Kiểm chứng và tệp thay đổi

Đọc parser/Inspector trong repo và tài liệu chính thức. Không chạy test/build mới vì không sửa code; kết quả 15 tests ở phiên #358 không được coi là kiểm chứng các đề xuất này. Chỉ cập nhật nhật ký, mục lục, memory và work log. Chưa benchmark engine trên tập tài liệu QNU, không kết luận engine nào tốt nhất tuyệt đối.
