# Phiên 684 — Đồng bộ nhánh v1.0.2 lên Gitea

## Yêu cầu và chỉ dẫn cuối

Người dùng yêu cầu push code thành nhánh `v1.0.2`. Sau khi Gitea nhận nhánh,
người dùng xác nhận chỉ cần Gitea, không cần GitHub. Chỉ dẫn này được ưu tiên
cho lần đồng bộ hiện tại; giữ nguyên cấu hình remote, không gửi lại GitHub.

## Kết quả mã nguồn

- Tạo nhánh đúng tên từ `v1.0.1`, giữ thay đổi có sẵn trong workspace.
- Fetch Gitea đạt; kiểm tra trước cho thấy nhánh mới chưa có trên hai remote.
- Commit `e112ac5e20d9669f4c165b09482792a3aaeae7aa`, thông điệp
  `feat: release QNU AI Platform v1.0.2`: 1394 tệp, 220296 dòng thêm/220 dòng xóa.
- Bao gồm BE/FE V1, mã và test legacy đã thay đổi thực, tài liệu/memory và sơ đồ.
  Bỏ thay đổi chỉ khác xuống dòng cùng tệp tạm `.workbuddy-ai/`, `tmp/`.
- `git push --set-upstream gitea v1.0.2:refs/heads/v1.0.2` exit0.
  `git ls-remote --heads gitea refs/heads/v1.0.2` xác nhận đúng commit trên.
- Lệnh push GitHub đã được khởi chạy trước chỉ dẫn cuối của người dùng.
  Sau chỉ dẫn mới, gửi Ctrl+C; tiến trình kết thúc exit1. Không gửi lại,
  không xác nhận trạng thái nhánh GitHub và không xóa nhánh remote nào.

## Kiểm tra và giới hạn

Cwd gốc repo. Đọc security/Git, workflow/memory, PROJECT_CONTEXT và diff thật.
Index ban đầu không có thay đổi staged. Staging dùng danh sách tệp cụ thể,
đối chiếu danh sách index và hash trước/sau, không dùng `git add .`.

- Quét pattern credential trên phần thêm mới và ZIP migration, sau đó kiểm lại
  diff staged: 29 điểm khớp đều là fixture kiểm thử, nhãn form hoặc placeholder
  tài liệu đã đối chiếu. Không phát hiện credential thật theo bộ pattern này;
  đây không phải bảo đảm tuyệt đối hay kết quả gitleaks/trufflehog.
- Không đưa `.env` thật, storage, node_modules, môi trường Python, dist, cache,
  báo cáo chạy thử hoặc dữ liệu PDF/DOCX gốc vào commit. Không có tệp mới >500KB.
  ZIP20KB là mã migration lịch sử, PNG là sơ đồ đã tạo và logo giao diện.
- `git diff --cached --check` **FAIL**, exit2: 703 điểm trailing whitespace và
  1 dòng trắng cuối tệp có sẵn trong gói mã. Không sửa source/migration trong
  tác vụ Git để che kết quả này. Đây không phải lượt kiểm thử ứng dụng.
- Gặp index.lock rỗng từ 26/10, không có tiến trình Git; lưu lại trong artifact
  rồi giải phóng. Khóa rỗng xuất hiện lại sau tiến trình đã kết thúc cũng được
  kiểm tra và lưu riêng trước commit; không xóa khóa đang có tiến trình sử dụng.
- Test/build ứng dụng, migration, inference, reindex, restart và deploy:
  **NOT RUN**. Số test ở phiên681/682 là lịch sử, không báo PASS mới.

Receipt/inventory/hash/diagnostic đã che giá trị nghi bí mật nằm trong
`storage/artifacts/context684-git-v1.0.2/` (Git ignore). Bổ sung nhật ký/snapshot
và ba index bằng commit tài liệu riêng; chỉ đồng bộ tiếp Gitea theo chỉ dẫn cuối.

[Nhánh trên Gitea](https://qnu-gitea.duckdns.org/admin/qnu-ai-platform/src/branch/v1.0.2).
[Snapshot684](../memory/snapshots/2026-10-28_session_684.md).
