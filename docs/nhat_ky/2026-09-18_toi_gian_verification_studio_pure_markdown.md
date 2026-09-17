# NHẬT KÝ LÀM VIỆC — Tối Giản Verification Studio Chuyên Biệt Pure Markdown (Phương Án 1)
**Ngày**: 2026-09-18 | **Thời gian**: 00:52 | **Phiên**: #76

---

## 1. Yêu Cầu Người Dùng & Mục Tiêu
- **Bối cảnh**: Tại màn hình Document Verification Studio, khung bên phải trước đó tồn tại 3 tab: "Văn bản", "Markdown" và "Bố cục & Khối".
- **Vấn đề**:
  - Gây dư thừa và nhầm lẫn về mặt định danh: Tab "Văn bản" thực chất là Markdown render theo từng trang (kèm nút sửa tay), còn tab "Markdown" lại là toàn bộ tài liệu nối 14 trang.
  - Tab "Bố cục & Khối" mang nặng tính kỹ thuật, danh sách tọa độ bounding boxes ít cần thiết khi khung bên trái đã vẽ sẵn các viền khung trực quan trên ảnh scan.
- **Quyết định (Phương án 1 - Tối giản toàn diện)**:
  - Bỏ hoàn toàn tab "Văn bản" và tab "Bố cục & Khối".
  - Chuyển toàn bộ khung bên phải thành **Giao diện Markdown tinh gọn**:
    - Bộ chọn phạm vi: `[Trang X (Trang hiện tại)]` vs `[Toàn bộ file (N trang)]`.
    - Bộ chuyển chế độ: `[Xem render]` vs `[Mã nguồn .md]`.
    - Công cụ: `[Sửa tay]`, `[Sao chép]`, `[Tải file .md]`.

---

## 2. Thay Đổi Kỹ Thuật Chi Tiết (Key Changes)

### Frontend: [`document-verification-studio-page.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/pages/document-verification-studio-page.tsx)
1. **Dọn dẹp mã chết & dependencies (Boy Scout Rule 8.1 & 8.2)**:
   - Gỡ bỏ import `Layers` và component `RegionsInspector`.
   - Loại bỏ `allRegions` useMemo không còn sử dụng.
   - Thay thế state `rightTabMode: "raw" | "markdown" | "regions"` bằng `markdownScope: "page" | "all"`.
2. **Thiết kế Right Toolbar tối giản**:
   - Scope Switcher bằng `<Tabs>`:
     - `Trang {currentPage}` (icon `FileText` text-primary)
     - `Toàn bộ file ({total_pages} trang)` (icon `FileCode`)
   - Nút `Sửa tay` (khi ở scope `page`): Tích hợp sẵn toggle `Xem trước` / `Sửa tiếp` và `Lưu sửa`.
   - Nút `Mã nguồn .md` / `Xem render` (icon `Code` / `Eye`).
   - Nút `Sao chép` & `Tải xuống .md` tự động linh hoạt theo phạm vi đang chọn (sao chép/tải về trang hiện tại hoặc toàn bộ file).
3. **Cải tiến Body Content**:
   - **Scope "page"**:
     - Hiển thị banner đánh dấu trang: `<!-- Trang X / N -->`.
     - Chế độ xem trước render với GFM Markdown (bảng, danh sách, blockquote).
     - Chế độ mã nguồn thô hiển thị code block font mono.
     - Chế độ sửa tay với textarea và xem trước trực tiếp.
   - **Scope "all"**:
     - Hiển thị danh sách toàn bộ các trang được render phân cách rõ ràng hoặc mã nguồn toàn văn.
4. **Footer Stats đồng bộ**:
   - Scope "page": Hiện số từ, số dòng của trang đó.
   - Scope "all": Hiện tổng số ký tự và tổng số trang.

---

## 3. Kết Quả Kiểm Thử (Verification)
1. **Frontend Linting & Typecheck**:
   - `npm run lint`: **0 lỗi** (91 files checked).
   - `npm run typecheck`: **0 lỗi** (`tsc --noEmit`).
   - `npm run build`: Vite build thành công (**9.72s**).
2. **Zero Mojibake**:
   - `python scripts/check_mojibake.py`: **225/225 files sạch**, 0 lỗi encoding.
