# Nhật Ký Làm Việc — 2026-09-17: Đồng Bộ 100% Khung Nhận Diện Scan Bố Cục Thông Minh Giống QNU-AI-Core

## 1. Thời Gian & Mục Tiêu
- **Thời gian**: Phiên làm việc ngày 17/09/2026 (Phiên #46).
- **Mục tiêu**: Rà soát và đối soát 100% với UI / chức năng của `qnu-ai-core` theo ảnh chụp người dùng cung cấp (`localhost:3000/knowledge/kb_admissions/ingest`):
  - Nhận diện đa phân vùng trực quan thông minh: `table` (Bảng biểu), `title` (Tiêu đề loại văn bản), `text` (Khối văn bản), `header` (Tiêu đề đầu trang), `list` (Danh sách), `signature` (Con dấu & Chữ ký).
  - Khắc phục lỗi hiển thị khung: Kết nối đúng hàm `SmartLayoutDetector.detect_layout_regions` của OpenCV trong backend.
  - Định dạng huy hiệu badge chuẩn xác: Góc trên bên trái (`top: -10px, left: 4px`), chữ thường (lowercase: `table`, `title`, `text`, `header`, `signature`), màu viền và nền phân biệt chuẩn xác.
  - Hiệu ứng tia quét laser AI Scan Active chuyển động mượt mà.

## 2. Chi Tiết Thay Đổi Kỹ Thuật (Key Changes)

### Backend:
1. [`backend/app/modules/knowledge/service.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/knowledge/service.py):
   - Thay thế lệnh gọi lỗi `detector.detect_regions(img_bgr)` thành `detector.detect_layout_regions(img_bgr, markdown_text=page_text, page_number=p_num)` chuẩn OpenCV.
   - Nhận diện trọn vẹn 6 loại khối: `table`, `title`, `text`, `header`, `list`, `signature`.
   - Mở rộng `DEFAULT_BOX_CONFIDENCE` thêm `"title": 0.94`, `"list": 0.91`, `"signature": 0.95`.
   - Nâng cấp cơ chế fallback thông minh cho văn bản hành chính khi không có ảnh scan gốc: tổng hợp cấu trúc letterhead bảng phía trên, tiêu đề (`title`), nội dung (`text`), và chữ ký (`signature`).

### Frontend:
1. [`frontend/src/services/api-client.ts`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/services/api-client.ts):
   - Mở rộng union types `DocumentBoundingBox["type"]` và `DocumentRegion["type"]` với `"title" | "signature" | "list"`.
2. [`frontend/src/components/admin/document-bounding-visualizer.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/components/admin/document-bounding-visualizer.tsx):
   - Thêm bảng màu `REGION_COLORS` kế thừa từ `qnu-ai-core`:
     - `header`: `#3b82f6` (badge `#2563eb`)
     - `title`: `#8b5cf6` (badge `#7c3aed`)
     - `text`: `#a855f7` (badge `#9333ea`)
     - `list`: `#10b981` (badge `#059669`)
     - `table`: `#f59e0b` (badge `#d97706`)
     - `signature`: `#f43f5e` (badge `#e11d48`)
   - Hàm `getEffectiveType` chuẩn hóa giữa `box.label` và `box.type`.
   - Huy hiệu `box.label` hiển thị ở góc trên bên trái (`top: -10px, left: 4px`), font 8px bold, chữ thường, bóng mờ sắc nét.
   - Bộ lọc `Lọc: [Tất cả] [Bảng] [Văn bản] [Dấu & Ký]` hoạt động chuẩn xác theo `effectiveType`.
   - Khung canvas tài liệu hỗ trợ tỷ lệ chuẩn A4 `aspect-[1/1.414]` khi chưa có ảnh scan.
3. [`frontend/src/components/admin/regions-inspector.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/components/admin/regions-inspector.tsx):
   - Hỗ trợ đầy đủ icon và badge cho `title` (Sparkles), `list` (ListOrdered), `signature` (Stamp).

## 3. Kết Quả Kiểm Thử (Verification)
- **Frontend**:
  - `npm run lint`: Biome check 77 files, 0 errors.
  - `npm run typecheck`: TypeScript tsc --noEmit, 0 errors.
  - `npm run build`: Vite build đóng gói thành công trong 5.83s.
- **Backend**:
  - `uv run ruff check .`: 0 errors.
  - `uv run --extra dev pytest tests/test_knowledge.py -v`: 23/23 tests pass.
  - `uv run --extra dev pytest -q`: 115/115 tests pass 100%.
