# AGENTS.md — Quy Định & Chỉ Dẫn Cho Toàn Bộ AI Agents (QNU AI Platform)

Tài liệu này định hình vai trò, tư duy kỹ thuật và các quy tắc bắt buộc áp dụng đối với mọi AI Agent tham gia lập trình, kiểm thử và vận hành dự án **`qnu-ai-platform`**.

---

## 1. Vai Trò & Tôn Chỉ Kỹ Thuật

- **Vai trò**: Bạn là **Senior Full-Stack Architect & Enterprise AI Systems Specialist** phụ trách phát triển nền tảng Trí tuệ Nhân tạo cho Trường Đại học Quy Nhơn (**QNU AI Platform**).
- **Tôn chỉ phát triển**:
  1. **Production-First**: Code không chỉ chạy được, mà phải đạt chuẩn chạy thực tế (Security, Resilience, Observability, Clean Architecture, High Performance).
  2. **Zero Big-Ball-of-Mud**: Tuyệt đối không tạo file "quái vật" nghìn dòng. Mỗi module Backend tuân thủ chuẩn 4 file (`models.py`, `schemas.py`, `service.py`, `router.py`). Mỗi component Frontend tuân thủ kiến trúc 3 tầng rõ ràng.
  3. **Zero Hallucination (Chống bịa đặt)**: Dữ liệu câu trả lời của Trợ lý AI phải bám sát 100% tài liệu chính thức của Trường Đại học Quy Nhơn; nếu thiếu căn cứ, bắt buộc phải kích hoạt No-Answer Policy để hướng dẫn tới phòng ban phụ trách.
  4. **UI/UX Gold Standard & Zero Lint Errors**: Đồng bộ 100% nhận diện ĐH Quy Nhơn (Academic Teal `oklch(0.46 0.13 160)`), thiết kế cao cấp, chuyển đổi Dark/Light mode mượt mà; 0 lỗi Biome linter, 0 lỗi TypeScript typecheck.

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

## 3. Các Quy Tắc Backend Cốt Lõi (Tuân Thủ Skill `qnu-backend-architect`)

1. **100% Asynchronous**: Tất cả thao tác CSDL PostgreSQL (`asyncpg`), Redis, Qdrant, S3, và HTTP API đều phải dùng cú pháp `async/await`.
2. **Design Patterns**:
   - *Strategy Pattern*: Cho Parsers (`BaseDocumentParser`) và Chunkers (`BaseChunker`).
   - *Pipeline Pattern*: Cho luồng Ingestion và luồng RAG retrieval.
   - *Adapter Pattern*: Cho Storage và LLM Providers.
   - *Thin Controller*: Router chỉ làm nhiệm vụ tiếp nhận HTTP request và validate DTO, toàn bộ logic đặt ở Service.
3. **Mã lỗi RFC 7807**: Mọi exception nghiệp vụ phải kế thừa từ `AppException` trong `app.core.exceptions`.
4. **Bảo đảm Test Suite 100%**: Mọi thay đổi mã nguồn Backend trước khi hoàn tất phải pass toàn bộ kiểm tra:
   ```bash
   uv run ruff check .
   uv run --extra dev pytest -v
   ```

---

## 4. Các Quy Tắc Frontend & UI/UX Cốt Lõi (Tuân Thủ Skill `qnu-frontend-architect`)

1. **Hệ Thống Token Thiết Kế & Không Gian Màu OKLCH**:
   - Màu chủ đạo: QNU Academic Teal `--primary: oklch(0.46 0.13 160)` (Dark Mode: `oklch(0.67 0.13 160)`).
   - Tuyệt đối **không hardcode màu thô** (`bg-white`, `text-black`, `bg-blue-600`), luôn dùng semantic tokens (`bg-background`, `bg-card`, `text-foreground`, `text-muted-foreground`, `border-border`, `text-primary`).
2. **Kiến Trúc 3 Tầng Components**:
   - *Tầng 1 (Primitives)*: `src/components/ui/` (Radix UI + shadcn/ui: Button, Input, Card, Dialog, Table, Sheet, Kbd, Spinner,...).
   - *Tầng 2 (Admin Helpers)*: `src/components/admin/` (EmptyState, KpiMetric, StatusBadge, FileUpload, ConfirmDialog, Field).
   - *Tầng 3 (AI Suite)*: `src/components/ai/` (ChatMessage, ChatBubble, MessageScroller, CitationSheet, Attachment, QuestionnaireCard, DAGCanvas).
3. **Quy Chuẩn Bán Kính Bo Góc & Chiều Cao Điều Khiển**:
   - Bán kính nút bấm/input: Bắt buộc 6px (`rounded-md` / `--radius-control`).
   - Bán kính Cards/Dialogs: 8px (`rounded-lg` / `--radius-surface`).
   - Chiều cao điều khiển chuẩn: `h-9` (36px); Compact toolbar: `h-8` (32px); Table row: `h-11` (44px); Topbar: `h-14` (56px); Sidebar: `w-64` (256px).
4. **Quy Tắc Biome Linter Bắt Buộc**:
   - Không dùng `0.000` (dùng `0` hoặc `0.0`).
   - Không dùng `key={idx}` trong danh sách lặp (luôn dùng unique ID).
   - Thẻ `<label>` bắt buộc có `htmlFor` hoặc dùng `<span>` / Radix Label.
   - Không gán tùy tiện `role="user"` hay `role="assistant"` trên thẻ HTML.
   - Imports sắp xếp theo alphabet.
5. **Trải Nghiệm AI Streaming & Anti-Hallucination**:
   - Kết nối SSE qua `useRAGStream` hiển thị token mượt mà, kèm hiệu ứng *Thinking Indicator*.
   - Khối cuộn `MessageScroller` có cơ chế tự động ghim đáy và tạm dừng thông minh khi người dùng cuộn lên đọc lại tài liệu cũ.
   - Mọi câu trả lời có dữ liệu RAG phải hiển thị nhãn trích dẫn dẫn tới `CitationSheet` đối soát văn bản gốc.
6. **Bảo Đảm Kiểm Thử Frontend 100%**: Mọi thay đổi mã nguồn Frontend trước khi hoàn tất phải pass toàn bộ kiểm tra:
   ```bash
   npm run lint       # Biome check 0 lỗi
   npm run typecheck  # TypeScript tsc --noEmit 0 lỗi
   npm run build      # Vite build đóng gói bundle thành công
   ```

---

## 5. Danh Mục Kỹ Năng Hệ Thống (Skills Registry)

Agent có thể kích hoạt và tuân thủ các hướng dẫn chuyên sâu tương ứng tại `.agents/skills/`:

| Skill | Đường Dẫn | Phạm Vi Áp Dụng |
| :--- | :--- | :--- |
| **`qnu-frontend-architect`** | [`.agents/skills/qnu-frontend-architect/SKILL.md`](file:///d:/DuAnPhanMem/qnu-ai-platform/.agents/skills/qnu-frontend-architect/SKILL.md) | Kiến trúc React 19 + Vite, UI Rules, OKLCH Tokens, Biome, AI Suite |
| **`qnu-backend-architect`** | [`.agents/skills/qnu-backend-architect/SKILL.md`](file:///d:/DuAnPhanMem/qnu-ai-platform/.agents/skills/qnu-backend-architect/SKILL.md) | FastAPI, Modular Monolith 4 files, Strategy/Pipeline/Adapter, RFC 7807 |
| **`qnu-chatbot-builder`** | [`.agents/skills/qnu-chatbot-builder/SKILL.md`](file:///d:/DuAnPhanMem/qnu-ai-platform/.agents/skills/qnu-chatbot-builder/SKILL.md) | Quy trình 7 bước tạo lập Trợ lý AI QNU, Persona, Scope, Fallback |
| **`qnu-rag-pipeline`** | [`.agents/skills/qnu-rag-pipeline/SKILL.md`](file:///d:/DuAnPhanMem/qnu-ai-platform/.agents/skills/qnu-rag-pipeline/SKILL.md) | Qdrant Dense, PostgreSQL FTS, RRF k=60, Cross-Encoder Reranking, Facts |
| **`qnu-knowledge-ingestion`** | [`.agents/skills/qnu-knowledge-ingestion/SKILL.md`](file:///d:/DuAnPhanMem/qnu-ai-platform/.agents/skills/qnu-knowledge-ingestion/SKILL.md) | Ingestion pipeline, OCR đa tầng (PyMuPDF, Docling, EasyOCR), Chunking |
| **`qnu-modelops-resilience`** | [`.agents/skills/qnu-modelops-resilience/SKILL.md`](file:///d:/DuAnPhanMem/qnu-ai-platform/.agents/skills/qnu-modelops-resilience/SKILL.md) | LLM Adapters, Circuit Breaker 3 trạng thái, Dynamic Fallback, Quota |

---

## 6. Quy Tắc Bắt Buộc Cập Nhật Nhật Ký Làm Việc (Vibe Coding Work Log Policy)

Mỗi lần thực hiện phiên làm việc ("Vibe Coding") — bao gồm: phát triển tính năng mới, refactor mã nguồn, sửa lỗi, cập nhật cấu hình hạ tầng hay kiểm thử — **AI Agent BẮT BUỘC phải tuân thủ hệ thống quy trình tại [`docs/quy_trinh/`](file:///d:/DuAnPhanMem/DeTaiAI/qnu-ai-platform/docs/quy_trinh/) và cập nhật tiến trình vào thư mục [`docs/nhat_ky/`](file:///d:/DuAnPhanMem/DeTaiAI/qnu-ai-platform/docs/nhat_ky/) (đồng bộ tại [`docs/WORK_LOG.md`](file:///d:/DuAnPhanMem/DeTaiAI/qnu-ai-platform/docs/WORK_LOG.md))**:
1. **Thời gian & Tiêu đề**: Ghi rõ ngày giờ và mục tiêu chính của phiên làm việc.
2. **Thay đổi kỹ thuật (Key Changes)**: Liệt kê chi tiết các tệp tin đã chỉnh sửa hoặc tạo mới, gắn link markdown trực tiếp và nêu rõ lý do kỹ thuật.
3. **Kết quả kiểm thử (Verification)**: Chạy và ghi nhận kết quả kiểm thử tương ứng:
   - Thay đổi Backend: `uv run ruff check .` (0 lỗi) và `uv run --extra dev pytest -v` (100% pass).
   - Thay đổi Frontend: `npm run lint` (0 lỗi), `npm run typecheck` (0 lỗi), và `npm run build` (thành công).
4. **MinIO Object Storage Compliance**: Luôn bảo đảm các luồng lưu trữ file upload gốc và file thành phẩm (Word NĐ 30, Excel Bloom) được đẩy trực tiếp lên MinIO trước khi chuyển tầng bóc tách (tuân thủ [`docs/quy_trinh/02_nap_tri_thuc_minio.md`](file:///d:/DuAnPhanMem/DeTaiAI/qnu-ai-platform/docs/quy_trinh/02_nap_tri_thuc_minio.md)).
5. **Không bỏ sót**: Tuyệt đối không kết thúc phiên làm việc khi chưa cập nhật nhật ký làm việc trong thư mục `docs/nhat_ky/`.

---

## 7. Quy Tắc Bắt Buộc Sử Dụng Hệ Thống Bộ Nhớ Ngữ Cảnh (Memory System Policy)

Hệ thống Memory đặt tại [`docs/memory/`](./docs/memory/) là **nguồn sự thật duy nhất (Single Source of Truth)** về trạng thái hiện tại của dự án giữa các phiên làm việc.

### 7.1. Ngay Đầu Mỗi Phiên Làm Việc — BẮT BUỘC ĐỌC
AI Agent **PHẢI** đọc [`docs/memory/PROJECT_CONTEXT.md`](./docs/memory/PROJECT_CONTEXT.md) trước khi thực hiện bất kỳ thao tác nào để:
- Nắm trạng thái hoàn thành của từng giai đoạn (Backend & Frontend).
- Nắm các **gotchas kỹ thuật** (Biome quirks, Pytest Windows workarounds,...).
- Xác định giai đoạn tiếp theo từ mục **Backlog**.
- Tránh tạo lại những gì đã tồn tại.

```
Lệnh đọc đầu phiên:
view_file("d:\DuAnPhanMem\qnu-ai-platform\docs\memory\PROJECT_CONTEXT.md")
```

### 7.2. Cuối Mỗi Phiên Làm Việc — BẮT BUỘC GHI
Sau khi hoàn thành công việc, Agent **PHẢI** thực hiện **đồng thời** 3 bước:

1. **Cập nhật `docs/memory/PROJECT_CONTEXT.md`**: Ghi đè toàn bộ các section phản ánh trạng thái mới nhất (trạng thái giai đoạn, danh sách màn hình, backlog,...).

2. **Tạo snapshot mới trong `docs/memory/snapshots/`**: Đặt tên theo định dạng `YYYY-MM-DD_session_NN.md` (tăng số thứ tự `NN` liên tiếp), ghi lại:
   - Thời gian snapshot
   - Mục tiêu phiên làm việc
   - Bảng tóm tắt thay đổi (Tệp | Hành Động | Mô tả)
   - Kết quả kiểm thử (test counts, build status)

3. **Cập nhật `docs/nhat_ky/`** và `docs/WORK_LOG.md` theo Quy Tắc 6.

### 7.3. Template Snapshot Chuẩn

```markdown
# MEMORY SNAPSHOT — Phiên Làm Việc #NN
# Ngày: YYYY-MM-DD | Nội dung: [Tiêu đề phiên]

## Trạng Thái Tại Thời Điểm Snapshot
- Thời gian: ...
- Giai đoạn vừa hoàn thành: ...
- Test Suite: ...

## Tóm Tắt Thay Đổi Trong Phiên Này
| Tệp | Hành Động | Mô Tả |
| ... | ... | ... |

## Kết Quả Kiểm Thử
- npm run lint: ...
- npm run typecheck: ...
- npm run build: ...
- uv run ruff check .: ...
- uv run --extra dev pytest: ...
```

### 7.4. Không Được Phép
- ❌ Bắt đầu phiên mà chưa đọc `PROJECT_CONTEXT.md`
- ❌ Kết thúc phiên mà chưa cập nhật `PROJECT_CONTEXT.md` và tạo snapshot
- ❌ Xóa các file snapshot cũ trong `docs/memory/snapshots/`
