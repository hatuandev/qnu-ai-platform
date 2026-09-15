# NHẬT KÝ LÀM VIỆC: THIẾT LẬP THƯ MỤC & TÀI LIỆU TRIỂN KHAI DOKPLOY
- **Thời gian**: 2026-09-15 16:20
- **Kỹ sư / Agent**: AI Senior Backend Architect & Enterprise Specialist
- **Mục tiêu phiên**: Xây dựng chuyên mục tài liệu kiến trúc hạ tầng và quy trình triển khai Dokploy cho dự án QNU AI Platform để toàn bộ đội ngũ phát triển và vận hành dễ dàng nắm bắt bối cảnh.

---

## 1. Bối Cảnh & Nhu Cầu
- Dự án đã hoàn thành toàn diện 8 giai đoạn Backend Modular Monolith với 68/68 unit/integration tests passed.
- Để phục vụ giai đoạn đưa sản phẩm lên máy chủ thực tế (VPS/Server) sử dụng nền tảng PaaS **Dokploy** kết hợp **Traefik Reverse Proxy**, nhóm phát triển cần một hệ thống tài liệu rõ ràng, trực quan, giải thích rõ:
  1. Các công nghệ sử dụng và lý do lựa chọn.
  2. Sơ đồ phân tầng mạng bảo mật (Zero Public Database Exposure).
  3. Quy trình 6 bước đưa ứng dụng lên Dokploy.
  4. Cơ chế an toàn dữ liệu qua 5 Named Volumes và runbook xử lý sự cố.

---

## 2. Các Thay Đổi Kỹ Thuật (Key Changes)
Đã khởi tạo chuyên mục tài liệu mới tại [`docs/trien_khai/`](../trien_khai/):
1. [`docs/trien_khai/README.md`](../trien_khai/README.md):
   - Bảng tổng hợp công nghệ triển khai: Dokploy, Traefik, FastAPI, ARQ Worker, PostgreSQL 16, Qdrant, Redis 7, MinIO, Gotenberg 8.
   - Sơ đồ kiến trúc mạng L7 Traefik và mạng cô lập nội bộ `qnu_internal_network`.
   - Phân tích lý do kiến trúc (Trade-off decisions).
2. [`docs/trien_khai/01_cong_nghe_ha_tang.md`](../trien_khai/01_cong_nghe_ha_tang.md):
   - Phân tích chuyên sâu vai trò của từng công nghệ và microservice trong hệ thống.
   - Cơ chế đệm stream SSE cho RAG để tránh lỗi 504 Gateway Timeout.
   - Bảng khuyến nghị cấu hình phần cứng máy chủ (Sizing Guide: Demo vs Production).
3. [`docs/trien_khai/02_quy_trinh_trien_khai_dokploy.md`](../trien_khai/02_quy_trinh_trien_khai_dokploy.md):
   - Quy trình 6 bước rõ ràng từ: Cài đặt Dokploy, trỏ DNS, tạo Compose Stack, điền biến môi trường, cấp phát SSL Let's Encrypt, chạy Alembic migration và smoke test.
   - Hướng dẫn quy trình cập nhật bản code mới qua Git Webhook (Day-2 Operations).
4. [`docs/trien_khai/03_an_toan_du_lieu_va_van_hanh.md`](../trien_khai/03_an_toan_du_lieu_va_van_hanh.md):
   - Cơ chế bảo vệ dữ liệu bằng 5 Named Volumes bền vững.
   - Quy trình sao lưu và phục hồi CSDL PostgreSQL và MinIO S3 bucket.
   - Sổ tay xử lý 4 sự cố phổ biến (SSE timeout, Circuit Breaker kích hoạt, MinIO bucket, Container unhealthy).
5. Cập nhật [`docs/deployment.md`](../deployment.md):
   - Liên kết trực tiếp tới cẩm nang `docs/trien_khai/`.

---

## 3. Tuân Thủ Tiêu Chuẩn (MinIO Compliance & Quality)
- Luồng tài liệu tuân thủ chuẩn lưu trữ S3 qua MinIO và bảo toàn dữ liệu bằng Persistent Volumes.
- Đảm bảo tính minh bạch và thống nhất giữa thiết kế kiến trúc và vận hành thực tế.
