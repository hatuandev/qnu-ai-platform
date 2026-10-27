# Phiên650 — Sao chép đầy đủ FE KTX làm frontendV1

Ngày 2026-10-26. Theo lựa chọn người dùng, giữ toàn bộ màn hình KTX và thay nghiệp vụ sau.
Nhập 324 tệp, giữ 78 tệp route, features/layout/menu/component/assets/docs và giấy phép.
Không nhập env/cache/dependency cũ; lockfile giữ nguyên dependency. Chạy cổng3001 riêng.

Thích nghi package/config, thêm thông báo mẫu, giữ demo UI nguồn và chặn mọi fetch
nghiệp vụ qua backendFetch. Auth và export/import riêng cũng đi qua ranh giới này;
không nối KTX/backendV1. Dữ liệu starter chỉ local, trang cần API báo chưa kết nối.

Đã chạy tại frontendV1: npm ci PASS/484gói, npm test 2PASS/0FAIL/0SKIP;
npm run build PASS (gồm TypeScript, có cảnh báo mainchunk667,97kB), Biome17tệp
thích nghi PASS. Lint toàn bộ FAIL56error/12warning/6info; source lint đối chiếu
cũng FAIL39error nhưng khác project context nên chưa phải parity đầy đủ.

Browser kiểm tra design-system/users desktop1440×900 sáng/tối, search1dòng/URL
và reload, mở/hủy form; mobile390×844 menu/rooms và lỗi API rõ, không page overflow.
Chưa nghiệm thu toàn bộ78route, nghiệp vụ KTX hay nối backendV1. Không chạy BE suite,
không sửa source KTX/frontend/BE cũ, migrate/deploy/Git. Giữ server mẫu3001.

[Báo cáo](../bao_cao/context650/IMPORT.md) · [README](../../frontendV1/README.md).
