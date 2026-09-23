# NHẬT KÝ LÀM VIỆC — PHIÊN #205
**Ngày**: 2026-09-23 | **Thời gian**: 14:25 (UTC+7)
**Người thực hiện**: AI Senior Full-Stack Architect & Enterprise AI Systems Specialist
**Chủ đề**: Thiết Kế Giao Diện Combos & Vision Adapter Chuẩn 9Router Proxy Theo Hệ Thống UI Rule QNU

---

## 1. Mục Tiêu & Bối Cảnh Nghiệp Vụ
- **Yêu cầu người dùng**: Lấy ý tưởng thiết kế giao diện từ công cụ `9Router Proxy` (bao gồm: màn hình danh sách Combos với các chiến lược Fallback / Round Robin / Fusion, phân hệ Vision Adapter, Modal "Create Combo" và Modal "Add Model to Combo" với các chips capabilities), nhưng phải bảo đảm tuân thủ 100% các tiêu chuẩn thiết kế (UI Rule) của Trường Đại học Quy Nhơn.
- **Tiêu chuẩn áp dụng**: 
  - Màu chủ đạo: Academic Teal `--primary: oklch(0.46 0.13 160)` (Dark Mode: `oklch(0.67 0.13 160)`).
  - Triệt tiêu hoàn toàn emoji ký tự, 100% icon `lucide-react`.
  - Quy chuẩn bo góc: `rounded-md` cho nút/input, `rounded-lg` cho card/dialog.
  - Zero Biome linter errors, Zero TypeScript errors.

---

## 2. Các Thay Đổi Kỹ Thuật Chi Tiết

### 2.1. Backend Architecture (Schemas & Catalog Service)
1. **Schema DTOs (`backend/app/modules/modelops/schemas.py`)**:
   - Thêm `ModelComboItem`: `id`, `name`, `strategy: "fallback" | "round_robin" | "fusion"`, `models: list[OCRComboItem]`, `is_default: bool`, `description`.
   - Thêm `VisionAdapterConfig`: `enabled: bool`, `strategy: "fallback" | "round_robin"`, `models: list[OCRComboItem]`.
   - Mở rộng `SystemModelDefaults` và `SystemModelDefaultsUpdate` hỗ trợ quản lý nhiều combo và vision pool.

2. **Dịch Vụ Catalog (`backend/app/modules/modelops/services/model_catalog_service.py`)**:
   - Khởi tạo combo mẫu chuẩn QNU `combo_qnu_ocr_master` (`qnu-ocr-master`, chiến lược `fallback`, 5 bước chuẩn của nhà trường, `is_default: True`).
   - Khởi tạo cấu hình mặc định `vision_adapter` (`enabled: True`, `strategy: "fallback"`).
   - Tự động đồng bộ `ocr_combo_chain` và `default_ocr_model` khi người dùng thay đổi hoặc gắn một combo làm mặc định.

### 2.2. Frontend Architecture (React 19 & QNU Design System)
1. **Types (`frontend/src/types/modelops.ts`)**:
   - Bổ sung interface `ModelComboItem` và `VisionAdapterConfig`.
   - Mở rộng `SystemModelDefaults`.

2. **Component Combos & Vision Section (`frontend/src/components/modelops/combos-vision-section.tsx`)**:
   - **Khối Explainer 3 Chiến Lược**: Card giải thích trực quan:
     - `Fallback`: Thử tuần tự theo thứ tự ưu tiên (chuyển sang model tiếp theo khi lỗi / 429 Quota).
     - `Round Robin`: Xoay vòng mô hình qua từng request để phân tải.
     - `Fusion`: Truy vấn song song đa mô hình và tổng hợp kết quả tốt nhất.
   - **Danh Sách Combos Cards**:
     - Hiển thị dải pills các mô hình theo thứ tự (`#1 Gemini 2.5 Flash`, `#2 Gemini Flash-Lite`, `#3 Mistral OCR 2503`...).
     - Huy hiệu trạng thái: `Fallback` (sky), `Round Robin` (amber), `Fusion` (purple), `Mặc Định Kho Tri Thức` (emerald).
     - Thanh thao tác: Gắn làm mặc định (`CheckCircle2`), Chỉnh sửa (`Pencil`), Xóa (`Trash2`).
     - Empty State bo tròn với icon `Layers` khi chưa có combo.
   - **Phân Hệ Vision Adapter**:
     - Hàng **Vision** (hình ảnh, scan, tables): Switch Bật/Tắt, Switch chế độ Fallback/Round Robin, dải badges các model trong Vision pool, nút `+ Thêm Model`.
     - Hàng **Audio** (âm thanh, giọng nói): Switch Bật/Tắt, nút `+ Thêm Model`.
   - **Dialog "Tạo / Chỉnh Sửa Combo" (Create/Edit Combo Modal)**:
     - Input tên combo `Combo Name` (placeholder: `my-combo`, hint quy chuẩn tên).
     - Select chiến lược điều phối (`Fallback`, `Round Robin`, `Fusion`).
     - Khung danh sách mô hình bên trong combo: Box dashed border khi chưa có model kèm nút `+ Thêm Mô Hình Vào Combo`. Danh sách thẻ model có thứ tự `#1, #2...`, nút di chuyển lên `ArrowUp`, xuống `ArrowDown`, nút xóa `Trash2`.
     - Checkbox gắn làm OCR Mặc Định Hệ Thống.
   - **Dialog "Thêm Mô Hình Vào Combo" (Add Model to Combo Modal)**:
     - Banner gợi ý: Info icon, "Bấm vào mô hình để thêm, bấm lại lần nữa để gỡ bỏ. Thay đổi sẽ được cập nhật tự động."
     - Search bar tìm kiếm nhanh.
     - Phân nhóm theo Provider (Google Gemini, Mistral Cloud, Cloudflare Workers AI, Local Edge Engine...).
     - Danh sách Pills / Chips:
       - Tên mô hình.
       - Capability icons: `Eye` (Vision/OCR), `Brain` (Reasoning/Thinking), `Zap` (Tốc độ cao), `Cpu` (Local Engine).
       - Hiệu ứng toggle selected: Highlight viền teal `border-primary`, nền `bg-primary/10`, icon `Check`.

3. **Tích Hợp Vào Màn Hình ModelOps (`frontend/src/pages/modelops-page.tsx`)**:
   - Thêm Segmented Tabs phân hệ:
     - Tab 1: **"Combos & Vision Adapter"** (icon `Layers`, badge số lượng Combos).
     - Tab 2: **"Nhà Cung Cấp & Khóa API"** (icon `Server`, badge số lượng Providers).
     - Tab 3: **"Mặc Định Hệ Thống"** (icon `Sparkles`).
   - Tổng hợp danh mục mô hình khả dụng `allAvailableModels` từ active providers để truyền vào dialog chọn model.

---

## 3. Kết Quả Kiểm Thử (Verification)

| Suite | Lệnh | Kết Quả |
| :--- | :--- | :--- |
| **Backend Linter** | `uv run ruff check .` | **All checks passed (0 lỗi)** |
| **Backend Pytest** | `uv run --extra dev pytest tests/test_ocr.py tests/test_modelops.py -v` | **36/36 passed (100%)** |
| **Frontend Linter** | `npm run lint` (`biome check src`) | **171 files checked, 0 errors** |
| **Frontend Typecheck** | `npm run typecheck` (`tsc --noEmit`) | **0 errors** |
| **Frontend Production Build** | `npm run build` (`tsc -b && vite build`) | **Thành công trong 6.83s** |

---

## 4. Kế Hoạch Tiếp Theo
- Trải nghiệm trực tiếp trên giao diện Dev server (Port 3001) tại mục `/models` để kiểm tra tương tác mượt mà giữa các modal và card.
- Thử tạo thêm các combo tùy chỉnh (ví dụ `fast-cheap-combo`, `high-accuracy-combo`) và chuyển đổi linh hoạt.
