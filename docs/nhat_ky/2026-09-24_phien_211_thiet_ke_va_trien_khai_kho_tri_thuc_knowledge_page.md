# NHẬT KÝ PHIÊN LÀM VIỆC #211
# Thời gian: 2026-09-24 11:45
# Nội dung: Thiết Kế & Triển Khai Hoàn Chỉnh Phân Hệ Kho Tri Thức (/knowledge) Trên Frontend2

---

## 1. Mục Tiêu Phiên Làm Việc
1. **Đóng vai trò Chuyên gia UI/UX & Frontend Architect** thiết kế toàn diện kiến trúc phân hệ Kho Tri Thức (`/knowledge`) trên nền tảng `frontend2`.
2. **Triển khai kiến trúc Master-Detail Deep Routing** (Mục 4.5 của `AGENTS.md`):
   - Danh sách tổng quan Master View: `/knowledge`
   - Trung tâm quản trị Dedicated Detail View: `/knowledge/:collectionId`
3. **Tuân thủ 100% các quy chuẩn cốt lõi**:
   - Nhận diện Academic Teal (`oklch(0.46 0.13 160)`).
   - 100% Lucide Icons thanh lịch, Zero Emoji trên giao diện quản trị (Mục 4.8).
   - Tận dụng triệt để Radix UI primitives & Admin helpers, Zero raw native form controls (Mục 4.9).
   - Thiết kế đa thiết bị & Responsive, không cuộn ngang vỡ layout (Mục 4.10).
   - Nhãn nút bấm ngắn gọn, tinh tế 1-2 từ (Mục 4.11).
4. **Bảo đảm chuẩn kiểm thử Frontend**: Biome check 0 lỗi, TypeScript typecheck 0 lỗi, Vite build thành công.

---

## 2. Các Thành Phần Đã Triển Khai

### A. Định Tuyến File-Based TanStack Router (`frontend2/src/routes/`)
- [`frontend2/src/routes/knowledge.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend2/src/routes/knowledge.tsx): Layout Route bọc `<Outlet />`.
- [`frontend2/src/routes/knowledge.index.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend2/src/routes/knowledge.index.tsx): Tuyến `/knowledge/` hiển thị `KnowledgePage`.
- [`frontend2/src/routes/knowledge.$collectionId.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend2/src/routes/knowledge.$collectionId.tsx): Tuyến động `/knowledge/:collectionId` hiển thị `CollectionDetailPage`.

### B. Màn Hình Danh Sách Master View: [`KnowledgePage`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend2/src/features/knowledge/knowledge-page.tsx)
- **Header & Action Bar**: Tiêu đề "Kho Tri Thức", nút "Làm mới", nút "Thêm kho" kích hoạt Dialog tạo kho mới.
- **Dải chỉ số KPI Telemetry**:
  - Kho Tri Thức (Đang hoạt động)
  - Văn Bản Bóc Tách (PDF, DOCX, XLSX)
  - Vector Chunks (BGE-M3 1024D)
  - Cơ Sở Dữ Liệu (Qdrant + Postgres Hybrid Search RRF k=60)
- **Thanh công cụ Toolbar**: Ô tìm kiếm Debounced thời gian thực, bộ lọc chiến lược Chunking (Điều/Khoản, Ngữ nghĩa), bộ lọc OCR Engine (PyMuPDF, Docling, EasyOCR), nút chuyển chế độ xem Thẻ (Grid) / Bảng (Table).
- **Cards Grid & Table View**: Thẻ hiển thị mã code font mono, số lượng tài liệu, số chunks, chiến lược chunking, nút "Nạp tài liệu", nút "Mở kho", và menu thao tác nhanh (Sửa, Đối soát, Xóa).

### C. Màn Hình Quản Trị Chi Tiết: [`CollectionDetailPage`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend2/src/features/knowledge/collection-detail-page.tsx)
- **Hero Header [`CollectionHeader`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend2/src/components/knowledge/collection-header.tsx)**:
  - Nút quay lại danh sách co giãn nhạy (`← Kho tri thức` / `← Kho`).
  - Badge trạng thái hiệu lực và mã kho.
  - Các nút hành động tinh gọn: "Đối soát", "Reindex", "Sửa", "Nạp tài liệu".
- **Tabs Điều Hướng 4 Khối Nghiệp Vụ Chuyên Sâu**:
  1. `Tài liệu`: Quản lý danh sách văn bản, bộ lọc loại/trạng thái, xem trước, tải tệp gốc, reindex từng file và xóa tài liệu.
  2. `Facts số`: Bảng biểu sự thật cấu trúc (Điểm chuẩn, Học phí, Chỉ tiêu), nút "Nhập Excel".
  3. `Tiến trình`: Theo dõi lịch sử tác vụ Ingestion chạy ngầm (ARQ background tasks), trạng thái và nút xem log.
  4. `Thử nghiệm`: Khung Sandbox truy vấn thử nghiệm trực tiếp Hybrid RRF BGE-M3 + Postgres FTS.

### D. Dialog Nạp Tài Liệu Thông Minh: [`DocumentUploadDialog`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend2/src/components/knowledge/dialogs/document-upload-dialog.tsx)
- Khu vực kéo thả tệp trực quan (hỗ trợ PDF, DOCX, XLSX, TXT, MD).
- Nhập tiêu đề hiển thị tùy chỉnh.
- Lựa chọn loại văn bản chuẩn hóa từ taxonomy hệ thống.
- Lựa chọn OCR Engine (Auto, PyMuPDF, Docling, Gemini Vision, Mistral OCR).
- Công tắc Fast-Track: Tự động phê duyệt & nạp vector vào Qdrant ngay sau khi bóc tách hoàn tất.

### E. Mở Rộng API Client: [`frontend2/src/services/knowledge-api.ts`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend2/src/services/knowledge-api.ts)
- Bổ sung hàm `deleteCollection(collectionId)`.
- Bổ sung alias `getReconciliationReport(collectionId)` và `getDocumentDownloadUrl(documentId)`.
- Kết nối `jobsApi.getIngestionTasks(collectionId)` đồng bộ.

---

## 3. Kết Quả Kiểm Thử (Verification)
- **Biome Linter**: `npx @biomejs/biome check --write` trên toàn bộ các file mới ➔ **0 lỗi, 0 cảnh báo**.
- **TypeScript**: `tsc --noEmit` ➔ **0 lỗi**.
- **Vite Build**: `npm run build` ➔ **Thành công (1.58s)**, sinh mã bundle riêng cho `knowledge.index` (17.04 kB) và `knowledge.$collectionId` (48.21 kB).

---

## 4. Tinh Chỉnh & Hoàn Thiện Vi Mô (UI/UX Micro-Polish)
Sau khi người dùng xem xét trực tiếp giao diện và phê duyệt các điểm tối ưu, đã tiến hành tinh chỉnh 5 hạng mục:
1. **Làm dịu nút bấm**:
   - Chuyển nút "Mở kho" trên các thẻ bộ sưu tập từ nền khối đậm sang dạng outline thanh thoát (`bg-primary/10 text-primary hover:bg-primary hover:text-primary-foreground border border-primary/20 transition-colors`), giúp tổng thể trang kho tri thức nhẹ nhàng và cao cấp hơn.
2. **Khắc phục cắt chữ trên Select Triggers**:
   - Mở rộng các trigger bộ lọc từ 140-160px lên 165-175px (Loại văn bản, Chiến lược Chunking, Bộ máy OCR, Mức ưu tiên), hiển thị trọn vẹn văn bản "Tất cả loại văn bản", "Mọi bộ máy OCR", "Mọi chiến lược" mà không bị dấu chấm lửng `...`.
3. **Format chuỗi kỹ thuật & Chuẩn hóa Badge trạng thái**:
   - Hàm `formatDocumentType` bổ sung ánh xạ toàn diện từ vựng hành chính (`thong_bao` ➔ "Thông báo", `quy_che` ➔ "Quy chế", `de_an` ➔ "Đề án",...).
   - Nhãn mức ưu tiên rút gọn tinh tế (`core` ➔ "Cốt lõi", `high` ➔ "Bổ trợ", `normal` ➔ "Tham khảo").
   - Hiển thị huy hiệu xanh `Đã index` khi tài liệu đạt trạng thái `ready` / `approved` / `completed`.
4. **Ẩn badge số đếm 0 trên Tabs**:
   - Trên thanh Tabs của trang chi tiết kho tri thức, các badge số đếm chỉ hiển thị khi `count > 0` (`allDocuments.length > 0`, `factsQuery.data.total > 0`, `allTasks.length > 0`), loại bỏ tình trạng hiển thị `(0)` thừa thãi.
5. **Chuẩn hóa dải KPI Counter đồng bộ mẫu hệ thống**:
   - Sử dụng đúng cấu trúc `<Card className="overflow-hidden border bg-card shadow-xs"><CardContent className="grid p-0 sm:grid-cols-2 lg:grid-cols-4 divide-y sm:divide-y-0 sm:divide-x">` kết hợp `KpiMetric` (icon góc trên phải, số đếm to đậm ở giữa, chú thích helper thanh mảnh ở dưới, các vách ngăn hairline phân cách giữa các ô), đồng bộ 100% với màn hình Quản lý cư trú (`residences-page.tsx`).
6. **Bố cục lưới đáp ứng (Responsive Grid Layout)**:
   - Cấu hình lưới hiển thị danh sách thẻ kho tri thức theo đúng yêu cầu:
     - **Mobile (< 640px)**: 1 cột (`grid-cols-1`).
     - **Tablet (640px - 1023px)**: 2 cột (`sm:grid-cols-2`).
     - **Desktop (≥ 1024px)**: 4 cột (`lg:grid-cols-4`).
   - Tối ưu padding nội dung thẻ (`p-4`) để tận dụng tối đa chiều rộng và bảo đảm các badge, nút thao tác cân đối.
7. **Thanh thao tác hàng loạt Popup nổi ở giữa (Floating Bulk Actions Pill)**:
   - Thay thế khối banner tĩnh đẩy layout cũ bằng component chuẩn hệ thống `DataTableBulkActions` (`fixed bottom-5 inset-x-0 z-40 flex justify-center`).
   - Khi tick chọn nhiều checkbox trong bảng tài liệu, xuất hiện thanh pill nổi bo tròn mềm mại giữa đáy màn hình gồm:
     - Nút tròn `X` bỏ chọn nhanh.
     - Vách ngăn hairline kèm badge đếm số lượng đen/trắng `(N) tài liệu đã chọn`.
     - Cặp nút hành động nhanh: **"Duyệt (N)"** (kích hoạt duyệt & vector hóa) và **"Xóa (N)"** (xóa hàng loạt).
8. **Tái thiết kế toàn diện trải nghiệm Đa thiết bị & Mobile Responsive (Cross-Device Standard)**:
   - **Tái thiết kế `CollectionHeader`**:
     - *Mobile Layout*: Tách biệt hàng nút điều hướng `← Kho` và huy hiệu trạng thái `Sẵn sàng` / mã kho `admissions`. Tiêu đề bộ sưu tập hiển thị rõ ràng, không bị chèn ép.
     - *Cụm nút hành động linh hoạt*: Nút hành động chính **"Nạp tài liệu"** hiển thị nổi bật dạng full-width (`col-span-3 sm:col-span-1`), bên dưới là lưới 3 cột đều cho 3 nút phụ ("Đối soát", "Reindex", "Sửa"). Trên màn hình máy tính bảng và desktop, toàn bộ 4 nút tự động chuyển thành hàng ngang cân xứng.
     - *Dòng Meta kỹ thuật dạng Pill Chips*: Thay thế các ký tự gạch chấm `•` dễ bị rớt dòng lẻ loi bằng các khối chip bo góc nguyên tử (`inline-flex` tags), tự động bọc dòng mượt mà trên màn hình nhỏ.
   - **Tối ưu thanh Tabs tối giản, không bị cắt xén (Zero Clipping)**:
     - Rút gọn nhãn tab tuân thủ nghiêm ngặt Quy tắc 11 `AGENTS.md` (loại bỏ badge số đếm cồng kềnh gây tràn màn hình), bổ sung `shrink-0 whitespace-nowrap` trên toàn bộ `TabsTrigger`. Cả 4 tab ("Tài liệu", "Facts số", "Tiến trình", "Thử nghiệm") vừa vặn hoàn hảo trên màn hình mobile 360px mà không bị cắt góc.
   - **Thiết kế Chế độ Thẻ di động chuyên biệt (Mobile Card-Based View)**:
     - Bổ sung chế độ xem thẻ (`sm:hidden`) cho Tab Tài liệu, Tab Tiến trình và Tab Facts số theo đúng quy chuẩn Rule 10 `AGENTS.md`, thay vì ép người dùng cuộn ngang bảng 6 cột chật chội.
     - Trên mobile, mỗi tài liệu hiển thị dạng thẻ card sắc nét với: checkbox chọn hàng loạt, tiêu đề, tên file, dung lượng, phiên bản, nhãn loại văn bản, mức ưu tiên, số chunks, trạng thái index, và hàng nút thao tác cảm ứng nhanh (Duyệt nhanh 1-Click, Scan Studio, Chunks Inspector, Tải tệp, Xóa).
     - Giữ nguyên cấu trúc Bảng (`hidden sm:block`) cho màn hình Tablet và Desktop.
   - **Lưới Bộ lọc Responsive 2 Cột (Responsive Filters Grid)**:
     - Tái cấu trúc cụm Selects thành lưới `grid grid-cols-2 gap-2 sm:flex` với `w-full sm:w-[155px]`, loại bỏ hoàn toàn tình trạng tràn ngang hoặc cắt chữ lửng `...` trên màn hình hẹp.
   - **Lược bỏ viền bao quanh thanh bộ lọc (Borderless Filter Bar)**:
     - Loại bỏ khung viền bao ngoài `border border-border bg-card p-3 shadow-2xs` trên toàn bộ thanh tìm kiếm và bộ lọc của trang Kho tri thức ([`knowledge-page.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend2/src/features/knowledge/knowledge-page.tsx)), trang Trợ lý AI ([`assistants-page.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend2/src/features/assistants/assistants-page.tsx)), cũng như các tab chi tiết bộ sưu tập ([`collection-documents-tab.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend2/src/components/knowledge/tabs/collection-documents-tab.tsx), [`collection-tasks-tab.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend2/src/components/knowledge/tabs/collection-tasks-tab.tsx), [`collection-facts-tab.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend2/src/components/knowledge/tabs/collection-facts-tab.tsx)).
     - Các điều khiển `Input` và `Select` tự giữ viền riêng thanh thoát, giúp giao diện thông thoáng, liền mạch và hiện đại hơn.
   - **Chuẩn hóa thành Quy Tắc UI Bắt Buộc (Rule 12 trong AGENTS.md & SKILL.md)**:
     - Bổ sung **Quy tắc 12: Quy Chuẩn Thanh Tìm Kiếm & Bộ Lọc Liền Mạch (Seamless & Borderless Filter Bar Pattern)** vào [`AGENTS.md`](file:///d:/DuAnPhanMem/qnu-ai-platform/AGENTS.md) và Mục 3.6 của [`.agents/skills/qnu-frontend-architect/SKILL.md`](file:///d:/DuAnPhanMem/qnu-ai-platform/.agents/skills/qnu-frontend-architect/SKILL.md).
     - Quy định nghiêm cấm "viền lồng viền" (box-in-box) trên thanh bộ lọc; container chỉ dùng flex/grid bố cục đặt trực tiếp trên nền trang (`bg-background`).

9. **Loại bỏ Tab "Thử nghiệm" và Lược bỏ Chip "Chiến lược: SemanticChunker"**:
   - **Lược bỏ Chip Chiến Lược Chunking kỹ thuật**: Loại bỏ khối chip `Chiến lược: {collection.chunking_strategy}` khỏi thanh sub-meta trong [`collection-header.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend2/src/components/knowledge/collection-header.tsx). Người dùng nghiệp vụ/quản trị viên không cần bận tâm về thuật toán kỹ thuật nội bộ (`SemanticChunker` / `ClauseBasedChunker`), giữ dòng meta gọn gàng và tập trung vào Model Embedding và Quy mô (số văn bản & chunks).
   - **Loại bỏ Tab "Thử nghiệm"**: Lược bỏ tab Playground và toàn bộ mã nguồn xử lý truy vấn sandbox trong [`collection-detail-page.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend2/src/features/knowledge/collection-detail-page.tsx) cùng định nghĩa type trong [`types.ts`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend2/src/components/knowledge/types.ts). Giờ đây trang chi tiết kho tri thức chỉ gồm 3 tab cốt lõi:
     - Tài liệu (`documents`): Quản lý danh sách văn bản, upload, duyệt, xem chunks.
     - Facts số (`facts`): Quản lý bảng dữ liệu có cấu trúc.
     - Tiến trình (`tasks`): Theo dõi các tác vụ xử lý nền, Ingestion & Reindex.
   - **Tối ưu mã nguồn**: Dọn dẹp sạch sẽ các state `sandboxQuery`, `isSearchingSandbox`, `sandboxResults`, handler `handleSandboxSearch` và import icon `Zap`.
