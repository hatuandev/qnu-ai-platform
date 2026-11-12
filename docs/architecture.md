# Kiến trúc QNU AI Platform — V1

> **Phạm vi:** tài liệu sống, mô tả hệ thống đang chạy tại HEAD.
> Bằng chứng là mã trong [`backendV1/`](../backendV1) và [`frontendV1/`](../frontendV1);
> khi tài liệu mâu thuẫn với mã/test, mã/test thắng.
> Bản kiến trúc cũ (Next.js, DAG, 5 trợ lý, PaddleOCR/Gemini) đã được thay thế và không còn
> mô tả hệ thống hiện hành. Bản đồ tài liệu: [docs/README.md](./README.md).

## 1. Mục tiêu sản phẩm

Nền tảng AI nội bộ phục vụ chuyển đổi số Trường Đại học Quy Nhơn, hướng tới các lĩnh vực:
tư vấn tuyển sinh, quy chế — quy định đào tạo, khai thác tài liệu thư viện, soạn thảo văn bản
hành chính và ngân hàng câu hỏi/đề thi.

Đây là **định hướng**, không phải danh sách tính năng đã có. Phần 5 liệt kê chính xác những gì
V1 đã triển khai và những gì còn là khung.

## 2. Nguyên tắc thiết kế

1. **Evidence-first:** mọi câu trả lời phải truy vết được về nguồn đã xuất bản (source →
   revision → OCR → biên soạn → duyệt → chỉ mục → trích dẫn). Không có bằng chứng thì từ chối
   kết luận, không thay bằng câu trả lời suy đoán.
2. **Job xong ≠ nội dung đã duyệt:** trạng thái xử lý kỹ thuật tách khỏi quyết định xuất bản của
   con người.
3. **Workspace là biên giới quyền**, không phải phân vùng vật lý. Mọi truy vấn tài nguyên đi qua
   `resolve_workspace_access`; `workspace_id` từ URL/body chỉ là đối tượng cần kiểm tra.
4. **Fail closed:** thiếu credential, thiếu quyền, provider lỗi hoặc loại provider chưa có
   adapter đều trả lỗi rõ ràng, không sinh dữ liệu giả và không tự fallback.
5. **Bí mật LLM nằm trong ModelOps DB** (mã hóa), không nằm trong `.env` hay bundle frontend.

## 3. Kiến trúc backend

Modular monolith: một tiến trình API + một tiến trình worker, cùng một codebase.

```
HTTP → middleware (correlation, CORS) → dependencies (actor, db)
     → router mỏng → service → port → adapter
```

| Tầng | Vai trò | Không được làm |
|---|---|---|
| `qnu/api/` | lắp ráp, dependency, handler lỗi, health | chứa SQL hay nghiệp vụ |
| `qnu/platform/` | config, DB, cache, storage, crypto, log, metric | import domain |
| `qnu/contracts/` | DTO dùng chung | logic nghiệp vụ |
| `qnu/ports/` | protocol ra hệ ngoài | import SDK cụ thể |
| `qnu/adapters/` | cài đặt port | được domain import |
| `qnu/domains/` | router + service + policy + models | import `adapters` |
| `qnu/workers/` | ARQ, queue riêng của V1 | nhặt job legacy |

Quy tắc phụ thuộc: `api → domains → ports/contracts → platform`; adapter chỉ được khởi tạo ở
`api/wiring.py`. Mỗi domain giao tiếp qua `public_api.py` — xem
[module-boundaries.md](../backendV1/docs/module-boundaries.md).

### Domain (13)

`identity`, `workspaces`, `modelops`, `knowledge`, `ocr`, `rag`, `assistants`,
`conversations`, `lifecycle`, `operations`, `evaluation`, `integration`, `answer_review`.

Các khung Phase 0 rỗng (`document_types`, `node_catalog`, `tools`, `workflows` và các
package con `knowledge/chunks|facts|glossary|...`, `rag/search|...`) đã được xóa ngày
2026-11-09 vì không có import/consumer. Kế hoạch taxonomy/nút/DAG vẫn nằm ngoài MVP,
không còn xuất hiện như module sản phẩm.

### Dữ liệu

- PostgreSQL 16, chuỗi Alembic riêng `0001…0019` (bảng version `alembic_version_backendv1`).
- Redis: queue ARQ `qnu:v1:jobs` + cache namespace `qnu:v1:cache:`.
- Qdrant: collection riêng theo generation/embedding model; chiều vector theo model đã cấu hình.
- MinIO/S3 hoặc local: tệp gốc và artifact content-addressed.

## 4. Luồng dữ liệu

1. **Workspace & quyền** — membership + role (`admin`/`editor`/`member`), platform admin
   quản trị toàn hệ thống; audit theo đơn vị.
2. **Kho tri thức** — collection theo workspace, upload tệp, revision bất biến, checksum,
   idempotency theo `(workspace, actor, key)`.
3. **Bóc tách** — native-first: PyMuPDF + PDF Inspector cho PDF có lớp chữ, Docling cho DOCX
   (qua Gotenberg), MinerU cho PDF scan/ảnh. Sinh raw + canonical JSON + Markdown + manifest.
4. **Rà soát hậu OCR** — sửa đoạn/ô, gợi ý chính tả qua ModelOps, lưu `text_versions` có hash.
5. **Biên soạn (Compiler)** — job bền vững theo chủ đề, bản nháp có trích dẫn và bảng nguyên bản;
   review ngữ nghĩa hai chiều nguồn/bản nháp.
6. **Xuất bản** — con người xác nhận và duyệt; document/version bất biến, preview + audit,
   thay thế/thu hồi/khôi phục.
7. **Lập chỉ mục** — publication đã duyệt → chunk giữ nguồn/bảng → embedding qua ModelOps →
   generation Qdrant; dense, hybrid (FTS + RRF) và rerank.
8. **Hỏi đáp & trợ lý** — search → evidence → model chat qua ModelOps → kiểm tra trích dẫn và
   nguồn hiện hành → câu trả lời; hội thoại lưu owner, thứ tự lượt và idempotency.

## 5. Năng lực hiện có và chưa có

**Đã có (có mã + test):** workspace/membership/audit; ModelOps provider/key/default/grant/
quota/usage; kho tri thức + revision; OCR PDF/DOCX với MinerU; rà soát văn bản hậu OCR;
Compiler + review; publication lifecycle; index/search dense/hybrid/rerank; hỏi đáp có trích dẫn;
trợ lý + hội thoại; vòng đời ngược (dừng/hủy/thùng rác/khôi phục/xóa có điều kiện); readiness,
backup bằng chứng, dọn dữ liệu dẫn xuất; API tích hợp cho ứng dụng ngoài (app key + gateway).

**Chưa có:** DAG engine và tool gateway; kênh public (widget/Messenger/Zalo); streaming/SSE;
chia sẻ chatbot công khai; xuất Word Nghị định 30 / Excel Bloom; Structured Fact Layer, wiki,
glossary; benchmark/quality gate tự động cho RAG của V1.

**Provider runtime:** `provider_type` `ollama` và `llamacpp` đại diện cho runtime chat nội bộ
tương thích OpenAI; discovery của admin đọc `/api/tags` + `/api/show` (Ollama) và `/props`
(llama.cpp) để lấy cửa sổ ngữ cảnh do server công bố. `nemotron` và `paddleocr` đã bị loại khỏi
`ck_provider_type`; OCR vẫn dùng giao thức `nemotron_chat_completions` qua provider
`openai_compatible`/`local`. `gemini` chỉ tồn tại để tương thích dữ liệu cũ; registry đánh dấu
“chưa có adapter” và runtime từ chối bằng mã `*_provider_type_unsupported`. Hai module stub chỉ
ném `NotImplementedError` đã được xóa ngày 2026-11-09. OCR hiện hành là MinerU/native.

## 6. Công nghệ

| Lớp | Công nghệ |
|---|---|
| Backend | Python 3.12, FastAPI, SQLAlchemy async, Pydantic v2, Alembic |
| Worker | ARQ (asyncio), lease + reconcile |
| Dữ liệu | PostgreSQL 16, Redis 7, Qdrant |
| Tệp | MinIO/S3 (boto3) hoặc local |
| Xử lý tài liệu | PyMuPDF, PDF Inspector 1.25.2, Docling, Gotenberg 8, MinerU |
| Model | OpenAI-compatible chat, embedding, rerank — cấu hình qua ModelOps |
| Frontend | React 19, Vite 8, TanStack Router/Query/Form/Table, Radix/shadcn, Tailwind 4, Biome |
| Xác thực | Dev gate local; SSO OpenIddict authorization code + PKCE (RS256/JWKS) |

## 7. Tài liệu chi tiết

Backend: [architecture](../backendV1/docs/architecture.md) ·
[module boundaries](../backendV1/docs/module-boundaries.md) ·
[OCR](../backendV1/docs/ocr-processing.md) ·
[Compiler](../backendV1/docs/compiler-v1.md) ·
[publication](../backendV1/docs/compiled-publication.md) ·
[index](../backendV1/docs/dense-indexing.md) ·
[RAG answers](../backendV1/docs/rag-answers.md) ·
[ModelOps](../backendV1/docs/workspaces-modelops.md) ·
[readiness](../backendV1/docs/readiness.md).

Vận hành: [quy trình V1](./quy_trinh/README.md) ·
[chạy local](./quy_trinh/38_huong_dan_chay_qnu_v1.md) ·
[triển khai](./trien_khai/02_quy_trinh_trien_khai_dokploy.md) ·
[memory](./memory/PROJECT_CONTEXT.md).
