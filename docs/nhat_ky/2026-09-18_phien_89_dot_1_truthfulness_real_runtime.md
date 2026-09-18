# Nhật Ký Phiên Làm Việc #89: Triển Khai Đợt 1 — Truthfulness & Real Runtime (Xóa Bỏ Hoàn Toàn "Thế Giới Ảo")

- **Thời gian**: 2026-09-18 15:45 - 16:35 (UTC+7)
- **Người thực hiện**: AI Senior Full-Stack Architect & Enterprise AI Systems Specialist
- **Mục tiêu phiên làm việc**:
  Thực hiện toàn diện **Đợt 1: Truthfulness & Real Runtime (Xóa bỏ hoàn toàn "Thế giới ảo")** theo lộ trình đề ra trong Báo cáo nhận xét tổng thể nền tảng [`docs/nhan_xet_tong_the_qnu_ai_platform_2026-09-18.md`](../nhan_xet_tong_the_qnu_ai_platform_2026-09-18.md). Chuyển dịch toàn bộ hệ thống từ mô phỏng sang runtime thực chất, triệt tiêu mock deceptive fallback, bảo đảm sự thật và tính toàn vẹn dữ liệu.

---

## 1. Bối Cảnh & Động Lực

Báo cáo kiểm toán hệ thống ngày 18/09/2026 đã chỉ ra các "vùng ảo" nguy hiểm cần xóa bỏ ngay:
1. **RAG sinh câu trả lời bằng code nối chuỗi tĩnh hoặc mock** thay vì thực thi qua LLM model runtime với Zero-Hallucination prompt instruction.
2. **Sparse Retrieval bỏ trống**: `retriever.py` chỉ thực hiện dense vector qua Qdrant, chưa thực hiện lexical search qua PostgreSQL FTS.
3. **SSE Streaming giả lập trên Frontend**: `use-rag-stream.ts` chứa mảng `MOCK_ASSISTANT_DATA` và hàm `streamSimulatedText` giả vờ gõ chữ token.
4. **Mock Fallbacks lừa dối trong API Client**: Khi backend ngắt kết nối hoặc không có dữ liệu, frontend tự ý nạp mock collections, mock quota, mock tools, mock runs tạo cảm giác "hệ thống vẫn sống tốt".
5. **Đánh giá TM-08 ảo**: Trang Evaluation hiển thị số liệu 94.2% / 91.8% / 88.5% cố định từ code giao diện thay vì truy vấn dữ liệu kiểm định thực từ PostgreSQL.

---

## 2. Chi Tiết Các Thay Đổi Kỹ Thuật

### 2.1. Backend — Real RAG Answer Synthesis & Sparse Lexical FTS
- **`backend/app/modules/rag/service.py`**:
  - Tích hợp gọi trực tiếp `modelops_service.generate()` với cấu hình Zero-Hallucination prompt instruction nghiêm ngặt của ĐH Quy Nhơn.
  - LLM chỉ được phép sử dụng dữ liệu từ Bảng số liệu đã xác thực (`fact_markdown`) và Đoạn trích tài liệu từ Kho tri thức (`candidates`).
  - Trong trường hợp nhà cung cấp mô hình bị lỗi mạng/timeout, kích hoạt graceful grounded synthesis fallback dựa trên trích đoạn thực tế và số liệu thực tế, bảo lưu 100% trích dẫn (`citations`) và số liệu (`facts_used`), không bịa đặt số liệu.
- **`backend/app/modules/rag/retriever.py`**:
  - Xây dựng phương thức `search_sparse_fts(db, collection_id, query, top_k)` sử dụng PostgreSQL Full-Text Search.
  - Sử dụng hàm `to_tsvector('simple', ...)` và `plainto_tsquery('simple', ...)`, xếp hạng văn bản bằng `ts_rank_cd()`.
  - Kết hợp điểm số từ FTS và vector embedding qua Reciprocal Rank Fusion (RRF $k=60$).
  - Có cơ chế phát hiện dialect (SQLite vs PostgreSQL) an toàn cho môi trường test in-memory.

### 2.2. Backend — Real Server-Sent Events (SSE) Token Streaming
- **`backend/app/modules/modelops/service.py` & `schemas.py`**:
  - Thêm phương thức `generate_stream(...)` vào `ModelOpsService`, trả về `AsyncGenerator[str, None]` truyền token trực tiếp từ LLM Provider Adapter.
  - Bổ sung trường `preferred_provider_id` và `preferred_model_name` vào `LLMGenerateRequest`.
- **`backend/app/modules/assistants/router.py` & `service.py`**:
  - Khai báo endpoint `/platform/v1alpha1/assistants/{reference}/chat_stream` và xử lý tham số `stream=true` trên endpoint `/chat`.
  - Phát các event chuẩn SSE:
    * `event: status` (trạng thái khởi tạo, xử lý RAG/DAG).
    * `event: citation` (danh sách trích dẫn tài liệu đối soát).
    * `event: artifact` (văn bản hành chính hoặc bảng tính Bloom kèm theo).
    * `event: token` (từng token sinh ra theo thời gian thực).
    * `event: done` (tổng kết token count, latency, USD cost).
    * `event: error` (thông báo sự cố nếu có).

### 2.3. Backend & Frontend — Continuous Quality Evaluation (TM-08) Thực Chất
- **`backend/app/modules/evaluation/service.py` & `router.py`**:
  - `run_evaluation()`: Thực thi trực tiếp đối thoại với trợ lý AI / pipeline RAG thật qua `AskRequest`, so sánh kết quả trả về với ground truth để tính 3 chỉ số Ragas TM-08 (Faithfulness $\ge 0.90$, Relevance $\ge 0.85$, Precision $\ge 0.80$).
  - `get_summary_metrics()` & `get_gap_inbox()`: Sử dụng truy vấn SQL thực tế (`SELECT count, avg(faithfulness_avg)... FROM evaluation_runs WHERE status = 'completed'`) thông qua `AsyncSession`. Trả về số liệu rỗng/chưa đo nếu chưa có phiên benchmark nào được thực hiện.
  - Bổ sung endpoint `GET /runs` trả về danh sách lịch sử các đợt kiểm định.
- **`frontend/src/pages/evaluation-page.tsx`**:
  - Viết lại toàn diện trang Evaluation:
    * Xóa bỏ các biến số fix cứng `94.2%`, `91.8%`, `88.5%`.
    * Tỷ lệ phần trăm và độ rộng thanh progress bar phản ánh chính xác dữ liệu từ backend (`metrics?.faithfulness * 100`).
    * Huy hiệu "Đạt Chuẩn" / "Chưa Đạt" / "Chưa Đo" tự động cập nhật theo ngưỡng TM-08 chuẩn.
    * Bổ sung bảng lịch sử phiên kiểm định (`runs`), cho thấy số test cases, số pass, tỷ lệ pass và trạng thái đạt chuẩn TM-08.
    * Thêm `EmptyState` khi chưa có lịch sử chạy hoặc chưa có khoảng trống tri thức.
    * Nút hành động "Chạy Benchmark TM-08" kích hoạt chạy kiểm định thật trên backend.

### 2.4. Frontend — Xóa Bỏ Deceptive Mock Fallbacks
- **`frontend/src/hooks/use-rag-stream.ts`**:
  - Xóa bỏ hoàn toàn hằng số `MOCK_ASSISTANT_DATA` và hàm giả lập gõ chữ `streamSimulatedText`.
  - Kết nối thật với endpoint `/chat_stream` qua fetch ReadableStream Reader, phân tách SSE events và cập nhật giao diện người dùng theo luồng token thực tế từ server.
- **`frontend/src/services/api-client.ts`**:
  - Xóa bỏ các mảng mock dữ liệu nghiệp vụ: `MOCK_DOCUMENTS`, `MOCK_INGESTION_TASKS`, `MOCK_PROVIDERS`, `MOCK_QUOTA`, `MOCK_TOOLS`.
  - Các hàm `getCollections`, `getDocuments`, `getModelProviders`, `getTokenQuota`, `getTools`, `getEvaluationMetrics`, `getGapInbox`, `getIngestionTasks` đều gọi trực tiếp API Backend thật và ném ngoại lệ rõ ràng khi máy chủ gặp sự cố, chấm dứt tình trạng "giao diện hoạt động ảo khi backend sập".
  - Giữ lại các bộ từ điển tra cứu chuyên ngành tĩnh phục vụ UX người dùng: `UIS_MAJORS_DATABASE` (dữ liệu mã ngành, điểm chuẩn tuyển sinh tĩnh của trường) và `ADMINISTRATIVE_TEMPLATES` (biểu mẫu hành chính Nghị định 30).
- **`frontend/src/pages/dashboard-page.tsx`**:
  - Đồng bộ phương thức `apiClient.getTokenQuota()`.

---

## 3. Kết Quả Kiểm Thử Toàn Diện

1. **Frontend**:
   - `npm run lint`: Biome check 93 files, **0 lỗi, 0 cảnh báo**.
   - `npm run typecheck`: TypeScript tsc --noEmit, **0 lỗi type**.
   - `npm run build`: Vite build thành công đóng gói bundle sản xuất trong **10.17 giây**.
2. **Backend**:
   - `uv run ruff check .`: **All checks passed! (0 lỗi linter)**.
   - `uv run --extra dev pytest -v`: **174 passed, 0 failed, 100% test pass** trong 48.41 giây.
3. **Chuẩn Hóa Tiếng Việt & Zero Mojibake**:
   - `python scripts/check_mojibake.py`: Quét toàn bộ 231 tệp mã nguồn, **0 phát hiện ký tự rác, 0 vỡ font tiếng Việt**.

---

## 4. Trạng Thái Hoàn Thành & Hướng Đi Tiếp Theo

- **Đợt 1: Truthfulness & Real Runtime** đã hoàn tất 100%. Nền tảng đã đoạn tuyệt với các mock deceptive, thiết lập nền tảng runtime thật cho cả RAG, Assistants và Đánh giá chất lượng TM-08.
- **Đợt 2 theo roadmap**: Enforce Tenant Isolation, Trusted Auth Context & RBAC, cùng với đồng bộ dữ liệu vector Qdrant cho Kho tri thức.
