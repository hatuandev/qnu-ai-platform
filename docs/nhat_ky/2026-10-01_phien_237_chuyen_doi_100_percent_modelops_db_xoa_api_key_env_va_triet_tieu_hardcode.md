# NHẬT KÝ LÀM VIỆC — PHIÊN #237
**Thời gian**: 2026-10-01 08:45 (UTC+7)  
**Vai trò**: AI Senior Full-Stack Architect & Enterprise AI Systems Specialist  
**Chủ đề**: Chuyển Đổi 100% Sang ModelOps DB, Xóa Bỏ Hoàn Toàn API Key Trong .env, Triệt Tiêu Hardcode Adapter Mocks & Tra Cứu Fact Layer Hình Thái Học

---

## 1. Bối Cảnh & Yêu Cầu Của Người Dùng

Sau khi người dùng thử nghiệm chatbot Tuyển sinh trên Web UI (`/assistants`), xuất hiện 4 vấn đề kỹ thuật nghiêm trọng:
1. **Chatbot luôn trả về thông báo từ chối cứng hoặc bảng số liệu không liên quan**: Khi người dùng hỏi *"Năm 2026 tuyển sinh những phương thức nào..."*, trợ lý luôn trả về: `"Dựa trên tài liệu chính thức của Trường Đại học Quy Nhơn: Về câu hỏi '...', vui lòng tham khảo các quy định hiện hành hoặc liên hệ Hotline 0256.3846.156."`. Khi hỏi *"Nếu em đạt giải Ba học sinh giỏi quốc gia thì được cộng bao nhiêu điểm ưu tiên?"*, trợ lý lại trả về bảng chỉ tiêu của ngành *"Toán giải tích (9460102)"*.
2. **Không gọi Google Gemini dù người dùng đã cấu hình khóa trên UI**: Người dùng đã nhập khóa Gemini API trên giao diện ModelOps (`/models`), nhưng hệ thống vẫn ưu tiên gọi OpenAI (`gpt-4o-mini`).
3. **Phụ thuộc vào biến môi trường `.env`**: Người dùng yêu cầu từ bỏ và xóa hoàn toàn API key LLM trong `.env`, chỉ quản trị tập trung 100% qua Nhà Cung Cấp ModelOps (`/models`) lưu trong PostgreSQL DB.
4. **Triệt tiêu hoàn toàn Hardcode**: Người dùng yêu cầu xử lý triệt để các nguyên nhân, loại bỏ toàn bộ mock giả, regex cắt lát thô trong Adapters và danh sách từ vựng gán cứng trong Fact Layer theo đúng Tôn chỉ AGENTS.md.
5. **Ràng buộc Git Push**: Tuân thủ nghiêm ngặt chỉ thị của người dùng: *"bạn cũng ko cần phải push code lên mỗi lần vide code, tôi sẽ tự làm"*. Tuyệt đối không chạy `git push`.

---

## 2. Phân Tích Nguyên Nhân Gốc Rễ (Root Cause Analysis)

Qua rà soát chuyên sâu toàn bộ pipeline từ UI $\rightarrow$ Workflow $\rightarrow$ RAG Service $\rightarrow$ ModelOps $\rightarrow$ Adapters:
- **Nguyên nhân 1 & 2 (Nuốt lỗi thiếu khóa & Ngăn chặn Failover)**:
  - Cấu hình Trợ lý Tuyển sinh có `primary_model="gpt-4o-mini"`. Khi truy vấn, `InferenceService` chọn `prov_openai`.
  - Trong `OpenAIAdapter`, khi `not self.api_key`, adapter không ném exception mà kích hoạt nhánh mock: trả về một `LLMResponse(content=...)` thành công giả với nội dung hotline cứng.
  - Vì adapter trả về kết quả hợp lệ (`status="success"`), `InferenceService` ghi nhận thành công, Circuit Breaker không mở và luồng Fallback sang Google Gemini (nơi có khóa thật) **hoàn toàn bị vô hiệu hóa**.
  - `InferenceService` đồng thời không kiểm tra trước xem Provider đám mây có khóa hoạt động trong CSDL hay không, dẫn đến việc nhà cung cấp không có khóa vẫn được xếp đầu danh sách gọi.
- **Nguyên nhân 3 (Pseudo-RAG Mock & Regex Slicing thô)**:
  - Các adapter (`OpenAIAdapter`, `GeminiAdapter`, `MistralAdapter`) chứa logic kiểm tra nếu có bảng `fact_markdown` hoặc đoạn trích thì cắt ghép regex trả về thô sơ không qua mô hình ngôn ngữ.
- **Nguyên nhân 4 (Khớp lỏng lẻo Unigram Fact Layer & Danh sách từ vựng hardcode)**:
  - Trong `facts.py`, khi người dùng hỏi *"đạt giải Ba HSG"*, từ `"giải"` được đưa vào danh sách từ khóa.
  - Câu lệnh SQL `KnowledgeFact.entity_name.ilike(f"%{clean_kw}%")` với `clean_kw = "giải"` đã khớp lỏng lẻo chuỗi con vào tên ngành *"Toán giải tích (9460102)"*.
  - Tại tầng lọc sau truy vấn, tồn tại mảng từ khóa cứng `common_attr_words = {"phương thức", "tuyển sinh", "chỉ tiêu", ...}`. Từ `"giải"` có 4 ký tự $\ge 3$ và không nằm trong mảng này nên bị coi là một `query_entity_marker`. Logic lọc kiểm tra `"giải" in "toán giải tích"` trả về `True`, khiến bảng chỉ tiêu ngành Toán giải tích bị trả về cho một câu hỏi chính sách giải thưởng học sinh giỏi.

---

## 3. Các Thay Đổi & Giải Pháp Kỹ Thuật Đã Triển Khai

### 3.1. Xóa Bỏ Hoàn Toàn API Key Khỏi `backend/.env`
- Đã xóa sạch các biến:
  - `OPENAI_API_KEY=`
  - `GEMINI_API_KEY=`
  - `MISTRAL_API_KEY=...`
- Cập nhật `DEFAULT_LLM_MODEL=gemini-2.5-flash` làm mô hình mặc định đồng bộ với Google Gemini.
- Toàn bộ thông tin xác thực LLM hiện được phân giải động 100% từ bảng `model_provider_configs` trong CSDL PostgreSQL 16.

### 3.2. Triệt Tiêu Mock Giả Trong Production Adapters & Fail-Loud
- **Tệp sửa đổi**:
  - `backend/app/modules/modelops/providers/openai_adapter.py`
  - `backend/app/modules/modelops/providers/gemini_adapter.py`
  - `backend/app/modules/modelops/providers/mistral_adapter.py`
- **Xử lý**:
  - Xóa bỏ toàn bộ nhánh pseudo-RAG mock, regex slicing và câu từ chối hotline cứng.
  - Khi `not self.api_key`: Kiểm tra nghiêm ngặt `settings.ENVIRONMENT in ("test", "testing")` và `self.api_key in ("mock", "test")`. Ở mọi môi trường thực tế (production/development), nếu thiếu khóa bắt buộc phải ném `AppException(status_code=401/503)` để kích hoạt Circuit Breaker và chuyển ngay sang Fallback Provider kế tiếp.

### 3.3. Nâng Cấp `InferenceService` (Cascading & Credential Prioritization)
- **Tệp sửa đổi**: `backend/app/modules/modelops/services/inference_service.py`
- **Xử lý trên cả `generate()` và `generate_stream()`**:
  - Thêm helper `_provider_has_credentials(p)` và `_is_local_provider(provider_type)`.
  - Chỉ lọc các provider đang kích hoạt (`only_active=True`).
  - Lọc và cô lập danh sách nhà cung cấp đã có khóa cấu hình (`configured_providers = [p for p in providers if _provider_has_credentials(p)]`).
  - Tăng vọt trọng số ưu tiên: Thưởng `+200` điểm cho provider có khóa hợp lệ trong CSDL, trừ `-500` điểm cho provider đám mây thiếu khóa.
  - Tự động bỏ qua các khóa trống trong key pool và các provider đám mây không có khóa.
  - Kết quả: Khi người dùng cấu hình khóa Gemini trên UI, hệ thống lập tức ưu tiên Google Gemini, tự động bỏ qua OpenAI chưa có khóa mà không nuốt lỗi.

### 3.4. Bóc Tách & Tra Cứu Fact Layer Theo Bất Biến Hình Thái Học (Algorithmic-First)
- **Tệp sửa đổi**: `backend/app/modules/rag/facts.py`
- **Xử lý**:
  - Xóa bỏ 100% mảng từ khóa gán cứng `common_attr_words` theo đúng Tôn chỉ 7 của AGENTS.md.
  - **Bất biến Hình thái học (Morphological Invariant)**:
    - Trong truy vấn SQL: Chỉ các cụm từ ghép danh từ hoàn chỉnh (`len(clean_kw.split()) >= 2` và `len(clean_kw) >= 4`) mới được phép khớp vào `KnowledgeFact.entity_name.ilike(...)`. Các từ đơn lẻ (unigrams như "giải", "thi", "điểm", "ba") chỉ được phép khớp vào `attribute_name` (tên thuộc tính).
    - Trong lọc thực thể (`query_entity_markers`): Chỉ tiếp nhận các mã định danh chuyên biệt (`entity_codes` như `7480201`, `6.8`), tên thực thể được bóc tách cụ thể (`target_entities`), hoặc mã số dạng chuỗi số trong keywords (`re.search(r"^\d{4,}$", clean_kw)`).
    - Đối với các câu hỏi chính sách chung (không nhắm vào ngành cụ thể nào), hệ thống tự động loại trừ toàn bộ các fact đặc thù của từng ngành lẻ (`_is_major_specific_fact`), giải quyết triệt để lỗi hiển thị "Toán giải tích" cho câu hỏi "giải Ba học sinh giỏi".

### 3.5. Chuyển Tiếp `preferred_provider_id` Trong Workflow DAG Node
- **Tệp sửa đổi**: `backend/app/modules/workflows/nodes/rag_answer_node.py`
- **Xử lý**:
  - Trích xuất `preferred_provider_id` từ `profile.model_policy` và truyền trực tiếp vào `AskRequest`.
  - Bảo đảm cấu hình nhà cung cấp ưu tiên của Trợ lý AI được chuyển vẹn nguyên sang `rag_service` và `InferenceService`.

### 3.6. Cập Nhật Quy Chuẩn Kỹ Thuật Vào `AGENTS.md`
- **Tệp sửa đổi**: `AGENTS.md`
- **Bổ sung**:
  - **Mục 1.9**: *Database-First ModelOps & Zero-Env LLM Credentials*: Toàn bộ thông tin cấu hình LLM lưu trữ 100% trong PostgreSQL qua giao diện `/models`. Cấm API key trong `.env`. Cấm tuyệt đối mock giả trong production adapters.
  - **Mục 3.6**: *Provider Credential Cascading & Fail-Fast Resolution*: Ưu tiên provider có khóa trong CSDL (+200 điểm), tự động bỏ qua provider thiếu khóa, chuyển tiếp `preferred_provider_id`.
  - **Mục 3.7**: *Morphological Fact-Layer Retrieval*: Tra cứu sự thật dựa trên bất biến hình thái học, cấm hardcode từ vựng trong mã nguồn.

---

## 4. Kết Quả Kiểm Thử (Verification & Testing)

1. **Test Suite RAG & Multiturn (`test_suggestion_perspective_and_multiturn.py`)**:
   - Bổ sung test case `test_lookup_facts_does_not_match_major_on_unigram_competition_award`.
   - Kết quả: **17/17 tests passed (100%)** trong 2.18s.
2. **Test Suite ModelOps (`test_modelops.py`)**:
   - Kiểm tra circuit breaker, dynamic fallback, provider catalog, key pool rotation, quota tracking.
   - Kết quả: **22/22 tests passed (100%)** trong 3.64s.
3. **Tuân thủ Git Policy**:
   - Đã chuẩn bị commit cục bộ. Không thực hiện lệnh `git push`.
