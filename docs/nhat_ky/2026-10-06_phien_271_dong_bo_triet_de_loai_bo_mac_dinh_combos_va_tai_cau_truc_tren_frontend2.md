# NHẬT KÝ LÀM VIỆC: ĐỒNG BỘ TRIỆT ĐỂ LOẠI BỎ MẶC ĐỊNH & COMBOS TRÊN FRONTEND2 (PORT 3000)

- **Thời gian**: 2026-10-06 09:25:00
- **Phiên làm việc**: Phiên 271
- **Kỹ sư / AI Agent**: Senior Full-Stack Architect & Enterprise AI Systems Specialist
- **Mục tiêu**: Loại bỏ dứt điểm tab "Mặc Định" & "Combos" trên màn hình ModelOps (`/models`), chuyển toàn bộ quyền quản lý mô hình Vector Embedding và Vision OCR vào từng Kho Tri Thức (`/knowledge`), chuyển Cross-Encoder Reranker sang từng Trợ lý AI (`/assistants`) trên ứng dụng thực tế `frontend2` (chạy tại cổng 3000).

---

## 1. Bối Cảnh & Nguyên Nhân Gốc Rễ (Root Cause)

- **Hiện tượng**: Người dùng phản ánh ảnh chụp màn hình tại `http://localhost:3000/models` vẫn hiển thị Tab "Mặc Định" và "Combos".
- **Nguyên nhân cốt lõi**:
  - Dự án có 2 thư mục frontend:
    1. `frontend/` (Port 3001) — Studio trước đó.
    2. `frontend2/` (Port 3000) — Client ứng dụng đang phục vụ người dùng qua lệnh `make dev1` (`make.ps1`).
  - Lượt refactor ban đầu đã áp dụng thành công trên `backend/` và `frontend/`, nhưng chưa đồng bộ hoàn tất sang thư mục `frontend2/`.

---

## 2. Các Thay Đổi Kỹ Thuật Đã Triển Khai (Frontend2)

### A. Tinh gọn ModelOps Page (`frontend2/src/features/modelops/modelops-page.tsx`)
1. **Loại bỏ 100% Tab "Mặc Định" và "Combos"**:
   - Gỡ bỏ các nút chuyển đổi `mainViewMode` (`providers` | `defaults` | `combos`).
   - Gỡ bỏ hoàn toàn `SystemDefaultsCard` và `CombosVisionSection`.
   - Dọn dẹp toàn bộ query và mutation dư thừa: `defaultsQuery`, `updateDefaultsMutation`, `setDefaultMutation`.
2. **Giao diện ModelOps thuần khiết**:
   - Màn hình `/models` tập trung 100% vào quản trị Nhà cung cấp AI (Model Providers), API Key Vault, hạn ngạch (Quota) và Circuit Breaker.

### B. Kho Tri Thức: Cấu hình Vector Embedding & Vision OCR Độc Lập
1. **Types & API Client**:
   - `frontend2/src/types/knowledge.ts`: Khai báo `CollectionDataProcessingConfig` (embedding model/provider/dim, OCR mode, primary/fallback OCR model/provider, ocr rescue).
   - `frontend2/src/services/knowledge-api.ts`: Hỗ trợ `data_processing` trong `getCollections`, `getCollection`, `createCollection`, `updateCollection`.
2. **Dialog Cấu hình 3 Tabs (`frontend2/src/components/knowledge/dialogs/collection-config-dialog.tsx`)**:
   - **Tab Cơ bản**: Đổi tên kho, mô tả phạm vi tri thức.
   - **Tab Vector Embedding**: Lựa chọn mô hình Embedding cho kho (BGE-M3 1024D, OpenAI 1536D/3072D).
     - **Bảo vệ Vector Invariance**: Khóa chọn Embedding nếu kho đã có tài liệu (`document_count > 0`), hiển thị thông báo an toàn toán học.
   - **Tab Vision OCR**: Chọn mô hình OCR Chính (`qwen3-vl:8b` RTX 5090 On-Premise) và Dự phòng (`gemini-3.1-flash-lite`), kèm Switch bật/tắt OCR Rescue.
3. **Đồng bộ Trang Chi Tiết & Danh Sách**:
   - `frontend2/src/features/knowledge/collection-detail-page.tsx` và `knowledge-page.tsx`: Nối đầy đủ props `documentCount`, `dataProcessingConfig`, `setDataProcessingConfig` vào dialog lưu cấu hình.

### C. Trợ Lý AI: Cấu hình Cross-Encoder Reranker Theo Persona
1. **Types & Form Mapping**:
   - `frontend2/src/types/assistants.ts` & `src/components/assistants/types.ts`: Bổ sung `reranker_policy` (`enabled`, `model_name`, `top_k`, `score_threshold`).
   - `frontend2/src/features/assistants/assistant-detail-page.tsx`: Map dữ liệu 2 chiều trong `toEditForm` và `updateMutation`.
2. **Giao diện Trợ lý (`frontend2/src/components/assistants/sections/assistant-knowledge-section.tsx`)**:
   - Bổ sung Card "Xếp Hạng Lại (Cross-Encoder Reranker)" với Switch Bật/Tắt, Dropdown chọn model (`bge-reranker-base`, `bge-reranker-large`, `ms-marco-MiniLM-L-6-v2`, `cohere-rerank-v3`), trường `top_k` và `score_threshold`.
   - Hiển thị thông điệp giải thích rõ ràng khi tắt Reranker (RRF trực tiếp, 0ms độ trễ).

---

## 3. Kết Quả Kiểm Thử (Verification)

- **Frontend2 Build**: Chạy `npm run build` (`vite build && tsc --noEmit`):
  - **Kết quả**: `✓ built in 3.22s` — **Exit Code 0, 0 lỗi TypeScript, 0 lỗi cú pháp**.
- **Hot-Reloading**: Giao diện `http://localhost:3000/models` đã được Vite tự động cập nhật ngay lập tức.
