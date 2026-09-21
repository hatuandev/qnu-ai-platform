# NHẬT KÝ LÀM VIỆC — PHIÊN #182
**Ngày**: 2026-09-21 | **Thời gian**: 22:15 (UTC+7)
**Tiêu đề**: Khắc Phục Lỗi Hội Thoại Đa Lượt (Multi-turn Resolution) & Triệt Tiêu Hoàn Toàn Rò Rỉ Mock Provider

---

## 1. Bối Cảnh & Vấn Đề Gặp Phải

Qua ảnh chụp màn hình cuộc trò chuyện thực tế của người dùng:
1. **Lượt 1**: Người dùng hỏi: *"bạn biết ngành công nghệ thông tin cần những môn học nào để xét tuyển không ?"* $\rightarrow$ Bot trả lời 5 tổ hợp môn và kết thúc bằng câu hỏi gợi ý: *"Bạn có muốn mình chia sẻ thêm thông tin về chỉ tiêu tuyển sinh hoặc các phương thức xét tuyển áp dụng cho ngành này không?"*.
2. **Lượt 2**: Người dùng phản hồi tự nhiên: *"có tôi muốn"*.
3. **Sự cố xảy ra**:
   - Bot mất **22,792 ms (~23 giây)** để phản hồi.
   - Nội dung in ra màn hình bị vỡ thành chuỗi debug rò rỉ:
     `[Local @cf/baai/bge-m3] Phản hồi từ máy chủ AI nội bộ ĐH Quy Nhơn: Đã ghi nhận yêu cầu: 'Câu hỏi của người dùng: có tôi muốn TÀI LIỆU TRÍCH XUẤT TỪ KHO TRI THỨC: --- Đoạn trích [1] --- Xét'.`

---

## 2. Phân Tích Kỹ Thuật (Root Cause Analysis)

1. **Nguyên nhân câu *"có tôi muốn"* bị ngắt cụt ngữ cảnh**:
   - Node `query.rewrite` (`query_rewrite_node.py`) trước đây chỉ nhận `message` đơn lẻ của lượt hiện tại, không sử dụng `conversation_history`.
   - Chuỗi `"có tôi muốn"` không có thực thể (Entity) nào, nên Hybrid RAG tìm kiếm không ra kết quả có ý nghĩa.
2. **Nguyên nhân rò rỉ chuỗi `[Local @cf/baai/bge-m3]`**:
   - Trong bảng `model_provider_configs`, bản ghi `system_model_defaults` mang `provider_type = "system_routing"` và `model_name = "@cf/baai/bge-m3"`.
   - `_get_active_providers()` trong `inference_service.py` lấy toàn bộ các bản ghi `is_active=True`, kéo nhầm các provider phi-chat (`system_routing`, `sentence_transformers`, `docling`) vào danh sách sinh văn bản LLM.
   - `get_llm_adapter` trong `providers/__init__.py` trước đây có nhánh fallback ngầm cuối cùng: bất kỳ provider type nào không khớp đều trả về `LocalVLLMAdapter(model_name=model_name)`.
   - Khi Gemini/Google API gặp lỗi timeout (ReadTimeout), cascade nhảy sang adapter này; kết nối `http://localhost:8000` thất bại và khối `except Exception` trong `local_vllm_adapter.py` nuốt trôi exception, trả về chuỗi mock debug `[Local @cf/baai/bge-m3]...` thay vì ném lỗi để kích hoạt tầng Factual Grounded Fallback của RAG!

---

## 3. Các Giải Pháp Đã Thực Hiện

### 3.1. Khôi Phục Ngữ Cảnh Đa Lượt (`query_rewrite_node.py`)
- Xây dựng hàm `resolve_multiturn_query(raw_query, history)` chạy ở tầng **Stage 0 (0ms)**:
  * Nhận diện các câu ngắn khẳng định / phản hồi (`"có"`, `"ừ"`, `"vâng"`, `"tôi muốn"`, `"có tôi muốn"`, `"tiếp đi"`, `"chi tiết đi"`...).
  * Quét tin nhắn trước đó của Assistant để bóc tách chủ đề gợi ý (ví dụ: *"chỉ tiêu tuyển sinh và các phương thức xét tuyển"*).
  * Quét tin nhắn của User để trích xuất thực thể chính (ví dụ: *"ngành Công nghệ thông tin"*).
  * Tái cấu trúc tức thì thành câu hỏi tra cứu độc lập đầy đủ:
    > **"Chỉ tiêu tuyển sinh và các phương thức xét tuyển ngành Công nghệ thông tin"**
  * Hỗ trợ thay thế đại từ chỉ định: `"học phí của ngành này"` $\rightarrow$ `"học phí của ngành Công nghệ thông tin"`.
- Bổ sung ngữ cảnh `history` vào `build_rewrite_prompt` để khi cần LLM Rewrite, mô hình hiểu trọn vẹn ngữ cảnh hội thoại đa lượt.

### 3.2. Lọc Sạch Nhà Cung Cấp ModelOps & Chống Rò Rỉ Mock
- [`inference_service.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/modelops/services/inference_service.py):
  * Định nghĩa `VALID_CHAT_PROVIDER_TYPES` chỉ chấp nhận các LLM chat thực thụ (`gemini`, `openai`, `cloudflare`, `deepseek`, `groq`, `claude`, `mistral`, `local_vllm`, `ollama`...).
  * Lọc bỏ hoàn toàn các cấu hình phi-LLM: `system_routing`, `sentence_transformers`, `docling`.
  * Bộ lọc `NON_CHAT_MODEL_KEYWORDS`: Cấm tuyệt đối không đưa mô hình chứa `bge-`, `embed`, `rerank`, `tableformer` vào luồng chat generation.
- [`providers/__init__.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/modelops/providers/__init__.py):
  * Thay thế dòng fallback ngầm bằng lệnh ném `ValueError(f"Unsupported LLM provider type: '{provider_type}'")`.
- [`local_vllm_adapter.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/modelops/providers/local_vllm_adapter.py):
  * Triệt tiêu hoàn toàn khối code sinh chuỗi mock debug `[Local...] Đã ghi nhận yêu cầu`.
  * Khi mất kết nối hoặc timeout, adapter ném `AppException(status_code=502, code="local_llm_unavailable")` chuẩn mực để `inference_service` kích hoạt fallback hoặc `rag_service` chuyển sang tổng hợp câu trả lời dựa trên trích dẫn tài liệu (Factual Grounded Fallback).

---

## 4. Kết Quả Kiểm Thử (Verification)

1. **Kiểm thử tự động mới (`test_multiturn_and_provider_safety.py`)**:
   - `test_resolve_multiturn_affirmative_short_response`: PASSED (100%).
   - `test_resolve_multiturn_pronoun_reference`: PASSED (100%).
   - `test_query_rewrite_node_handler_resolves_multiturn_in_workflow`: PASSED (100%).
   - `test_provider_safety_valid_chat_types`: PASSED (100%).
   - `test_get_llm_adapter_rejects_unsupported_provider`: PASSED (100%).
   - `test_local_vllm_adapter_fails_loudly_when_offline`: PASSED (100%).
2. **Kiểm thử mô phỏng thực tế đa lượt (Live E2E Multi-turn Chat)**:
   - Lượt 1: Hỏi môn xét tuyển CNTT $\rightarrow$ Trả lời 5 tổ hợp môn chính xác.
   - Lượt 2: Người dùng gõ *"có tôi muốn"* $\rightarrow$ Hệ thống tự động chuyển đổi thành tra cứu chỉ tiêu & phương thức ngành CNTT, trả về bảng chỉ tiêu điểm trúng tuyển chính thức 2024-2025 với 6 trích dẫn minh chứng, **0% rò rỉ mock, 0% lỗi kỹ thuật**!
3. **Toàn bộ Test Suite Hệ Thống**:
   - Backend: `uv run ruff check .` $\rightarrow$ **0 lỗi**.
   - Pytest: `67/67 passed (100%)`.
   - Frontend: `npm run lint` $\rightarrow$ **168 files checked, 0 lỗi**.
   - TypeScript: `npm run typecheck` $\rightarrow$ **0 lỗi**.
   - Vite Build: `npm run build` $\rightarrow$ **Thành công (13.70s)**.
