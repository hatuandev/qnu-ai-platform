# 45 — Gửi duyệt, yêu cầu sửa và danh sách “Cần xử lý” (V1)

> **TÀI LIỆU LỊCH SỬ (từ 2026-11-13):** `frontendV1` đã được gỡ khỏi repo; giao diện duy nhất hiện hành là `frontendV2`. Nội dung dưới đây mô tả màn hình cũ, không dùng để kết luận hiện trạng.

```text
Phiên bản draft (đã chuẩn bị nội dung)
→ editor/admin xem trước và gửi duyệt (submission pending)
→ reviewer/admin mở đúng phiên bản, đọc bằng chứng và chọn:
   • yêu cầu sửa (bắt buộc lý do) → submission changes_requested
   • duyệt theo gate publication hiện hành → submission resolved trong cùng transaction
→ người gửi/admin có thể rút yêu cầu chưa xử lý → cancelled
→ muốn sửa nội dung: tạo phiên bản mới từ nội dung đã điều chỉnh rồi gửi duyệt lại
```

Submission là bản ghi bàn giao riêng, không thay enum xuất bản
(`draft/approved/published/superseded/withdrawn`). Gửi duyệt không làm phiên bản
thành approved; duyệt xong không tự publish và không tự hiện “sẵn sàng tra cứu”.
Bản nháp chưa gửi không xuất hiện trong hàng chờ; bản cũ đã duyệt/xuất bản vẫn
đọc được và không bị hồi tố.

Mọi thao tác đều có xem trước → xác nhận, khóa idempotency, kiểm quyền lại ở
server và lưu audit. Preview ghim document/version/bundle hash; nội dung hoặc
phiên bản thay đổi làm preview hết hiệu lực. Nội dung phiên bản là bất biến:
yêu cầu sửa không chỉnh trực tiếp mà tạo phiên bản mới, giữ lịch sử yêu cầu cũ.

Trang “Cần xử lý” là read model scoped workspace/collection, phân trang và lọc
theo loại ở server:

- `review_pending`: submission đang chờ duyệt.
- `changes_requested`: yêu cầu sửa chưa được thay thế.
- `awaiting_publish`: phiên bản đã duyệt nhưng chưa xuất bản.
- `preparation_failed`: chỉ lần chuẩn bị nội dung mới nhất thất bại.
- `sync_incomplete`: collection chưa đồng bộ xong theo trạng thái hiện tại.

Mỗi dòng ghi tài liệu, vấn đề, thời điểm, nhóm quyền có thể xử lý và deep link.
Chưa giao cá nhân thì hiện “Chờ người duyệt”, không gán người phụ trách giả.
Mục chỉ biến mất khi trạng thái tài nguyên/submission thật đổi; không có nút
dismiss để đánh dấu hoàn tất.

Quyền: gửi duyệt admin/editor; duyệt/yêu cầu sửa admin/reviewer; rút yêu cầu
admin hoặc chính người gửi; reviewer không cần quyền editor. Workspace vẫn là
biên giới quyền; URL và dữ liệu client không chứng minh quyền.

[API review](../../backendV1/qnu/domains/knowledge/review/router.py) ·
[API inbox](../../backendV1/qnu/domains/knowledge/inbox/router.py) ·
[Trang Cần xử lý](../../frontendV1/src/features/inbox/inbox-page.tsx) ·
[Nhật ký 900](../nhat_ky/2026-11-08_phien_900_ban_giao_duyet_va_inbox.md).
