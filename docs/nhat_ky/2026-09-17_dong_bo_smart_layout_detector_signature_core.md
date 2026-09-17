# Nhật Ký Làm Việc — Đồng Bộ 100% Khung Nhận Diện Scan Bố Cục Thông Minh & Con Dấu / Chữ Ký Giống QNU-AI-Core

- **Thời gian thực hiện**: 2026-09-17 23:55 (UTC+7)
- **Phiên số**: #48
- **Kỹ sư phụ trách**: Senior Full-Stack Architect & Enterprise AI Systems Specialist

---

## 1. Mục Tiêu Phiên Làm Việc
1. Rà soát so sánh trực quan và bóc tách cơ chế nhận diện scan layout giữa `qnu-ai-core` và `qnu-ai-platform` qua 4 ảnh chụp thực tế (Trang 1, 2, 9 Đề án tuyển sinh 2026 và Quyết định 2327 có con dấu đỏ và chữ ký).
2. Làm rõ bản chất và vai trò của `pdf inspector` trong Core so với `SmartLayoutDetector` (OpenCV).
3. Khắc phục dứt điểm nguyên nhân khiến tài liệu hiển thị danh sách thô `Khối văn bản 1..15` mà không hiện con dấu đỏ `signature` và phân vùng bố cục.
4. Bổ sung tính năng quét lại bố cục thông minh (Smart Re-scan) trên giao diện Frontend.

---

## 2. Các Thay Đổi Kỹ Thuật Chi Tiết (Key Changes)

### 2.1. Backend
- [`backend/app/modules/knowledge/service.py`](../../backend/app/modules/knowledge/service.py):
  - Bổ sung static method `_is_stale_raw_blocks(page_blocks: dict)`: Tự động kiểm tra nếu toàn bộ metadata trong CSDL chỉ chứa các khối thô chưa phân loại (`Khối văn bản N`, thiếu `signature`, `table`, `title`, `header`, `list`).
  - Cập nhật `_ensure_page_blocks(self, db, doc, refresh_layout=False)`: Bỏ qua stale cache và kích hoạt `SmartLayoutDetector.detect_layout_regions` trên ảnh pixmap PDF thực tế (OpenCV HSV segmentation + morphology line extraction), sau đó lưu đè kết quả phân vùng chuẩn vào CSDL.
  - Cập nhật `get_studio_view(self, db, document_id, refresh_layout=False)`: Chuyển tiếp cờ ép quét lại layout từ API.
- [`backend/app/modules/knowledge/router.py`](../../backend/app/modules/knowledge/router.py):
  - Mở rộng endpoint `GET /documents/{document_id}/studio-view` tiếp nhận query parameter `refresh_layout: bool = False`.

### 2.2. Frontend
- [`frontend/src/services/api-client.ts`](../../frontend/src/services/api-client.ts):
  - Cập nhật `getStudioView` và `getDocumentVerification` hỗ trợ tham số `refreshLayout: boolean = false`.
- [`frontend/src/components/admin/document-bounding-visualizer.tsx`](../../frontend/src/components/admin/document-bounding-visualizer.tsx):
  - Bổ sung nút "Quét lại" (Smart Scan) với icon `Sparkles`, hỗ trợ trạng thái xoay spinner khi đang quét và disabled an toàn.
- [`frontend/src/pages/document-verification-studio-page.tsx`](../../frontend/src/pages/document-verification-studio-page.tsx):
  - Tích hợp `handleRescanLayout` kích hoạt API quét lại layout và invalidate TanStack Query cache.

---

## 3. Kết Quả Kiểm Thử (Verification)
- **Backend Quality**:
  - `uv run ruff check .`: 0 errors.
  - `uv run --extra dev pytest tests/test_knowledge.py -v`: 23/23 passed.
  - `uv run --extra dev pytest -q`: 117/117 passed (100%).
- **Frontend Quality**:
  - `npm run lint`: Biome check 77 files, 0 errors.
  - `npm run typecheck`: TypeScript 0 errors.
  - `npm run build`: Vite build thành công trong 5.56s.
