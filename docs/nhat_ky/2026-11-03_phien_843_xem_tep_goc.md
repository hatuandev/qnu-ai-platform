# Phiên 843 — Ưu tiên xem tệp gốc

API tiến độ trả `used_ocr` theo kết quả OCR đã lưu của từng trang. V1 mở
tệp gốc cho trang đọc trực tiếp hoặc chưa có kết quả. Trang có kết quả OCR
mở chế độ đối chiếu, có thể chuyển sang tệp gốc. Nội dung bóc tách và rà soát
vẫn truy cập được.

Biome, build frontend, 26 Vitest và Ruff đạt. Hai ca backend cô lập cho PDF
hỗn hợp và MinerU đạt. Chưa kiểm tra trực quan trên app đang chạy.
