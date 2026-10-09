# Nhật Ký Phiên #298 — Thay Thế Nhà Cung Cấp Ollama Bằng vLLM On-Premise (BGE-M3, BGE-Reranker-v2-M3, Qwen3-Embedding-4B)

- **Thời gian**: 2026-10-08
- **Tác vụ**: Xóa bỏ nhà cung cấp `QNU AI Server (RTX 5090 - Ollama)` và các seed data liên quan; Cấu hình và seed mới nhà cung cấp `QNU AI Server (RTX 5090 - vLLM)` với 3 mô hình cục bộ: `bge-m3` (pooling/embeddings), `bge-reranker-v2-m3` (rerank/score), và `qwen3-embedding-4b` (pooling/embeddings 2560D).
- **Môi trường**: Backend FastAPI, Python 3.12, vLLM Tailscale On-Premise (`http://tormemrtxproto.tail0924dd.ts.net:8000/v1`).

---

## 1. Bối Cảnh & Yêu Cầu Người Dùng

1. **Yêu cầu xóa**: Xóa hoàn toàn nhà cung cấp `QNU AI Server (RTX 5090 - Ollama)` (`prov_rtx5090_ollama`, URL `http://tormemrtxproto.tail0924dd.ts.net:11434`) và mọi seed data/defaults liên quan trong CSDL và mã nguồn.
2. **Yêu cầu cấu hình vLLM mới**:
   - URL: `http://tormemrtxproto.tail0924dd.ts.net:8000/v1` (Port 8000 chuẩn của vLLM trên mạng Tailscale).
   - Tên mô hình chuẩn:
     * `bge-m3`: vLLM pooling / embeddings (1,024 dims).
     * `bge-reranker-v2-m3`: vLLM rerank / score Cross-Encoder.
     * `qwen3-embedding-4b`: vLLM pooling / embeddings (2,560 dims).

---

## 2. Chi Tiết Các Tệp Thay Đổi

1. **[`backend/app/core/config.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/core/config.py)**:
   - Thêm cấu hình `VLLM_BASE_URL: str = Field(default="http://tormemrtxproto.tail0924dd.ts.net:8000/v1", validation_alias=AliasChoices("VLLM_BASE_URL", "VLLM_URL"))`.
2. **[`backend/app/modules/modelops/services/provider_service.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/modelops/services/provider_service.py)**:
   - Thay thế `prov_rtx5090_ollama` trong `STANDARD_QNU_PROVIDERS` bằng `prov_rtx5090_vllm` (`QNU AI Server (RTX 5090 - vLLM)`).
   - Khai báo chi tiết 3 mô hình trong `model_specs`: `bge-m3` (embedding), `bge-reranker-v2-m3` (reranker), `qwen3-embedding-4b` (embedding).
   - Bổ sung cơ chế tự động dọn dẹp nhà cung cấp Ollama cũ nếu còn tồn tại trong CSDL: `if "prov_rtx5090_ollama" in existing: await db.delete(...)`.
   - Cập nhật URL kết nối vLLM fallback từ port 8002 sang port 8000.
3. **[`backend/app/modules/modelops/services/model_catalog_service.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/modelops/services/model_catalog_service.py)**:
   - Cập nhật `DEFAULT_QNU_OCR_COMBO_CHAIN`: Chuyển quyền ưu tiên 1 sang Google Gemini Cloud (`gemini-3.1-flash-lite`), loại bỏ Ollama.
   - Cập nhật `DEFAULT_QNU_EMBEDDING_COMBO_CHAIN`: Ưu tiên 1 là `prov_rtx5090_vllm` (`bge-m3`), kế tiếp là Cloudflare và Google Gemini.
   - Cập nhật `DEFAULT_QNU_RERANKER_COMBO_CHAIN`: Ưu tiên 1 là `prov_rtx5090_vllm` (`bge-reranker-v2-m3`), kế tiếp là Cloudflare.
   - Cập nhật `default_data`: `default_embedding_provider_id="prov_rtx5090_vllm"`, `default_reranker_provider_id="prov_rtx5090_vllm"`.
4. **[`backend/app/modules/modelops/schemas.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/modelops/schemas.py)**:
   - Cập nhật `SystemModelDefaults`: `default_embedding_provider_id = "prov_rtx5090_vllm"`, `default_reranker_provider_id = "prov_rtx5090_vllm"`.
5. **[`backend/app/modules/knowledge/schemas.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/knowledge/schemas.py)** & **[`collection_service.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/knowledge/services/collection_service.py)**:
   - Cập nhật fallback `CollectionDataProcessingConfig`: `embedding_provider_id="prov_rtx5090_vllm"`, `embedding_model="bge-m3"`, `primary_ocr_provider_id="prov_gemini"`.
6. **[`backend/app/modules/assistants/seeder.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/assistants/seeder.py)**:
   - Cập nhật `reranker_policy` mặc định sang `prov_rtx5090_vllm` và `bge-reranker-v2-m3`.
   - Cập nhật trợ lý `ast_drafting` và `ast_question_bank` sang `prov_gemini` (`gemini-2.5-flash`), loại bỏ `prov_rtx5090_ollama`.
7. **[`backend/app/modules/rag/reranker.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/rag/reranker.py)**:
   - Cập nhật fallback endpoint URL sang `getattr(settings, "VLLM_BASE_URL", "") or "http://tormemrtxproto.tail0924dd.ts.net:8000/v1"`.
8. **[`backend/scripts/sync_data_processing_and_reranker.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/scripts/sync_data_processing_and_reranker.py)** & **[`inspect_and_sync_db.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/scripts/inspect_and_sync_db.py)**:
   - Cập nhật logic đồng bộ hóa sang `prov_rtx5090_vllm`.
9. **[`backend/tests/test_vllm_reranker.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/tests/test_vllm_reranker.py)**:
   - Bổ sung test case `test_vllm_seed_provider_config` kiểm định cấu hình 3 model của vLLM và xác nhận `prov_rtx5090_ollama` đã bị loại bỏ hoàn toàn.

---

## 3. Kết Quả Kiểm Thử

- **Pytest**: `tests/test_vllm_reranker.py` $\rightarrow$ **4/4 PASSED (100%)**:
  * `test_reranker_vllm_native_scoring`: PASSED
  * `test_vllm_llm_adapter_factory`: PASSED
  * `test_vllm_embedding_generation`: PASSED
  * `test_vllm_seed_provider_config`: PASSED
- **Ruff Linter**: All checks passed! 0 lỗi, 0 cảnh báo.
