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
   - **Cấm test giả (Anti-Mock-Test)**: Test không được pass nhờ đường fallback/mock (ví dụ service trả catalog seed khi DB lỗi, embedding giả khi Qdrant offline). Mỗi suite phải có ít nhất 1 ca phủ đường lỗi (DB down, API lỗi, RAG trống kết quả) để hành vi fallback lộ rõ và tuân thủ No-Answer Policy.

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
5. **Tư Duy UI Mở & Kiến Trúc Điều Hướng Sâu (Master-Detail Deep Routing Pattern)**:
   - **Tuyệt đối không nhồi nhét "Monolithic Tabbed Page"**: Không gộp toàn bộ tính năng danh sách, chi tiết, chỉnh sửa chuyên sâu và quy trình wizard vào một file trang duy nhất bằng các thẻ Tab gò bó hay Dialog chật hẹp.
   - **Quy chuẩn 1 Domain = List Page + Dedicated Detail Pages**:
     - *Trang Danh Sách (Master/List View)*: Tập trung vào tổng quan thực thể (Kho tri thức, Trợ lý AI, Provider, Workflows), bộ lọc tìm kiếm, chỉ số KPI và danh sách Card/Bảng tối giản, thoáng đãng.
     - *Trang Chi Tiết Độc Lập (Dedicated Detail View)*: Khi người dùng click vào bất kỳ Card/Hàng bảng nào, **BẮT BUỘC PHẢI chuyển hướng sang trang chi tiết riêng biệt** với URL phân cấp rõ ràng (ví dụ: `/knowledge/collections/:id`, `/assistants/:id`, `/models/:id`, `/workflows/:id`).
     - *Tách File Độc Lập*: Trang chi tiết phải là một component/file riêng (ví dụ `collection-detail-page.tsx`, `assistant-detail-page.tsx`), không viết chung thành khối nghìn dòng trong trang danh sách.
   - **Tiêu chuẩn bắt buộc trên Trang Chi Tiết**:
     - *Thanh điều hướng quay lại & Breadcrumb*: Có nút quay lại (`ArrowLeft`) và breadcrumb phân cấp rõ ràng (`Kho Tri Thức / [Tên Bộ Sưu Tập]`).
     - *Header & Action Toolbar*: Tên đối tượng, huy hiệu trạng thái và các nút thao tác đặc thù (Chỉnh sửa, Xóa, Đồng bộ, Test,...).
     - *Không gian hiển thị sâu*: Tận dụng toàn bộ màn hình để bố trí 2-3 cột dữ liệu sâu (tài liệu con, chunks, vector embedding, facts số hóa, lịch sử hoạt động) mà không bị gò bó.
     - *Deep Linking*: Người dùng có thể F5, bookmark hoặc chia sẻ URL trực tiếp tới đúng đối tượng.
6. **Trải Nghiệm AI Streaming & Anti-Hallucination**:
   - Kết nối SSE qua `useRAGStream` hiển thị token mượt mà, kèm hiệu ứng *Thinking Indicator*.
   - Khối cuộn `MessageScroller` có cơ chế tự động ghim đáy và tạm dừng thông minh khi người dùng cuộn lên đọc lại tài liệu cũ.
   - Mọi câu trả lời có dữ liệu RAG phải hiển thị nhãn trích dẫn dẫn tới `CitationSheet` đối soát văn bản gốc.
7. **Bảo Đảm Kiểm Thử Frontend 100%**: Mọi thay đổi mã nguồn Frontend trước khi hoàn tất phải pass toàn bộ kiểm tra:
   ```bash
   npm run lint       # Biome check 0 lỗi
   npm run typecheck  # TypeScript tsc --noEmit 0 lỗi
   npm run build      # Vite build đóng gói bundle thành công
   ```
   - **Cấm test/assert trên mock che lỗi**: E2E và unit test phải phân biệt rõ trạng thái "Backend thật" và "Offline Seed Fallback"; tuyệt đối không assert số liệu nghiệp vụ (điểm chuẩn, quota, metrics, citations) khi đang ở chế độ fallback.

---

## 5. Danh Mục Kỹ Năng Hệ Thống (Skills Registry)

Agent có thể kích hoạt và tuân thủ các hướng dẫn chuyên sâu tương ứng tại `.agents/skills/`:

| Skill | Đường Dẫn | Phạm Vi Áp Dụng |
| :--- | :--- | :--- |
| **`qnu-frontend-architect`** | [`.agents/skills/qnu-frontend-architect/SKILL.md`](.agents/skills/qnu-frontend-architect/SKILL.md) | Kiến trúc React 19 + Vite, UI Rules, OKLCH Tokens, Biome, AI Suite |
| **`qnu-backend-architect`** | [`.agents/skills/qnu-backend-architect/SKILL.md`](.agents/skills/qnu-backend-architect/SKILL.md) | FastAPI, Modular Monolith 4 files, Strategy/Pipeline/Adapter, RFC 7807 |
| **`qnu-chatbot-builder`** | [`.agents/skills/qnu-chatbot-builder/SKILL.md`](.agents/skills/qnu-chatbot-builder/SKILL.md) | Quy trình 7 bước tạo lập Trợ lý AI QNU, Persona, Scope, Fallback |
| **`qnu-rag-pipeline`** | [`.agents/skills/qnu-rag-pipeline/SKILL.md`](.agents/skills/qnu-rag-pipeline/SKILL.md) | Qdrant Dense, PostgreSQL FTS, RRF k=60, Cross-Encoder Reranking, Facts |
| **`qnu-knowledge-ingestion`** | [`.agents/skills/qnu-knowledge-ingestion/SKILL.md`](.agents/skills/qnu-knowledge-ingestion/SKILL.md) | Ingestion pipeline, OCR đa tầng (PyMuPDF, Docling, EasyOCR), Chunking |
| **`qnu-modelops-resilience`** | [`.agents/skills/qnu-modelops-resilience/SKILL.md`](.agents/skills/qnu-modelops-resilience/SKILL.md) | LLM Adapters, Circuit Breaker 3 trạng thái, Dynamic Fallback, Quota |
| **`qnu-clean-code-architect`** | [`.agents/skills/qnu-clean-code-architect/SKILL.md`](.agents/skills/qnu-clean-code-architect/SKILL.md) | Chuẩn mực Clean Code khi Vibe Coding: Boy Scout Rule, Zero Dead Code/Any, Guard Clauses, SRP |

---

## 6. Quy Tắc Bắt Buộc Cập Nhật Nhật Ký Làm Việc (Vibe Coding Work Log Policy)

Mỗi lần thực hiện phiên làm việc ("Vibe Coding") — bao gồm: phát triển tính năng mới, refactor mã nguồn, sửa lỗi, cập nhật cấu hình hạ tầng hay kiểm thử — **AI Agent BẮT BUỘC phải tuân thủ hệ thống quy trình tại [`docs/quy_trinh/`](docs/quy_trinh/) và cập nhật tiến trình vào thư mục [`docs/nhat_ky/`](docs/nhat_ky/) (đồng bộ tại [`docs/WORK_LOG.md`](docs/WORK_LOG.md))**:
1. **Thời gian & Tiêu đề**: Ghi rõ ngày giờ và mục tiêu chính của phiên làm việc.
2. **Thay đổi kỹ thuật (Key Changes)**: Liệt kê chi tiết các tệp tin đã chỉnh sửa hoặc tạo mới, gắn link markdown trực tiếp và nêu rõ lý do kỹ thuật.
3. **Kết quả kiểm thử (Verification)**: Chạy và ghi nhận kết quả kiểm thử tương ứng:
   - Thay đổi Backend: `uv run ruff check .` (0 lỗi) và `uv run --extra dev pytest -v` (100% pass).
   - Thay đổi Frontend: `npm run lint` (0 lỗi), `npm run typecheck` (0 lỗi), và `npm run build` (thành công).
4. **MinIO Object Storage Compliance**: Luôn bảo đảm các luồng lưu trữ file upload gốc và file thành phẩm (Word NĐ 30, Excel Bloom) được đẩy trực tiếp lên MinIO trước khi chuyển tầng bóc tách (tuân thủ [`docs/quy_trinh/02_nap_tri_thuc_minio.md`](docs/quy_trinh/02_nap_tri_thuc_minio.md)).
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

---

## 8. Quy Chuẩn Clean Code Bắt Buộc Khi Vibe Coding (Vibe Coding Clean Code Standards)

"Vibe Coding" là phong cách lập trình tốc độ cao dựa trên trí tuệ nhân tạo, nhưng **tuyệt đối không được đánh đổi chất lượng mã nguồn lấy tốc độ**. Mọi AI Agent tham gia dự án QNU AI Platform phải tuân thủ nghiêm ngặt 8 điều răn Clean Code sau:

### 8.1. Quy Tắc Hướng Đạo Sinh (The Boy Scout Rule)
> *"Luôn để codebase sạch hơn lúc bạn tìm thấy nó."*
- Khi mở bất kỳ file nào để sửa lỗi hoặc thêm tính năng, Agent **phải tự động dọn dẹp**: xóa bỏ các `import` không dùng, loại bỏ các biến chết (dead variables), và sửa các cảnh báo linter tiềm ẩn trong file đó.
- Không để lại "rác kỹ thuật" (technical debt) với lý do "đó là code của người trước viết".

### 8.2. Triệt Tiêu Mã Chết & Rác Debug (Zero Dead Code & Zero Debug Junk)
- **Cấm tuyệt đối comment-out code cũ**: Không bao giờ để lại các khối lệnh bị comment `// const oldData = ...` hay `# def old_method():`. Nếu code không còn dùng, **XÓA THẲNG TAY** — Git lưu lại toàn bộ lịch sử.
- **Cấm để lại rác debug**: Tuyệt đối dọn sạch toàn bộ `console.log(...)`, `console.debug(...)`, `print(...)` debug tạm thời trước khi kết thúc turn. Chỉ giữ lại các structured log (`logger.info`, `logger.error`) có cấu trúc chuẩn.
- **Không dùng placeholder cẩu thả**: Cấm để lại `// TODO: implement later`, `pass` trống rỗng hay mock giả tạm bợ mà không có fallback an toàn hoặc logic xử lý hoàn chỉnh.

### 8.3. An Toàn Kiểu Dữ Liệu Tuyệt Đối (Type Safety & Zero `any`)
- **Frontend (TypeScript)**:
  - Cấm sử dụng kiểu `any` hoặc ép kiểu mù quáng `as any` để qua mặt compiler.
  - Luôn định nghĩa explicit interfaces / types cho Component Props, API DTOs, và State.
  - Sử dụng Generic Types và Discriminated Unions khi làm việc với dữ liệu đa hình.
- **Backend (Python)**:
  - 100% hàm phải có Type Hints đầy đủ (`def foo(x: int) -> str:`).
  - Sử dụng Pydantic v2 Models (`BaseModel`) cho toàn bộ request/response DTOs, cấm dùng `dict` không định hình.

### 8.4. Đặt Tên Tự Giải Thích (Self-Documenting Naming)
- Tên biến, hàm, component phải nói lên chính xác mục đích và nghiệp vụ ĐH Quy Nhơn:
  - **Boolean**: Bắt buộc bắt đầu bằng tiền tố: `is...`, `has...`, `should...`, `can...` (ví dụ: `isUploading`, `hasPermission`, `shouldFallback`).
  - **Functions / Methods**: Bắt đầu bằng động từ hành động rõ ràng (`fetchDocuments`, `handleFileSelect`, `calculateElapsedMs`, `formatFactTable`).
  - **Constants**: Viết hoa phân tách bằng gạch dưới (`UPPER_SNAKE_CASE`, ví dụ `MAX_CHUNK_SIZE`, `DEFAULT_RETRY_ATTEMPTS`).
  - **Cấm viết tắt vô nghĩa**: Tuyệt đối không đặt tên kiểu `d`, `temp`, `res1`, `item2`, `val`, `x`, `arr`.

### 8.5. Đơn Trách Nhiệm & Hàm Nhỏ Gọn (Single Responsibility & Small Functions)
- Mỗi hàm hoặc component chỉ giải quyết **MỘT** nhiệm vụ duy nhất và làm thật tốt nhiệm vụ đó.
- Hàm không nên dài quá 40 dòng. Nếu một hàm vượt quá phạm vi đó, hãy tách thành các private helper functions hoặc pure utilities.
- Trong React: Không nhồi logic tính toán, parsing chuỗi hoặc format dữ liệu phức tạp vào thân JSX. Hãy tách ra `useMemo`, custom hooks hoặc utility functions riêng ngoài render scope.

### 8.6. Mẫu Trả Về Sớm (Early Return / Guard Clauses Pattern)
- Luôn kiểm tra điều kiện biên, lỗi đầu vào và `return` sớm nhất có thể (Fail-Fast):
  ```typescript
  // ❌ Xấu (Pyramid of Doom - Lồng ghép sâu):
  if (user) {
    if (user.isActive) {
      if (hasPermission) {
        doAction();
      }
    }
  }

  // ✅ Đẹp (Early Return / Guard Clauses):
  if (!user || !user.isActive || !hasPermission) return;
  doAction();
  ```

### 8.7. Không Nuốt Lỗi Âm Thầm (No Swallowed Exceptions)
- Tuyệt đối cấm khối lệnh rỗng: `catch (e) {}` hay `except Exception: pass` nuốt trôi lỗi mà không có bất kỳ phản hồi nào.
- Mọi khối bắt lỗi phải:
  1. Ghi log có ngữ cảnh (`logger.warning` / `logger.error` kèm lý do), HOẶC
  2. Kích hoạt graceful fallback **được phép**: retry với backoff, chuyển sang provider dự phòng, hoặc dùng cache hợp lệ gần nhất **có gắn nhãn thời điểm dữ liệu**, HOẶC
  3. Hiển thị thông báo thân thiện (Toast / Alert) để người dùng nắm được nguyên nhân sự cố.
- **CẤM fallback bằng mock data bịa đặt cho dữ liệu nghiệp vụ**: Tuyệt đối không trả số liệu giả (điểm chuẩn, học phí, chỉ tiêu, nội dung quy chế, trích dẫn văn bản,...) khi backend/RAG thất bại. Khi thiếu dữ liệu thật, Frontend phải hiển thị trạng thái lỗi/trống rõ ràng và Backend phải kích hoạt No-Answer Policy (điều hướng tới phòng ban phụ trách) — không bao giờ hiển thị số liệu giả như số liệu thật.

### 8.8. Vòng Lặp Tự Làm Sạch Tự Động (Clean-As-You-Go Loop)
- Trước khi kết thúc bất kỳ lượt xử lý (turn) nào hoặc bàn giao code cho người dùng, Agent **BẮT BUỘC** phải tự chạy kiểm tra tĩnh và format:
  ```bash
  # Frontend:
  npm run lint       # Biome tự động rà soát & format
  npm run typecheck  # TypeScript kiểm tra 0 lỗi type

  # Backend:
  uv run ruff check .  # Ruff kiểm tra & dọn imports
  ```
- **Không bao giờ bàn giao code khi còn bất kỳ lỗi lint hay typecheck nào!**

---

## 9. Quy Tắc Bắt Buộc Về Git, Encoding & Bảo Mật Secrets

Ba sự cố đã từng xảy ra thật trong dự án (commit ảnh nhị phân 9MB, double-encoding mojibake, hardcode `SECRET_KEY`) — các quy tắc dưới đây là biện pháp ngăn tái diễn.

### 9.1. Không Commit File Nhị Phân & Dung Lượng Lớn Vào Git
- **Cấm** commit ảnh scan, PDF/DOCX mẫu, video, model weights, datasets, thư mục cache (`ocr-cache`, `node_modules`, `.venv`, `dist`, `test-results`) vào repository.
- Tài liệu gốc và ảnh scan dung lượng lớn phải lưu trên **MinIO/S3 Object Storage** (tuân thủ mục 6.4) hoặc **Git LFS** nếu bắt buộc version cùng code.
- Thư mục `frontend/public/` chỉ giữ assets nhẹ phục vụ UI (icons, placeholder); trước mỗi commit, Agent phải kiểm tra `git status` và từ chối stage file `> 500KB` khi chưa được người dùng xác nhận.

### 9.2. Bắt Buộc UTF-8 Cho Mọi File Text
- Mọi file `.md`, `.py`, `.ts/.tsx`, `.json`, `.yml/.yaml`, `.toml` phải được đọc/ghi ở encoding **UTF-8** (khuyến nghị giữ BOM cho markdown tiếng Việt, LF cho line endings).
- Dấu hiệu double-encoding (file hỏng): xuất hiện `Ã`, `â€`, `á»` khi mở file. Khi phát hiện, Agent phải **khôi phục bằng cách đảo ngược** (map từng ký tự về byte gốc cp1252 rồi decode UTF-8) và đối chiếu với bản cha trên git — tuyệt đối không commit đè file hỏng.
- Sau khi ghi file tiếng Việt, Agent phải đọc lại kiểm chứng trước khi kết thúc phiên.

### 9.3. Cấm Hardcode Secrets Trong Code
- Tuyệt đối không hardcode `SECRET_KEY`, API key, password, connection string vào mã nguồn. Mọi secret phải đọc từ biến môi trường / file `.env` (và `.env` **không bao giờ** được commit).
- Giá trị mặc định trong `app/core/config.py` chỉ được là placeholder rỗng hoặc giá trị dev vô hại; `DEV_AUTH_ENABLED` bắt buộc là `False` ở môi trường production.
- Trước mỗi commit, Agent phải rà soát diff để bảo đảm không lọt secret mới (API key, token, private key) vào lịch sử git.

