# Nhật ký669 — Review chức năng frontendV1

- Ngày: 2026-10-27, Asia/Bangkok.
- Yêu cầu: review những chức năng FE đã triển khai, trong khi người dùng tiếp tục phát triển FE.
- Áp dụng qnu-frontend-architect, qnu-clean-code-architect và admin-frontend-design; đọc AGENTS gốc/frontendV1, PROJECT_CONTEXT, verification và workflow/memory.
- Phạm vi: các phần QNU đã có đến Compiler. Source frontendV1 chưa được Git track; đọc file thực tế, không dùng Git diff làm bằng chứng duy nhất. Giữ toàn bộ thay đổi người dùng.
- Kết luận: **CHANGES REQUESTED**, 7 nhóm lỗi; ưu tiên bản nháp Compiler bị giữ khi chuyển lượt (P1). Ba nút tải thiếu client, chat quá 50 lượt, React key theo nội dung, cache invalidation, auto-review và runner test đều cần sửa.

## Kiểm chứng

- `npm test` trong frontendV1: exit 1, 42 PASS/6 tệp FAIL khởi chạy/0 SKIP; alias và TSX không nạp được bằng runner đã cấu hình.
- `npm run build`: exit 0 PASS, có TypeScript; cảnh báo chunk >500kB. Kết quả trước các tệp publication được viết đồng thời, không nghiệm thu các tệp mới đó.
- `npm run lint`: exit 1 FAIL, 64 errors/14 warnings/6 infos, 450 tệp. Có lỗi mẫu cũ và lỗi QNU mới.
- Biome 96 tệp API/auth/QNU features: exit 1 FAIL, 5 errors/2 warnings trong trang chi tiết Compiler.
- `node storage/artifacts/context668-fe-review/probes.cjs`: exit 1, 7 probes FAIL đúng lỗi, dùng handler/hook thật và dữ liệu trong bộ nhớ; QueryClient thật cho invalidation. Không gọi API/AI hay ghi dữ liệu. Lượt R1 đầu sai selector raw, chỉnh harness rồi tái hiện lỗi client; không đổi app.
- Browser: cổng mặc định3001 không chạy; mở Vite thử riêng3009, trang đăng nhập hiển thị. Backend8002 không chạy; các màn sau đăng nhập/SSO thật/layout mobile/dark chưa nghiệm thu. Phiên bị ngắt có chủ ý; kiểm tra lại không còn listener3009 hoặc process Node của lượt thử.
- Chưa sửa source app, chưa migrate/restart/deploy hay thay provider. Publication đang được viết đồng thời chưa review.

## Bàn giao

- [Báo cáo chi tiết](../bao_cao/context669/REVIEW.md).
- [Kết quả và hash nguồn](../bao_cao/context669/verification.json).
- [Snapshot669](../memory/snapshots/2026-10-27_session_669.md).
- Artifact harness trong storage/artifacts/context668-fe-review bị Git ignore; tên folder668 đã dùng trước khi dành số669 cho báo cáo để tránh phiên FE đồng thời.
- Đề xuất sửa các finding rồi kiểm tra luồng FE→BE bằng phiên đăng nhập thật. Không kết luận số test lịch sử Context665/667 là trạng thái test hiện tại.
