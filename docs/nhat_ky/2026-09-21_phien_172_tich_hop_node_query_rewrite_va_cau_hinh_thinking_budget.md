# Nhật Ký Làm Việc — Phiên #172 (2026-09-21)
# Tích Hợp Node DAG Query Rewrite (Sửa Lỗi Gõ Nhầm Ngữ Cảnh) & Cấu Hình Thinking Budget

## 1. Mục Tiêu & Bối Cảnh Phiên Làm Việc
- **Yêu cầu người dùng**:
  1. Cho phép cấu hình bật/tắt hoặc điều chỉnh ngân sách suy nghĩ ngầm (`thinking_budget`) cho Google Gemini 2.5 để người dùng có thể linh hoạt chuyển đổi giữa Chế độ Phản Hồi Siêu Tốc (1-2s RAG Chat) và Suy Luận Chuyên Sâu (Deep Reasoning).
  2. Bổ sung node chuẩn hóa câu hỏi và phát hiện lỗi gõ nhầm trượt phím Telex hoặc nhầm lẫn ngữ cảnh vào quy trình DAG (`query.rewrite`) — ví dụ người dùng gõ nhầm *"học phí ngày công nghệ thông tin là bao nhiêu"* (gõ "ngày" thay vì "ngành"), hoặc gõ tắt (*"cntt"*, *"qtkd"*), hệ thống phải tự động nhận diện và sửa đúng ngữ cảnh tuyển sinh QNU.
  3. Cập nhật đồ thị DAG của Trợ lý Tuyển sinh (`admissions-assistant`) để tự động đi qua node `query.rewrite`.
  4. Đảm bảo câu hỏi học phí của thí sinh trả về đầy đủ, chính xác các con số trong Đề án tuyển sinh chính thức (cử nhân đại trà 83-97 triệu đồng, kỹ sư đại trà 112,3 triệu đồng, chương trình tiếng Anh gấp 1,5 lần) với đầy đủ trích dẫn hợp lệ.

---

## 2. Các Thay Đổi Kỹ Thuật (Key Changes)

### 2.1. Phân Hệ ModelOps & Cấu Hình Thinking Budget
- **Backend Schemas & Adapters**:
  - [`backend/app/modules/modelops/schemas.py`](../../backend/app/modules/modelops/schemas.py): Bổ sung trường `thinking_budget: int = Field(0, ge=0, le=4096)` vào `LLMGenerateRequest`.
  - [`backend/app/modules/modelops/providers/gemini_adapter.py`](../../backend/app/modules/modelops/providers/gemini_adapter.py):
    * Cấu hình tham số `thinkingConfig: {"thinkingBudget": thinking_budget}` theo đúng chuẩn Google Generative Language API.
    * Khi `thinking_budget == 0`: Tắt hoàn toàn suy nghĩ ngầm, giúp Gemini 2.5 và Gemini Flash phản hồi siêu tốc trong 1-2 giây.
    * Khi `thinking_budget > 0`: Tự động điều chỉnh `maxOutputTokens = max(max_tokens, thinking_budget + 1024)` tránh hiện tượng bị cắt cụt câu trả lời khi token suy nghĩ chiếm dung lượng.
  - [`backend/app/modules/modelops/services/inference_service.py`](../../backend/app/modules/modelops/services/inference_service.py): Chuyển tiếp an toàn tham số `thinking_budget` qua kwargs cho adapter runtime.
  - [`backend/app/modules/rag/schemas.py`](../../backend/app/modules/rag/schemas.py): Bổ sung `thinking_budget` vào `AskRequest`, đồng thời nâng giới hạn `max_tokens` từ 4096 lên 32000.
  - [`backend/app/modules/rag/service.py`](../../backend/app/modules/rag/service.py): Chuyển tiếp `thinking_budget` từ `AskRequest` sang `LLMGenerateRequest`. Thêm chốt chặn bảo vệ `SemanticCache`: chỉ lưu cache khi `status == "answered"` và có trích dẫn hợp lệ, triệt tiêu hiện tượng cache lưu nhầm câu từ chối tạm thời.
- **Frontend UI & Settings**:
  - [`frontend/src/types/assistants.ts`](../../frontend/src/types/assistants.ts) & [`frontend/src/components/assistants/types.ts`](../../frontend/src/components/assistants/types.ts): Khai báo `thinking_budget?: number`.
  - [`frontend/src/components/assistants/sections/assistant-model-section.tsx`](../../frontend/src/components/assistants/sections/assistant-model-section.tsx): Bổ sung ô nhập số "Ngân sách suy nghĩ ngầm (Thinking Budget tokens)" kèm nhãn giải thích (0 = Tắt suy nghĩ để chat siêu tốc 1-2s; >0 = Bật Deep Reasoning).
  - [`frontend/src/pages/assistant-detail-page.tsx`](../../frontend/src/pages/assistant-detail-page.tsx) & [`frontend/src/pages/assistant-create-page.tsx`](../../frontend/src/pages/assistant-create-page.tsx): Đồng bộ form state, mutation update và gán giá trị mặc định `thinking_budget: 0`.

### 2.2. Xây Dựng Node DAG Chuẩn Hóa Câu Hỏi (`query.rewrite`)
- **Node Handler Hai Tầng**:
  - Tạo mới [`backend/app/modules/workflows/nodes/query_rewrite_node.py`](../../backend/app/modules/workflows/nodes/query_rewrite_node.py):
    * **Tầng 1 — Fast Rule Engine (0ms)**: Chuẩn hóa Unicode NFC sạch; bóc tách và sửa các lỗi trượt phím Telex ngữ cảnh phổ biến (`ngày` $\rightarrow$ `ngành`, `học bà` $\rightarrow$ `học bạ`, `điểm chuẫn` $\rightarrow$ `điểm chuẩn`, `kí túc sá` $\rightarrow$ `ký túc xá`, `sư pham` $\rightarrow$ `sư phạm`); mở rộng từ viết tắt (`cntt`, `qtkd`, `đgnl`, `thpt`, `ktx`, `nd 116`); viết hoa chuẩn 17 ngành học trọng điểm QNU.
    * **Tầng 2 — Fast Contextual LLM Rewrite (~150ms)**: Gọi LLM Flash với prompt Few-shot nghiêm ngặt, timeout 3.0s, tự động cascade an toàn về kết quả Tầng 1 nếu có lỗi mạng hoặc quá hạn.
    * Lưu trữ câu hỏi đã chuẩn hóa vào `context.node_data["normalized_query"]` và `context.node_data["user_message"]`.
- **Node Registry & Visual Catalog**:
  - Đăng ký node trong [`backend/app/modules/workflows/registry.py`](../../backend/app/modules/workflows/registry.py) và hỗ trợ aliases trong [`backend/app/modules/workflows/compiler.py`](../../backend/app/modules/workflows/compiler.py).
  - Tạo manifest JSON [`configs/nodes/query.rewrite.v1alpha1.json`](../../configs/nodes/query.rewrite.v1alpha1.json).
  - Cập nhật thư viện node [`frontend/src/components/admin/node-catalog-drawer.tsx`](../../frontend/src/components/admin/node-catalog-drawer.tsx).

### 2.3. Tích Hợp Vào Quy Trình DAG Trợ Lý Tuyển Sinh & Đồng Bộ DB
- Cập nhật [`configs/workflows/admissions-assistant.v1alpha1.json`](../../configs/workflows/admissions-assistant.v1alpha1.json):
  * Đặt node `query_rewrite` nằm giữa `condition_route` và `knowledge_answer`.
  * Cạnh nối (edges): `condition_route` $\rightarrow$ `query_rewrite` $\rightarrow$ `knowledge_answer`.
- Đồng bộ đồ thị mới vào CSDL PostgreSQL (`workflow_definitions`, `workflow_drafts`, `workflow_versions`).
- Sửa lỗi timestamp timezone tại `KnowledgeGapRecord` trong `app/modules/evaluation/service.py` (`replace(tzinfo=None)` để tương thích cột PostgreSQL `TIMESTAMP WITHOUT TIME ZONE`).
- Khắc phục cơ chế Semantic Cache & Citation Guard: Thêm kiểm tra `has_substantive_content` giúp bảo tồn trích dẫn và đánh dấu `status: answered` khi câu trả lời có chứa thông tin học phí kèm số hotline tư vấn.

---

## 3. Kết Quả Kiểm Thử Thực Tế (Verification)

### 3.1. Kiểm Thử Luồng Chat End-to-End Qua DAG
- **Câu hỏi người dùng (có lỗi gõ nhầm Telex)**:
  `"học phí ngày công nghệ thông tin là bao nhiêu"`
- **Hành trình DAG thực thi**:
  1. `chat_input`: Tiếp nhận thông điệp gốc.
  2. `condition_route`: Nhận diện câu hỏi tra cứu nghiệp vụ, điều hướng tới `query_rewrite`.
  3. `query_rewrite`: Nhận diện trượt phím `"ngày"` $\rightarrow$ `"ngành"`, viết hoa chuẩn hóa $\rightarrow$ `"học phí ngành Công nghệ thông tin là bao nhiêu"`.
  4. `knowledge_answer`: Hybrid RAG truy xuất chính xác 4 trích dẫn từ tài liệu PDF tuyển sinh `doc_f0c1` (Trang 10, 11, 12). Mô hình `gemini-flash-latest` sinh phản hồi có cấu trúc chuẩn:
     * Cử nhân đại trà: 83 - 97 triệu đồng (toàn khóa 4 năm).
     * Kỹ sư đại trà: 112,3 triệu đồng (toàn khóa 4,5 năm).
     * Chương trình tiếng Anh (CNTT): tính theo định mức kinh tế - kỹ thuật, dự kiến bằng 1,5 lần chương trình đại trà.
  5. `citation_guard`: Xác thực căn cứ đầy đủ (`is_grounded: True`, 4 citations) $\rightarrow$ điều hướng tới `chat_output`.
  6. `chat_output`: Phản hồi `status: "answered"` với đầy đủ 4 trích dẫn Trang 10, 11, 12.

### 3.2. Kiểm Thử Tự Động (Automated Regression Tests)
- **Backend Tests**:
  * `uv run ruff check .`: 0 lỗi.
  * `uv run --extra dev pytest tests/test_workflows.py tests/test_query_rewrite_node.py tests/test_modelops.py tests/test_rag.py`: **65/65 tests passed (100%)** trong 4.92s.
  * `uv run --extra dev pytest tests/test_assistants.py`: **12/12 tests passed (100%)** trong 3.00s.
- **Frontend Checks**:
  * `npm run lint`: Biome kiểm tra 168 files trong 169ms, **0 lỗi**.
  * `npm run typecheck`: `tsc --noEmit` đạt **0 lỗi**.
  * `npm run build`: Vite build thành công đóng gói bundle trong **8.34s** (2661 modules transformed).
- **Tài liệu quy trình**: Đồng bộ sơ đồ và mục 5.7 trong [`docs/quy_trinh/04_dieu_phoi_tro_ly_dag.md`](../quy_trinh/04_dieu_phoi_tro_ly_dag.md).
