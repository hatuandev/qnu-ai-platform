# Phiên 689 — Lối vào chức năng QNU AI trên sidebar

Người dùng là admin, yêu cầu hiển thị chức năng QNU AI trên sidebar sau khi
ẩn menu KTX. Đối chiếu route thực tế: nhiều chức năng cần workspace, OCR và
Compiler/tìm kiếm/đánh giá cần kho, nên không tự suy workspace/kho hoặc tạo
liên kết tới tài nguyên không được chọn.

Thêm `WorkspaceSidebar` và nối tại `app-sidebar.tsx`: kho/tài liệu, OCR/chính
tả, Compiler/review, tìm kiếm/hỏi đáp, đánh giá, trợ lý, hội thoại, thành viên,
model workspace, quota, audit, tài nguyên/thùng rác, job, backup và cleanup.
Mục cần kho đưa tới danh sách kho với chữ chọn kho; chưa có workspace đưa tới
Workspaces và có hướng dẫn chọn. Khi chọn workspace qua route/detail hoặc
Dashboard, dùng đúng ID và giữ lựa chọn trong bộ nhớ gắn session khi chuyển
trang; hiển thị workspace hiện tại. Đổi session không dùng lựa chọn cũ.
Backend vẫn kiểm workspace/role, không coi sidebar là cấp quyền. Không tạo route
mới hoặc hiển thị chức năng chưa có, giữ nhóm QNU AI và ẩn các nhóm mẫu KTX.

Kiểm chứng thực chạy cwd frontendV1: Biome3tệp PASS; Vitest trọng tâm
`tests/workspace-sidebar-689.test.tsx --maxWorkers=2` 3PASS, kiểm chọn
workspace, route và logout; `npm run build` + TypeScript exit0. Từng có lỗi
Biome trong fixture và lỗi gọi Python do sai cwd, đã sửa rồi chạy lại đạt.
Có cảnh báo Vite/bundle vốn có. Chưa kiểm browser thực, toàn bộ suite hoặc
backend; không thay API/auth, dữ liệu, runtime, migration, deploy hay Git push.

[Snapshot689](../memory/snapshots/2026-10-28_session_689.md).
