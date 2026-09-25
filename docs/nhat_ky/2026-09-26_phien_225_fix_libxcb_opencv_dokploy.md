# NHẬT KÝ LÀM VIỆC — PHIÊN #225
**Ngày**: 2026-09-26 | **Thời gian**: 00:05 (UTC+7)
**Tiêu đề**: Fix Migrate Crash Thiếu libGL/libxcb Cho OpenCV Trên Slim

---

## 1. Triệu Chứng (log Dokploy)
- `DEV_ACCESS_PASSWORD` đã qua; DB kết nối OK và tự tạo `qnu_ai_platform`.
- `db migrate` chết: `Database migration failed: libxcb.so.1: cannot open shared object file`.
- Nguyên nhân: `app/modules/ocr/layout_detector.py:15` import `cv2` ở top-level → mọi lệnh `app.cli` đều nạp OpenCV; bản `opencv-python` (non-headless) cần lib hệ thống X11/GL mà image `python:3.12-slim` không có.

## 2. Thay Đổi
- `backend/Dockerfile`: thêm `libgl1 libglib2.0-0` vào apt install (chuẩn fix OpenCV trên slim, kéo theo chuỗi libxcb).
- Không đổi dependencies Python (giữ cả 2 bản opencv như `pyproject`, tránh rủi ro runtime OCR).

## 3. Kết Quả
- Chưa redeploy kiểm chứng (cần rebuild layer apt, nhanh vì cache từ bước này trở xuống mới build lại — lưu ý layer apt thay đổi nên các layer sau build lại, nhưng deps `.venv` cache theo `pyproject` không đổi nên vẫn nhanh).
