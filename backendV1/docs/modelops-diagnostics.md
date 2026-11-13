# ModelOps V1 — Discovery và kiểm tra provider

Công cụ chẩn đoán dành cho quản trị ModelOps (`ai.models.manage`), không phải
API cho chatbot hoặc bằng chứng nghiệm thu chất lượng RAG. Tái dùng provider,
key mã hóa, permission, network policy và các decoder hiện có.

## API

Prefix `/platform/v1alpha1`:

| Phương thức/đường dẫn | Hành vi |
| --- | --- |
| GET `/modelops/providers/{id}/diagnostics` | Đọc20lượt thử gần nhất, xác định khớp cấu hình hay stale |
| POST `/modelops/providers/{id}/discover` | Lấy tối đa500model IDs từ endpoint đã lưu; không inference hoặc sửa cấu hình |
| POST `/modelops/providers/{id}/probe` | Body `{"capability":"chat"}`; hoặc embedding, rerank, ocr |

Không nhận endpoint, credential, model hay tài liệu tùy ý từ body. Server lấy
active key theo priority/created_at như runtime. Provider tắt hoặc capability
chưa khai báo trả409 trước HTTP upstream. Quyền models.view không đủ đọc/chạy.

HTTP200 của API chẩn đoán có nghĩa đã tạo observation, phải đọc `outcome`:
ok/failed/unsupported. Upstream401/429/503 trở thành failed, giữ `http_status`
và thông báo tĩnh an toàn. Lỗi quyền/resource/configuration của QNU vẫn dùng
Problem Details. Không lưu hoặc trả raw body/ảnh/prompt/header/secret.

## Contract

- OpenAI-compatible/local dùng URL builder và decoder của runtime. Nemotron
  hỗ trợ discovery/OCR. Gemini/PaddleOCR báo unsupported, không fake thành công.
- Discovery kiểm kiểu/độ dài/ký tự model IDs và không nhận credential phản chiếu.
  Envelope lỗi HTTP200 không được coi là danh sách rỗng. Listed không là verified.
- Chat yêu cầu content không rỗng, finish hợp lệ; chưa kiểm strict JSON/tools.
- Embedding kiểm vector hữu hạn/khác0, index/count/model, dimension nếu đã khai
  báo. Dimension quan sát chỉ báo cáo, không tự sửa cấu hình hoặc index.
- Rerank kiểm đủ hit, index duy nhất/đúng phạm vi và score hữu hạn.
- OCR dùng PNG sinh trong RAM, cùng OCR_PROMPT/Nemotron payload và parser layout
  thật. Không nhập ảnh hay response thử vào kho tri thức.
- Network policy như runtime, không redirect/proxy môi trường/retry/fallback.
  Deadline tổng tối đa60giây hoặc timeout provider thấp hơn; output tối đa1024
  token hoặc giới hạn khai báo thấp hơn. FE dành70giây riêng cho request thử.
  Timeout không đồng nghĩa miễn phí hoặc chắc chắn upstream chưa chạy.

Đây là thao tác quản trị toàn cục bằng mẫu cố định, không lấy corpus hay gán
chi phí vào workspace tùy ý. Token quan sát lưu riêng ở observation; số liệu
chưa đo giữ null, không ghi0. Upstream có thể tính phí lượt gọi thử.

## Lưu trữ và tính nhất quán

Provider.extra_config giữ `diagnostic_checks_v1`, tối đa20records; không thêm
migration. Observation có ID, capability, thời điểm, latency, code/HTTP,
Retry-After nếu server trả, requested/observed model, dimension/token và danh
sách model. Audit ghi actor/action/provider/code. Hash identity không trả ra DTO.

Fingerprint gồm endpoint/model/type/capability/active/timeout, capacity/dimension,
auth policy và active key. `configuration_status=current` chỉ nghĩa cấu hình
khớp lúc thử, không là giám sát sức khỏe liên tục. Đổi target/khóa làm kết quả
cũ stale. Đổi trong lúc gọi trả409, không ghi success cho cấu hình mới.

Không giữ transaction/row lock trong lúc chờ upstream. Khi lưu, lock provider,
kiểm fingerprint và merge history để giữ các sửa đổi/lượt thử đồng thời.
Cancellation không bị đổi thành thành công. Retry-After chỉ là thông tin,
chưa triển khai key cooldown runtime. Model do gateway báo là quan sát response,
không là bằng chứng độc lập về model upstream thực tế.

Discovery chấp nhận tối đa 5000 model để hỗ trợ gateway tổng hợp nhiều nhà cung cấp.
Vượt mức này trả `provider_catalog_too_large`, không cắt danh sách hoặc báo thành công
một phần. Mỗi ID/metadata vẫn được kiểm tra; ID trùng hoặc dữ liệu sai làm thất bại
toàn lượt. Tra cứu ID trùng dùng set, tránh chi phí bậc hai khi catalog lớn.

## Giao diện

Trang chi tiết provider có Lấy danh sách model và Thử theo capability. Bộ chọn
model mở dialog sửa có sẵn; người dùng xem và lưu thủ công. Discovery/probe
không tự sửa defaults/capacity/dimension hoặc credential. Đổi model vẫn
làm khai báo capacity cũ stale theo quy tắc hiện có.

Query theo session, session mới remount trạng thái tương tác. Không auto-run
khi mở trang, không fake progress. Key rotation/revoke/provider update làm mới
query. UI hiện6lượt gần nhất với thời điểm và lỗi rõ ràng; API giữ20lượt.
Xem [hướng dẫn sử dụng](../../docs/quy_trinh/39_modelops_lay_danh_sach_va_chay_thu.md).
