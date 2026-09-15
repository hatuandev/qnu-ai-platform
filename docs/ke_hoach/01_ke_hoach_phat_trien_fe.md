# Kế Hoạch Phát Triển Frontend QNU AI Platform (Chuẩn Design System QLKTX)

> **Dự án**: QNU AI Platform Frontend (`frontend/`)  
> **Kiến trúc mục tiêu**: Vite 8 + React 19 + TanStack Suite + Tailwind CSS v4 + Biome  
> **Mẫu thiết kế đối chiếu**: Hệ thống thiết kế & Khung vỏ QLKTX (`qnu-ktx/src/Web/ClientApp`)  
> **Ngày lập kế hoạch**: 15/09/2026  

---

## 🎯 1. Mục Tiêu & Tôn Chỉ Thiết Kế

1. **Đồng bộ 100% với hệ thống phần mềm Trường ĐH Quy Nhơn (`qnu-ktx`)**:
   - Sử dụng chung không gian màu **OKLCH** với sắc xanh Teal học thuật đặc trưng (`--primary: oklch(0.46 0.13 160)`).
   - Kế thừa trọn vẹn khung vỏ giao diện (**`AdminShell`**): Thanh bên (**`AppSidebar`**), Thanh đỉnh (**`Topbar`**), Dải phân cấp (**`Breadcrumbs`**), và Hộp thoại tìm kiếm nhanh (**`CommandMenu`** `Ctrl + K`).
   - Tuân thủ nghiêm ngặt quy chuẩn tỷ lệ chữ (Typography: 14px body/controls, 12px toolbars/headers, 11px microcopy), bán kính bo góc (6px control, 8px surface) và Dark/Light mode tự động.
2. **Hiệu năng cao & Tối ưu máy chủ VPS (Dokploy)**:
   - Thay thế hoàn toàn SSR cồng kềnh của Next.js bằng **Vite 8 Single Page Application (SPA)** siêu nhẹ (serve qua Nginx chỉ tốn ~15–20MB RAM).
   - Tốc độ Hot Module Replacement (HMR) dưới 50ms, kiểm tra định dạng và linter siêu tốc với **Biome**.
3. **Chuyên biệt hóa cho Trí tuệ Nhân tạo (AI Extensions)**:
   - Tích hợp công nghệ hiển thị thời gian thực Server-Sent Events (**SSE Streaming**).
   - Tích hợp thư viện đồ thị kéo thả **`@xyflow/react` (React Flow v12)** phục vụ Visual DAG Canvas cho 05 Trợ lý AI QNU.
   - Bổ sung bộ components chuyên trách AI: Bong bóng tin nhắn (**`Message` & `Bubble`**), Bộ cuộn thông minh (**`MessageScroller`**), Thẻ đính kèm tệp (**`Attachment`**), Thẻ câu hỏi trắc nghiệm (**`Questionnaire`**), và Ngăn kéo tra cứu dẫn chứng (**`CitationSheet`**).

---

## 🎨 2. Hệ Thống Token Thiết Kế & Quy Chuẩn Giao Diện

### 2.1. Bảng Token Màu OKLCH (`src/styles/tokens.css`)

```css
:root {
  /* Màu sắc chủ đạo (QNU Academic Teal) */
  --primary: oklch(0.46 0.13 160);
  --primary-foreground: oklch(0.985 0 0);

  /* Bề mặt & Nền */
  --background: oklch(1 0 0);
  --foreground: oklch(0.145 0 0);
  --card: oklch(1 0 0);
  --card-foreground: oklch(0.145 0 0);
  --popover: oklch(1 0 0);
  --popover-foreground: oklch(0.145 0 0);

  /* Màu ngữ nghĩa trạng thái */
  --success: oklch(0.55 0.14 160);       /* Trạng thái Healthy / Sẵn sàng */
  --warning: oklch(0.72 0.15 80);        /* Cảnh báo hạn ngạch Token / Quota */
  --destructive: oklch(0.577 0.245 27.325); /* Lỗi Circuit Breaker / Từ chối */
  --info: oklch(0.58 0.16 250);          /* Thông tin RAG / Dẫn chứng */

  /* Bảng màu biểu đồ (FinOps & Ragas TM-08) */
  --chart-1: oklch(0.46 0.13 160);
  --chart-2: oklch(0.58 0.16 250);
  --chart-3: oklch(0.72 0.15 80);
  --chart-4: oklch(0.58 0.14 320);

  /* Kích thước & Căn lề chuẩn */
  --radius-micro: 0.25rem;               /* 4px: Badges, Kbd */
  --radius-control: 0.375rem;            /* 6px: Buttons, Inputs */
  --radius-surface: 0.5rem;              /* 8px: Cards, Dialogs, Drawers */
  --sidebar-width: 16rem;                /* 256px */
  --topbar-height: 3.5rem;               /* 56px */
  --control-height: 2.25rem;             /* 36px */
  --control-height-sm: 2rem;             /* 32px */
  --table-row-height: 2.75rem;           /* 44px */
}

/* Chế độ Dark Mode */
.dark {
  --background: oklch(0.145 0 0);
  --foreground: oklch(0.985 0 0);
  --card: oklch(0.18 0 0);
  --card-foreground: oklch(0.985 0 0);
  --primary: oklch(0.67 0.13 160);
  --primary-foreground: oklch(0.16 0 0);
  --border: oklch(1 0 0 / 12%);
  --input: oklch(1 0 0 / 14%);
}
```

### 2.2. Quy Tắc Typography & Bán Kính Bắt Buộc
1. **Body & Controls**: Chuẩn 14px (`text-sm`), phông chữ `Inter`.
2. **Compact Toolbars & Headers**: Chuẩn 12px (`text-xs`), chiều cao `size="sm"` (32px), icons `size-3.5`.
3. **Table Headers**: 12px (`text-xs`), semibold, chữ màu nhạt `text-muted-foreground`.
4. **Bán kính bo góc**: Mọi nút bấm và input tuân thủ nghiêm ngặt 6px (`rounded-md`); các Cards và Panel bề mặt dùng 8px (`rounded-lg` hoặc `rounded-xl` với `shadow-2xs`).

---

## 🧩 3. Danh Mục Components: Kế Thừa & Tự Xây Dựng (AI Custom)

Dựa trên danh sách các components và bộ thư viện của `qnu-ktx`, hệ thống chia thành 3 lớp rõ ràng:

### Lớp 1: Components Cơ Sở (Primitives kế thừa từ Radix & shadcn)
- `Button`, `Input`, `Textarea`, `Label`, `Badge`, `Avatar`, `Card`, `Tabs`, `Table`, `Dialog`, `Alert Dialog`, `Dropdown Menu`, `Collapsible`, `Accordion`, `Tooltip`, `Popover`, `Progress`, `Skeleton`, `Switch`, `Separator`.

### Lớp 2: Components Quản Trị Tái Sử Dụng (Kế thừa từ `qnu-ktx/src/components/admin/`)
- **`empty-state.tsx`** (`Empty`): Hiển thị khi danh sách tài liệu trống hoặc chưa bắt đầu phiên chat.
- **`field.tsx`** (`Field`): Wrapper chuẩn cho trường nhập liệu kèm label và lỗi validate Zod.
- **`file-upload.tsx`**: Kéo thả tệp PDF, Word, Excel nạp vào hệ thống RAG.
- **`confirm-dialog.tsx`**: Hộp thoại xác nhận xóa tài liệu, phê duyệt workflow.
- **`status-badge.tsx`**: Hiển thị trạng thái màu chuẩn (Closed, Open, Half-Open, Ready, Processing).
- **`kpi-metric.tsx`**: Thẻ thống kê số lượng token, chi phí FinOps USD, tỷ lệ Faithfulness.

### Lớp 3: Components Chuyên Biệt AI (Tự Xây Dựng Mới — Custom AI Components)
- **`ChatMessage` & `ChatBubble`** ⭐:
  - Phân tách rõ ràng giữa câu hỏi người dùng và câu trả lời AI.
  - Tích hợp Avatar riêng cho từng Trợ lý (Tuyển sinh, Quy chế, Thư viện, Soạn thảo, Đề thi).
  - Tích hợp hiệu ứng đang suy nghĩ (*Thinking Indicator* / *Pulsing Dots*).
  - Tích hợp thanh công cụ: Nút sao chép nội dung Markdown, nút tạo lại câu trả lời (Regenerate), và các nhãn trích dẫn nguồn (**Citation Badges**).
- **`MessageScroller`** ⭐:
  - Khối cuộn thông minh: Tự động cuộn xuống dưới khi AI đang stream chữ ra, nhưng tự động dừng cuộn nếu người dùng lăn chuột lên trên để đọc lại tài liệu cũ (tránh giật màn hình).
- **`Attachment`** ⭐:
  - Thẻ đính kèm tệp nhỏ gọn hiển thị icon định dạng (PDF/DOCX/XLSX), tên file, dung lượng và trạng thái bóc tách OCR.
- **`QuestionnaireCard`** ⭐:
  - Khung hiển thị câu hỏi trắc nghiệm (A, B, C, D) sinh ra từ Trợ lý Ngân hàng đề thi (`question_bank`) hoặc bộ 100 câu kiểm thử Ragas TM-08. Hỗ trợ người dùng bấm chọn đáp án và bung lời giải thích.
- **`CitationSheet`** ⭐:
  - Ngăn kéo trượt từ mép phải màn hình (`Sheet`), hiển thị chi tiết tên văn bản quy phạm, số hiệu Điều/Khoản, số trang và trích đoạn dẫn chứng để người dùng đối chiếu tính trung thực (Anti-Hallucination).
- **`Kbd`**:
  - Phím tắt nhỏ gọn font-mono (ví dụ: `Ctrl + K`, `Enter`, `Shift + Enter`).
- **`Spinner`**:
  - Vòng xoay biểu thị trạng thái đang xử lý embedding vector hoặc gọi mô hình.

---

## 🗺️ 4. Bản Đồ Điều Hướng & Cấu Trúc Tính Năng Chi Tiết (In-depth Feature Architecture)

Bản đồ điều hướng được chuẩn hóa từ [`qnu-ai-core/services/studio-ui`](file:///d:/DuAnPhanMem/DeTaiAI/qnu-ai-core/services/studio-ui), trong đó làm rõ các cấu phần chuyên sâu của từng phân hệ (đặc biệt là **Kho Tri Thức** hợp nhất toàn bộ luồng bóc tách OCR, loại văn bản, bảng sự thật và playground):

```
[ Khung Vỏ Quản Trị: AdminShell ]
│
├── 1. VẬN HÀNH & TRỢ LÝ (Operations & Assistants):
│     ├── /                    : Bảng điều khiển Tổng quan (Thống kê tokens, chi phí FinOps, trạng thái hệ thống)
│     ├── /assistants          : Danh mục 05 Trợ lý AI Chuyên trách QNU
│     │     ├── [id]           : Chi tiết & Cấu hình Trợ lý (Persona, System Prompt, Tri thức ràng buộc, Guardrails)
│     │     ├── [id]/canvas    : Visual DAG Canvas (Trực quan hóa đồ thị quy trình xử lý của Trợ lý qua React Flow)
│     │     └── [id]/chat      : Thử nghiệm Trò chuyện Chuyên biệt (Test riêng cho từng trợ lý)
│     ├── /chat                : Khung Chatbot Studio Toàn năng (Hỏi đáp trực tiếp, SSE streaming, Citation Drawer)
│     ├── /conversations       : Hội thoại & Handoff (Lịch sử chat đa kênh, Bàn giao trực tiếp cho Tư vấn viên - Live Human Handoff)
│     ├── /channels            : Kênh Phân phối & Mã Nhúng (Cấu hình Web Widget nhúng, CDN script cho cổng thông tin trường)
│     └── /runs                : Lịch sử Thực thi DAG (Trace chi tiết các bước chạy node, input/output và độ trễ)
│
├── 2. KHO TRI THỨC & QUY TRÌNH (Knowledge Hub & Pipelines):
│     ├── /knowledge           : Trung tâm Quản trị Tri thức (Collections theo 5 module)
│     │     ├── [id]           : Chi tiết Collection gồm 3 tab chức năng:
│     │     │     ├── Tab Documents  : Danh sách tài liệu (Upload kéo thả tích hợp chọn bộ máy OCR: PyMuPDF, PaddleOCR, Docling, RapidOCR; quản lý trạng thái, phân loại)
│     │     │     ├── Tab Jobs       : Hàng đợi tác vụ ngầm Ingestion & Cửa sổ Live Terminal Logs
│     │     │     └── Tab Playground : Sân chơi thử nghiệm truy xuất Hybrid RAG (Dense + Sparse FTS + Rerank)
│     │     ├── [id]/documents/[docId] : Document Studio Viewer (Soi văn bản Markdown, Soi từng Chunk Điều/Khoản)
│     │     └── [id]/ingest    : Wizard Nạp Tri Thức Nâng Cao (Upload -> Chọn OCR -> Preview -> Chunking -> Index)
│     │
│     ├── /document-types      : Quản lý Loại Văn bản (Cấu hình mẫu biểu, mức độ ưu tiên pháp lý: Quyết định, Quy chế, Tờ trình...)
│     ├── /nodes               : Danh mục Node Manifest (Đặc tả thư viện các loại Node của DAG Engine)
│     ├── /tools               : Cổng Công cụ & API Ngoài (Builtin: UIS tra cứu điểm chuẩn, Xuất Word NĐ30, Excel Bloom; Custom Tools với Test Runner cURL)
│     └── /evaluation          : Kiểm định Chất lượng Ragas TM-08 gồm 3 tab chức năng:
│           ├── Tab Datasets   : Bộ dữ liệu kiểm thử vàng (Golden Dataset 100 câu hỏi tuyển sinh & quy chế)
│           ├── Tab Scorecard  : Bảng điểm 3 chỉ số TM-08 (Faithfulness >= 0.90, Relevance >= 0.85, Precision >= 0.80)
│           └── Tab Gap Inbox  : Hộp thư lỗ hổng tri thức (Gom câu hỏi bot chưa trả lời được để biên tập bổ sung)
│
└── 3. HỆ THỐNG & QUẢN TRỊ (System & ModelOps):
      ├── /models              : Quản trị Mô hình & Provider (ModelOps) gồm 2 tab:
      │     ├── Tab Providers  : Quản lý Cloud (OpenAI, Gemini), Local On-Premise (vLLM, Qwen2.5-7B), Custom Provider
      │     └── Tab Profiles   : Hồ sơ mô hình (Routing, Fallback Cascade, Circuit Breaker 3 trạng thái, Hạn ngạch Quota & FinOps Logs)
      ├── /developer           : Cổng Developer & API Keys (Quản lý khóa API các phòng ban, Webhooks, API Docs)
      └── /design-system       : Hệ thống Thiết kế UI (Showcase kiểm thử tokens, bảng màu OKLCH, typography, components)
```

---

## 📅 5. Lộ Trình Triển Khai 5 Giai Đoạn (Implementation Roadmap)

### Giai Đoạn 1: Scaffolding & Dọn Dẹp Nền Tảng
- Xóa bỏ các tệp tin cấu hình Next.js cũ trong `qnu-ai-platform/frontend`.
- Khởi tạo `package.json` mới với: Vite 8, React 19, TypeScript, TanStack Router, TanStack Query v5, TanStack Table v8, TanStack Form, Zod v4, Tailwind CSS v4, `@tailwindcss/vite`, `@radix-ui/*`, `lucide-react`, `sonner`, `@biomejs/biome`, `@xyflow/react`, `eventsource-parser`, `react-markdown`.
- Thiết lập `vite.config.ts` (kèm reverse proxy tới Backend `http://localhost:8001`), `biome.json`, `tsconfig.json`, `index.html`.

### Giai Đoạn 2: Đồng Bộ Design System & UI Primitives
- Thiết lập `src/styles/tokens.css` (OKLCH Color Palette, Radius, Spacing, Transitions) và `src/styles/globals.css`.
- Sao chép và chuẩn hóa toàn bộ các UI Primitives từ `qnu-ktx` sang `src/components/ui/` (`button`, `input`, `badge`, `card`, `dialog`, `dropdown-menu`, `sidebar`, `table`, `tabs`, `sheet`, `tooltip`, `popover`, `progress`, `skeleton`, v.v.).
- Tạo component `Kbd` và `Spinner`.
- Xây dựng `ThemeProvider` hỗ trợ chuyển đổi Light/Dark/System mode.

### Giai Đoạn 3: Dựng Khung Vỏ Layout Shell (`AdminShell`)
- Xây dựng `src/layouts/app-sidebar.tsx`: Thanh bên thu gọn mượt mà, render menu từ `src/navigation/config.ts`, đính kèm badges và footer thông tin người dùng.
- Xây dựng `src/layouts/topbar.tsx`: Header cố định 56px với hiệu ứng `backdrop-blur`, `SidebarTrigger`, `Breadcrumbs`, thanh tìm kiếm nhanh `Ctrl + K`, nút đổi theme, popover thông báo.
- Xây dựng `src/layouts/command-menu.tsx`: Hộp thoại modal tìm kiếm nhanh (cmdk).
- Xây dựng `src/layouts/admin-shell.tsx` gắn kết toàn bộ khung vỏ.

### Giai Đoạn 4: Bộ Tiện Ích Chuyên Trách AI (AI Suite Components)
- Xây dựng Custom Hook `useRAGStream()` bằng `eventsource-parser` kết nối endpoint SSE Backend.
- Xây dựng `ChatMessage`, `ChatBubble` (kèm Markdown, code highlight, citation badges).
- Xây dựng `MessageScroller` tự động ghim đáy mượt mà.
- Xây dựng `CitationSheet` hiển thị trích đoạn minh chứng tài liệu gốc.
- Xây dựng `Attachment` cho phép kéo thả tài liệu và đính kèm trong chat.
- Xây dựng `QuestionnaireCard` hiển thị câu hỏi trắc nghiệm Bloom.
- Xây dựng `DAGCanvas` trên nền `@xyflow/react` render trực quan các nodes của 5 Trợ lý QNU.

### Giai Đoạn 5: Thiết Lập Định Tuyến & Các Màn Hình Chức Năng
- Cấu hình TanStack Router file-based:
  - Phân hệ 1 (Vận hành & Trợ lý): `/` (Tổng quan), `/assistants` (Trợ lý AI), `/chat` (Thử nghiệm Chat), `/conversations` (Hội thoại & Handoff), `/channels` (Kênh phân phối), `/runs` (Lịch sử thực thi).
  - Phân hệ 2 (Tri thức & Quy trình): `/knowledge` (Kho tri thức - tích hợp wizard upload tài liệu chọn OCR profile), `/document-types` (Loại văn bản), `/nodes` (Danh mục node), `/tools` (Công cụ & API ngoài), `/evaluation` (Đánh giá chất lượng TM-08).
  - Phân hệ 3 (Hệ thống & Quản trị): `/models` (Mô hình & Provider), `/developer` (Cổng Developer & API keys), `/design-system` (Hệ thống thiết kế UI).
  - Tự động sinh `src/routeTree.gen.ts`.
- Kết nối TanStack Query với các REST API endpoints của Backend FastAPI (`http://localhost:8001/platform/v1alpha1/...`).
- Kiểm thử và xác minh:
  - `npm run lint` (Biome pass 100% 0 lỗi).
  - `npm run typecheck` (TypeScript pass 100% 0 lỗi).
  - `npm run build` (Đóng gói production bundle thành công).

---

## 🧪 6. Tiêu Chuẩn Nghiệm Thu & Đảm Bảo Chất Lượng

1. **Zero Lint & Type Errors**:
   ```bash
   npm run lint       # Biome kiểm tra cú pháp và định dạng 0 lỗi
   npm run typecheck  # TypeScript kiểm tra kiểu dữ liệu 0 lỗi
   npm run build      # Vite biên dịch ra thư mục dist/ thành công
   ```
2. **Trải nghiệm Thẩm mỹ Đạt Chuẩn Gold Standard**:
   - Giao diện sắc nét, chuẩn nhận diện ĐH Quy Nhơn, chuyển đổi Dark/Light mode không bị chớp giật (flash of unstyled content).
   - Sidebar và Command Menu phản hồi ngay lập tức dưới 16ms (60fps).
   - Luồng hỏi đáp AI hiển thị chữ chạy từng token mượt mà, bảng số liệu Facts hiển thị đẹp mắt, dẫn chứng trích dẫn rõ ràng.
