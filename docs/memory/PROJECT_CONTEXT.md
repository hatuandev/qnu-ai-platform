# PROJECT_CONTEXT.md â€” Snapshot Ngá»¯ Cáº£nh Dá»± Ãn QNU AI Platform

> **âš ï¸ QUAN TRá»ŒNG**: AI Agent pháº£i Ä‘á»c file nÃ y NGAY Äáº¦U má»—i phiÃªn lÃ m viá»‡c vÃ  cáº­p nháº­t láº¡i CUá»I má»—i phiÃªn.
> ÄÃ¢y lÃ  nguá»“n sá»± tháº­t duy nháº¥t (Single Source of Truth) vá» tráº¡ng thÃ¡i hiá»‡n táº¡i cá»§a dá»± Ã¡n.

---

## 1. ThÃ´ng Tin PhiÃªn Gáº§n Nháº¥t

- **Thá»i gian cáº­p nháº­t**: 2026-09-17 09:30 (UTC+7)
- **PhiÃªn sá»‘**: #35 (tÃ­nh tá»« Ä‘áº§u dá»± Ã¡n)
- **Agent**: AI Senior Full-Stack Architect & Enterprise AI Systems Specialist
- **Má»¥c tiÃªu Ä‘Ã£ hoÃ n thÃ nh**: 
  1. **Kháº¯c phá»¥c Triá»‡t Äá»ƒ Váº¥n Äá» Hiá»ƒn Thá»‹ Scan & Markdown Studio (Äá»“ng bá»™ 100% vá»›i `qnu-ai-core`)**:
     - **Sao chÃ©p vÃ  Ä‘á»“ng bá»™ toÃ n bá»™ 14 trang áº£nh scan thá»±c táº¿ 300 DPI**: TrÃ­ch xuáº¥t trá»±c tiáº¿p tá»« kho OCR cache cá»§a `qnu-ai-core` (`services/studio-ui/public/ocr-cache/ccbf29700d/`) sang `frontend/public/ocr-cache/doc_ts_2026/` (`page_1.jpg` Ä‘áº¿n `page_14.jpg`).
     - **Thay tháº¿ hoÃ n toÃ n bá»™ giáº£ láº­p HTML cÅ© báº±ng tháº» `<img>` áº£nh scan tháº­t**: Loáº¡i bá» hoÃ n toÃ n khá»‘i div giáº£ láº­p vÄƒn báº£n thÃ´, giáº£i quyáº¿t dá»©t Ä‘iá»ƒm tÃ¬nh tráº¡ng trang 3 Ä‘áº¿n 14 bá»‹ tráº¯ng tinh. Lá»›p phá»§ Bounding Boxes hiá»ƒn thá»‹ chÃ­nh xÃ¡c theo tá»· lá»‡ % OpenCV trÃªn áº£nh scan tháº­t.
     - **Render Markdown chuáº©n xÃ¡c qua `ReactMarkdown` + `remarkGfm`**: Cá»™t pháº£i thay tháº¿ viá»‡c in text thÃ´ báº±ng bá»™ component render GitHub-Flavored Markdown chuáº©n má»±c: Báº£ng biá»ƒu tuyá»ƒn sinh (53 ngÃ nh, chá»‰ tiÃªu, tá»• há»£p mÃ´n, Ä‘iá»ƒm chuáº©n 2 nÄƒm 2024-2025, báº£ng quy Ä‘á»•i IELTS/VSTEP, phá»¥ lá»¥c xÃ©t tuyá»ƒn tháº³ng) cÃ³ viá»n báº£ng, header xÃ¡m, alternating row colors, blockquote Academic Teal trÃ­ch dáº«n vÄƒn báº£n quy pháº¡m.
     - **Cáº£i tiáº¿n cháº¿ Ä‘á»™ Sá»­a tay (Human-in-the-loop)**: Bá»• sung nÃºt chuyá»ƒn Ä‘á»•i "Xem trÆ°á»›c" (Preview) vÃ  "Quay láº¡i sá»­a" trá»±c tiáº¿p trong textarea, cho phÃ©p cÃ¡n bá»™ kiá»ƒm tra káº¿t quáº£ render Markdown trÆ°á»›c khi lÆ°u hoáº·c náº¡p vÃ o Vector DB.
  2. **TÃ¡ch Module Dá»¯ Liá»‡u Theo Chuáº©n Clean Code (Rule 8 AGENTS.md)**:
     - Táº¡o tá»‡p Ä‘á»™c láº­p `frontend/src/services/verification-data.ts` (1,393 dÃ²ng, 69KB) chá»©a toÃ n bá»™ dá»¯ liá»‡u bÃ³c tÃ¡ch, bounding boxes vÃ  layout regions cá»§a 14 trang scan Äá» Ã¡n tuyá»ƒn sinh 2026, giáº£i phÃ³ng dung lÆ°á»£ng cho `api-client.ts`.
     - Sá»­a lá»—i PEP 8 E402 trong `backend/app/main.py`.
  3. **Kiá»ƒm thá»­ ToÃ n Diá»‡n & Äáº¡t TiÃªu Chuáº©n Sáº£n Pháº©m 100%**:
     - `uv run ruff check .`: All checks passed (0 lá»—i).
     - `npm run lint`: Biome check 0 lá»—i, 0 cáº£nh bÃ¡o.
     - `npm run typecheck`: TypeScript tsc --noEmit 0 lá»—i.
     - `npm run build`: Vite build thÃ nh cÃ´ng Ä‘Ã³ng gÃ³i production bundle.
     - `npx playwright test tests/e2e/09_knowledge_ingestion_studio.spec.ts --project="Google Chrome"`: 3/3 tests passed (18.6s).

---

## 2. Tá»•ng Quan Dá»± Ãn

| Thuá»™c TÃ­nh | GiÃ¡ Trá»‹ |
| :--- | :--- |
| **TÃªn dá»± Ã¡n** | QNU AI Platform |
| **Tá»• chá»©c** | TrÆ°á»ng Äáº¡i há»c Quy NhÆ¡n (QNU) |
| **Workspace** | `D:\DuAnPhanMem\qnu-ai-platform` |
| **Backend** | `D:\DuAnPhanMem\qnu-ai-platform\backend` (FastAPI, Port 8001) |
| **Frontend** | `D:\DuAnPhanMem\qnu-ai-platform\frontend` (Vite 6 + React 19, Port 3001) |
| **Codebase gá»‘c tham kháº£o** | `D:\DuAnPhanMem\qnu-ai-core` (FastAPI + Streamlit/Vite Studio, Port 3000) |

---

## 3. Tráº¡ng ThÃ¡i HoÃ n ThÃ nh CÃ¡c Giai Äoáº¡n

### âœ… Backend (8/8 Giai Äoáº¡n â€” HOÃ€N THÃ€NH)

| Giai Äoáº¡n | MÃ´ Táº£ | Tráº¡ng ThÃ¡i |
| :--- | :--- | :---: |
| 1 | Scaffolding FastAPI + Cáº¥u hÃ¬nh háº¡ táº§ng 7 dá»‹ch vá»¥ | âœ… Done |
| 2 | Module Assistants (05 Trá»£ lÃ½ QNU) | âœ… Done |
| 3 | Module Knowledge (Collections, Ingestion Pipeline, OCR Ä‘a táº§ng) | âœ… Done |
| 4 | Module RAG (Hybrid RRF k=60, Cross-Encoder Reranking, Structured Fact Layer) | âœ… Done |
| 5 | Module ModelOps (Provider Presets, Key Pool 429 Failover, Circuit Breaker) | âœ… Done |
| 6 | Module Tools (UIS Admissions Query, Word NÄ 30, Excel Bloom) | âœ… Done |
| 7 | Module Evaluation (Ragas TM-08: Faithfulness, Relevance, Precision) | âœ… Done |
| 8 | Module Workflows (DAG Pipeline, ARQ Workers, Guardrails) | âœ… Done |

**Backend Quality**: 73/73 tests passed | Ruff: 0 errors

---

### âœ… Frontend (8/8 Giai Äoáº¡n â€” HOÃ€N THÃ€NH & Äá»’NG Bá»˜ 100% Vá»šI QNU-AI-CORE)

| Giai Äoáº¡n | MÃ n HÃ¬nh / Module | Tráº¡ng ThÃ¡i |
| :--- | :--- | :---: |
| 1 | Master Layout (Sidebar w-64, Topbar h-14, Academic Teal oklch) | âœ… Done |
| 2 | Assistants Studio (05 Trá»£ lÃ½, Persona, ModelOps config, Tool Gateway) | âœ… Done |
| 3 | Knowledge Management & Master-Detail Navigation (List + Detail + Ingest + Full Studio) | âœ… Done |
| 4 | Document Verification Studio (Full 14 scan pages, BBoxes, Regions, ReactMarkdown Tables, In-place Edit) | âœ… Done |
| 5 | Omni-Channel Chat Studio (SSE Streaming, Thinking Indicator, CitationSheet) | âœ… Done |
| 6 | ModelOps Dashboard (4 Presets, Secret Key Masking, Circuit Breaker Monitor) | âœ… Done |
| 7 | Tools Gateway (Word NÄ 30 Preview, Excel Bloom Matrix, Template Library) | âœ… Done |
| 8 | Workflow DAG Canvas (@xyflow/react, 6 Custom Node types, Run DAG & Inspector) | âœ… Done |

**Frontend Quality**:
- Biome Linter: 0 errors
- TypeScript: 0 errors
- Vite Build: 100% passed
- Playwright E2E Suites: 9 suites passed (Bao gá»“m Suite 09 Studio)

---

## 4. Danh Má»¥c Gotchas Ká»¹ Thuáº­t (Kinh Nghiá»‡m Thá»±c Táº¿)

1. **Strict Mode trong Playwright**:
   - Khi cÃ³ text xuáº¥t hiá»‡n á»Ÿ cáº£ thanh Breadcrumb/Header vÃ  trong thÃ¢n trang (vÃ­ dá»¥ `Trang 1 / 14`), báº¯t buá»™c pháº£i dÃ¹ng `page.getByText('Trang 1 / 14', { exact: true })` hoáº·c `.first()` Ä‘á»ƒ trÃ¡nh lá»—i `strict mode violation`.
2. **Hiá»ƒn thá»‹ áº¢nh Scan TÃ i Liá»‡u BÃ³c TÃ¡ch**:
   - KhÃ´ng Ä‘Æ°á»£c dÃ¹ng text/HTML mock Ä‘á»ƒ giáº£ láº­p trang scan. Báº¯t buá»™c pháº£i phá»¥c vá»¥ áº£nh scan tháº­t tá»« thÆ° má»¥c tÄ©nh `frontend/public/ocr-cache/doc_ts_2026/page_N.jpg` vá»›i tá»‰ lá»‡ khung hÃ¬nh chuáº©n A4 vÃ  zoom container.
3. **Render Báº£ng Biá»ƒu Markdown**:
   - Markdown thÃ´ (`whitespace-pre-wrap`) khÃ´ng hiá»ƒn thá»‹ Ä‘Æ°á»£c báº£ng. Báº¯t buá»™c dÃ¹ng `ReactMarkdown` vá»›i plugin `remarkGfm` vÃ  custom `components={{ table, thead, th, td, tr }}` cÃ³ styling viá»n Ã´ rÃµ rÃ ng.
4. **PEP 8 E402 trong Backend**:
   - Khi xá»­ lÃ½ Ä‘oáº¡n mÃ£ sá»­a lá»—i Windows IPv6 `no_proxy`, Ä‘áº·t Ä‘oáº¡n sanitize sau toÃ n bá»™ module imports chuáº©n Ä‘á»ƒ ruff check 0 lá»—i.

---

## 5. Backlog & Káº¿ Hoáº¡ch Tiáº¿p Theo

- [x] Äá»“ng bá»™ áº£nh scan thá»±c táº¿ 14 trang tá»« `qnu-ai-core` vÃ o Studio Ä‘á»‘i soÃ¡t.
- [x] Render Markdown báº£ng biá»ƒu vÃ  cáº¥u trÃºc phÃ¢n cáº¥p chuáº©n GitHub Flavored Markdown.
- [x] ThÃªm cháº¿ Ä‘á»™ xem trÆ°á»›c (Preview) khi hiá»‡u Ä‘Ã­nh vÄƒn báº£n trong cháº¿ Ä‘á»™ Sá»­a tay (Human-in-the-loop).
- [ ] TÃ­ch há»£p API backend thá»±c táº¿ cho endpoint bÃ³c tÃ¡ch Ä‘a táº§ng qua Docling microservice.
- [ ] Má»Ÿ rá»™ng cÆ¡ cháº¿ kÃ©o tháº£ trá»±c tiáº¿p khung Bounding Box trÃªn áº£nh scan Ä‘á»ƒ cáº­p nháº­t tá»a Ä‘á»™ ROI cho ngÆ°á»i dÃ¹ng cÃ¡n bá»™.
