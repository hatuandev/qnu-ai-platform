# Capacity ModelOps — hợp đồng cho runtime OCR/Compiler

Phần capacity được triển khai riêng trong Context641 để phối hợp với tác vụ OCR.
API tạo/sửa provider nhận `token_limits`; đây là khai báo của quản trị viên, không
phải kết quả tự động kiểm định model. Dùng các giá trị do endpoint/model thực tế hỗ trợ.

```json
{
  "token_limits": {
    "context_window_tokens": 1048576,
    "max_input_tokens": null,
    "max_output_tokens": 65536
  }
}
```

Các số trên chỉ là ví dụ hợp đồng, không phải capacity của Nemotron. Không có trần
8K/32K chung. API có giới hạn input/output độc lập có thể để context dùng chung là
null. Trường chưa biết giữ null; không suy context bằng cách cộng input với output.

Response provider trả token_limits, capacity_status (unknown/configured/stale) và
capacity_basis. PATCH bỏ qua trường giữ nguyên; null tường minh xóa khai báo. Đổi
endpoint/model vô hiệu cấu hình cũ, kể cả sau đó đổi lại; khai báo lại sẽ ghim đích
mới. Dùng JSONB hiện có, không cần migration mới.

Runtime khác gọi qua `qnu.domains.modelops.public_api`:

- `resolve_model_capacity(db, actor, workspace_id, capability, provider_id=None)`:
  kiểm resolver/grant/capability/provider rồi trả snapshot bất biến và configuration_hash.
- `plan_model_request(..., input_tokens, requested_output_tokens=None,
  reserve_tokens=0, minimum_output_tokens=1)` trả snapshot cùng ngân sách. Chưa biết
  capacity/input hoặc vượt giới hạn gây lỗi tường minh; không cắt nội dung đầu vào.

Input tokens do runtime tin cậy tính/đo, bao gồm prompt, ảnh, framing theo giao thức.
Không lấy số ký tự Base64 làm token ảnh. Chưa có cách tính ảnh đáng tin phải báo
model_input_budget_unknown, không coi input=0. Output tính cả reasoning nếu protocol
quy định. Requested output là giới hạn tác vụ tường minh; không ép mặc định8192.

**OCR đã nối guard từ Context643:** trước gửi từng trang, resolve lại provider,
kiểm configuration_hash, rồi gọi plan_model_request. Run ghim hash endpoint/model/
timeout/capacity và hash prompt; thay cấu hình chặn resume hoặc tạo generation mới.
finish_reason=length giữ raw response nhưng không báo OCR hoàn tất.

Trong token_limits có thể khai báo `ocr_page_input` gồm:

- `max_image_width`, `max_image_height`: phạm vi kích thước ảnh được accounting bao phủ.
- `input_tokens_upper_bound`: cận trên bảo thủ đã có căn cứ cho tổng prompt, framing
  và ảnh trong phạm vi đó; không phải số ký tự Base64.
- `prompt_sha256`: SHA-256 của đúng prompt mà accounting bao phủ, UTF-8.

Đây vẫn là khai báo operator_configured; không được coi là kết quả kiểm định hay
tokenizer tự động. Thiếu accounting, prompt đổi hoặc ảnh vượt phạm vi thì OCR báo
lỗi trước HTTP. Cần nhập giá trị phù hợp endpoint/model thực tế qua API quản trị;
không suy accounting cho mọi trang từ usage của một phản hồi mẫu.

`OCR_MAX_OUTPUT_TOKENS` vẫn là ngân sách tác vụ mặc định8192 đã ghim trong run,
không phải context/model capacity. Trần validation32768 đã được gỡ; có thể đặt
ngân sách tác vụ lớn hơn khi model cho phép. Runtime OCR đối chiếu ngân sách đó
với profile và accounting trước gửi, không coi biến môi trường là capacity.
Quota reserve bằng tổng input bound + output, không dùng OCR_PAGE_TOKEN_BUDGET cố định.

Tự động discovery metadata provider và đếm token ảnh phụ thuộc protocol/runtime,
không được đánh dấu đã có chỉ vì API lưu được capacity. Không tạo verified giả.
