# Nhật Ký Phiên Làm Việc #118 — Triển Khai Giai Đoạn 8: Assistant Workspace Deep Modularization & Monolithic Page Decomposition

- **Thời gian**: 2026-09-19 18:20 (Giờ địa phương)
- **Mục tiêu chính**: Phân rã triệt để trang "quái vật" [assistant-detail-page.tsx](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/pages/assistant-detail-page.tsx) (1.745 dòng) thành các feature sections và dialogs nhỏ có trách nhiệm đơn nhất (SRP), đạt chuẩn Clean Code (Mục 8 AGENTS.md), Semantic & Accessibility (P0.4), Typography (P1.4).

---

## 1. Bối Cảnh & Lý Do Kỹ Thuật

Trước Giai đoạn 8, tệp `assistant-detail-page.tsx` là tệp lớn nhất frontend (1.745 dòng), vi phạm nguyên tắc "Zero Big-Ball-of-Mud" khi nhồi nhét:
- Toàn bộ form 7 lớp cấu hình vòng đời AI Assistant.
- Cổng kiểm định 5 lớp sẵn sàng xuất bản (Publish Gate).
- Strip chỉ số KPI thời gian thực.
- 3 Dialogs lớn (Clone Assistant, Embed Widget, Version History & Rollback).
- Logic điều hướng 6 sub-views (`overview`, `playground`, `workflow`, `channels`, `quality`, `runs`).

## 2. Các Thay Đổi Kỹ Thuật Chi Tiết

### 2.1. Phân Rã Thành Các Module Feature Chuyên Biệt
1. [types.ts](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/components/assistants/types.ts): Định nghĩa kiểu dữ liệu dùng chung cho form chỉnh sửa (`AssistantEditForm`), danh sách gợi ý (`SampleQuestionItem`), và hằng số phân loại chuyên môn (`CATEGORY_OPTIONS`).
2. [assistant-header.tsx](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/components/assistants/assistant-header.tsx): Quản lý Hero Header, Status Badges, Action Toolbar đa nhiệm, Strip KPI thời gian thực và Banner cổng kiểm định 5 tiêu chí xuất bản (Publish Gate).
3. [assistant-persona-section.tsx](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/components/assistants/sections/assistant-persona-section.tsx): Tầng 1 (Persona, Scope, System Prompt kèm tính năng AI tự động viết prompt, danh sách câu hỏi gợi ý tương tác).
4. [assistant-model-section.tsx](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/components/assistants/sections/assistant-model-section.tsx): Tầng 3 (ModelOps: Chọn Primary/Fallback model từ danh sách nhà cung cấp thật, tinh chỉnh Temperature và Max Tokens).
5. [assistant-knowledge-section.tsx](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/components/assistants/sections/assistant-knowledge-section.tsx): Tầng 2 (Liên kết Kho tri thức RAG, deep link tới chi tiết kho, khuyến nghị chiến lược Chunking).
6. [assistant-tools-section.tsx](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/components/assistants/sections/assistant-tools-section.tsx): Tầng 5 & 6 (Liên kết Workflow DAG, deep link mở DAG Studio, cơ chế kiểm soát Human-in-the-loop HITL).
7. [assistant-guardrails-section.tsx](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/components/assistants/sections/assistant-guardrails-section.tsx): Tầng 4 & 7 (6 chốt an toàn Guardrails, No-Answer Policy, Panel chỉ số chuẩn Ragas TM-08).
8. [assistant-danger-zone.tsx](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/components/assistants/sections/assistant-danger-zone.tsx): Card kích hoạt lại / vô hiệu hóa trợ lý với dialog xác nhận 2 bước an toàn.
9. [assistant-clone-dialog.tsx](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/components/assistants/dialogs/assistant-clone-dialog.tsx): Hộp thoại nhân bản trợ lý chuyên trách 1-click.
10. [assistant-embed-dialog.tsx](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/components/assistants/dialogs/assistant-embed-dialog.tsx): Hộp thoại cung cấp mã nhúng Web Chat Widget vào cổng thông tin trường.
11. [assistant-version-history-dialog.tsx](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/components/assistants/dialogs/assistant-version-history-dialog.tsx): Hộp thoại xem lịch sử snapshot và rollback cấu hình.

### 2.2. Tái Cấu Trúc Orchestrator Page
- [assistant-detail-page.tsx](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/pages/assistant-detail-page.tsx): Giảm từ **1.745 dòng xuống còn ~550 dòng** (giảm gần 70% dung lượng tệp), giữ vai trò điều phối state cấp cao, data fetching và sub-view routing.

### 2.3. Chuẩn Hóa Typography & Accessibility
- Loại bỏ hoàn toàn `text-[9px]`, `text-[10px]` ở các vùng dữ liệu quản trị, chuẩn hóa thành `text-xs` (12px) hoặc `text-sm` (14px).
- Bổ sung đầy đủ `aria-label` cho các công tắc Switch Guardrails.
- Toàn bộ vùng tương tác sử dụng `<button>` chuẩn semantic kèm focus ring.

### 2.4. Boy Scout Rule Dọn Dẹp Backend Ruff
- Khắc phục 10 lỗi cảnh báo Ruff E741 (biến `l` mơ hồ) và E402 (import thứ tự) trong `openai_adapter.py`, `layout_detector.py`, `service.py`, `conftest.py`, `test_auth.py`.

---

## 3. Kết Quả Kiểm Thử (Verification)

| Công cụ kiểm thử | Lệnh thực thi | Kết quả | Ghi chú |
| :--- | :--- | :--- | :--- |
| **Biome Linter** | `npm run lint` | ✅ **0 lỗi** | Đã format và check toàn bộ `src/` |
| **TypeScript Typecheck** | `npm run typecheck` | ✅ **0 lỗi** | `tsc --noEmit` hoàn tất chuẩn xác |
| **Vite Production Build** | `npm run build` | ✅ **Thành công (8.23s)** | Đóng gói bundle sạch sẽ |
| **Zero Mojibake** | `python scripts/check_mojibake.py` | ✅ **302/302 files sạch** | 100% UTF-8 không lỗi vỡ font |
| **Backend Ruff Linter** | `uv run ruff check .` | ✅ **0 lỗi** | All checks passed |
| **Backend Test Suite** | `uv run --extra dev pytest -q` | ✅ **232/232 passed (50.52s)** | 100% test suite đạt chuẩn |
