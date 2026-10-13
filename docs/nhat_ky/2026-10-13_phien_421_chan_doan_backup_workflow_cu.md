# Phiên 421 — Backup bị chặn bởi ba workflow lỗi cũ

## Yêu cầu và phạm vi

Người dùng gửi ảnh lần sao lưu mới vẫn thất bại sau sửa launcher phiên 420. Chỉ kiểm tra metadata, truy vấn DB trong transaction read-only và đối chiếu báo cáo kiểm thử cũ; không chạy lại backup, không khôi phục/reset, không sửa workflow thật hay restart dịch vụ.

## Bằng chứng

- Backup `bkp_7430df87ffca495186b2287e8e4a0211`, correlation `corr_13e75f45709c`, tạo 2026-10-13 13:19:12 UTC (20:19:12 VN), runner PID 9224 đã chạy; progress 15, trạng thái failed.
- Metadata error: `Còn workflow đang chạy; hãy chờ hoàn tất hoặc đối soát execution bị gián đoạn trước khi sao lưu.` Không còn lỗi spawn/Selector của phiên 419.
- `capture_all()` đã tới kiểm tra PostgreSQL trước dump, file/S3/vector và mã hóa. Guard không chụp dữ liệu khi còn workflow `running` là chủ đích bảo đảm an toàn, không nên bỏ guard để backup thành công giả.
- Read-only DB cho thấy đúng 3 execution `running`, tất cả deadline null/completed_at null/node_execution_count 0/saved nodes 0:

| Execution | Created UTC | Correlation | Bằng chứng lỗi cũ |
|---|---|---|---|
| `0f200a3a-30dc-4736-b1b9-159277ae387c` | 04:23:57 | `corr_9de8b577196d` | `storage/admissions_eval413.json` và nhật ký 413: HTTP 500, orphan running |
| `c7d8e6f3-e4a7-4ee7-a644-d81c2c11a303` | 07:00:51 | `corr_51bdaa5dd6da` | `storage/admissions_eval415.json`, audit và nhật ký 415: HTTP 500, orphan running |
| `8bb61da6-22e0-44ec-ab2e-d1f69ca23ba1` | 07:00:53 | `corr_a22538683359` | Cùng báo cáo 415, HTTP 500, orphan running |

- BE/worker đang chạy được khởi động lại lúc 20:18:23 giờ địa phương, sau các bản ghi này. Không in command line, mật khẩu hay DB URL.
- `expire_abandoned_executions()` chỉ xử lý `running` có deadline thực đã quá hạn 30 giây; không tự kết luận execution legacy thiếu deadline là dead. Đây là quyết định an toàn của phiên 416, không phải lỗi Redis lưu kết quả cũ.

## Kết luận và hướng xử lý cần xác nhận

Launcher mới đã hoạt động trong lần sao lưu thật; blocker hiện tại là trạng thái nghiệp vụ tồn dư từ các lượt test 413/415 trước sửa workflow boundary/finalize 416/417. Chưa chứng minh toàn bộ backup corpus thật sẽ thành công sau gỡ blocker này.

Đề xuất đối soát có kiểm soát: với sự đồng ý của người dùng, chuyển chính 3 execution đã đối chiếu HTTP 500 sang failed, ghi lý do legacy reconciliation và vết kiểm toán; conditional update chỉ đúng ID/status/deadline như đã quan sát. Không xóa execution/nodes/hội thoại, không replay tools/chatbot, không cập nhật hàng loạt mọi record running. Giữ nguyên backup failed và các guard an toàn; người dùng tạo backup mới bằng mật khẩu tự giữ.

Không reset DB/xóa Redis/bỏ kiểm tra quiescence hoặc tự sinh deadline giả cho các bản ghi cũ. Chưa thực hiện mutation trong phiên này, chờ người dùng xác nhận vì đây là đối soát trạng thái DB hiện hành ngoài sửa tương thích launcher.

## Kiểm chứng và tài liệu

Metadata đọc được bằng quyền read ngoài sandbox; DB dùng `transaction(readonly=True)` và chỉ select execution metadata/counts. Đối chiếu báo cáo cũ và process creation time. Một probe inline nhập sai cú pháp không kết nối DB, đã thay bằng script read-only đúng. Không sửa runtime nên không chạy Ruff/Pytest/Vite; kết quả phiên 420 không được coi là test corpus thật của phiên 421.

Đã đồng bộ nhật ký README, PROJECT_CONTEXT và WORK_LOG. Bài học: test portable launcher và dữ liệu mẫu không thay cho kiểm tra trạng thái tồn dư của bản cài đặt thật; phải phân biệt lỗi khởi chạy với guard nghiệp vụ sau khi runner đã chạy.
