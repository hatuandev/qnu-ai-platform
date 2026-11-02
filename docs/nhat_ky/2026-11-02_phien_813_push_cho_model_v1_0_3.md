# Phiên 813 — Push cấu hình chờ model lên v1.0.3

Người dùng yêu cầu push thay đổi vừa hoàn tất lên v1.0.3. Dùng worktree release riêng, nền f9c3f604 trên Gitea; giữ main v1.0.2 và các thay đổi chưa commit. GitHub tiếp tục hoãn theo lựa chọn806, không sửa lịch sử hoặc force push.

Phạm vi commit: helper provider-setup lưu/kiểm tra wait_for_completion; profile QNU/router khai báo wait=true; regression812 và mock capacity tương thích; hướng dẫn và nhật ký812/813. Không đưa .env, khóa, qnu-mineru-test.http, PDF/OCR, tệp tạm hoặc dữ liệu test vào commit.

Kiểm chứng trên snapshot release: 19 PASS / 3 suites qua Vitest; npm run test:e2e:typecheck exit0; Biome4files exit0; diffcheck và UTF-8/LF đạt. Không rerun model, reindex hoặc restart. Backend wait760 5PASS là kết quả812, không phải chạy lại ở813; full backend không được tuyên bố PASS.

Runtime ModelOps DB được chỉnh ở812 không nằm trong Git. Profile sẽ áp lại khi provider-setup chạy; lượt uncertain cũ không tự gửi lại. HTTP read đã bỏ cutoff300, worker còn30phút như tài liệu812, không coi pipeline vô hạn.

Tại mốc tạo commit này, remote HEAD được kiểm tra là f9c3f604. Push chỉ Gitea refs/heads/v1.0.3 theo fast-forward; hash kết quả và xác minh ls-remote được ghi vào tmp/push813/push-receipt.json sau thao tác và báo trong phản hồi cuối.
