# Phiên 691 — Nối router sidebar theo chức năng

Người dùng báo bấm sidebar không chuyển tới chức năng. Nguyên nhân: ở phiên689,
nhiều mục trỏ chung về `/workspaces` hoặc danh sách kho; đang ở trang đó thì
bấm không tạo điều hướng hữu ích và không giữ mục người dùng chọn. Test cũ mock
Link chỉ xác nhận props, chưa tái hiện click/router. Sửa theo yêu cầu, giữ các
thay đổi người dùng và sidebar688–690.

Thêm route thực `/workspaces/choose/$feature` thuộc ranh giới V1 và màn chọn
workspace/kho lấy dữ liệu bằng query hiện có, có loading/error/trống/phân trang,
link tạo/quản lý tài nguyên. Sidebar gắn feature, giữ workspace đã chọn theo
session. Route chọn giữ feature và workspace ở URL; sau chọn workspace/kho,
mở đúng đích: OCR→sources, Compiler→compilations, Tìm kiếm→index, Hỏi đáp→
answers, Đánh giá→evaluations; các mục khác tới trang workspace tương ứng,
bao gồm jobs/backups/storage view. OCR cần chọn tiếp nguồn và phiên bản thực tế.
Không tự chọn workspace/kho, không suy cấp quyền: API/server vẫn kiểm actor,
membership và tài nguyên. Các chức năng chưa có UI không được giả thành đã có.

Tách Tìm kiếm/Hỏi đáp; regex nhận workspace không nhầm route `choose` thành ID.
Nhóm QNU AI không đưa các menu KTX trở lại. Test689 cập nhật kỳ vọng theo hành
vi được yêu cầu, không giảm assertions; test691 chạy router TanStack thực với
fixture query, click sidebar→chọn workspace→chọn kho và xác nhận path/tab/đích.

Kiểm chứng thực chạy cwd frontendV1:

- Biome 6tệp thay đổi PASS.
- Test trọng tâm `npm test -- tests/sidebar-navigation-691.test.tsx
  tests/workspace-sidebar-689.test.tsx --maxWorkers=2`:10PASS/0FAIL.
- Full `npm test -- --maxWorkers=2 --reporter=json ...`:358PASS/0FAIL/0SKIP,
  exit0, receipt `storage/artifacts/context691-fe-tests.json`.
- `npm run build` (gồm TypeScript) exit0, log context691-build-verified.log;
  cảnh báo Vite native config/bundle lớn cũ.
- Thử nghiệm đầu dùng import toàn route tree trong test môi trường bị timeout
  2ca; đổi fixture sang route thật và memory router nhỏ, không tăng timeout,
  chạy lại đạt. ScrollTo jsdom được stub ở fixture. Test không chứng minh browser
  hoặc API thật đã được nghiệm thu; các route destination là fixture trong test.
- UTF-8 không BOM/LF, link docs, diff scoped kiểm cuối; routeTree do Vite sinh,
  không sửa tay. Không chạy BE/model, không sửa quyền, không reindex/migration/
  restart/deploy hoặc push. Chưa kiểm giao diện thật trên thiết bị.

Người dùng có thể tải lại FE để Vite nạp route mới; nếu chưa có workspace/kho,
tạo hoặc chọn tương ứng. OCR cần chọn thêm nguồn, không giả định nguồn bất kỳ.

[Snapshot691](../memory/snapshots/2026-10-28_session_691.md).
