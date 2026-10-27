# Context650 — Sao chép FE QNU-KTX thành frontendV1

Ngày 2026-10-26. Người dùng chọn **giữ toàn bộ màn hình KTX làm mẫu, thay nghiệp vụ sau**.

## Kết quả

- Nhập 324 tệp từ `D:/DuAnPhanMem/QLKTX/qnu-ktx/src/Web/ClientApp`;
  giữ đủ 78 tệp route và toàn bộ features, navigation, layout, public assets, tài liệu,
  LICENSE/THIRD_PARTY_NOTICES. Không đổi menu nghiệp vụ sang QNU AI.
- React 19 / Vite 8 / TypeScript / Tailwind 4 / TanStack / Radix theo lockfile nguồn.
  Dependency entries không đổi; metadata package đổi thành `qnu-ai-platform-frontend-v1`.
- Chạy riêng loopback cổng 3001. Bỏ cấu hình Aspire/proxy/BFF của KTX;
  không nhập `.env.local`, node_modules, dist, cache, IDE hoặc lịch sử Git.
- Dùng chế độ demo có sẵn trong source, có thông báo mẫu trên trang. `backendFetch`
  chặn GET/POST/PUT/PATCH/DELETE và upload/download trước khi gọi mạng, gồm cả fetch
  riêng trong auth, import hồ sơ và xuất hóa đơn. Không nối API KTX hoặc backendV1.
- Chỉ dữ liệu mẫu sẵn có của starter (users/roles/design-system) có thể thao tác local.
  Các màn hình cần API giữ UI và hiển thị lỗi chưa kết nối; không thay bằng dữ liệu giả.
- Giữ định dạng UTF-8 không BOM/LF, Biome parser cho Tailwind 4. Chạy safe formatter
  trên riêng thư mục mới; không sửa nghiệp vụ nguồn chỉ để làm xanh lint.

## Kiểm chứng đã chạy

| Kiểm tra | Kết quả |
|---|---|
| `npm ci --ignore-scripts --no-audit --no-fund --cache .npm-cache` | PASS, 484 packages; trước đó thử offline thiếu cache và lần quyền hạn chế lỗi DNS |
| `npm test` | PASS, 2/2, 0 fail/skip; chặn fetch mọi method và file, quét toàn bộ direct fetch sites |
| `npm run build` | PASS exit 0, gồm Vite và TypeScript; một cảnh báo chunk chính 667,97 kB |
| `npm run typecheck` riêng | PASS exit 0 (lần quyền hạn chế bị kẹt đã dừng; chạy lại có quyền cần thiết) |
| Biome trên 17 tệp thích nghi/config/test | PASS exit 0 |
| `npm run lint -- --max-diagnostics=0` | **FAIL exit 1**, 56 error / 12 warning / 6 info trong mã được nhập |
| Lint source/snapshot đối chiếu | FAIL, 39 error; số liệu bên ngoài project không phải baseline parity tương đương, không tuyên bố toàn bộ lint không regression |
| Browser desktop 1440×900 | `/design-system`, `/users` tải được; tìm Alex còn 1 dòng, URL giữ khi reload; mở/hủy form mời; sáng/tối hoạt động |
| Browser mobile 390×844 | Menu Sheet mở, chuyển `/rooms` đóng menu; trạng thái lỗi API rõ; không cuộn ngang toàn trang ở các trang đã kiểm tra |
| Console tại các lượt kiểm tra | Không có error/warn được ghi nhận |

Cwd kiểm tra ứng dụng: `frontendV1`. Chưa chạy backend suite vì không đổi BE.
Không nghiệm thu toàn bộ 78 routes hay luồng KTX end-to-end. Build không chứng minh
mọi màn hình, quyền hoặc nghiệp vụ đã chạy thật. Các lỗi lint cần xử lý ở đợt riêng.

## Bảo toàn và giới hạn

Manifest/hash kiểm tra repo nguồn không đổi, đủ bộ route, không nâng dependency;
1.902 tệp code/config/docs trong frontend/backend/backendV1 có seal đầu phiên.
Chi tiết kiểm chứng và screenshot local ở `tmp/context650/` (ignored).

Không migrate, sửa DB/cấu hình đang chạy, restart dịch vụ cũ, deploy, commit/push.
Máy chủ frontendV1 mới trên 3001 được giữ để người dùng xem mẫu.

Khi chuyển nghiệp vụ: bắt đầu auth/workspace theo contract backendV1, rồi ModelOps,
tri thức và trợ lý. Thay đồng bộ backend-fetch/runtime/claim mapping trước khi nối API;
role demo và permission `ktx.*` không được dùng để cấp quyền workspace thật.

Xem [README frontendV1](../../../frontendV1/README.md).
