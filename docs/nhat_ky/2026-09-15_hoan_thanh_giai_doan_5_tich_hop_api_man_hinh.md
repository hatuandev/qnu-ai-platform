# NHẬT KÝ LÀM VIỆC: HOÀN THÀNH GIAI ĐOẠN 5 FRONTEND (TÍCH HỢP API & CÁC MÀN HÌNH NGHIỆP VỤ CHUYÊN SÂU)
- **Thời gian**: 2026-09-15 21:55
- **Kỹ sư / Agent**: AI Senior Backend Architect & Enterprise Specialist
- **Mục tiêu phiên**: Hiện thực hóa toàn bộ **Giai đoạn 5: Tích Hợp API Thực Tế, Bộ Định Tuyến Hoàn Chỉnh & Các Màn Hình Nghiệp Vụ Chuyên Sâu** theo kế hoạch tại [`docs/ke_hoach/01_ke_hoach_phat_trien_fe.md`](file:///d:/DuAnPhanMem/qnu-ai-platform/docs/ke_hoach/01_ke_hoach_phat_trien_fe.md). Xây dựng lớp dịch vụ TanStack Query Client kết nối REST API backend (`/platform/v1alpha1/*`), cấu trúc 9 màn hình nghiệp vụ chuyên sâu tương ứng với 15 tuyến đường trong `NAVIGATION_CONFIG`, và hoàn tất kiểm định chất lượng 100%.

---

## 1. Tóm Tắt Các Thay Đổi Kỹ Thuật

| Cấu Phần / Màn Hình | Tệp Tin Mã Nguồn | Đặc Tả Kỹ Thuật & Nghiệp Vụ |
| :--- | :--- | :--- |
| **TanStack Query Client** | [`frontend/src/lib/query-client.ts`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/lib/query-client.ts) | Cấu hình `QueryClient` đồng bộ (`staleTime: 60s`, `gcTime: 5m`, `retry: 1`, `refetchOnWindowFocus: false`). |
| **API Client & Seed Data** | [`frontend/src/services/api-client.ts`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/services/api-client.ts) | Kết nối `/platform/v1alpha1/*` có gõ kiểu Typescript chặt chẽ: `getHealth()`, `getAssistants()`, `getCollections()`, `getDocuments()`, `getModelProviders()`, `getTokenQuotas()`, `getTools()`, `getEvaluationMetrics()`, `getGapInbox()`, `getWorkflowRuns()`. Tích hợp hạt giống tri thức chuẩn QNU khi backend offline. |
| **Bảng Điều Khiển Live** | [`frontend/src/pages/dashboard-page.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/pages/dashboard-page.tsx) | Thống kê số lượng Tokens, FinOps USD, TM-08 Faithfulness, cơ cấu chi phí LLM Providers, ping kết nối backend trực tiếp, và danh mục 05 Trợ lý AI. |
| **Quản Trị Tri Thức & Ingestion** | [`frontend/src/pages/knowledge-page.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/pages/knowledge-page.tsx) | Quản lý Collections tri thức, bảng văn bản tìm kiếm/lọc, Dialog xem trước nội dung chunk và Ingestion Wizard 3 bước (chọn hồ sơ OCR Docling/PyMuPDF/EasyOCR, thuật toán Chunking ClauseBased vs Semantic, lưu trữ MinIO S3). |
| **Mô Hình & Circuit Breaker** | [`frontend/src/pages/modelops-page.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/pages/modelops-page.tsx) | Quản lý danh sách LLM Providers (OpenAI, Gemini, Local vLLM), trạng thái Circuit Breaker (`CLOSED`, `OPEN`, `HALF_OPEN`), thanh tiến độ hạn ngạch Quota tháng, quy tắc Dynamic Fallback và thêm khóa API. |
| **Cổng Công Cụ & Tools** | [`frontend/src/pages/tools-page.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/pages/tools-page.tsx) | Tích hợp 3 Tools chuẩn nghiệp vụ QNU (Tra cứu điểm chuẩn UIS, Soạn thảo văn bản Word NĐ 30, Bảng tính đề thi Excel Bloom) kèm Tool Playground trực tiếp và cơ chế Human-in-the-loop. |
| **Kiểm Định Ragas TM-08** | [`frontend/src/pages/evaluation-page.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/pages/evaluation-page.tsx) | Đo lường 3 chỉ số Ragas TM-08: Faithfulness ($\ge 90\%$), Answer Relevance ($\ge 85\%$), Context Precision ($\ge 80\%$), bảng lịch sử chạy đánh giá và Hộp thư Tri thức Thiếu hụt (**Gap Inbox**). |
| **Hội Thoại & Handoff** | [`frontend/src/pages/conversations-page.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/pages/conversations-page.tsx) | Lịch sử các phiên hội thoại đa kênh, danh sách luồng tin nhắn, bảng điểm độ hài lòng và công tắc bàn giao tức thì cho Chuyên viên tư vấn (**Human Handoff**). |
| **Kênh & Nhúng Web Widget** | [`frontend/src/pages/channels-page.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/pages/channels-page.tsx) | Trình sinh mã nhúng Web Chat Widget (thẻ `<script>` nhúng vào Portal trường), bộ cấu hình tiêu đề, vị trí, lời chào mừng và khung mô phỏng Website 1:1 trực quan. |
| **Lịch Sử Thực Thi DAG Runs** | [`frontend/src/pages/runs-page.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/pages/runs-page.tsx) | Bảng ghi nhật ký các lượt chạy workflow, trạng thái kết quả, độ trễ và Dialog truy vết dòng thời gian Checkpoints (`Trace`). |
| **Cổng Developer & API Keys** | [`frontend/src/pages/developer-page.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/pages/developer-page.tsx) | Quản lý API Key các phòng ban, đoạn mã tích hợp SDK (cURL, Python, TypeScript) và liên kết tài liệu OpenAPI Swagger. |
| **Bộ Định Tuyến Trung Tâm** | [`frontend/src/App.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/App.tsx) | Bọc toàn bộ ứng dụng bằng `QueryClientProvider`, liên kết hoàn chỉnh 15 tuyến đường trong `NAVIGATION_CONFIG` vào `AdminShell`. |

---

## 2. Kết Quả Kiểm Thử & Nghiệm Thu (Verification)

### 2.1. Frontend Quality Checks
* **Biome Linter & Formatter**:
  ```powershell
  npm run lint
  # Checked 58 files in 67ms. No fixes applied. (0 errors, 0 warnings)
  ```
* **TypeScript Strict Typecheck**:
  ```powershell
  npm run typecheck
  # tsc --noEmit -> 0 errors (100% pass)
  ```
* **Vite Production Build**:
  ```powershell
  npm run build
  # ✓ 2474 modules transformed.
  # dist/index.html                     1.48 kB │ gzip:   0.82 kB
  # dist/assets/index-BwoKqK82.css     78.60 kB │ gzip:  12.97 kB
  # dist/assets/index-DLi6Epmm.js   1,010.57 kB │ gzip: 303.75 kB
  # ✓ built in 7.03s
  ```

### 2.2. Backend Regression Checks
* **Ruff Linter**: `uv run ruff check .` $\rightarrow$ `All checks passed!` (0 errors).
* **Pytest Test Suite**: `uv run --extra dev pytest` $\rightarrow$ `68 passed, 3 warnings in 4.23s` (100% pass).

---

## 3. Kết Luận
- **Giai đoạn 5**: **HOÀN THÀNH 100% (PASSED)**.
- Toàn bộ 5 giai đoạn phát triển Frontend theo lộ trình [`docs/ke_hoach/01_ke_hoach_phat_trien_fe.md`](file:///d:/DuAnPhanMem/qnu-ai-platform/docs/ke_hoach/01_ke_hoach_phat_trien_fe.md) đã được hoàn thiện đầy đủ, đạt chuẩn kiến trúc Enterprise, tích hợp sâu hạ tầng AI của Trường Đại học Quy Nhơn.
