# Context613 — Cấu hình dung lượng model

## Trường cấu hình mới

Quản trị có thể khai báo `token_limits` cho đúng alias trong `model_capabilities` bằng API cập nhật provider hiện có. Frontend chưa có form riêng cho trường này. Cấu hình bên dưới chỉ là ví dụ, chưa được áp dụng lên provider đang chạy:

```json
{
  "model_capabilities": {
    "your-exact-model-alias": {
      "probe_role": "chat",
      "token_limits": {
        "endpoint": "https://provider.example/v1",
        "context_window_tokens": 32768,
        "max_output_tokens": 8192,
        "basis": "operator_configured",
        "reasoning_in_output_budget": true
      }
    }
  }
}
```

Alias phải đúng tên được route sử dụng, bao gồm prefix nếu có. Endpoint phải trùng URL provider đã cấu hình; không chứa credential hoặc query. Không thêm API key vào profile. `basis=provider_reported` chỉ phù hợp khi có thông tin thật từ provider; tên model hoặc việc model có trong danh mục không chứng minh context.

## Chọn giá trị

- Context là dung lượng server/provider thực sự cấp cho lần chạy, gồm input và ngân sách sinh theo giao thức của provider. Model quảng cáo context lớn không chứng minh server đã bật mức đó.
- Max output là giới hạn đầu ra được xác nhận hoặc cấu hình cho route; phải nhỏ hơn context để chừa input. Không có một giá trị 8.192 bắt buộc cho mọi model nữa.
- Nếu reasoning nằm trong ngân sách sinh, phần đó cùng chịu trần output. Provider dùng ngân sách thinking riêng chưa được compiler hỗ trợ đầy đủ; khai báo false sẽ yêu cầu xác nhận ngân sách riêng thay vì âm thầm bỏ qua.
- Không dùng toàn bộ context chỉ vì có thể. Các giới hạn calls, thời gian, số đối tượng và kích thước artifact vẫn là chính sách vận hành riêng.

Compiler phân giải lại profile khi bắt đầu job và kiểm configuration seal tại checkpoint. Đổi model/profile trong lúc job đang chạy làm checkpoint không còn đúng cấu hình; không tự trộn hai cấu hình vào một bản đang duyệt.

## Khi chưa khai báo

Hệ thống giữ ngân sách tương thích của server, đánh dấu **chưa xác minh giới hạn model**. Với route không có override, hiện là context24K/output2.500. Lượt thử GPT-OSS của Context613 có override server riêng medium/output8.192/context24K, không đổi default.

Vì vậy việc cập nhật mã không đồng nghĩa app tự biết context của mọi provider. Cần khai báo hoặc cung cấp dữ liệu capability đáng tin cậy trước khi muốn tận dụng context lớn hơn. Không tự gửi request tăng dần đến khi provider lỗi để đo giới hạn.

## Fallback và cập nhật

Ngân sách compiler hiện chọn mức phù hợp nhỏ nhất trên primary/fallback đã cấu hình. Ví dụ profile primary128K/output16K và fallback32K/output4K sẽ lập nhóm theo32K/output4K. Đây là cách giữ toàn bộ bằng chứng nguyên vẹn khi chuyển route; chưa tối ưu theo hai kế hoạch riêng cho primary/fallback.

Form cũ chỉ cập nhật role/vision/reasoning sẽ giữ token profile hiện có. Gửi explicit `"token_limits": null` mới xóa profile đó. Đổi endpoint cần xác nhận lại profile gắn endpoint mới.

Các lỗi cần chú ý: `MODEL_TOKEN_LIMITS_INVALID`, `MODEL_TOKEN_LIMITS_STALE`, `MODEL_OUTPUT_LIMIT_EXCEEDED`, `MODEL_REASONING_BUDGET_UNVERIFIED`. Chúng không phải kết luận tài liệu không có dữ kiện.

Nguồn mã: [ModelOps schemas](../../../backend/app/modules/modelops/schemas.py), [profile và merge](../../../backend/app/modules/modelops/services/token_limits.py), [phân giải compiler](../../../backend/app/modules/knowledge/services/compilation_modelops.py).
