# NHẬT KÝ LÀM VIỆC — THIẾT LẬP SKILL FRONTEND & QUY TẮC UI RULES VÀO HỆ THỐNG AGENT

> **Thời gian**: 2026-09-15 22:15 (UTC+7)  
> **Kỹ sư / Agent**: AI Senior Full-Stack Architect & Enterprise AI Systems Specialist  
> **Nhiệm vụ**: Xem lại toàn diện mã nguồn Frontend (`frontend/`), khởi tạo bộ Skill chuyên trách Frontend (`qnu-frontend-architect`), và cập nhật toàn bộ quy chuẩn UI/UX vào `AGENTS.md`.

---

## 1. Bối Cảnh & Mục Tiêu

Dự án đã hoàn thành toàn diện 8/8 giai đoạn Backend và 5/5 giai đoạn Frontend. Để đảm bảo mọi AI Agent và kỹ sư tham gia dự án trong tương lai luôn tuân thủ nghiêm ngặt chuẩn thiết kế của Trường Đại học Quy Nhơn (chuẩn hóa từ `qnu-ktx`), chúng ta cần:
1. Soát xét lại toàn bộ kiến trúc và các quy chuẩn Frontend hiện có (`components/ui`, `components/admin`, `components/ai`, `layouts`, `pages`, `services`).
2. Đóng gói bộ kỹ năng chuẩn **`qnu-frontend-architect`** đặt tại `.agents/skills/qnu-frontend-architect/SKILL.md`.
3. Cập nhật tài liệu chỉ đạo tối cao [**`AGENTS.md`**](../../AGENTS.md) để bắt buộc mọi Agent tuân thủ các quy tắc UI, không gian màu OKLCH, kiến trúc 3 tầng components, và các quy tắc tránh lỗi linter Biome.

---

## 2. Các Thay Đổi Kỹ Thuật (Key Changes)

### 2.1. Khởi Tạo Skill `qnu-frontend-architect`
- **Tệp tin**: [`.agents/skills/qnu-frontend-architect/SKILL.md`](../../.agents/skills/qnu-frontend-architect/SKILL.md)
- **Nội dung bao hàm**:
  - **Tôn chỉ thiết kế & Nhận diện QNU**: Academic Teal `--primary: oklch(0.46 0.13 160)`, Dark Mode first-class, cấm hardcode màu thô (`bg-white`, `text-black`).
  - **Kiến trúc 3 Tầng Components**:
    - Tầng 1: Primitives (`src/components/ui/`) — 21 thành phần Radix + shadcn.
    - Tầng 2: Admin Helpers (`src/components/admin/`) — 6 thành phần tái sử dụng (`empty-state`, `kpi-metric`, `status-badge`, `file-upload`, `confirm-dialog`, `field`).
    - Tầng 3: AI Suite (`src/components/ai/`) — 7 thành phần chuyên trách AI (`chat-message`, `chat-bubble`, `message-scroller`, `citation-sheet`, `attachment`, `questionnaire-card`, `dag-canvas`).
  - **Quy chuẩn Token Thiết Kế**: Radius micro (4px), control (6px), surface (8px); Chiều cao điều khiển `h-9` (36px), `h-8` (32px), table row `h-11` (44px), topbar `h-14` (56px).
  - **Quy tắc Biome Linter Gotchas**: Không dùng `0.000` (dùng `0` hoặc `0.0`), không dùng `key={idx}` trong mảng, `<label>` phải có `htmlFor` hoặc dùng `<span>`, không dùng `role="user"` / `role="assistant"` trên DOM.
  - **Quản lý State & API**: TanStack Query v5 cache keys, cơ chế Offline Seed Fallback.
  - **Chuẩn AI UX & Streaming**: SSE event handling, auto-scroll protection, CitationSheet anti-hallucination.
  - **Bộ 3 lệnh nghiệm thu**: `npm run lint`, `npm run typecheck`, `npm run build`.

### 2.2. Cập Nhật Chỉ Đạo Tối Cao `AGENTS.md`
- **Tệp tin**: [`AGENTS.md`](../../AGENTS.md)
- **Nội dung bổ sung**:
  - Cập nhật vai trò thành: **Senior Full-Stack Architect & Enterprise AI Systems Specialist**.
  - Bổ sung tôn chỉ thứ 4: **UI/UX Gold Standard & Zero Lint Errors**.
  - Thêm **Mục 4: Các Quy Tắc Frontend & UI/UX Cốt Lõi (Tuân Thủ Skill `qnu-frontend-architect`)**.
  - Bổ sung **Mục 5: Danh Mục Kỹ Năng Hệ Thống (Skills Registry)** với 6 skills đầy đủ của dự án.
  - Cập nhật quy tắc kiểm thử trong Work Log Policy và Memory Policy bao gồm cả Backend (`uv run ruff check .`, `uv run --extra dev pytest -v`) và Frontend (`npm run lint`, `npm run typecheck`, `npm run build`).

---

## 3. Kết Quả Kiểm Thử (Verification)

### 3.1. Frontend Quality Checks
```bash
# 1. Biome Linter
npm run lint
# Output: Checked 58 files in 47ms. No fixes applied. (0 errors)

# 2. TypeScript Typecheck
npm run typecheck
# Output: tsc --noEmit (0 errors)

# 3. Production Build
npm run build
# Output:
# ✓ 2474 modules transformed.
# dist/index.html                     1.48 kB │ gzip:   0.82 kB
# dist/assets/index-BwoKqK82.css     78.60 kB │ gzip:  12.97 kB
# dist/assets/index-DLi6Epmm.js   1,010.57 kB │ gzip: 303.75 kB
# ✓ built in 7.54s
```

### 3.2. Backend Quality Checks
```bash
# 1. Ruff Linter
uv run ruff check .
# Output: All checks passed! (0 errors)

# 2. Pytest Suite
uv run --extra dev pytest
# Output: 68 passed, 3 warnings in 5.33s (100% pass)
```

---

## 4. Kết Luận

Hệ thống Agent giờ đây đã được trang bị đầy đủ skill Frontend chuyên sâu cùng các quy tắc UI/UX bắt buộc, bảo đảm chất lượng đồng nhất từ Backend đến Frontend cho nền tảng QNU AI Platform.
