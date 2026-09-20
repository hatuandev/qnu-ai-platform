# Nhật Ký Làm Việc — 2026-09-20 (Phiên #167)
## Tinh Giản Giao Diện Trợ Lý AI & Tách Biệt DAG Visual Studio Thành Màn Hình Độc Lập

### 1. Bối Cảnh & Mục Tiêu
- **Bối cảnh**: Màn hình Chi tiết Trợ lý AI (`/assistants/:id`) trước đó xuất hiện nhiều chi tiết gây quá tải thị giác và thông tin dư thừa:
  - 4 thẻ KPI thô/giả (128 lượt chạy, 240 ms latency, duplicate tên kho tri thức, duplicate Ragas TM-08).
  - Chuỗi ID kỹ thuật dài dòng (`ast_admissions`) hiển thị dưới tên trợ lý.
  - Hộp lý thuyết tĩnh về chiến lược Chunking trong phần Gắn kết Tri thức RAG.
  - Dải cảnh báo Publish Gate 5 tiêu chí bị nhuộm màu đỏ chói toàn màn hình khi đang ở trạng thái bản nháp.
  - Toàn bộ đồ thị DAG Studio trực quan (vốn là một Studio rộng lớn với Node Catalog và Property Inspector) bị ép nhồi vào một sub-tab bên trong trang cấu hình, dẫn đến việc vỡ layout âm mép `-m-6` và giao diện chật chội.
- **Mục tiêu**:
  - Dọn sạch toàn bộ thông tin thừa và dữ liệu giả theo yêu cầu người dùng.
  - Tách DAG Studio thành một trang độc lập toàn màn hình chuẩn Master-Detail Deep Routing (`/workflows/:id`), có nút điều hướng qua lại liền mạch giữa Trợ lý và Quy trình.
  - Rút gọn hệ thống sub-nav của Trợ lý AI về 3 tab cấu hình cốt lõi.

---

### 2. Các Thay Đổi Kỹ Thuật (Key Changes)

#### A. Frontend
1. **[`assistant-header.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/components/assistants/assistant-header.tsx)**:
   - Xóa bỏ 4 thẻ KPI mock (128 runs, 240ms, v.v.).
   - Loại bỏ hiển thị chuỗi technical ID `assistant.id` gây rối mắt.
   - Thêm nút hành động nổi bật `[Sơ đồ DAG Studio]` điều hướng thẳng tới `/workflows/:id?returnTo=/assistants/:code`.
   - Làm dịu container Publish Gate: sử dụng `bg-card border` phẳng, giữ trọn vẹn nghiệp vụ thẩm định tiêu chí và blocker nhưng không còn nhuộm đỏ toàn màn hình.
   - Xóa bỏ các icon thừa: `Activity`, `Clock`, `Library`, `ShieldCheck`.
2. **[`assistant-workspace-nav.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/components/assistants/assistant-workspace-nav.tsx)**:
   - Rút gọn danh sách `WORKSPACE_TABS` từ 8 tabs xuống còn **3 tabs cấu hình trọng tâm**:
     - `overview`: "Thông tin & Tri thức" (icon `Bot`)
     - `models`: "Mô hình & An toàn" (icon `Cpu`)
     - `tools`: "Quy trình & Công cụ" (icon `Wrench`)
   - Dọn sạch các icon không còn dùng: `History`, `MessageSquare`, `Network`, `Share2`, `ShieldCheck`.
3. **[`assistant-knowledge-section.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/components/assistants/sections/assistant-knowledge-section.tsx)**:
   - Xóa bỏ khối ghi chú lý thuyết "Khuyến nghị Chiến lược Chunking & RAG" (`ClauseBasedChunker` vs `SemanticChunker`).
   - Xóa import `Sparkles` không dùng.
4. **[`assistant-tools-section.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/components/assistants/sections/assistant-tools-section.tsx)**:
   - Cập nhật nút "Mở đồ thị DAG Studio" đính kèm tham số `?returnTo=/assistants/:code`.
5. **[`assistant-detail-page.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/pages/assistant-detail-page.tsx)**:
   - Bổ sung hook tự động chuyển tiếp nếu người dùng vào URL `/assistants/:id/workflow` sang `/workflows/:id?returnTo=...`.
   - Xóa component lồng `DAGCanvasPage` để giải phóng bundle và triệt tiêu lỗi layout lồng ghép.
   - Loại bỏ `runsQuery` và `kpiStats` không còn sử dụng.
6. **[`dag-canvas-page.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/pages/dag-canvas-page.tsx)**:
   - Đọc tham số `returnTo` từ query URL.
   - Cập nhật nút Back quay về `returnTo` nếu có, và bổ sung thêm nút trực quan `[Quay lại Trợ lý]` ngay trên thanh tiêu đề studio.

#### B. Backend
1. **[`ingestion_service.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/knowledge/services/ingestion_service.py)**:
   - Dùng `getattr(doc, "status", ...)` và `getattr(doc, "index_status", ...)` nhằm tránh lỗi `AttributeError` khi đối tượng doc trong test case là mock/SimpleNamespace.

---

### 3. Kết Quả Kiểm Thử (Verification)
- **Frontend**:
  - `npm run typecheck`: **0 lỗi** (`tsc --noEmit`).
  - `npm run lint`: **0 lỗi** (Biome check 167 files sạch).
  - `npm run build`: **Thành công** (`vite build` trong 13.54s).
- **Backend**:
  - `uv run ruff check .`: **0 lỗi** (All checks passed).
  - `uv run --extra dev pytest tests/test_knowledge.py -k test_studio_view_reports_size_and_chunks`: **PASSED**.
