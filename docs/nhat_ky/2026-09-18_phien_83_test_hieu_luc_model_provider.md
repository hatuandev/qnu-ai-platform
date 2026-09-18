# NHẬT KÝ LÀM VIỆC — PHIÊN #83
# Ngày: 2026-09-18 | Phiên Làm Việc: Tính Năng Kiểm Thử Hiệu Lực Các Model Trong Provider (Model Health Probing & 1-Click Dead Models Cleanup)

---

## 1. Mục Tiêu & Bối Cảnh Nghiệp Vụ
- **Yêu cầu người dùng**: Tại trang quản lý Provider (`/models/:id`), bổ sung tính năng kiểm thử xem các model hiện tại đã cấu hình còn hiệu lực cung cấp từ phía nhà cung cấp (Google Gemini, OpenAI, Mistral, Cloudflare, Local vLLM/Ollama,...) hay không.
- **Mục tiêu kỹ thuật**:
  1. Xây dựng Backend endpoint kiểm thử model theo từng provider (`POST /platform/v1alpha1/modelops/providers/{provider_id}/models/test`), hỗ trợ cả kiểm tra toàn diện hàng loạt (batch) và kiểm tra đơn lẻ (single model).
  2. Triển khai cơ chế Lightweight Real Ping thích ứng cho từng dòng Provider (Gemini 1-token prompt, Cloudflare Workers AI embedding/prompt, Mistral OCR model check & completions, OpenAI chat/completions/embeddings, Docling/SentenceTransformers local check).
  3. Bổ sung giao diện thẻ "Mô Hình Khả Dụng" trên Frontend:
     - Nút `[⚡ Test Tất Cả Models]` trên Header với icon loading trạng thái.
     - Hiển thị chấm trạng thái và huy hiệu cho từng model tag: 🟢 Khả dụng (kèm độ trễ latency ms), 🔴 Không khả dụng (404/ngừng hỗ trợ), 🟡 Cooldown Rate Limit 429.
     - Nút `[▶]` kiểm tra nhanh từng model độc lập.
     - Banner cảnh báo thông minh khi có model hỏng kèm nút `[🧹 Dọn Dẹp Model Lỗi]` 1-click tự động gỡ bỏ các model không còn hỗ trợ khỏi cấu hình Provider.
  4. Đạt chuẩn 100% không lỗi Biome, TypeScript typecheck, Vite build, pytest và Zero Mojibake.

---

## 2. Chi Tiết Các Thay Đổi Kỹ Thuật

### 2.1. Backend Module ModelOps
- **[`backend/app/modules/modelops/schemas.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/modelops/schemas.py)**:
  - Bổ sung `SingleModelTestResult` (model_name, success, status, latency_ms, message, tested_at).
  - Bổ sung `ProviderModelsTestRequest` (model_name tùy chọn).
  - Bổ sung `ProviderModelsTestResponse` (provider_id, total_models, available_models, unavailable_models, results).
- **[`backend/app/modules/modelops/service.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/modelops/service.py)**:
  - Bổ sung hàm private `_ping_single_model` thực hiện ping thực tế có giới hạn thời gian (5s timeout), phân nhánh tối ưu theo từng nhà cung cấp (Google Gemini `generateContent`, Cloudflare Workers AI `run`, Mistral OCR `GET /v1/models/{model}` hoặc chat completions, OpenAI `chat/completions` hoặc `embeddings`).
  - Bổ sung hàm `test_provider_models` hỗ trợ chạy song song an toàn qua `asyncio.Semaphore(5)` để kiểm thử đồng thời tối đa 5 model mà không gây nghẽn kết nối hoặc bị Rate Limit.
- **[`backend/app/modules/modelops/router.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/modelops/router.py)**:
  - Bổ sung endpoint `POST /platform/v1alpha1/modelops/providers/{provider_id}/models/test`.
- **[`backend/tests/test_modelops.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/tests/test_modelops.py)**:
  - Bổ sung 2 test case: `test_provider_models_test_all_success` và `test_provider_models_test_single_model_and_invalid`.
  - Kết quả kiểm thử: 15/15 tests PASS (100%).

### 2.2. Frontend Service & UI
- **[`frontend/src/services/api-client.ts`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/services/api-client.ts)**:
  - Export interface `SingleModelTestResult`, `ProviderModelsTestResponse`.
  - Bổ sung phương thức `apiClient.testProviderModels(providerId, modelName?)`.
- **[`frontend/src/pages/modelops-page.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/pages/modelops-page.tsx)**:
  - Thêm state `isTestingAllModels`, `testingModelName`, `modelTestResults`, `modelTestSummary`.
  - Thêm các handlers `handleTestAllModels`, `handleTestSingleModel`, `handleCleanUnavailableModels`.
  - Nâng cấp Card "Mô Hình Khả Dụng":
    - Header: Nút `[⚡ Test Tất Cả Models]`.
    - Từng model tag: hiển thị trạng thái kết quả test (xanh lá kèm latency ms, đỏ khi không khả dụng, vàng khi rate limit) và nút `[▶]` để test đơn lẻ.
    - Banner cảnh báo model chết và nút `[🧹 Dọn Dẹp Model Lỗi]` 1-click.
- **[`docs/quy_trinh/06_modelops_circuit_breaker.md`](file:///d:/DuAnPhanMem/qnu-ai-platform/docs/quy_trinh/06_modelops_circuit_breaker.md)**:
  - Bổ sung Mục 4: Quy trình Kiểm Thử Hiệu Lực Mô Hình LLM Đa Nhà Cung Cấp (Active Model Health Probing & 1-Click Cleanup).

---

## 3. Kết Quả Kiểm Thử Toàn Diện (Verification)
1. **Frontend Linter (Biome)**:
   - `npm run lint` -> Kiểm tra 93 tệp: **0 lỗi** (Passed).
2. **Frontend Typecheck (TypeScript)**:
   - `npm run typecheck` (`tsc --noEmit`) -> **0 lỗi** (Passed).
3. **Frontend Production Bundle Build**:
   - `npm run build` (`tsc -b && vite build`) -> **Thành công** trong 8.94s.
4. **Backend Linter (Ruff)**:
   - `ruff check .` -> **0 lỗi** (All checks passed).
5. **Backend Unit & Integration Tests (Pytest)**:
   - `pytest tests/test_modelops.py` -> **15/15 passed** (100%).
6. **Zero Mojibake Audit**:
   - `python scripts/check_mojibake.py` -> Quét 231 tệp: **0 phát hiện rác ký tự / vỡ font** (Passed).
