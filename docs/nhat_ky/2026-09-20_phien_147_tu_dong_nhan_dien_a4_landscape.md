# NHẬT KÝ LÀM VIỆC — PHIÊN #147
**Ngày thực hiện**: 20/09/2026  
**Tiêu đề**: Tự Động Nhận Diện & Thích Ứng Khổ Giấy A4 Nằm Ngang (Landscape) & Đứng (Portrait) Trong Scan Studio

---

## 1. Bối Cảnh & Câu Hỏi Của Người Dùng

Người dùng kiểm tra tài liệu gồm 22 trang (trang 1-2 là tờ trình/kế hoạch đứng, trang 3-22 là các bảng biểu Phụ lục nằm ngang) và đặt câu hỏi:
> *"hình như chế độ review không phải là chế độ xem pdf thuần phải không sao nó không nhận dạng được A4 nằm ngang ?"*

### Phân tích kỹ thuật:
1. **Bản chất của Chế độ Review (Scan Studio / Verification Mode)**:
   - Không phải là một iframe nhúng PDF thuần (PDF Viewer thông thường của trình duyệt).
   - Đây là **Studio Đối Soát Thị Giác Tài Liệu (Visual Document AI / OCR Studio)** giống như cơ chế của **Mistral Document AI Playground, AWS Textract hay Google Cloud Document AI**.
   - Trình nhúng PDF thuần không thể hiển thị lớp phủ Bounding Boxes ngữ nghĩa đa màu (`text`, `table`, `header`, `signature`), không thể sửa trực tiếp Markdown từng trang, không thể gắn nhãn và không hỗ trợ quy trình phê duyệt Human-in-the-loop.
2. **Nguyên nhân không nhận dạng được A4 nằm ngang (Landscape) trước đó**:
   - Ở phiên #144, để chống sụp đổ chiều cao (height collapse) khi ảnh đang nạp, khung giấy bị gán cứng tỷ lệ A4 đứng `aspect-[1/1.414]` (chiều cao gấp 1.414 lần chiều rộng) và thẻ `<img>` bị gán `object-fill`.
   - Với tài liệu hỗn hợp: Trang 1-2 là A4 đứng, nhưng **trang 3 đến 22 là A4 NẰM NGANG (Landscape)**.
   - Khi trang ngang bị ép vào khung đứng:
     * Bề ngang bị bóp nghẹt từ 1131px xuống 800px.
     * Bề dọc bị kéo dãn ngoằng ngoẵng từ 800px lên 1131px.
     * Chữ bị kéo dài, các cột bảng biểu bị ép dúm dó lại sát rạt nhau.

---

## 2. Giải Pháp Tự Động Nhận Diện & Thích Ứng Khổ Giấy

Triển khai cơ chế **Dynamic Aspect-Ratio & Orientation Matching**:

1. **Frontend (`ocr-canvas.tsx`)**:
   - Tự động nhận diện hướng giấy từ kích thước ảnh thực tế (`naturalWidth` & `naturalHeight`):
     ```typescript
     const nw = e.currentTarget.naturalWidth;
     const nh = e.currentTarget.naturalHeight;
     const isLandscape = nw > nh;
     const aspectRatio = nw / nh; // ~Math.SQRT2 cho Landscape, ~1/Math.SQRT2 cho Portrait
     ```
   - Khung `page-canvas` áp dụng `style={{ aspectRatio: `${aspectRatio}` }}` linh hoạt, bỏ class cứng `aspect-[1/1.414]`.
   - Độ rộng hiển thị `effectivePageWidth`: tự động mở rộng `baseWidth * Math.SQRT2` khi là trang Landscape, giúp bảng biểu nằm ngang có đầy đủ không gian hiển thị rộng rãi, thoáng đãng như file PDF gốc.
   - Thẻ `<img>`: chuyển sang `object-contain w-full h-full`, bảo đảm ảnh khớp khít 100% từng pixel với khung mà không bị méo mó, co kéo.
   - Chuẩn hóa Bounding Boxes theo `baseW` và `baseH` tương ứng với hướng giấy (`1131 x 800` cho Landscape, `800 x 1131` cho Portrait).

2. **Frontend (`scan-studio-page.tsx`) & Types (`knowledge.ts`)**:
   - Mở rộng `DocumentVerificationData.pages` hỗ trợ `dimensions?: { width: number; height: number; orientation?: "portrait" | "landscape" }`.
   - Trong `mapVerificationDataToStudioDoc`, tôn trọng `p.dimensions` từ Backend.

3. **Backend (`ingestion_service.py` & `service.py`)**:
   - Trong `_ensure_page_blocks`, đọc kích thước trang `page.rect` từ PyMuPDF, xác định `orientation = "landscape" if pw > ph else "portrait"`, lưu vào `doc.doc_metadata["page_dimensions"]`.
   - Trong `build_studio_pages`, gắn `dimensions` vào từng trang trả về trong API `get_studio_view`.

---

## 3. Các Tệp Đã Chỉnh Sửa

| Tệp | Hành Động | Mô Tả |
| :--- | :--- | :--- |
| [`frontend/src/components/knowledge/ocr/ocr-canvas.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/components/knowledge/ocr/ocr-canvas.tsx) | `MODIFY` | Tự động nhận diện A4 Landscape/Portrait từ `naturalWidth/Height`, dynamic aspect-ratio, mở rộng độ rộng trang ngang và dùng `object-contain`. |
| [`frontend/src/pages/scan-studio-page.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/pages/scan-studio-page.tsx) | `MODIFY` | Hỗ trợ `p.dimensions` động từ backend trong `mapVerificationDataToStudioDoc`. |
| [`frontend/src/types/knowledge.ts`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/types/knowledge.ts) | `MODIFY` | Bổ sung trường `dimensions` vào `DocumentVerificationData.pages`. |
| [`backend/app/modules/knowledge/services/ingestion_service.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/knowledge/services/ingestion_service.py) | `MODIFY` | Lưu và trả về `page_dimensions` cho từng trang trong `build_studio_pages` và `get_studio_view`. |
| [`backend/app/modules/knowledge/service.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/knowledge/service.py) | `MODIFY` | Cập nhật chữ ký `build_studio_pages` nhận `page_dimensions`. |

---

## 4. Kết Quả Kiểm Thử

- **Backend Linter**: `uv run ruff check .` $\rightarrow$ **All checks passed! (0 lỗi)**.
- **Frontend Linter**: `npm run lint` $\rightarrow$ **Checked 165 files in 153ms. No fixes applied. (0 lỗi)**.
- **TypeScript**: `npm run typecheck` $\rightarrow$ **0 lỗi**.
- **Bundle**: `npm run build` $\rightarrow$ **Vite bundle thành công**.
