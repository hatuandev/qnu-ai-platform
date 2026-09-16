# Nhật Ký Phát Triển: Live Ingestion Stepper Tracker & Rich Document Chunks Inspector (Hướng 1)

- **Thời gian**: 17:15 - 17:40, Thứ Tư, 16/09/2026 (UTC+7)
- **Tác giả**: Senior Full-Stack Architect & Enterprise AI Systems Specialist
- **Mục tiêu**: Kế thừa và nâng cấp các tính năng tinh hoa từ `qnu-ai-core` cho module Kho Tri Thức:
  1. Live Ingestion Stepper Tracker (Theo dõi tiến trình 4 chặng theo thời gian thực).
  2. Rich Document & Chunks Inspector (Giao diện 3 Tabs đối soát bóc tách chuyên sâu, số hóa fact và siêu dữ liệu MinIO).

---

## 1. Bối Cảnh & Cơ Sở Kiến Trúc

Theo phân tích kiến trúc từ `qnu-ai-core` và yêu cầu nâng tầm trải nghiệm người dùng trên QNU AI Platform:
- **Hạn chế trước đây**: Sau khi nhấn nút nạp tài liệu, hệ thống chỉ hiển thị trạng thái tải đơn điệu, người dùng không nắm được tài liệu đang nằm ở chặng nào (đã lưu MinIO chưa, đang chạy OCR hay đang vector hóa vào Qdrant). Khi xem lại tài liệu, danh sách chunks chỉ hiển thị dạng văn bản cơ bản, thiếu đối soát các bảng số liệu trích xuất (Fact Layer) và siêu dữ liệu kỹ thuật.
- **Giải pháp Hướng 1**:
  - **Live Stepper Tracker**: Hiển thị Modal theo dõi trực quan 4 chặng chuẩn mực (`MinIO S3 Raw` -> `Docling TableFormer / Mistral OCR` -> `ClauseBased / Semantic Chunking` -> `Qdrant 1024D Dense + PostgreSQL FTS Lexical Indexing`). Có thanh phần trăm động (0% -> 100%), tính toán thời gian latency ms từng chặng và cung cấp nút điều hướng ngay sang bảng tài liệu.
  - **Rich Document & Chunks Inspector**: Tổ chức 3 Tabs (`chunks`, `facts`, `meta`):
    - *Tab 1 (Ma Trận Chunks)*: Thẻ từng chunk với số từ, loại đoạn (Điều/Khoản), nút sao chép text tiện dụng kèm tooltip/badge phản hồi.
    - *Tab 2 (Lớp Dữ Liệu Số Hóa - Structured Fact Layer)*: Kết xuất bảng Markdown Table điểm chuẩn/chỉ tiêu/học phí đối soát trực tiếp số liệu đã bóc tách.
    - *Tab 3 (Siêu Dữ Liệu Kỹ Thuật MinIO & Qdrant)*: Hiển thị đường dẫn lưu trữ S3 Object URI, mã băm SHA-256 tính toàn vẹn, kích thước tệp, độ trễ và thông số Vector Embedding Specs.

---

## 2. Chi Tiết Thay Đổi Kỹ Thuật (Key Changes)

### 2.1. Thành phần Mới: `IngestionProgressModal`
- **Tệp tin**: [`frontend/src/components/admin/ingestion-progress-modal.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/components/admin/ingestion-progress-modal.tsx)
- **Chức năng**:
  - 4 stages có trạng thái động: `pending` | `running` | `completed`.
  - Icon trực quan: `Database` (MinIO S3), `Sparkles` (Docling/Mistral OCR), `FileCode` (Chunker), `CheckCircle` (Qdrant Indexing).
  - Thanh tiến trình mượt mà với hiệu ứng shimmer chuyển động.
  - Đồng bộ màu sắc chuẩn Academic Teal `--primary: oklch(0.46 0.13 160)`.
  - Bo góc 6px cho controls (`rounded-control`) và 8px cho surfaces (`rounded-surface`).

### 2.2. Nâng cấp Trang Chi Tiết Bộ Sưu Tập: `CollectionDetailPage`
- **Tệp tin**: [`frontend/src/pages/collection-detail-page.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/pages/collection-detail-page.tsx)
- **Chức năng**:
  - Tích hợp `IngestionProgressModal` khi submit form nạp văn bản.
  - Nâng cấp Modal xem Chunks (Dialog 6) thành **Rich Document & Chunks Inspector** với 3 Tabs chuyên sâu, cơ chế sao chép clipboard với phản hồi `Đã sao chép`, và bảng dữ liệu số hóa Markdown.
  - Dọn sạch các biến không sử dụng, bảo đảm 0 cảnh báo Biome.

### 2.3. Đồng bộ Trang Tổng Quan: `KnowledgePage`
- **Tệp tin**: [`frontend/src/pages/knowledge-page.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/pages/knowledge-page.tsx)
- **Chức năng**: Kích hoạt `IngestionProgressModal` trong Tab Ingest Wizard toàn cục `/knowledge`.

### 2.4. Bổ Sung Seed Fallback Providers
- **Tệp tin**: [`frontend/src/services/api-client.ts`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/services/api-client.ts)
- **Chức năng**: Cung cấp cấu hình mock 4 providers chuẩn (`Docling`, `Mistral`, `BGE-M3`, `Cloudflare Workers AI`) giúp hệ thống kiểm thử tự động và vận hành độc lập hoàn toàn đáng tin cậy.

### 2.5. Kiểm Thử Tự Động Playwright E2E Mới
- **Tệp tin**: [`frontend/tests/e2e/06_ingestion_stepper_and_inspector.spec.ts`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/tests/e2e/06_ingestion_stepper_and_inspector.spec.ts)
- **Chức năng**:
  - `TC-STEP-01`: Kiểm thử Live Stepper theo dõi 4 chặng pipeline nạp hoàn tất 100%.
  - `TC-STEP-02`: Kiểm thử Rich Inspector 3 Tabs và chức năng sao chép nội dung chunk.

---

## 3. Kết Quả Kiểm Thử & Nghiệm Thu (Verification)

```bash
# 1. Kiểm tra Linter Biome Frontend
npm run lint
# Output: Checked 61 files in 70ms. No fixes applied. (0 errors)

# 2. Kiểm tra Typecheck TypeScript Frontend
npm run typecheck
# Output: tsc --noEmit (0 errors)

# 3. Kiểm tra Build Production Frontend
npm run build
# Output: built in 6.46s (Thành công)

# 4. Kiểm thử Playwright E2E Suites 05 & 06 trên Google Chrome
npx playwright test tests/e2e/05_smart_auto_recommendation.spec.ts tests/e2e/06_ingestion_stepper_and_inspector.spec.ts --project="Google Chrome"
# Output: 5 passed (20.5s) - 100% PASS

# 5. Kiểm thử Backend Ruff & Pytest
uv run ruff check .
# Output: All checks passed! (0 errors)
uv run --extra dev pytest -v
# Output: 73 passed, 4 warnings in 5.78s (100% PASS)
```

---

## 4. Ảnh Chụp Màn Hình Nghiệm Thu

1. **Live Ingestion Stepper Completed**:
   `C:/Users/AnhTuan/.gemini/antigravity-ide/brain/744e6051-db17-49ba-b02b-56558fe5c873/live_ingestion_stepper_completed.png`
2. **Rich Chunks Inspector — Tab 1: Ma Trận Chunks & Sao Chép**:
   `C:/Users/AnhTuan/.gemini/antigravity-ide/brain/744e6051-db17-49ba-b02b-56558fe5c873/rich_chunks_inspector_tab1.png`
3. **Rich Chunks Inspector — Tab 2: Lớp Dữ Liệu Số Hóa (Fact Layer)**:
   `C:/Users/AnhTuan/.gemini/antigravity-ide/brain/744e6051-db17-49ba-b02b-56558fe5c873/rich_chunks_inspector_tab2_facts.png`
4. **Rich Chunks Inspector — Tab 3: Siêu Dữ Liệu MinIO & Qdrant Specs**:
   `C:/Users/AnhTuan/.gemini/antigravity-ide/brain/744e6051-db17-49ba-b02b-56558fe5c873/rich_chunks_inspector_tab3_metadata.png`
