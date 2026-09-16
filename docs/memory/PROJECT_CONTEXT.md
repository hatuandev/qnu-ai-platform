# PROJECT_CONTEXT.md — Snapshot Ngữ Cảnh Dự Án QNU AI Platform

> **⚠️ QUAN TRỌNG**: AI Agent phải đọc file này NGAY ĐẦU mỗi phiên làm việc và cập nhật lại CUỐI mỗi phiên.
> Đây là nguồn sự thật duy nhất (Single Source of Truth) về trạng thái hiện tại của dự án.

---

## 1. Thông Tin Phiên Gần Nhất

- **Thời gian cập nhật**: 2026-09-16 23:30 (UTC+7)
- **Phiên số**: #33 (tính từ đầu dự án)
- **Agent**: AI Senior Full-Stack Architect & Enterprise AI Systems Specialist
- **Mục tiêu đã hoàn thành**: 
  1. **Hoàn thiện Cổng Trích Xuất & Biểu Mẫu Hành Chính (Lựa chọn A từ `qnu-ai-core`)**:
     - Xây dựng `DocxNd30Editor`: Form soạn thảo văn bản hành chính theo chuẩn Nghị định 30/2020/NĐ-CP, kèm khung xem trước tờ giấy A4 trực quan (`nd30-paper-preview`) căn lề 20-20-30-15mm, phông Times New Roman, kẻ chân quốc hiệu/tiêu ngữ và bảng chữ ký, xuất file Word `.docx`.
     - Xây dựng `BloomMatrixEditor`: Trình thiết kế ma trận phân phối đề thi theo 4 cấp độ tư duy Bloom (Nhận biết, Thông hiểu, Vận dụng, Vận dụng cao), tự động tính tổng câu, điểm số và biểu đồ tỷ lệ %, xuất bảng tính Excel `.xlsx`.
     - Xây dựng `UisAdmissionsExplorer`: Cổng tra cứu trực quan dữ liệu điểm chuẩn 3 năm gần nhất, tổ hợp môn, chỉ tiêu và học phí các ngành đào tạo ĐH Quy Nhơn thời gian thực.
     - Xây dựng `AdministrativeTemplatesView`: Thư viện 6 phôi mẫu văn bản nhà trường kèm danh sách placeholder và nút **"Nạp Vào Form Soạn Thảo (1-Click Fill)"**.
     - Tích hợp 4 Tabs chuyên môn tại `ToolsPage` (`/tools`).
  2. **Kiểm thử E2E Playwright 100% Pass**: Bộ test `08_tools_and_templates_export.spec.ts` đạt 3/3 tests pass (11.7s) trên Google Chrome với 3 ảnh chụp màn hình nghiệm thu trực quan.
  3. **Kiểm tra chất lượng Clean Code**: Biome 0 lỗi, TypeScript 0 lỗi, Vite build đóng gói thành công 100%, Ruff 0 lỗi.

---

## 2. Tổng Quan Dự Án

| Thuộc Tính | Giá Trị |
| :--- | :--- |
| **Tên dự án** | QNU AI Platform |
| **Tổ chức** | Trường Đại học Quy Nhơn (QNU) |
| **Workspace** | `D:\DuAnPhanMem\qnu-ai-platform` |
| **Backend** | `D:\DuAnPhanMem\qnu-ai-platform\backend` |
| **Frontend** | `D:\DuAnPhanMem\qnu-ai-platform\frontend` (Port 3001) |
| **Ref codebase cũ** | `D:\DuAnPhanMem\qnu-ai-core` (Port 3000) |
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
| 5 | Module ModelOps (Provider Presets, Key Pool 429 Failover, Circuit Breaker) | ✅ Done |
| 6 | Module Tools (UIS Admissions Query, Word NĐ 30, Excel Bloom) | ✅ Done |
| 7 | Module Evaluation (Ragas TM-08: Faithfulness, Relevance, Precision) | ✅ Done |
| 8 | Module Workflows (DAG Pipeline, ARQ Workers, Guardrails) | ✅ Done |

**Backend Test Suite**: 73/73 tests passed | Ruff: 0 errors

---

### ✅ Frontend (7/7 Giai Đoạn — HOÀN THÀNH & NÂNG CẤP TOÀN DIỆN)

| Giai Đoạn | Mô Tả | Trạng Thái |
| :--- | :--- | :---: |
| 1 | Scaffolding Vite 6 + React 19 + TypeScript + Biome + OKLCH Design Tokens | ✅ Done |
| 2 | 21 UI Primitives + 6 Admin Helpers + Design System Showcase | ✅ Done |
| 3 | AdminShell (AppSidebar, Topbar, CommandMenu, ThemeProvider) | ✅ Done |
| 4 | AI Suite (useRAGStream, ChatMessage, CitationSheet, Attachment, QuestionnaireCard, DAGCanvas) | ✅ Done |
| 5 | API Integration (TanStack Query) + 9 Business Screens + 15 Routes fully wired | ✅ Done |
| 6 | **Visual DAG Workflow Studio (Lựa chọn B từ QNU-AI-Core)**: In-Canvas Test Runner, 8 Custom Nodes, Catalog Drawer, Property Inspector, 5 Workflows | ✅ Done |
| 7 | **Administrative Document & Tool Studio (Lựa chọn A từ QNU-AI-Core)**: Docx NĐ 30 Editor with Live Paper Preview, Bloom Matrix Excel Exporter, UIS Live Explorer, Templates Library (1-Click Fill) | ✅ Done |

**Frontend Checks**: Biome 0 errors | TypeScript 0 errors | Vite build ✓ (1,200 kB) | Playwright E2E: 21/21 passed

---

## 4. Hệ Thống Kỹ Năng Agent (Skills Registry)

Dự án hiện có **07 bộ kỹ năng chuẩn hóa** tại `.agents/skills/`:

| Skill | Vị Trí | Mô Tả |
| :--- | :--- | :--- |
| **`qnu-frontend-architect`** | [`.agents/skills/qnu-frontend-architect/SKILL.md`](../../.agents/skills/qnu-frontend-architect/SKILL.md) | Kiến trúc React 19, UI Rules, OKLCH Tokens, Biome, 3-tier components |
| **`qnu-backend-architect`** | [`.agents/skills/qnu-backend-architect/SKILL.md`](../../.agents/skills/qnu-backend-architect/SKILL.md) | Chuẩn 4 tệp tin, Strategy/Pipeline/Adapter, RFC 7807 |
| **`qnu-chatbot-builder`** | [`.agents/skills/qnu-chatbot-builder/SKILL.md`](../../.agents/skills/qnu-chatbot-builder/SKILL.md) | Vòng đời 7 bước tạo mới và cấu hình Trợ lý AI QNU |
| **`qnu-rag-pipeline`** | [`.agents/skills/qnu-rag-pipeline/SKILL.md`](../../.agents/skills/qnu-rag-pipeline/SKILL.md) | Qdrant Dense, FTS Lexical, RRF k=60, Cross-Encoder, Fact Layer |
| **`qnu-knowledge-ingestion`** | [`.agents/skills/qnu-knowledge-ingestion/SKILL.md`](../../.agents/skills/qnu-knowledge-ingestion/SKILL.md) | Ingestion pipeline, OCR đa tầng, Clause-based chunking |
| **`qnu-modelops-resilience`** | [`.agents/skills/qnu-modelops-resilience/SKILL.md`](../../.agents/skills/qnu-modelops-resilience/SKILL.md) | LLM Adapters, Circuit Breaker 3 trạng thái, Quota, Cost Tracker |
| **`qnu-clean-code-architect`** | [`.agents/skills/qnu-clean-code-architect/SKILL.md`](../../.agents/skills/qnu-clean-code-architect/SKILL.md) | Chuẩn mực Clean Code khi Vibe Coding: Boy Scout Rule, Zero Any/Dead Code, SRP |

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
Vite 6 + React 19 + TypeScript 5 (port 3001)
├── Tailwind CSS v4 (OKLCH Design Tokens — Academic Teal)
├── Biome 2 (Linter + Formatter)
├── TanStack Query v5 (Server state management)
├── @xyflow/react v12 (Visual DAG Studio, 8 Custom Nodes, Live Pulse Animation)
├── Document Studio (Docx NĐ 30 Live Paper Sheet, Bloom Excel Matrix, UIS Live Explorer, Templates Library)
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
│   ├── admin/        # 13 Admin Helpers (DocxNd30Editor, BloomMatrixEditor, UisAdmissionsExplorer, AdministrativeTemplatesView, InCanvasTestRunner, NodeCatalogDrawer, PropertyInspector, ...)
│   └── ai/           # AI Suite (ChatBubble, ChatMessage, CitationSheet, DAGCanvas with 8 custom node types, ...)
├── hooks/            # useRAGStream (SSE streaming hook)
├── layouts/          # AdminShell, AppSidebar, Topbar, CommandMenu
├── lib/              # query-client.ts (TanStack QueryClient)
├── navigation/       # config.ts (NAVIGATION_CONFIG — 15 routes)
├── pages/            # 13 màn hình (Dashboard, Knowledge, ModelOps, DAG Canvas Studio, Tools Studio, ...)
└── services/         # api-client.ts (REST endpoints + executeWorkflow + executeTool + Offline Seed Fallback)
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
| `/nodes` | `dag-canvas-page.tsx` | Visual DAG Canvas Studio (5 Luồng, Test Runner, Catalog, Inspector) |
| `/tools` | `tools-page.tsx` | **Studio Xuất Bản Tài Liệu NĐ 30, Ma Trận Bloom, Cổng UIS, Thư Viện Phôi Mẫu** |
| `/evaluation` | `evaluation-page.tsx` | Kiểm định Ragas TM-08 + Gap Inbox |
| `/models` | `modelops-page.tsx` | Model Providers + Circuit Breaker |
| `/developer` | `developer-page.tsx` | API Keys + SDK Snippets |
| `/design-system` | `design-system-page.tsx` | Design System Showcase |

---

## 9. Các Điểm Chú Ý Kỹ Thuật Quan Trọng

### Port Configuration
- Frontend chạy trên cổng **`3001`** (`http://localhost:3001`) độc lập với `qnu-ai-core` (cổng `3000`).

### Decree 30/2020/ND-CP Formatter
- Lề trang chuẩn: Trên 20mm, Dưới 20mm, Trái 30mm (đóng gáy), Phải 15mm.
- Quốc hiệu, Tiêu ngữ căn giữa, gạch chân chuẩn tỷ lệ.
- Phông chữ chuẩn Times New Roman (12-13pt), thụt đầu đoạn 1cm - 1.27cm.

### Bloom Taxonomy Exam Matrix
- 4 Cấp độ: Nhận biết (Remember), Thông hiểu (Understand), Vận dụng (Apply), Vận dụng cao (Analyze/Create).
- Biểu đồ tỷ lệ 4 màu trực quan tự động tính toán tổng số câu, điểm số và phần trăm.

---

## 10. Giai Đoạn Tiếp Theo (Backlog)

> Cả 2 Lựa chọn A (Studio Xuất Bản Biểu Mẫu Hành Chính) và B (Visual DAG Workflow Studio) kế thừa từ `qnu-ai-core` đã hoàn thành xuất sắc.
> Các định hướng tiếp theo có thể cân nhắc:

- [ ] **Authentication**: Đăng nhập JWT, phân quyền cán bộ/sinh viên
- [ ] **Real-time Notifications**: WebSocket hoặc SSE thông báo tiến trình nạp tài liệu
- [ ] **Mobile Responsive**: Tối ưu layout cho thiết bị di động
- [ ] **Code Splitting**: Dynamic imports tách nhỏ bundle

---

*Snapshot được tạo lúc: 2026-09-16 23:30 UTC+7*
