# Phiên 690 — Sắp xếp và rút gọn sidebar

Người dùng gửi ảnh sidebar và yêu cầu sắp xếp menu, rút ngắn nhãn. Trong
`frontendV1/src/layouts/workspace-sidebar.tsx`, nhóm các lối vào hiện có theo
Tri thức, Trợ lý và Quản trị & vận hành; giữ chỉ dẫn chọn workspace và ID đang
chọn. Nhãn dài được rút gọn (OCR & chính tả, Biên soạn, Tìm kiếm & hỏi đáp,
Hạn mức, Tác vụ...), giữ nguyên từng route, search view và quyền backend.
Chọn workspace trước, các tác vụ tài liệu vẫn cần chọn kho như phiên689.

Cập nhật cùng test sidebar hiện có theo nhãn và nhóm, giữ kiểm tra chọn scope,
view sao lưu và trạng thái chưa đăng nhập. Cwd frontendV1: Biome2tệp PASS,
Vitest trọng tâm 3PASS/0FAIL/0SKIP, `npm run build` gồm TypeScript PASS exit0;
log build `storage/artifacts/context690-sidebar-build.log`, cảnh báo Vite/bundle
cũ. Kiểm tra UTF-8 không BOM/LF, link docs và diff. Không test browser trực tiếp
hoặc full suite, không sửa API/auth, restart, migration, deploy hay push.

[Snapshot690](../memory/snapshots/2026-10-28_session_690.md).
