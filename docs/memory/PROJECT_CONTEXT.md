# PROJECT_CONTEXT.md — Snapshot Ngữ Cảnh Dự Án QNU AI Platform

> **⚠️ QUAN TRỌNG**: AI Agent phải đọc file này NGAY ĐẦU mỗi phiên làm việc và cập nhật lại CUỐI mỗi phiên.
> Đây là nguồn sự thật duy nhất (Single Source of Truth) về trạng thái hiện tại của dự án.

---

## 1. Thông Tin Phiên Gần Nhất

- **Thời gian cập nhật**: 2026-09-16 09:55 (UTC+7)
- **Phiên số**: #14 (tính từ đầu dự án)
- **Agent**: AI Senior Full-Stack Architect & Enterprise AI Systems Specialist
- **Mục tiêu đã hoàn thành**: Thiết lập hoàn chỉnh hệ sinh thái Auto Testing chuẩn Enterprise: Tích hợp Playwright MCP Server, xây dựng bộ 3 test suite Playwright E2E (12/12 tests PASS 100%), khắc phục lỗi thiếu `TooltipProvider` khi thu gọn thanh bên và chuẩn hóa `h3` locators trong `03_knowledge_tools.spec.ts`. Bảo đảm 100% test suite toàn hệ thống xanh mướt (Pytest 68/68 + Playwright 12/12, 0 lỗi Biome, 0 lỗi TypeScript).

---

## 2. Tổng Quan Dự Án

| Thuộc Tính | Giá Trị |
| :--- | :--- |
| **Tên dự án** | QNU AI Platform |
| **Tổ chức** | Trường Đại học Quy Nhơn (QNU) |
| **Workspace** | `D:\DuAnPhanMem\qnu-ai-platform` |
| **Backend** | `D:\DuAnPhanMem\qnu-ai-platform\backend` |
| **Frontend** | `D:\DuAnPhanMem\qnu-ai-platform\frontend` |
| **Ref codebase cũ** | `D:\DuAnPhanMem\qnu-ai-core` |
| **Tham khảo QLKTX** | `D:\DuAnPhanMem\QLKTX\qnu-ktx\src\Web\ClientApp` |

---

## 3. Trạng Thái Hoàn Thành Các Giai Đoạn

### ✅ Backend (8/8 Giai Đoạn — HOÀN THÀNH)

| Giai Đoạn | Mô Tả | Trạng Thái |
| :--- | :--- | :---: |
| 1 | Scaffolding FastAPI + Cấu hình hạ tầng 7 dịch vụ | ✅ Done |
| 2 | Module Assistants (05 Trợ lý QNU) | ✅ Done |
| 3 | Module Knowledge (Collections, Ingestion Pipeline, OCR đa tầng) | ✅ Done |
| 4 | Module RAG (Hybrid RRF k=60, Cross-Encoder Reranking, Structured Fact Layer) | ✅ Done |
| 5 | Module ModelOps (Circuit Breaker, Dynamic Fallback, Cost Tracker, Quota) | ✅ Done |
| 6 | Module Tools (UIS Admissions Query, Word NĐ 30, Excel Bloom) | ✅ Done |
| 7 | Module Evaluation (Ragas TM-08: Faithfulness, Relevance, Precision) | ✅ Done |
| 8 | Module Workflows (DAG Pipeline, ARQ Workers, Guardrails) | ✅ Done |

**Backend Test Suite**: 68/68 tests passed | Ruff: 0 errors

---

### ✅ Frontend (5/5 Giai Đoạn — HOÀN THÀNH)

| Giai Đoạn | Mô Tả | Trạng Thái |
| :--- | :--- | :---: |
| 1 | Scaffolding Vite 6 + React 19 + TypeScript + Biome + OKLCH Design Tokens | ✅ Done |
| 2 | 21 UI Primitives + 6 Admin Helpers + Design System Showcase | ✅ Done |
| 3 | AdminShell (AppSidebar, Topbar, CommandMenu, ThemeProvider) | ✅ Done |
| 4 | AI Suite (useRAGStream, ChatMessage, CitationSheet, Attachment, QuestionnaireCard, DAGCanvas) | ✅ Done |
| 5 | API Integration (TanStack Query) + 9 Business Screens + 15 Routes fully wired | ✅ Done |

**Frontend Checks**: Biome 0 errors | TypeScript 0 errors | Vite build ✓ (1,010 kB / 303 kB gzip)

---

## 4. Hệ Thống Kỹ Năng Agent (Skills Registry)

Dự án hiện có **06 bộ kỹ năng chuẩn hóa** tại `.agents/skills/`:

| Skill | Vị Trí | Mô Tả |
| :--- | :--- | :--- |
| **`qnu-frontend-architect`** | [`.agents/skills/qnu-frontend-architect/SKILL.md`](../../.agents/skills/qnu-frontend-architect/SKILL.md) | Kiến trúc React 19, UI Rules, OKLCH Tokens, Biome, 3-tier components |
| **`qnu-backend-architect`** | [`.agents/skills/qnu-backend-architect/SKILL.md`](../../.agents/skills/qnu-backend-architect/SKILL.md) | Chuẩn 4 tệp tin, Strategy/Pipeline/Adapter, RFC 7807 |
| **`qnu-chatbot-builder`** | [`.agents/skills/qnu-chatbot-builder/SKILL.md`](../../.agents/skills/qnu-chatbot-builder/SKILL.md) | Vòng đời 7 bước tạo mới và cấu hình Trợ lý AI QNU |
| **`qnu-rag-pipeline`** | [`.agents/skills/qnu-rag-pipeline/SKILL.md`](../../.agents/skills/qnu-rag-pipeline/SKILL.md) | Qdrant Dense, FTS Lexical, RRF k=60, Cross-Encoder, Fact Layer |
| **`qnu-knowledge-ingestion`** | [`.agents/skills/qnu-knowledge-ingestion/SKILL.md`](../../.agents/skills/qnu-knowledge-ingestion/SKILL.md) | Ingestion pipeline, OCR đa tầng, Clause-based chunking |
| **`qnu-modelops-resilience`** | [`.agents/skills/qnu-modelops-resilience/SKILL.md`](../../.agents/skills/qnu-modelops-resilience/SKILL.md) | LLM Adapters, Circuit Breaker 3 trạng thái, Quota, Cost Tracker |

---

## 5. Kiến Trúc Hệ Thống Hiện Tại

### Stack Công Nghệ Backend
```
FastAPI + Uvicorn (port 8001)
├── PostgreSQL 16       (port 5432) — Structured Facts + FTS
├── Qdrant Vector DB    (port 6333) — 1024D BGE-M3 embeddings
├── Redis 7             (port 6379) — Cache + ARQ task queue
├── MinIO S3            (port 9000) — Object storage (knowledge-raw, knowledge-processed)
├── ARQ Workers                     — Async ingestion pipeline
└── Docling / PyMuPDF / EasyOCR    — OCR document parsing
```

### Stack Công Nghệ Frontend
```
Vite 6 + React 19 + TypeScript 5
├── Tailwind CSS v4 (OKLCH Design Tokens — Academic Teal)
├── Biome 2 (Linter + Formatter)
├── TanStack Query v5 (Server state management)
├── @xyflow/react v12 (DAG Canvas visualization)
├── Radix UI + shadcn/ui primitives
└── lucide-react icons
```

---

## 6. Cấu Trúc Module Backend (`backend/app/modules/`)

```
modules/
├── assistants/     # 05 Trợ lý QNU (Tuyển sinh, Quy chế, Thư viện, Soạn thảo, Đề thi)
├── knowledge/      # Collections, Documents, Ingestion Pipeline
├── rag/            # Hybrid RAG (Qdrant + PostgreSQL FTS + RRF + Reranker)
├── modelops/       # LLM Providers, Circuit Breaker, Quota, Cost Tracker
├── tools/          # UIS Admissions Query, Word NĐ 30 Export, Excel Bloom Export
├── evaluation/     # Ragas TM-08 metrics, Gap Inbox
└── workflows/      # DAG execution, ARQ Workers, Guardrails
```

---

## 7. Cấu Trúc Màn Hình Frontend (`frontend/src/`)

```
src/
├── components/
│   ├── ui/           # 21 UI Primitives (Button, Card, Badge, Dialog, Table, Tabs, ...)
│   ├── admin/        # 6 Admin Helpers (EmptyState, KpiMetric, StatusBadge, ...)
│   └── ai/           # AI Suite (ChatBubble, ChatMessage, CitationSheet, DAGCanvas, ...)
├── hooks/            # useRAGStream (SSE streaming hook)
├── layouts/          # AdminShell, AppSidebar, Topbar, CommandMenu
├── lib/              # query-client.ts (TanStack QueryClient)
├── navigation/       # config.ts (NAVIGATION_CONFIG — 15 routes)
├── pages/            # 13 màn hình (Dashboard, Knowledge, ModelOps, Tools, ...)
└── services/         # api-client.ts (REST endpoints + Offline Seed Fallback)
```

---

## 8. Các Màn Hình (Pages) Hiện Có

| Route | File | Mô Tả |
| :--- | :--- | :--- |
| `/` | `dashboard-page.tsx` | Bảng điều khiển: KPI, FinOps, TM-08, Backend Ping |
| `/assistants` | `App.tsx` (inline) | Danh mục 05 Trợ lý AI chuẩn QNU |
| `/chat` | `chat-studio-page.tsx` | Studio Chat SSE Toàn năng |
| `/conversations` | `conversations-page.tsx` | Lịch sử hội thoại + Human Handoff |
| `/channels` | `channels-page.tsx` | Web Chat Widget Embed Generator |
| `/runs` | `runs-page.tsx` | Lịch sử thực thi DAG + Trace |
| `/knowledge` | `knowledge-page.tsx` | Quản trị tri thức + Ingestion Wizard |
| `/document-types` | `knowledge-page.tsx` | Dùng chung KnowledgePage |
| `/nodes` | `dag-canvas-page.tsx` | Visual DAG Canvas Studio |
| `/tools` | `tools-page.tsx` | Cổng công cụ QNU + Tool Playground |
| `/evaluation` | `evaluation-page.tsx` | Kiểm định Ragas TM-08 + Gap Inbox |
| `/models` | `modelops-page.tsx` | Model Providers + Circuit Breaker |
| `/developer` | `developer-page.tsx` | API Keys + SDK Snippets |
| `/design-system` | `design-system-page.tsx` | Design System Showcase |

---

## 9. Các Điểm Chú Ý Kỹ Thuật Quan Trọng

### Biome Linter Gotchas
- Số `0.000` → dùng `0` hoặc `0.0` (tránh `lint/suspicious/noApproximativeNumericConstant`)
- Không dùng `key={idx}` trong danh sách — luôn dùng ID duy nhất
- Label không có `htmlFor` → dùng `<span>` thay thế
- Không dùng `role="user"` / `role="assistant"` trên DOM — vi phạm WAI-ARIA
- Imports phải được sắp xếp theo thứ tự alphabet (Biome tự organize imports)

### Pytest Windows
- Luôn chạy: `uv run --extra dev pytest` (có `--basetemp=.pytest_temp` trong pyproject.toml)
- **Không** dùng `uv run pytest` thẳng (lỗi temp dir trên Windows)
- Biến môi trường `no_proxy` trên Windows chứa `::1` khiến `httpx` crash (`Invalid port: ':1'`) -> đã tự động làm sạch trong `tests/conftest.py`.

### Docker Compose Stack
- `docker-compose.yml`: Dành riêng cho 5 dịch vụ hạ tầng (`postgres:16`, `qdrant:latest`, `redis:7-alpine`, `minio:RELEASE.2025-04-22T22-12-26Z`, `gotenberg:8`).
- Khởi chạy chỉ cần: `docker compose up -d` (toàn bộ 5/5 containers đạt trạng thái `healthy` ngay lập tức).
- Qdrant healthcheck dùng bash TCP socket test `bash -c ': >/dev/tcp/127.0.0.1/6333'` do image không có sẵn `curl`.

### API Client
- Base URL: `/platform/v1alpha1/` (proxy qua Vite dev server)
- Offline Seed Fallback: tự động khi `fetch()` thất bại — không cần xử lý thêm
- Tất cả endpoints đều async với TanStack Query `useQuery()`

---

## 10. Giai Đoạn Tiếp Theo (Backlog)

> Dự án đã hoàn tất 5 giai đoạn Frontend và hệ thống Skill / Memory.
> Các hạng mục có thể triển khai tiếp theo (chưa được lên kế hoạch chính thức):

- [ ] **Authentication**: Đăng nhập JWT, phân quyền tenant/admin
- [ ] **Real-time Notifications**: WebSocket hoặc SSE cho trạng thái ingestion
- [ ] **Analytics Dashboard**: Biểu đồ thống kê nâng cao (Recharts / Victory)
- [ ] **Mobile Responsive**: Tối ưu giao diện cho màn hình nhỏ
- [x] **E2E Testing Setup**: Đã tích hợp Playwright MCP Server kết nối trực tiếp Chrome cho AI Auto Testing
- [ ] **i18n**: Đa ngôn ngữ Tiếng Việt / Tiếng Anh
- [ ] **Code Splitting**: Tách bundle theo route để tối ưu hiệu năng tải trang

---

*Snapshot được tạo lúc: 2026-09-15 22:20 UTC+7*
*Phiên tiếp theo: Đọc section 10 (Backlog) để xác định ưu tiên tiếp theo với người dùng.*
