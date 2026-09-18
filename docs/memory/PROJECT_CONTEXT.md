# PROJECT_CONTEXT.md — Snapshot Ngữ Cảnh Dự Án QNU AI Platform

> **⚠️ QUAN TRỌNG**: AI Agent phải đọc file này NGAY ĐẦU mỗi phiên làm việc và cập nhật lại CUỐI mỗi phiên.
> Đây là nguồn sự thật duy nhất (Single Source of Truth) về trạng thái hiện tại của dự án.

---

## 1. Thông Tin Phiên Gần Nhất

- **Thời gian cập nhật**: 2026-09-18 17:15 (UTC+7)
- **Phiên số**: #91 (tính từ đầu dự án)
- **Agent**: AI Senior Full-Stack Architect & Enterprise AI Systems Specialist
- **Mục tiêu đã hoàn thành**:
  1. **Tái Cấu Trúc Phân Rã api-client.ts Thành Modular Domain Services & Facade Pattern (phiên #91)**:
     - Phân rã tệp nguyên khối `frontend/src/services/api-client.ts` từ 2.074 dòng xuống còn 57 dòng.
     - **Tách dữ liệu danh mục tĩnh (`frontend/src/constants/`)**: Chuyển các mảng dữ liệu hành chính NĐ 30 (`administrative-templates.ts`) và cơ sở dữ liệu tra cứu 40 ngành đào tạo ĐH Quy Nhơn (`uis-majors.ts`) ra khỏi tầng API.
     - **Tách kiểu dữ liệu DTO (`frontend/src/types/`)**: Phân loại toàn bộ 38 TypeScript interfaces vào 9 tệp domain types (`common.ts`, `assistants.ts`, `knowledge.ts`, `modelops.ts`, `tools.ts`, `evaluation.ts`, `workflows.ts`, `domain-templates.ts`, `studio-ocr.ts`).
     - **Chia tách Domain API Services (`frontend/src/services/`)**: Tạo các service client độc lập (mỗi file 40 - 250 dòng): `http-client.ts`, `system-api.ts`, `knowledge-api.ts`, `jobs-api.ts`, `modelops-api.ts`, `tools-api.ts`, `evaluation-api.ts`, `workflow-runs-api.ts`, `ocr-studio-api.ts`.
     - **Facade Pattern Zero Breaking Changes**: Giữ lại `api-client.ts` làm Facade entrypoint re-export toàn bộ types, constants và đối tượng composite `apiClient`, bảo đảm toàn bộ 25 components/trang hiện hữu hoạt động nguyên vẹn 100% không đổi cú pháp import.
     - **Verification**: Frontend `npm run lint` 0 lỗi (115 files), `npm run typecheck` 0 lỗi (`tsc --noEmit`), `npm run build` thành công (9.50s); Backend `uv run ruff check .` 0 lỗi, `uv run --extra dev pytest` 27/27 passed; Zero Mojibake 253/253 files (100% sạch).
  1. **Góp Ý Định Hướng Chức Năng Trọng Tâm (phiên #90)**:
     - Tạo tài liệu [`docs/gop_y_dinh_huong_chuc_nang_trong_tam_qnu_ai_platform_2026-09-18.md`](../gop_y_dinh_huong_chuc_nang_trong_tam_qnu_ai_platform_2026-09-18.md).
     - Định vị năm trợ lý hiện tại là **Official Starter Templates**, không phải giới hạn cứng của nền tảng.
     - Chốt thứ tự ưu tiên: RAG Data Integrity → Assistant Runtime Integrity → Golden Assistant Quy chế → Assistant Builder → Auth/RBAC/Tenant → Evaluation/Observability → Workflow nâng cao.
     - Phiên chỉ cập nhật tài liệu, không thay đổi code/schema/runtime.
  1. **Triển Khai Đợt 1: Truthfulness & Real Runtime (phiên #89)**:
     - **RAG Real LLM Answer Synthesis**: Tích hợp `modelops_service.generate()` vào `RagService.ask()` với Zero-Hallucination prompt instruction của ĐH Quy Nhơn, bảo lưu trích dẫn và grounded context fallback.
     - **Sparse Lexical Search**: Hoàn thiện `search_sparse_fts()` trong `retriever.py` qua PostgreSQL FTS (`tsvector`, `plainto_tsquery`, `ts_rank_cd`), kết hợp RRF k=60 với dense vectors.
     - **Real SSE Streaming**: Triển khai endpoint `/assistants/{reference}/chat_stream` và `stream=true` trên `/chat`, phát chuẩn SSE events: `status`, `citation`, `artifact`, `token`, `done`, `error`.
     - **Triệt tiêu Deceptive Mock Fallbacks**: Xóa bỏ `MOCK_ASSISTANT_DATA` và `streamSimulatedText` trong `use-rag-stream.ts`. Xóa bỏ `MOCK_DOCUMENTS`, `MOCK_INGESTION_TASKS`, `MOCK_PROVIDERS`, `MOCK_QUOTA`, `MOCK_TOOLS` trong `api-client.ts`, surface lỗi thật tới người dùng.
     - **Truthful Continuous Evaluation (TM-08)**: Backend `run_evaluation()` gọi trợ lý/RAG thật; `get_summary_metrics()` & `get_gap_inbox()` truy vấn CSDL `evaluation_runs` thật qua `AsyncSession`. Frontend `evaluation-page.tsx` hiển thị bảng lịch sử chạy thật, thanh progress tỷ lệ thật, huy hiệu chuẩn TM-08 và nút chạy Benchmark TM-08.
     - **Verification**: Frontend `npm run lint` 0 lỗi, `npm run typecheck` 0 lỗi, `npm run build` thành công (10.17s); Backend `uv run ruff check .` 0 lỗi, `uv run --extra dev pytest -v` 174/174 passed (100%); Zero Mojibake 231/231 files.
  1. **Đánh Giá Chuyên Sâu Hệ Thống RAG (phiên #88)**:
     - Rà soát Qdrant dense search, PostgreSQL FTS, RRF, reranker, Structured Facts, ModelOps synthesis, cache, citation/no-answer, evaluation và Frontend retrieval UX.
     - Kết luận: RAG ở mức **Internal Beta / RAG Engineering Preview**, điểm đề xuất **5.0/10**; kiến trúc pipeline đạt 6.5–7.0 nhưng data integrity live chỉ 2.5–3.0.
     - Tạo báo cáo [`docs/nhan_xet_rag_hien_tai_2026-09-18.md`](../nhan_xet_rag_hien_tai_2026-09-18.md) với dữ liệu live, scorecard, P0/P1/P2, roadmap và production gate.
     - Phát hiện live: sparse retrieval lấy document pending; 788 Question Bank facts đều orphan; Qdrant canonical `col_question_bank` rỗng còn legacy `col_col_question_bank` có 16/17 points.
     - Verification: RAG Pytest 10/10 pass; Ruff còn 1 import-order error trong test mới của session song song; PostgreSQL/Qdrant read-only audit thành công.
     - Gói ưu tiên tiếp theo: **RAG Data Integrity & Groundedness**.
  1. **Đánh Giá Chuyên Sâu Trợ Lý AI và Quy Trình Workflow (phiên #87)**:
     - Rà soát Assistant Lifecycle 7 lớp, Chat runtime, Workflow Control Plane, compiler, DAG engine, approval, tools, ModelOps, RAG, citation và TM-08.
     - Kết luận: phân hệ ở mức **Internal Beta / Workflow Control Plane Preview**, điểm đề xuất **5.2/10**; UI/control plane đạt 7.0–8.0 nhưng runtime production chỉ 3.5–4.5.
     - Tạo báo cáo [`docs/nhan_xet_tro_ly_ai_va_workflow_2026-09-18.md`](../nhan_xet_tro_ly_ai_va_workflow_2026-09-18.md) với scorecard, đánh giá năm workflow, P0/P1/P2, roadmap và production gate.
     - Rủi ro P0: approval bị bypass; LiveMode còn mock nghiệp vụ; TM-08 mô phỏng; execute/resume không khóa immutable version; tenant/audit identity chưa trusted; tool policy chưa enforce.
     - Gói ưu tiên tiếp theo: **Assistant–Workflow Runtime Integrity** — bỏ auto-approval/mock LiveMode, bind policy xuống runtime, exact-version execution và evaluation thật.
  1. **Đánh Giá Chuyên Sâu Chức Năng Kho Tri Thức (phiên #86)**:
     - Rà soát ingestion, storage, OCR, chunking, facts, human verification, Qdrant indexing, Hybrid Retrieval và Frontend fallback theo hai skill Knowledge/RAG.
     - Kết luận: Kho tri thức ở mức **Internal Beta**, điểm đề xuất **6.0/10**; Document Intelligence/verification đạt khoảng 7.5–8.0 nhưng index/retrieval integrity chỉ khoảng 4.5–5.0.
     - Tạo báo cáo [`docs/nhan_xet_kho_tri_thuc_2026-09-18.md`](../nhan_xet_kho_tri_thuc_2026-09-18.md) với scorecard, P0/P1/P2, roadmap và production acceptance gate.
     - Phát hiện Qdrant drift: `col_col_question_bank` có 16 points, `col_question_bank` có 0 points, `col_drafting` có 6 points.
     - Ưu tiên tiếp theo: state machine `ready/index_failed`, migrate/reconcile Question Bank, chống ghost vector, cấm mock embedding LiveMode và enforce tenant filter.
  1. **Đánh Giá Tổng Thể QNU AI Platform & Hiệu Chỉnh Maturity Status (phiên #85)**:
     - Rà soát source, API live, dữ liệu PostgreSQL, test suite và đối chiếu `qnu-ai-core`.
     - Kết luận chính thức: dự án ở mức **Internal Beta / Engineering Preview**, điểm đề xuất **5.6/10**, chưa production-ready.
     - Tạo báo cáo [`docs/nhan_xet_tong_the_qnu_ai_platform_2026-09-18.md`](../nhan_xet_tong_the_qnu_ai_platform_2026-09-18.md) với scorecard, rủi ro P0/P1, nhận xét từng phân hệ, roadmap và acceptance gate.
     - Rủi ro cao nhất: chưa enforce auth/RBAC/tenant isolation; Evaluation/TM-08 mô phỏng; LiveMode còn mock fallback; RAG chưa gọi LLM synthesis; Assistant model/tool policy chưa bind đầy đủ; DAG chưa có production resilience và exact-version resume.
     - Dữ liệu live: 13 nodes, 5 assistants, 5 workflows, 5 collections, 11 providers; ba collection Admissions/Regulations/Library đang 0 document/0 chunk.
     - Verification: Backend Ruff pass, Pytest 172 passed/17 warnings; Frontend lint/typecheck/build pass; Mojibake 231/231 files sạch; frontend build còn cảnh báo bundle 1.50 MB.
  1. **Redesign Giao Diện Mô Hình Khả Dụng & Hộp Thoại Thêm Model Theo Chuẩn Modern Card Grid & Mac-Style Dialog (phiên #84)**:
     - **Mục tiêu**: Điều chỉnh toàn diện UI/UX khu vực "Mô Hình Khả Dụng" và "Hộp thoại Thêm Mô Hình Tùy Chỉnh" theo 2 hình ảnh tham khảo người dùng cung cấp, tuân thủ 100% OKLCH Academic Teal semantic tokens, chuẩn bo góc 8px/6px và clean code.
     - **Thay đổi kỹ thuật chi tiết**:
       * **Khu vực Mô Hình Khả Dụng (Full-Width Card Grid - Ảnh Mẫu 1)**:
         - Đưa thành Full-Width Card nằm trên khu vực 2 cột Key Pool & Specs.
         - Topbar: Tiêu đề `Bot` icon, badge tổng models, dropdown bộ lọc `all` / `vision` / `reasoning` / `default`, nút `[+ Thêm Model]`, nút `[⚡ Test Tất Cả]`.
         - 3-Column Responsive Grid (`grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3`).
         - Model Card: Icon Robot `Bot` bên trái, Model ID pill font-mono, tên thân thiện tiếng Việt, icons Vision (`Eye`) / Reasoning (`Brain`), huy hiệu mặc định hệ thống (`Embed`, `Rerank`, `OCR`), thanh công cụ mini (🟢 latency ms / 🔴 404 / 🟡 429 badge, nút bình nghiệm `FlaskConical` test đơn lẻ, nút copy `Copy` / `Check`, nút xóa `X`).
         - Dashed Card `[+ Thêm Mô Hình (Add Model)]` tạo CTA trực quan cuối grid.
         - Smart alert banner phát hiện model chết kèm nút `[🧹 Dọn Dẹp Model Lỗi]` 1-click.
       * **Hộp Thoại Thêm Mô Hình Tùy Chỉnh (Add Custom Model Dialog - Ảnh Mẫu 2)**:
         - Mac-style window controls (3 chấm đỏ/vàng/xanh) + Tiêu đề & mô tả.
         - Input Model ID font-mono kèm nút `[🧪 Test]` inline live ping tới provider trước khi lưu.
         - Subtext: `Gửi tới nhà cung cấp dưới dạng: model-id`.
         - Banner hiển thị kết quả kiểm thử trực tiếp (success/error/latency ms).
         - 2 công tắc gạt (Switches) cho **Vision** (Hỗ trợ ảnh & OCR) và **Reasoning** (Suy luận chuyên sâu).
         - 1-Click suggested chips từ preset của provider, tự động gán gợi ý Vision/Reasoning.
       * **Clean Code & Type Safety**:
         - Loại bỏ các biến chết/unused `detailModelInput`, `handleDetailAddModel`, `currentPreset`.
         - Bọc icons Lucide trong thẻ `<span>` để tránh lỗi TS2322 `title` prop.
         - Biome linter check 93 files 0 lỗi, TypeScript typecheck 0 lỗi, Vite build thành công 10.42s, Pytest 15/15 passed (100%), Zero Mojibake 231/231 files.
  2. **Tính Năng Kiểm Thử Hiệu Lực Mô Hình LLM Provider & Dọn Dẹp Model Hết Hỗ Trợ 1-Click (phiên #83)**:
     - **Mục tiêu**: Bổ sung tính năng kiểm thử xem các model hiện tại cấu hình trong Provider còn hiệu lực hoạt động do nhà cung cấp cung cấp hay không, phát hiện model đã bị ngừng cung cấp (deprecated/404) hoặc gặp lỗi cấp quyền/quota.
     - **Thay đổi kỹ thuật chi tiết**:
       * **Backend ModelOps Health Probing**:
         - Schemas `SingleModelTestResult`, `ProviderModelsTestRequest`, `ProviderModelsTestResponse` trong `backend/app/modules/modelops/schemas.py`.
         - Service `_ping_single_model` thực hiện ping thực tế có phân nhánh adapter (Google Gemini `generateContent`, Cloudflare Workers AI `run`, Mistral OCR lookup/completions, OpenAI `chat/completions` / `embeddings`, Docling/SentenceTransformers local).
         - Service `test_provider_models` hỗ trợ chạy song song tối đa 5 model đồng thời bằng `asyncio.Semaphore(5)`.
         - Endpoint `POST /platform/v1alpha1/modelops/providers/{provider_id}/models/test`.
         - Pytest suite `tests/test_modelops.py` (15/15 passed 100%).
       * **Frontend Model Testing UI**:
         - Client method `testProviderModels(providerId, modelName?)` trong `frontend/src/services/api-client.ts`.
         - Trang Chi Tiết Provider (`/models/:id` - `modelops-page.tsx`):
           * Nút `[⚡ Test Tất Cả Models]` trên Header thẻ "Mô Hình Khả Dụng" với loading state.
           * Per-model status tag: chấm tròn & badge trạng thái (🟢 Khả dụng kèm latency ms, 🔴 Không khả dụng 404, 🟡 Cooldown Rate Limit 429).
           * Nút `[▶]` kiểm thử đơn lẻ cho từng model.
           * Smart cleanup alert banner khi phát hiện model chết kèm nút `[🧹 Dọn Dẹp Model Lỗi]` 1-click tự động gỡ bỏ khỏi cấu hình.
       * **Đồng bộ Quy trình**:
         - Cập nhật `docs/quy_trinh/06_modelops_circuit_breaker.md` (Mục 4: Kiểm Thử Hiệu Lực Mô Hình LLM Đa Nhà Cung Cấp).
     - **Kiểm thử đạt chuẩn 100% Zero Error**:
       * Backend Pytest: 15/15 passed (100%).
       * Backend Ruff: All checks passed (0 lỗi).
       * Frontend Lint: Biome checked 93 files (0 lỗi).
       * Frontend Typecheck: `tsc --noEmit` (0 lỗi).
       * Frontend Build: `tsc -b && vite build` built thành công trong 8.94s.
       * Zero Mojibake Audit: 231/231 files UTF-8 sạch 100%.
  2. **Triển Khai Phân Hệ Xuất Văn Bản DOCX/PDF Chuẩn NĐ 30 & Nạp Toàn Văn Nghị Định 30 Vào CSDL Mặc Định (phiên #82)**:
     - **Mục tiêu**: Xây dựng phân hệ tạo và kết xuất văn bản hành chính chuẩn Nghị định 30/2020/NĐ-CP (`docxtpl` + Gotenberg 8 PDF conversion) cho Trợ lý Soạn thảo (`ast_drafting`), cấu hình prompt 3 tầng tương tác tự nhiên, và nạp toàn văn 11 trang NĐ 30 vào PostgreSQL (`col_drafting`) & Qdrant vector index làm Seed Data mặc định của nền tảng.
     - **Thay đổi kỹ thuật chi tiết**:
       * **Bộ mẫu Word `.docx` QNU (`backend/app/templates/documents/`)**:
         - Đã tạo 3 file template chuẩn thể thức NĐ 30: `mau_to_trinh_nd30.docx`, `mau_thong_bao_nd30.docx`, `mau_quyet_dinh_nd30.docx` (phông Times New Roman 13-14pt, căn lề 30-20-20-15mm, Quốc hiệu Tiêu ngữ chuẩn mực sư phạm).
       * **Dịch vụ Document Generator & Tool Endpoint**:
         - Module `document_generator.py`: render `docxtpl` + Gotenberg 8 PDF conversion + graceful fallback to docx + lưu trữ qua `storage_service`.
         - Endpoint `GET /platform/v1alpha1/tools/artifacts/{filename}` và `POST /export/document`.
         - Tool handler `document_exporter.py` trả về `artifacts` có URL tải trực tiếp.
       * **Seed Data Toàn Văn Nghị Định 30/2020/NĐ-CP**:
         - Bóc tách 11 trang NĐ 30 thành 6 Chunks theo Chương/Điều và 7 Facts số hóa (29 loại văn bản hành chính, căn lề A4, phông chữ Unicode TCVN 6909:2001, con dấu 1/3, dấu giáp lai $\le 5$ tờ, bút xanh, hiệu lực 05/03/2020).
         - Tự động nạp vào PostgreSQL `col_drafting` và đánh chỉ mục vector vào Qdrant với UUID5 point IDs.
         - Hook `seed_default_knowledge` vào startup lifespan của FastAPI backend.
       * **Workflow DAG & RAG Pipeline Optimization**:
         - Cập nhật `sample_retrieval` trong `drafting-assistant.v1alpha1.json` trỏ `col_drafting` và `format: docx,pdf`.
         - Loại bỏ `artifact.export` khỏi `_TERMINAL_NODE_TYPES` trong `engine.py` để luồng tiếp tục chảy sang output node.
         - Hỗ trợ cả `query_points` và `search` trong `vector_indexer.py` cho `qdrant-client` hiện đại.
         - Tự động truyền `is_approved=True` trong context chat của `assistant_service.chat`.
       * **Frontend Thẻ Tải File Trực Quan**:
         - `use-rag-stream.ts`, `chat-message.tsx`, `attachment.tsx`: render thẻ tải file `.docx` và `.pdf` riêng biệt, badge loại tệp, dung lượng file và nút download.
     - **Kiểm thử đạt chuẩn 100% Zero Error**:
       * Backend Pytest: 44/44 passed (100%) bao gồm 10 tests `test_document_generator.py`.
       * Backend Ruff: All checks passed (0 lỗi).
       * Frontend Lint: Biome checked 93 files (0 lỗi).
       * Frontend Typecheck: `tsc --noEmit` (0 lỗi).
       * Frontend Build: Vite build thành công (10.35s).
       * Zero Mojibake Audit: 231/231 files UTF-8 sạch 100%.
  2. **Triển Khai Tính Năng AI Agent Auto-Creator (Tự Sinh Agent Trọn Gói) & Nút Viết Hộ Prompt (phiên #81)**:
     - **Mục tiêu**: Hiện thực hóa tính năng AI Tự Sinh Agent từ một câu ý tưởng tự nhiên và nút Viết Hộ Prompt chuẩn phong thái học thuật ĐH Quy Nhơn (Zero Hallucination, Hotline 0256.3846.156).
     - **Thay đổi kỹ thuật chi tiết**:
       * **Backend Endpoint `POST /platform/v1alpha1/assistants/generate`**:
         - Schemas `AssistantGenerateRequest` & `AssistantGenerateResponse` trong `backend/app/modules/assistants/schemas.py`.
         - Service `generate_spec` kết nối ModelOps LLM generation và cơ chế dự phòng `_build_fallback_spec` tự động nhận diện từ khóa tiếng Việt chuẩn xác (Tuyển sinh, Quy chế, Soạn thảo NĐ 30, Khảo thí Bloom, Thư viện, Ký túc xá).
         - Router endpoint `POST /generate` trong `backend/app/modules/assistants/router.py`.
         - Unit test `test_api_generate_assistant_spec` trong `backend/tests/test_assistants.py`.
       * **Frontend UI Agent Auto-Creator & Prompt Writer**:
         - Client API `generateAssistantSpec(idea, categoryHint)` trong `frontend/src/services/assistants-api.ts`.
         - Trang Tạo Mới (`/assistants/new` - `assistant-create-page.tsx`): Thêm Card "AI Tự Sinh Agent Trọn Gói" với input ý tưởng, nút **[✨ Tự Sinh Agent]**, 4 chip gợi ý nhanh, tự sinh mã slug không dấu chuẩn Unicode, tự điền trọn bộ thông số form; nút **[✨ Viết hộ tôi]** trên ô System Prompt.
         - Trang Chi Tiết (`/assistants/:id` - `assistant-detail-page.tsx`): Bổ sung nút **[✨ Viết hộ tôi]** cạnh ô System Prompt để tối ưu hoặc viết lại prompt bất kỳ lúc nào.
     - **Kiểm thử đạt chuẩn 100% Zero Error**:
       * Backend Pytest: `uv run --extra dev pytest tests/test_assistants.py -v` — 9/9 passed (100%).
       * Backend Ruff: `uv run ruff check .` — All checks passed (0 lỗi).
       * Frontend Lint: `npm run lint` — Checked 93 files in 128ms (0 lỗi).
       * Frontend Typecheck: `npm run typecheck` — `tsc --noEmit` (0 lỗi).
       * Frontend Build: `npm run build` — Vite v6.4.3 built thành công trong 7.92s.
       * Zero Mojibake Audit: `python scripts/check_mojibake.py` — 227/227 files UTF-8 sạch 100%.
       * Browser Subagent E2E: Đã kiểm tra trực quan, tạo video recording `assistant_auto_creator_demo_1789700749600.webp` và 5 ảnh chụp màn hình minh chứng.
  2. **Nâng Cấp Toàn Diện UI/UX Phân Hệ Quy Trình Workflow DAG Thành Enterprise Control Center (phiên #80)**:
     - **Mục tiêu**: Xử lý triệt để lỗi visual collision trên thanh công cụ DAG Studio (nơi 5 tabs dài chen chúc làm wrap chữ thành cột xanh lá cây che phủ icon) và hoàn thiện chuẩn Master-Detail Deep Routing qua trang danh mục `/workflows`.
     - **Thay đổi kỹ thuật chi tiết**:
       * **Tạo mới Trang Danh Mục Quy Trình (`/workflows` - `workflows-page.tsx`)**:
         - Thanh KPI Metrics Strip: Tổng quy trình (5 chuẩn QNU), Đang phục vụ (100% active v1.0.0), Độ phức tạp DAG (nodes/edges trung bình), Chuẩn kiểm định Ragas TM-08.
         - Tìm kiếm thời gian thực và bộ lọc theo 5 lĩnh vực chuyên môn (Tuyển sinh, Quy chế, Thư viện, Soạn thảo NĐ 30, Khảo thí Bloom).
         - 5 thẻ `WorkflowCard` hiện đại hiển thị chi tiết kiến trúc DAG, Trợ lý AI liên kết và 3 nút tác vụ: **[Mở DAG Studio]**, **[Thử nghiệm]**, **[Lịch sử]**.
         - Tích hợp `WorkflowVersionHistoryDialog` hỗ trợ xem lịch sử và khôi phục rollback phiên bản ngay tại trang danh mục.
       * **Đại Tu Thanh Header DAG Canvas Studio (`/workflows/:id` & `/canvas`)**:
         - Triệt tiêu hoàn toàn lỗi vỡ layout: Thay thế dãy 5 tabs nút bấm bằng **Workflow Switcher Dropdown** `<Select>` tinh gọn, hiển thị icon chuyên môn và tên quy trình cùng dirty badge indicator.
         - Bổ sung nút quay lại (`<ArrowLeft>`) điều hướng mượt mà về `/workflows`.
         - Tái cấu trúc toolbar thành 3 cụm khoa học: Cụm Biên soạn (`+ Thêm node`, `Chạy thử`, `Lưu nháp`), Cụm Control Plane (`Kiểm tra`, `Xuất bản`, `Lịch sử`), và Cụm Tiện ích (`Sao chép link`, `Sao chép JSON`, `Tải lại`, `Studio Chat`).
       * **Đồng Bộ Menu Sidebar & Routing**:
         - Thêm mục *"Quy Trình Workflow DAG"* (`/workflows`, icon `Workflow`, badge `5 DAGs`) vào Sidebar mục *Kho Tri Thức & Quy Trình*.
         - Đăng ký route `/workflows` trong `App.tsx` trỏ tới `WorkflowsPage`.
     - **Kiểm thử đạt chuẩn 100% Zero Error**:
       * Frontend Lint: `npm run lint` — Checked 93 files in 130ms (0 lỗi).
       * Frontend Typecheck: `npm run typecheck` — `tsc --noEmit` (0 lỗi).
       * Frontend Build: `npm run build` — Vite build thành công (8.17s, `dist/` bundle sạch).
       * Backend Pytest: `uv run --extra dev pytest tests/test_workflows.py -v` — 18/18 tests passed (100%).
       * Backend Ruff: `uv run ruff check .` — All checks passed (0 lỗi).
       * Zero Mojibake Audit: `python scripts/check_mojibake.py` — 227/227 files UTF-8 sạch 100%.
       * Browser E2E Test: Đã xác thực giao diện qua browser subagent, lưu 3 ảnh chụp màn hình và video recording `workflows_ui_demo_1789699203962.webp`.
  2. **Nâng Cấp Toàn Diện UI/UX Phân Hệ Trợ Lý AI Thành Enterprise AI Assistant Control Center (phiên #79)**:
     - **Mục tiêu**: Chuyển đổi toàn diện giao diện quản trị Trợ lý AI (`/assistants`, `/assistants/:id`, `/assistants/new`) từ các ô nhập văn bản thô (free-text inputs) sang trải nghiệm Trung tâm Điều hành Cấp Doanh nghiệp (Enterprise AI Assistant Control Center) kết nối dữ liệu thật từ Backend APIs.
     - **Thay đổi kỹ thuật chi tiết**:
       * **Thanh KPI Metrics Strip thời gian thực**: Tự động tính toán tổng số lượt hội thoại (`totalRuns`), độ trễ trung bình (`avgLatency` ms), tên và số lượng tài liệu trong Kho tri thức RAG (`docCount`), và trạng thái đạt chuẩn TM-08.
       * **Ràng Buộc Tri Thức & Quy Trình Động (Dynamic Select Gateway)**:
         - Thay thế ô input text `collection_id` bằng dropdown `<Select>` kết nối trực tiếp `apiClient.getCollections()`, hiển thị tên bộ sưu tập và số lượng tài liệu kèm nút "Mở chi tiết kho tri thức" (`/knowledge/:id`).
         - Thay thế ô input text `workflow_id` bằng dropdown `<Select>` kết nối `workflowsApi.listDefinitions()`, hiển thị tên quy trình DAG kèm nút "Mở đồ thị DAG Studio" (`/workflows/:id`).
       * **ModelOps & Mô Hình Kép**: Dropdown chọn lọc `primary_model` và `fallback_model` từ danh mục mô hình chuẩn có chú thích hiệu năng, kèm thanh trượt `temperature` (0.0 - 1.0) và giới hạn `max_tokens`.
       * **Trung Tâm Kiểm Soát An Toàn 6 Công Tắc (Interactive Guardrails Switch Center)**:
         - Thay thế 6 badge tĩnh bằng 6 thẻ điều khiển có `<Switch>` tương tác hai chiều, liên kết trực tiếp vào `config.guardrails` (Prompt Injection, Mask PII, Require Grounded Answer, Protect System Prompt), `config.tools` (Human Approval HITL), và `config.output_policy` (Require Citations).
       * **Quản Lý Câu Hỏi Gợi Ý Tương Tác (Editable Sample Questions List)**:
         - Danh sách câu hỏi mẫu đánh số thứ tự với cấu trúc Object độc lập `{ id, text }`, cho phép thêm mới, chỉnh sửa trực tiếp và xóa từng câu hỏi. Triệt tiêu hoàn toàn cảnh báo Biome `noArrayIndexKey`.
       * **Bảng Kiểm Toán Chuẩn Ragas TM-08**:
         - Hiển thị 3 chỉ số Ragas TM-08 (Faithfulness $\ge 0.90$, Answer Relevance $\ge 0.85$, Context Precision $\ge 0.80$), ô chỉnh sửa `no_answer_message` dự phòng khi thiếu căn cứ, và nút liên kết nhanh sang `/evaluation`.
       * **Quản Lý Vòng Đời Vùng Nguy Hiểm & Kích Hoạt Lại (Reactivate Assistant)**:
         - Bổ sung hàm `activateAssistant(reference)` trong `frontend/src/services/assistants-api.ts`.
         - Nút kép thông minh: "Vô hiệu hóa trợ lý" (khi đang hoạt động) và "Kích hoạt lại trợ lý" (khi đã bị vô hiệu hóa), gửi `PATCH /assistants/:id` với `{ is_active: true }` để kích hoạt lại tức thì.
       * **Trang Danh Sách (`/assistants`) & Tạo Mới (`/assistants/new`)**:
         - Cập nhật `AssistantCard` với 3 nút tác vụ nhanh (`Thử chat`, `Mở DAG`, `Cấu hình`), huy hiệu chuẩn TM-08, bộ lọc trạng thái (`Tất cả`, `Đang hoạt động`, `Đã tạm dừng`), và đồng bộ hóa thông báo bằng `toast` (Sonner).
     - **Kiểm thử đạt chuẩn 100% Zero Error**:
       * Frontend Lint: `npm run lint` — Checked 92 files (0 lỗi).
       * Frontend Typecheck: `npm run typecheck` — `tsc --noEmit` (0 lỗi).
       * Frontend Build: `npm run build` — Vite build thành công (8.34s, `dist/` bundle sạch).
       * Backend Pytest: `uv run --extra dev pytest tests/test_assistants.py -v` — 8/8 tests passed (100%).
       * Backend Ruff: `uv run ruff check .` — All checks passed (0 lỗi).
       * Zero Mojibake Audit: `python scripts/check_mojibake.py` — 226/226 files UTF-8 sạch 100%.
       * Browser E2E Test: Đã xác thực giao diện qua browser subagent và lưu video/screenshot tại artifacts.
  2. **Triển Khai Hoàn Tất 100% Toàn Bộ 5 Đợt Kế Hoạch 04 — Hoàn Thiện Hệ Sinh Thái Trợ Lý AI & DAG Control Plane (phiên #78)**:
     - **Mục tiêu**: Hiện thực hóa 100% [Kế hoạch 04](file:///d:/DuAnPhanMem/qnu-ai-platform/docs/ke_hoach/04_ke_hoach_hoan_thien_tro_ly_ai_dag.md), xóa bỏ hoàn toàn dữ liệu giả, nâng cấp DAG Canvas và Trợ lý AI thành Workflow Control Plane cấp Enterprise với bảo vệ chống bịa đặt (Anti-Hallucination), cổng kiểm định chất lượng TM-08 và điều hướng sâu (Deep Linking).
     - **Thay đổi kỹ thuật chi tiết theo 5 Đợt**:
       * **Đợt 0 & 1 (Assistant Binding & Snapshot bất biến)**: `AssistantRuntimeProfile` snapshot cho từng lượt chạy; RAG & LLM nodes tôn trọng profile; Input/Output guardrails; loại bỏ toàn bộ fallback mock.
       * **Đợt 2 (Workflow Control Plane)**: Module `workflows` 4 files chuẩn Clean Architecture (`models.py`, `schemas.py`, `service.py`, `router.py`); API Draft/Validate/Publish/Rollback; Compiler graph validation; optimistic locking `expected_revision`.
       * **Đợt 3 (DAG Engine Production)**: Ready-set topological scheduler; condition branching với regex tiếng Việt an toàn; fan-out/fan-in synchronization; deadlock detection; durable checkpoint PostgreSQL; human approval token & resume; Tool gateway schema & permission validation.
       * **Đợt 4 (Trải nghiệm vận hành & Deep Link)**: In-Canvas Test Runner nhận trace thật; Node Catalog Drawer; Version History Dialog khôi phục bản nháp; Dirty state tracking; Deep link `/runs/:runId` (mở modal timeline checkpoint & copy link) và `/workflows/:id` (đồng bộ tab workflow trên DAG Studio & copy link).
       * **Đợt 5 (Quality Gate TM-08 & Anti-Hallucination)**: `compiler.py` bắt buộc có node thẩm định trích dẫn hoặc fallback (`workflow_rag_missing_citation_guard`) khi dùng RAG; `service.py` kiểm tra kết quả `EvaluationRun` mới nhất trước khi publish (`workflow_quality_gate_failed`).
     - **Kiểm thử đạt chuẩn 100% Zero Error**:
       * Backend Pytest: 18/18 tests passed (`tests/test_workflows.py`) bao gồm cycle, deadlock, fan-out/fan-in, human approval, compiler citation guard và TM-08 quality gate.
       * Backend Ruff: All checks passed (0 lỗi).
       * Frontend Biome: Checked 92 files (0 lỗi).
       * Frontend Typecheck: `tsc --noEmit` (0 lỗi).
       * Frontend Build: Vite build thành công (8.10s, `dist/` bundle sạch).
       * Zero Mojibake Audit: 226/226 files UTF-8 sạch 100%.
  2. **Xử Lý Triệt Để Lỗi Chuẩn Hóa PDF Scan & Loại Bỏ Hoàn Toàn Text Giả Lập (phiên #77)**:
     - **Vấn đề**: Người dùng kiểm tra tệp PDF scan 9 trang (`4740-qd-bgddt-bo-chi-so-cds-dai-hoc.pdf`, QĐ 4740 BGDĐT), Document Verification Studio hiển thị toàn bộ văn bản giả lập (`### Tiêu đề đầu trang`, `## Tên loại văn bản / Trích yếu nội dung`, `Đoạn văn bản quy định`, `Bảng biểu số liệu`, `Con dấu & Chữ ký xác thực`), mất 100% nội dung thật.
     - **Nguyên nhân gốc rễ**:
       * `layout_detector.py` (dòng 965..990, 295, 193) gán chuỗi mô tả tiếng Việt vào thuộc tính `text` của box thay vì để rỗng.
       * `chunker.py` không parse ranh giới `<!-- Trang X -->`, gán `page_number = None` cho cả 9 chunks.
       * `service.py` kích hoạt `is_clumped = True` giả mạo, vứt bỏ toàn bộ chunks thật để thay bằng `_synthesize_page_markdown_from_blocks` chứa text giả lập.
       * `mistral_adapter.py` truyền `page.get_text()` rỗng vào Layout Detector thay vì text OCR thật.
     - **Giải pháp triệt để**:
       * `layout_detector.py`: Gỡ bỏ 100% text giả lập khỏi `raw_boxes`, `tables`, `stamps`. Khi không có text OCR, `text = ""` và `content_snippet = ""`.
       * `chunker.py`: Tự động parse `_RE_PAGE_MARKER` để gán chính xác `page_number` cho từng chunk (1 đến 9).
       * `mistral_adapter.py`: Truyền markdown THẬT từ Mistral OCR của từng trang vào `SmartLayoutDetector`.
       * `service.py`: Lưu `page_markdowns` vào `doc_metadata`, ưu tiên dùng trong `build_studio_pages`, lọc sạch `_SYNTHESIS_PLACEHOLDERS`, và kích hoạt **Auto-Rescue** trong `get_studio_view` khi tài liệu có 0 chunks hoặc khi người dùng bấm `[Quét lại]`.
       * Reprocess CSDL: Nạp đầy đủ **9 chunks thật (14.194 ký tự)** của QĐ 4740 vào PostgreSQL.
     - **Kiểm thử**:
       * Backend Pytest: 44/44 passed (100%) trong 46.65s (bổ sung 2 test case mới).
       * Backend Ruff: 0 error.
       * Zero Mojibake Audit: 225/225 files sạch (100%).
       * Frontend: Biome 0 lỗi, TypeScript 0 lỗi, Vite build thành công (12.04s).
  2. **Tối Giản Toàn Diện Màn Hình Đối Soát Document Verification Studio — Pure Markdown (Phương Án 1 - phiên #76)**:
     - **Yêu cầu người dùng**: Bỏ các tab gây thừa thãi ("Văn bản", "Markdown", "Bố cục & Khối"); chỉ tập trung vào một đích duy nhất: dữ liệu chuẩn hóa Markdown sạch để nạp vào Vector DB hoặc xuất file .md.
     - **Giải pháp**:
       * Thay thế 3 tab cũ bằng **Right Toolbar tối giản**:
         - Scope Switcher: `[Trang hiện tại (Trang X)]` vs `[Toàn bộ file (N trang)]` dùng `<Tabs>` semantic.
         - Toggle Chế độ xem: `[Xem render]` vs `[Mã nguồn .md]` (icon `Code`/`Eye`).
         - Công cụ hành động: `[✏️ Sửa tay]` (kèm `[Xem trước]`, `[Lưu sửa]`, `[Hủy]`), `[Sao chép]`, `[Tải file .md]`.
       * Dọn dẹp sạch mã chết (Boy Scout Rule 8.1 & 8.2): Gỡ bỏ import `Layers`, `RegionsInspector` và `allRegions` useMemo.
       * Cả 2 scope (`page` và `all`) đều hỗ trợ chuyển đổi linh hoạt giữa xem render GFM và xem mã nguồn thô trong thẻ `<pre>`.
       * Footer stats đồng bộ tự động theo scope (`từ • dòng` khi ở trang đơn, `ký tự • trang` khi ở toàn bộ file).
     - **Kiểm thử**: Biome lint 0 lỗi (91 files), TypeScript 0 lỗi (`tsc --noEmit`), Vite build thành công (9.72s), Zero Mojibake 225/225 files sạch.
  2. **Sửa Triệt Để Lỗi Chuẩn Hóa Markdown Bị Mất Bảng Biểu & Scan Không Nhận Diện Bảng — Kế Thừa QNU-AI-Core (phiên #75)**:
     - **Vấn đề**: Người dùng tải tệp (đặc biệt là tệp DOCX tuyển sinh 14 trang `Thong tin tuyen sinh dai hoc 2026_Lan2-1 (1).docx`), toàn bộ các bảng biểu biểu mẫu tuyển sinh từ trang 2 đến trang 13 bị biến thành chuỗi chữ giữ chỗ `Bảng biểu dữ liệu số hóa` thay vì trích xuất thành bảng Markdown (`| STT | Mã xét tuyển | ... |`), khung scan nhận diện bảng không sinh ra bảng Markdown tương ứng.
     - **Nguyên nhân gốc rễ**:
       * `layout_detector.py` (dòng 295, 405) gán cứng `"text": "Bảng biểu dữ liệu số hóa"` và loại bỏ toàn bộ text con trong bảng, không gọi `tab.extract()`.
       * `DocxParser` trong `office_parser.py` duyệt văn bản trước rồi dồn bảng xuống cuối tệp, trả về `page_count = 1` khiến chunks bị dồn về trang 1 (`is_clumped = True`).
       * Trong `service.py`, `_synthesize_page_markdown_from_blocks` lấy text từ block của trang, dẫn đến toàn bộ nội dung từ trang 2 đến trang 13 biến thành dòng chữ giữ chỗ vô nghĩa.
     - **Giải pháp bám sát `qnu-ai-core`**:
       * `layout_detector.py`: Bổ sung `_format_table_markdown(rows)`. Khi `find_tables()` phát hiện bảng, gọi `tab.extract()` chuyển đổi thành Markdown table thực sự. Gán bảng Markdown này vào `table["text"]` và `content_snippet`. Triệt tiêu hoàn toàn chuỗi placeholder.
       * `office_parser.py`: Nâng cấp toàn diện `DocxParser` theo chuẩn `docx_processor.py` của `qnu-ai-core`: duyệt tuần tự `child in doc.element.body`, chuẩn hóa Quốc hiệu/Tiêu ngữ/Số hiệu NĐ 30, tách hàng La Mã thành tiêu đề, xử lý colspan và ngắt dòng trong ô `<br>`/`;`, cân bằng số cột.
       * `cleaner.py`: Bổ sung Unicode NFC (Zero Mojibake), chuẩn hóa cấu trúc bảng Markdown (`_normalize_markdown_table_block`), nối bảng qua trang (`_stitch_table_continuations`), làm sạch số trang đơn độc.
       * `service.py`: Cập nhật `_synthesize_page_markdown_from_blocks` giữ nguyên bảng Markdown, bổ sung phát hiện `has_placeholder` trong `_is_stale_raw_blocks` để tự động re-extract dữ liệu cũ, lưu `text` đầy đủ cho từng block trong `_ensure_page_blocks`.
       * `blocks.py`: Bổ sung `_format_table_markdown` và cập nhật `extract_page_blocks` trích xuất bảng Markdown từ PDF vector tables.
       * `verification-data.ts`: Dọn dẹp sạch 12 vị trí chứa chuỗi `"Bảng biểu dữ liệu số hóa"` trong mock fixture.
     - **Kiểm thử**:
       * Parse thực tế tệp DOCX tuyển sinh: 23.118 ký tự, 4 bảng lớn, đầy đủ 53 ngành tuyển sinh và tổ hợp môn, 0 placeholder.
       * Pytest: `test_knowledge_docx_tables.py` (3/3 passed), `test_smart_layout.py` (4/4 passed), `test_knowledge.py` (25/25 passed).
       * Ruff: 0 lỗi. Biome: 0 lỗi. TypeScript: 0 lỗi. Vite build: thành công. Zero Mojibake: 225/225 files sạch.
  2. **Sửa Lỗi OCR Bounding Box Nát Bét Trên PDF — Loại Bỏ Khối Giả Lập, Tích Hợp SmartLayoutDetector (phiên #74)**:
     - **Vấn đề**: Upload file PDF (`4740-qd-bgddt-bo-chi-so-cds-dai-hoc.pdf`) vào Kho Tri Thức, Document Verification Studio hiển thị khu nhận diện OCR (bounding box overlay) nát bét: các khối ngang chồng chéo (x=8.0, width=84.0) với badge chứa 40 ký tự markdown thô (`**bộ giáo dục**`, `# **quyết định**`). Trên trang landscape (bảng biểu), dải sọc cắt ngang hoàn toàn lệch.
     - **Nguyên nhân gốc rễ**: `MistralOCRAdapter` tạo blocks giả lập (mỗi dòng markdown = 1 khối ngang). `_is_stale_raw_blocks` chấp nhận khối giả (vì type `title`/`header` tồn tại) nên không kích hoạt SmartLayoutDetector. Frontend render `{box.label}` verbatim.
     - **Giải pháp**: (1) `mistral_adapter.py`: Thay vòng lặp giả bằng `SmartLayoutDetector` thực (PyMuPDF hybrid + OpenCV), trả `blocks=[]` nếu detector thất bại. (2) `knowledge/service.py`: Phát hiện synthetic blocks (`x≈8.0, width≈84.0` hoặc markdown `**`/`#` trong label) → auto re-extract. (3) `document-bounding-visualizer.tsx`: `REGION_BADGE_LABELS` map + `getDisplayBadge` + max-width 120px ellipsis.
     - **Kiểm thử**: Pytest 143/143 passed, Ruff 0 lỗi, Biome 0 lỗi, TypeScript 0 lỗi, Vite build thành công.
  2. **Khắc Phục Lưu API Key Provider & Xử Lý Tính Đặc Thù Của Từng Provider (Cloudflare, Mistral, Gemini, OpenAI) (phiên #73)**:
     - **Vấn đề**: Người dùng thêm API key vào Mistral trong Quản lý Provider (`/models`) nhưng không được lưu lại. Ngoài ra, cấu trúc API của Cloudflare Workers AI khác biệt (yêu cầu `account_id` trong URL), cần nghiên cứu tính đặc thù của từng provider.
     - **Nguyên nhân gốc rễ**:
       * Bảng `model_provider_configs` lưu `api_keys` trong cột `extra_config` (`JSONB`). Khi sửa đổi mảng con `extra["api_keys"]`, SQLAlchemy không phát hiện thay đổi nếu thiếu `flag_modified(config, "extra_config")`. Vì vậy `await db.commit()` âm thầm bỏ qua câu lệnh `UPDATE`!
       * Thiếu cơ chế đồng bộ hóa tức thì (In-memory Live Sync) giữa cấu hình DB và các runtime services (`settings.MISTRAL_API_KEY`, `settings.CLOUDFLARE_API_TOKEN`, `settings.CLOUDFLARE_ACCOUNT_ID`), khiến OCR hoặc RAG không nhận được key mới nếu chưa restart backend.
     - **Giải pháp**:
       * Bổ sung `flag_modified(config, "extra_config")` cho toàn bộ các thao tác Key Pool: `add_provider_key`, `update_provider`, `update_provider_key`, `delete_provider_key`, `simulate_key_rotation`.
       * Triển khai hàm `_sync_runtime_credentials`: tự động tiêm key và account_id vào `settings` ngay khi tạo/sửa/xóa key hoặc khi load danh sách provider lúc khởi động.
       * Xử lý tính đặc thù của từng Provider:
         - **Cloudflare Workers AI**: Hỗ trợ trường `account_id`, URL `https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/run`, endpoint xác thực `/accounts/{account_id}/ai/models/search`.
         - **Mistral AI**: Endpoint xác thực `/v1/models`, model OCR `mistral-ocr-latest`.
         - **Google Gemini**: Xác thực qua `?key=` hoặc header `x-goog-api-key`.
         - **OpenAI / DeepSeek / Groq / OpenRouter / NVIDIA**: Xác thực chuẩn Bearer token và endpoint `/v1/models`.
       * Triển khai kiểm tra kết nối thật (Real HTTP Verification) trong `test_provider` và `test_provider_key` thay cho số liệu giả lập.
     - **Kiểm thử**:
       * Pytest: 143/143 passed (100% pass toàn bộ test suite dự án).
       * Ruff: 0 lỗi.
       * Frontend: Biome 0 lỗi, TypeScript 0 lỗi, Vite build thành công (`dist/` bundle).
  2. **Tích Hợp Mistral OCR & Cơ Chế Điều Phối Bóc Tách Đa Tầng Core → Platform (phiên #72)**:
     - **Vấn đề**: Người dùng upload tệp PDF dạng scan (`4740-qd-bgddt-bo-chi-so-cds-dai-hoc.pdf`), Platform kích hoạt Docling TableFormer trên CPU tải trọng 770MB weights Heron Object Detection và chạy suy luận mất hàng chục giây.
     - **Giải pháp bóc tách chuẩn Core**:
       * Tạo `MistralOCRAdapter` (`backend/app/modules/ocr/adapters/mistral_adapter.py`) gọi Mistral OCR API (`POST https://api.mistral.ai/v1/ocr`, model `mistral-ocr-latest`), trả về markdown, pages và bounding boxes studio. Kiểm tra tính sẵn sàng trung thực qua `settings.MISTRAL_API_KEY`.
       * Triển khai cơ chế phân định thông minh (Smart Extension-based Routing):
         - File Word/Excel (`.docx`, `.doc`, `.xlsx`, `.xls`): Ưu tiên `Docling TableFormer` / `openpyxl` bảo toàn 100% ma trận bảng.
         - File PDF: Trích xuất nhanh văn bản số hóa qua PyMuPDF fast-path (10-30ms); nếu là bản scan (văn bản <40 ký tự) $\rightarrow$ chuyển cứu hộ Mistral OCR (Cloud API 1-2s).
         - Graceful Local Fallback: Nếu không cấu hình `MISTRAL_API_KEY` hoặc lỗi mạng, tự động rơi về Local OCR (`easyocr` / `docling` / `pymupdf_ocr`) với `fallback_triggered=True`.
         - File ảnh (`.png`, `.jpg`,...): Ưu tiên Mistral OCR, fallback Local OCR.
       * Sửa lỗi buffer 1D trong `easyocr_adapter.py`: truyền trực tiếp `image_bytes` vào `reader.readtext`.
       * Frontend: Cập nhật `file-inspector.ts` và `document-ingest-page.tsx` với đề xuất `Fast-path + Mistral OCR` và option `mistral: "mistral_ocr"`.
     - **Kiểm thử**:
       * Backend: `uv run ruff check .` (0 lỗi), `pytest tests/test_ocr.py` (13/13 passed 100%), `pytest tests/test_knowledge.py` (25/25 passed 100%).
       * Frontend: `npm run lint` (0 lỗi trên 90 files), `npm run typecheck` (0 lỗi), `npm run build` (thành công trong 15.95s).
  2. **Đồng Bộ Quản Trị Trợ Lý AI Core → Platform Bằng Dữ Liệu Thật (phiên #71)**:
     - Xác định bảng `assistants` ban đầu rỗng; API cũ che giấu tình trạng này bằng 5 bản ghi fallback trong bộ nhớ và trang `/assistants` tiếp tục hiển thị hằng số frontend.
     - Tạo seed idempotent 5 trợ lý + 5 `WorkflowDefinition` từ `configs/workflows`, không ghi đè cấu hình người dùng và không chạm Provider/ModelOps.
     - Chuẩn hóa cấu hình vòng đời 7 lớp: Persona/Scope, Knowledge, Model/Fallback, Guardrails, Tools/HITL, Output/Citations và Evaluation TM-08.
     - Hoàn thiện API list/detail/create/update/deactivate, templates, seed-defaults, import/export bundle; lỗi DB được phản ánh trung thực, không fallback mock.
     - Thay trang tĩnh bằng `/assistants`, `/assistants/new`, `/assistants/:code` dùng TanStack Query, có loading/error/empty, tìm kiếm/lọc, seed, import/export và liên kết Chat/DAG đúng trợ lý.
     - Đã nạp và xác minh PostgreSQL có 5 bản ghi thật; API list/detail/templates trả HTTP 200; kiểm tra trực quan ba route trên trình duyệt thành công.
     - **Kiểm thử**: Assistants 7/7 passed, Ruff 0 lỗi; frontend Biome 0 lỗi, TypeScript 0 lỗi, Vite build thành công. Toàn bộ backend đạt 141/142; 1 lỗi ngoài phạm vi ở OCR concurrent (`OCRExtractResponse.fallback_engine`).
  1. **Khắc Phục Lỗi TypeError `document_type_code` & Hoàn Thiện Studio Page Builder (phiên #70)**:
     - **Hiện tượng**: Tải lên tệp tin `7.1.6 Kế hoạch triển khai 2 phần mềm của Nhà trường.docx` qua Studio Nạp Kho Tri thức bị lỗi `Tải lên thất bại (HTTP 500). Vui lòng thử lại.` Do Backend trả `TypeError: KnowledgeService.list_documents() got an unexpected keyword argument 'document_type_code'` và `KnowledgeService.ingest_document()`.
     - **Nguyên nhân**: `KnowledgeService` bị thiếu tham số `document_type_code` do quá trình revert trước đó.
     - **Giải pháp**:
       * Import `document_types_service` và bổ sung `document_type_code: str | None = None` vào `KnowledgeService.list_documents` (kèm query filter `where(KnowledgeDocument.document_type_code == document_type_code)`).
       * Bổ sung `document_type_code: str | None = None` vào `KnowledgeService.ingest_document`, xác thực active code với `document_types_service.validate_active_code`, gán vào `KnowledgeDocument.document_type_code` và lưu `document_type_source`.
       * Bổ sung tham số `page_markdowns` và helper `_synthesize_page_markdown_from_blocks` trong `build_studio_pages` để bảo toàn nội dung từng trang khi chunks bị dồn.
     - **Kiểm thử**: `uv run ruff check .` (0 lỗi), `uv run --extra dev pytest tests/test_knowledge.py tests/test_document_types.py tests/test_jobs.py` (47/47 passed 100%), Endpoint `GET /platform/v1alpha1/knowledge/documents` phản hồi `HTTP 200 OK`.
  2. **Đồng Bộ Lịch Sử Tác Vụ (`JobRecord`) Cho Luồng Nạp Tài Liệu Kho Tri Thức (phiên #69)**:
     - **Hiện tượng**: Người dùng nạp tệp thành công vào CSDL (hiển thị 1 tài liệu hiệu lực 16 chunks), nhưng tab "Tiến trình & Lịch sử Tác vụ (0)" trống không có tác vụ nào.
     - **Bản chất kỹ thuật**:
       * Luồng nạp qua Studio chạy đồng bộ trực tiếp (Human-in-the-loop Ingestion) để trả kết quả bóc tách tức thì (<1s) cho người dùng đối soát mắt, không đẩy qua hàng đợi Redis/ARQ.
       * Tab "Tiến trình & Lịch sử Tác vụ" gọi `GET /jobs?limit=50` từ bảng `job_records` (trước đây chỉ ghi khi người dùng bấm Reindex hoặc chạy worker task ngầm).
     - **Giải pháp**:
       * Cập nhật `ingest_document` và `approve_document` trong `knowledge/service.py` để tự động ghi nhận bản ghi `JobRecord(job_type="ingestion", status="completed", progress=100.0)` kèm metadata (tên tệp, dung lượng, OCR engine, chunks).
       * Bổ sung `sync_ingestion_job_records` trong lifespan startup để tự động hồi tố lịch sử cho các tài liệu đang có trong kho.
       * Đã tạo thành công bản ghi tác vụ cho `Thong tin tuyen sinh dai hoc 2026_Lan2-1 (1).docx` trong CSDL.
     - **Kiểm thử**: `test_jobs.py` pass 15/15 (100%), Ruff 0 lỗi, Biome 0 lỗi, TypeScript 0 lỗi.
  2. **Tự Động Hóa 100% Loại Văn Bản (Taxonomy) Cho Trang Nạp Tài Liệu Kho Tri Thức (phiên #68)**:
     - **Yêu cầu người dùng**: Sau khi trải nghiệm tính năng auto cấu hình ban đầu, người dùng phản hồi cần tự động chọn luôn "Loại văn bản" (đặc biệt khi upload file tuyển sinh như `Thong tin tuyen sinh dai hoc 2026_Lan2-1 (1).docx` không bị rơi vào "Chọn loại văn bản" / "Chưa xác định").
     - **Giải pháp toàn diện**:
       * Nâng cấp `frontend/src/lib/file-inspector.ts`:
         - Bổ sung nhận diện từ khóa tuyển sinh / đề án (`/(?:de\s*an|tuyen\s*sinh|thong\s*tin\s*tuyen\s*sinh)/` -> `de_an`).
         - Cung cấp cơ chế dự phòng thông minh theo ngữ cảnh Kho Tri Thức đa hình (`collectionContext`: id, name, code) -> tự động gán loại văn bản đặc thù cho từng kho (`col_admissions` -> `de_an`, `col_regulations` -> `quy_che`, `col_library` -> `giao_trinh`, `col_question_bank` -> `de_cuong_mon_hoc`, `col_drafting` -> `cong_van`).
         - Đồng bộ `getPriorityForDocumentType`: phân cấp chuẩn xác `de_an` vào `standardTypes` (Điểm 8/10, Tiêu chuẩn x50) theo đúng catalog backend NĐ 30.
       * Cải tiến `frontend/src/pages/document-ingest-page.tsx`:
         - Tách hàm `processFile(f: File)` dùng chung cho cả sự kiện click duyệt chọn file và kéo thả file (`onDrop` / `onDragOver`).
         - Bổ sung `useEffect` tự động gán Loại văn bản mặc định theo Kho tri thức ngay khi mở trang mà không cần chờ chọn file.
         - Cập nhật nhãn Loại văn bản trong Smart Recommendation Banner hiển thị tên tiếng Việt chính thức.
     - **Kiểm thử**: Biome lint 0 lỗi trên 86 files, TypeScript 0 lỗi, Vite build thành công (10.81s), backend pytest 25/25 knowledge tests pass (100%), Ruff 0 lỗi.
  2. **Tích Hợp Smart Auto-Recommendation Cho Trang Nạp Tài Liệu Kho Tri Thức (phiên #66)**:
     - **Yêu cầu người dùng**: Tìm hiểu và tích hợp chức năng tự động đề xuất cấu hình bóc tách khi chọn file kế thừa từ `qnu-ai-core`.
     - **Giải pháp**:
       * Nâng cấp `frontend/src/lib/file-inspector.ts`: bổ sung `detectDocumentTypeFromFilename` (18 mẫu đối chiếu 37 loại Taxonomy), `extractYearFromFilename` (regex 4 chữ số), `cleanTitleFromFilename` và `getPriorityForDocumentType` (Cốt lõi 10/10, Tiêu chuẩn 8/10, Tham khảo 6/10).
       * Tích hợp vào `frontend/src/pages/document-ingest-page.tsx`: tự động chọn bộ máy OCR (Word/Excel -> Docling TableFormer bảo toàn bảng; Text/MD -> PyMuPDF Fast; PDF -> Auto), tự động chọn Loại văn bản, tự động điền Năm hiệu lực, hiển thị **Smart Recommendation Banner** màu Academic Teal và cập nhật mức ưu tiên pháp lý động.
     - **Kiểm thử**: Biome lint 0 lỗi trên 86 files, TypeScript 0 lỗi, Vite build thành công (12.59s), logic tests pass 100%.
  2. **Khắc Phục Lỗi "Xóa Tài Liệu Thất Bại (HTTP 500)" Do Backend Offline & Tối Ưu Xử Lý Lỗi Proxy (phiên #65)**:
     - **Nguyên nhân gốc rễ**: Người dùng duyệt Frontend (`port 3001`) nhưng tiến trình Backend (`port 8001`) chưa được khởi chạy. Vite Proxy (`localhost:3001 -> 127.0.0.1:8001`) bị từ chối kết nối `ECONNREFUSED` nên trả về `HTTP 500`. Frontend do không gọi được API danh sách nên fallback hiển thị tài liệu mẫu `doc_ts_2026`; khi người dùng bấm xóa, yêu cầu tiếp tục gặp 500 từ Vite proxy.
     - **Giải pháp**:
       * Khởi động dịch vụ Backend FastAPI trên port 8001, xác thực mọi API `/health/live`, `/knowledge/collections`, `/jobs`, `/modelops/defaults` đều phản hồi HTTP 200 OK.
       * Cải tiến `apiClient.deleteDocument`: Tự động bắt lỗi HTTP 500 từ proxy khi backend offline, hiển thị thông báo lỗi rõ ràng hướng dẫn khởi động backend, và dọn dẹp mock list an toàn.
     - **Kiểm thử**: Backend 136/136 tests pass (100%), Ruff 0 lỗi; Frontend Biome 0 lỗi (83 files), TypeScript 0 lỗi.
  2. **Tính Năng Thiết Lập Model Mặc Định Hệ Thống (Embedding, Reranker, OCR) Cho Kho Tri Thức & RAG (phiên #64)**:
     - **Yêu cầu người dùng**: Bổ sung tính năng cấu hình model mặc định (Cloudflare vs Local) để tự động áp dụng khi sử dụng Kho Tri Thức và RAG.
     - **Kiến trúc & Giải pháp**:
       * Backend Service & API (`modelops`): Cung cấp schema `SystemModelDefaults` và endpoints `GET /modelops/defaults`, `PUT /modelops/defaults`, `POST /modelops/providers/{id}/set-default`. Tự động scan model khả dụng của các provider active trong CSDL.
       * Lưu trữ PostgreSQL bền vững: Bản ghi `system_model_defaults` trong `model_provider_configs`, tự động đồng bộ vào runtime `settings` (Lifespan Startup).
       * Giao diện Quản trị ModelOps (`modelops-page.tsx`): Card điều khiển "Mô Hình Mặc Định Hệ Thống (Active System Defaults)" với 3 dropdowns tương tác thời gian thực; huy hiệu "★ Default" và nút gán nhanh "Đặt Default" trên từng model tag.
       * Phản ánh trực quan Kho Tri Thức (`knowledge-page.tsx` & `collection-detail-page.tsx`): Hiển thị model embedding mặc định động kèm icon phân biệt (`Zap` cho Cloudflare Workers AI Edge vs `Cpu` cho Local CPU).
     - **Kiểm thử**: Backend pytest 13/13 modelops + 34/34 rag/knowledge pass (100%), Ruff check 0 lỗi; Frontend Biome 0 lỗi, TypeScript 0 lỗi, Vite build bundle thành công.
  2. **Tạo seed data taxonomy Platform và khắc phục lỗi không hiển thị dữ liệu (phiên #63)**:
     - Xác định database đã có 37 dòng trong `platform_document_types`, nhưng API list HTTP 500 vì schema cũ thiếu `knowledge_documents.document_type_code`.
     - Tạo `document_types/seed_data.py` làm manifest seed versioned, sinh từ catalog 37 loại đã đối chiếu với `qnu-ai-core`, không tạo nguồn dữ liệu nghiệp vụ thứ hai.
     - Thêm `scripts/seed_document_types.py` để seed idempotent bằng lệnh rõ ràng; sửa logic sync không còn `KeyError` khi so sánh các trường source audit.
     - Bổ sung startup schema repair và migration idempotent cho cột/index/FK; đã áp dụng migration vào PostgreSQL hiện tại.
     - Xác minh API GET list trả 37 loại và POST sync trả HTTP 200 (`total=37`, `added=0`, `updated=0`); không chạm Provider/ModelOps seed của session song song.
     - Kiểm thử phiên: Backend **135/135 passed**, Ruff 0 lỗi.
  1. **Seed Dữ Liệu Provider Cloudflare Workers AI & Mistral OCR, Tích Hợp BGE-M3 và Reranker (phiên #60)**:
     - **Yêu cầu người dùng**: Seed data Cloudflare, Mistral OCR cho Provider, đồng bộ API key từ file env của `qnu-ai-core`, sử dụng Cloudflare cho BGE-M3 Embedding và Reranker.
     - **Giải pháp xử lý**:
       * Cấu hình `config.py` & `.env`: Bổ sung `EMBEDDING_PROVIDER="cloudflare"` và `RERANKER_PROVIDER="cloudflare"`, đặt mặc định `EMBEDDING_MODEL="@cf/baai/bge-m3"` và `RERANKER_MODEL="@cf/baai/bge-reranker-base"`.
       * Nạp `CLOUDFLARE_ACCOUNT_ID="ab6bf644b640759c330c44f109e3f000"`, `CLOUDFLARE_API_TOKEN="cfut_...df00"`, `MISTRAL_API_KEY="r1Dv...07T4"`.
       * Tích hợp Cloudflare BGE-M3 trong `vector_indexer.py`: Thêm `_embed_texts_cloudflare` gọi trực tiếp API Cloudflare Workers AI (16 chunks tính xong trong 1.00s thay vì 101.94s trên CPU, nhanh gấp 100 lần), kèm fallback tự động sang SentenceTransformers hoặc mock vector.
       * Tích hợp Cloudflare BGE Reranker trong `reranker.py`: Thêm `_rerank_cloudflare` gọi API `@cf/baai/bge-reranker-base`, xếp hạng chính xác ngữ nghĩa trong 1.21s, kèm fallback tự động sang RRF ordering.
       * Seed CSDL PostgreSQL `model_provider_configs`: Cập nhật `prov_cloudflare` và `prov_mistral` kèm Key Pool hoạt động chuẩn UTF-8 ("Khóa Mistral OCR & Platform").
     - **Kiểm thử**:
       * Backend: 25/25 test_knowledge pass, 9/9 test_rag pass, Ruff 0 lỗi.
       * Frontend: Biome check 0 lỗi, TypeScript 0 lỗi.
       * Đo đạc thực tế: Cloudflare BGE-M3 trả về vector 1024 chiều trong **1.00s**, Cloudflare Reranker trả về điểm số tương quan cao (0.898) trong **1.21s**.
  2. **Triển khai taxonomy loại văn bản Core → Platform (phiên #61)**:
     - Khảo sát danh mục 37 loại văn bản trong `qnu-ai-core/services/platform-api/.../document_taxonomy.py`.
     - Phân biệt taxonomy của Product Platform với `document_type` dạng chuỗi tự do trong AI Core engine.
     - Xác định Platform mới chưa có module/table/API Document Types và `KnowledgeDocument` chưa có `document_type_code`.
     - Tạo module `document_types` với catalog 37 loại/28 mã NĐ30, bảng `platform_document_types`, migration có kiểm tra schema, source hash/version và sync idempotent bảo vệ custom type.
     - Bổ sung CRUD/filter/API sync, gắn `document_type_code` vào `KnowledgeDocument`, upload ingestion và filter tài liệu theo loại.
     - Đồng bộ workflow extractor/exporter về mã canonical; thêm frontend `/document-types` list/detail, CRUD, deactivate và nút sync thật qua TanStack Query.
     - Chốt taxonomy v1 là 37 loại; `Dự toán`, `Nghị định`, `Ma trận đề thi` giữ ngoài taxonomy như legacy/artifact.
     - Trạng thái: nền tảng taxonomy v1 đã triển khai; chưa có Core HTTP endpoint versioned nên sync hiện dùng catalog import tương thích trong Platform.
     - Phạm vi file không bao gồm provider/modelops seed của session song song.
     - **Yêu cầu người dùng**: Khi làm sạch dữ liệu xong bấm "Xác nhận & Nạp vào Vector DB" trong Document Verification Studio thì nút bấm xoay mãi không dừng lại.
     - **Nguyên nhân gốc rễ**:
       * Mô hình BGE-M3 (2.24GB) chạy CPU inference cho 16 chunks dài mất tới 101.94s, vượt quá ngưỡng timeout 60s của client/proxy, khiến kết nối HTTP bị drop timeout và UI xoay mãi.
       * `_get_embedding_model()` chạy đồng bộ trên main thread của Event Loop Uvicorn, kèm theo truy vấn unauthenticated lên HuggingFace Hub làm khóa cứng server 25-30s đầu.
       * Thiết kế API `approve_document` đợi tính toán vector xong mới trả lời HTTP.
     - **Giải pháp xử lý**:
       * Tối ưu `vector_indexer.py`: Tải mô hình ưu tiên local cache (`local_files_only=True`, tải trong 2.45s), nạp qua `asyncio.to_thread` không chặn Event Loop, thêm timeout guard 30s với graceful fallback sang deterministic mock vector, chuẩn hóa tên collection tránh lặp `col_col_`.
       * Tối ưu `service.py`: Tách nạp Qdrant sang `_background_index_document` chạy ngầm qua `asyncio.create_task`. Lưu bản sửa tay vào PostgreSQL xong trả về kết quả ngay (<0.5s), không bắt HTTP client phải đợi 1.5 phút.
     - **Đo lường & Kiểm thử**:
       * Độ trễ API `POST /documents/{id}/approve` giảm từ >60s (Timeout) xuống **0.39s** (giảm 99.6%).
       * Điểm vector nạp thành công vào Qdrant (`col_question_bank`: 16 points).
       * Backend: 25/25 test_knowledge pass, 9/9 test_rag pass, Ruff 0 lỗi.
       * Frontend: Biome check 0 lỗi, TypeScript 0 lỗi, Vite build thành công.
  2. **Điều Chỉnh Thứ Tự Tab & Phân Định Trách Nhiệm Markdown / Văn Bản Trong Studio (phiên #58)**:
     - **Yêu cầu người dùng**: Sắp xếp lại 3 tab theo thứ tự `Văn bản`, `Markdown`, `Bố cục & Khối`; trong đó tab `Markdown` hiển thị tất cả nội dung của toàn bộ file, còn tab `Văn bản` hiển thị theo từng trang.
     - **Giải pháp xử lý**:
       * Sắp xếp lại thứ tự TabsList: `Văn bản` (1st, default), `Markdown` (2nd), `Bố cục & Khối` (3rd).
       * Tab `Văn bản` (Page-by-page): Hiển thị nội dung bóc tách của từng trang (`currentPage`), hỗ trợ chế độ "Sửa tay" (Human-in-the-loop) trực tiếp trên trang đang chọn, sao chép và tải về tệp riêng cho trang đó.
       * Tab `Markdown` (Full Document): Tổng hợp toàn bộ nội dung Markdown của tất cả các trang, kết hợp hiển thị các khối phân tách trang trực quan, tích hợp nút chuyển đổi nhanh giữa xem Render GFM và xem Mã nguồn thô, hỗ trợ sao chép toàn bộ Markdown và tải về tệp `.md` hoàn chỉnh của toàn bộ file.
       * Thanh thống kê Footer: Hiển thị linh hoạt (tab Markdown hiển thị tổng ký tự & tổng trang; tab Văn bản hiển thị số từ & dòng của trang hiện tại).
     - **Kiểm thử**: Biome lint 0 lỗi, TypeScript typecheck 0 lỗi, Vite build thành công; Backend 25/25 tests passed (100%), Ruff check 0 lỗi.
  2. **Khắc Phục Dứt Điểm Lỗi Markdown Dồn Hết Vào Trang 1 & Trang 2 Trắng Tinh (phiên #57)**:
     - **Nguyên nhân gốc rễ**: Khi tài liệu DOCX hoặc đa trang được upload, chunks được sinh ra có `page_number = None`. Trong `build_studio_pages`, toàn bộ chunks bị ép về `page_number = 1`, khiến Trang 1 gom toàn bộ 22.985 ký tự của cả 14 trang, còn các trang 2..14 không có chunk nào nên `markdown_content = ""` (trắng tinh).
     - **Giải pháp xử lý**:
       * Cập nhật `_ensure_page_blocks` trong `KnowledgeService`: Duyệt qua từng trang của PDF (cả PDF gốc hoặc Word render qua Gotenberg), bóc tách riêng bảng Markdown (`find_tables()`) và vùng văn bản (`SmartLayoutDetector`), lưu `page_markdowns` độc lập cho từng trang vào `doc_metadata`.
       * Cập nhật `build_studio_pages`: Hỗ trợ tham số `page_markdowns`. Khi dựng nội dung từng trang, ưu tiên lấy trực tiếp `page_markdowns[page_number]`. Nếu chunks bị dồn vào trang 1 trong tài liệu nhiều trang (`is_all_clumped_in_p1`), không gán toàn bộ cho trang 1 mà tự động tổng hợp Markdown chuẩn từ blocks của từng trang đó.
       * Cập nhật `approve_document`: Khi người dùng lưu sửa tay, đồng bộ cả `KnowledgeChunk(page_number=...)` và `doc_metadata["page_markdowns"]`.
       * Bổ sung 2 unit test trong `tests/test_knowledge.py` kiểm chứng không bao giờ dồn chunks vào trang 1 và bảo đảm trang 2 không bị rỗng.
     - **Khắc phục lỗi ECONNREFUSED khi chạy `make dev`**:
       * Đổi Vite proxy target trong `frontend/vite.config.ts` từ `http://localhost:8001` sang `http://127.0.0.1:8001` (tránh lỗi IPv6 `::1` trên Windows).
       * Thêm độ trễ an toàn 2s trong `make.bat` và `make.ps1` để Backend mở cổng 8001 trước khi Vite bật lên.
     - **Kiểm thử**: Backend Ruff check 0 lỗi, pytest 3/3 passed; Frontend typecheck 0 lỗi.
  2. **Khắc Phục Bóc Tách Bảng Song Song & Bảo Toàn Danh Sách (List) Độc Lập (phiên #56)**:
     - Giải quyết triệt để phản ánh của người dùng trên tài liệu 14 trang (`media_1789641791050.pdf` - Trang 9 chỉ hiện 2 bảng và mất sạch text/list):
       * Khử rò rỉ ô bảng song song (side-by-side tables) qua tính toán tỷ lệ giao cắt diện tích dọc (>50%) và ngang (>10px) hoặc tọa độ tâm block, không để các ô điểm IELTS/VSTEP tràn ra ngoài thành text.
       * Thiết lập rào cản `table_between`: ngăn cách tuyệt đối không gộp các đoạn văn bản xuyên qua bảng biểu.
       * Chuẩn hóa luật gộp Strictly Same-Type: `list` chỉ gộp với `list`, `text` chỉ gộp với `text`, giữ nguyên bản sắc nhãn `list`.
       * Mở rộng `_is_list_marker` hỗ trợ đầy đủ ký tự tiếng Việt (`đ`, `Đ`), dấu ngoặc đơn, gạch đầu dòng, số thứ tự.
       * Sửa an toàn `_suppress_overlapping_boxes`: chỉ xóa khối text/list nếu chính nó lọt lòng trên 60% bên trong bảng, không bao giờ xóa khối lớn vì bao quanh bảng.
     - Kiểm thử: Trang 9 hiển thị đầy đủ 9 khối vĩ mô sắc nét (`text`, `list` b. & c., 2 `table`, `text`, `list` c., `title` mục 6 & Đợt 1, `list` a, b, c, `text`). Backend 126/126 tests passed (100%), Ruff check 0 lỗi; Frontend Biome lint 0 lỗi trên 78 files, TypeScript 0 lỗi, Vite build thành công (5.32s).
  2. **Chuẩn Hóa Phân Vùng Bố Cục Vĩ Mô (Macro Layout Sections) Theo Chuẩn QNU-AI-Core (phiên #55)**:
     - Khảo sát mã nguồn thực tế `qnu-ai-core` (`smart_layout_detector.py`, `test_layout_classifier.py`, `sample-data.ts`), xác nhận cơ chế Adjacent Band Merging để gom các đoạn văn bản kề nhau thành khối vĩ mô.
     - Triệt tiêu hoàn toàn hiện tượng phân mảnh vi mô (micro-segmentation) từng câu/mục con/dòng căn cứ.
     - Thêm thuật toán `_merge_into_macro_regions` trong `SmartLayoutDetector`:
       * Gom Header Trang 1 thành 2 khối cân xứng (Cơ quan bên trái & Quốc hiệu bên phải).
       * Giữ nguyên Tiêu đề chính độc lập (`KẾ HOẠCH`, `QUYẾT ĐỊNH`, v.v.).
       * Gộp các đoạn căn cứ pháp lý và tiểu mục chỉ đạo liên tiếp thành các khối text vĩ mô.
       * Phân cách mục La Mã rõ ràng (`I.`, `II.`, `III.`, v.v.).
       * Bảo vệ nguyên vẹn các khối `table`, `signature` và `list` (Nơi nhận).
     - Giảm **67%** số lượng khung nhận diện trên tài liệu mẫu (từ 36 khung vụn xuống 12 khung vĩ mô: Trang 1 có 5, Trang 2 có 2, Trang 3 có 2, Trang 4 có 3).
     - Kiểm thử: Backend 125/125 pytest passed (100%), Ruff check 0 lỗi; Frontend Biome lint 0 lỗi trên 78 files, TypeScript 0 lỗi, Vite build thành công (5.33s).
  2. **Loại Bỏ Tính Năng Tia Quét & Chuẩn Hóa Khung Nhận Diện Scan Bố Cục Văn Bản Hành Chính (phiên #54)**:
     - Gỡ bỏ hoàn toàn nút bấm, hiệu ứng animation laser beam và HUD badge trên giao diện Document Verification Studio và Scan Studio theo yêu cầu người dùng.
     - Nâng cấp `SmartLayoutDetector` kết hợp Vector PDF (PyMuPDF blocks + `find_tables()`) và Computer Vision OpenCV.
     - Triệt tiêu phân mảnh ô bảng: gộp gọn bảng dữ liệu 9 hàng thành 1 khối `table` duy nhất.
     - Điều chỉnh ngưỡng mật độ con dấu tương thích (0.04) cho con dấu tròn lớn, bắt trọn vẹn con dấu ĐH Quy Nhơn.
     - Hợp nhất hoàn chỉnh khối Dấu & Ký (`signature`): tự động bao trọn Chức vụ (`HIỆU TRƯỞNG`), Con dấu tròn màu đỏ và Họ tên người ký (`PGS. TS. Đoàn Đức Tùng`) kể cả khi mực dấu đóng đè, loại bỏ toàn bộ khung text trùng lặp.
     - Phân loại chính xác ngữ nghĩa hành chính Việt Nam (NĐ 30/2020/NĐ-CP): Tiêu đề cơ quan, Quốc hiệu, Tiêu ngữ, Căn cứ pháp lý, Tiêu đề mục La Mã, Mục số, Danh sách gạch đầu dòng, và Khối Nơi nhận.
     - Bổ sung unit test suite `test_smart_layout.py` (3 test cases).
     - Kiểm thử: Backend 125/125 pytest passed (100%), Ruff check 0 lỗi; Frontend Biome lint 0 lỗi trên 78 files, TypeScript 0 lỗi, Vite build hoàn tất thành công (5.54s).
  2. **Thiết Kế Lại Component Select & Chuẩn Hóa Bộ UI Primitives (phiên #53)**:
     - Tạo UI Primitive `frontend/src/components/ui/select.tsx` dựa trên `@radix-ui/react-select` (bo góc 8px, popover mượt mà, checkmark indicator).
     - Thay thế 100% thẻ `<select>` native trên toàn bộ hệ thống (`collection-detail-page.tsx`, `document-ingest-page.tsx`, `scan-studio-page.tsx`, `modelops-page.tsx`, `channels-page.tsx`, `docx-nd30-editor.tsx`).
     - Tinh chỉnh các UI primitives khác theo UI Rules: bổ sung thanh cuộn siêu mỏng 6px (`globals.css`), chuyển `badge.tsx` sang dạng pill `rounded-full` soft tint, làm mềm viền focus `input.tsx` và `textarea.tsx`.
     - Kiểm thử: Biome lint 0 lỗi trên 78 files, TypeScript 0 lỗi, Vite build thành công (5.68s), pytest 23/23 pass.
  2. **Rollback Font Chữ & Typography Sidebar Về Ban Đầu (phiên #52)**:
     - Khôi phục `frontend/src/layouts/app-sidebar.tsx` và `--font-sans` trong `frontend/src/styles/globals.css` về trạng thái ban đầu của Platform theo yêu cầu người dùng (`text-xs py-2`, `text-[10px]` labels/badges, loại bỏ active pill).
     - Kiểm thử: Biome lint 0 lỗi trên 77 files, TypeScript `tsc --noEmit` 0 lỗi.
  2. **Hoàn Thiện Nút Xóa Tác Vụ, Nút Dọn Dẹp Đã Xong & Sửa Lỗi Hủy Job HTTP 409 (phiên #51)**:
     - **Nguyên nhân HTTP 409**: Bản ghi job trong CSDL PostgreSQL đã ở trạng thái `cancelled`, nhưng `mapJobToIngestionTask` trong `frontend/src/services/api-client.ts` gom nhầm thành `processing`, khiến UI hiển thị "Đang xử lý" và render nút Hủy (`X`). Khi người dùng bấm `X`, Backend từ chối với lỗi 409 vì job đã kết thúc.
     - **Khắc phục triệt để**:
       - Mở rộng kiểu `IngestionTask.status` hỗ trợ `cancelled`.
       - Ánh xạ đúng `status: "cancelled" -> "cancelled"`.
       - Thêm cơ chế idempotent cancel cho Backend: nếu job đã `cancelled` thì trả về bản ghi ngay thay vì ném lỗi 409.
       - Cập nhật badge `TASK_STATUS_BADGE.cancelled` thành "Đã hủy" với style badge muted và icon `X` rõ ràng.
       - Thêm bộ lọc trạng thái "Đã hủy" và "Thất bại" trong filter dropdown.
     - **Thêm nút Xóa từng tác vụ (`Trash2`)**:
       - Bổ sung nút Xóa trên từng dòng bảng tác vụ kèm `ConfirmDialog` xác nhận xóa.
       - Thêm phương thức `delete_job` trong Backend service và endpoint `DELETE /jobs/{job_id}`.
       - Thêm `apiClient.deleteJob(jobId)` xử lý xóa an toàn (hỗ trợ idempotent 404).
     - **Hiện thực hóa nút "Dọn dẹp đã xong"**:
       - Gắn handler và `ConfirmDialog` cho nút "Dọn dẹp đã xong" trên thanh công cụ tác vụ.
       - Thêm phương thức `cleanup_jobs` trong Backend service và endpoint `DELETE /jobs/cleanup?collection_id={id}` dọn dẹp hàng loạt các jobs completed/cancelled/failed.
       - Thêm `apiClient.cleanupJobs(collectionId)`.
       - Hiển thị banner xanh `taskSuccessMessage` tự động ẩn sau khi thao tác thành công.
     - **Triệt tiêu Mock Trap trong Ingestion Tasks**:
       - Sửa `apiClient.getIngestionTasks` để khi Backend trả về mảng rỗng `[]` (đã dọn sạch), Frontend hiển thị đúng Empty State thay vì lén lút fallback về `MOCK_INGESTION_TASKS`.
     - **Kiểm thử**: Backend 122/122 pytest passed (100%), Ruff check 0 lỗi; Frontend Biome lint 0 lỗi trên 77 files, TypeScript `tsc --noEmit` 0 lỗi, Vite build hoàn tất thành công (13.59s).
  2. **Đồng Bộ Font Chữ & Typography Sidebar Theo Chuẩn QNU AI Core (phiên #50)**:
     - Đồng bộ font family Inter/system-ui và typography Sidebar.



---

## 2. Tổng Quan Dự Án

| Thuộc Tính | Giá Trị |
| :--- | :--- |
| **Tên dự án** | QNU AI Platform |
| **Tổ chức** | Trường Đại học Quy Nhơn (QNU) |
| **Workspace** | `D:\DuAnPhanMem\qnu-ai-platform` |
| **Backend** | `D:\DuAnPhanMem\qnu-ai-platform\backend` (FastAPI, Port 8001) |
| **Frontend** | `D:\DuAnPhanMem\qnu-ai-platform\frontend` (Vite 6 + React 19, Port 3001) |
| **Codebase gốc tham khảo** | `D:\DuAnPhanMem\qnu-ai-core` (FastAPI + Streamlit/Vite Studio, Port 3000) |

---

## 3. Trạng Thái Hoàn Thành Các Giai Đoạn

### ⚠️ Backend — Đủ bề rộng chức năng, production readiness còn một phần

> Lưu ý phiên #85: bảng dưới đây phản ánh **độ phủ module/UI lịch sử**, không đồng nghĩa mọi module đã hoàn thiện runtime hoặc đủ điều kiện production. Trạng thái production phải theo acceptance gate trong báo cáo đánh giá tổng thể.

| Giai Đoạn | Mô Tả | Trạng Thái |
| :--- | :--- | :---: |
| 1 | Scaffolding FastAPI + Cấu hình hạ tầng 7 dịch vụ | ✅ Done |
| 2 | Module Assistants (05 Trợ lý QNU) | ✅ Done |
| 3 | Module Knowledge (Collections, Ingestion Pipeline, OCR đa tầng) | ✅ Done |
| 4 | Module RAG (Hybrid RRF k=60, Cross-Encoder Reranking, Structured Fact Layer) | ✅ Done |
| 5 | Module ModelOps (Provider Presets, Key Pool 429 Failover, Circuit Breaker) | ✅ Done |
| 6 | Module Tools (UIS Admissions Query, Word NĐ 30, Excel Bloom) | ✅ Done |
| 7 | Module Evaluation (Ragas TM-08: Faithfulness, Relevance, Precision) | ✅ Done |
| 8 | Module Workflows (DAG Pipeline, ARQ Workers, Guardrails) | ✅ Done |

**Backend Quality**: Assistants 7/7 tests passed | Full suite 141/142 (1 lỗi OCR concurrent ngoài phạm vi) | Ruff: 0 errors
(OCR: pymupdf + docling 2.128 + easyocr 1.7.2 thật | Layout: SmartLayoutDetector OpenCV morphological line + HSV stamps | Studio: studio-view + page-image + bboxes engine thật | Facts: entity/attribute/value đúng nghĩa | Jobs: ARQ thật + cancel/retry/stats, reindex/test, collection PUT/DELETE | Preview: office→PDF qua Gotenberg | Batch-approve | Lint exit 0 | Counts thật, download, vector cleanup)

---

### ⚠️ Frontend — Độ phủ màn hình cao, LiveMode cần loại bỏ business mock fallback

> Lưu ý phiên #85: frontend còn business mock fallback; SSE Chat hiện là JSON + simulated text streaming; bundle production hiện khoảng 1.50 MB sau minify.

| Giai Đoạn | Màn Hình / Module | Trạng Thái |
| :--- | :--- | :---: |
| 1 | Master Layout (Sidebar w-64, Topbar h-14, Academic Teal oklch) | ✅ Done |
| 2 | Assistants Studio (05 Trợ lý, Persona, ModelOps config, Tool Gateway) | ✅ Done |
| 3 | Knowledge Management & Master-Detail Navigation (List + Detail + Ingest + Full Studio) | ✅ Done |
| 4 | Document Verification Studio (Full 14 scan pages, BBoxes, Regions, ReactMarkdown Tables, In-place Edit) | ✅ Done |
| 4b | **Scan & OCR Document Intelligence Studio** (`/ocr`: Split-Screen, OpenCV Boxes, Excel Viewer, API Code) | ✅ Done |
| 5 | Omni-Channel Chat Studio (SSE Streaming, Thinking Indicator, CitationSheet) | ✅ Done |
| 6 | ModelOps Dashboard (4 Presets, Secret Key Masking, Circuit Breaker Monitor) | ✅ Done |
| 7 | Tools Gateway (Word NĐ 30 Preview, Excel Bloom Matrix, Template Library) | ✅ Done |
| 8 | Workflow DAG Canvas (@xyflow/react, 6 Custom Node types, Run DAG & Inspector) | ✅ Done |

**Frontend Quality**:
- Biome Lint: 0 errors across all 90 files | TypeScript: 0 errors | Vite Build: 100% passed
- Playwright E2E: Suite 09 có TC-INGEST-01→04 (bao gồm TC-INGEST-04 chống tái diễn hardcode)

---

## 4. Danh Mục Gotchas Kỹ Thuật (Kinh Nghiệm Thực Tế)

1. **Strict Mode trong Playwright**:
   - Khi có text xuất hiện ở cả thanh Breadcrumb/Header và trong thân trang (ví dụ `Trang 1 / 14`, filename), bắt buộc phải dùng `page.getByText('...', { exact: true })` hoặc `.first()` để tránh lỗi `strict mode violation`.
2. **Hiển thị Ảnh Scan Tài Liệu Bóc Tách**:
   - Không được dùng text/HTML mock để giả lập trang scan. Bắt buộc phải phục vụ ảnh scan thật từ thư mục tĩnh `frontend/public/ocr-cache/doc_ts_2026/page_N.jpg` với tỉ lệ khung hình chuẩn A4 và zoom container. Với tệp mới không có scan cache, hiển thị khung canvas tài liệu số hóa sạch.
3. **Render Bảng Biểu Markdown**:
   - Markdown thô (`whitespace-pre-wrap`) không hiển thị được bảng. Bắt buộc dùng `ReactMarkdown` với plugin `remarkGfm` và custom `components={{ table, thead, th, td, tr }}` có styling viền ô rõ ràng.
4. **Chuẩn Hóa Encoding UTF-8 trên Windows (Tránh Mojibake)**:
   - Mọi script Python chạy console trên Windows phải thiết lập `sys.stdout.reconfigure(encoding="utf-8")` để không bị lỗi `UnicodeEncodeError` với bảng mã `cp1252`.
   - File đọc/ghi bắt buộc chỉ định rõ `encoding="utf-8"`.
5. **PEP 8 E402 trong Backend**:
   - Khi xử lý đoạn mã sửa lỗi Windows IPv6 `no_proxy`, đặt đoạn sanitize sau toàn bộ module imports chuẩn để ruff check 0 lỗi.

---

## 5. Backlog & Kế Hoạch Tiếp Theo

- [ ] Thực hiện gói **RAG Data Integrity & Groundedness**: retrieval chỉ lấy document `ready/approved`, đúng tenant/revision; thêm relevance threshold và claim-citation verification.
- [ ] Xóa/rebuild 788 orphan facts Question Bank; thêm FK/cascade, source evidence và content revision cho `knowledge_facts`.
- [ ] Reconcile 17 chunks Question Bank sang Qdrant collection chuẩn `col_question_bank`; kiểm chứng parity rồi mới xóa `col_col_question_bank`.
- [ ] Cấm mock embedding trong LiveMode; hỗ trợ sparse-only degraded mode có nhãn và health signal rõ ràng.
- [ ] Version hóa RAG cache theo tenant/collection/content revision/assistant/model/policy và invalidate khi approve/edit/archive/delete/reindex.
- [ ] Thực hiện hotfix **Assistant–Workflow Runtime Integrity**: bỏ `is_approved=true`, bỏ mock answer/citation/artifact trong LiveMode, fail-fast khi export lỗi và loại KPI/count giả.
- [ ] Lấy tenant/user/role/approval actor từ trusted auth context; enforce tool allowlist, node permissions, connection allowlist và approval trước side effect.
- [ ] Hoàn thiện workflow Soạn thảo/Ngân hàng câu hỏi: clarify wait/resume, RAG context assembly, syllabus/CLO/Bloom validation và artifact metadata động.
- [ ] Triển khai SSE thật và cancellation server-side; sửa citation DTO mapping `source_id/section/page_number/quote` sang Frontend.
- [ ] Thực hiện gói **Knowledge Index Integrity**: state machine `review_pending/indexing/ready/index_failed`, retrieval chỉ lấy đúng revision `ready`, và reconciliation PostgreSQL–Qdrant.
- [ ] Đối chiếu/migrate 16 points từ `col_col_question_bank` sang collection chuẩn `col_question_bank`; chỉ xóa legacy sau khi kiểm chứng.
- [ ] Đồng bộ vector/facts khi approve, sửa, archive, xóa document/collection; loại ghost citations và cấm mock embedding trong LiveMode.
- [ ] Nâng lexical retrieval từ `ILIKE` lên PostgreSQL FTS thật; chạy dense/sparse song song và enforce tenant/workspace filter trong Qdrant.
- [ ] Áp authentication, RBAC và trusted tenant context lên toàn bộ router thay đổi dữ liệu.
- [ ] Tách DemoMode/LiveMode và loại business mock fallback khỏi LiveMode.
- [ ] Thay Evaluation/TM-08 mô phỏng bằng việc chạy Assistant/RAG runtime thật và tổng hợp metrics từ DB.
- [ ] Nối RAG Answer Composer với ModelOps; bind Assistant primary/fallback model, tool allowlist và evaluation policy xuống runtime.
- [ ] Khóa Workflow execution/resume vào immutable version; bổ sung timeout, retry/backoff, cancellation, schema/port và permission validation.
- [ ] Nạp tài liệu chính thức và golden datasets cho Admissions, Regulations và Library.
- [ ] Tách các file lớn trên 1.000 dòng theo SRP, ưu tiên ModelOps, API client, Knowledge service và các detail pages.
- [ ] Tối ưu frontend bundle bằng code splitting và route-level lazy loading.
- [x] Đồng bộ ảnh scan thực tế 14 trang từ `qnu-ai-core` vào Studio đối soát.
- [x] Render Markdown bảng biểu và cấu trúc phân cấp chuẩn GitHub Flavored Markdown.
- [x] Thêm chế độ xem trước (Preview) khi hiệu đính văn bản trong chế độ Sửa tay (Human-in-the-loop).
- [x] Nối FE vào BE thật cho luồng nạp/đối soát (upload pending, approve + index Qdrant, OCR auto-routing Docling/EasyOCR lazy).
- [x] Cài Docling 2.128 thật + kiểm chứng Đề án 2026 (48.050 ký tự markdown, bảng đầy đủ, conf 0.97).
- [x] Sửa dứt điểm lỗi hardcode upload file và bổ sung kiểm thử tự động chống tái diễn (TC-INGEST-04).
- [x] Xây dựng bộ quét tự động Zero Mojibake (`scripts/check_mojibake.py`).
- [x] Endpoint studio-view + render page-image từ backend (cache storage) + bboxes/regions thật từ engine; xóa 29 ảnh qd2699 (~6MB) khỏi git (giữ 14 ảnh demo theo AGENTS 8.9).
- [x] Xây dựng Scan & OCR Document Intelligence Studio độc lập (`/ocr`) kèm SmartLayoutDetector OpenCV (nhận diện bảng, con dấu đỏ, phân đoạn text) và ExcelSpreadsheetViewer đa sheet.
- [ ] Kéo thả ROI trên ảnh scan (mở rộng studio-view).
- [ ] Chuẩn hóa CRLF→LF + `.gitattributes` để `npm run lint` (biome check) xanh toàn repo.
- [x] Triển khai nền tảng taxonomy 37 loại văn bản từ `qnu-ai-core` sang `qnu-ai-platform` (`docs/ke_hoach/03_ke_hoach_dong_bo_taxonomy_loai_van_ban.md`).
- [x] Tạo seed manifest taxonomy Platform và sửa lỗi schema/API khiến danh sách loại văn bản không hiển thị (`backend/scripts/seed_document_types.py`).
- [x] Đồng bộ 13 NodeManifest từ `qnu-ai-core` và hiển thị Node Catalog tại `/nodes`; giữ DAG Canvas tại `/canvas`.
- [x] Đồng bộ 5 trợ lý Core vào PostgreSQL thật; hoàn thiện API CRUD/seed/bundle và UI list/create/detail tại `/assistants`.
- [ ] Phiên OCR/Provider hoàn thiện trường `fallback_engine` trong `OCRExtractResponse` để full backend suite trở lại 142/142.
- [ ] Bổ sung Core manifest/HTTP endpoint versioned, parser confidence/evidence, E2E CRUD/sync và scheduler sync taxonomy.
