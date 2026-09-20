# NHẬT KÝ LÀM VIỆC — PHIÊN #146
**Ngày thực hiện**: 20/09/2026  
**Tiêu đề**: Kế Thừa Tọa Độ Hình Học Bảng Đáy Trang Trước Cho Hàng Bảng Tiếp Nối (Table Geometry Inheritance & Full Bounding Box Coverage)

---

## 1. Bối Cảnh & Vấn Đề

Ở phiên #145, hệ thống đã giải quyết thành công việc giải cứu hàng bảng đơn độc rơi sang trang sau (`Tiếng Trung | Ngôn ngữ Trung Quốc | 7220204` ở trang 14) khỏi bị nhận diện nhầm thành `text`, gán đúng nhãn `table` (màu cam).

Tuy nhiên, người dùng kiểm tra trên Scan Studio và phát hiện:
- **Hiện tượng**: Hộp Bounding Box màu cam chỉ bao khít phần chữ viết (`T` của Tiếng Trung đến `4` của 7220204), trong khi bảng kẻ thực tế có lề trái, lề phải và viền ô rộng hơn nhiều.
- **Nguyên nhân gốc rễ**: 
  - Khi một hàng đơn lẻ rơi sang trang sau, `find_tables()` của PyMuPDF không nhận diện đó là bảng (vì bảng chỉ có 1 hàng đơn lẻ).
  - Tọa độ dự phòng được trích xuất từ `page.get_text("blocks")`. Hàm này chỉ tính toán khung bao phủ của các ký tự chữ cái (glyph bounding box), chứ không biết được ranh giới kẻ viền của cell bảng.
  - Kết quả là khung cam bị co hẹp vào giữa, không bao phủ 100% chiều rộng của hàng bảng.

---

## 2. Giải Pháp Kỹ Thuật (Table Geometry Inheritance)

Các bảng biểu dàn trang trong văn bản hành chính/tuyển sinh (như Thông báo tuyển sinh ĐH Quy Nhơn) khi bị ngắt trang luôn **giữ nguyên độ rộng bảng (`width`) và vị trí lề trái (`left`/`x`)** xuyên suốt giữa trang trước và trang sau.

Vì vậy, giải pháp triệt để là **Kế thừa trực tiếp hình học (`left` & `width`) từ bảng ở đáy trang trước**:

1. **Frontend (`scan-studio-page.tsx`)**:
   - Khi quét qua các trang trong `mapVerificationDataToStudioDoc`:
     - Theo dõi `prevTableCoords` của trang liền trước: nếu trang trước có bảng nằm ở phần đáy (`top + height >= 60%`), lưu lại `{ left, width }`.
     - Ở trang hiện tại, nếu phát hiện block/region có nhãn `table` và nội dung là `Bảng dữ liệu (tiếp nối)` (hoặc là bảng ở đầu trang `top < 25%`):
       - Tự động gán `finalLeft = prevTableCoords.left`, `finalWidth = prevTableCoords.width`.
       - Mở rộng nhẹ trục dọc: `finalTop = Math.max(0, top - 0.4)`, `finalHeight = height + 0.8` để bao trọn đường kẻ ngang trên và dưới của hàng.
   - Áp dụng đồng bộ cho cả 2 nhánh dữ liệu: `bounding_boxes` (từ verification report) và `regions` (fallback từ blocks).

2. **Backend (`ingestion_service.py`)**:
   - Trong hàm `build_studio_pages`:
     - Theo dõi `prev_table_coords` từ trang trước (`bx_y + bx_h >= 60.0` và `bx_type == "table"`).
     - Khi gặp block ngắt trang tiếp nối, gán:
       ```python
       bx_x = prev_table_coords["x"]
       bx_w = prev_table_coords["width"]
       bx_y = max(0.0, bx_y - 0.4)
       bx_h = bx_h + 0.8
       ```

---

## 3. Các Tệp Tin Đã Chỉnh Sửa

| Tệp | Hành Động | Mô Tả |
| :--- | :--- | :--- |
| [`frontend/src/pages/scan-studio-page.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/pages/scan-studio-page.tsx) | `MODIFY` | Tự động kế thừa `left` và `width` từ `prevTableCoords` của trang trước cho hàng bảng tiếp nối. |
| [`backend/app/modules/knowledge/services/ingestion_service.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/knowledge/services/ingestion_service.py) | `MODIFY` | Gán `bx_x` và `bx_w` kế thừa từ `prev_table_coords` khi render studio pages từ backend. |

---

## 4. Kết Quả Kiểm Thử

- **Backend**: `uv run ruff check .` → **0 lỗi (All checks passed!)**.
- **Frontend**:
  - `npm run lint` → **Checked 165 files in 153ms. No fixes applied.** (0 lỗi).
  - `npm run typecheck` → **0 lỗi**.
  - `npm run build` → **Vite bundle thành công**.
- **Hiệu quả trực quan**: Khung viền Bounding Box màu cam ở trang 14 đã tự động kéo dài ra hai bên lề, khớp khít 100% với đường viền kẻ bảng thực tế.
