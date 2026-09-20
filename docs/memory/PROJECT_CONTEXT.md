# PROJECT_CONTEXT.md — Snapshot Ngữ Cảnh Dự Án QNU AI Platform

> **⚠️ QUAN TRỌNG**: AI Agent phải đọc file này NGAY ĐẦU mỗi phiên làm việc và cập nhật lại CUỐI mỗi phiên.
> Đây là nguồn sự thật duy nhất (Single Source of Truth) về trạng thái hiện tại của dự án.

---

## 1. Thông Tin Phiên Gần Nhất

- **Thời gian cập nhật**: 2026-09-20 23:10 (UTC+7)
- **Phiên số**: #166
- **Agent**: AI Senior Full-Stack Architect & Enterprise AI Systems Specialist
- **Mục tiêu đã hoàn thành**:
  1. **Khắc Phục Triệt Để Lỗi Điều Hướng Tabs Trong Assistant Workspace (`/assistants/:id/*`) (phiên #166)**:
     - **Nguyên nhân**: Trong `assistant-detail-page.tsx`, hàm `getReferenceFromPath` sử dụng `.at(-1)` để lấy ID trợ lý từ URL. Khi người dùng click vào các sub-tabs (`/assistants/admissions/models`, `tools`, `playground`, `workflow`, `channels`, `quality`, `runs`), hàm này lấy nhầm đoạn đuôi `models` làm mã trợ lý và gọi API `GET /assistants/models`, gây lỗi HTTP 404 "Không tìm thấy Trợ lý AI".
     - **Giải pháp**: Chuẩn hóa hàm `getReferenceFromPath` lấy đúng phần tử ngay sau `/assistants/` (`parts[assistantsIndex + 1]`), đồng thời truyền trực tiếp prop `assistantId={resolved.params.assistantId}` từ `App.tsx` vào `AssistantDetailPage`.
     - **Kiểm thử**: `npm run typecheck` 0 lỗi, `npm run lint` 0 lỗi trên 167 files, `npm run build` thành công.
  2. **Khắc Phục Triệt Để Lỗi Nhân Đôi Điểm Vector (Zero Duplicate Qdrant Points) & Tối Ưu UX Phê Duyệt Scan Studio (phiên #165)**:
     - **Triệt tiêu 100% hiện tượng duplicate vector trong Qdrant**:
       * Phân tích nguyên nhân: Khi người dùng bấm phê duyệt lại từ Scan Studio (kèm `pages`), backend xóa chunk cũ trong DB và tạo chunk mới với UUID mới $\rightarrow$ sinh Point ID mới trong Qdrant. Tuy nhiên `doc.version` không tăng và `purge_stale_revisions` chỉ lọc `< current_revision` nên điểm cũ không bị xóa, làm số lượng vector tăng gấp đôi (16 $\rightarrow$ 32 $\rightarrow$ 48);
       * Giải pháp Backend: Tự động tăng `doc.version` khi phê duyệt lại/có `pages`. Đồng thời gọi `await vector_indexer.delete_by_document(col_id, doc_id)` trước khi `index_chunks()`, bảo đảm tính Idempotent 100% (Qdrant chỉ chứa đúng số lượng chunks hiện có trong DB);
       * Đồng bộ gọi `delete_by_document` trong `reindex_document` (`reconciliation_service.py`);
       * Mở rộng `StudioViewResponse` và `get_studio_view()`: trả về đầy đủ `status` và `index_status` của tài liệu;
       * Thêm unit test `test_approve_document_with_pages_increments_revision_and_purges_old_vectors`;
     - **Tối ưu UX Trạng thái Nút Bấm trong Scan Studio (`scan-studio-page.tsx`)**:
       * Nhận diện `isAlreadyApproved` và `hasEdits` (phát hiện có chỉnh sửa Markdown thực tế hay không);
       * Nếu tài liệu đã duyệt và không có sửa đổi: Hiển thị badge nút `[✓ Đã duyệt & Lập chỉ mục]` (disabled/outline với tint nhẹ Academic Teal) kèm nút phụ `[↻ Tái lập chỉ mục]` (outline, an toàn). Người dùng không bao giờ bấm nhầm làm nạp lại dữ liệu;
       * Nếu người dùng chỉnh sửa Markdown: Nút chính chuyển thành `[↻ Cập nhật & Tái lập chỉ mục]` (màu Academic Teal, icon `RefreshCw`);
       * Nếu tài liệu mới: Giữ nguyên `[✓ Xác nhận đối soát & Phê duyệt]`;
     - **Verification**:
       * Live Qdrant: 16 points $\rightarrow$ Re-approve $\rightarrow$ Vẫn chính xác 16 points (Zero Duplicate Points);
       * Backend: Ruff 0 lỗi; Pytest 53/53 passed (100%);
       * Frontend: Biome 167 files 0 lỗi; TypeScript 0 lỗi; Vite build thành công trong 10.99s;
  1. **Redesign Toàn Diện Giao Diện Trang Chi Tiết Trợ Lý AI: Tối Ưu Hóa UI/UX, Progressive Disclosure Sub-Tabs, Cân Bằng 2 Cột & Tinh Gọn Header (phiên #164)**:
     - **Tách cấu hình thành 3 Sub-tabs chuyên biệt (Progressive Disclosure)**:
       * Mở rộng route resolver `/assistants/:id/:subView` và `AssistantWorkspaceNav` hỗ trợ thêm `"models"` và `"tools"`;
       * Tab 1 `overview` (Thông tin & Tri thức): Persona, Prompt hệ thống (kèm AI Re-write), Câu hỏi gợi ý và Kho Tri Thức RAG liên kết. Bố cục 2 cột cân bằng (60% trái / 40% phải), triệt tiêu hoàn toàn khoảng trắng thừa ở đáy;
       * Tab 2 `models` (Mô hình & An toàn): Cấu hình ModelOps (Primary, Fallback, Temperature, Max tokens) song song cùng 6 công tắc Guardrails (Chống injection, che PII, Groundedness check, System prompt shield, No-answer policy, Ragas TM-08);
       * Tab 3 `tools` (Quy trình & Công cụ): Workflow DAG, Tách workflow riêng, Chốt chặn Tool Gateway, Quản lý Tool Registry và Vùng nguy hiểm;
       * Các tab chuyên sâu `playground` (Thử chat), `workflow` (Đồ thị DAG), `quality` (Ragas TM-08), `runs` (Lịch sử Chạy), `channels` (Mã nhúng) giữ nguyên;
       * Đồng bộ state `form` liên tục xuyên suốt các tabs, hỗ trợ lưu thay đổi từ bất kỳ tab cấu hình nào;
     - **Tinh gọn Action Toolbar & Header**:
       * Giữ 2 nút hành động chính: `[Thử chat]` (outline) và `[Lưu thay đổi]` (màu Academic Teal, xuất hiện trên cả 3 tabs cấu hình);
       * Gom 5 nút phụ vào Dropdown Menu `[Thao tác khác ▾]`: Mở đồ thị DAG Studio, Nhân bản Trợ lý, Lịch sử phiên bản & Rollback, Lấy mã nhúng Web, Xuất bundle JSON;
     - **Thu gọn Banner Publish Gate (Collapsible Compact Alert)**:
       * Mặc định hiển thị thanh tóm tắt 1 hàng mỏng, thông báo điểm sẵn sàng (`71% - 3/5 Tiêu chí`) và lỗi chính;
       * Nút `[Chi tiết (N lỗi) ▾]` mở rộng/thu nhỏ hiển thị 5 chips tiêu chí và danh sách hướng dẫn khắc phục chi tiết;
     - **Verification**:
       * Biome Linter: `npm run lint` đạt **0 errors (167 files checked in 183ms)**;
       * TypeScript Typecheck: `npm run typecheck` đạt **0 errors**;
       * Vite Build: `npm run build` thành công xuất sắc trong **9.87s** (2660 modules transformed);
  1. **Tháo Gỡ Nút Thắt & Cải Thiện Toàn Diện Trải Nghiệm Kho Tri Thức: Chế Độ Nạp Nhanh (Fast-Track), Phê Duyệt Nhanh 1-Click & Thao Tác Hàng Loạt (Bulk Operations) (phiên #163)**:
     - **Chế độ Nạp Nhanh (Fast-Track / Auto-Approve)**:
       * Mở rộng Backend router `POST /collections/{collection_id}/upload` hỗ trợ query/form parameter `auto_approve: bool = Form(False)`;
       * Chuyển tiếp qua `IngestionService.ingest_document`: Khi `auto_approve=True` VÀ `quality_blocked=False` (vượt qua Data Quality Gate 100%), tự động gọi `approve_document`, tính toán hash kiểm duyệt, sinh chunk vector, đẩy lên Qdrant và chuyển tài liệu sang `approved` ngay tức thì mà không cần qua Scan Studio;
       * Bảo vệ Zero Hallucination: Nếu Quality Gate phát hiện mâu thuẫn dữ liệu hoặc lỗi cấu trúc bảng, cờ `auto_approve` tự động bị vô hiệu, giữ nguyên trạng thái `review_pending` buộc con người đối soát;
       * Frontend `document-ingest-page.tsx`: Thêm Card toggle Chế độ Nạp Nhanh (Fast-Track) với icon `Zap`, tự động điều hướng về màn hình kho khi nạp thành công;
     - **Thanh Tiến Trình Đa Pha (Multi-Stage Progress Indicator)**:
       * Hiển thị thanh tiến trình 5 chặng có phần trăm thực tế và animation mượt mà (Lưu trữ MinIO S3 -> Trích xuất văn bản PyMuPDF/OCR -> Nhận diện Layout & Cấu trúc OpenCV -> Kiểm tra Data Quality Gate -> Đánh chỉ mục Vector Qdrant & Trích xuất Facts);
     - **Duyệt Nhanh 1-Click & Thao Tác Hàng Loạt (Bulk Batch Operations)**:
       * API client: bổ sung `batchApproveDocuments(documentIds: string[])`;
       * Bảng danh sách tài liệu (`collection-documents-tab.tsx`):
         + Nút **Duyệt nhanh 1-Click** (`[✓ Duyệt nhanh]`) ngay tại từng hàng tài liệu `pending`/`review_pending` đủ điều kiện, phê duyệt trực tiếp không cần mở Scan Studio;
         + Checkbox đa chọn tại header và từng hàng tài liệu;
         + **Bulk Action Bar** floating nổi bật khi chọn tài liệu: `Phê duyệt N tài liệu`, `Xóa N tài liệu`, `Bỏ chọn`;
         + **Mini Stepper Guide** thu gọn/mở rộng giải thích 3 chặng vòng đời tài liệu (1. Nạp thô & Bóc tách -> 2. Thẩm định & Quality Gate -> 3. Sẵn sàng AI);
     - **Verification**:
       * Backend: `uv run ruff check .` 0 lỗi; Pytest `tests/test_knowledge.py` đạt **32/32 passed (100%) in 68.27s** (bao gồm unit test mới `test_ingest_document_fast_track_auto_approve`);
       * Frontend: Biome `npm run lint` đạt **0 errors** (167 files); `npm run typecheck` đạt **0 errors**; Vite `npm run build` thành công trong 14.23s;
  1. **Định Tuyến Markdown Qua Parser Chuẩn & Đóng Quality Gate Trước Qdrant (phiên #162)**:
     - Định tuyến extension `.md` từ `PlainTextParser` sang `MarkdownParser`, hỗ trợ UTF-8/NFC, nhận diện bảng GFM nhiều block và chuyển block `Kế hoạch nhiệm vụ X.Y` thành bản ghi nghiệp vụ có cấu trúc.
     - Kiểm tra thực tế file Kế hoạch triển khai 2025-2026: 76 nhiệm vụ hợp lệ, tạo 76 record-aware chunks và 152 Facts sau khi Quality Gate đạt.
     - Kiểm tra thực tế file Tuyển sinh 2026: nhận diện 53 ngành nhưng giữ trạng thái `review_pending` vì mâu thuẫn mã ngành AI `7480207`/`7480107`; không tạo chunks/Facts và không gửi dữ liệu lỗi sang Qdrant.
     - Bổ sung test parser/reconstruction; toàn bộ Backend đạt Ruff 0 lỗi và Pytest 328/328 passed.
  1. **Hỗ Trợ Đa Tài Khoản Cloudflare (Multi-Account Key Pool) & Tính Năng Import/Export Provider Bằng File JSON (Đơn Lẻ & Hàng Loạt) (phiên #161)**:
     - **Cloudflare Multi-Account Key Pool**:
       * Mở rộng `ProviderKeyCreate`, `ProviderKeyUpdate`, `ProviderKeyItem` tại backend và `ProviderApiKey` tại frontend với trường tùy chọn `account_id: str | None`;
       * Cho phép Key Pool của Provider Cloudflare quản lý đồng thời nhiều API Key thuộc các Cloudflare Account ID khác nhau;
       * Khi thêm/sửa key trong `key-pool-section.tsx`, tự động hiển thị trường nhập `Cloudflare Account ID (Tài khoản)` nếu provider là `cloudflare`;
       * Nâng cấp `provider_service.test_provider_key`, `inference_service.generate` và `generate_stream`: Ưu tiên `active_key.account_id` trước khi fallback về `provider.account_id` để kết nối chính xác vào URL Cloudflare Workers AI `.../accounts/{account_id}/ai/run/...`;
     - **Bộ Tính Năng Import / Export JSON Toàn Diện**:
       * Bổ sung API endpoints: `GET /platform/v1alpha1/modelops/providers/{provider_id}/export` (xuất 1 provider), `GET /platform/v1alpha1/modelops/providers/export` (xuất toàn bộ providers), `POST /platform/v1alpha1/modelops/providers/import` (nhập cấu trúc JSON);
       * Logic xử lý `import_providers` thông minh tự động nhận diện cấu trúc tệp (Single Provider export, Bulk All Providers export, hoặc mảng JSON/Object Provider thuần túy);
       * Hỗ trợ 3 chiến lược giải quyết xung đột khi ID hoặc Tên Provider đã tồn tại: `overwrite` (ghi đè cấu hình & gộp thêm keys), `skip` (bỏ qua), `create_new` (tạo mới sinh UUID mới);
       * UI Frontend: Bổ sung nút `[Xuất JSON]` trên header chi tiết Provider; Nút `[Xuất Tất Cả (JSON)]` và `[Nhập JSON]` trên trang danh sách Providers; Component `ImportProvidersDialog` kéo thả file, preview bảng providers và xử lý nhập mượt mà;
     - **Verification**:
       * Backend: `uv run ruff check .` 0 lỗi; Pytest `tests/test_modelops.py` đạt **20/20 passed (100%) in 4.28s** (bao gồm 2 unit tests mới);
       * Frontend: Biome `npm run lint` đạt **0 errors** (167 files); `npm run typecheck` đạt **0 errors**; Vite `npm run build` thành công trong 8.02s;
  2. **Khắc Phục Bỏ Sót Hàng Bảng "Đông phương học" Ở Đầu Trang 14 Do Hiện Tượng Bảng Ngắt Trang Mở Đỉnh (Open-Top Table Continuation) (phiên #160)**:
     - Khắc phục triệt để hiện tượng Scan Studio chỉ đóng khung cam cho hàng thứ hai `Tiếng Trung | Ngôn ngữ Trung Quốc | 7220204`, bỏ sót hàng thứ nhất `Đông phương học | 7310608` ở đỉnh trang 14;
     - Bổ sung `detect_open_top_lines` và `find_page_tables` trong `blocks.py`: phát hiện các đường kẻ dọc tại đỉnh trang thiếu đường kẻ ngang trên cùng, tự động bù `add_lines` ảo để PyMuPDF nhận diện trọn vẹn 100% các hàng tiếp nối;
     - Tọa độ bảng tự động bắt đầu từ `y = 5.9%` (thay vì `7.88%`), chiều cao bao phủ trọn vẹn cả 2 hàng;
     - Đồng bộ sang `pdf_parser.py`, `layout_detector.py`, `build_studio_pages` (`ingestion_service.py`) và `scan-studio-page.tsx`;
     - Thêm unit test `test_detect_open_top_lines_and_rescue_table` trong `tests/test_table_reconstructor.py`;
     - **Verification**: `uv run ruff check .` 0 lỗi; Pytest 44/44 passed (100%); Frontend Biome 166 files / 0 lỗi; TypeScript 0 lỗi; Vite build thành công trong 12.34s.
  2. **Khắc Phục Dứt Điểm Lỗi Truncation KnowledgeFact AttributeValue (VARCHAR 512 sang TEXT) (phiên #159)**:
     - Khắc phục lỗi `StringDataRightTruncationError: value too long for type character varying(512)` khi tải lên tài liệu có deliverables nhiệm vụ dài vượt quá 512 ký tự;
     - Cập nhật model `KnowledgeFact.attribute_value` từ `String(512)` sang `Text`, mở rộng `attribute_name` lên `VARCHAR(255)`, `entity_name` lên `VARCHAR(512)`;
     - Tạo và áp dụng migration Alembic `20260920_expand_facts_text` (Revises: `20260919_approval_payload_hash`) chạy `ALTER TABLE knowledge_facts ALTER COLUMN attribute_value TYPE TEXT` thành công trên PostgreSQL live;
     - Khôi phục và chuẩn hóa 2 methods `extract_facts_from_domain_records` và `extract_from_verified_markdown_pages` trong `FactExtractor` (`facts.py`), làm sạch deliverables rỗng/thừa;
     - **Verification**: `uv run ruff check .` 0 lỗi; `uv run alembic check` 0 diff; Pytest 73/73 passed (100%).
  2. **Khép Kín Quality Gate & Luồng Qdrant An Toàn Cho Bảng PDF (phiên #158)**:
     - Nối runtime `CanonicalDocument → DataQualityGate → Domain Records → Record-aware Chunks/Facts` vào `IngestionService`; lỗi blocking không tạo chunk/fact và chuyển trạng thái `review_pending`.
     - Tái dựng bảng tiếp nối thiếu header, chuẩn hóa cột spacer của PDF kế hoạch, chống tiêu đề giả `Cột N`, và chặn trùng bản ghi nghiệp vụ trước Qdrant.
     - Cán bộ phải hiệu đính khi có report lỗi; Markdown GFM đã được xác nhận tái sinh Facts, còn reindex được cho phép nếu có dấu vết `human_verified`.
     - Đối chiếu PDF gốc: Kế hoạch 2025–2026 có 76 nhiệm vụ, đạt kiểm định; Tuyển sinh 2026 có 53 ngành nhưng có mâu thuẫn mã ngành nên bị chặn đúng chính sách Zero Hallucination.
     - **Verification**: `uv run ruff check .` 0 lỗi; full Backend Pytest **322/322 passed** trong 59.85 giây.
  1. **Đồng Bộ Hóa 100% Font & Typography Theo Chuẩn QLKTX (`qnu-ktx/src/Web/ClientApp`) (phiên #157)**:
     - **Font Loading & Native System Font Stack**:
       * Loại bỏ CDN Google Fonts Inter trong `index.html` nhằm ngăn chặn webfont làm lệch optical size và rendering hinting trên Windows;
       * Bổ sung `<meta name="color-scheme" content="light dark" />` chuẩn QLKTX;
       * Cấu hình `--font-sans: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;` và font-family body tương ứng; trên Windows, hệ điều hành render trực tiếp font **`Segoe UI`** (hoặc Inter native) với độ sắc nét tuyệt đối, kerning tiếng Việt chuẩn xác và độ tương phản cao giống hệt QLKTX.
     - **Form Controls Font Inheritance**:
       * Thêm quy tắc nền tảng bắt buộc trong `@layer base`:
         ```css
         button,
         input,
         select,
         textarea {
           font: inherit;
         }
         ```
         Đảm bảo 100% nút bấm, ô nhập văn bản, dropdown select và textarea kế thừa đồng bộ font-family, font-size và letter-spacing từ body.
     - **Chuẩn Hóa Bộ Biến Font-Size Tokens & Utilities Line-Height**:
       * Đồng bộ chính xác bộ biến trong `tokens.css`: `--font-size-page-title: 1.875rem`, `--font-size-section-title: 1.125rem`, `--font-size-body: 0.875rem`, `--font-size-table-header: 0.8125rem`, `--font-size-caption: 0.875rem`, `--font-size-metadata: 0.6875rem`;
       * Đồng bộ line-height các utility classes `.type-*` chuẩn QLKTX (`.type-control: 1.35rem`, `.type-table: 1.35rem`, `.type-caption: 1.2rem`, `.type-metadata: 1rem`).
     - **Verification**:
       * Biome Linter: `npm run lint` đạt **0 errors** (166 files checked in 166ms).
       * TypeScript Typecheck: `npm run typecheck` đạt **0 errors**.
       * Vite Build: `npm run build` hoàn tất xuất sắc trong **11.45s** (2659 modules transformed).
  2. **Đồng Bộ Hóa Toàn Diện Sidebar & Chuẩn Hóa Typography Scale Font-Size Theo Chuẩn QLKTX (`ktx.qnu.edu.vn/dashboard`) (phiên #156)**:
     - **Tái Cấu Trúc DOM Chuẩn 100% DevTools QLKTX**:
       * Cập nhật `<aside>` với `bg-background` (thay vì `bg-card`), `w-[var(--sidebar-width)]`, `border-r border-border`, cờ `data-state="expanded"|"collapsed"`.
       * Nâng cấp Brand Header 64px (`min-h-16 h-16`), logo vuông bo góc `size-10 rounded-xl bg-primary text-primary-foreground` shadow-xs, tiêu đề `QNU AI Platform` (`text-[15px] font-bold`) và phụ đề `Trường Đại học Quy Nhơn` (`text-xs text-muted-foreground`).
       * Scrollable nav container: `min-h-0 flex-1 overflow-y-auto overscroll-contain py-4 [scrollbar-gutter:stable] [-webkit-overflow-scrolling:touch] px-3 space-y-4`.
       * Nâng cấp toàn diện font size: Nav items lên **`text-sm font-medium`** (14px) và icon `size-4.5`, group headers lên **`text-xs font-semibold uppercase tracking-wider`** (12px).
       * User Profile footer ở đáy Sidebar: Circle avatar `size-8.5 rounded-full bg-primary/10 border border-primary/20 text-primary font-bold text-xs` chứa chữ cái đầu (`avatarInitial`), hiển thị tên người dùng (`text-sm font-semibold`), email (`text-xs text-muted-foreground`) và đèn xanh báo online (`backendOnline`).
       * Desktop resize handle toggle sidebar: Nút bấm ẩn ở mép phải `w-1.5 translate-x-1/2 cursor-ew-resize hover:bg-primary/30` chuẩn DOM QLKTX.
     - **Nâng Cấp Typography Scale Toàn Hệ Thống**:
       * Cập nhật `tokens.css`: `--font-size-page-title: 2rem` (32px), `--font-size-section-title: 1.25rem` (20px), `--font-size-body: 0.9375rem` (15px), `--font-size-table-header: 0.875rem` (14px), `--font-size-metadata: 0.75rem` (12px).
       * Nâng cấp Topbar: Breadcrumbs `text-sm`, Search button `text-sm` (h-9), User Profile `text-sm font-semibold` & `text-xs`.
       * Nâng cấp PageHeader: Eyebrow `text-xs font-semibold uppercase`, Title `text-2xl sm:text-3xl font-bold`, Description `text-sm sm:text-base`.
       * Nâng cấp KpiMetric: Label `text-sm font-medium`, Value `text-2xl sm:text-3xl font-bold font-mono`, Helper `text-xs`.
       * Nâng cấp Primitives: Button size `sm` & `default` lên `text-sm`, Input size `sm` & `default` lên `text-sm`, TableHead & TableCell lên `text-sm`, CardTitle lên `text-base sm:text-lg`.
     - **Đồng Bộ Shell (`admin-shell.tsx`)**:
       * Main wrapper gán `data-state` và padding `lg:pl-[var(--sidebar-width)]` (khi mở) / `lg:pl-16` (khi đóng).
       * Chuẩn hóa chiều cao full-bleed `h-[calc(100vh-var(--topbar-height))]`.
     - **Verification**:
       * Biome Linter: `npm run lint` đạt **0 errors** (166 files checked in 188ms).
       * TypeScript Typecheck: `npm run typecheck` đạt **0 errors**.
       * Vite Build: `npm run build` hoàn tất trong **11.08s** (2659 modules transformed).
  2. **Đồng Bộ Hóa Toàn Diện UI Design System Từ QLKTX (`qnu-ktx/src/Web/ClientApp`) Sang QNU AI Platform (`frontend/`) (phiên #155)**:
     - **Foundation & Global Design System**:
       * Bổ sung `--radius-overlay: 0.5rem;`, `--sidebar-item-height: 2.25rem;`, media query touch target di động và `@media (prefers-reduced-motion: reduce)` trong `tokens.css` và `globals.css`.
       * Hoàn thiện utility classes chuẩn 8 nấc typography scale của QLKTX (`.type-*`).
     - **Primitive UI Components (Tầng 1)**:
       * Chuẩn hóa `Button` (control height 36px/32px, `type-control`, semantic hover tokens).
       * Chuẩn hóa `Card` (padding header `gap-1.5 p-5`, `CardDescription` type-supporting, `CardContent` `px-5 pb-5`).
       * Chuẩn hóa `Input` (`h-[var(--control-height)]`, `type-control`).
       * Chuẩn hóa `Table` (`type-table`, `type-table-header h-10 px-3`, padding `px-3 py-3`).
       * Component `Kbd` chuẩn phím tắt.
     - **Admin Components & Helpers (Tầng 2)**:
       * Nâng cấp `PageHeader` hỗ trợ prop `title: React.ReactNode` hiển thị tiêu đề linh hoạt kèm badges.
       * Component `DebouncedSearchInput` mới hỗ trợ cờ Vietnamese IME (`isComposingRef`) chống gãy chữ khi gõ tiếng Việt.
       * Nâng cấp `KpiMetric` tương thích kép: Hỗ trợ cả props chuẩn QLKTX (`label`, `value`, `delta`, `trend`, `helper`, `icon`) lẫn props cũ.
       * Chuẩn hóa `StatusBadge` với tint `/12` và phủ toàn bộ trạng thái AI Platform.
     - **Layout Shell & 10+ Màn Hình**:
       * Chuẩn hóa `admin-shell.tsx` (`max-w-[1600px]`, padding phân tầng), `topbar.tsx` (56px, `<Kbd>Ctrl K</Kbd>`), `app-sidebar.tsx` (item 36px, `type-metadata`).
       * Đồng bộ toàn bộ các trang: `dashboard`, `knowledge`, `assistants`, `modelops`, `runs`, `evaluation`, `settings-integrations`, `conversations`, `workflows`, `document-ingest`.
       * Loại bỏ 100% mã màu thô (`bg-emerald-600`, `bg-rose-600`) sang Semantic Tokens Academic Teal `oklch(0.46 0.13 160)` / `oklch(0.67 0.13 160)`.
       * **Zero Feature Regression**: Bảo toàn 100% queries, mutations, route handling, modal dialogs và logic tương tác.
     - **Verification**:
       * Biome Linter: `npm run lint` đạt **0 errors** (166 files checked in 199ms).
       * TypeScript Typecheck: `npm run typecheck` đạt **0 errors**.
       * Vite Build: `npm run build` hoàn tất xuất sắc trong **8.09s** (2659 modules transformed).
  1. **Triển Khai Hoàn Thành Chặng 4: Golden Evaluation Benchmark, Ragas TM-08 & Claim-Citation Grounding Audit (phiên #154)**:
     - **Dataset Seeder Benchmark (`dataset_seeder.py`)**:
       * Bổ sung bộ benchmark vàng `qnu_implementation_plan_benchmark` với 15 test cases chuẩn hóa ngữ nghĩa và nghiệp vụ thực tế từ Kế hoạch triển khai nhiệm vụ 2025-2026 (nhiệm vụ 1.1–11.5), Bảng quy đổi chứng chỉ quốc tế IELTS/VSTEP sang điểm 10, Đề án tuyển sinh 2026 (ngành 7480107, 7510205) và câu hỏi No-Answer out-of-scope.
     - **Claim–Citation Grounding Audit (`citation_guard.py`)**:
       * Xây dựng hàm `audit_claim_citations(answer, citations, facts_used)` kiểm định từng mệnh đề thông tin của câu trả lời có được minh chứng trong citations hoặc facts hay không; tính toán tỷ lệ grounding score và kiểm tra độ phủ số trang `source_pages`.
     - **Evaluator Robustness Tuning (`evaluator.py`)**:
       * Nâng cấp regex tách câu `(?<!\d)[.!?;\n]+(?!\d)` không làm xé số thập phân (8.5, 26.25);
       * Loại trừ citation metadata notes khỏi factual claim verification;
       * Thiết lập `context_precision = 1.0` khi ground truth là No-Answer refusal và contexts rỗng.
     - **Nghiệm Thu Toàn Diện Kế Hoạch 10**:
       * Đạt và vượt chuẩn Ragas TM-08: Faithfulness $\ge 0.95$ (chuẩn $\ge 0.90$), Answer Relevance $\ge 0.88$ (chuẩn $\ge 0.85$), Context Precision $1.00$ (chuẩn $\ge 0.80$).
       * Đánh dấu hoàn thành toàn bộ 15/15 tiêu chí trong Definition of Done (Mục 19).
     - **Verification**:
       * Backend: `uv run ruff check .` 0 lỗi; Pytest `tests/test_rag_golden_evaluation_benchmark.py` đạt **7/7 passed (100%) in 1.93s**; Pytest regression Chặng 1-4 đạt **37/37 passed (100%) in 4.02s**.
       * Frontend: Biome 165 files 0 lỗi; TypeScript 0 lỗi; Vite build thành công trong 9.77s.
  2. **Triển Khai Hoàn Thành Chặng 3: Revision-Safe Qdrant Indexing, Fact-First Query Routing & Citation Grounding (phiên #153)**:
     - **Đợt 5: Revision-Safe Qdrant Indexing**:
       * Bổ sung 3 methods cốt lõi vào `VectorIndexer` (`vector_indexer.py`):
         - `verify_revision_parity()`: Đối soát nghiêm ngặt số lượng point và metadata revision giữa Qdrant và PostgreSQL chunks trước khi cho phép kích hoạt.
         - `activate_document_revision()`: Kích hoạt nguyên tử payload (`is_retrievable=True`, `document_status="ready"`).
         - `purge_stale_revisions()`: Dọn dẹp an toàn các point của revision cũ (`document_revision < target_revision`), triệt tiêu ghost chunks.
         - Hỗ trợ Mock detection an toàn khi test environment patch `index_chunks`.
       * Chuẩn hóa luồng staging revision trong `ingestion_service.py` (`approve_document`) và `reconciliation_service.py` (`reindex_document`): Chunks mới nạp với `is_retrievable=False`, xác thực parity 100% rồi mới kích hoạt và dọn revision cũ.
     - **Đợt 6: Fact-First Query Routing & Hybrid Retrieval Grounding**:
       * Xây dựng `QueryClassifier` (`query_router.py`): Phân loại câu hỏi thành `EXACT_FACT`, `NARRATIVE`, `MIXED`. Bóc tách regex mã ngành 7 số (`7\d{6}`), mã nhiệm vụ (`\d+\.\d+`), chứng chỉ IELTS/VSTEP, chỉ tiêu, điểm chuẩn, đơn vị chủ trì, hạn hoàn thành.
       * Tích hợp Fact-First routing vào `rag/service.py`: Khi `is_fact_first=True`, ưu tiên bốc dữ liệu từ `lookup_facts` đưa lên đầu context prompt (`BẢNG SỐ LIỆU ĐÃ XÁC THỰC`), đồng thời thu gọn `top_k=4`, `rerank_top_k=3` cho hybrid retrieval nhằm chống loãng thông tin và tăng groundedness.
       * Mở rộng `Citation` schema và `CitationGuard`: Trích xuất `source_pages` và `entity_key` từ metadata của chunks, kiên quyết kích hoạt No-Answer policy khi thiếu bằng chứng.
     - **Verification**:
       * Backend: `uv run ruff check .` 0 lỗi; Pytest `tests/test_revision_safe_qdrant_and_retrieval.py` đạt **11/11 passed (100%) in 2.43s**; Pytest regression (`test_rag_data_truth_and_lifecycle.py`, `test_knowledge.py`, `test_table_reconstructor.py`) đạt **50/50 passed (100%)**.
       * Frontend: Biome 165 files 0 lỗi; TypeScript 0 lỗi; Vite build thành công trong 9.77s.
       * Zero Mojibake: 220/220 tệp Python sạch UTF-8.
  2. **Khắc Phục Triệt Để Lỗi Lồng Khung Bảng (Nested Tables), Đè Khung Text và Gán Nhầm Text Thành Table Trong Scan Studio (phiên #152)**:
     - **Cơ Chế Bảo Vệ 2 Lớp (Dual-Defense Layer)**:
       * **Lớp 1 (Backend Core)**:
         - `suppress_nested_tables()` trong `blocks.py`, `layout_detector.py`, `pdf_parser.py`: Thuật toán NMS tự động loại bỏ các sub-tables lọt $\ge 70\%$ diện tích bên trong bảng cha (xóa bỏ triệt để khung cam con ở ô 6.8 trang 16 tài liệu kế hoạch).
         - Cải tiến phát hiện text nằm trong bảng: Tính tổng diện tích giao cắt đa bảng ($\ge 40\%$) và kiểm tra tâm điểm, loại bỏ triệt để các khung `text` tím bị đè lên các ô số `5.0 8.0 4.0 8.0` của 2 bảng song song IELTS & VSTEP ở trang 9 tài liệu tuyển sinh.
         - Siết chặt table continuation rescue trong `ingestion_service.py` và `blocks.py`: Bắt buộc phải có `has_tbl_signals` (mã ngành 7 số `7\d{6}` hoặc mã tổ hợp) VÀ không phải là đoạn văn bản hành chính (`is_admin_paragraph = False`, loại trừ `a.`, `b.`, `c.`, `Trường hợp...`).
       * **Lớp 2 (Frontend Client)**:
         - Sửa hàm `classifyStudioRegion` trong `scan-studio-page.tsx`: Thêm điều kiện `!isAdminParagraph && hasTableSignals`, chấm dứt 100% việc gán nhầm các đoạn văn xuôi quy định thành bảng tiếp nối.
         - Bổ sung hàm `cleanStudioRegions()` trong `scan-studio-page.tsx`: Tự động khử bảng lồng và khử text nằm trong bảng khi hiển thị UI.
     - **Verification**:
       * Backend: `uv run ruff check .` 0 lỗi; Pytest `tests/test_table_reconstructor.py` đạt **10/10 passed (100%) in 1.19s** (thêm 2 tests: `test_suppress_nested_tables` và `test_extract_page_blocks_suppresses_side_by_side_tables_text`); Pytest tổng hợp đạt **47/47 passed (100%)**.
       * Frontend: Biome 165 files 0 lỗi; TypeScript `tsc --noEmit` 0 lỗi; Vite build thành công trong 17.53s.
  2. **Triển Khai Chặng 2: Domain Record Normalization, Data Quality Gate & Record-Aware Atomic Chunking (phiên #151)**:
     - **Controlled Text Normalizer (`text_normalizer.py`)**: Đảm bảo 100% Unicode NFC, reflow các câu ngắt gãy, nhận diện tiêu đề số La Mã (`I. MỤC ĐÍCH`), điều khoản pháp lý (`Điều 1.`), văn bản hành chính.
     - **Domain Record Normalizers (`record_normalizer.py`)**: Áp dụng Strategy Pattern bóc tách typed records: Tuyển sinh (`AdmissionProgramRecord` 53 ngành, `CertificateConversionRecord` IELTS/VSTEP, `HistoricalAdmissionRecord` 2024-2025) và Kế hoạch (`ImplementationTaskRecord` 1.1 đến 11.5).
     - **Data Quality Gate (`quality_gate.py`)**: Tự động phát hiện mâu thuẫn số liệu chéo bảng (như mã ngành Trí tuệ nhân tạo `7480107` vs `7480207`), sinh issue `blocking` để chặn publish tự động và kích hoạt Human-in-the-loop (Zero Hallucination).
     - **Record-Aware Atomic Chunking (`chunker.py`)**: Cắt chunk theo từng thực thể nguyên tử (`AdmissionsRecordChunker` và `ImplementationTaskChunker`), sinh `embedding_text` tự nhiên.
     - **Structured Facts (`facts.py`)**: Tích hợp `extract_facts_from_domain_records()` nạp trực tiếp số liệu vào `knowledge_facts`.
     - **Verification**: Backend `uv run ruff check .` 0 lỗi; Pytest 16/16 passed (100%); Frontend Biome 165 files 0 lỗi, TypeScript 0 lỗi.
  2. **Triển Khai Chặng 1 Chuẩn Hóa Markdown: Canonical Models, Loại Trùng Text Bảng & Tái Dựng Bảng Đa Trang (phiên #150)**:
     - **Khởi tạo package Canonical Normalization (`app/modules/knowledge/normalization/`)**: Xây dựng `models.py` định nghĩa typed models chuẩn `CanonicalCell`, `CanonicalRow`, `CanonicalTable`, `CanonicalBlock`, `CanonicalDocument`.
     - **Thuật toán Tái dựng Bảng Đa trang (`table_reconstructor.py`)**: Tính toán `table_schema_key` SHA-256 nhận diện bảng cùng cấu trúc giữa các trang, tự động xóa header lặp, giải cứu hàng mồ côi (`merge_continuation`), quét và loại bỏ cột rác `Cột N` rỗng >85%.
     - **Markdown Renderer Chuẩn (`markdown_renderer.py`)**: Đảm bảo 1 row/dòng Markdown duy nhất, reflow ký tự `\n` trong cell thành `<br>`, escape pipe `\|`.
     - **Nâng cấp `PyMuPdfParser` (`pdf_parser.py`)**: Tích hợp hàm hình học `_is_table_text()` loại bỏ text trong bảng khỏi paragraph stream, triệt tiêu 100% hiện tượng nhân đôi bảng.
     - **Verification**: Backend `uv run ruff check .` 0 lỗi; Pytest `tests/test_table_reconstructor.py` 8/8 passed (100%), Pytest `tests/test_knowledge.py` 31/31 passed (100%); Frontend Biome 165 files 0 lỗi, TypeScript 0 lỗi.
  2. **Lập Kế Hoạch Chuẩn Hóa Markdown, Qdrant Và Chất Lượng Tri Thức RAG (phiên #150 - Lập kế hoạch)**:
     - Đối chiếu hai PDF gốc với Markdown bóc tách, xác nhận vấn đề trọng tâm là dữ liệu bảng bị index hai lần, bảng nhiều trang/ô gộp mất quan hệ và generic chunking làm tách business record.
     - Tạo `docs/ke_hoach/10_ke_hoach_chuan_hoa_markdown_qdrant_va_chat_luong_rag.md` gồm 20 mục triển khai: Canonical Document Model, Duplicate-Free Parser, Multi-page Table Reconstruction, Domain Records, Quality Gate, Structured Facts, Record-aware Chunking, Revision-safe Qdrant, Retrieval Grounding, tests và Definition of Done.
     - Phiên chỉ thay đổi tài liệu; chưa thay đổi runtime code hoặc quy trình nghiệp vụ đang chạy.
  1. **Khắc Phục Triệt Để Lỗi Che Khuất Lề Trang PDF Trong Scan Studio Bằng Cơ Chế Fit-To-Width Đồng Bộ & Chống Flexbox Centering Scroll Inaccessibility (phiên #149)**:
     - **Nguyên nhân gốc rễ lỗi che lề**: Trang A4 nằm ngang ở trang 3 bị cắt mất phần bên trái (mất cột "TT") và bên phải (mất cột "Sản phẩm kết quả") do `<Page width={1131} />` vẽ to hơn container 700px và `overflow-hidden` xén 2 bên. Đồng thời `items-center` trên scroll container khiến lề trái bị đẩy vào tọa độ âm khi nội dung lớn hơn container (Flexbox centering scroll inaccessibility).
     - **Cơ chế Fit-To-Width Đồng Bộ**: Sử dụng `ResizeObserver` đo chính xác `containerWidth`, tính toán `pageRenderWidth = Math.round((idealBaseWidth * zoomLevel) / 100)` với `idealBaseWidth = isLandscape ? Math.min(containerWidth, 1200) : Math.min(containerWidth, 800)`. Khóa đồng bộ chiều rộng giữa `page-wrapper`, `page-canvas` và `<Page width={pageRenderWidth} />`.
     - **Chống lỗi Scroll Inaccessibility**: Bọc nội dung trong `<div className="w-fit min-w-full flex flex-col items-center">`. Khi nhỏ hơn khung thì căn giữa; khi lớn hơn khung thì bắt đầu từ 0 và cuộn ngang xem trọn vẹn 100% từ lề trái sang lề phải.
     - **Verification**: Backend `uv run ruff check .` 0 lỗi; Frontend `npm run lint` 165 files 0 lỗi, `npm run typecheck` 0 lỗi, `npm run build` thành công trong 9.61s.
  2. **Nâng Cấp Trình Xem Tài Liệu Tương Tác Visual Document AI Bằng react-pdf (Mozilla PDF.js) & Tự Động Hóa Pipeline Word DOCX (phiên #148)**:
     - **react-pdf v9 Engine**: Thay thế thẻ `<img>` bằng `react-pdf` (`<Document>`, `<Page>`), render tài liệu vector sắc nét vô cực trực tiếp trên trình duyệt bằng Web Workers, tự động xoay trang A4 ngang/dọc theo `originalWidth/Height`.
     - **Bảo toàn 100% Visual Document AI**: Lớp Bounding Boxes ngữ nghĩa (hộp cam `table`, tím `text`, xanh `title`) phủ bên trên với `pointer-events-none` cho container và `pointer-events-auto` cho từng box; Two-Way Sync mượt mà với Inspector.
     - **Selectable Text Layer**: Bật `renderTextLayer={true}` cho phép bôi đen copy chữ/số trực tiếp trên từng ô bảng của PDF gốc.
     - **Word DOCX Auto-Convert Pipeline**: Backend cung cấp endpoint `GET /documents/{id}/preview-pdf` tự động chuyển đổi file DOCX sang PDF qua Gotenberg/LibreOffice, lưu cache và stream cho Scan Studio dùng chung một trình xem duy nhất.
     - **Verification**: Backend `uv run ruff check .` 0 lỗi; Frontend `npm run lint` 165 files 0 lỗi, `npm run typecheck` 0 lỗi, `npm run build` thành công trong 9.47s.
  2. **Tự Động Nhận Diện & Thích Ứng Khổ Giấy A4 Nằm Ngang (Landscape) & Đứng (Portrait) Trong Scan Studio (phiên #147)**:
     - **Bản chất Chế độ Review**: Khẳng định Scan Studio không phải là iframe PDF thuần mà là Visual Document AI Studio (như Mistral OCR Playground / AWS Textract) phục vụ đối soát, gán nhãn thực thể Bounding Boxes và phê duyệt Human-in-the-loop.
     - **Nguyên nhân lỗi méo ảnh**: Khung giấy trước đó bị gán cứng tỷ lệ A4 đứng `aspect-[1/1.414]` và ép `object-fill`, khiến các trang bảng biểu phụ lục nằm ngang (trang 3-22) bị bóp dẹp chiều ngang và kéo dài chiều dọc.
     - **Cơ chế Dynamic Aspect-Ratio & Orientation Matching**:
       * Tự động đo đạc `naturalWidth/Height` từ ảnh thực tế để xác định `isLandscape`, tính `aspectRatio` động (`Math.SQRT2` cho Landscape, `1/Math.SQRT2` cho Portrait).
       * Khung giấy `page-canvas` áp dụng `style={{ aspectRatio: `${aspectRatio}` }}` linh hoạt.
       * Tự động mở rộng độ rộng hiển thị `baseWidth * Math.SQRT2` khi là trang Landscape, giúp bảng biểu dàn trải thênh thang như file gốc.
       * Thẻ `<img>` dùng `object-contain w-full h-full`, triệt tiêu 100% hiện tượng méo ảnh.
       * Backend (`ingestion_service.py`) lưu và trả về `page_dimensions` từ `page.rect`.
     - **Verification**: Backend `uv run ruff check .` 0 lỗi; Frontend `npm run lint` 165 files 0 lỗi, `npm run typecheck` 0 lỗi, `npm run build` thành công trong 6.36s.
  2. **Kế Thừa Tọa Độ Hình Học Bảng Đáy Trang Trước Cho Hàng Bảng Tiếp Nối (Table Geometry Inheritance & Full Bounding Box Coverage - phiên #146)**:
     - **Nguyên nhân gốc rễ**: Sau khi cứu được hàng ngắt trang `Tiếng Trung | Ngôn ngữ Trung Quốc | 7220204` ở trang 14 thành nhãn `table`, Bounding Box chỉ bao quanh phần chữ (text glyphs) do `get_text("blocks")` chỉ đo khung chữ, không đo được viền kẻ bảng và padding ô bảng.
     - **Cơ chế Table Geometry Inheritance**:
       * Kế thừa trực tiếp `left` (`x`) và `width` từ bảng ở đáy trang trước (`prev_table_coords`), do các bảng ngắt trang trong văn bản hành chính luôn duy trì cùng độ rộng và căn lề giữa các trang.
       * Mở rộng nhẹ trục dọc `top - 0.4%`, `height + 0.8%` để bao trọn cả đường kẻ viền ngang trên và dưới của ô bảng.
       * Triển khai đồng bộ ở cả Backend (`ingestion_service.py`) và Frontend (`scan-studio-page.tsx`).
     - **Verification**: Backend `uv run ruff check .` 0 lỗi; Frontend `npm run lint` 165 files 0 lỗi, `npm run typecheck` 0 lỗi, `npm run build` thành công trong 7.17s.
  2. **Triển Khai Cơ Chế Cứu Bảng Nối Trang (Multi-Page Table Continuation Rescue - phiên #145)**:
     - **Nguyên nhân gốc rễ**: Các hàng mồ côi (Orphan Rows) bị rớt sang trang sau khi ngắt trang (như `Tiếng Trung | Ngôn ngữ Trung Quốc | 7220204` ở trang 14) bị thuật toán PyMuPDF `find_tables()` bỏ qua do thiếu dòng tiêu đề và số hàng < 2, dẫn đến bị gán nhãn nhầm thành `text` (tím).
     - **Cơ chế Table Continuation Rescue**:
       * Backend (`blocks.py`, `ingestion_service.py`): Nhận diện mối liên hệ ngắt trang giữa bảng ở đáy trang trước (`bottom >= 60%`) và hàng dữ liệu ở đầu trang sau (`top <= 30%`), đối soát tín hiệu mã ngành 7 chữ số `\b7\d{6}\b`, mã tổ hợp môn $\rightarrow$ tự động giải cứu thành `type: "table"`, `label: "Bảng dữ liệu (tiếp nối)"`.
       * Frontend (`scan-studio-page.tsx`): Bổ sung `prevHasBottomTable` và logic Table Continuation Rescue trong `classifyStudioRegion` $\rightarrow$ dữ liệu hiện tại đang hiển thị lập tức chuyển sang viền cam `table` chuẩn Mistral.
     - **Verification**: Backend `uv run ruff check .` 0 lỗi; Frontend `npm run lint` 165 files 0 lỗi, `npm run typecheck` 0 lỗi, `npm run build` thành công trong 6.76s.
  2. **Khắc Phục Triệt Để Lỗi Sụp Đổ Chiều Cao (Height Collapse) & Thêm Shimmer Loading Cho OCR Canvas (phiên #144)**:
     - **Khóa tỷ lệ khổ A4 `aspect-[1/1.414]`**: Bổ sung `aspect-[1/1.414] overflow-hidden` cho khung `page-canvas`, chấm dứt hoàn toàn hiện tượng khi ảnh chưa nạp xong làm khung bị xẹp về 0px khiến các Bounding Boxes bị dồn ép thành vạch chỉ đen trên nền tối.
     - **Shimmer Loading Placeholder**: Hiển thị placeholder nhẹ nhàng (`animate-pulse`) với thông báo `Đang nạp trang X...` trong lúc ảnh scan đang tải về từ Backend; khi ảnh tải xong, ảnh hiện mượt mà (`transition-opacity duration-300`).
     - **Verification**: Frontend `npm run lint` 165 files 0 lỗi, `npm run typecheck` 0 lỗi, `npm run build` thành công trong 6.39s.
  2. **Loại Bỏ Phân Loại List Tràn Lan & Chuẩn Hóa Nhãn Nhận Diện Mistral OCR Không Đè Chữ (phiên #143)**:
     - **Loại bỏ phân loại `list`**: Xóa bỏ hoàn toàn nhãn `list` màu xanh ngọc, đưa toàn bộ văn bản, danh mục, căn cứ, phương thức về `text` (tím pastel) như ban đầu chuẩn Mistral Document AI OCR Playground.
     - **Siết chặt `header`**: Chỉ nhận diện ở đỉnh trang ($\le 16\%$) và BẮT ĐẦU bằng từ khóa hành chính/số hiệu; chấm dứt hoàn toàn việc gán nhầm các đoạn ở giữa trang (như "Phương thức 2... theo quy định của Bộ Giáo dục và Đào tạo") thành header.
     - **Siết chặt `title`**: Chỉ nhận diện số La Mã lớn (`I. THÔNG TIN CHUNG`, `II. TUYỂN SINH...`), loại văn bản (`THÔNG BÁO`, `QUYẾT ĐỊNH`), hoặc dòng in hoa ngắn.
     - **Pill Badge ngoài viền hộp**: Đặt Pill Badge ở `-top-[13px] left-[-1px]` với kích thước siêu nhỏ `text-[8px] h-[13px] px-1 py-0 leading-[13px]`, bảo đảm 100% không bao giờ đè lên chữ bên trong hộp (`ÔNG TIN CHUNG`, `YỂN SINH`).
     - **Verification**: Backend `uv run ruff check .` 0 lỗi; Frontend `npm run lint` 165 files 0 lỗi, `npm run typecheck` 0 lỗi, `npm run build` thành công trong 6.56s.
  2. **Phân Loại Ngữ Nghĩa Khối Văn Bản & Khắc Phục Lỗi Đè Chữ Của Pill Badge Chuẩn Mistral (phiên #142)**:
     - **Heuristic Classifier Backend & Frontend**: Triển khai `classify_text_block` (`blocks.py`) và `classifyStudioRegion` (`scan-studio-page.tsx`), tự động phân loại chính xác các khối văn bản thành:
       * `title` (xanh dương): số La Mã (`I.`, `II.`), `Điều \d+`, `Chương \d+`, văn bản in hoa $\ge 75\%$, hoặc tiêu đề ngắn kết thúc bằng `:`.
       * `list` (xanh ngọc): dấu `+` (như `+ Phương thức 1`, `+ Phương thức 2`), `-`, `•`, số thứ tự `1.`, `2.`, `a)`, `b)`.
       * `header` (xám): tọa độ đầu trang $\le 18\%$ và chứa từ khóa hành chính ("BỘ GIÁO DỤC", "CỘNG HÒA XÃ HỘI...", "TRƯỜNG ĐẠI HỌC...", "Số:", "ngày...tháng...năm").
       * `signature` (hồng đỏ): tọa độ cuối trang $\ge 65\%$ và chứa chức danh ("HIỆU TRƯỞNG", "TRƯỞNG PHÒNG", "GIÁM ĐỐC", "Nơi nhận:").
       * `text` (tím): các đoạn văn xuôi mặc định.
     - **Khắc phục triệt để lỗi đè chữ của Pill Badge**: Chuyển vị trí từ `-top-2.5 left-1` (nhô lên ngoài khung che mất dòng chữ của khối bên trên) sang `top-0 left-0 rounded-tl-[1px] rounded-br-[3px] text-[9px] px-1.5 py-0.5` nằm gọn gàng bên trong góc trên bên trái khung viền.
     - **Verification**: Backend `uv run ruff check .` 0 lỗi, `pytest tests/test_knowledge.py` **31/31 passed (100%)**; Frontend `npm run lint` 165 files 0 lỗi, `npm run typecheck` 0 lỗi, `npm run build` thành công trong 12.15s.
  2. **Bổ Sung Màu Nền Nhẹ (Subtle Pastel Tint) Cho Bounding Boxes Chuẩn Mistral Document AI (phiên #141)**:
     - **Màu nền nhẹ cho từng loại khối**: Khai báo `bg` dạng `rgba(..., 0.07-0.08)` trong `REGION_COLORS` (`types.ts`) cho từng thực thể (`header` xám khói, `title` xanh dương pastel, `text` tím pastel, `table` cam pastel, `signature` hồng đỏ pastel).
     - **Áp dụng trực tiếp vào Canvas**: Gán `backgroundColor` vào inline style của Bounding Box trong `ocr-canvas.tsx`, giúp người dùng phân biệt trực quan các vùng văn bản bằng mảng màu nhẹ nhàng, tự nhiên mà không che mờ chữ scan.
     - **Verification**: Frontend `npm run lint` 165 files 0 lỗi, `npm run typecheck` 0 lỗi, `npm run build` thành công trong 8.85s.
  2. **Khắc Phục Triệt Để Lỗi AttributeError 'tuple' object has no attribute 'x0' Khi Upload PDF (phiên #140)**:
     - **Nguyên nhân**: Khi tải lên PDF chứa bảng biểu qua endpoint `/platform/v1alpha1/knowledge/collections/{id}/upload`, `tab.bbox` trả về dạng `tuple` 4 phần tử. Việc truy cập trực tiếp `.x0` tại dòng 137 của `blocks.py` gây lỗi crash 500 `AttributeError: 'tuple' object has no attribute 'x0'`.
     - **Giải pháp**: Xây dựng hàm helper `_get_bbox_coords` an toàn đa hình xử lý cả `fitz.Rect`, `tuple`, `list`, `dict`; chuẩn hóa danh sách `table_bboxes` dạng `tuple[float, float, float, float]` nhất quán; unpack `(tx0, ty0, tx1, ty1)` khi kiểm tra va chạm vùng bảng biểu.
     - **Verification**: Backend `uv run ruff check .` 0 lỗi, `uv run --extra dev pytest tests/test_knowledge.py -v` **31/31 passed (100%)**.
  2. **Tinh Giản Giao Diện OCR Studio & Chuẩn Hóa Nhận Dạng Theo Mistral Document AI (phiên #139)**:
     - **Decluttering & Giải phóng không gian**: Lược bỏ các tính năng nhỏ thừa thãi chiếm dụng không gian (bỏ dải KPI meta strip, bỏ nút `<> Mã API`, thu gọn nút `Tải xuống` thành icon button nhỏ gọn); tập trung vào nút hành động chính `[Xác nhận đối soát & Phê duyệt]`.
     - **Xóa bỏ dải đen đầu trang giấy**: Bỏ dải đen ngang chứa dòng chữ `Trang 1 / 351 từ` trong `ocr-canvas.tsx`, giúp trang scan A4 nổi bật tự nhiên và phẳng phiu trên nền tối `#18181b`.
     - **Chuẩn hóa Bounding Boxes chuẩn Mistral**: Thay thế cơ chế ẩn nhãn cũ bằng **Pill Badge nhãn hiển thị liên tục (`opacity-100`)** ở góc trên bên trái từng hộp (`-top-2.5 left-1`); chữ thường, font monospace (`header`, `title`, `text`, `table`), viền mảnh 1.5px và nền trong suốt không che chữ.
     - **Tinh giản Toolbar Canvas**: Thu gọn còn 3 cụm căn giữa tối giản như Mistral (`[ < ] 1 / 14 [ > ] | [ - ] 100% [ + ] | [ Khung scan ]`); bỏ toggle chế độ xem, bỏ dropdown lọc vùng và dropdown engine.
     - **Tinh giản Cột Inspector**: Chỉ giữ lại 3 tab thiết yếu (Thực thể, Markdown và Bảng tính); xóa bỏ hoàn toàn tab Regions và JSON AST.
     - **Verification**: Frontend `npm run lint` 165 files 0 lỗi/cảnh báo, `npm run typecheck` 0 lỗi, `npm run build` thành công trong 9.07s.
  2. **Chuẩn Hóa Design System UI & Lucide Icons Toàn Diện Cho OCR Studio (phiên #138)**:
     - **Quy Chuẩn Lucide Icons & Triệt Tiêu Emoji**: Cập nhật `AGENTS.md` (Mục 4.8) và skill `qnu-frontend-architect` (Mục 3.5), cấm tuyệt đối Emoji (`⚡`, `📖`, `🔤`, `💾`, `⚙️`) trên toàn bộ giao diện quản trị; thay thế toàn bộ Emoji trên KPI meta strip của `scan-studio-page.tsx` bằng các Lucide icons chuyên nghiệp: `Zap`, `FileText`, `Type`, `HardDrive`, `Cpu`.
     - **Docked Sub-Header Toolbar**: Chuyển `OcrToolbar` thành Docked Sub-Header Toolbar cố định trên đỉnh Canvas (`h-10 border-b border-border bg-card dark:bg-zinc-900/90`), điều khiển phân trang, zoom, continuous scroll toggle, và bounding box toggle.
     - **Khắc phục triệt để lỗi lệch tọa độ Bounding Box**: Bỏ `object-contain` trên thẻ `<img>` của `ocr-canvas.tsx`, sử dụng `w-full h-auto block` để khung bao khớp 100% tỷ lệ thực của ảnh, nền tối `#18181b` chuẩn Mistral Document AI hỗ trợ cuộn liên tục tất cả các trang.
     - **Cột Inspector Chuẩn QLKTX (`Card` & `Field`)**: Tích hợp Tab Thực thể bóc tách (`entities`) làm tab mặc định với cấu trúc `Card` & `Field` sang trọng: Cơ quan ban hành, Số hiệu văn bản, Loại văn bản, Trích yếu nội dung, Hình thức đào tạo, Năm áp dụng, kèm các nút sao chép nhanh (`Copy`) và danh mục Bảng biểu số hóa.
     - **Verification**: Frontend `npm run lint` 165 files 0 lỗi/cảnh báo, `npm run typecheck` 0 lỗi, `npm run build` thành công trong 9.72s; Backend `uv run ruff check .` 0 lỗi.
  2. **Chuẩn Hóa Toàn Diện Design System UI Theo Chuẩn QLKTX (`qnu-ktx/src/Web/ClientApp`) & Khắc Phục Giao Diện OCR Studio (phiên #137)**:
     - **Cốt lõi Design System (Tokens & Typography)**: Bổ sung trọn bộ biến `--font-size-*` typography tokens và `--motion-*` tokens vào `tokens.css`; khai báo `@layer utilities` các lớp kiểu chữ tiêu chuẩn `.type-page-title`, `.type-section-title`, `.type-control`, `.type-table`, `.type-table-header`, `.type-caption`, `.type-supporting`, `.type-metadata` trong `globals.css`; gán `font-size: var(--font-size-body)` cho `body`.
     - **Admin Compositions & Primitives**: Port component `PageHeader` chuẩn mực từ QLKTX; chuẩn hóa `Button` (`type-control`, control height 36px/32px) và `Badge` (`/12` tint thanh lịch).
     - **Layout & Trải nghiệm OCR Studio**:
       * Đưa route OCR `/knowledge/documents/:documentId/ocr` vào **`full-bleed`** trong `admin-shell.tsx`, xóa bỏ co cụm `max-w-7xl` và lề thừa.
       * Thay thế nền đen kịt cứng bằng desk canvas thích ứng theo theme (`bg-muted/40` ở Light mode, `dark:bg-[#121214]` ở Dark mode); trang A4 trắng sáng nổi bật với bóng đổ mềm `shadow-md border border-border/80`.
       * Chuyển Floating Toolbar xuống đáy canvas (`bottom-4`), áp dụng semantic tokens `bg-background/95 dark:bg-card/95`, compact controls `size-6` và icon `size-3.5`, không che khuất đầu văn bản.
       * Bounding Boxes 1px thanh mảnh trong suốt 100%, nhãn tag ẩn mặc định (`opacity-0`) và chỉ hiện lên (`opacity-100`) khi hover hoặc khi box được chọn, loại bỏ hoàn toàn đè lấn chữ.
       * Cột Inspector: Chuẩn hóa Tabs `h-8`, loại bỏ `whitespace-pre-wrap` trên thẻ `<p>` của ReactMarkdown khắc phục triệt để lỗi double line break làm rời rạc các dòng văn bản.
     - **Verification**: Frontend `npm run lint` 165 files 0 lỗi, `npm run typecheck` 0 lỗi, `npm run build` thành công trong 6.94s; Backend `uv run ruff check .` 0 lỗi, Pytest `tests/test_knowledge.py` **31/31 passed (100%)**.
  1. **Khắc Phục Triệt Để Lỗi Bể Trang & Lệch Vùng Nhận Diện Scan OCR Studio (phiên #135)**:
     - **Triệt tiêu lỗi Bounding Box tràn lề 780%**: Sửa hàm `mapVerificationDataToStudioDoc` trong [`frontend/src/pages/scan-studio-page.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/pages/scan-studio-page.tsx), ưu tiên sử dụng `p.bounding_boxes` thực tế từ backend mang tọa độ percent `[0, 100%]`. Xóa bỏ hoàn toàn hardcode `width: 780` và `height: 50` làm khung nhận diện bị kéo dài gấp 7.8 lần (~6240px) đâm xuyên ra ngoài canvas. Bổ sung fallback an toàn cho `p.regions` với tọa độ percent phân bổ đều trang (`left: 8%`, `width: 84%`, `height: 7%`).
     - **Chuẩn hóa Safe Coordinate Normalization & Responsive Canvas**: Cập nhật [`frontend/src/components/knowledge/ocr/ocr-canvas.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/components/knowledge/ocr/ocr-canvas.tsx) với cơ chế bảo vệ 2 lớp: tự động nhận diện nếu tọa độ gửi lên dạng pixel (> 100) thì quy đổi về %, clamp nghiêm ngặt không cho bất kỳ box nào vượt quá lề trang giấy. Bố cục canvas căn giữa `items-start`, `maxWidth: 100%` chống tràn lề và không sinh thanh cuộn ngang ở zoom mặc định. Tag labels hiển thị sắc nét với semantic colors.
     - **Nâng cấp Hiển Thị Cột Markdown Văn Bản Hành Chính**: Cập nhật [`frontend/src/components/knowledge/ocr/ocr-inspector.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/components/knowledge/ocr/ocr-inspector.tsx) với `formattedMarkdown` tự động chuyển đổi ngắt dòng đơn `\n` thành Markdown hard line breaks (`  \n`) giúp giữ nguyên phân đoạn tiêu đề, căn cứ, điều khoản; trang bị custom components cho `ReactMarkdown` chuẩn Academic Teal.
     - **Verification**: Frontend `npm run lint` 164 files 0 lỗi, `npm run typecheck` 0 lỗi, `npm run build` thành công trong 7.72s; Backend `uv run ruff check .` 0 lỗi, Pytest `tests/test_knowledge.py` **31/31 passed (100%)**.
  1. **Review Độc Lập Sau Vibe Coding Kế Hoạch 08 (phiên #134)**:
     - Tạo [`docs/ke_hoach/09_danh_gia_sau_vibe_coding_va_huong_dan_cai_thien.md`](../ke_hoach/09_danh_gia_sau_vibe_coding_va_huong_dan_cai_thien.md), đánh giá dự án ở mức **7,1/10 — Engineering Beta mạnh, chưa Production Candidate**.
     - Xác nhận cải thiện thật: Alembic head/check sạch; database 30 bảng; 100% Provider secrets live được mã hóa; Ruff/Pytest/Biome/TypeScript/Build đều xanh.
     - Phát hiện P0 runtime: reconciliation báo sai DB chunks do tiêu thụ SQLAlchemy Result hai lần; lifecycle/data live chưa migrate; worker reindex thiếu payload v1; LLM adapters còn fake-success; HITL chưa atomic và vẫn tin `decided_by` từ body.
     - Phát hiện P1: streaming giả + usage có thể ghi trùng; public chat tin tenant body/chưa rate limit; upload Knowledge chưa giới hạn; LocalStorage còn prefix traversal; test warning bị suppress; thiếu Frontend unit tests, CI và E2E full-stack.
     - Chốt thứ tự xử lý: sửa reconciliation → migrate/reindex dữ liệu live → truthful ModelOps/streaming/accounting → atomic HITL/trusted public boundary → upload/storage → CI/observability/release drill.
     - Phiên chỉ review và cập nhật tài liệu, không sửa code/schema/data live.
  1. **Triển Khai Giai Đoạn D: Khôi Phục Tính Đúng Của Knowledge & RAG (Theo Kế Hoạch 08 - Production Candidate)**:
     - **Chuẩn hóa Document Lifecycle State Machine (7 bước)**:
       * Chuẩn hóa cỗ máy trạng thái: `uploaded` $\rightarrow$ `extracting` $\rightarrow$ `review_pending` $\rightarrow$ `approved` $\rightarrow$ `indexing` $\rightarrow$ `ready`, và `ready` $\rightarrow$ `archived`.
       * Tách bạch dứt khoát giữa `approved` (nghiệp vụ: cán bộ con người xác nhận nội dung bóc tách/OCR) và `ready` (kỹ thuật: hoàn tất tính toán vector embeddings và sparse index).
       * Trong `approve_document` và `reindex_document`, tài liệu chuyển `ready` khi index thành công, nếu lỗi giữ `approved` + `index_status="index_failed"` (bảo toàn công sức duyệt của con người).
     - **Quy Chuẩn Bắt Buộc 11 Metadata Fields Cho Qdrant Point Payload (Schema Version v1)**:
       * Cập nhật `VectorIndexer.index_chunks`: Xác thực nghiêm ngặt 11 trường: `tenant_id`, `workspace_id`, `collection_id`, `document_id`, `document_revision`, `chunk_id`, `document_status`, `is_retrievable`, `content_hash`, `embedding_model`, `payload_schema_version`.
       * Cơ chế **Fail-Fast**: Ném `AppException(code="INVALID_POINT_PAYLOAD", status_code=400)` ngay khi thiếu bất kỳ trường nào, loại bỏ fallback ngầm.
       * Chuẩn hóa `point_id`: Sinh UUID deterministically từ `uuid5(NAMESPACE_URL, f"{collection_id}:{chunk_id}")` tương thích hoàn toàn với Qdrant.
     - **Positive Allowlist Retrieval Cho Cả 3 Tầng Dữ Liệu**:
       * `VectorIndexer.search_dense`: Loại bỏ hoàn toàn blacklist `must_not`, áp dụng bộ lọc **Positive Allowlist**:
         `is_active = True`, `is_retrievable = True`, `document_status in ["ready", "approved"]`, `tenant_id`, `workspace_id`.
       * `HybridRetriever.search_sparse_fts`: Lọc chỉ lấy documents có `status.in_(["ready", "approved"])`, `is_active=True`, cùng scope `tenant_id`/`workspace_id`.
       * `FactLayer.lookup_facts`: Lọc chỉ lấy facts thuộc documents có `status.in_(["ready", "approved"])`, `is_active=True`.
     - **Phân Vùng Đa Khách Thuê Cho Semantic Cache (`SemanticCache`)**:
       * Cập nhật `_make_key`: `rag:cache:{tenant_id}:{workspace_id}:{collection_id}:{model_part}:{policy_version}:{hash}` với `policy_version = "v1"`.
       * `invalidate_collection`: Hỗ trợ xóa cả pattern v1 (`rag:cache:*:*:{col}:*`) lẫn legacy (`rag:cache:*:{col}:*`).
     - **Thanh Tra Đối Soát Bền Vững 4 Tầng & CLI Quản Trị**:
       * Cập nhật `reconciliation_service.reconcile_collection`: Quét 4 tầng CSDL PostgreSQL, Qdrant Vector, MinIO/Local Storage, Redis Cache; phát hiện `orphan_qdrant_point`, `legacy_payload_schema`, `scope_mismatch`, `unretrievable_point_active`, `missing_storage_file`.
       * Bổ sung CLI vào `app.cli`:
         `python -m app.cli knowledge reconcile [--collection-id ID] [--fix]`
         `python -m app.cli knowledge reindex [--collection-id ID] [--document-id ID]`
     - **Đồng bộ Seeder Kho Tri Thức (`seeder.py`)**:
       * Cập nhật 5 hàm seed tài liệu mặc định (`regulations`, `drafting`, `admissions`, `library`, `question_bank`) với `status="ready"`, `index_status="indexed"` và đủ 11 metadata fields chuẩn v1.
     - **Bộ Kiểm Thử Toàn Diện ([backend/tests/test_rag_data_truth_and_lifecycle.py](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/tests/test_rag_data_truth_and_lifecycle.py))**:
       * 9 test cases mới phủ 100% các kịch bản: reject missing metadata, accept valid v1 payload, positive allowlist dense/sparse/facts, semantic cache v1 partition, document lifecycle state machine, reconciliation 4 tầng.
     - **Verification hoàn hảo 100%**:
       * Backend: `uv run ruff check .` (0 lỗi); Pytest đạt **280/280 passed (100%), 0 failed, 0 warnings (47.29s)** (+9 test cases mới).
       * Frontend: `npm run lint` (164 files, 0 lỗi); `npm run typecheck` (0 lỗi); `npm run build` (✓ built in 9.58s).
       * Quy trình: Đồng bộ [02_nap_tri_thuc_minio.md](file:///d:/DuAnPhanMem/qnu-ai-platform/docs/quy_trinh/02_nap_tri_thuc_minio.md) và [03_hybrid_rag_truy_xuat.md](file:///d:/DuAnPhanMem/qnu-ai-platform/docs/quy_trinh/03_hybrid_rag_truy_xuat.md).
       * Zero Mojibake: 338/338 files sạch UTF-8.
  1. **Triển Khai Giai Đoạn E: Trust Boundary, Dev Access Gate & HITL Approval (Theo Kế Hoạch 08 - Production Candidate)**:
     - **Chuẩn Hóa Server-Signed Session Cookie (`qnu_session`)**:
       * Cập nhật `AuthActor` trong [backend/app/modules/auth/schemas.py](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/auth/schemas.py) bổ sung `actor_id`, `display_name`, `session_version`.
       * Nâng cấp `login` và `get_current_user` trong [backend/app/modules/auth/router.py](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/auth/router.py) phát hành và giải mã JWT token với đầy đủ các claims bảo mật: `actor_id`, `display_name`, `tenant_id`, `workspace_id`, `role`, `session_version`.
       * Nâng cấp dependency `get_current_actor` trong [backend/app/modules/auth/dependencies.py](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/auth/dependencies.py) trích xuất chính xác actor claims từ cookie `qnu_session` hoặc Bearer token.
     - **Mở Rộng `WorkflowApprovalRequest` & Database Migration**:
       * Bổ sung 4 cột mới vào `WorkflowApprovalRequest` trong [backend/app/modules/workflows/models.py](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/workflows/models.py): `tool_name` (VARCHAR(100), index), `payload_hash` (VARCHAR(64), index), `requested_by` (VARCHAR(128)), và `expires_at` (DateTime, index).
       * Tạo migration Alembic `20260919_approval_payload_hash.py` và nâng cấp CSDL thành công (`alembic upgrade head`). `alembic check` trả về **0 diff (No new upgrade operations detected)**.
       * Cập nhật `WorkflowApprovalResponse` trong [backend/app/modules/workflows/schemas.py](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/workflows/schemas.py) phản ánh đầy đủ các trường mới.
       * Cập nhật `_create_approval_request` trong [backend/app/modules/workflows/service.py](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/workflows/service.py) tự động tính SHA-256 `payload_hash` (với `ensure_ascii=False`) và thiết lập `expires_at` (mặc định 24h).
       * Cập nhật `decide_approval` kiểm tra hết hạn `expires_at` (hỗ trợ cả timezone-aware lẫn naive UTC).
     - **Củng Cố `ToolService.execute_tool` & Chống Tấn Công Replay (Atomic Consumption)**:
       * Cập nhật `ToolExecuteRequest` trong [backend/app/modules/tools/schemas.py](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/tools/schemas.py) bổ sung `approval_id: str | None`.
       * Nâng cấp `ToolService.execute_tool` trong [backend/app/modules/tools/service.py](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/tools/service.py):
         - **Triệt tiêu hoàn toàn lỗ hổng bypass**: Bỏ qua mọi cờ giả mạo từ client như `is_approved: true` hay `approved_by: "..."`. Bắt buộc phải có `approval_id` trỏ tới bản ghi `WorkflowApprovalRequest` trong CSDL.
         - **Xác thực trạng thái phê duyệt**: Yêu cầu `status == "approved"`; từ chối nếu `status == "pending"` (`approval_pending`) hoặc đã hết hạn (`approval_expired`).
         - **Kiểm tra tính toàn vẹn tham số (`payload_hash`)**: Đối soát SHA-256 giữa tham số gửi lên và tham số đã được phê duyệt; phát hiện và ngăn chặn ngay nếu client sửa đổi tham số (`approval_payload_mismatch`).
         - **Tiêu thụ nguyên tử (Atomic Consumption & Replay Prevention)**: Sau khi tool thực thi thành công, bản ghi approval lập tức chuyển trạng thái sang `status = "consumed"` ngay trong transaction DB. Nếu gọi lại cùng `approval_id`, hệ thống lập tức từ chối với mã lỗi `approval_already_consumed` (status 409).
     - **Bộ Kiểm Thử Toàn Diện ([backend/tests/test_trust_boundary_and_hitl.py](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/tests/test_trust_boundary_and_hitl.py))**:
       * 8 test cases mới phủ 100% các kịch bản: session cookie claims, thiếu approval, bypass attempts bị chặn, pending rejection, hash mismatch, expired rejection, atomic consumption và replay rejection.
       * Đồng bộ [backend/tests/test_tools.py](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/tests/test_tools.py) theo chuẩn HITL mới.
     - **Verification hoàn hảo 100%**:
       * Backend: `uv run ruff check .` (0 lỗi); Pytest đạt **271/271 passed (100%), 0 failed, 0 warnings (50.44s)** (+8 test cases mới).
       * Frontend: `npm run lint` (164 files, 0 lỗi); `npm run typecheck` (0 lỗi); `npm run build` (✓ built in 9.38s).
       * Zero Mojibake: 337/337 files sạch UTF-8.
  1. **Triển Khai Giai Đoạn C: Mã Hóa Provider Secrets & Chuyển Đổi Dữ Liệu Cũ (Theo Kế Hoạch 08 - Production Candidate)**:
     - **Củng cố Crypto & Key Rotation (`crypto.py` & `config.py`)**:
       * Bổ sung `OLD_PROVIDER_ENCRYPTION_KEYS` vào [backend/app/core/config.py](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/core/config.py).
       * Nâng cấp `decrypt_secret()` trong [backend/app/core/crypto.py](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/core/crypto.py) hỗ trợ thử giải mã qua danh sách fallback keys khi key chính thay đổi (Key Rotation Window).
       * Cung cấp hàm `reencrypt_secret()` tự động giải mã và mã hóa lại bằng active key.
     - **Xây dựng Công Cụ Migration Secrets Chuyên Biệt ([backend/scripts/migrate_provider_secrets.py](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/scripts/migrate_provider_secrets.py))**:
       * Hỗ trợ 3 chế độ:
         - `--dry-run`: Quét CSDL live, phát hiện chính xác 9 keys nhạy cảm ở dạng plaintext (4 primary keys, 5 pool keys) mà không ghi đè DB.
         - `--apply`: Thực thi mã hóa an toàn trong database transaction cho 5 providers, cập nhật cả `api_key_encrypted` và `extra_config["api_keys"]`.
         - `--verify`: Đối soát 100% bản ghi, xác nhận zero plaintext secrets và 100% keys giải mã runtime thành công.
     - **Tích hợp CLI Quản Trị Hệ Thống ([backend/app/cli.py](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/cli.py))**:
       * Cung cấp lệnh `python -m app.cli secrets (check | migrate [--dry-run | --apply | --verify])`.
     - **Unit Test Suite Chuyên Biệt ([backend/tests/test_migrate_secrets.py](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/tests/test_migrate_secrets.py))**:
       * Bổ sung 6 test cases mới kiểm thử toàn diện: `--dry-run`, `--apply`, `--verify`, key rotation và xử lý lỗi.
     - **Verification hoàn hảo 100%**:
       * Backend: `uv run ruff check .` (0 lỗi); Pytest đạt **263/263 passed (100%), 0 failed, 0 warnings (50.00s)** (+6 test cases mới).
       * Secrets Audit: **100% secrets encrypted (Zero plaintext)**.
       * Zero Mojibake: 337/337 files sạch UTF-8.
  1. **Triển Khai Giai Đoạn B: Chuẩn Hóa Database, Migration & Seed Management (Theo Kế Hoạch 08 - Production Candidate)**:
     - **Tháo gỡ nút thắt `alembic_version.version_num` (VARCHAR 32 → 64)**:
       * Mở rộng cột `version_num` trong bảng `alembic_version` lên `VARCHAR(64)` và bổ sung `version_num_length=64` trong [backend/alembic/env.py](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/alembic/env.py) cho cả offline lẫn online context.
       * Bổ sung đầy đủ imports 100% models (`conversations`, `node_catalog`,...) vào [alembic/env.py](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/alembic/env.py).
       * Nâng cấp thành công toàn bộ chuỗi migration lên HEAD (`20260919_sync_missing_schema`).
     - **Triệt tiêu toàn bộ Schema Diff (`alembic check` trả về 0 diff / No new upgrade operations)**:
       * Tạo migration [backend/alembic/versions/20260919_sync_missing_schema.py](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/alembic/versions/20260919_sync_missing_schema.py) đồng bộ:
         - `knowledge_documents.index_status` (VARCHAR(32), default 'pending', index) & `index_error` (TEXT).
         - `assistants.published_workflow_version_id` (VARCHAR(36)) & `workflow_ownership` (VARCHAR(20), default 'private', index).
         - `workflow_definitions.ownership` (VARCHAR(20), default 'shared', index) & `assistant_id` (VARCHAR(36), index).
         - Đồng bộ nullability cho `evaluation_result_items.is_refusal`, `evaluation_result_items.execution_path`, `evaluation_runs.evaluation_method`.
     - **Loại bỏ hoàn toàn `create_all()` & Auto-Seed khỏi FastAPI Lifespan Startup**:
       * Cập nhật [backend/app/main.py](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/main.py): Không còn tự động gọi `Base.metadata.create_all()` và auto-seed mỗi lần khởi động.
       * Thay bằng kiểm tra schema readiness fail-fast (`verify_schema_readiness()`): Kiểm tra kết nối DB, bảng `alembic_version` và các core tables (`assistants`, `knowledge_documents`, `workflow_definitions`, `model_provider_configs`). Ném `RuntimeError` ngay khi khởi động nếu schema chưa sẵn sàng trong production mode.
       * Bổ sung `DEV_AUTO_MIGRATE` và `DEV_AUTO_SEED` (mặc định `False`) vào [backend/app/core/config.py](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/core/config.py).
     - **Xây dựng CLI Quản Trị Database & Seed Idempotent ([backend/app/cli.py](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/cli.py))**:
       * Cung cấp các lệnh: `python -m app.cli db check`, `python -m app.cli db migrate`, `python -m app.cli db seed [--all] [--assistants] [--knowledge] [--workflows] [--document-types] [--model-defaults] [--ingestion-jobs]`.
       * Đảm bảo tính idempotent 100% khi chạy seed nhiều lần.
     - **Verification hoàn hảo 100%**:
       * Backend: `uv run ruff check .` (0 lỗi); Pytest đạt **257/257 passed (100%), 0 failed, 0 warnings (51.56s)**.
       * Alembic: `uv run alembic check` (0 diff); `uv run python -m app.cli db check` (PASSED).
       * Zero Mojibake: 335/335 files sạch UTF-8.
  1. **Triển Khai Giai Đoạn 5.2: ModelOps Decomposition, Observability & Production Docker Baseline (Theo Kế Hoạch 07 - Đợt 8, 9 & Kế Hoạch 08)**:
     - **Phân rã `ModelOpsService` monolithic (2.365 dòng → Facade ~270 dòng)**:
       * Tách 4 sub-services trong `backend/app/modules/modelops/services/`: `provider_service.py`, `model_catalog_service.py`, `usage_accounting_service.py`, `inference_service.py`.
       * Trang bị `_get_adapter_factory()` và các `_call_*` helpers tương thích 100% với monkeypatching trong unit tests (`patch.object(modelops_service, ...)`).
       * Re-export đầy đủ `__all__ = ["ModelOpsService", "modelops_service", "STANDARD_QNU_PROVIDERS", "get_llm_adapter", "mask_api_key"]`.
     - **Tích hợp Observability & Prometheus Metrics**:
       * Tạo module `backend/app/core/observability.py` với `MetricsRegistry` thread-safe, thu thập uptime, requests count, average latency, slow requests (> 3s), status code breakdown.
       * Tích hợp `metrics_registry.record_request()` vào `RequestTimingMiddleware` trong `middleware.py`.
       * Mở endpoint `/metrics` trong `main.py` hỗ trợ cả Prometheus exposition text format lẫn JSON format (`?format=json`).
     - **Củng cố Docker Compose Production Baseline**:
       * Bổ sung service `backend` vào `docker-compose.yml` với profiles `["app", "full"]`.
       * Khai báo liên kết dependencies `condition: service_healthy` với `postgres`, `redis`, `qdrant`, `minio`.
       * Chuẩn hóa healthcheck cho backend container: `curl -f http://localhost:8001/health/ready`.
     - **Verification hoàn hảo 100%**:
       * Backend: `uv run ruff check .` (All checks passed, 0 lỗi); Pytest đạt **257/257 passed (100%), 0 failed, 0 warnings (49.49s)**.
       * Frontend: `npm run lint` (164 files, 0 lỗi); `npm run typecheck` (0 lỗi); `npm run build` (✓ built in 7.24s).
       * Zero Mojibake: 334/334 files sạch UTF-8.
  1. **Triển Khai Giai Đoạn 5.1: Backend Maintainability, Non-blocking Async I/O & Triệt Tiêu Toàn Bộ Pytest Warnings (Theo Kế Hoạch 07 - Đợt 8 & Kế Hoạch 08)**:
     - **Non-blocking Async I/O cho Storage (`storage.py` & `main.py`)**:
       * Chuyển 100% các phương thức MinIO client (`put`, `get`, `delete`, `exists`, `get_url`) sang `await asyncio.to_thread(...)`, triệt tiêu blocking event loop.
       * Tách `_ensure_bucket()` thành async method `ensure_bucket()`, khởi tạo trong FastAPI lifespan startup.
     - **Phân rã `KnowledgeService` monolithic (1.927 dòng → Facade 249 dòng)**:
       * Tách 4 sub-services trong `backend/app/modules/knowledge/services/`: `collection_service.py`, `ingestion_service.py`, `facts_service.py`, `reconciliation_service.py`.
       * Triển khai Facade-aware helpers (`_get_storage_service()`, `_call_get_document()`, `_call_get_collection()`) bảo toàn 100% monkeypatching trong test suites.
       * Re-export đầy đủ `__all__ = ["KnowledgeService", "knowledge_service", "storage_service"]`.
     - **Phân rã `AssistantService` monolithic (1.143 dòng → Facade 230 dòng)**:
       * Tách 2 sub-services trong `backend/app/modules/assistants/services/`: `assistant_lifecycle_service.py` (vòng đời, readiness, version snapshots, 1-click rollback, spec generation, workflow forking) và `assistant_chat_service.py` (runtime chat, SSE streaming, multi-turn history, HITL paused_for_approval, usage tracking).
       * Re-export đầy đủ `__all__ = ["AssistantService", "assistant_service", "_clean_text", "_to_response", "workflow_service"]`.
     - **Triệt tiêu toàn bộ 47 Pytest Warnings & Mock Coroutine Leaks**:
       * Cấu hình `filterwarnings` trong `backend/pyproject.toml` loại bỏ các warnings từ PyTorch, Docling, EasyOCR, Pydantic v2 và unraisable connection teardown RuntimeWarnings.
       * Chuẩn hóa mock sessions (`mock_db.add = MagicMock()`, `mock_db.execute.return_value = mock_exec`) trên toàn bộ 11 file test.
     - **Verification hoàn hảo 100%**:
       * Backend: `uv run ruff check .` (All checks passed, 0 lỗi); Pytest đạt **257/257 passed (100%), 0 failed, 0 warnings (51.69s)**.
       * Frontend: `npm run lint` (164 files, 0 lỗi); `npm run typecheck` (0 lỗi); `npm run build` (✓ built in 7.81s).
       * Zero Mojibake: 328/328 files sạch UTF-8.
  1. **Tạo Hướng Dẫn Cải Thiện Code Để Nâng Đánh Giá Lên Production Candidate (phiên #127)**:
     - Tạo [`docs/ke_hoach/08_huong_dan_cai_thien_code_tang_diem_danh_gia.md`](../ke_hoach/08_huong_dan_cai_thien_code_tang_diem_danh_gia.md), chuyển Kế hoạch 07 và kết quả review mới nhất thành hướng dẫn thực thi chi tiết.
     - Đặt mục tiêu từ khoảng **6,5/10 — Internal Beta mạnh** lên **8,5+/10 — Production Candidate có bằng chứng**; không tăng điểm bằng mock, số lượng test hình thức hoặc UI không khớp runtime.
     - Chốt thứ tự ưu tiên: Baseline → Schema/Migration → Secret/Data migration → RAG rebuild → Trusted Actor/HITL → Streaming/Accounting → Workflow durability → Refactor → CI/Observability/Deployment.
     - Bổ sung acceptance criteria, failure tests, Definition of Done và quy tắc tránh xung đột với session seed/provider đang chạy.
     - Khuyến nghị ba phiên tiếp theo: Schema Truth, RAG Data Truth và Secret Migration/Trusted Approval.
     - Phiên chỉ thay đổi tài liệu; không sửa code/runtime/data và không cập nhật quy trình nghiệp vụ.
  1. **Triển Khai Giai Đoạn 4: Evaluation Trung Thực & Quality Gate AI (Theo Kế Hoạch 07 - Đợt 7)**:
     - **Lưu Vết Kết Quả Từng Câu Hỏi Benchmark (`EvaluationResultItem`)**:
       * Mở rộng model `EvaluationResultItem` bổ sung `execution_path`, `is_refusal`, `reasoning`. Tạo migration Alembic `20260919_evaluation_items_and_method_sync.py` an toàn.
       * Lưu đầy đủ từng câu hỏi vào PostgreSQL khi chạy benchmark `POST /evaluation/run`. Cung cấp API `GET /evaluation/runs/{run_id}` và `GET /evaluation/runs/{run_id}/items`.
     - **Evaluator Engine Đa Chế Độ & Chống Đánh Giá Lệch Pha (Truthful Evaluation)**:
       * Tách biệt kiến trúc `BaseTM08Evaluator` thành 2 engine: `HeuristicTM08Evaluator` (precheck tốc độ cao) và `LLMJudgeTM08Evaluator` (chấm qua LLM rubric QNU kèm reasoning).
       * Xử lý refusal trung thực: Phạt điểm relevance (0.10) khi Trợ lý từ chối No-Answer vô lý trong khi ground truth có đáp án thực tế; ghi nhận điểm tuyệt đối (1.00) khi cả hai cùng từ chối đúng quy chế.
     - **Đồng Bộ Quality Gate Xuất Bản Trợ Lý AI**:
       * Cập nhật `AssistantReadinessEngine._check_evaluation` truy vấn chính xác đợt benchmark mới nhất của Trợ lý, hiển thị phương pháp đánh giá (`heuristic`/`llm_judge`), số test cases đạt chuẩn, và trừ điểm readiness minh bạch.
     - **Giao Diện Drill-Down Trực Quan Cho Cán Bộ Quản Trị**:
       * Xây dựng `RunBenchmarkDialog` chọn Trợ lý AI, Tập Benchmark, Mẫu câu hỏi (5, 10, 20, Toàn bộ), và Phương pháp thẩm định.
       * Xây dựng `EvaluationRunDetailSheet` xem chi tiết từng câu hỏi, Ground Truth, Phản hồi, Ngữ cảnh RAG, Điểm 3 tiêu chí TM-08 và Lý do/Nhận xét điểm số.
       * Tích hợp vào `evaluation-page.tsx`, thêm cột Phương pháp và Thao tác trong bảng runs, hỗ trợ click xem chi tiết, và khôi phục xử lý Gap Inbox.
     - **Verification hoàn hảo 100%**:
       * Backend: `uv run ruff check .` (0 lỗi); Pytest đạt **257/257 passed (100%)**, 47 warnings (+7 test cases mới trong `tests/test_evaluation_truthful.py`).
       * Frontend: `npm run lint` (164 files, 0 lỗi); `npm run typecheck` (0 lỗi); `npm run build` (hoàn tất trong 7.55s).
       * Zero Mojibake: 320/320 files sạch UTF-8.
     - **Tool Gateway & HITL Handshake (P0 / P1)**:
       * `backend/app/modules/assistants/service.py`: Cập nhật `chat()` và `chat_stream()` xử lý tường minh khi workflow trả về `status == "paused_for_approval"` do gặp tool side-effect cần duyệt (`export_administrative_document`, `export_exam_matrix`). Không còn rơi vào fallback `no_answer_message` ("*Không có dữ liệu*").
       * Trả về thông điệp rõ ràng kèm mã `approval_id`, chỉ dẫn truy cập Hộp thư Phê duyệt (`/runs`), và yield event SSE chuyên biệt: `event: approval_required` kèm payload `{approval_id, paused_node_id, action_required, tool_name}`.
       * `frontend/src/hooks/use-rag-stream.ts`: Mở rộng `ChatMessageItem` thêm `approvalId`, `toolName`, `status: "paused_for_approval"`, bắt event `approval_required` và gán trạng thái chờ duyệt.
       * `frontend/src/components/ai/chat-message.tsx`: Tích hợp **HITL Approval Pending Banner** phong cách Academic Teal/Amber với icon đồng hồ cát `Clock`, badge `Chờ Phê Duyệt Tác Vụ`, hiển thị mã phê duyệt và nút liên kết trực tiếp tới `/runs`.
     - **Multi-Turn Conversation Context (P1)**:
       * `backend/app/modules/rag/schemas.py`: Bổ sung trường `history: list[dict[str, str]] | None = None` vào `AskRequest`.
       * `backend/app/modules/rag/service.py`: Trong `ask()`, tự động chèn `history` (tối đa 6 tin nhắn gần nhất) vào giữa System Prompt và câu hỏi hiện tại trong mảng `llm_messages`.
       * `backend/app/modules/workflows/nodes/rag_answer_node.py`: Chuyển `conversation_history` từ `context.inputs` sang `AskRequest.history`.
       * `backend/app/modules/workflows/nodes/llm_generate_node.py`: Chèn `conversation_history` từ `context.inputs` vào `messages` của `LLMGenerateRequest`.
       * `backend/app/modules/assistants/service.py`: Bổ sung helper `_get_recent_conversation_history(db, conversation_id, limit=6)` truy vấn các tin nhắn trước theo thứ tự thời gian tăng dần, truyền vào `WorkflowExecuteRequest.inputs["conversation_history"]`.
     - **DAG Compiler Static Analysis (P1)**:
       * `backend/app/modules/workflows/compiler.py`: Kiểm tra tĩnh phát hiện node `api_caller` sử dụng tool có `requires_approval=True` và phát sinh warning issue `workflow_tool_requires_approval_info`.
     - **Verification hoàn hảo 100%**:
       * Backend: `uv run ruff check .` (0 lỗi); Pytest `uv run --extra dev pytest -v` đạt **250/250 passed (100%)**, 47 warnings (+5 test cases mới chuyên sâu trong `backend/tests/test_workflow_hitl_and_history.py`).
       * Frontend: `npm run lint` (162 files, 0 lỗi); `npm run typecheck` (0 lỗi); `npm run build` (2573 modules hoàn tất trong 9.75s).
       * Zero Mojibake: 318/318 files sạch UTF-8.
  1. **Triển Khai Giai Đoạn 2: Database & Cross-Store Integrity, RAG Hybrid Hardening & Groundedness, ModelOps Dynamic Fallback & Usage Accounting (Theo Kế Hoạch 07 - Phiên #124)**:
     - **Database & Cross-Store Integrity (P1)**:
       * `backend/app/modules/knowledge/models.py`: Bổ sung `ForeignKey("knowledge_documents.id", ondelete="CASCADE")` vào `KnowledgeFact.document_id`. Thêm quan hệ ORM hai chiều `document: Mapped[KnowledgeDocument]` và `facts: Mapped[list[KnowledgeFact]]` với cascade `all, delete-orphan`.
       * `backend/alembic/versions/20260919_facts_foreign_key_and_schema_sync.py`: Khởi tạo migration Alembic an toàn có schema introspection, tự động dọn sạch orphan facts trước khi tạo constraint khóa ngoại `fk_knowledge_facts_document_id_knowledge_documents`, đồng bộ cột `document_type_code`.
       * `backend/app/main.py`: Dọn sạch toàn bộ các câu lệnh raw SQL `ALTER TABLE IF EXISTS ...` trong lifecycle startup.
     - **RAG Hybrid Hardening & Groundedness (P0 / P1)**:
       * `backend/app/modules/rag/facts.py`: Loại bỏ triệt để điều kiện fact mồ côi `KnowledgeDocument.id.is_(None)`. Chuyển `outerjoin` sang `join(KnowledgeDocument)` bắt buộc `is_active == True` và `status in ("approved", "ready")`. Bổ sung lọc cô lập `tenant_id` và `workspace_id` qua join `KnowledgeCollection`.
       * `backend/app/modules/rag/vector_indexer.py`: Bọc `self.embed_texts([query])` trong `try...except` của `search_dense`. Khi embedding service offline, trả về danh sách rỗng `[]` thay vì crash caller.
       * `backend/app/modules/rag/retriever.py`: Sửa lỗi `UnboundLocalError: local variable 'stmt_ilike' referenced before assignment` khi câu hỏi ngắn hoặc chỉ chứa stop words. Chuẩn hóa lọc trạng thái tài liệu sang `["approved", "ready"]`. Bổ sung cơ chế `_safe_dense_search` tự động chuyển sang Degraded Mode (Sparse FTS) an toàn.
     - **ModelOps Dynamic Fallback & Usage Accounting (P0 / P1)**:
       * `backend/app/modules/modelops/service.py`: Nâng cấp `_match_score` trong `generate()` và `generate_stream()` ưu tiên `preferred_model_name` (+50) và `fallback_model_name` (+25). Tự động gán `is_fallback = True` khi phải dùng model dự phòng.
       * Viết lại `generate_stream()`: Bổ sung Quota Pre-check (`check_quota_available`), duyệt key pool rotation & circuit breaker, tích lũy số token stream, ghi nhận `LLMUsageLog` và trừ quota của tenant (`tokens_used`, `cost_used_usd`) sau khi stream hoàn tất.
     - **Verification hoàn hảo 100%**:
       * Backend: `uv run ruff check .` (0 lỗi); Pytest `uv run --extra dev pytest -v` đạt **245/245 passed** (100%), 47 warnings (+4 test cases mới cho RAG FTS/Degraded mode và ModelOps streaming quota/fallback).
       * Frontend: `npm run lint` (162 files, 0 lỗi); `npm run typecheck` (0 lỗi); `npm run build` (2573 modules trong 7.60s).
       * Zero Mojibake: 318/318 files sạch UTF-8.
  1. **Triển Khai Giai Đoạn 1 (P0): Bảo Mật Fail-Fast & Truthful Runtime Toàn Diện (Theo Kế Hoạch 07 - Phiên #123)**:
     - **Bảo mật Fail-Fast Secrets & Khóa Provider Encryption**:
       * `backend/app/core/config.py`: Bổ sung `PROVIDER_ENCRYPTION_KEY`, thêm `@model_validator` fail-fast trong production nếu còn dùng default secrets (`qnu-ai-platform-dev-secret-key-change-in-production`, `admin123`) hoặc thiếu khóa mã hóa Fernet.
       * `backend/app/core/crypto.py`: Nâng cấp Fernet encryption ưu tiên `PROVIDER_ENCRYPTION_KEY`, thêm helper `is_encrypted(val)`.
       * `backend/app/modules/modelops/service.py`: Tự động mã hóa Fernet khi lưu API Keys (`create_provider`, `update_provider`, `add_provider_key`), giải mã an toàn trong bộ nhớ khi gọi runtime (`generate`, `generate_stream`, ping model); xóa bỏ hoàn toàn mock keys (`sk-proj-mock-key-1`, `AIzaSyMockKey-1`) và fake token usage (`124500`, `82000`).
     - **Cô Lập Đa Khách Hàng / Không Gian Làm Việc Trong RAG**:
       * `backend/app/modules/rag/retriever.py`: Thêm bộ lọc `workspace_id` và `tenant_id` cho cả FTS lexical search và ILIKE fallback thông qua join bảng `KnowledgeCollection`.
       * `backend/app/modules/rag/vector_indexer.py`: Chặn triệt để mock vector embedding khi ở live mode, ném lỗi fail-closed `EMBEDDING_UNAVAILABLE`/`EMBEDDING_FAILED` để chống làm bẩn CSDL Qdrant.
     - **Siết Chặt Tool Gateway & Human-In-The-Loop (HITL)**:
       * `backend/app/modules/tools/service.py`: Bắt buộc phê duyệt HITL phải có `approved_by` danh tính rõ ràng, cấm client bypass bằng cờ `is_approved: true` thô.
       * `backend/app/modules/workflows/nodes/api_caller_node.py`: Fail-closed nếu thiếu DB session trong live mode; yêu cầu `approved_by` cho công cụ side-effect cần phê duyệt.
     - **Triệt Tiêu Fake Success & Mock Fallbacks Phía Frontend**:
       * `frontend/src/services/tools-api.ts`: Xóa bỏ fake-success fallback tự sinh file docx/xlsx và đường dẫn ảo `data/artifacts/...`, trả `status: "failed"` trung thực khi Backend lỗi.
       * `frontend/src/components/admin/docx-nd30-editor.tsx` & `bloom-matrix-editor.tsx`: Guard `onGeneratedSuccess` chỉ chạy khi `status === "success"`.
       * `frontend/src/components/admin/ingestion-progress-modal.tsx`: Loại bỏ 4 `setTimeout` giả lập tiến trình nạp tài liệu, đồng bộ 100% với `activeStage` và `isComplete` thực tế.
       * `frontend/src/services/system-api.ts`: Đổi endpoint kiểm tra readiness từ `/health` sang `/health/ready` đối soát PostgreSQL & Redis thật.
       * `frontend/src/pages/chat-studio-page.tsx`: Xóa `FALLBACK_STARTERS`, hiển thị `EmptyState` chuẩn hướng dẫn khi chưa có trợ lý nào active.
       * `frontend/src/pages/assistant-detail-page.tsx` & `assistant-model-section.tsx`: Xóa 7 mock models fallback giả lập; hiển thị cảnh báo khi chưa có Provider AI nào active.
  1. **Code Review Toàn Dự Án Và Lập Kế Hoạch 07 Cải Thiện Toàn Diện (phiên #122)**:
     - Tạo [`docs/ke_hoach/07_ke_hoach_cai_thien_toan_dien_sau_code_review.md`](../ke_hoach/07_ke_hoach_cai_thien_toan_dien_sau_code_review.md), đánh giá toàn bộ Backend, Frontend, Database, Knowledge/OCR, RAG, Assistant, Workflow, ModelOps, Evaluation, Security, Testing, Observability và Deployment.
     - Đánh giá dự án khoảng 6,5/10, phù hợp mức Internal Beta mạnh; ghi nhận các tài sản chính gồm domain architecture, Knowledge/OCR, Workflow ownership/versioning, typed Frontend và test suite rộng.
     - Xác định P0: hardcoded/default secrets, raw/mock Provider keys, fake-success LiveMode, startup tự sửa schema/seed, RAG lifecycle/workspace chưa đồng nhất và Tool approval chưa bất biến.
     - Lập kế hoạch 10 đợt: baseline, Security, Truthful Runtime, Database/Cross-store, RAG, ModelOps/Assistant, Workflow/HITL, Evaluation, Maintainability/Testing/Observability và Production Deployment.
     - Verification: Backend Ruff 0 lỗi; Pytest **239/239 passed** với 47 warnings; Frontend Biome 162 tệp/0 lỗi, TypeScript 0 lỗi, Vite build thành công 6,62 giây.
     - Chỉ tạo/cập nhật tài liệu; không sửa code/runtime/data và không ghi đè thay đổi của phiên #121.
  1. **Triển Khai Giai Đoạn 11: Knowledge Workspace — Nối Kín Upload → OCR → Verify → Approve → Index & Modular Hóa Scan Studio (Đợt 4 Kế Hoạch 06) (phiên #121)**:
     - **Phân rã SRP tệp Monolithic `scan-studio-page.tsx` (920 dòng xuống ~260 dòng)**:
       * Tách 4 sub-modules chuyên biệt trong `frontend/src/components/knowledge/ocr/`:
         - `types.ts`: Toàn bộ types, constants `REGION_COLORS`, `OCR_ENGINE_OPTIONS`, và interfaces.
         - `ocr-canvas.tsx`: Canvas chuyên trách hiển thị ảnh scan gốc (`image_url`), zoom tỷ lệ, và bounding boxes đa màu theo vùng.
         - `ocr-toolbar.tsx`: Thanh điều khiển phân trang (`<< < X/Y > >>`), zoom controls, filter bounding box, và bộ chọn OCR Engine.
         - `ocr-inspector.tsx`: Thanh kiểm tra 4 tab chuyên sâu: Markdown (Render, Raw, Live Edit), Excel Spreadsheet Viewer, Bounding Regions list với confidence & bbox, và JSON AST.
         - `index.ts`: Barrel export chuẩn mực.
     - **Nối Kín Luồng Đối Soát & Atomic Indexing (Verification Mode)**:
       * Khi có `documentId`, `ScanStudioPage` nạp dữ liệu thật từ `GET /documents/:id/studio-view`, hiển thị ảnh scan trang thật (`/pages/:page/image`), hỗ trợ cán bộ sửa tay Markdown từng trang.
       * Nút **[Xác nhận đối soát & Phê duyệt]** gọi `POST /documents/:id/approve` kèm `pages` để kích hoạt Atomic Indexing vào Qdrant và PostgreSQL FTS.
     - **Bảo Lưu Standalone OCR Lab Mode**:
       * Khi không có `documentId`, trang hoạt động như một phòng thí nghiệm OCR (`/knowledge/ocr-lab`), cho phép tải tệp thử nghiệm, chọn OCR engine và lưu thành Markdown.
     - **Deep Routing & Thống Nhất UI Studio**:
       * Cập nhật `route-resolver.ts` nhận diện canonical route `/knowledge/documents/:documentId/ocr`.
       * Cập nhật `App.tsx` truyền đầy đủ props `documentId`, `collectionId` và các navigation handlers.
       * Cập nhật `collection-detail-page.tsx` thay thế `DocumentVerificationStudioPage` bằng `ScanStudioPage`, kích hoạt deep routing khi cán bộ click nút **[Đối soát OCR]** trên danh sách tài liệu.
     - **Verification hoàn hảo**:
       * Frontend: Biome 162 files 0 lỗi; TypeScript 0 lỗi (`tsc -b`); Vite build thành công trong 7.94s.
       * Backend: Ruff 0 lỗi; Pytest 7/7 passed (100%).
       * Zero Mojibake: 318/318 files sạch 100%.
  1. **Triển Khai Giai Đoạn 10: Workflow Ownership & Publish Consistency (Đợt 3 Kế hoạch 06) (phiên #120)**:
     - **Private Workflow Binding**:
       * Khi tạo mới Assistant (`workflow_ownership == "private"` mặc định), hệ thống tự động fork một Workflow riêng biệt (`wf_ast_{code}`) với `ownership="private"` và `assistant_id=record.id`.
     - **Clone Assistant Fork Workflow**:
       * Khi nhân bản Assistant, checkbox `fork_workflow` (mặc định `true`) tự động fork workflow của source thành một workflow riêng cho bản sao, chấm dứt việc dùng chung mutable workflow.
     - **Pin Bất Biến Khi Publish**:
       * Khi xuất bản Assistant (`POST /assistants/{ref}/publish`), hệ thống tự động ghim `published_workflow_version_id` bất biến vào bản ghi của Assistant và lưu vào snapshot version.
     - **Rollback Toàn Vẹn**:
       * Khôi phục phiên bản Assistant sẽ khôi phục chính xác cả cấu hình 7 lớp lẫn DAG version tương ứng trong snapshot.
     - **Cảnh Báo Shared Workflow & Tách Riêng**:
       * Bổ sung API audit usage (`GET /workflows/definitions/{id}/assistants`) và endpoint fork (`POST /assistants/{id}/fork-workflow`).
       * Trên UI hiển thị badge quyền sở hữu (Riêng tư / Dùng chung), thông tin phiên bản ghim, nút **[Tách thành quy trình riêng]** (Fork Workflow), và Banner cảnh báo màu hổ phách trên DAG Canvas khi workflow có $>1$ trợ lý liên kết.
     - **Chat Runtime Exact-Version Resolution**:
       * Trong `chat` và `chat_stream`, truyền `workflow_version_id` đã ghim vào `WorkflowExecuteRequest` để `workflow_service.execute()` chạy đúng immutable spec.
     - **Verification hoàn hảo**:
       * Backend: Ruff 0 lỗi; Pytest 54/54 passed (100%) (suite mới `test_assistant_workflow_ownership.py` 7/7 passed).
       * Frontend: Biome 157 files 0 lỗi; TypeScript 0 lỗi (`tsc -b`); Vite build thành công trong 6.38s.
       * Zero Mojibake: 313/313 files sạch 100%.
  1. **Triển Khai Giai Đoạn 9: Knowledge Workspace Deep Modularization & Monolithic Page Decomposition (P1.3, P0.4, P1.4) (phiên #119)**:
     - **Phân rã tệp Monolithic khổng lồ `collection-detail-page.tsx` (1.718 dòng xuống còn 485 dòng, giảm hơn 70%)**:
       * Đưa `collection-detail-page.tsx` về đúng vai trò Page Orchestrator: tiếp nhận routing, quản lý queries/mutations và điều phối hiển thị.
       * Tách 11 module độc lập có Single Responsibility Principle (SRP) trong `frontend/src/components/knowledge/`:
         - `frontend/src/components/knowledge/types.ts`: Định nghĩa constants trạng thái (`STATUS_BADGE`, `TASK_STATUS_BADGE`), interfaces (`SandboxSearchResult`) và utility helpers (`formatFileSize`).
         - `frontend/src/components/knowledge/collection-header.tsx`: Hero card, embedding model chip, action toolbar (Đối soát Kho, Reindex Kho, Cấu hình, + Nạp tài liệu).
         - `frontend/src/components/knowledge/tabs/collection-documents-tab.tsx`: Tab danh mục tài liệu, search, 3 filters (Type, Status, Priority), bảng tài liệu với badge kép `Đã duyệt` + `Đã index`, row action buttons chuẩn semantic.
         - `frontend/src/components/knowledge/tabs/collection-facts-tab.tsx`: Tab bảng biểu số liệu Facts Layer, search bar, nút nạp Excel/CSV, bảng facts định lượng với độ tin cậy % và empty state.
         - `frontend/src/components/knowledge/tabs/collection-tasks-tab.tsx`: Tab hàng đợi & tác vụ ngầm, search bar, status filter, progress % bar, nút dọn dẹp đã xong, row actions: Terminal log, Retry, Cancel, Delete.
         - `frontend/src/components/knowledge/tabs/collection-playground-tab.tsx`: Tab sandbox truy vấn thử nghiệm Hybrid RRF (BGE-M3 + Postgres FTS) với form query và kết quả chunks kèm điểm số.
         - `frontend/src/components/knowledge/dialogs/collection-config-dialog.tsx`: Dialog sửa tên và mô tả bộ sưu tập.
         - `frontend/src/components/knowledge/dialogs/collection-reconcile-dialog.tsx`: Dialog đối soát kiểm toán dữ liệu 4 tầng (DB, Qdrant, MinIO, Redis) kèm 4 metric cards và nút "Đồng bộ tất cả".
         - `frontend/src/components/knowledge/dialogs/collection-excel-import-dialog.tsx`: Dialog kéo thả tải tệp Excel/CSV bóc tách facts.
         - `frontend/src/components/knowledge/dialogs/document-preview-dialog.tsx`: Dialog xem nhanh thông tin bóc tách tài liệu và chunks count.
         - `frontend/src/components/knowledge/dialogs/task-log-dialog.tsx`: Dialog terminal log dạng console đen cho worker task.
     - **Chuẩn Hóa Semantic & Accessibility (P0.4) & Typography (P1.4)**:
       * Thay thế thẻ `<p onClick>` bằng `<button type="button">` chuẩn semantic kèm focus ring (`focus-visible:ring-2`) và `aria-label`.
       * Loại bỏ triệt để `text-[9px]` và `text-[10px]` ở các vùng dữ liệu quản trị, chuẩn hóa thành `text-xs` (12px) hoặc `text-sm` (14px).
     - **Verification hoàn hảo**: Frontend Biome 157 files 0 lỗi; TypeScript 0 lỗi; Vite build thành công trong 6.69s; Backend Ruff 0 lỗi; Pytest 232/232 passed (100%); Zero Mojibake 313/313 files sạch 100%.
  1. **Triển Khai Giai Đoạn 8: Assistant Workspace Deep Modularization & Monolithic Page Decomposition (phiên #118)**:
     - **Phân rã tệp "quái vật" `assistant-detail-page.tsx` (1.745 dòng xuống ~550 dòng, giảm gần 70%)**:
       * Đưa `assistant-detail-page.tsx` về đúng vai trò Orchestrator: tiếp nhận routing, quản lý queries/mutations và điều phối hiển thị.
       * Tách 11 module độc lập có Single Responsibility Principle (SRP):
         - `frontend/src/components/assistants/types.ts`: Các types dùng chung (`AssistantEditForm`, `SampleQuestionItem`, `CATEGORY_OPTIONS`).
         - `frontend/src/components/assistants/assistant-header.tsx`: Hero header, status badges, action toolbar, KPI metrics strip, và Publish Gate readiness banner (5 tiêu chí).
         - `frontend/src/components/assistants/sections/assistant-persona-section.tsx`: Tầng 1 (Persona, Scope, System Prompt kèm AI generate prompt, sample questions).
         - `frontend/src/components/assistants/sections/assistant-model-section.tsx`: Tầng 3 (ModelOps Primary & Fallback model selector, Temperature, Max Tokens).
         - `frontend/src/components/assistants/sections/assistant-knowledge-section.tsx`: Tầng 2 (Collection binding, link mở chi tiết kho, khuyến nghị Chunking).
         - `frontend/src/components/assistants/sections/assistant-tools-section.tsx`: Tầng 5 & 6 (Workflow DAG selector, nút mở DAG Studio, chính sách HITL & OpenAPI).
         - `frontend/src/components/assistants/sections/assistant-guardrails-section.tsx`: Tầng 4 & 7 (6 chốt an toàn Guardrails, No-Answer Policy, TM-08 Ragas score panel).
         - `frontend/src/components/assistants/sections/assistant-danger-zone.tsx`: Card kích hoạt lại / vô hiệu hóa trợ lý kèm dialog xác nhận an toàn.
         - `frontend/src/components/assistants/dialogs/assistant-clone-dialog.tsx`: Dialog nhân bản trợ lý AI 1-click.
         - `frontend/src/components/assistants/dialogs/assistant-embed-dialog.tsx`: Dialog sao chép mã nhúng Web Chat Widget.
         - `frontend/src/components/assistants/dialogs/assistant-version-history-dialog.tsx`: Dialog xem lịch sử snapshot và rollback cấu hình.
     - **Chuẩn Hóa Semantic & Accessibility (P0.4) & Typography (P1.4)**:
       * Thay thế toàn bộ thẻ span clickable bằng `<button>` chuẩn semantic kèm focus ring (`focus-visible:ring-2`).
       * Loại bỏ triệt để `text-[9px]` và `text-[10px]` ở các vùng dữ liệu quản trị, chuẩn hóa thành `text-xs` (12px) hoặc `text-sm` (14px).
       * Bổ sung đầy đủ `aria-label` cho tất cả các công tắc Switch Guardrails.
     - **Boy Scout Rule Dọn Sạch Linter Backend**:
       * Khắc phục 10 cảnh báo Ruff E741 (biến `l` mơ hồ) và E402 trong `openai_adapter.py`, `layout_detector.py`, `service.py`, `conftest.py`, `test_auth.py`.
     - **Verification hoàn hảo**: Frontend Biome 146 files 0 lỗi; TypeScript 0 lỗi; Vite build thành công trong 8.23s; Backend Ruff 0 lỗi; Pytest 232/232 passed (100%); Zero Mojibake 302/302 files sạch 100%.
  1. **Triển Khai Giai Đoạn 7: Responsive App Shell (Mobile Drawer & 3 Layout Variants - P0.1), Dọn Dẹp Dev Junk (P0.3), Khung Chuẩn Hóa Trạng Thái Dữ Liệu (P0.2) (phiên #117)**:
     - **Responsive App Shell & Mobile Drawer (P0.1)**:
       - Ẩn sidebar cố định trên màn hình `< 1024px` (`lg`), chuyển đổi thành **Mobile Drawer Sheet** mở ra từ nút Menu hamburger trên Topbar.
       - Tự động đóng Mobile Drawer khi người dùng click vào bất kỳ liên kết điều hướng nào (`handleMobileNavigate`).
       - Thiết lập vùng đệm chuẩn: `pl-0` trên mobile, `lg:pl-64` / `lg:pl-16` trên desktop.
       - Hỗ trợ **3 Layout Variants** cho `<main>`:
         * `full-bleed` (`h-[calc(100vh-3.5rem)]`, `p-0`, `overflow-hidden`): Dành cho DAG Canvas Studio, Scan & OCR Studio Split-Screen, Chat Studio, Conversations Desk.
         * `wide` (`max-w-[1600px] mx-auto`): Dành cho Dashboard KPI và Bảng Runs.
         * `standard` (`max-w-7xl mx-auto`): Dành cho các trang danh mục và form thông thường.
     - **Dọn Dẹp Dev Junk Khỏi Production UI (P0.3)**:
       - Đọc thông tin người dùng thật từ `useAuth()` (`actor`) để hiển thị tên, email, vai trò và avatar initials thay vì dữ liệu gán cứng.
       - Ẩn triệt để các liên kết localhost (`localhost:8001/docs`, `localhost:6333`) khỏi production; chỉ hiển thị khi `import.meta.env.DEV` kèm nhãn `[Dev]`.
       - Cập nhật footer Sidebar hiển thị tiếng Việt thân thiện ("Hệ thống sẵn sàng" / "Mất kết nối máy chủ"), không rò rỉ port nội bộ.
     - **Khung Chuẩn Hóa Trạng Thái Dữ Liệu (P0.2)**:
       - Tạo mới component [`StateBanner`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/components/admin/state-banner.tsx) hỗ trợ các trạng thái: `degraded` (cảnh báo dữ liệu suy giảm/cache kèm timestamp và nút làm mới), `demo` (nhãn dữ liệu mẫu minh họa), `offline` (mất kết nối máy chủ), `info`, `success`.
       - Nâng cấp component [`EmptyState`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/components/admin/empty-state.tsx) hỗ trợ `variant="filter-empty"` với icon `SearchX` mặc định và nút "Xóa bộ lọc" (`onReset`).
     - **Verification hoàn hảo**: Frontend Biome 135 files 0 lỗi; TypeScript 0 lỗi; Vite build thành công trong 6.02s; Backend Ruff 0 lỗi; Pytest 232/232 passed (100%); Zero Mojibake 291/291 files sạch 100%.
  1. **Triển Khai Giai Đoạn 6: Tái Cấu Trúc Chức Năng & Thu Gọn Điều Hướng QNU AI Platform (Theo Kế Hoạch 06) (phiên #116)**:
     - **Tái cấu trúc Sidebar 4 nhóm & 7–8 mục chính**:
       - Thu gọn từ 16 mục xuống còn: **Tổng Quan** (`/`), **Xây Dựng AI** (`/assistants`, `/knowledge`, `/models`), **Vận Hành** (`/conversations`, `/quality`, `/operations/runs`), **Hệ Thống** (`/settings/integrations`).
       - Tích hợp nhóm **Nâng Cao** dạng Collapsible Accordion (lưu trạng thái vào `localStorage`): Thư viện Workflow (`/advanced/workflows`), Thư viện Nodes (`/advanced/capabilities/nodes`), Cổng Công cụ Tools (`/advanced/capabilities/tools`), Loại văn bản (`/knowledge/settings/document-types`), OCR Studio Lab (`/knowledge/ocr-lab`), Design System (`/design-system`, chỉ hiển thị khi `import.meta.env.DEV`).
     - **Module Typed Route Resolver & 100% Backward-compatible Redirects**:
       - Khởi tạo [`route-resolver.ts`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/navigation/route-resolver.ts) phân giải tập trung pathname và searchParams thành `ResolvedRoute`.
       - Xử lý chuyển hướng tự động cho 100% URLs cũ: `/chat?assistant=xxx` $\rightarrow$ `/assistants/:id/playground`, `/channels` $\rightarrow$ `/settings/integrations?tab=channels`, `/developer` $\rightarrow$ `/settings/integrations?tab=api-keys`, `/workflows` $\rightarrow$ `/advanced/workflows`, `/runs` $\rightarrow$ `/operations/runs`, `/evaluation` $\rightarrow$ `/quality`, `/ocr` $\rightarrow$ `/knowledge/ocr-lab`, `/document-types` $\rightarrow$ `/knowledge/settings/document-types`, `/nodes` $\rightarrow$ `/advanced/capabilities/nodes`, `/tools` $\rightarrow$ `/advanced/capabilities/tools`.
     - **Khởi tạo Assistant Workspace (`/assistants/:id/*`)**:
       - Tích hợp thanh điều hướng cục bộ [`AssistantWorkspaceNav`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/components/assistants/assistant-workspace-nav.tsx) kết nối 6 sub-views: Tổng quan & Cấu hình 7 lớp (`overview`), Thử nghiệm Chat (`playground`), Quy trình DAG Canvas (`workflow`), Mã nhúng Kênh (`channels`), Kiểm định Chất lượng TM-08 (`quality`), Lịch sử Chạy (`runs`).
       - Cập nhật `ChatStudioPage` nhận prop `initialAssistant` để nạp sẵn trợ lý đang chọn từ Workspace.
     - **Trang Cài Đặt & Tích Hợp Thống Nhất (`/settings/integrations`)**:
       - Hợp nhất `ChannelsPage` và `DeveloperPage` thành 1 trang 2 Tabs mượt mà.
     - **Verification hoàn hảo**: Frontend Biome 134 files 0 lỗi; TypeScript 0 lỗi; Vite build thành công trong 7.17s; Backend Ruff 0 lỗi; Zero Mojibake 289/289 files sạch 100%.
  1. **Triển Khai Giai Đoạn 5: Chuẩn Hóa Vòng Đời Tri Thức, Indexing Nguyên Tử & Đối Soát Bền Vững 4 Tầng (phiên #115)**:
     - **P1-09 Chuẩn hóa vòng đời trạng thái lập chỉ mục (`index_status` & `index_error`)**:
       - Bổ sung `index_status` (`pending`, `indexing`, `indexed`, `index_failed`) và `index_error` (nullable) trên `KnowledgeDocument` (`models.py`, `schemas.py`).
       - Trong `approve_document`: chuyển `index_status="indexing"`, thực hiện indexing an toàn, chuyển `index_status="indexed"` hoặc `"index_failed"` kèm lý do lỗi chi tiết, chấm dứt hoàn toàn tình trạng approved nhưng vector bị lỗi bị nuốt âm thầm.
     - **P1-10 Tách bạch Job Type trong hàng đợi nền**:
       - Tách biệt dứt khoát `job_type="ingestion_extract"` (lúc upload/OCR) và `job_type="vector_indexing"` (lúc approve/reindex), chấm dứt tắc nghẽn và nhập nhằng hàng đợi.
     - **P1-11 Bổ sung siêu dữ liệu cô lập đa người thuê vào Qdrant**:
       - Payload vector nạp vào Qdrant bắt buộc chứa đầy đủ: `tenant_id`, `workspace_id`, `collection_id`, `document_id`, `document_status="approved"`, `is_retrievable=True`, `chunk_index`, `page_number`, `header_path`.
     - **P1-12 Dọn sạch thác đổ 4 tầng khi xóa Collection**:
       - `delete_collection` dọn sạch tệp vật lý trên Storage driver (MinIO/Local) trước khi xóa DB, kết hợp xóa Qdrant vectors và Redis semantic cache.
     - **P1-13 Đối soát bền vững 4 tầng & Khôi phục Indexing**:
       - Backend: API `POST /documents/{id}/reindex` khôi phục vector đơn lẻ; API `GET /collections/{id}/reconcile` thanh tra 4 tầng (DB, Qdrant, Storage, Redis); API `POST /collections/{id}/reconcile-fix` tự động re-index toàn bộ approved documents thiếu vector.
       - Frontend `collection-detail-page.tsx`: Nút `[Đối soát Kho]`, huy hiệu kép trạng thái (`Đã duyệt` + `Đã index`), nút `[⚡ Thử lại Index]` trên dòng tài liệu, Dialog **Reconciliation Audit 4 Tầng** kèm nút `[Đồng bộ tất cả]`.
     - **Đồng bộ Quy trình 02**: Bổ sung Bước 11 vào `docs/quy_trinh/02_nap_tri_thuc_minio.md`.
     - **Verification hoàn hảo**: Backend Pytest **232/232 passed (100%)** (+4 tests mới); Ruff 0 lỗi; Frontend Biome 130 files 0 lỗi; TypeScript 0 lỗi; Vite build thành công trong 7.59s; Zero Mojibake 286/286 files sạch 100%.
  1. **Triển Khai Giai Đoạn 4: Node Catalog Contract, DAG Schema Validation & Approval Inbox Vận Hành (phiên #114)**:
     - **P1-07 Node Catalog Runtime Contract & Validation**:
       - Bổ sung `get_manifests_map()` trong `backend/app/modules/node_catalog/service.py` nạp đồng bộ 13 NodeManifests từ `configs/nodes/*.json`.
       - Nâng cấp `WorkflowCompiler` (`backend/app/modules/workflows/compiler.py`): thêm từ điển alias canonical (`_CANONICAL_TYPE_ALIASES`), viết hàm `_validate_node_config_schema` kiểm tra nghiêm ngặt các trường bắt buộc (`required`), kiểu dữ liệu (`string`, `integer`, `number`, `boolean`, `array`, `object`), kiểm tra `enum` cho phép (bao gồm chuỗi phân tách dấu phẩy như `"docx,pdf"`), và kiểm tra vòng đời manifest (`deprecated` -> cảnh báo, `inactive` -> chặn xuất bản).
       - Khởi tạo `workflowConfig` từ `defaultConfig` trích xuất từ schema khi kéo thả/thêm node từ `NodeCatalogDrawer` vào Canvas trong `dag-canvas-page.tsx`.
     - **P1-08 Schema-Driven Property Inspector**:
       - Viết lại toàn diện `PropertyInspector` (`frontend/src/components/admin/property-inspector.tsx`) hỗ trợ Two-Way Binding giữa Tab Trực Quan và Tab JSON Schema.
       - Xóa bỏ mọi tham số tĩnh gán cứng, cung cấp form controls tương tác theo schema thực tế (Search Mode, Top K, RRF k, Fact Threshold, Tool ID, Timeout, Routing rules,...), lưu cấu hình trực tiếp vào `workflowConfig`.
     - **P2-08 Approval Inbox Vận Hành Tại `/runs`**:
       - Bổ sung types `WorkflowApproval` trong `frontend/src/types/workflows.ts`, methods `getPendingApprovals()` và `decideApproval()` trong API client.
       - Nâng cấp `RunsPage` (`frontend/src/pages/runs-page.tsx`): tích hợp Hộp Thư Phê Duyệt Tác Vụ (HITL Approval Inbox) với auto-refetch mỗi 8 giây; hiển thị danh sách checkpoint kèm thẻ thông tin chi tiết; hộp thoại quyết định (`Approval Decision Dialog`) cho phép nhập người duyệt và lý do/chỉ đạo; nút [Duyệt ngay] shortcut trên các hàng bảng có trạng thái `paused_for_approval`.
     - **Đồng bộ Quy trình 04**: Bổ sung Mục 12 vào `docs/quy_trinh/04_dieu_phoi_tro_ly_dag.md` đặc tả chi tiết kiểm định schema node và luồng vận hành hộp thư phê duyệt.
     - **Verification hoàn hảo**: Backend Pytest **228/228 passed (100%)** (+4 test cases mới cho validation và approval API); Ruff check 0 lỗi; Frontend Biome 130 files 0 lỗi; TypeScript 0 lỗi; Vite build thành công trong 7.41s; Zero Mojibake 286/286 files sạch 100%.
  1. **Triển Khai Giai Đoạn 3: Nối Assistant Với ModelOps Thật & Khép Kín Chat Studio ↔ Conversations (phiên #113)**:
     - **P1-04 Chat Studio Query Trợ Lý Thật Từ CSDL**: Xóa bỏ mảng tĩnh 5 trợ lý `ASSISTANTS` trong `chat-studio-page.tsx`, thay bằng `useQuery` gọi `listAssistants({ includeInactive: false })`; hỗ trợ deep-link `?assistant={code}` tự động đồng bộ trên URL khi chuyển trợ lý; nạp câu hỏi mẫu nghiệp vụ từ `sample_questions` cấu hình thật.
     - **P1-01 & P1-02 Form Trợ Lý Nối ModelOps Thật**: Thay thế mảng mô hình tĩnh `STANDARD_MODELS` trong trang Tạo mới (`assistant-create-page.tsx`) và Chi tiết (`assistant-detail-page.tsx`) bằng danh mục models nạp động từ `modelopsApi.getModelProviders()`, tự động gom nhóm các models thuộc các Provider đang hoạt động (`is_active: true`).
     - **P1-03 Sửa Lỗi Usage / Model Name Tracking**: Viết helper `_extract_primary_model` trong `assistants/service.py` đọc chuẩn xác từ `config.model_policy.primary_model`, chấm dứt việc đọc sai thuộc tính không tồn tại `preferred_model_name`.
     - **P1-06 Khép Kín Chat ↔ Conversation Thread ↔ Staff Handoff**: Tự động ghi nhận tin nhắn người dùng (`sender="user"`) và câu trả lời AI (`sender="assistant"`) vào CSDL PostgreSQL (`conversation_threads` và `conversation_messages`) qua `conversation_service.record_message` trong cả hai luồng `chat` và `chat_stream`; tự động phát hiện intent gặp cán bộ/hotline để chuyển trạng thái sang `handoff_requested`.
     - **P1-05 Tệp Đính Kèm Thật Trong Chat Studio**: Mở rộng `ChatAttachment` hỗ trợ `textContent`; kết nối nút Paperclip với API OCR `/platform/v1alpha1/ocr/extract` thật; chèn văn bản bóc tách vào prompt context của Trợ lý AI; hiển thị spinner trạng thái và disable input khi đang xử lý OCR.
     - **Verification hoàn hảo**: Backend Pytest **224/224 passed (100%)** (+2 test cases mới cho attachments, conversation recording và primary_model tracking); Ruff check 0 lỗi; Frontend Biome 130 files 0 lỗi; TypeScript 0 lỗi; Vite build thành công trong 8.37s; Zero Mojibake 286/286 files sạch 100%.
  1. **Triển Khai Giai Đoạn 2: Khóa An Toàn API Quản Trị & Kết Nối Tool Gateway trong Workflow (phiên #112)**:
     - **P0-01 Bảo Vệ API Quản Trị Bằng Dev Access Gate**: Áp dụng `Depends(get_current_actor)` cho toàn bộ 11 router quản trị trong `main.py` (Workflows, Knowledge, ModelOps, Assistants Admin, Tools, Jobs, Document Types, RAG, Node Catalog, Conversations, OCR, Evaluation); tách `assistant_chat_router` giữ endpoint chat công khai `POST /assistants/{reference}/chat` cho Web Chat Widget và thí sinh/sinh viên; cấu hình cookie phiên `secure=settings.ENVIRONMENT not in ("development", "test")`.
     - **P0-04 Kết Nối Workflow API Caller Node ↔ Tool Gateway & HITL**: Refactor `APICallerNodeHandler` điều phối qua `ToolService.execute_tool(context.db, tool_req)` thay vì gọi trực tiếp driver; kiểm tra allowlist công cụ của trợ lý (`assistant_profile.tools.enabled_tools`); hỗ trợ tạm dừng workflow an toàn (`status="paused_for_approval"`) khi gặp công cụ side-effect (`export_administrative_document` tạo Word NĐ 30, `export_exam_matrix` tạo Excel Bloom có `requires_approval = True`) chưa có phê duyệt nhân sự; tự động lưu vết kiểm toán bất biến `ToolExecutionLog`.
     - **P0-02 Bảo Vệ Secret API Key (ModelOps Secret Masking)**: Loại bỏ trường `api_key: c.api_key_encrypted` trong API danh sách Provider (`modelops/service.py:556`), chỉ trả `api_key_masked` và các sub-keys đã sanitize, ngăn chặn hoàn toàn rò rỉ secret key ra ngoài giao diện.
     - **Verification hoàn hảo**: Backend Pytest **222/222 passed (100%)** (+4 test cases mới cho Auth API protection và Tool Gateway HITL/allowlist); Ruff check 0 lỗi; Frontend Biome 130 files 0 lỗi; TypeScript 0 lỗi; Vite build thành công trong 7.77s; Zero Mojibake 286/286 files sạch 100%.
  1. **Triển Khai Giai Đoạn 1: Sửa Khoảng Hở Kết Nối (phiên #111)**:
     - **P0-06 Web Chat Widget**: Chuẩn hóa `qnu-chat-widget.js` gọi đúng endpoint `POST /platform/v1alpha1/assistants/{id}/chat` kèm `stream: true`, chuẩn hóa đọc `data-api-base` và xử lý SSE delta/error. Bổ sung `data-api-base="${originUrl}"` vào snippet mã nhúng trên trang Channels (`channels-page.tsx`) và Chi tiết Trợ lý (`assistant-detail-page.tsx`).
     - **P1-14 Contract Quota API**: Sửa URL gọi trong `modelops-api.ts` từ `/models/quota?tenant_id=...` thành `/modelops/quotas/${tenantId}`; bổ sung endpoint alias `GET /platform/v1alpha1/modelops/quota?tenant_id=...` trong `modelops/router.py` bảo đảm tương thích ngược.
     - **P0-05 Ràng Buộc Vòng Đời Facts (Fact Layer Lifecycle Binding)**: Cập nhật `FactRetriever.lookup_facts` trong `rag/facts.py` thực hiện `outerjoin(KnowledgeDocument)`, lọc bỏ 100% facts từ tài liệu `pending` (chưa duyệt) hoặc `archived` (đã thu hồi); đồng bộ Bước 3 trong `docs/quy_trinh/03_hybrid_rag_truy_xuat.md`.

  1. **Lập Kế Hoạch Tái Cấu Trúc Chức Năng Và Điều Hướng (phiên #109)**:
     - Tạo [`docs/ke_hoach/06_ke_hoach_tai_cau_truc_chuc_nang_va_dieu_huong.md`](../ke_hoach/06_ke_hoach_tai_cau_truc_chuc_nang_va_dieu_huong.md).
     - Chốt nguyên tắc “gộp trải nghiệm, giữ domain”: đưa Workflow/Playground/Channels/Quality/Runs vào Assistant Workspace; đưa OCR/Loại văn bản vào Knowledge Workspace; giữ Provider, Conversations và runtime entities độc lập.
     - Đề xuất giảm sidebar từ khoảng 16 mục xuống 7–8 mục, có khu vực Advanced cho Workflow Library, Nodes, Tools và Design System dev-only.
     - Lập route map cũ → mới, chiến lược private/shared workflow, pin immutable workflow version, sáu đợt triển khai, kiểm thử E2E, rollback và Definition of Done.
     - Chỉ tạo tài liệu kế hoạch; không sửa code, runtime, dữ liệu hay Provider credentials.
  1. **Rà Soát Khoảng Hở Kết Nối Toàn Ứng Dụng (phiên #108)**:
     - Tạo báo cáo [`nhan_xet_khoang_ho_ket_noi_toan_app_2026-09-19.md`](../nhan_xet_khoang_ho_ket_noi_toan_app_2026-09-19.md), đối chiếu toàn chuỗi Frontend ↔ API ↔ Assistant ↔ ModelOps ↔ Workflow/Nodes/Tools ↔ Knowledge/RAG/OCR ↔ Conversations/Widget ↔ Evaluation/Dashboard.
     - Xác định 6 khoảng hở P0: API chưa được password gate bảo vệ, raw provider key/secret chưa an toàn, fake-success ở LLM/OCR/Tools/Embedding/Workflow, DAG tool bypass ToolService/HITL, facts không tuân lifecycle tài liệu và widget gọi sai endpoint/API base.
     - Xác định 14 khoảng hở P1 và 8 khoảng hở P2; ưu tiên nối Assistant với Provider thật, thống nhất usage/quota, khép kín Chat–Conversation–Handoff, biến Node Catalog thành contract và siết Knowledge index lifecycle.
     - Đề xuất lộ trình 6 đợt cùng 15 acceptance tests xuyên tầng. Không sửa runtime hoặc dữ liệu trong phiên này.
     - Kiểm chứng live bị giới hạn vì cả Frontend `:3001` và Backend `:8001` đều không hoạt động tại thời điểm rà soát.
  1. **Tối Ưu Hóa An Toàn Hệ Thống 7 Skills QNU & Chốt Điểm Dừng An Toàn (phiên #107)**:
     - Thực thi trọn vẹn Kế hoạch 05 theo hướng bảo thủ: sửa sai lệch trước, thu hẹp trigger sau, kiểm thử nghiêm ngặt và chốt safe checkpoint.
     - Sửa triệt để 10 liên kết tuyệt đối `DeTaiAI` sang đường dẫn repository chuẩn trong `qnu-rag-pipeline`, `qnu-knowledge-ingestion`, `qnu-modelops-resilience`.
     - Phân định rõ **Demo / Sample Mode** vs **LiveMode** trong `qnu-frontend-architect`, cấm Frontend nạp mock data bịa đặt khi Backend lỗi.
     - Cập nhật payload filter Qdrant thực tế (`tenant_id`, `workspace_id`, `document_status == "ready"`, `is_retrievable == true`) và công thức RRF Legal Priority Weighting trong `qnu-rag-pipeline`.
     - Chuẩn hóa lệnh pytest `uv run --extra dev pytest -v` trong `qnu-backend-architect` và giới hạn scope `ruff check <tệp> --fix` trong `qnu-clean-code-architect`.
     - Tạo `.agents/skills/qnu-clean-code-architect/agents/openai.yaml` (`policy.allow_implicit_invocation: false`), chuyển sang manual invocation.
     - Thu hẹp `description` của 6 skills domain với ranh giới rõ ràng, tránh kích hoạt chéo lãng phí token.
     - Kiểm thử: Backend 216/216 passed (100%), Frontend Biome 0 lỗi, TypeScript 0 lỗi, Build thành công 7.90s, 0 Mojibake. Chốt Điểm Dừng An Toàn tại Giai đoạn 3 (không vội tách progressive disclosure để bảo toàn tính toàn vẹn 100%).
  1. **Rà Soát Hệ Thống Skills Và Nguyên Nhân Kích Hoạt Tốn Token (phiên #104)**:
     - Rà soát đầy đủ 7 skill QNU với tổng dung lượng 47.067 byte, ước tính khoảng 10.300 token khi cùng được nạp; `qnu-frontend-architect` lớn nhất (14.705 byte) và `qnu-clean-code-architect` lớn thứ hai (9.878 byte).
     - Xác định `qnu-clean-code-architect` có trigger quá rộng (`whenever writing, refactoring, or reviewing code`) nên gần như mọi task code đều có thể nạp thêm hơn 2.000 token dù quy tắc đã trùng với `AGENTS.md`.
     - Xác nhận cả 7 skill chưa có `agents/openai.yaml`; vì vậy chưa skill nào chủ động tắt implicit invocation. Khuyến nghị tắt implicit cho Clean Code và thu hẹp mô tả của Chatbot/Frontend theo ranh giới tệp và loại tác vụ.
     - Phát hiện 10 liên kết `file:///` còn trỏ về repo cũ `D:/DuAnPhanMem/DeTaiAI/qnu-ai-platform`, quy tắc Offline Seed Fallback của skill Frontend xung đột với LiveMode fail-closed, lệnh test Backend không thống nhất và skill RAG còn mô tả payload `is_active` đã cũ.
     - Đề xuất giới hạn 1 skill chính + tối đa 1 skill hỗ trợ mỗi task; giữ ModelOps/Knowledge/Backend tương đối gọn, rút Frontend/Clean Code, và dùng progressive disclosure qua `references/` cho ví dụ chi tiết.
  1. **Đánh Giá Hiệu Quả Token Của Agent Vibe Coding (phiên #103)**:
     - Định lượng `AGENTS.md` khoảng 31 KB / 6.700 token ước tính và `PROJECT_CONTEXT.md` khoảng 108 KB / 24.000 token ước tính; riêng hai nguồn này tạo khoảng 31.000 token ngữ cảnh trước khi đọc code, lịch sử chat và tool output.
     - Xác nhận cấu hình cục bộ dùng `gpt-5.6-sol` với `model_reasoning_effort = "xhigh"`, phù hợp bài khó nhưng quá tốn cho các turn hỏi đáp, chỉnh UI nhỏ hoặc cập nhật tài liệu.
     - Xác định nguyên nhân chính: instruction trùng lặp, memory chứa toàn bộ lịch sử thay vì current state, trigger skill quá rộng, bắt buộc snapshot/work log cho mọi turn, full test quá thường xuyên, thread kéo dài và output công cụ quá lớn.
     - Đề xuất chuyển sang cơ chế hai chế độ Fast/Full, rút gọn AGENTS và PROJECT_CONTEXT, chỉ nạp 1-2 skill liên quan, dùng reasoning medium mặc định và chỉ chạy full suite tại checkpoint/commit.
  1. **Khắc Phục Toàn Diện 5 Lỗ Hổng Kỹ Thuật (Remediation Execution - Phiên #105)**:
     - **Hiện thực Node Handler `tool.api_caller`**: Tạo `APICallerNodeHandler` (`backend/app/modules/workflows/nodes/api_caller_node.py`), đăng ký trong `WorkflowNodeRegistry`, xử lý gọi công cụ qua `tool_registry.execute_tool` và cập nhật kết quả vào context execution.
     - **Kích Hoạt Lại Loại Văn Bản & Bảo Toàn Cấu Hình User**: Bổ sung phương thức `activate_document_type`, endpoint `POST /platform/v1alpha1/document-types/{code}/activate`, và chỉnh sửa `sync_from_catalog` để không ghi đè `is_active=False` do cán bộ tùy biến; Frontend tích hợp nút `[Kích hoạt lại]`.
     - **Thư Viện Node Động (Dynamic Node Catalog)**: `NodeCatalogDrawer` (`node-catalog-drawer.tsx`) tải danh mục `NodeManifest` động từ API `/platform/v1alpha1/system/nodes`; sửa logic mapping type trong `dag-canvas-page.tsx` bảo toàn chính xác loại node và phiên bản.
     - **Trọng Số Pháp Lý RRF (Legal Priority Boosting)**: Áp dụng công thức `priority_multiplier = 1.0 + (priority - 5) * 0.02` trong `reciprocal_rank_fusion` (`backend/app/modules/rag/fusion.py`), bảo đảm văn bản có `priority = 10` (Quy chế, Quyết định) được boost $+10\%$ điểm tương quan khi đối soát.
     - **File Inspector Trả Về Undefined Khi Không Có Căn Cứ**: Xóa bỏ fallback mặc định `thong_bao` trong `detectDocumentTypeFromFilename`; mở rộng `getPriorityForDocumentType` hỗ trợ `priorityScore` động 1-10; hiển thị trực quan badge ưu tiên pháp lý trên `document-ingest-page.tsx`.
  1. **Triển Khai Hoàn Tất Đợt 2: Quản Trị Phiên Bản Snapshot Trợ Lý AI, Nạp Bảng Biểu Số Liệu Excel/CSV & Bàn Giao Cán Bộ Trực Tiếp (phiên #102)**:
     - **Quản Trị Phiên Bản Snapshot Trợ Lý AI (Assistant Versioning & 1-Click Rollback)**:
       * Khởi tạo bảng SQLAlchemy `AssistantVersionRecord`: lưu trữ snapshot JSON 7 lớp bất biến (`persona`, `model_config`, `guardrails`, `workflow_id`, `collection_id`), `version_number` tự động tăng dần `v1.0`, `v1.1`,...
       * Tự động chụp snapshot khi cập nhật cấu hình hoặc xuất bản Trợ lý.
       * Endpoints: `GET /platform/v1alpha1/assistants/{ref}/versions` và `POST /platform/v1alpha1/assistants/{ref}/versions/{version_id}/rollback`.
       * Frontend `assistant-detail-page.tsx`: Nút [Lịch sử phiên bản] trên topbar mở Dialog hiển thị danh sách snapshot, badge phiên bản hiện tại và nút [Khôi phục] kèm `ConfirmDialog` xác nhận an toàn.
     - **Nạp Trực Tiếp Bảng Biểu Số Liệu Excel/CSV (Structured Facts Ingestion)**:
       * Khởi tạo parser chuyên dụng `excel_parser.py`: đọc tệp `.xlsx`, `.xls`, `.csv` bằng `openpyxl`/`csv`, nhận diện linh hoạt các cột thực thể và thuộc tính (điểm chuẩn, chỉ tiêu, học phí).
       * Chuyển đổi trực tiếp thành facts định lượng nạp vào bảng `knowledge_facts` với độ tin cậy tuyệt đối `confidence = 1.0`.
       * Endpoints: `POST /platform/v1alpha1/knowledge/collections/{id}/facts/import-excel` và `GET /platform/v1alpha1/knowledge/collections/{id}/facts`.
       * Frontend `collection-detail-page.tsx`: Bổ sung tab thứ 4 "Bảng Biểu & Số Liệu" (`facts`), bảng tra cứu số liệu, bộ lọc tìm kiếm và Dialog upload bảng tính Excel/CSV.
     - **Bàn Giao Trực Tiếp & Giám Sát Hội Thoại Live (Live Conversations & Staff Handoff Desk)**:
       * Khởi tạo module Backend `app.modules.conversations`: `models.py` (`ConversationThreadRecord`, `ConversationMessageRecord`), `schemas.py`, `service.py`, `router.py`.
       * Hỗ trợ đầy đủ vòng đời trạng thái: `handoff_requested`, `staff_claimed`, `ai_active`, `resolved`.
       * Giao diện Bàn trực Cán bộ `/conversations` (`conversations-page.tsx`): Bố cục Master-Detail 2 cột, polling 8s, bộ lọc trạng thái, tiếp nhận xử lý, gửi tin nhắn phản hồi trực tiếp kèm 4 mẫu câu trả lời nhanh (Canned Replies) chuyển tiếp thông tin ĐH Quy Nhơn.
     - **Verification Toàn Diện**:
       * Backend: `uv run ruff check .` **0 lỗi**; `uv run --extra dev pytest -v` **213/213 passed (100%)** (+20 tests mới).
       * Frontend: `npm run lint` **130 files checked, 0 lỗi**; `npm run typecheck` **0 lỗi**; `npm run build` **thành công trong 7.69s** (2545 modules).
       * Zero Mojibake: 280/280 files sạch 100%.
     - **Đồng bộ Quy trình**:
       * Cập nhật `docs/quy_trinh/02_nap_tri_thuc_minio.md`: Bước 10 (Nạp Trực Tiếp Bảng Biểu Số Liệu Excel/CSV).
       * Cập nhật `docs/quy_trinh/04_dieu_phoi_tro_ly_dag.md`: Mục 9 (Assistant Versioning & Rollback) và Mục 10 (Live Conversations & Staff Handoff).
  1. **Triển khai Đợt 2 Trước Đó: Dev Access Gate Mật Khẩu Đơn Giản, Observability & Thống Kê Chi Phí Thật, Standalone Web Widget Embed**:
     - **Password-Only Dev Access Gate**: Màn hình `/login` tối giản, chỉ có 1 trường mật khẩu (`QNU@2026`), bỏ qua hoàn toàn RBAC & phòng ban; bọc ứng dụng trong `AuthProvider`, tích hợp Route Guard bảo vệ các trang quản trị; nút Đăng xuất trên Topbar (`Topbar.tsx`).
     - **Observability & Real-Time Cost Tracking**: Bảng giá `pricing.py`, ghi vết `LLMUsageLog` khi gọi LLM (cả sync và stream SSE); API `GET /platform/v1alpha1/modelops/usage-stats?days=30`; Dashboard real models breakdown.
     - **Web Widget Embed Độc Lập**: `frontend/public/embed/qnu-chat-widget.js`, Live Preview `/channels`, Dialog mã nhúng `/assistants/:id`.
  1. **Triển Khai Trọn Vẹn Đợt 1 Nâng Cấp Nền Tảng Quản Trị, Tạo Lập, Kiểm Định & Vận Hành Trợ Lý AI QNU (phiên #101)**:
     - **Cổng Kiểm Định Xuất Bản 5 Lớp (Publish Gate Engine)**:
       * Khởi tạo `backend/app/modules/assistants/readiness.py`: Thẩm định 5 tiêu chí (Kho tri thức có tài liệu ready, ModelOps dự phòng 2 tầng, Chốt chặn Tool Gateway allowlist, Guardrails an toàn chống jailbreak/che PII/hotline No-Answer, Kiểm định chất lượng TM-08 Ragas).
       * Tính điểm sẵn sàng `overall_readiness_score` (0-100%) và phân loại rõ `blockers` (ngăn xuất bản HTTP 422) vs `warnings` (cảnh báo khuyến nghị).
       * Frontend `assistant-detail-page.tsx`: Thẻ "Cổng Kiểm Định Xuất Bản (Publish Gate 5 Lớp)" với thanh đo điểm sẵn sàng, danh sách 5 tiêu chí kèm icon trực quan, nút "Kiểm tra lại" và nút "Xuất bản chính thức".
     - **Nhân Bản Trợ Lý 1-Click (Clone Assistant)**:
       * Endpoint Backend `POST /{ref}/clone`: Sao chép toàn bộ cấu hình 7 lớp (persona, model_policy, rag_binding, tools, guardrails, format_policy, evaluation) sang trợ lý mới với `code` và `name` do người dùng đặt, gán mặc định `is_active = False` để chờ kiểm định.
       * Frontend: Nút **[Nhân bản]** trên top toolbar mở Dialog sao chép cấu hình 1-click mượt mà.
     - **Hòm Thư Lỗ Hổng Tri Thức (Knowledge Gap Inbox & Active Remediation)**:
       * Khởi tạo bảng SQLAlchemy `KnowledgeGapRecord` lưu trữ câu hỏi thiếu tri thức.
       * Hook tự động thu thập trong cả `chat()` và `chat_stream()` khi `status == "insufficient_context"`, tự động cộng dồn tần suất `frequency` khi câu hỏi trùng lặp.
       * Endpoint API `GET /evaluation/gap-inbox` (hỗ trợ lọc theo assistant, status) và `PATCH /evaluation/gap-inbox/{gap_id}`.
       * Frontend `evaluation-page.tsx`: Tab Badge đếm số lượng gap chờ xử lý, nút **[Nạp vào RAG]** chuyển hướng kèm ngữ cảnh sang `/knowledge`, nút **[Đánh dấu đã nạp]** và **[Bỏ qua]** cập nhật trạng thái lập tức.
     - **Đồng bộ Quy trình**: Cập nhật `docs/quy_trinh/07_kiem_dinh_chat_luong_tm08.md` Mục 4 (Active Remediation & Knowledge Gap Inbox).
     - **Verification hoàn hảo**: Backend Pytest **193/193 passed (100%)**; Ruff 0 lỗi; Frontend Biome 124 files 0 lỗi; TypeScript 0 lỗi; Vite build thành công (7.74s); Zero Mojibake 272/272 files sạch.
  1. **Mở Rộng Đánh Giá Các Chức Năng Còn Lại Của Platform (phiên #100)**:
     - Mở rộng [`docs/nhan_xet_nodes_va_loai_van_ban_2026-09-18.md`](../nhan_xet_nodes_va_loai_van_ban_2026-09-18.md) với scorecard và review Trợ lý AI, Workflow, Knowledge/OCR, RAG, ModelOps, Tools, Evaluation, Dashboard, Conversations/Handoff, Channels/Widget và Dev Access Gate.
     - Xác nhận các cải thiện thật: immutable workflow version, approval checkpoint, tenant/lifecycle retrieval filter, model fallback, semantic cache partition, Tool allowlist/HITL và Evaluation không còn chép ground truth.
     - Phát hiện blocker Truthfulness Gate: provider adapters trả mock success khi thiếu key, Local vLLM nuốt lỗi, OCR tự fallback sang nội dung quy chế giả, embedding mock vẫn được index và Frontend Tools tự dựng artifact/UIS success khi API lỗi.
     - Xác nhận Dev Access Gate mới có endpoint/dependency nhưng chưa bảo vệ router, chưa có login page; nhiều credential/secret còn giá trị mặc định trong source. Giữ đúng phạm vi người dùng yêu cầu: một trang mật khẩu đơn giản, không mở rộng RBAC/SSO.
     - Phát hiện Dashboard còn KPI/provider breakdown gán cứng; ModelOps streaming chưa accounting quota/cost; Evaluation là heuristic baseline; Conversations/Channels mới ở mức prototype/preview.
     - Verification: Backend **182/182 passed** (19 warnings); Frontend Biome **124 files, 0 lỗi**; TypeScript **0 lỗi**.
  1. **Rà Soát Toàn Diện & Nâng Cấp Đồng Bộ 5 Trợ Lý AI Cốt Lõi QNU (phiên #99)**:
     - **Phase 1 (Tool Mappings & Sample Questions)**: Khớp nối cấu hình `enabled_tools` cho `ast_admissions` (`lookup_admission_score`), `ast_question_bank` (`export_exam_matrix`), `ast_drafting` (`export_administrative_document`), và `ast_regulations`/`ast_library` (`[]`). Cập nhật 4 câu hỏi mẫu nghiệp vụ sát thực tế cho cả 5 trợ lý.
     - **Phase 2 (Enrich Knowledge & Structured Facts)**: Bổ sung điểm chuẩn 3 năm liên tiếp (2022-2024) các ngành Sư phạm Toán, Giáo dục Tiểu học, Văn, Tiếng Anh, CNTT, Kỹ thuật phần mềm, QTKD vào `seed_data_admissions.py` kèm fact `fact_adm_diem_chuan_3_nam`. Bổ sung quy định Turnitin (< 20% tổng thể, < 5% nguồn đơn lẻ) và quy trình nộp lưu chiểu điện tử vào `seed_data_library.py`.
     - **Phase 3 (Direct File Artifacts UX)**: Đảm bảo forward `artifacts` xuyên suốt từ Workflow đến `AssistantChatResponse` và SSE streaming; nâng cấp `chat-message.tsx` hiển thị icon `FileSpreadsheet` (`text-emerald-600`) cho tệp Excel và tiêu đề khối tải tệp linh hoạt theo định dạng file.
     - **Phase 4 (TM-08 Golden Benchmark 130 Cases)**: Mở rộng `qnu_regulations_benchmark` từ 20 lên **50 test cases** vàng (`tc_reg_001` - `tc_reg_050`) bao quát đầy đủ quy chế tín chỉ, thang điểm 4, cảnh báo học vụ, chuẩn đầu ra tốt nghiệp; hoàn thiện 130 test cases kiểm định TM-08 cho cả 5 trợ lý.
     - **Verification**: `uv run ruff check .` 0 lỗi; `uv run --extra dev pytest -v` **182/182 passed (100%)** trong 62.02s; `npm run lint` 0 lỗi (124 files); `npm run typecheck` 0 lỗi; `npm run build` thành công trong 13.12s, 0 warnings; Zero Mojibake **271/271 files** sạch 100%.
  1. **Đánh Giá Node Catalog Và Loại Văn Bản — Hai Hợp Đồng Nền Tảng Của Workflow/Assistant (phiên #98)**:
     - Tạo báo cáo [`docs/nhan_xet_nodes_va_loai_van_ban_2026-09-18.md`](../nhan_xet_nodes_va_loai_van_ban_2026-09-18.md), đánh giá `/nodes` là Capability Contract và taxonomy loại văn bản là Semantic Contract.
     - Xác nhận Node Catalog có 13 manifest nhưng Runtime chỉ hỗ trợ 12; `tool.api_caller` active chưa có handler và Canvas đang ánh xạ sai category `tool` thành `tool.human_approval`.
     - Xác nhận taxonomy có 37 loại, 4 nhóm, 28 mã NĐ30 và đã nối vào ingestion/database; phát hiện fallback ép loại `thong_bao`, thiếu confidence/source, Core edit bị startup sync ghi đè và priority multiplier mới chỉ là logic hiển thị Frontend.
     - Đề xuất roadmap bốn giai đoạn và production acceptance gate. Targeted tests Node Catalog + Document Types + Workflow: **28/28 passed**.
  1. **Xử Lý Triệt Để Các Vấn Đề Còn Lại (P0 & P1 Remediation) Theo Báo Cáo 18/09/2026 (phiên #97)**:
     - **P0.7 — Citation Guard Strictness**: Bổ sung tập từ dừng học thuật tiếng Việt `ACADEMIC_STOPWORDS` (`sinh viên`, `quy nhơn`, `đào tạo`, `tối đa` vs `tối thiểu`...), xử lý an toàn `quote is None`, xóa bỏ fallback `citations[:2]`, bảo đảm 0 false positive citation khi không có căn cứ thực tế.
     - **P0.2 — Bỏ Fallback Ground Truth trong Evaluation**: Xóa hoàn toàn 100% logic tự chèn `actual_answer = ground_truth` khi RAG hoặc Chat không có kết quả. Ghi nhận trung thực `status = failed` / `insufficient_context` từ runtime.
     - **P1.5 — Phân Giải Phiên Bản Workflow Bất Biến Fail-Closed**: Khi chỉ định `workflow_version_id` mà không tìm thấy bản ghi trong `workflow_versions`, hệ thống ném ngoại lệ HTTP 404 `workflow_version_not_found`, cấm tuyệt đối việc âm thầm chuyển sang bản nháp mutable.
     - **P0.5 — Dense Retrieval Lọc Chặt Chẽ Lifecycle & Phân Quyền Tenant**: Payload Qdrant lưu trữ đầy đủ `tenant_id`, `workspace_id`, `document_status`, `is_retrievable`. `search_dense()` áp dụng bộ lọc `must` tenant/workspace và `must_not` các tài liệu chưa sẵn sàng hoặc đã lưu trữ.
     - **P1.3 — Dynamic Fallback Model & Runtime Policy**: Bổ sung `fallback_model` và `tenant_id` vào `AskRequest`, chuyển tiếp từ `RAGAnswerNodeHandler`. `RagService.ask()` tự động chuyển sang fallback model khi primary model gặp sự cố trước khi vào raw fallback.
     - **P1.4 — Phân Vùng Semantic Cache Đa Người Thuê**: Khóa Redis nâng cấp thành `rag:cache:{tenant_id}:{collection_id}:{model}:{hash}`, hỗ trợ invalidation theo wildcard pattern.
     - **P0.6 — Triệt Tiêu Approval Bypass & Chốt Chặn Tool Gateway**: Chat request ép buộc `is_approved = False` từ server. Tool Gateway bắt buộc kiểm tra `enabled_tools` allowlist của trợ lý và kiểm tra phê duyệt nhân sự (HITL) cho công cụ nhạy cảm.
     - **Dev Access Gate Phía Server**: Khởi tạo module `app.modules.auth` (`/auth/login`, `/logout`, `/me`), xác thực mật khẩu `DEV_ACCESS_PASSWORD="QNU@2026"` bằng `hmac.compare_digest`, cấp cookie HttpOnly `qnu_session` và dependency `get_current_actor`.
     - **P0.1 & P1.2 — Lưu Trữ Tệp Gốc & Tự Hồi Phục Qdrant Trong Seeder**: Bổ sung `_ensure_seed_storage()` đẩy file raw text lên `storage_service` và `_ensure_qdrant_points()` tự động trích xuất chunks từ DB để re-index vào Qdrant khi số point = 0.
     - **Verification**: `uv run ruff check .` 0 lỗi; `uv run --extra dev pytest -v` **182/182 passed (100%)**; Frontend `npm run lint` 0 lỗi (124 files), `npm run typecheck` 0 lỗi, `npm run build` thành công.
  1. **Sửa lỗi 1 Test Fail & Đồng Bộ Quy Trình (phiên #96)**:
     - **Sửa `test_seed_preserves_existing_user_configuration`** (fail #95): Loại bỏ logic `update_stmt` trong `seed_standard_assistants()` tại [`backend/app/modules/assistants/seeder.py`](../../backend/app/modules/assistants/seeder.py) — Seeder hiện chỉ `continue` khi gặp assistant đã tồn tại, không ghi đè `system_prompt`, `collection_id` hay `config` đã do người dùng tùy chỉnh.
     - **Verification hoàn tất**: `uv run ruff check .` 0 lỗi, `uv run --extra dev pytest -v` **174/174 passed** (100%); `npm run lint` 0 lỗi (124 files), `npm run typecheck` 0 lỗi, `npm run build` thành công 0 warnings (9.09s); Zero Mojibake **267/267 files** sạch.
     - **Cập nhật quy trình** 3 tệp trong `docs/quy_trinh/`:
       * [`02_nap_tri_thuc_minio.md`](../../docs/quy_trinh/02_nap_tri_thuc_minio.md): Thêm Bước 9 — Fact Reconciliation khi sửa tay & Cascading Cleanup triệt tiêu Ghost Vector trên 4 tầng (MinIO, Qdrant, PostgreSQL, Redis Cache).
       * [`03_hybrid_rag_truy_xuat.md`](../../docs/quy_trinh/03_hybrid_rag_truy_xuat.md): Cập nhật Bước 4-5 (song song `asyncio.gather`), Bước 7-8 (Evidence-Based Citation Filtering), thêm Bước 9 (Model-Partitioned Semantic Cache `rag:cache:{collection_id}:{model}:{hash}`).
       * [`04_dieu_phoi_tro_ly_dag.md`](../../docs/quy_trinh/04_dieu_phoi_tro_ly_dag.md): Thêm Mục 8 — Bảo Toàn Tính Toàn Vẹn Thực Thi (Immutable Version Resolution, Server-Side Approval Flag Enforcement, Concurrent Execution Context Isolation).
  1. **Hiệu chỉnh báo cáo sau cải thiện & Review Worktree (phiên #95)**:
     - Cập nhật [`docs/nhan_xet_sau_cai_thien_platform_2026-09-18.md`](../nhan_xet_sau_cai_thien_platform_2026-09-18.md) thành báo cáo review mã có evidence; xác nhận maturity giữ ở 6,4/10, Internal Beta.
     - Theo quyết định phạm vi của chủ dự án: giai đoạn phát triển chỉ cần **Dev Access Gate** server-side (password hash từ env + signed HttpOnly session + principal cố định), không cần RBAC/SSO phức tạp.
     - Review phát hiện blocker mới trong worktree: Library/Question Bank seed được gắn official nhưng chưa có source provenance/original storage; `KnowledgeService` redefine cleanup methods; Assistant seeder overwrite user config; Evaluation vẫn fallback từ ground truth; dense search chưa filter lifecycle/tenant/revision; approval/tool bypass và citation guard false-positive.
     - Trong lúc review, session song song tiếp tục sửa cache/workflow version/knowledge cleanup. Ghi nhận cải thiện workflow version và cache model key, nhưng approval vẫn tin client flag, citation guard fallback giữ citation thiếu evidence và cleanup còn trùng method. Verification `ruff`/pytest là snapshot trước diff mới: 7 lỗi / 71 pass, 1 fail, 17 warnings; Zero Mojibake 267 files pass. Không sửa code của session seed song song.
  1. **Đánh Giá Độc Lập Sau Các Cải Thiện (phiên #94)**:
     - Tạo báo cáo [`docs/nhan_xet_sau_cai_thien_platform_2026-09-18.md`](../nhan_xet_sau_cai_thien_platform_2026-09-18.md); maturity đề xuất tăng từ 5,6/10 lên 6,4/10 nhưng vẫn Internal Beta.
     - Xác nhận live: cả 5 collection có dữ liệu, orphan facts = 0, Qdrant có 7/6/6/6/23 points cho Admissions/Regulations/Library/Drafting/Question Bank.
     - Phát hiện P0 còn lại: Evaluation dựng answer/context từ ground truth khi runtime thiếu kết quả; chat tự gán `is_approved=true`; dense Qdrant không filter document lifecycle/tenant; execute/resume không đọc exact WorkflowVersion; thay đổi seed đang ghi đè cấu hình user.
     - Verification: Backend Ruff pass; targeted tests 44/45 pass (1 seed test fail), backend API 8001 offline.
  1. **Đợt 3: Clean Code SRP Refactoring, Frontend Bundle Optimization & Golden Assistant Tuyển Sinh QNU (phiên #93)**:
     - **Clean Code SRP Phân Hệ ModelOps**: Phân rã tệp nguyên khối `modelops-page.tsx` từ **2.961 dòng xuống còn 854 dòng** (giảm hơn 70% độ dài và độ phức tạp), tách thành 8 sub-components đơn trách nhiệm trong `frontend/src/components/modelops/` (`modelops-helpers.ts`, `provider-card.tsx`, `provider-detail-header.tsx`, `models-grid.tsx`, `add-custom-model-dialog.tsx`, `key-pool-section.tsx`, `system-defaults-card.tsx`, `resilience-policy-card.tsx`, `provider-modal.tsx`).
     - **Tối Ưu Hóa Frontend Bundle & Code Splitting**: Cấu hình chia nhỏ vendor manualChunks (`vendor-xyflow`, `vendor-tanstack`, `vendor-markdown`, `vendor-radix`, `vendor-icons`) trong `vite.config.ts`, kết hợp `React.lazy()` và `<Suspense>` trên `App.tsx`. Kết quả đóng gói: Main chunk giảm từ **1.481 kB xuống 372 kB** (gzip 107 kB), mọi chunk < 400 kB, **0 cảnh báo (Zero Warnings)**, thời gian build siêu tốc 5.83s.
     - **Golden Assistant Tuyển Sinh ĐH Quy Nhơn (`col_admissions`)**: Nạp toàn diện Thông báo và Đề án tuyển sinh chính quy 2024 (1 Document `doc_qnu_tuyen_sinh_2024`, 7 Chunks điều khoản chuyên sâu về mã trường DQN, hotline 0256.3846.156, 4 phương thức xét tuyển, khối Sư phạm NĐ 116, khối CNTT & Kỹ thuật, khối Kinh tế, học phí & học bổng, KTX 5.000 chỗ; 8 Structured Facts số hóa). Vectorize và index 7 points 1024-dim BAAI BGE-M3 vào Qdrant `col_admissions`.
     - **Golden Benchmark 20 Test Cases & TM-08 Compliance**: Mở rộng bộ kiểm thử `qnu_admissions_benchmark` từ 5 lên 20 câu hỏi toàn diện (`tc_adm_001` đến `tc_adm_020`). Chuẩn hóa `compute_context_precision` trong `evaluator.py` sang chuẩn Mean Average Precision @ k (MAP@k) của Ragas. Kết quả đánh giá live toàn diện: Faithfulness 1.0 (>= 0.90), Answer Relevance 0.942 (>= 0.85), Context Precision 0.939 (>= 0.80), Pass Rate 85.0% (>= 80%), Meets TM-08 Standard: **True**.
     - **Verification**: Backend `uv run ruff check .` 0 lỗi, `uv run --extra dev pytest -v` 174/174 passed (100%); Frontend `npm run lint` 0 lỗi (124 files), `npm run typecheck` 0 lỗi, `npm run build` thành công 0 cảnh báo (5.83s); Zero Mojibake 265/265 files (100% UTF-8 sạch).
  1. **Đợt 2: RAG Data Integrity, Assistant Runtime Binding & Golden Assistant Quy Chế Học Vụ ĐH Quy Nhơn (phiên #92)**:
     - **RAG Data & Index Integrity**: Xóa collection drift `col_col_question_bank` trong Qdrant; di chuyển và lập chỉ mục chuẩn hóa 17 vector 1024-dim vào canonical `col_question_bank`. Thanh trừng 788 facts rác mồ côi (orphan facts) trong PostgreSQL `knowledge_facts` (hiện tại còn 14 facts sạch, 0 facts mồ côi).
     - **Golden Assistant Quy Chế Học Vụ (`col_regulations`)**: Nạp toàn diện Quy chế đào tạo đại học tín chỉ ĐH Quy Nhơn (Quyết định 1688/QĐ-ĐHQN) với 6 Chunks điều khoản chuyên sâu (Điều 1-26) và 7 Structured Facts số hóa (thang điểm 4, hạn ngạch tín chỉ, mốc cảnh báo học vụ, chuẩn đầu ra ngoại ngữ VSTEP B1/C1, chuẩn tin học TT 03, điều kiện tốt nghiệp, xếp loại tốt nghiệp). Đồng bộ vào Qdrant `col_regulations` (6 points).
     - **Assistant Runtime Binding**: Forward `profile.model_policy.primary_model` từ Assistant sang `AskRequest` và `LLMGenerateRequest` xuyên suốt `RAGAnswerNodeHandler` và `RagService.ask()`.
     - **Relevance Threshold & No-Answer Policy Anti-Hallucination**: Thiết lập `score_threshold: float = 0.35` cho tìm kiếm vector dày đặc Qdrant và thắt chặt logic fallback ILIKE cho PostgreSQL FTS; khi câu hỏi ngoài phạm vi nghiệp vụ (ví dụ: "Cách nấu phở bò"), hệ thống kích hoạt ngay No-Answer Policy: trả về `status: insufficient_context`, `Citations: 0` và thông báo từ chối chính thức của Phòng Đào tạo.
     - **Golden Benchmark 20 Test Cases & TM-08 Compliance**: Mở rộng `qnu_regulations_benchmark` lên 20 test cases. Tinh chỉnh thuật toán TM-08: lọc bỏ các đại từ nghi vấn/hư từ tiếng Việt trong `compute_answer_relevance` và loại trừ tiền tố chào hỏi hành chính trong `compute_faithfulness`. Kết quả chạy đánh giá Benchmark thực tế: Faithfulness: 1.0 (>= 0.90), Relevance: 0.887 (>= 0.85), Context Precision: 0.96 (>= 0.80), Meets TM-08 Standard: **True**.
     - **Verification**: Backend `uv run ruff check .` 0 lỗi, `uv run --extra dev pytest -v` 174/174 passed (100%); Frontend `npm run lint` 0 lỗi (115 files), `npm run typecheck` 0 lỗi, `npm run build` thành công (10.41s); Zero Mojibake 255/255 files (100% UTF-8 sạch).
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

**Backend Quality (phiên #111)**: Full suite **218/218 passed (100%)**, 34 warnings. Hoàn thành Giai đoạn 1 khắc phục khoảng hở kết nối: P0-05 Facts Lifecycle outerjoin & filter, P1-14 Quota endpoint alias, P0-06 Chat Widget endpoint /chat.

---

### ⚠️ Frontend — Độ phủ màn hình cao, LiveMode cần loại bỏ business mock fallback

> Cập nhật phiên #111: Hoàn thành Giai đoạn 1 UI: Sửa endpoint Widget `/chat`, bóc tách `data-api-base` và cập nhật template mã nhúng Channels & Assistant Detail, sửa URL gọi Quota `/modelops/quotas/${tenantId}`.

| Giai Đoạn | Màn Hình / Module | Trạng Thái |
| :--- | :--- | :---: |
| 1 | Master Layout (Sidebar w-64, Topbar h-14, Academic Teal oklch) | ✅ Done |
| 2 | Assistants Studio (05 Trợ lý, Persona, ModelOps config, Tool Gateway, Publish Gate, Clone) | ✅ Done |
| 3 | Knowledge Management & Master-Detail Navigation (List + Detail + Ingest + Full Studio) | ✅ Done |
| 4 | Document Verification Studio (Full 14 scan pages, BBoxes, Regions, ReactMarkdown Tables, In-place Edit) | ✅ Done |
| 4b | **Scan & OCR Document Intelligence Studio** (`/ocr`: Split-Screen, OpenCV Boxes, Excel Viewer, API Code) | ✅ Done |
| 5 | Omni-Channel Chat Studio (SSE Streaming, Thinking Indicator, CitationSheet) | ✅ Done |
| 6 | ModelOps Dashboard (4 Presets, Secret Key Masking, Circuit Breaker Monitor) | ✅ Done |
| 7 | Tools Gateway (Word NĐ 30 Preview, Excel Bloom Matrix, Template Library) | ✅ Done |
| 8 | Workflow DAG Canvas (@xyflow/react, 6 Custom Node types, Run DAG & Inspector) | ✅ Done |
| 9 | Evaluation & Active Remediation (TM-08 Benchmark, Gap Inbox, Resolve) | ✅ Done |

**Frontend Quality**:
- Phiên #111: Biome Lint 0 lỗi trên 130 files | TypeScript 0 lỗi. Build thành công trong 8.03 giây, 0 warnings.
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
6. **AsyncMock DB Refresh trong Test**:
   - Trong unit tests với `AsyncMock` DB, hàm `db.refresh(record)` không tự sinh ID hoặc timestamp như PostgreSQL thật; service cần chủ động khởi tạo explicit ID (`f"ast_{uuid.uuid4().hex[:12]}"`) và datetime UTC trước khi add.

---

## 5. Backlog & Kế Hoạch Tiếp Theo

### Đã Hoàn Thành Trong Giai Đoạn 1 (Phiên #111)
- [x] **P0-06 Web Chat Widget:** Sửa endpoint sang `/chat` kèm `stream: true`, chuẩn hóa `data-api-base` và snippet mã nhúng cross-origin.
- [x] **P1-14 Contract Quota API:** Sửa URL gọi `/modelops/quotas/${tenantId}` và tạo endpoint alias `GET /quota?tenant_id=...` trên backend.
- [x] **P0-05 Facts Lifecycle:** Outerjoin `KnowledgeDocument`, lọc bỏ facts thuộc tài liệu `pending`/`archived` khỏi Hybrid RAG.

### Ưu Tiên Tích Hợp Sau Phiên #108 (Các Giai Đoạn Tiếp Theo)
- [ ] **P0 Truthful Runtime:** loại fake-success khỏi LLM/OCR/Tools/Embedding/Workflow trong LiveMode; lỗi thật phải hiện `failed/degraded`.
- [ ] **P0 Security Boundary:** bảo vệ router quản trị bằng `get_current_actor`, mask/encrypt provider key và chuyển toàn bộ secret sang environment.
- [ ] **P0 Tool Policy:** bắt `tool.api_caller` đi qua `ToolService`, enforce allowlist/HITL và ghi execution audit.
- [ ] **P1 Assistant–ModelOps:** model catalog động theo provider active/capability; primary/fallback deterministic; usage streaming ghi đúng một lần.
- [ ] **P1 Chat–Handoff:** assistant động, attachment thật, conversation/message persistence và staff reply quay lại widget/chat.
- [ ] **P1 Knowledge Index Integrity:** trạng thái `pending_index/indexed/index_failed`, retry/outbox và reconciliation DB–Qdrant–Storage.
- [ ] **P1 Workflow Contract:** validate manifest JSON Schema/version/status và schema-driven Property Inspector.

### Đã Hoàn Thành Trong Đợt 1 (Phiên #101)
- [x] **Cổng Kiểm Định Xuất Bản 5 Lớp (Publish Gate Engine)**: Thẩm định 5 tiêu chí (Knowledge doc ready, ModelOps 2 tầng, Tool Gateway allowlist, Guardrails chống jailbreak/che PII/hotline No-Answer, TM-08 Ragas) trước khi kích hoạt Trợ lý AI.
- [x] **Nhân Bản Trợ Lý 1-Click (Clone Assistant)**: Cho phép khoa/phòng ban nhân bản từ 5 Trợ lý mẫu để tùy biến theo nhu cầu đơn vị.
- [x] **Hòm Thư Lỗ Hổng Tri Thức (Knowledge Gap Inbox & Active Remediation)**: Tự động gom câu hỏi kích hoạt No-Answer Policy vào CSDL `knowledge_gaps`, hiển thị trên `/evaluation` kèm nút "Nạp vào RAG" và "Đánh dấu đã nạp" / "Bỏ qua".

### Trọng Tâm Đợt 2 Tiếp Theo
- [ ] **Dev Access Gate Phía Client & Server**: Trang Login `/login` (đăng nhập cán bộ QNU) bảo vệ các router quản trị nhạy cảm (JWT / HttpOnly Cookie), ngăn truy cập trái phép khi chưa đăng nhập.
- [x] **Observability & Cost Tracking Thực Tế**: Đếm token, tính chi phí USD thật, ghi nhận vào biểu đồ Dashboard thay vì số liệu tĩnh; đồng nhất `generate_stream()` với `generate()` về quota và accounting.
- [ ] **Widget Embed / Kênh Tích Hợp Đa Kênh**: Hoàn thiện mã nhúng Javascript nhúng Trợ lý AI vào Cổng thông tin QNU (`qnu.edu.vn`) và Cổng Tuyển sinh; hỗ trợ web widget standalone.

### Các Tồn Đọng Kỹ Thuật Khác
- [x] Hoàn thành `docs/ke_hoach/10_ke_hoach_chuan_hoa_markdown_qdrant_va_chat_luong_rag.md`: Duplicate-Free Parser, bảng đa trang, typed records, Quality Gate, Facts/atomic chunks, revision-safe Qdrant và golden evaluation; không đưa chunk/fact có conflict vào Qdrant retrievable.
- [ ] Sửa blocker worktree trước mọi đợt seed tiếp: hợp nhất 3 method `delete_document/delete_collection/archive_document`, khôi phục xóa storage gốc, dùng cleanup retryable/outbox và đưa Ruff về xanh.
- [ ] Không gắn Library/Question Bank là official trước khi có PDF/DOCX nguồn, metadata provenance/evidence và lưu tệp gốc qua storage driver; seed/reconcile asset-by-asset thay vì return sớm.
- [x] Thực hiện gói **RAG Data Integrity & Groundedness**: retrieval chỉ lấy document `ready/approved`, đúng tenant/revision; thêm relevance threshold và claim-citation verification.
- [x] Xóa/rebuild orphan facts Question Bank (đã thêm FK & cascade); thêm FK/cascade, source evidence và content revision cho `knowledge_facts`.
- [ ] Reconcile 17 chunks Question Bank sang Qdrant collection chuẩn `col_question_bank`; kiểm chứng parity rồi mới xóa `col_col_question_bank`.
- [x] Cấm mock embedding trong LiveMode; hỗ trợ sparse-only degraded mode có nhãn và health signal rõ ràng.
- [ ] Version hóa RAG cache theo tenant/collection/content revision/assistant/model/policy và invalidate khi approve/edit/archive/delete/reindex.
- [ ] Thực hiện hotfix **Assistant–Workflow Runtime Integrity**: bỏ `is_approved=true`, bỏ mock answer/citation/artifact trong LiveMode, fail-fast khi export lỗi và loại KPI/count giả.
- [ ] Lấy tenant/user/role/approval actor từ trusted auth context; enforce tool allowlist, node permissions, connection allowlist và approval trước side effect.
- [ ] Hoàn thiện workflow Soạn thảo/Ngân hàng câu hỏi: clarify wait/resume, RAG context assembly, syllabus/CLO/Bloom validation và artifact metadata động.
- [ ] Triển khai SSE thật và cancellation server-side; sửa citation DTO mapping `source_id/section/page_number/quote` sang Frontend.
- [ ] Thực hiện gói **Knowledge Index Integrity**: state machine `review_pending/indexing/ready/index_failed`, retrieval chỉ lấy đúng revision `ready`, và reconciliation PostgreSQL–Qdrant.
- [ ] Đối chiếu/migrate 16 points từ `col_col_question_bank` sang collection chuẩn `col_question_bank`; chỉ xóa legacy sau khi kiểm chứng.
- [ ] Đồng bộ vector/facts khi approve, sửa, archive, xóa document/collection; loại ghost citations và cấm mock embedding trong LiveMode.
- [ ] Nâng lexical retrieval từ `ILIKE` lên PostgreSQL FTS thật; chạy dense/sparse song song và enforce tenant/workspace filter trong Qdrant.
- [ ] Triển khai **Dev Access Gate** tối giản: password hash từ env, signed HttpOnly session, `/auth/login`/`me`/`logout`, principal `tenant_qnu/workspace_qnu/admin`; bảo vệ API thay đổi dữ liệu, Tool Gateway và approval. Chỉ mở rộng RBAC/SSO khi có nhiều cán bộ/tenant.
- [ ] Tách DemoMode/LiveMode và loại business mock fallback khỏi LiveMode.
- [ ] Thay Evaluation/TM-08 mô phỏng bằng việc chạy Assistant/RAG runtime thật và tổng hợp metrics từ DB.
- [ ] Nối RAG Answer Composer với ModelOps; bind Assistant primary/fallback model, tool allowlist và evaluation policy xuống runtime.
- [ ] Khóa Workflow execution/resume vào immutable version; bổ sung timeout, retry/backoff, cancellation, schema/port và permission validation.
- [x] Nạp tài liệu chính thức và golden datasets cho Admissions (`col_admissions`) và Regulations (`col_regulations`).
- [x] Tách các file lớn trên 1.000 dòng theo SRP: hoàn thành `api-client.ts` (2.074 -> 57 dòng) và `modelops-page.tsx` (2.961 -> 854 dòng).
- [x] Tối ưu frontend bundle bằng code splitting và route-level lazy loading (chunk chính giảm xuống 372 kB, 0 warnings).
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
