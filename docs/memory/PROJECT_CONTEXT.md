# PROJECT_CONTEXT.md — Snapshot Ngữ Cảnh Dự Án QNU AI Platform

> **⚠️ QUAN TRỌNG**: AI Agent phải đọc file này NGAY ĐẦU mỗi phiên làm việc và cập nhật lại CUỐI mỗi phiên.
> Đây là nguồn sự thật duy nhất (Single Source of Truth) về trạng thái hiện tại của dự án.

---

## 1. Thông Tin Phiên Gần Nhất

- **Thời gian cập nhật**: 2026-09-17 17:55 (UTC+7)
- **Phiên số**: #56 (tính từ đầu dự án)
- **Agent**: AI Senior Full-Stack Architect & Enterprise AI Systems Specialist
- **Mục tiêu đã hoàn thành**:
  1. **Khắc Phục Bóc Tách Bảng Song Song & Bảo Toàn Danh Sách (List) Độc Lập (phiên #56)**:
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

**Backend Quality**: 125/125 tests passed | Ruff: 0 errors
(OCR: pymupdf + docling 2.128 + easyocr 1.7.2 thật | Layout: SmartLayoutDetector OpenCV morphological line + HSV stamps | Studio: studio-view + page-image + bboxes engine thật | Facts: entity/attribute/value đúng nghĩa | Jobs: ARQ thật + cancel/retry/stats, reindex/test, collection PUT/DELETE | Preview: office→PDF qua Gotenberg | Batch-approve | Lint exit 0 | Counts thật, download, vector cleanup)

---

### ✅ Frontend (ĐỒNG BỘ 100% VỚI QNU-AI-CORE + SCAN STUDIO)

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
- Biome Lint: 0 errors across all 77 files | TypeScript: 0 errors | Vite Build: 100% passed (5.66s)
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
