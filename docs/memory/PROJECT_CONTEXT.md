# PROJECT_CONTEXT.md — Snapshot Ngữ Cảnh Dự Án QNU AI Platform

> **⚠️ QUAN TRỌNG**: AI Agent phải đọc file này NGAY ĐẦU mỗi phiên làm việc và cập nhật lại CUỐI mỗi phiên.
> Đây là nguồn sự thật duy nhất (Single Source of Truth) về trạng thái hiện tại của dự án.

---

## 1. Thông Tin Phiên Gần Nhất

- **Thời gian cập nhật**: 2026-09-17 09:30 (UTC+7)
- **Phiên số**: #35 (tính từ đầu dự án)
- **Agent**: AI Senior Full-Stack Architect & Enterprise AI Systems Specialist
- **Mục tiêu đã hoàn thành**: 
  1. **Khắc phục Triệt Để Vấn Đề Hiển Thị Scan & Markdown Studio (Đồng bộ 100% với `qnu-ai-core`)**:
     - **Sao chép và đồng bộ toàn bộ 14 trang ảnh scan thực tế 300 DPI**: Trích xuất trực tiếp từ kho OCR cache của `qnu-ai-core` (`services/studio-ui/public/ocr-cache/ccbf29700d/`) sang `frontend/public/ocr-cache/doc_ts_2026/` (`page_1.jpg` đến `page_14.jpg`).
     - **Thay thế hoàn toàn bộ giả lập HTML cũ bằng thẻ `<img>` ảnh scan thật**: Loại bỏ hoàn toàn khối div giả lập văn bản thô, giải quyết dứt điểm tình trạng trang 3 đến 14 bị trắng tinh. Lớp phủ Bounding Boxes hiển thị chính xác theo tỷ lệ % OpenCV trên ảnh scan thật.
     - **Render Markdown chuẩn xác qua `ReactMarkdown` + `remarkGfm`**: Cột phải thay thế việc in text thô bằng bộ component render GitHub-Flavored Markdown chuẩn mực: Bảng biểu tuyển sinh (53 ngành, chỉ tiêu, tổ hợp môn, điểm chuẩn 2 năm 2024-2025, bảng quy đổi IELTS/VSTEP, phụ lục xét tuyển thẳng) có viền bảng, header xám, alternating row colors, blockquote Academic Teal trích dẫn văn bản quy phạm.
     - **Cải tiến chế độ Sửa tay (Human-in-the-loop)**: Bổ sung nút chuyển đổi "Xem trước" (Preview) và "Quay lại sửa" trực tiếp trong textarea, cho phép cán bộ kiểm tra kết quả render Markdown trước khi lưu hoặc nạp vào Vector DB.
  2. **Tách Module Dữ Liệu Theo Chuẩn Clean Code (Rule 8 AGENTS.md)**:
     - Tạo tệp độc lập `frontend/src/services/verification-data.ts` (1,393 dòng, 69KB) chứa toàn bộ dữ liệu bóc tách, bounding boxes và layout regions của 14 trang scan Đề án tuyển sinh 2026, giải phóng dung lượng cho `api-client.ts`.
     - Sửa lỗi PEP 8 E402 trong `backend/app/main.py`.
  3. **Kiểm thử Toàn Diện & Đạt Tiêu Chuẩn Sản Phẩm 100%**:
     - `uv run ruff check .`: All checks passed (0 lỗi).
     - `npm run lint`: Biome check 0 lỗi, 0 cảnh báo.
     - `npm run typecheck`: TypeScript tsc --noEmit 0 lỗi.
     - `npm run build`: Vite build thành công đóng gói production bundle.
     - `npx playwright test tests/e2e/09_knowledge_ingestion_studio.spec.ts --project="Google Chrome"`: 3/3 tests passed (18.6s).

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

**Backend Quality**: 73/73 tests passed | Ruff: 0 errors

---

### ✅ Frontend (8/8 Giai Đoạn — HOÀN THÀNH & ĐỒNG BỘ 100% VỚI QNU-AI-CORE)

| Giai Đoạn | Màn Hình / Module | Trạng Thái |
| :--- | :--- | :---: |
| 1 | Master Layout (Sidebar w-64, Topbar h-14, Academic Teal oklch) | ✅ Done |
| 2 | Assistants Studio (05 Trợ lý, Persona, ModelOps config, Tool Gateway) | ✅ Done |
| 3 | Knowledge Management & Master-Detail Navigation (List + Detail + Ingest + Full Studio) | ✅ Done |
| 4 | Document Verification Studio (Full 14 scan pages, BBoxes, Regions, ReactMarkdown Tables, In-place Edit) | ✅ Done |
| 5 | Omni-Channel Chat Studio (SSE Streaming, Thinking Indicator, CitationSheet) | ✅ Done |
| 6 | ModelOps Dashboard (4 Presets, Secret Key Masking, Circuit Breaker Monitor) | ✅ Done |
| 7 | Tools Gateway (Word NĐ 30 Preview, Excel Bloom Matrix, Template Library) | ✅ Done |
| 8 | Workflow DAG Canvas (@xyflow/react, 6 Custom Node types, Run DAG & Inspector) | ✅ Done |

**Frontend Quality**:
- Biome Linter: 0 errors
- TypeScript: 0 errors
- Vite Build: 100% passed
- Playwright E2E Suites: 9 suites passed (Bao gồm Suite 09 Studio)

---

## 4. Danh Mục Gotchas Kỹ Thuật (Kinh Nghiệm Thực Tế)

1. **Strict Mode trong Playwright**:
   - Khi có text xuất hiện ở cả thanh Breadcrumb/Header và trong thân trang (ví dụ `Trang 1 / 14`), bắt buộc phải dùng `page.getByText('Trang 1 / 14', { exact: true })` hoặc `.first()` để tránh lỗi `strict mode violation`.
2. **Hiển thị Ảnh Scan Tài Liệu Bóc Tách**:
   - Không được dùng text/HTML mock để giả lập trang scan. Bắt buộc phải phục vụ ảnh scan thật từ thư mục tĩnh `frontend/public/ocr-cache/doc_ts_2026/page_N.jpg` với tỉ lệ khung hình chuẩn A4 và zoom container.
3. **Render Bảng Biểu Markdown**:
   - Markdown thô (`whitespace-pre-wrap`) không hiển thị được bảng. Bắt buộc dùng `ReactMarkdown` với plugin `remarkGfm` và custom `components={{ table, thead, th, td, tr }}` có styling viền ô rõ ràng.
4. **PEP 8 E402 trong Backend**:
   - Khi xử lý đoạn mã sửa lỗi Windows IPv6 `no_proxy`, đặt đoạn sanitize sau toàn bộ module imports chuẩn để ruff check 0 lỗi.

---

## 5. Backlog & Kế Hoạch Tiếp Theo

- [x] Đồng bộ ảnh scan thực tế 14 trang từ `qnu-ai-core` vào Studio đối soát.
- [x] Render Markdown bảng biểu và cấu trúc phân cấp chuẩn GitHub Flavored Markdown.
- [x] Thêm chế độ xem trước (Preview) khi hiệu đính văn bản trong chế độ Sửa tay (Human-in-the-loop).
- [ ] Tích hợp API backend thực tế cho endpoint bóc tách đa tầng qua Docling microservice.
- [ ] Mở rộng cơ chế kéo thả trực tiếp khung Bounding Box trên ảnh scan để cập nhật tọa độ ROI cho người dùng cán bộ.
