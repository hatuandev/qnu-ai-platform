# NHẬT KÝ LÀM VIỆC — Cập Nhật Quy Trình 02 (MinIO Ingestion) & Tích Hợp Dynamic Active Models Cho Ingestion Wizard

- **Thời gian**: 2026-09-16 15:30 (UTC+7)
- **Người thực hiện**: AI Senior Full-Stack Architect & Enterprise AI Systems Specialist
- **Mục tiêu**:
  1. Cập nhật tài liệu quy trình chuẩn [`docs/quy_trinh/02_nap_tri_thuc_minio.md`](file:///d:/DuAnPhanMem/qnu-ai-platform/docs/quy_trinh/02_nap_tri_thuc_minio.md):
     - Xác định rõ vai trò **PDF Inspector**: Với tệp PDF chứa văn bản kỹ thuật số (digital text $\ge 40$ ký tự), hệ thống trích xuất siêu tốc (10-30ms) qua engine native để bảo toàn bảng biểu; chỉ những trang scan dạng ảnh hoặc không có text mới kích hoạt mô hình OCR.
     - Lọc mô hình động từ **Quản Lý Provider**: Chỉ hiển thị các mô hình thuộc Provider có trạng thái Đang Bật (`is_active = True`). Provider tắt sẽ tự động biến mất khỏi menu lựa chọn.
     - Tuân thủ 100% nguyên tắc lưu trữ: File upload gốc lưu tại MinIO S3 (`qnu-ai-documents`), siêu dữ liệu, facts và chunks lưu tại PostgreSQL 16, vectors lưu tại Qdrant.
  2. Nâng cấp giao diện Frontend **Ingestion Wizard** tại [`frontend/src/pages/knowledge-page.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/pages/knowledge-page.tsx):
     - Lấy danh sách provider từ API `getModelProviders()`, lọc theo `p.is_active === true`.
     - Tích hợp 2 dropdown động: **Mô hình OCR (Provider BẬT)** và **Mô hình Embedding (Provider BẬT)** kèm badge `Active`.
     - Gắn hộp thông tin hướng dẫn về cơ chế **PDF Inspector tự động**.

---

## 1. Chi Tiết Thực Hiện

### 1.1. Cập Nhật Tài Liệu Quy Trình [`02_nap_tri_thuc_minio.md`](file:///d:/DuAnPhanMem/qnu-ai-platform/docs/quy_trinh/02_nap_tri_thuc_minio.md)
- Cập nhật biểu đồ luồng `flowchart TD` (Mermaid) thể hiện tầng Dynamic Provider Selection và tầng PDF Inspector phân nhánh bóc tách.
- Bổ sung chi tiết kỹ thuật cho 7 bước: Lọc Provider Đang Bật, MinIO Object Storage, Phân nhánh PDF Inspector vs OCR, Làm sạch văn bản, Phân mảnh (Clause vs Semantic), Trích xuất Fact Layer và Đánh chỉ mục kép (Dual Indexing).

### 1.2. Nâng Cấp Giao Diện Ingestion Wizard
- Thay thế dropdown OCR tĩnh bằng dữ liệu thực tế từ các Provider đang bật:
  - Menu OCR: Hiển thị các mô hình OCR đang bật (ví dụ: `Mistral AI — mistral-ocr-latest`, `Docling Local — docling-tableformer-local`).
  - Menu Embedding: Hiển thị các mô hình vector đang bật (ví dụ: `Local SentenceTransformers — BAAI/bge-m3`, `Cloudflare Workers AI — @cf/baai/bge-m3`).
- Bổ sung Banner thông báo: "💡 Cơ chế PDF Inspector tự động...".

---

## 2. Kết Quả Kiểm Thử (Verification)

1. **Backend Tests**:
   - `uv run ruff check .`: 0 errors.
   - `uv run --extra dev pytest -v`: 73/73 passed (100%).
2. **Frontend Checks**:
   - `npm run lint`: Biome check 0 errors.
   - `npm run typecheck`: TypeScript tsc 0 errors.
   - `npm run build`: Vite build thành công (8.39s).
3. **Browser Subagent E2E Verification**:
   - Truy cập `http://localhost:3000/knowledge`, chuyển tab "Nạp Tri Thức".
   - Xác nhận dropdown hiển thị đầy đủ các mô hình OCR và Embedding từ Provider đang bật, banner thông tin hiển thị trực quan. Ảnh chụp: `knowledge_ingest_wizard_1789547191111.png`.
