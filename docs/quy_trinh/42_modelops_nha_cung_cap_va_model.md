# ModelOps V1 — nhà cung cấp, khóa và model

Áp dụng cho `backendV1/` và `frontendV1/`, Context702 ngày 28/10/2026.

Cập nhật BE Context791: giới hạn token khi thêm model là tùy chọn; runtime text có ngân sách dự phòng được ghi rõ provisional. Xem [ngân sách tự động](V1_MODELOPS_NGAN_SACH_TU_DONG.md) và [prompt hoàn thiện FE](../ke_hoach/PROMPT_FE_MODELOPS_TU_DONG_791.md). Ngân sách tạm không phải thông số model đã đo; OCR ảnh/dimension vẫn có điều kiện riêng. Phần luồng UI dưới đây mô tả phiên702/733, chưa phải kết quả nghiệm thu FE791.

## Luồng sử dụng

1. Mở **ModelOps → Nhà cung cấp → Thêm nhà cung cấp**. Chọn OpenAI / ChatGPT, Google Gemini, Server AI QNU hoặc nhà cung cấp khác; nhập tên và địa chỉ API. Chưa cần model hoặc API key ở bước tạo.
2. Trang chi tiết mở ngay sau khi lưu. Trong **API keys**, thêm khóa upstream được cấp bởi server AI. QNU bảo vệ khóa trong DB, chỉ trả masked hint khi đọc lại. Xoay/thu hồi tại đây là thay đổi credential QNU sử dụng; việc thu hồi trên upstream vẫn do nhà cung cấp thực hiện.
3. Bấm **Thử kết nối** để gọi API danh sách model. HTTP thành công chỉ chứng minh lấy được danh sách bằng cấu hình hiện tại; chưa chứng minh inference từng model hoạt động.
4. Bấm **Nhập từ /models → Lấy lại** để xem model và thông số server công bố. Chọn model, chọn đúng chức năng cho model mới rồi **Áp dụng**. Model đã có được đồng bộ thông số; model mới được thêm kèm capacity/dimension nếu server cung cấp. **Thêm model** thủ công vẫn dùng khi server không hỗ trợ danh sách.
5. Mở **Cấu hình & chạy thử** trên từng model: kiểm tra thông số đã nhận, bổ sung phần thiếu như giới hạn input riêng/ngân sách OCR, chính sách phục hồi; chạy mẫu theo đúng chức năng. Server công bố chưa phải kết quả kiểm định. Thông số thiếu không bị suy đoán; xung đột capacity/dimension cần kiểm tra trước khi áp dụng.
6. Cấp **model cụ thể** cho workspace và chọn mặc định. Số liệu sử dụng tự mở kỳ theo UTC ở lượt gọi đầu tiên. Nhà cung cấp không được cấp như một model thực thi. Workspace V1 tiếp tục là biên giới quyền qua `resolve_workspace_access`.

Một server QNU là một nhà cung cấp, có thể chứa Nemotron, Qwen, BGE embedding và reranker. Các model mới dùng khóa dùng chung tại nhà cung cấp; không cần nhập lại endpoint/khóa cho từng model. Mỗi model vẫn có ID, capability, capacity, quyền workspace và lịch sử sử dụng riêng.

## Giao thức

Các kết nối mới sử dụng API tương thích OpenAI. Preset OpenAI là `https://api.openai.com/v1`; Gemini là `https://generativelanguage.googleapis.com/v1beta/openai`; QNU là `http://100.105.13.53:8000/v1`.

Gemini sử dụng [giao thức tương thích OpenAI chính thức của Google](https://ai.google.dev/gemini-api/docs/openai/), gồm đường dẫn `/models` và `/chat/completions` dưới base URL này. Việc chọn preset không cấp API key hoặc chứng nhận upstream hoạt động. Chức năng thực tế phải được chạy thử với server đang dùng; không có đăng nhập tài khoản ChatGPT/Gemini qua web trong luồng này.

## API và đường dẫn

Prefix BE `/platform/v1alpha1`, yêu cầu `ai.models.manage`:

| Tác vụ | API |
| --- | --- |
| Danh sách / tạo nhà cung cấp | GET / POST `/modelops/connections` |
| Đọc / sửa nhà cung cấp | GET / PATCH `/modelops/connections/{connection_id}` |
| Danh sách / thêm model | GET / POST `/modelops/connections/{connection_id}/models` |
| Khóa / xoay / thu hồi / audit | API `/modelops/providers/{connection_id}/keys` và các action hiện có |
| Thử kết nối / lấy danh sách | POST `/modelops/providers/{connection_id}/discover` |
| Đồng bộ capacity model đã có | POST `/modelops/connections/{connection_id}/sync-capacity` |
| Chạy thử model | POST `/modelops/providers/{model_id}/probe` |

FE dùng `/modelops/providers` cho danh sách, `/modelops/providers/{connection_id}` cho nhà cung cấp và `/modelops/models/{model_id}` cho cấu hình model. Deep link model cũ `/modelops/providers/{model_id}` tiếp tục được hỗ trợ. API `/modelops/providers` cũ giữ tương thích với model độc lập; giao diện mới tạo qua `connections`.

Khóa ứng dụng gọi vào QNU ở **API tích hợp** giữ luồng riêng theo [quy trình41](41_api_tich_hop_ung_dung.md).

## Chuyển dữ liệu hiện có

Migration mới `0005_provider_connections` nối sau `0004_application_api_keys`, không sửa baseline:

- Thêm nhà cung cấp cha, gom các model cũ theo đúng base URL đã lưu, chỉ chuẩn hóa dấu `/` cuối. Không đoán nhà cung cấp qua tên model.
- Giữ ID, endpoint, capability, capacity, trạng thái model, grants, defaults, binding trợ lý, usage và chỉ mục cũ.
- Giữ ID/ciphertext/trạng thái credential; chuyển quyền sở hữu bản ghi khóa về nhà cung cấp cha, đồng thời lưu phạm vi model cũ trong `model_ids`. Khóa cũ không tự mở rộng cho các model khác.
- Khi thêm model mới, cần một khóa dùng chung đang bật được tạo ở trang nhà cung cấp. Nếu chỉ có khóa cũ giới hạn theo model, server trả `connection_key_required` và hướng dẫn thêm khóa dùng chung.
- Tắt nhà cung cấp chặn runtime và chạy thử của model con; catalog không còn cung cấp các model đó. Thu hồi khóa dùng chung ảnh hưởng mọi model sử dụng khóa đó.
- Endpoint nhà cung cấp đã có model bị khóa sửa để giữ các tham chiếu đã ghim; khi chuyển server, tạo kết nối mới và cấu hình/cấp model tương ứng có chủ ý.

Trước khi nâng DB có dữ liệu: giữ bản sao lưu, dừng phiên API/worker đang dùng DB để tránh ghi đồng thời, xác nhận đúng cấu hình rồi chạy từ gốc repo:

```powershell
.\make.ps1 v1-migrate
.\make.ps1 v1-dev
```

DB hiện hành phải ở head `0005_provider_connections`. Không dùng stamp/reset để bỏ qua migration. SQL offline chỉ tạo DDL bổ sung; chuyển dữ liệu legacy thực hiện khi nâng online. Downgrade bị từ chối để giữ quan hệ và dữ liệu bằng chứng.

Context702 chuẩn bị mã/migration và kiểm chứng trên DB dùng một lần; không tự áp lên DB đang phục vụ hoặc restart phiên của người dùng. Kết quả test mock chỉ chứng minh hợp đồng nội bộ, không thay thế kiểm tra khóa và inference thật trên server.
