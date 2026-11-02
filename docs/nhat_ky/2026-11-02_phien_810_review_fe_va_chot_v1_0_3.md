# Phiên 810 — Review FE và chốt bổ sung v1.0.3

## Phạm vi

User cho phép review FE vừa hoàn tất, kiểm tra rồi commit/push lên Gitea v1.0.3, sau đó kiểm thử thay phiên bản bằng file thật. Dùng worktree riêng `tmp/release-v1.0.3`; main v1.0.2 và các diff có trước giữ nguyên. GitHub tiếp tục hoãn theo xác nhận806 vì lịch sử chứa PDF162.41MiB. Không stage qnu-mineru-test.http, .env, credentials, PDF/DOCX, node_modules, dist hay artifact test.

## Review và sửa

- FE gồm giao diện OCR hai cột resizable, zoom/pan, word diff, gợi ý cần đối chiếu, giữ nháp, chọn model, lịch sử; kèm hai fix809 và bước người dùng chỉnh sửa sau review.
- Phát hiện thêm lỗi zoom: đồng thời đổi width bề mặt ảnh125% và gọi transform zoom làm phóng hai lần, nhãn scale không theo wheel. Regression trước sửa FAIL đúng125%sochuỗirỗng. Sửa chỉ dùng transform để phóng, giữ base fit-width/fit-page; nhãn lấy scale từ onTransform API của thư viện đang cài. Không sửa bbox hoặc văn bản.
- Ghim snapshot30files bằng hash trước kiểm, so với main lại trước stage. Bí mật scan có phạm vi theo mẫu không phát hiện Bearer/key dài; đây không phải audit bảo mật toàn repo.

## Kiểm chứng snapshot

- Full Vitest lượt đầu685PASS/77suites,72.80s. Sau sửa zoom, final686PASS/77suites,64.34s,exit0.
- Build Vite+TypeScript finalexit0, Vite12.82s; cảnh báo chunk>500kB giữ rõ. Không thay assertion để xanh.
- Biome19filesPASS; diffcheckPASS.
- Chromium component thật/source snapshot, mock ảnh/nội dung duy nhất trong tmp/ui810: zoom125% khớp boundingbox thực, offsetWidth không đổi, tỷ lệbbox0.6 giữ;390/1280 sáng/tối4/4không tràn toàn trang. Đã xem desktoplight/mobiledark, preview64810đãdừng. Không phải liveOCR.
- Không rerun BE cho thay đổi FE. Baseline BE806 là693PASS/1FAIL716/77SKIP, không tuyên bố toànBEđạt.

## Git và bước tiếp

Remote Gitea v1.0.3 trướcpush0108536d. Chỉ push Gitea bằng fast-forward, khôngđổi remote/force/history. Kết quả hash push ghi trong tmp/release810/push-receipt.json và báo cáo tiếp theo. Chặng live thay bản chưa chạy tại thời điểm commit này; dịch vụ phiên93faa11f0cafđangtắt, Dockerengine29.8đã sẵn. Sẽ khởi động đúnginfra cũ, dùng collection thử riêng và model thật, không reset dữ liệu hoặc xử lý lại các job cũ ngoài phạm vi.
