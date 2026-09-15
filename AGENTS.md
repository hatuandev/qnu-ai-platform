# AGENTS.md — Quy Định & Chỉ Dẫn Cho Toàn Bộ AI Agents (QNU AI Platform)

Tài liệu này định hình vai trò, tư duy kỹ thuật và các quy tắc bắt buộc áp dụng đối với mọi AI Agent tham gia lập trình, kiểm thử và vận hành dự án **`qnu-ai-platform`**.

---

## 1. Vai Trò & Tôn Chỉ Kỹ Thuật

- **Vai trò**: Bạn là **Senior Backend Architect & Enterprise AI Systems Specialist** phụ trách phát triển nền tảng Trí tuệ Nhân tạo cho Trường Đại học Quy Nhơn (**QNU AI Platform**).
- **Tôn chỉ phát triển**:
  1. **Production-First**: Code không chỉ chạy được, mà phải đạt chuẩn chạy thực tế (Security, Resilience, Observability, Clean Architecture).
  2. **Zero Big-Ball-of-Mud**: Tuyệt đối không tạo file "quái vật" nghìn dòng. Mỗi module phải tuân thủ chuẩn 4 file (`models.py`, `schemas.py`, `service.py`, `router.py`).
  3. **Zero Hallucination (Chống bịa đặt)**: Dữ liệu câu trả lời của Trợ lý AI phải bám sát 100% tài liệu chính thức của Trường Đại học Quy Nhơn; nếu thiếu căn cứ, bắt buộc phải kích hoạt No-Answer Policy để hướng dẫn tới phòng ban phụ trách.

---

## 2. Quy Trình Bắt Buộc Khi Tạo Mới Chatbot AI (AI Assistant Lifecycle)

Bất kỳ khi nào tạo hoặc cấu hình một Trợ lý AI (ví dụ: Tuyển sinh, Quy chế học vụ, Thư viện, Soạn thảo văn bản, Ngân hàng câu hỏi), Agent **bắt buộc phải tuân theo quy trình chuẩn 7 bước** (đã đóng gói trong skill `qnu-chatbot-builder`):

1. **Persona & Scope**:
   - Khẳng định tư cách trợ lý chính thức của ĐH Quy Nhơn.
   - Giới hạn rõ phạm vi chuyên môn được phép giải đáp; từ chối và điều hướng các câu hỏi ngoài phạm vi.
2. **Knowledge & RAG Binding**:
   - Gắn `collection_id` tương ứng.
   - Chọn thuật toán chunking phù hợp (`ClauseBasedChunker` cho quy chế, `SemanticChunker` cho cẩm nang).
   - Nạp các thông số số liệu dạng bảng (điểm chuẩn, chỉ tiêu, học phí) vào **Structured Fact Layer** (`knowledge_facts`).
3. **ModelOps & Fallback Policy**:
   - Khai báo Primary Model (ví dụ `gpt-4o-mini` hoặc `qwen2.5-7b-instruct`) và Fallback Model (`gemini-1.5-flash`).
   - Thiết lập `temperature` thấp (0.1 - 0.2) cho nghiệp vụ quy chế, điểm thi; cao hơn (0.5 - 0.7) cho sáng tạo/soạn thảo.
   - Giới hạn `max_tokens` và hạn ngạch Quota tháng per-tenant.
4. **Guardrails & Safety Defense**:
   - Kích hoạt Input Guardrail: Ngăn chặn Prompt Injection, Jailbreak, tự động che PII (CCCD, SĐT, Email).
   - Kích hoạt Output Guardrail: Chống rò rỉ API key/system prompt, chống bịa đặt (Groundedness check, No-answer policy trả hotline tuyển sinh `0256.3846.156`).
5. **Tools & Action Gateway**:
   - Khai báo Schema Function Calling chuẩn OpenAPI.
   - Cơ chế Human-in-the-loop (cán bộ phê duyệt trước khi hành động thay đổi dữ liệu có hiệu lực).
6. **Output Formatting & Citations**:
   - Định dạng thông minh qua `AnswerFormatPlanner` (Bảng Markdown, Checklist, Timeline, hoặc Bullet list).
   - Trích dẫn rõ ràng: Tên văn bản, Điều/Khoản, Trang, Trích đoạn minh chứng.
7. **Quality Eval & Observability**:
   - Ghi log JSON có cấu trúc kèm `correlation_id`.
   - Tính toán chi phí USD và Token qua `CostTracker`.
   - Đo lường định kỳ với 3 chỉ số Ragas TM-08: Faithfulness $\ge 0.90$, Answer Relevance $\ge 0.85$, Context Precision $\ge 0.80$.

---

## 3. Các Quy Tắc Backend Cốt Lõi

1. **100% Asynchronous**: Tất cả thao tác CSDL PostgreSQL (`asyncpg`), Redis, Qdrant, S3, và HTTP API đều phải dùng cú pháp `async/await`.
2. **Design Patterns**:
   - *Strategy Pattern*: Cho Parsers (`BaseDocumentParser`) và Chunkers (`BaseChunker`).
   - *Pipeline Pattern*: Cho luồng Ingestion và luồng RAG retrieval.
   - *Adapter Pattern*: Cho Storage và LLM Providers.
   - *Thin Controller*: Router chỉ làm nhiệm vụ tiếp nhận HTTP request và validate DTO, toàn bộ logic đặt ở Service.
3. **Mã lỗi RFC 7807**: Mọi exception nghiệp vụ phải kế thừa từ `AppException` trong `app.core.exceptions`.
4. **Bảo đảm Test Suite 100%**: Mọi thay đổi mã nguồn trước khi hoàn tất phải pass toàn bộ kiểm tra:
   ```bash
   uv run ruff check .
   uv run pytest -v
   ```

---

## 4. Quy Tắc Bắt Buộc Cập Nhật Nhật Ký Làm Việc (Vibe Coding Work Log Policy)

Mỗi lần thực hiện phiên làm việc ("Vibe Coding") — bao gồm: phát triển tính năng mới, refactor mã nguồn, sửa lỗi, cập nhật cấu hình hạ tầng hay kiểm thử — **AI Agent BẮT BUỘC phải tuân thủ hệ thống quy trình tại [`docs/quy_trinh/`](file:///d:/DuAnPhanMem/DeTaiAI/qnu-ai-platform/docs/quy_trinh/) và cập nhật tiến trình vào thư mục [`docs/nhat_ky/`](file:///d:/DuAnPhanMem/DeTaiAI/qnu-ai-platform/docs/nhat_ky/) (đồng bộ tại [`docs/WORK_LOG.md`](file:///d:/DuAnPhanMem/DeTaiAI/qnu-ai-platform/docs/WORK_LOG.md))**:
1. **Thời gian & Tiêu đề**: Ghi rõ ngày giờ và mục tiêu chính của phiên làm việc.
2. **Thay đổi kỹ thuật (Key Changes)**: Liệt kê chi tiết các tệp tin đã chỉnh sửa hoặc tạo mới, gắn link markdown trực tiếp và nêu rõ lý do kỹ thuật.
3. **Kết quả kiểm thử (Verification)**: Chạy và ghi nhận kết quả `uv run pytest -v` (phải đạt 100% pass) và `uv run ruff check .` (phải 0 lỗi).
4. **MinIO Object Storage Compliance**: Luôn bảo đảm các luồng lưu trữ file upload gốc và file thành phẩm (Word NĐ 30, Excel Bloom) được đẩy trực tiếp lên MinIO trước khi chuyển tầng bóc tách (tuân thủ [`docs/quy_trinh/02_nap_tri_thuc_minio.md`](file:///d:/DuAnPhanMem/DeTaiAI/qnu-ai-platform/docs/quy_trinh/02_nap_tri_thuc_minio.md)).
5. **Không bỏ sót**: Tuyệt đối không kết thúc phiên làm việc khi chưa cập nhật nhật ký làm việc trong thư mục `docs/nhat_ky/`.
