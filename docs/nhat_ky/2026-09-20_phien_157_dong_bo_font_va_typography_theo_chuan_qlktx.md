# NHẬT KÝ PHIÊN LÀM VIỆC #157
**Ngày**: 2026-09-20 | **Thời gian**: 17:45 (UTC+7)
**Mục tiêu**: Đồng bộ hóa 100% font chữ (`font-family`, typography scale, font loading và inheritance) của dự án Quản lý Ký túc xá ĐH Quy Nhơn (`D:\DuAnPhanMem\QLKTX\qnu-ktx\src\Web\ClientApp`) sang `qnu-ai-platform/frontend`.

---

## 1. Bối Cảnh & Nguyên Nhân Gây Lệch Font
- Người dùng phản ánh font chữ và font size hiển thị giữa `qnu-ai-platform` và `qnu-ktx` không đồng nhất.
- Qua đối soát trực tiếp mã nguồn của `qnu-ktx`:
  1. `qnu-ktx` **không tải Google Fonts** trong `index.html`, mà sử dụng Native System Font Stack:
     ```css
     font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
     ```
     Trên hệ điều hành Windows, hệ thống ưu tiên font **`Segoe UI`** (hoặc `Inter` native nếu có) kết hợp ClearType rendering cho độ sắc nét tuyệt đối và chuẩn xác dấu thanh tiếng Việt. Ngược lại, `qnu-ai-platform` trước đó tải web font CDN Inter của Google làm thay đổi rendering optical size.
  2. `qnu-ktx` áp dụng quy tắc bắt buộc trong `@layer base`:
     ```css
     button,
     input,
     select,
     textarea {
       font: inherit;
     }
     ```
     Giúp toàn bộ form controls thừa hưởng đồng bộ font chữ từ `body`.
  3. Bổ sung `<meta name="color-scheme" content="light dark" />` chuẩn QLKTX.
  4. Đồng bộ hóa bộ thông số `--font-size-*` trong `tokens.css` và line-height các utility classes `.type-*`.

---

## 2. Chi Tiết Các Thay Đổi Kỹ Thuật

| Tệp | Hành Động | Mô Tả Kỹ Thuật |
| :--- | :--- | :--- |
| [`frontend/index.html`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/index.html) | MODIFY | Loại bỏ liên kết tải CDN Google Fonts Inter; bổ sung `<meta name="color-scheme" content="light dark" />` chuẩn QLKTX. |
| [`frontend/src/styles/globals.css`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/styles/globals.css) | MODIFY | Cập nhật `--font-sans: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;`; cập nhật `body` và bổ sung `button, input, select, textarea { font: inherit; }`; đồng bộ line-height các utility classes `.type-*` chuẩn QLKTX. |
| [`frontend/src/styles/tokens.css`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/styles/tokens.css) | MODIFY | Chuẩn hóa toàn bộ bộ tokens font size theo đúng QLKTX: `--font-size-page-title: 1.875rem`, `--font-size-section-title: 1.125rem`, `--font-size-body: 0.875rem`, `--font-size-table-header: 0.8125rem`, `--font-size-caption: 0.875rem`, `--font-size-metadata: 0.6875rem`. |

---

## 3. Kết Quả Kiểm Thử Toàn Diện
- **Biome Linter**: `npm run lint` đạt **0 errors** (166 files checked in 166ms).
- **TypeScript Typecheck**: `npm run typecheck` đạt **0 errors**.
- **Vite Build**: `npm run build` hoàn thành đóng gói production bundle thành công.
