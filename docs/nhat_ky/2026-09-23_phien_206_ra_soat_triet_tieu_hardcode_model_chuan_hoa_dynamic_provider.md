# NHẬT KÝ LÀM VIỆC — PHIÊN #206
**Ngày:** 2026-09-23 | **Thời gian:** 15:10 - 15:40 (UTC+7)  
**Tiêu đề:** Rà Soát Triệt Tiêu Toàn Diện Hardcoded Models, Tôn Trọng Cấu Hình Nhà Cung Cấp Động 100% & Bổ Sung Chuẩn AGENTS.md

---

## 1. Mục Tiêu Phiên Làm Việc
- Phản hồi trực tiếp yêu cầu của người dùng: Rà soát toàn bộ codebase tìm và xóa bỏ triệt để mọi hành vi gán cứng (hardcode) tên mô hình (model name). Người dùng nhấn mạnh: "tôi không mấy làm chức năng nhà cung cấp mà phải hardcode model, bạn cũng bổ sung ý này vào agent luôn nhé".
- Khắc phục tận gốc nguyên nhân vì sao người dùng cấu hình model mới (như `gemini-3.5-flash`, `mistral-ocr-2503`) nhưng khi thực thi hệ thống lại tự ý fallback về model cũ (`gemini-2.5-flash`, `gpt-4o-mini`).
- Bổ sung quy định bắt buộc **Zero Hardcoded Models Policy** vào tài liệu quản trị AI Agent (`AGENTS.md`).

---

## 2. Các Phát Hiện Kỹ Thuật (Key Findings & Root Causes)
1. **Lỗi nuốt model trong `inference_service.py`**:
   - Khi người dùng gửi yêu cầu với `preferred_model_name = "gemini-3.5-flash"` (hoặc model mới), code trước đây kiểm tra: `if req.preferred_model_name in p_models ...`.
   - Nếu danh sách `p_models` trong DB là danh sách seed cũ và chưa kịp cập nhật model 3.5, điều kiện trả về `False`.
   - Hệ thống tự động bỏ qua `preferred_model_name` của người dùng và rơi xuống nhánh `else: chosen_model = p["model_name"]` (tức là `gemini-2.5-flash`).
2. **Thiếu truyền tham số model trong Workflow `llm_generate_node.py`**:
   - Node LLM sinh nội dung chỉ trích xuất prompt và temperature từ `AssistantRuntimeProfile` nhưng quên truyền `preferred_model_name`, `fallback_model_name`, `preferred_provider_id` vào `LLMGenerateRequest`.
   - Dẫn đến việc khi chạy trợ lý qua DAG Workflow, request luôn có `preferred_model_name = None`, khiến hệ thống chỉ chạy model mặc định của provider.
3. **Hardcode trong `MistralOCRAdapter`**:
   - Adapter Mistral không nhận tham số `model_name` và gán cứng `"model": "mistral-ocr-latest"` trong payload API.
4. **Hardcode ngụy tạo che giấu lỗi trong `readiness.py`**:
   - Dòng `primary = getattr(policy, "primary_model", None) or "gpt-4o-mini"` tự điền giá trị ngầm, làm vô hiệu hóa kiểm tra `if not primary:`.
5. **Hardcode chuỗi cố định trong `assistant_chat_service.py`**:
   - `_extract_primary_model` lặp lại chuỗi cứng `"gpt-4o-mini"` ở 6 vị trí thay vì đọc từ cấu hình hệ thống `settings.DEFAULT_LLM_MODEL`.
6. **Hardcode model trong Cloudflare embedding/reranker**:
   - `vector_indexer.py` và `reranker.py` tự động cưỡng ép về model mặc định nếu chuỗi không chứa `@cf/`.

---

## 3. Các Thay Đổi Kỹ Thuật Chi Tiết (Key Code Changes)

| Tệp | Hành Động | Mô Tả Kỹ Thuật |
| :--- | :--- | :--- |
| `backend/app/modules/modelops/services/inference_service.py` | Cập nhật | Bổ sung hàm `_is_model_compatible_with_provider` nhận diện độ tương thích họ model động (Gemini/Gemma, GPT/o1/o3, Claude, Mistral, Qwen/DeepSeek/Llama). Nâng cấp `_match_score` và phân giải `chosen_model` động trong cả `generate()` và `stream_generate()`: nếu người dùng chỉ định provider hoặc model tương thích, hệ thống ưu tiên 100% `req.preferred_model_name`, không bao giờ đè về model cũ. |
| `backend/app/modules/workflows/nodes/llm_generate_node.py` | Cập nhật | Trích xuất `preferred_model_name`, `fallback_model_name`, `preferred_provider_id` từ `config` hoặc `profile.model_policy` và truyền vào `LLMGenerateRequest`. |
| `backend/app/modules/ocr/adapters/mistral_adapter.py` | Cập nhật | Thêm tham số `model_name: str \| None = None` vào `__init__`, lưu `self._model_name`, thêm property `model_name` và truyền `self._model_name` vào payload gọi API. |
| `backend/app/modules/ocr/service.py` | Cập nhật | Trong `_resolve_adapter`: hỗ trợ khởi tạo `MistralOCRAdapter(model_name=name_or_model)` động. Trong `_extract_auto`: hỗ trợ dynamic `default_ocr_model` cho cả Gemini và Mistral, tự động đưa model được cấu hình lên đầu danh sách candidates. |
| `backend/app/modules/assistants/readiness.py` | Cập nhật | Bỏ gán cứng `or "gpt-4o-mini"` và `or "gemini-2.5-flash-lite"`. Kiểm tra trung thực cấu hình của người dùng và trả về cảnh báo/lỗi chính xác khi thiếu cấu hình. |
| `backend/app/modules/assistants/services/assistant_chat_service.py` | Cập nhật | Thay thế chuỗi hardcode `"gpt-4o-mini"` bằng `settings.DEFAULT_LLM_MODEL`. |
| `backend/app/modules/rag/vector_indexer.py` | Cập nhật | Chuẩn hóa tiền tố Cloudflare embedding động từ `settings.EMBEDDING_MODEL`, không cưỡng ép về model cứng. |
| `backend/app/modules/rag/reranker.py` | Cập nhật | Chuẩn hóa tiền tố Cloudflare reranker động từ `settings.RERANKER_MODEL`, không cưỡng ép về model cứng. |
| `backend/tests/test_modelops.py` | Cập nhật | Bổ sung 2 test cases mới: `test_dynamic_model_resolution_respects_custom_and_future_models` (kiểm tra gọi `gemini-3.5-flash` được giữ nguyên vẹn) và `test_llm_generate_node_forwards_assistant_profile_models` (kiểm tra Workflow node truyền đúng model từ profile). |
| `AGENTS.md` | Cập nhật | Bổ sung **Zero Hardcoded Models Policy**: Mục 1.6 (Tôn chỉ kỹ thuật), Mục 3.5 (Backend core rules), Mục 8.11 (Quy chuẩn Clean Code Vibe Coding). |

---

## 4. Kết Quả Kiểm Thử (Verification)
1. **Backend Linter & Test Suite**:
   - `backend\.venv\Scripts\ruff.exe check backend/`: **0 lỗi** (All checks passed).
   - `pytest test_modelops.py test_ocr.py -v`: **40/40 passed (100%)** trong 10.99s.
   - `pytest test_assistants.py -v`: **12/12 passed (100%)** trong 1.68s.
2. **Frontend Linter & Build Suite**:
   - `npm run lint`: **171 files checked, 0 lỗi**.
   - `npm run typecheck`: **0 lỗi** (tsc --noEmit clean).
   - `npm run build`: **Vite build thành công (5.17s)**.
