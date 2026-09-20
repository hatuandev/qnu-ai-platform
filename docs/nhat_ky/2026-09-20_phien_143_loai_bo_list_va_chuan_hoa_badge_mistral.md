# Nhật Ký Làm Việc — Phiên 143 (2026-09-20)
## Loại Bỏ Phân Loại List Tràn Lan & Chuẩn Hóa Nhãn Nhận Diện Mistral OCR Không Đè Chữ

### 1. Thời Gian & Mục Tiêu
- **Thời gian**: 2026-09-20 14:21 UTC+7
- **Mục tiêu**:
  - Loại bỏ hoàn toàn phân loại `list` (màu xanh ngọc). Trả về trạng thái giao diện hài hòa ban đầu chuẩn Mistral Document AI OCR Playground: các nội dung văn bản, danh mục, căn cứ, phương thức tuyển sinh... đều là `text` (màu tím nhẹ nhàng).
  - Siết chặt điều kiện nhận diện `header`: Chỉ nhận diện ở đỉnh trang ($\le 16\%$) và BẮT ĐẦU bằng từ khóa hành chính/số hiệu. Chấm dứt hoàn toàn việc gán nhầm các đoạn văn ở giữa trang (như "Phương thức 2... theo quy định của Bộ Giáo dục và Đào tạo") thành `header`.
  - Siết chặt `title`: Chỉ nhận diện số La Mã lớn (`I. THÔNG TIN CHUNG`, `II. TUYỂN SINH...`), loại văn bản (`THÔNG BÁO`, `QUYẾT ĐỊNH`), hoặc dòng in hoa ngắn.
  - Sửa vị trí Pill Badge sang `-top-[13px] left-[-1px]`: Nằm bên ngoài phía trên viền hộp, mép dưới tiếp giáp đỉnh viền, kích thước siêu nhỏ `text-[8px] h-[13px] px-1 py-0 leading-[13px]`, bảo đảm 100% không bao giờ đè lên chữ bên trong hộp (như `ÔNG TIN CHUNG`, `YỂN SINH`).

### 2. Các Thay Đổi Kỹ Thuật (Key Changes)
- [`backend/app/modules/knowledge/parsers/blocks.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/knowledge/parsers/blocks.py):
  - Xóa bỏ phân loại `list` trong `classify_text_block`.
  - Siết chặt `header`: `top_percent <= 16.0 and re.match(r"^(?:bộ giáo dục|trường đại học|cộng hòa xã hội|độc lập\s*-\s*tự do|số\s*[:\/])", clean, re.I)`.
  - Siết chặt `title`: `re.match(r"^(?:I|II|III|IV|V|VI|VII|VIII|IX|X)\.\s+[A-ZÀ-Ỹ]", clean)`.
  - Mặc định toàn bộ là `text`.
- [`frontend/src/pages/scan-studio-page.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/pages/scan-studio-page.tsx):
  - Đồng bộ hàm `classifyStudioRegion`: Loại bỏ hoàn toàn nhánh `list`, siết chặt điều kiện `header` và `title`.
- [`frontend/src/components/knowledge/ocr/ocr-canvas.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/components/knowledge/ocr/ocr-canvas.tsx):
  - Chuyển vị trí Pill Badge sang `-top-[13px] left-[-1px] px-1 py-0 text-[8px] font-mono font-medium lowercase rounded-t-[2px] rounded-br-[2px] text-white shadow-xs pointer-events-none leading-[13px] h-[13px] z-20 select-none whitespace-nowrap`.

### 3. Kết Quả Kiểm Thử (Verification)
- **Backend**:
  - `uv run ruff check .`: 0 errors.
- **Frontend**:
  - `npm run lint`: Checked 165 files in 185ms. 0 errors.
  - `npm run typecheck`: 0 errors.
  - `npm run build`: vite build thành công trong 6.56s.
