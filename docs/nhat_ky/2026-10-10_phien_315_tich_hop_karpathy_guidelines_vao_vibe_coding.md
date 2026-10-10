# Phiên 315 — Tích Hợp Karpathy Guidelines Vào Vibe Coding

## Mục tiêu

Tích hợp các nguyên tắc từ `multica-ai/andrej-karpathy-skills` vào quy tắc Agent và skill Clean Code hiện có của QNU AI Platform, đồng thời tối ưu nhịp làm việc để AI coding nhanh hơn mà vẫn bảo vệ các thay đổi rủi ro cao.

## Thay đổi

| Tệp | Hành động | Nội dung |
| :--- | :--- | :--- |
| `AGENTS.md` | Cập nhật | Bổ sung Karpathy-Inspired Fast Coding Loop, Surgical Changes và chiến lược kiểm thử theo rủi ro |
| `.agents/skills/qnu-clean-code-architect/SKILL.md` | Cập nhật | Mở rộng skill cho coding/review/refactor thường ngày; thêm ba chế độ test-first, code-theo-lô và chỉnh nhanh |
| `.agents/skills/qnu-clean-code-architect/agents/openai.yaml` | Cập nhật | Cho phép implicit invocation và bổ sung metadata hiển thị |
| `docs/memory/PROJECT_CONTEXT.md` | Cập nhật | Ghi nhận quy tắc Vibe Coding mới |
| `docs/memory/snapshots/2026-10-10_session_248.md` | Tạo mới | Snapshot phiên tích hợp skill |
| `docs/nhat_ky/README.md` | Cập nhật | Thêm phiên 315 vào mục lục |
| `docs/WORK_LOG.md` | Cập nhật | Thêm tiến trình phiên 315 |

## Quyết định cốt lõi

1. Không tạo skill mới trùng lặp; cập nhật `qnu-clean-code-architect` hiện có.
2. Test-first chỉ bắt buộc cho lỗi rủi ro cao: dữ liệu, transaction, concurrency, idempotency, migration, auth/RBAC, tenant isolation và thanh toán.
3. Tính năng thông thường được sửa theo một batch rồi test một lần ở cuối.
4. Thay đổi UI hoặc nội dung đơn giản chỉ cần lint/build tương ứng nếu không đổi logic.
5. Thay Boy Scout Rule mở rộng bằng Surgical Change Rule để tránh AI tự ý refactor ngoài phạm vi.
6. Final verification theo quy định Backend/Frontend vẫn bắt buộc; tối ưu tốc độ không đồng nghĩa bỏ kiểm chứng.

## Kiểm tra

- `quick_validate.py .agents/skills/qnu-clean-code-architect`: đạt — `Skill is valid!`.
- Đã kiểm tra diff giới hạn đúng Agent, skill và tài liệu phiên.
- Không chạy backend/frontend application tests vì phiên này không thay đổi mã nguồn runtime.

## Bài học

Vibe Coding nhanh nhất khi mức độ kiểm thử tỷ lệ với rủi ro. Bắt mọi thay đổi đi qua cùng một quy trình nặng làm chậm phản hồi, trong khi bỏ test ở các invariant dữ liệu quan trọng lại làm tăng chi phí sửa lỗi. Phân loại rủi ro trước khi triển khai giúp cân bằng tốc độ và độ tin cậy.
