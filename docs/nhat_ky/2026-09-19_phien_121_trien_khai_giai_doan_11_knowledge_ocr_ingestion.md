# NHẬT KÝ LÀM VIỆC — PHIÊN #121

- **Thời gian thực hiện**: 19:15 – 19:28, ngày 19/09/2026
- **Mục tiêu phiên**: Triển khai hoàn tất **Giai đoạn 11: Knowledge Workspace — Nối Kín Upload → OCR → Verify → Approve → Index & Modular Hóa Scan Studio (Đợt 4 Kế Hoạch 06)**.
- **Tiêu chuẩn tuân thủ**: `AGENTS.md` (Quy định 1-8), Zero Big-Ball-of-Mud, Single Responsibility Principle, Master-Detail Deep Routing, Zero Mojibake, Zero Linter & Type Errors.

---

## 1. Tóm Tắt Nhiệm Vụ & Bối Cảnh

Tệp `scan-studio-page.tsx` trước đây là một file monolithic gần 1000 dòng kết hợp cả Canvas hiển thị bounding boxes, toolbar phân trang & zoom, inspector Markdown & JSON AST, cùng logic nạp file và đối soát. Đồng thời, luồng đối soát OCR của tài liệu trong Kho Tri Thức (`CollectionDetailPage`) chưa được nối kín với API phê duyệt và atomic indexing của Backend.

Phiên #121 đã hoàn thành trọn vẹn:
1. **Phân rã SRP tệp monolithic `scan-studio-page.tsx`** thành 4 sub-modules chuyên biệt đặt tại `frontend/src/components/knowledge/ocr/`:
   - `types.ts`: Toàn bộ types, constants `REGION_COLORS`, `OCR_ENGINE_OPTIONS`, và interfaces.
   - `ocr-canvas.tsx`: Canvas chuyên trách hiển thị ảnh scan gốc (`image_url`), zoom tỷ lệ, và bounding boxes đa màu theo vùng.
   - `ocr-toolbar.tsx`: Thanh điều khiển phân trang (`<< < X/Y > >>`), zoom controls, filter bounding box, và bộ chọn OCR Engine.
   - `ocr-inspector.tsx`: Thanh kiểm tra 4 tab chuyên sâu: Markdown (Render, Raw, Live Edit), Excel Spreadsheet Viewer, Bounding Regions list với confidence & bbox, và JSON AST.
   - `index.ts`: Barrel export chuẩn mực.
2. **Tái cấu trúc Orchestrator `ScanStudioPage`**:
   - Rút gọn file xuống ~260 dòng sạch sẽ.
   - Hỗ trợ song song 2 chế độ:
     - **Document Verification Mode** (khi có `documentId`): Tải dữ liệu thật từ `GET /documents/:id/studio-view`, hiển thị ảnh trang scan thật (`/pages/:page/image`), hỗ trợ cán bộ sửa tay Markdown từng trang, và bấm **[Xác nhận đối soát & Phê duyệt]** để gọi `POST /documents/:id/approve` kèm `pages` để kích hoạt Atomic Indexing vào Qdrant và PostgreSQL FTS.
     - **Standalone OCR Lab Mode** (khi không có `documentId`): Giữ nguyên môi trường sandbox tải tệp thử nghiệm, chọn OCR engine và lưu thành Markdown.
3. **Deep Routing & Thống Nhất UI Studio**:
   - Cập nhật `route-resolver.ts` nhận diện canonical route `/knowledge/documents/:documentId/ocr`.
   - Cập nhật `App.tsx` truyền đầy đủ props `documentId`, `collectionId` và các navigation handlers.
   - Cập nhật `collection-detail-page.tsx` thay thế `DocumentVerificationStudioPage` bằng `ScanStudioPage`, kích hoạt deep routing khi cán bộ click nút **[Đối soát OCR]** trên danh sách tài liệu.

---

## 2. Chi Tiết Thay Đổi Kỹ Thuật

| Tệp Tin | Hành Động | Lý Do Kỹ Thuật |
| :--- | :--- | :--- |
| `frontend/src/components/knowledge/ocr/types.ts` | Tạo mới | Định nghĩa cấu trúc dữ liệu tường minh, chuẩn hóa màu sắc bounding box OKLCH |
| `frontend/src/components/knowledge/ocr/ocr-canvas.tsx` | Tạo mới | Tách biệt logic render canvas, ảnh gốc và bounding box ra khỏi trang chính |
| `frontend/src/components/knowledge/ocr/ocr-toolbar.tsx` | Tạo mới | Tách biệt các bộ điều khiển phân trang, zoom và engine |
| `frontend/src/components/knowledge/ocr/ocr-inspector.tsx` | Tạo mới | Tách biệt các tab kiểm tra Markdown, Excel, Regions và AST |
| `frontend/src/components/knowledge/ocr/index.ts` | Tạo mới | Barrel export cho toàn bộ module |
| `frontend/src/pages/scan-studio-page.tsx` | Tái cấu trúc | Đóng vai trò Orchestrator kết nối state và API Backend |
| `frontend/src/navigation/route-resolver.ts` | Chỉnh sửa | Bổ sung route canonical `/knowledge/documents/:documentId/ocr` |
| `frontend/src/App.tsx` | Chỉnh sửa | Tích hợp route OCR Studio với props đầy đủ |
| `frontend/src/pages/collection-detail-page.tsx` | Chỉnh sửa | Sử dụng chung `ScanStudioPage` cho subView `verify` và deep routing |
| `backend/tests/conftest.py` | Chỉnh sửa | Thêm `# noqa: E402` sửa cảnh báo Ruff linter |

---

## 3. Kết Quả Kiểm Thử Toàn Diện

```bash
# Frontend Linter (Biome)
npm run lint
# Output: Checked 162 files in 150ms. No fixes applied. (0 lỗi)

# Frontend Typecheck (TypeScript)
npm run typecheck
# Output: tsc --noEmit (0 lỗi)

# Frontend Production Bundle Build
npm run build
# Output: ✓ built in 7.94s, dist/assets/scan-studio-page-mf77hm-L.js 32.63 kB (Thành công 100%)

# Backend Linter (Ruff)
uv run ruff check .
# Output: All checks passed! (0 lỗi)

# Backend Pytest
uv run --extra dev pytest tests/test_assistant_workflow_ownership.py -q
# Output: 7 passed in 2.62s (100% pass)

# Zero Mojibake Audit
python scripts/check_mojibake.py
# Output: Tổng số tệp đã quét: 318. Không phát hiện bất kỳ lỗi Mojibake nào!
```
