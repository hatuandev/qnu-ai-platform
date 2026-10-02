# NHẬT KÝ LÀM VIỆC: KIỂM THỬ CHATBOT TUYỂN SINH BẰNG 20 CÂU

- **Thời gian:** 2026-10-02
- **Kỹ sư / Agent:** AI Senior Full-Stack Architect & Enterprise Specialist
- **Mục tiêu:** xây dựng đáp án chuẩn từ 7 PDF tuyển sinh, chạy 20 câu trên assistant `admissions`, chấm kết quả và ghi nhận hành vi ModelOps.

## 1. Công việc thực hiện

- Trích xuất và kiểm tra trực quan các trang PDF có bảng rộng để tránh lệch cột.
- Xác nhận trạng thái ingestion của `col_admissions`: 7 tài liệu, 132 chunks, 1.332 facts.
- Xây dựng bộ 20 câu gồm thông tin chung, phương thức, điều kiện, lịch, học phí, ưu tiên, quy đổi, chỉ tiêu, điểm chuẩn, cơ sở pháp lý, kết quả 2025 và No-Answer.
- Gọi API chat thật với hội thoại độc lập cho từng câu.
- Tách lần chạy bị hạn chế mạng và lần chạy dính semantic cache khỏi kết quả chính thức.
- Xóa 25 semantic cache của riêng collection trước lần chạy sạch.

## 2. Kết quả xác minh

- 20/20 request HTTP thành công.
- 14 câu đạt, 3 câu đạt một phần, 3 câu không đạt; điểm 77,5%.
- Độ trễ trung bình 5,685 giây; P95 7,628 giây; tối đa 7,817 giây.
- Các câu không đạt: Q06 phạm vi PT5, Q09 lịch năng khiếu, Q16 chỉ tiêu ngành.
- Quan sát runtime xoay khỏi khóa Gemini khi gặp 429 và tiếp tục fallback provider.
- Không chạy test/lint/build mã nguồn vì phiên chỉ đánh giá dữ liệu và hành vi runtime, không sửa logic ứng dụng.

## 3. Trạng thái

- **Hoàn thành báo cáo:** `docs/bao_cao/2026-10-02_kiem_thu_chatbot_tuyen_sinh_20_cau.md`.
- **Tồn tại P0:** không lưu semantic cache cho phản hồi suy giảm; tăng độ chính xác routing tài liệu theo năm và loại số liệu.
- **Giới hạn:** chưa kiểm chứng được xoay ba khóa Gemini thật do pool tại thời điểm kiểm thử chỉ có một khóa khả dụng.

