# Phiên 712 — URL theo mã workspace và sidebar

Ngày: 2026-10-29. Phạm vi: frontendV1 và endpoint tra cứu chỉ đọc trong backendV1.

## Yêu cầu và kết quả

Người dùng chốt chọn workspace tại header; URL không cần /w/ và không lặp collection trong link nguồn. Dùng mã workspace hiện có (ví dụ cong-tac-sinh-vien), không đổi mã hay migrate dữ liệu.

- URL công khai /:code/knowledge và /:code/files/:sourceId; giữ query runId/page/hash.
- TanStack route mask giữ các route nội bộ đã gõ kiểu. Link cũ tự rút gọn bằng replace; link ngắn mới/F5 tra cứu qua BE rồi mở đúng trang. history state workspacePath buộc router commit khi chỉ đổi mask trên cùng href; không lưu token/quyền.
- Header không tự gán workspace đầu tiên khi chưa chọn; đổi workspace bỏ source/run/revision cũ, về danh sách của workspace mới. Quản lý workspace nằm trong dropdown của admin, bỏ mục trùng trong sidebar.
- Trang chi tiết nguồn active Kho tri thức; breadcrumb dùng cùng bộ nhận diện.
- BE GET /workspaces/resolve-route?code=...&source_id=... tra workspace qua resolve_workspace_access trước khi tìm nguồn theo workspace. load_collection/load_source giữ lifecycle guard. Workspace không được phép trả404; suspended trả403. Không có dữ liệu nguồn trong phản hồi lỗi.
- Các mã trùng tên route hệ thống giữ link dài tương thích; không tự đổi mã đang dùng.

## File chính

- backendV1/qnu/domains/workspaces/navigation.py, router.py; tests/unit/test_workspace_navigation_712.py.
- frontendV1/src/navigation/workspace-links.ts, workspace-features.ts, utils.ts, config.ts.
- frontendV1/src/features/workspaces/workspace-link-bridge.tsx; routes/$workspaceCode.$.tsx; layouts/admin-shell.tsx, workspace-switcher.tsx; app/api/v1/endpoints.ts (chỉ thêm nhận diện route ngắn).
- Hai test workspace-links-712 và workspace-link-router-712. Route tree được Vite sinh tự động, không sửa tay.

## Kiểm chứng thực chạy

- FE npm test -- --maxWorkers=2: 465PASS/53file, exit0. Regression real router gồm link cũ và link ngắn mới, giữ runId/page; targeted19PASS sau sửa boundary.
- FE npm run build (vite + tsc) và typecheck: PASS/exit0. Biome11file của phạm vi: PASS. Full lint FAIL28error ngoài file sửa (folder/modelops/shared UI); không sửa lan. Log storage/artifacts/workspace-links-lint-full.log.
- BE Ruff/format các file sửa đạt. Full pytest trên mã cuối: 338PASS/60SKIP; các integration cần TEST_DATABASE_URL chưa chạy, không nghiệm thu DB thật. Dùng basetemp riêng trong storage/artifacts sau lần đầu lỗi quyền thư mục Temp (313PASS/60SKIP/23ERROR); lần thử test âm có1FAIL do mock scalars().first chưa thiết lập, sửa fixture rồi chạy lại, không đổi assertion/guard. Một lần gọi từ root repo ghi335PASS/3FAIL/60SKIP do các subprocess migration/recovery cần cwd backendV1; chạy lại đúng cwd và basetemp mới để xác nhận gate cuối.
- HTTP regression qua router với DB fake kiểm tra guard thật: non-member404/suspended403, không tiếp tục lookup nguồn. Chưa test qua PostgreSQL thật.
- Browser dữ liệu đang có: link cũ → link ngắn, F5 mở đúng nguồn/run, Kho tri thức aria-current=page; chọn shl về /shl/knowledge (kho trống), không còn runId nguồn cũ; Back quay đúng tài liệu và breadcrumb.
- Không upload/xóa/bóc tách/gọi model trong kiểm tra này. Ảnh chứng cứ local storage/artifacts/workspace-navigation-712.png, không đưa tài liệu vào Git.

## Runtime và giới hạn

Người dùng xác nhận riêng khởi động lại V1. Đã kiểm PID runner9260 đúng repo và dừng cây tiến trình, chạy lại runner v1-dev ẩn (PID28344), API8002/worker/FE3001 hoạt động. Việc này nạp cả thay đổi OCR/Gotenberg từ phiên khác; không nhận các thay đổi đó là phần triển khai712. Giữ mọi diff đồng thời; không migrate, seed, thay model/grant/quota, push hoặc commit. Các test cũ được chạy lại với môi trường thiếu DB test nên phần integration vẫn NOT RUN.

Xem [quy trình](../quy_trinh/44_dieu_huong_workspace_v1.md).
