# Nhật Ký Phiên Làm Việc #284: Chuyển Đổi Hạ Tầng AI Server Sang vLLM & Tích Hợp Native vLLM Reranker

- **Ngày thực hiện**: 2026-10-07
- **Người thực hiện**: Senior Full-Stack Architect & Enterprise AI Systems Specialist (AI Pair Programmer)
- **Mục tiêu**:
  1. Hỗ trợ chuyển đổi hạ tầng mô hình trên AI Server GPU RTX 5090 từ **Ollama** sang **vLLM** theo yêu cầu người dùng.
  2. Bổ sung hỗ trợ giao thức chuẩn **Native vLLM / TEI `/v1/rerank`** trong hệ thống Reranker của QNU AI Platform.
  3. Mở rộng ModelOps (`get_llm_adapter`, `provider_service`, `vector_indexer`) hỗ trợ loại nhà cung cấp `vllm`.
  4. Cập nhật Frontend UI (`ProviderModal`, `modelops-helpers`, `types/modelops`) hỗ trợ quản lý nhà cung cấp vLLM.

---

## 1. Bối Cảnh & Phân Tích Kỹ Thuật

Người dùng thông báo đã thay đổi cách tiếp cận các mô hình trên AI Server GPU RTX 5090 (`tormemrtxproto`) từ Ollama sang vLLM, và chia sẻ kết quả kiểm tra thực tế:
```bash
tormem@tormemrtxproto:~$ curl -s http://127.0.0.1:8002/v1/rerank \
  -H "Content-Type: application/json" \
  -d '{
    "model": "bge-reranker-v2-m3",
    "query": "Trường Đại học Quy Nhơn nằm ở đâu?",
    "documents": [
      "Hà Nội là thủ đô của Việt Nam.",
      "Trường Đại học Quy Nhơn tọa lạc tại thành phố Quy Nhơn.",
      "BGE-M3 là mô hình embedding đa ngôn ngữ.",
      "Sinh viên có thể đăng ký học phần trực tuyến."
    ],
    "top_n": 4
  }'
```
Kết quả trả về độ tương quan (relevance score) đạt `0.999855` cho tài liệu Đại học Quy Nhơn.

### Phân tích sự khác biệt kiến trúc giữa Ollama và vLLM:
1. **Ollama**:
   - Tất cả các mô hình (Chat, Vision, Embedding) được phục vụ chung qua 1 tiến trình và 1 cổng duy nhất (`11434`), gọi theo tham số `model`.
   - Không hỗ trợ endpoint chuẩn `/v1/rerank` cho Cross-Encoder reranker.
2. **vLLM / TEI**:
   - Tối ưu hóa sâu VRAM bằng PagedAttention và Continuous Batching trên kiến trúc NVIDIA GPU RTX 5090 Blackwell.
   - Thường triển khai độc lập theo từng tiến trình / cổng:
     - **Cổng 8002**: Reranker (`BAAI/bge-reranker-v2-m3`), phục vụ endpoint chuẩn `/v1/rerank`.
     - **Cổng 8000 / 8001**: LLM Chat / Instruct & Embedding (OpenAI-compatible endpoints `/v1/chat/completions`, `/v1/embeddings`).

---

## 2. Các Thay Đổi Kiến Trúc Đã Triển Khai

### A. Backend RAG Reranker (`backend/app/modules/rag/reranker.py`)
- Xây dựng hàm `_rerank_vllm_or_generic(query, candidates, runtime, top_k)`:
  - Tự động phân giải URL tới `/v1/rerank` hoặc `/rerank`.
  - Gửi payload chuẩn TEI/vLLM: `{"model": ..., "query": ..., "documents": [...], "top_n": ...}`.
  - Phân tích kết quả `results: [{"index": int, "relevance_score": float}]` và kết hợp với thang điểm Reciprocal Rank Fusion (RRF).
  - Tự động tương thích với cả phương thức đồng bộ lẫn bất đồng bộ của `resp.json()`.
- Đấu nối nhánh phân giải runtime trong `rerank()`:
  - Tự động kích hoạt khi `runtime.provider_type in ("vllm", "tei", "custom", "ollama", "openai")` hoặc khi có `api_base_url`.
  - Fallback mềm (Graceful Degradation) sang RRF thuần túy nếu server vLLM bận hoặc lỗi mạng.

### B. Backend ModelOps Factory & Provider Service
- **`backend/app/modules/modelops/providers/__init__.py`**:
  - Bổ sung `"vllm"`, `"tei"` vào danh sách tương thích OpenAI trong `get_llm_adapter`.
- **`backend/app/modules/modelops/services/provider_service.py`**:
  - Bổ sung `vllm` vào `test_connection` kiểm tra endpoint `GET /v1/models`.
  - Bổ sung xử lý `probe_model` thông minh: kiểm tra `"rerank" in m_lower` sẽ tự động probe tới `/v1/rerank` với query mẫu và nhận diện độ trễ chính xác thay vì gửi sang `/chat/completions`.
- **`backend/app/modules/modelops/services/model_catalog_service.py`**:
  - Gỡ bỏ `vllm` khỏi danh sách `REMOVED_LOCAL_PROVIDER_TYPES`.
- **`backend/app/modules/rag/vector_indexer.py`**:
  - Cho phép `provider in ("ollama", "ollama_local", "local", "vllm", "custom", "openai", "tei")`.
  - Tối ưu hóa: khi provider là `vllm`, bỏ qua việc gọi thử endpoint native Ollama `/api/embed`, đi thẳng tới `/v1/embeddings` với format OpenAI chuẩn.
  - Tự động tương thích với cả phương thức đồng bộ lẫn bất đồng bộ của `resp.json()`.

### C. Frontend ModelOps UI
- **`frontend/src/types/modelops.ts`**:
  - Bổ sung `"vllm" | "ollama"` vào union `ModelProvider.type`.
- **`frontend/src/components/modelops/provider-modal.tsx`**:
  - Bổ sung lựa chọn `vLLM / TEI (On-Premise GPU & High-Throughput)` trong dropdown chọn loại provider khi thêm hoặc sửa cấu hình.
- **`frontend/src/components/modelops/modelops-helpers.ts`**:
  - Bổ sung danh sách gợi ý mô hình (`PRESET_SUGGESTED_MODELS.vllm`) bao gồm `bge-reranker-v2-m3`, `bge-m3`, `BAAI/bge-m3`, `Qwen/Qwen2.5-7B-Instruct`, v.v.

---

## 3. Kiểm Thử & Đảm Bảo Chất Lượng (QA)

1. **Backend Unit Testing**:
   - Bộ kiểm thử mới [`tests/test_vllm_reranker.py`](backend/tests/test_vllm_reranker.py) đạt **3/3 PASSED**:
     - `test_reranker_vllm_native_scoring`: Kiểm tra bóc tách điểm vLLM và sắp xếp kết quả (PASSED).
     - `test_vllm_llm_adapter_factory`: Kiểm tra khởi tạo Adapter vLLM qua OpenAIAdapter (PASSED).
     - `test_vllm_embedding_generation`: Kiểm tra nạp embedding vector 1024D qua `/v1/embeddings` (PASSED).
   - Kiểm tra hồi quy [`tests/test_document_repository.py`](backend/tests/test_document_repository.py): 5/5 PASSED.
2. **Ruff Linter**:
   - `uv run ruff check app tests/test_vllm_reranker.py`: 0 lỗi (All checks passed!).

---

## 4. Hướng Dẫn Cấu Hình Mô Hình & Provider Cho Người Dùng

### A. Cấu Hình Provider Reranker (Cổng 8002)
1. Vào trang **Quản Lý Mô Hình (ModelOps)** (`/models`) -> bấm nút **Thêm Provider**.
2. **Tên hiển thị**: `QNU AI Server (RTX 5090 - vLLM Reranker)`
3. **Loại Provider**: Chọn `vLLM / TEI (On-Premise GPU & High-Throughput)`
4. **Base URL**: `http://tormemrtxproto.tail0924dd.ts.net:8002/v1` (hoặc `http://100.105.13.53:8002/v1`).
5. **Mô hình**: Thêm `bge-reranker-v2-m3`.
6. Bấm **Lưu** và bấm nút **Thử nghiệm (Probe)** bên cạnh model để kiểm tra độ trễ.
7. Vào tab **Cấu Hình Mặc Định Hệ Thống** -> mục **Reranker** -> chọn Provider này và model `bge-reranker-v2-m3`.

### B. Cấu Hình Provider Embedding (Cổng 8001)
1. Bấm nút **Thêm Provider**:
   - **Tên hiển thị**: `QNU AI Server (RTX 5090 - vLLM Embedding)`
   - **Loại Provider**: Chọn `vLLM / TEI (On-Premise GPU & High-Throughput)`
   - **Base URL**: `http://tormemrtxproto.tail0924dd.ts.net:8001/v1` (hoặc `http://100.105.13.53:8001/v1`).
   - **Mô hình**: Thêm `bge-m3`.
2. Bấm **Lưu** và bấm nút **Thử nghiệm (Probe)** bên cạnh model `bge-m3`.
3. Vào tab **Cấu Hình Mặc Định Hệ Thống** -> mục **Embedding** -> chọn Provider này và model `bge-m3`.
4. Vào từng **Kho Tri Thức** (`/knowledge/:id`) -> tab **Mô hình & Cấu hình** -> chọn Provider RTX 5090 vLLM Embedding và model `bge-m3`.

### C. Cấu Hình Provider LLM Chat (Cổng 8000 khi sẵn sàng)
- Khi bạn khởi chạy instance vLLM Chat (ví dụ port `8000` với model `Qwen/Qwen2.5-7B-Instruct` hoặc `deepseek-ai/DeepSeek-R1-Distill-Qwen-32B`):
  1. Thêm 1 provider với Base URL `http://tormemrtxproto.tail0924dd.ts.net:8000/v1`.
  2. Gán làm Primary Model cho các Trợ lý AI tại `/assistants`.
