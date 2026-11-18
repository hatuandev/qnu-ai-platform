# Phiên 1011 — Cho phép trợ lý chưa gắn kho tri thức

## Quyết định

- Người dùng chọn "Cho phép trợ lý 0 kho": được lưu cấu hình khi chưa gắn kho,
  để hoàn thiện tên, mô tả, chỉ dẫn và mô hình trước, gắn kho sau.
- **Sai lệch so với mô tả phương án, ghi rõ**: phương án nêu "chào hỏi vẫn trả
  lời được". Bản triển khai này **không** làm được điều đó vì hội thoại và lượt
  hỏi gắn chặt với kho (`chat_conversations.collection_id NOT NULL` và khóa
  composite `uq_chat_conversation_scope`). Thay vào đó, mọi đường trả lời đều
  báo lỗi rõ ràng `assistant_no_collections` / `public_chatbot_unavailable`
  cho tới khi gắn lại ít nhất một kho. Không có câu trả lời chào hỏi tự do.

## Thay đổi

- **Hợp đồng**: `AssistantCreate/Update.collection_ids` nhận danh sách rỗng
  (bỏ hết kho) và `AssistantConfig.collection_id` cho phép `None`. Cột vô
  hướng `collection_id` của `chat_assistants` trở thành nullable; chỉ là bản
  phản chiếu `collection_ids[0]`, ràng buộc kho tồn tại vẫn do bảng liên kết
  `chat_assistant_collections` giữ.
- **Migration** `0035_assistant_without_collections`: bỏ khóa ngoại
  `fk_chat_assistant_collection` và cho `collection_id` nullable. Downgrade
  chủ động từ chối chạy nếu còn trợ lý chưa gắn kho (tránh bịa kho hoặc xóa
  dòng). Head vẫn là một nhánh duy nhất.
- **Danh sách**: bộ lọc `_usable_binding` đổi thành `or_(~bound, usable)` —
  trợ lý 0 kho vẫn hiện; chỉ ẩn khi mọi kho đang gắn đều không dùng được.
- **Readiness**: trợ lý 0 kho trả sớm `status="empty"`, `collection_id=None`,
  `collection_name=""`, `collections=[]`.
- **Chặn trả lời, báo lỗi rõ**:
  - Bắt đầu hội thoại: 409 `assistant_no_collections`.
  - Kiểm thử câu trả lời: 409 `assistant_no_collections` (đặt **trước** lời
    gọi readiness, vì `all(...)` trên danh sách rỗng luôn đúng và sẽ báo nhầm
    "kho chưa có tài liệu").
  - Kênh công khai: 409 `public_chatbot_unavailable` với lời vô hại.
  - Gateway OpenAI: 409 `assistant_no_collections`.
  - Bật công khai vẫn bị chặn gián tiếp vì readiness `empty` chưa đạt `ready`.
- **Giao diện**:
  - Form cấu hình bỏ điều kiện bắt buộc chọn kho; thêm cảnh báo cam "Trợ lý
    chưa gắn kho tri thức"; hộp xác nhận đổi câu chữ khi bỏ toàn bộ kho ("Bỏ
    kho và lưu").
  - Danh sách, chi tiết và tab Tổng quan hiện nhãn "Chưa gắn kho" thay vì
    "Chưa có nội dung"/"Kho chưa có tài liệu xuất bản" gây hiểu nhầm.
  - Hỏi thử và trang Chat: cảnh báo riêng, khóa ô gửi và nút câu hỏi gợi ý.
  - Link "Mở kho tri thức" và link sang Kho tri thức truyền
    `collectionId: collection_id ?? undefined` để hợp với schema search.
  - Thông báo lỗi bật công khai đổi thành "Trợ lý chưa sẵn sàng phục vụ: hãy
    gắn kho tri thức, hoàn tất xuất bản và nạp chỉ mục…" — đúng cho cả hai
    trường hợp chưa gắn kho và kho chưa xuất bản.

## Kiểm chứng

### Tĩnh

- Ruff đạt trên 8 tệp backend vừa sửa/đã tạo, gồm migration 0035.
- `alembic heads` trả đúng một head `0035_assistant_without_collections`.
- Biome đạt (sau khi format 2 tệp) và `tsc --noEmit` đạt trên frontendV2.

### Migration và schema (đã áp, PASS)

- `alembic upgrade head` chạy `0034 -> 0035`; bảng phiên bản riêng
  `alembic_version_backendv1` ghi `0035_assistant_without_collections`.
- Schema dev: `public.chat_assistants.collection_id` **is_nullable = YES**;
  ràng buộc `fk_chat_assistant_collection` **không còn**.

### Sống qua API :8002 (workspace `ws_623614ba7fb8`, PASS)

| # | Việc | Kết quả |
|---|---|---|
| 0 | Trợ lý 2 kho `ast_44fc63a77512` còn nguyên 2 kho | PASS |
| 1 | Tạo trợ lý với `collection_ids: []` | 201, `collection_ids=[]`, mirror `null` |
| 2 | Readiness trợ lý 0 kho | `empty`, `collections=[]`, `collection_id=null` |
| 3 | Lưu lại (sửa mô tả) vẫn 0 kho | 200, rev 1→2, vẫn rỗng (rev chỉ tăng khi cấu hình đổi) |
| 4 | Bắt đầu hội thoại | 409 `assistant_no_collections` |
| 5 | Kiểm thử câu trả lời | 409 `assistant_no_collections` |
| 6 | Bật kênh công khai | 409 `publication_not_ready` |
| 7 | Tạo hội thoại cho trợ lý 2 kho | 201 |
| 8 | Một lượt hỏi thật trên trợ lý 2 kho | 200, turn `completed`, `answered`, 612 ký tự, 1 nguồn trích dẫn |
| 9 | Xóa trợ lý tạm | 204 |

- Ghi chú trung thực: trợ lý 2 kho đang **tạm dừng** sẵn từ trước; hội thoại
  tạo lúc đang dừng trả 409 `assistant_inactive` (đúng). Để kiểm lượt trả lời,
  bật tạm rồi **trả lại trạng thái tạm dừng** ngay sau đó. Một câu hỏi không
  nêu năm nhận đúng phản hồi làm rõ phạm vi (`answer_scope_clarification_required`)
  vì trợ lý gắn 2 kho khác năm (2025 + 2026); câu nêu rõ "năm dữ liệu 2026" mới
  được trả lời. Đây là hành vi phạm vi hiện có, không phải lỗi của thay đổi này.
- Dọn dẹp: cả hai trợ lý tạm đã xóa; còn lại hội thoại kiểm chứng
  `cnv_56b7abefe622` trong nhật ký trợ lý 2 kho.

### Chưa chạy (NOT RUN)

- Kiểm tra trên trình duyệt (form + hộp xác nhận "Bỏ kho và lưu" + nhãn
  "Chưa gắn kho"): không mở phiên trình duyệt trong phiên này.
- Gateway OpenAI 409 `assistant_no_collections`: cần tạo app client + API key
  mới để gọi; đã kiểm bằng mã, chưa gọi sống.
- Lượt hỏi trên kênh công khai bị chặn: đã chặn gián tiếp ở bước 6 nên không
  có slug để gọi.
- Full suite backend và commit/push: **NOT RUN**.
