# Phiên 688 — Ẩn mục QNU-KTX trong sidebar V1

Người dùng yêu cầu bỏ khỏi sidebar các menu mẫu QNU-KTX không liên quan QNU AI.
Áp dụng skill frontend/clean code; thay đổi duy nhất ở SidebarBody:
chỉ đưa các nhóm không đánh dấu `template` qua bộ lọc quyền, bỏ nhãn Mẫu không
còn được hiển thị. Nhóm QNU AI và kiểm tra quyền V1 giữ nguyên. Cấu hình, route
mẫu, breadcrumb, command menu và nội dung trang không bị xóa hay thay quyền.
Yêu cầu mới về sidebar có ưu tiên hơn mặc định giữ menu mẫu trong frontend AGENTS.

Kiểm chứng: Biome trên app-sidebar.tsx PASS; `npm run build` gồm TypeScript
được chạy tại frontendV1 (kết quả ghi trong snapshot). Kiểm tra diff/UTF-8/LF;
không sửa auth/backend, cấu hình đang chạy hay thực hiện migration/deploy/Git.
Chưa kiểm tra hình ảnh/thiết bị thật hoặc end-to-end qua trình duyệt.

[Snapshot688](../memory/snapshots/2026-10-28_session_688.md).
