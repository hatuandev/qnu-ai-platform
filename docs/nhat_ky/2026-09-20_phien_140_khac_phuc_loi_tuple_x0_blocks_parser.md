# NHẬT KÝ PHIÊN LÀM VIỆC — PHIÊN #140
# Ngày: 2026-09-20 | Nội dung: Khắc Phục Lỗi AttributeError: 'tuple' object has no attribute 'x0' Khi Upload PDF Bóc Tách Bảng Biểu

## 1. Mục Tiêu Phiên Làm Việc
Khắc phục triệt để lỗi crash 500 khi upload tài liệu qua endpoint `POST /platform/v1alpha1/knowledge/collections/{id}/upload`:
`AttributeError: 'tuple' object has no attribute 'x0'` tại [backend/app/modules/knowledge/parsers/blocks.py](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/knowledge/parsers/blocks.py) dòng 137.

---

## 2. Các Tệp Tin Đã Thay Đổi

| Tệp | Hành Động | Lý Do Kỹ Thuật |
| :--- | :--- | :--- |
| [`backend/app/modules/knowledge/parsers/blocks.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/knowledge/parsers/blocks.py) | MODIFY | Bổ sung hàm `_get_bbox_coords` an toàn đa hình xử lý cả `tuple`, `list`, `fitz.Rect` và `dict`; chuẩn hóa `table_bboxes` dạng `tuple[float, float, float, float]` chống crash thuộc tính `x0` |

---

## 3. Kết Quả Kiểm Thử
- `uv run ruff check .`: All checks passed! 0 lỗi.
- `uv run --extra dev pytest tests/test_knowledge.py -v`: 31/31 passed (100%).
