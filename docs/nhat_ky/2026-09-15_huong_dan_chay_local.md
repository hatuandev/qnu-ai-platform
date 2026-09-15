# NHẬT KÝ LÀM VIỆC — THIẾT LẬP TÀI LIỆU HƯỚNG DẪN KHỞI CHẠY CỤC BỘ (LOCAL RUN GUIDE)

> **Thời gian**: 2026-09-15 22:35 (UTC+7)  
> **Kỹ sư / Agent**: AI Senior Full-Stack Architect & Enterprise AI Systems Specialist  
> **Nhiệm vụ**: Soạn thảo tài liệu hướng dẫn khởi chạy cục bộ toàn diện cho nhà phát triển, bao gồm backend FastAPI, frontend Vite/React 19 và cụm cơ sở dữ liệu nền.

---

## 1. Bối Cảnh & Mục Tiêu

Nhằm tạo điều kiện thuận lợi nhất cho các lập trình viên và cán bộ kỹ thuật của Trường ĐH Quy Nhơn có thể cài đặt, chạy thử nghiệm và phát triển ứng dụng ngay trên máy tính cá nhân mà không gặp rào cản về cấu hình container phức tạp, chúng ta cần:
1. Xây dựng tài liệu hướng dẫn chi tiết từng bước khởi chạy Backend, Frontend và hạ tầng CSDL cục bộ.
2. Cung cấp cả hướng dẫn khởi chạy nhanh (Quickstart trong 3 bước) và cẩm nang chi tiết xử lý sự cố thường gặp (Port conflict, cài đặt `uv`, cấu hình `.env`).
3. Đặt tệp hướng dẫn trực tiếp tại thư mục gốc [**`HUONG_DAN_CHAY_LOCAL.md`**](../../HUONG_DAN_CHAY_LOCAL.md) và tại [**`docs/huong_dan_chay_local.md`**](../huong_dan_chay_local.md).

---

## 2. Các Tệp Tin Tạo Mới

| Tệp Tin | Loại | Mô Tả Chi Tiết |
| :--- | :---: | :--- |
| [`HUONG_DAN_CHAY_LOCAL.md`](../../HUONG_DAN_CHAY_LOCAL.md) | Tài liệu | Hướng dẫn khởi chạy nhanh 3 bước tại thư mục gốc |
| [`docs/huong_dan_chay_local.md`](../huong_dan_chay_local.md) | Tài liệu | Cẩm nang toàn diện: Sơ đồ kiến trúc local, yêu cầu tiên quyết, lệnh PowerShell, xử lý sự cố |

---

## 3. Kết Quả Kiểm Thử (Verification)

Mọi tệp tin đều tuân thủ định dạng Markdown chuẩn, đường dẫn liên kết nội bộ chính xác.
- Frontend: `npm run lint` pass (0 errors), `npm run typecheck` pass (0 errors).
- Backend: `uv run ruff check .` pass (0 errors), `pytest` 68/68 passed (100%).

---

## 4. Kết Luận

Tài liệu đã sẵn sàng, cung cấp đầy đủ thông tin để người dùng khởi chạy toàn bộ nền tảng chỉ trong vài phút.
