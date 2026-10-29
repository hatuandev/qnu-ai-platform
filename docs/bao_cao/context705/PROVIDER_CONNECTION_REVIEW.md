# Context705 — Review kiểm tra API Key/kết nối nhà cung cấp

Ngày: 2026-10-29. Kết luận: **CHANGES REQUESTED**.
Trang: `http://127.0.0.1:3001/providers/conn_1e28e3a3c8e44f93`.
Người dùng xác nhận tập trung **Kiểm tra API Key / kết nối**. Đã tạm dừng nghiên cứu
AnythingLLM. Không sửa app, cấu hình, khóa hoặc dữ liệu model của người dùng.

## Kết luận thực tế

Nhà cung cấp đang bật, có2khóa active, cùng tên hiển thị và cùng ưu tiên5. Timeout lưu
là120giây. API kiểm tra kết nối hiện trả200/ok=true, đọc được4model trong47ms; thao tác
trên browser kiểm tra lần lượt cũng hiện toast thành công31ms. Đây chỉ là một lượt
GET `/models` dùng khóa active đầu tiên; chưa xác nhận khóa thứ hai.

Server thật trả401 khi không có Authorization và khi dùng khóa giả tổng hợp. Vì vậy
không có bằng chứng server thật đang bỏ xác thực. Không so sánh/giải mã hai secret để
kết luận chúng giống nhau; cùng masked hint không đủ chứng minh cùng khóa.

## F1 — [P1] Nút kiểm tra một khóa không chọn khóa đó

**Nguồn:** `frontendV1/src/features/modelops/connections/connection-detail.tsx:157`,
`frontendV1/src/features/modelops/connections/api.ts:195`,
`backendV1/qnu/domains/modelops/connections/service.py:295` và `schemas.py:64`.

`handleTestSingleKey(key)` chỉ dùng key cho spinner/thông báo, gửi `mutateAsync({})`.
Server tự lấy khóa active đầu tiên theo priority/created_at. Contract không nhận key_id:
request gửi ID khóa thứ hai tới API thật trả422. Probe FE click khóa thứ hai nhận `{}`
thay vì định danh khóa đã chọn (FAIL đúng assertion).

**Ảnh hưởng:** khóa thứ hai có thể hỏng nhưng UI vẫn báo thành công bằng khóa thứ nhất;
nhãn thông báo gán kết quả cho khóa người dùng bấm. Với hai khóa cùng tên khó phân biệt hơn.

**Đề xuất:** nhận `key_id` thay vì yêu cầu client gửi lại secret; server kiểm khóa thuộc
đúng connection, trạng thái hợp lệ và chỉ dùng khóa đó. Response có safe key_id/test_id.
Không tự fallback sang khóa khác trong tác vụ chẩn đoán một khóa.

## F2 — [P1] “Kiểm tra kết nối lần lượt” chỉ kiểm một lần

**Nguồn:** `connection-detail.tsx:141`.

Handler gọi `mutateAsync({})` đúng1lần, không lặp danh sách khóa và không có kết quả
riêng từng khóa. Probe FE có2khóa mong2lượt nhưng nhận1lượt (FAIL). Browser hiện một
thông báo tổng thành công, phù hợp với hành vi này.

**Ảnh hưởng:** người dùng hiểu rằng toàn bộ khóa đã được xác nhận nhưng các khóa sau
không được kiểm tra.

**Đề xuất:** duyệt lần lượt các ID khóa hoặc có batch API trả từng kết quả; tiếp tục
sang khóa kế tiếp sau lỗi, tổng hợp số đạt/lỗi/bỏ qua. Không báo tất cả đạt khi mới đạt1khóa.

## F3 — [P1] HTTP lỗi hoặc nội dung sai vẫn báo thành công

**Nguồn:** `backendV1/qnu/domains/modelops/connections/service.py:326–353`.

- Ngoài401/403, nhánh fallback trả `ok=True` kể cả404,429,500.
- HTTP200trả HTML hoặc JSON không có danh sách model hợp lệ cũng được đánh dấu thành công.
-5probe API qua router đều FAIL:404/429/500, HTML200, JSONerror200. Đây là upstream
  giả lập có kiểm soát, không phải quan sát server thật đang trả các lỗi đó.
- Các control200model list/401/403 đều PASS.

**Ảnh hưởng:** toast xanh có thể biểu thị sai endpoint, quá hạn mức hoặc server hỏng.

**Đề xuất:** phân biệt reachable/authenticated/discovered; HTTP lỗi là lỗi,200sai schema
là phản hồi không hợp lệ. Giữ HTTP status và error code an toàn; không nuốt parse error.
GET `/models` thành công không chứng minh chat/OCR/embedding/rerank inference đã chạy đạt.

## F4 — [P1] Kiểm tra HTTPS tắt xác minh chứng chỉ

**Nguồn:** `service.py:323`, `httpx.AsyncClient(timeout=10, verify=False)`.
Probe kiểm cấu hình client tại ranh giới HTTP FAIL vì verify=False.

**Ảnh hưởng:** khi connection dùng HTTPS, kết quả có thể báo đạt dù chứng chỉ không hợp
lệ; có rủi ro gửi credential tới đường truyền không được xác minh. Kết nối đang review
làHTTP nên đây không phải nguyên nhân trực tiếp của kết quả47ms hiện tại. Chưa thử mạng
MITM/chứng chỉ thật và không thay thiết lập mạng của máy.

**Đề xuất:** dùng TLS verification mặc định hoặc CA tin cậy do server cấu hình; không
để boolean client tùy ý tắt kiểm chứng chỉ.

## F5 — [P2] Bỏ qua timeout đã cấu hình

**Nguồn:** `service.py:323`, `service.py:358`.
Connection thật lưu120giây, nhưng nhánh test cố định10giây và thông báo cũng ghi10giây.
Probe parent timeout37giây vẫn tạo client timeout10(FAIL).

**Ảnh hưởng:** backend chậm hơn10giây bị báo timeout dù người dùng đã tăng cấu hình.
Chưa mô phỏng chờ120giây trên server thật; giới hạn được xác nhận bằng code và spy HTTP.

**Đề xuất:** dùng timeout connection hoặc giới hạn chẩn đoán được công bố rõ ràng;
đồng bộ với timeout frontend để kết quả cuối không bị mất ở client.

## F6 — [P2] Round Robin chỉ là trạng thái local, chưa lưu chính sách

**Nguồn:** `connection-detail.tsx:73`, `connection-detail.tsx:288–289`.
Công tắc dùng `useState(false)`/`setRoundRobin`, không đọc/lưu chính sách server. Probe
bật công tắc rồi remount cùng connection nhận false(FAIL). Không bật/tắt công tắc thật
trên dữ liệu người dùng.

**Ảnh hưởng:** giao diện khiến người dùng tưởng đang điều khiển xoay khóa nhưng không
thay đổi runtime. Không kết luận thuật toán pool phía server hiện có là round robin.

**Đề xuất:** nối với policy thực của ModelOps hoặc ẩn/vô hiệu kèm mô tả cho đến khi có API.

## F7 — [P2] Badge luôn ghi “Đang hoạt động” kể cả khóa không active

**Nguồn:** `connection-detail.tsx:332`.
Text trạng thái được viết cố định; chỉ switch đọc `key.status`. Probe fixture có1active
và1suspended nhưng hiện2badge active(FAIL). Hai khóa thật hiện đều active, nên sai nhãn
chưa xuất hiện trong dữ liệu đang mở.

**Đề xuất:** badge theo trạng thái active/suspended/revoked; phân biệt “được bật” với
“đã kiểm tra kết nối đạt”, không suy hai trạng thái này từ nhau.

## F8 — [P2] Lượt kiểm tra không cập nhật lịch sử/trạng thái kết nối

**Nguồn:** `connections/service.py::test_connection` và `output`; FE `useTestConnection`.
Trước và sau khi kiểm tra API thật, last_probe_at vẫn là `2026-10-28T13:59:31.682526Z`.
Nhánh test chỉ trả response, không lưu diagnostic check/audit; mutation không invalidate
query. Không có kết quả từng khóa để kiểm lại sau khi toast biến mất.

**Đề xuất:** lưu receipt an toàn theo connection+key+configuration revision; thời điểm,
latency, outcome/code/status; cập nhật UI sau test. Không log plaintext key/raw provider
body. Tái dùng diagnostic history hiện có thay vì tạo hệ thống thứ hai.

## F9 — [P2] Connection đã tắt vẫn đi qua nhánh kiểm tra network

**Nguồn:** `service.py:288–323`.
Handler test_connection không kiểm parent.is_active; probe parent bị tắt vẫn phát request
và trả200thay vì409(FAIL). Nhánh diagnostics hiện có kiểm provider/parent đang bật.
Đây là hành vi ở fixture, không tắt connection thật để thử.

**Đề xuất:** thống nhất chính sách. Nếu cho phép admin thử connection đang tắt thì phải
là thao tác chẩn đoán tường minh, không gán thành trạng thái sẵn sàng phục vụ; nếu không
cho phép thì chặn trước egress giống diagnostics.

## Bằng chứng và kiểm chứng

| Nhóm | Kết quả thực chạy |
|---|---|
| Browser trang người dùng | Mở trang thật, thấy2khóa/4model; bấm kiểm khóa1,khóa2 và kiểm lần lượt; toast cuối thành công31ms |
| API local thật | Đọc metadata/key DTO không secret; test{} trả200/ok=true/4model/47ms; chọn key_id thứ2trả422; history timestamp giữ nguyên |
| Upstream trực tiếp với mẫu an toàn | Không auth401; invalid synthetic key401 |
| FE batch | **FAIL**:4probe mới FAIL,4test hiện có PASS; exit1 |
| Backend HTTP boundary | **FAIL**:8probe lỗi FAIL,3control PASS; pytest exit1 |
| Lint test mới | Ruff check/format và Biome PASS |
| Build/full suite/benchmark/model inference | **NOT RUN** — review chỉ phạm vi kiểm tra kết nối, không sửa app |

Lệnh từ `frontendV1`:
`npm test -- tests/test_connection_review_705.test.tsx tests/test_provider_connections_702.test.tsx`.
Lệnh từ `backendV1`:
`uv run --frozen --extra dev pytest tests/unit/test_connection_review_705.py -q --basetemp=../storage/artifacts/provider-connection-review-705/pytest-temp-final`.

Test mới cố ý giữ assertion mô tả hành vi đúng để làm bằng chứng lỗi, không đổi chúng
sang xác nhận hành vi sai để lấy PASS. Backend fake session/credential/upstream nằm
trong app HTTP router riêng; không cần DB test/migration và không đụng dữ liệu phục vụ.
Artifact log/receipt local: `storage/artifacts/provider-connection-review-705/`.

## Phạm vi sửa đề xuất

1. Trước hết sửa contract chọn khóa và batch lần lượt(F1,F2), rồi xử lý kết quả HTTP(F3).
2. Dùng chung policy network/TLS/timeout và trạng thái hợp lệ với diagnostics(F4,F5,F9).
3. Lưu kết quả theo khóa và cập nhật UI; nối hoặc bỏ công tắc chưa hoạt động(F6,F7,F8).
4. Chạy lại probe hiện tại, regression connection/modelops và chỉ sau đó xác nhận thử
   hai khóa thật bằng từng ID. Không cần thay provider/model hoặc cấp lại quyền.

Phiên này chỉ thêm2tệp test review, báo cáo và nhật ký/index/snapshot. Hash4tệp ứng dụng
liên quan giữ nguyên. Không sửa hay xoá khóa, không xem plaintext credential, không
đổi provider/model/config, không restart/reindex/publish/deploy/Git commit/push.
