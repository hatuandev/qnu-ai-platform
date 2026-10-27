# Runbook rollback

| Tình huống | Hành động |
|---|---|
| v1 trả 5xx hàng loạt | Gỡ location nginx → traffic về legacy |
| Dữ liệu v1 ghi sai | Không xoá; tạo migration đảo chiều có audit |
| Migration v1 lỗi | Kiểm lỗi và trạng thái transaction; sửa bằng forward migration. Baseline từ chối downgrade để giữ bằng chứng; thử trên DB test riêng trước |
| Queue v1 kẹt | Dừng worker v1; job của v1 không ảnh hưởng legacy |

Nguyên tắc: **không** sửa bảng legacy, **không** xoá dữ liệu không có audit.
