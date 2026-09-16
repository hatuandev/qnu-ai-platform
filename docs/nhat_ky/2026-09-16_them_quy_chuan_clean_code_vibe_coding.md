# Nhật Ký Phát Triển: Tích Hợp Năng Lực & Quy Chuẩn Clean Code Khi Vibe Coding Cho AI Agent

- **Thời gian**: 21:50 - 22:00, Thứ Tư, 16/09/2026 (UTC+7)
- **Tác giả**: Senior Full-Stack Architect & Enterprise AI Systems Specialist
- **Mục tiêu**: Bổ sung tư duy và quy chuẩn Clean Code khi thực hiện Vibe Coding cho toàn bộ AI Agent trong dự án `qnu-ai-platform`.

---

## 1. Bối Cảnh & Đặt Vấn Đề

"Vibe Coding" là phong cách lập trình tốc độ cao dựa trên trí tuệ nhân tạo, cho phép hiện thực hóa ý tưởng nhanh chóng. Tuy nhiên, nếu thiếu kỷ luật, Vibe Coding dễ để lại rác kỹ thuật:
- Mã cũ bị comment-out thay vì xóa bỏ.
- Debug log sót lại (`console.log`, `print`).
- Ép kiểu bừa bãi (`as any`) làm suy yếu hệ thống type của TypeScript.
- Đặt tên cẩu thả (`temp`, `data1`, `val`).
- Nuốt lỗi âm thầm (`catch (e) {}`).
- Vi phạm Single Responsibility khiến component/function phình to mất kiểm soát.

---

## 2. Các Thay Đổi Kỹ Thuật Đã Thực Hiện

### 2.1. Cập nhật `AGENTS.md` (Hiến pháp Dự Án)
- **Tệp tin**: [`AGENTS.md`](file:///d:/DuAnPhanMem/qnu-ai-platform/AGENTS.md)
- **Nội dung bổ sung**:
  - **Mục 8: Quy Chuẩn Clean Code Bắt Buộc Khi Vibe Coding** gồm 8 điều răn bắt buộc:
    1. *The Boy Scout Rule*: "Luôn để codebase sạch hơn lúc bạn tìm thấy nó."
    2. *Zero Dead Code & Zero Debug Junk*: Cấm tuyệt đối comment-out code cũ và debug rác.
    3. *An Toàn Kiểu Dữ Liệu Tuyệt Đối*: Cấm dùng `any` hoặc `as any`; 100% Type Hints trên Backend.
    4. *Đặt Tên Tự Giải Thích*: Boolean bắt đầu bằng `is/has/should/can`, function dùng động từ, cấm viết tắt vô nghĩa.
    5. *Đơn Trách Nhiệm & Hàm Nhỏ Gọn*: Hàm < 40 dòng, tách logic tính toán khỏi thân JSX.
    6. *Mẫu Trả Về Sớm (Early Return / Guard Clauses)*: Triệt tiêu cấu trúc lồng ghép `if-else` đa tầng.
    7. *Không Nuốt Lỗi Âm Thầm*: Cấm `catch` rỗng; luôn có fallback an toàn, toast hoặc structured log.
    8. *Vòng Lặp Tự Làm Sạch Tự Động (Clean-As-You-Go Loop)*: Tự động chạy `npm run lint`, `npm run typecheck`, `uv run ruff check .` đạt 0 lỗi trước khi trả kết quả.

### 2.2. Xây dựng Skill Mới: `qnu-clean-code-architect`
- **Tệp tin**: [`.agents/skills/qnu-clean-code-architect/SKILL.md`](file:///d:/DuAnPhanMem/qnu-ai-platform/.agents/skills/qnu-clean-code-architect/SKILL.md)
- **Nội dung**:
  - Triết lý Speed + Craftsmanship.
  - Chuẩn mực Frontend (React 19 + TypeScript + Biome + Tailwind v4 OKLCH Tokens).
  - Chuẩn mực Backend (FastAPI + Python 3.14 + Pydantic v2 + SQLAlchemy Async).
  - Bảng tra cứu Anti-Patterns và cách sửa chuẩn Clean Code.
  - Checklist tự kiểm toán 5 bước trước mỗi lượt hoàn tất.

### 2.3. Cập nhật Bảng Tổng Hợp Kỹ Năng
- Cập nhật danh mục kỹ năng hệ thống từ 06 lên **07 kỹ năng** tại `AGENTS.md` và `docs/memory/PROJECT_CONTEXT.md`.

---

## 3. Kết Quả Kiểm Tra Tĩnh (Static Verification)

```bash
# Frontend Linter
npm run lint
# Output: Checked 61 files in 81ms. No fixes applied. (0 errors)

# Frontend Typecheck
npm run typecheck
# Output: tsc --noEmit (0 errors)

# Backend Linter
uv run ruff check .
# Output: All checks passed! (0 errors)
```
