# 41 — API tích hợp ứng dụng bên ngoài (backendV1)

Phạm vi: inbound API key gọi trợ lý QNU. Khóa này khác khóa server AI do ModelOps giữ để gọi upstream.

## Cấu hình và thao tác quản trị

1. API cần schema `0004_application_api_keys`. Dùng quy trình migration V1 hiện có trên môi trường được quản trị; các kiểm thử tự áp migration trong DB riêng.
2. Khai báo `PUBLIC_BASE_URL` trong cấu hình backendV1 bằng địa chỉ HTTP(S) mà ứng dụng bên ngoài truy cập được, không có phần `/platform/v1alpha1`. Ví dụ phát triển: `http://localhost:8002`. Khi chạy sau reverse proxy, dùng URL công khai thực tế của QNU; không dùng URL upstream model.
3. Mở ModelOps → API tích hợp, chọn workspace. Người gọi phải là admin của workspace hoặc admin nền tảng; server xác minh membership.
4. Tạo khóa cho ứng dụng: chọn rõ “Tất cả trợ lý” hoặc ít nhất một trợ lý cụ thể. Phạm vi cụ thể rỗng bị từ chối. Quyền tất cả bao gồm trợ lý được thêm sau này; chỉ chọn khi có chủ đích.
5. Lưu secret hiển thị một lần. Backend chỉ giữ SHA-256; không có API đọc lại plaintext. Tạo/xoay trả `Cache-Control: no-store`; frontend không giữ secret trong kết quả mutation. Modal đóng sẽ xóa state hiển thị.
6. Có thể tạm dừng/kích hoạt lại, xoay hoặc thu hồi khóa. Xoay thu hồi khóa cũ trong cùng transaction, khóa hàng để tránh hai worker tạo hai bản thay thế. Thu hồi là trạng thái cuối, không bật lại được.

Khóa đã tạo trước bản sửa với `allowed_assistant_ids=[]` vẫn giữ ý nghĩa cũ là tất cả trợ lý; bản sửa không âm thầm đổi quyền đã cấp. Nếu khóa đó từng được tạo do chọn phạm vi rỗng ngoài ý muốn, quản trị viên cần thu hồi và tạo khóa mới với danh sách trợ lý rõ ràng. Xoay khóa giữ nguyên phạm vi, không tự thu hẹp quyền cũ.

Thiếu `PUBLIC_BASE_URL`, API cấu hình trả503 với mã `public_endpoint_unconfigured`. FE hiển thị lỗi, không đoán URL theo origin frontend, Host hay X-Forwarded-Host. Chỉ sửa cấu hình môi trường mình quản lý và khởi động lại qua quy trình vận hành khi đã được phép; bản sửa mã không tự đổi cấu hình/chạy lại tiến trình đang dùng.

## Hợp đồng gọi API

Base URL OpenAI:

```text
<PUBLIC_BASE_URL><API_PREFIX>/integrations/openai/v1
```

- `GET /models`: trả ID của các trợ lý đang hoạt động mà khóa được phép truy cập, trong workspace đã xác minh. Trợ lý/kho đã bị ẩn theo lifecycle không xuất hiện.
- `POST /chat/completions`: `model` là ID từ `/models`. Hiện hỗ trợ đúng một tin nhắn `user`, nội dung1–8000ký tự và `stream=false`.
- Chưa hỗ trợ lịch sử nhiều lượt, system/assistant messages, streaming, tools/functions, temperature/top_p/max_tokens hay trường ngoài schema. Các yêu cầu này bị trả400, không nhận rồi bỏ qua. Hội thoại nhiều lượt có luồng Conversations V1 riêng, chưa mở qua gateway này.
- Persona, giới hạn đầu ra và toàn bộ RagPolicy lấy từ snapshot cấu hình trợ lý: dense/hybrid/rerank, metadata, context, verification. Reranker lấy từ runtime container; ModelOps vẫn kiểm provider grants, capability và quota của workspace.
- `qnu_extensions` chứa assistant_id/revision, status/reason, statements, sources, verification. `insufficient_evidence` không được coi như câu trả lời có bằng chứng; client đọc status/reason thay vì chỉ kiểm content có rỗng hay không.

Ví dụ request, thay ID bằng kết quả `/models` và đưa secret qua cơ chế cấu hình bí mật của ứng dụng:

```json
{
  "model": "ast_id_from_models",
  "messages": [{"role": "user", "content": "Câu hỏi cần tìm thông tin"}],
  "stream": false
}
```

Không nhúng secret ứng dụng vào JavaScript public hoặc commit vào repo. Máy chủ ứng dụng gọi QNU với `Authorization: Bearer <secret>`.

## Quyền, hạn mức và lỗi

- Khóa/app phải active, chưa hết hạn, cùng workspace; actor máy có membership thật và không có quyền admin nền tảng.
- Gateway kiểm lại khóa/app/hạn dùng/membership/workspace và trạng thái/revision trợ lý tại checkpoint trước khi sinh, sau khi sinh/kiểm chứng và trước khi trả kết quả. Dữ liệu không được trả khi quyền đã mất ở thời điểm kiểm tra đó.
- RPM/RPD đếm lượt yêu cầu qua Redis theo key, UTC và namespace triển khai. Redis không sẵn sàng trả503 `rate_limiter_unavailable`, không bỏ qua hạn mức. Vượt hạn mức trả429 và Retry-After. Cả lượt `/models` cũng tính vào hạn mức.
- Lỗi domain giữ HTTP status/mã lỗi (ví dụ quota429, cấu hình409, dịch vụ503); error envelope OpenAI dùng `error.message/type/param/code`. Lỗi validation của gateway là400. Lỗi bất ngờ trả thông báo chung; không trả chuỗi exception/upstream secret thô. API quản trị vẫn theo RFC7807.
- Log hiện có ghi lượt inference thành công/thất bại và usage quan sát của chặng trả lời; chưa phải sổ kiểm toán đầy đủ mọi auth/validation/models request hay tổng token mọi chặng. Chức năng quản lý trạng thái toàn app và liên kết usage từng chặng nằm ngoài10lỗi được sửa trong Context700.

Kiểm thử tập trung tại `backendV1/tests/integration/test_integration_gateway_regressions.py` và `frontendV1/tests/test_modelops_integration_regressions.test.tsx`; đọc kết quả thực chạy trong nhật ký Context700, không suy upstream thật đã hoạt động từ fake model/test.
