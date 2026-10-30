# Kiểm tra bốn model thật trên server QNU

Muốn chạy từ model đến upload và toàn bộ pipeline theo một thứ tự duy nhất, dùng [hướng dẫn tổng hợp toàn luồng](./V1_TEST_TOAN_LUONG_MODEL_QNU.md). Phần dưới giải thích riêng nhóm model.

Bổ sung nhóm test riêng sau khi đã thêm nhà cung cấp, khóa và model qua ModelOps. Agent chỉ viết mã và kiểm tra tĩnh; không coi `/models` là bằng chứng inference hoạt động và chưa chạy live inference khi bổ sung mã.

## Chuẩn bị phiên live

Nếu còn phiên workflow, Ctrl+C cửa sổ `serve` rồi `cleanup`. Tại thư mục repo:

```powershell
.\test-v1-e2e.ps1 cleanup
.\test-v1-e2e.ps1 init --mode live
.\test-v1-e2e.ps1 serve
```

Nếu chưa có phiên cũ thì bỏ `cleanup`. Giữ cửa sổ serve; mở đúng URL frontend E2E in ra. Phiên live có DB thử riêng và không khởi động AI giả lập. Các cấu hình ModelOps của dev không tự được sao chép sang phiên này.

Trước discovery, chạy bài test quản lý nhà cung cấp:

```powershell
.\test-v1-e2e.ps1 run provider-setup --headed
```

Bài này tạo QNU provider/key và đăng ký bốn model nếu thiếu. Khóa nhập ẩn trong PowerShell rồi lưu qua ModelOps DB, không đưa vào source hoặc `.env`. Đồng thời kiểm API sửa/bật/tắt, kết nối, sidebar và form tạo provider UI tạm. Nhà cung cấp/key/model đã có được dùng lại; không cần làm tay để vượt BLOCKED. Xem [hướng dẫn tổng hợp](./V1_TEST_TOAN_LUONG_MODEL_QNU.md) để biết chi tiết và giới hạn kiểm tra UI.

Model và nhà cung cấp phải được bật. Dùng giới hạn token/capacity do server thật khai báo khi cấu hình; không xem thông số của model giả lập là thông số server. Embedding test ghi chiều vector quan sát, không tự ghi đè dimension của model/chỉ mục. Endpoint/model ID mong đợi nằm trong [profile không chứa secret](../../scripts/e2e_profiles/qnu-server.json); nếu server đổi model ID, điều chỉnh profile và cấu hình ModelOps tương ứng trước khi chạy.

## Chạy từng lệnh

Ở cửa sổ thứ hai:

```powershell
.\test-v1-e2e.ps1 run model-discovery --headed
.\test-v1-e2e.ps1 run model-chat --headed
.\test-v1-e2e.ps1 run model-embedding --headed
.\test-v1-e2e.ps1 run model-rerank --headed
.\test-v1-e2e.ps1 run model-ocr --headed
```

Hoặc chạy nhóm này liên tiếp, dừng ở lỗi đầu:

```powershell
.\test-v1-e2e.ps1 models --headed
```

Có thể thay đầu lệnh bằng `make.ps1 v1-e2e`, ví dụ `make.ps1 v1-e2e run model-chat --headed`. Không cần chạy navigation/upload trước nhóm model; discovery cần PASS trước các probe còn lại. Bốn probe độc lập nhau sau discovery, không cần tất cả probe trước đó PASS mới thử model khác. `models` chạy cả provider-setup trước năm chặng model; `all` vẫn chỉ chạy tám chặng nghiệp vụ; muốn thử model trước thì chạy `models` riêng.

Runner từ chối model-* trong workflow. Test chọn đúng connection, endpoint, model ID và capability từ DB. Nếu chưa thêm hoặc có nhiều cấu hình trùng khớp thì BLOCKED, không tự chọn một model khác hoặc fallback. Chưa có key đang bật thì BLOCKED; key sai/timeout/schema sai là FAIL với mã diagnostic và upstream HTTP an toàn.

## Test thực sự kiểm tra gì?

Tất cả request đi qua API ModelOps hiện có để lấy credential mã hóa trong DB và sử dụng adapter/egress policy của backend. Không gọi server AI trực tiếp từ trình duyệt hay giữ credential trong file test.

| Chặng | Request mẫu từ adapter hiện tại | Điều kiện đạt |
| --- | --- | --- |
| `model-discovery` | GET `/v1/models` | HTTP upstream 200, catalog hợp lệ và đủ bốn ID trong profile. Chưa phải inference. |
| `model-chat` | Chat completions, prompt ngắn “Reply with OK.” | Adapter đọc được nội dung chat hợp lệ; không chỉ HTTP 200. |
| `model-embedding` | Embeddings với một câu mẫu | Đủ vector, giá trị số hữu hạn và chiều hợp lệ; ghi chiều quan sát, kiểm chiều khai báo nếu có. |
| `model-rerank` | Câu hỏi “QNU”, hai đoạn giả lập | Adapter xác nhận index/score và kết quả rerank đúng contract. |
| `model-ocr` | Ảnh tự sinh chứa “QNU TEST 123” | Phản hồi OCR được giải mã và có layout/tọa độ hợp lệ theo adapter Nemotron. |

Mỗi lượt phải có `outcome=ok`, `diagnostic_ok`, upstream HTTP200 và kết quả còn `current` được lưu trong lịch sử ModelOps. Nếu server trả observed model ID thì test so với ID đã yêu cầu. Nếu server không trả model ID hoặc usage, báo cáo giữ null, không giả số liệu. Diagnostic API có thể trả HTTP200 để mô tả upstream lỗi: test vẫn FAIL khi outcome thất bại.

Đây là kiểm tra khả năng kết nối và hợp đồng inference trên dữ liệu tự sinh. Chưa đo độ chính xác OCR trên tài liệu thật, thứ tự rerank theo nhãn chuẩn, chất lượng tiếng Việt, strict JSON Compiler, RAG/citation, throughput hay capacity phần cứng. Discovery PASS không đảm bảo probe PASS. Những giới hạn này không được đổi thành skip để coi model đã đạt.

## Xem kết quả và kiểm tra toàn luồng sau đó

```powershell
.\test-v1-e2e.ps1 status
.\test-v1-e2e.ps1 report
```

Ngoài HTML/JSON Playwright, từng lượt đạt có `model-observation.json` trong thư mục báo cáo: model yêu cầu/quan sát, diagnostic ID, HTTP, latency, chiều embedding và usage nếu có. Không ghi raw response, secret hoặc ảnh OCR vào báo cáo này. Trace/video/screenshot tắt cho nhóm model vì trang ModelOps có thể chứa thông tin cấu hình và token.

Các diagnostic lưu lịch sử trong DB thử và gửi request thật tới server QNU, có thể phát sinh usage upstream. Chạy lại mỗi lệnh là một lượt kiểm tra mới, không tự retry inference. Dọn phiên E2E sẽ xóa cấu hình/key của phiên thử cùng Docker volume, giữ báo cáo cục bộ; không ảnh hưởng cấu hình ModelOps dev.

Sau khi các probe đạt và đã cấu hình capacity/dimension/OCR budget đúng server thật, tiếp tục tám chặng nghiệp vụ trong cùng phiên live theo [hướng dẫn tổng hợp](./V1_TEST_TOAN_LUONG_MODEL_QNU.md). Navigation gắn đúng bốn model đã kiểm định làm mặc định của workspace thử và tạo quota hữu hạn theo profile nếu chưa có. Không dùng PASS của nhóm model thay cho kết quả toàn luồng.
