# V1 — Test model QNU rồi chạy toàn bộ quy trình

Nếu cần bản lệnh ngắn sau khi bật máy hoặc muốn tạo phiên mới, xem [Chạy lại E2E](./V1_QUY_TRINH_TEST_LAI.md).

Đây là hướng dẫn tổng hợp cho một phiên thử dùng server QNU thật. Thứ tự:

**Test tạo provider/key/model → test đủ bốn model → gắn model mặc định vào workspace thử → upload → bóc tách/sửa → biên soạn/review → phát hành/index → hỏi đáp → quyền/API key → xóa/nạp lại.**

Mọi lệnh chạy tại `D:\DuAnPhanMem\qnu-ai-platform`. Dùng hai cửa sổ PowerShell. Không cần chạy `make dev` hoặc `v1-dev`.

## 1. Tạo phiên live — cửa sổ thứ nhất

Mở Docker Desktop. Nếu còn `serve` của phiên cũ, nhấn Ctrl+C ở cửa sổ đó rồi dọn:

```powershell
.\test-v1-e2e.ps1 cleanup
```

Nếu chưa có phiên cũ, bỏ lệnh cleanup. Tạo phiên mới và giữ cửa sổ serve:

```powershell
.\test-v1-e2e.ps1 init --mode live
.\test-v1-e2e.ps1 serve
```

Chờ dòng `E2E live: http://127.0.0.1:...`, mở đúng URL đó. Các cổng được cấp riêng mỗi phiên; không lấy URL FE dev để cấu hình nhầm DB. Phiên live không chạy AI giả lập; backend/worker/FE và PostgreSQL/Redis/MinIO/Qdrant/Gotenberg thử do runner quản lý riêng.

### Chạy tiếp sau khi tắt máy

Checkpoint và dữ liệu Docker có thể còn sau khi tắt máy; tiến trình phục vụ phải được kiểm tra lại. Không chạy `cleanup`/`init` nếu muốn giữ dữ liệu và cấu hình model của phiên cũ. Trước tiên:

```powershell
.\test-v1-e2e.ps1 status
```

Nếu các container của phiên đã dừng, mở Docker Desktop rồi bật lại đúng container cũ, giữ volume:

```powershell
$e2eRun = (Get-Content .\tmp\v1-e2e\active.json | ConvertFrom-Json).run_id
docker compose -f ".\tmp\v1-e2e\$e2eRun\compose.json" -p "qnu-e2e-$e2eRun" start
.\test-v1-e2e.ps1 serve
```

Chỉ mở một `serve`. Nếu báo đang chạy, kiểm tra phiên đang phục vụ; không tiếp tục gọi `init` hoặc xóa lock bằng tay. Khi API/worker/FE đã sẵn sàng, chạy tiếp từ chặng chưa đạt ở cửa sổ thứ hai. Nếu đã cleanup thành công thì cấu hình và dữ liệu thử cũ không còn; cần tạo phiên mới từ bước1.

## 2. Test Nhà cung cấp — cửa sổ thứ hai

Không cần tự tạo nhà cung cấp/key/model trước. Trong phiên live đang chạy, thực hiện:

```powershell
.\test-v1-e2e.ps1 run provider-setup --headed
```

Lệnh tự tạo QNU provider tại `http://100.105.13.53:8000/v1` nếu thiếu, kiểm tra API sửa/lưu và trạng thái. Nếu chưa có khóa active, terminal yêu cầu **nhập API key ẩn**; dán khóa rồi Enter. Không truyền key trong tham số, `.env`, source hoặc file checkpoint. Key đi từ bộ nhớ tới API ModelOps local, lưu mã hóa trong DB thử; trình duyệt test không nhận raw key. Nếu đã thêm key qua UI, lệnh dùng khóa đang bật và không hỏi lại. Key sai thì thay/xoay trong giao diện rồi chạy lại provider-setup.

Sau đó bài Playwright kiểm tra kết nối thật bằng key đã lưu, catalog bốn model, tự đăng ký bốn model nếu thiếu, chặn inference khi provider bị tắt và bật lại trong finally. Nó còn mở sidebar **Nhà cung cấp**, kiểm danh sách/chi tiết và thực sự submit form tạo một provider UI tạm không credential, xác nhận lưu rồi xóa provider tạm đó qua API. QNU provider và bốn model được giữ cho pipeline. Đây là test kết hợp API và UI, chưa tự nhập raw key vào form frontend.

Nếu đã có một QNU provider cùng endpoint, bài test dùng lại; cấu hình trùng sẽ BLOCKED. Không chạy provider-setup sau khi đã upload, vì bài test có bật/tắt provider; muốn kiểm lại toàn bộ quản lý nhà cung cấp ở thời điểm đó thì tạo phiên mới. provider-setup lưu capacity/dimension server công bố bằng snapshot discovery; timeout và OCR/input override bổ sung từ profile E2E có căn cứ, không tự bịa capacity. Trên FE phiên thử, mục **Nhà cung cấp** ở sidebar mở thẳng `/providers`; mục Cấu hình giữ thiết lập khác.

Các model được đăng ký:

| Chức năng | Model ID | Được dùng ở đâu trong pipeline |
| --- | --- | --- |
| Chat | `qwen3.8-27b-q4` | Compiler, Compiler Review, trả lời và gateway chat. |
| Embedding | `bge-m3` | Tạo chỉ mục và vector truy vấn. |
| Rerank | `bge-reranker-v2-m3` | Xếp hạng lại ứng viên sau hybrid search trong hỏi đáp. |
| OCR | `nemotron-parse` | OCR trang scan hoặc trang không đủ text native. PDF/DOCX có chữ vẫn dùng native-first theo backend. |

Sau provider-setup PASS, capacity/dimension đã được tự đồng bộ từ `/v1/models`; có thể chạy ngay nhóm model, không cần dừng để nhập thông số thủ công. Script dùng snapshot đã lưu và endpoint/model trong profile, đồng bộ model đã có hoặc đăng ký model mới kèm metadata. QNU giữ guard unknown/conflict; server công bố không phải inference verified.

Nếu muốn xem hoặc tự đồng bộ qua giao diện: mở đúng FE phiên thử → **Nhà cung cấp → Server AI QNU → Nhập từ /models → Lấy lại → chọn model → Áp dụng**. Bước này tùy chọn khi provider-setup đã PASS.

| Model | Thông số server đang công bố | Bổ sung ngoài metadata |
| --- | --- | --- |
| Qwen | Context131072, output16384 | Timeout 300 giây; input riêng để trống; Compiler/Review 8192 giữ. |
| BGE embedding | Context8192, dimension1024 | Timeout 60 giây; input riêng có thể để trống vì có context. |
| BGE rerank | Context8192 | Timeout 60 giây; input riêng 1024 nếu giữ chính sách thử cũ. |
| Nemotron | Context16384, output8192 | Timeout 180 giây và ngân sách ảnh OCR bên dưới. |

Các con số phản ánh server người vận hành vừa bổ sung; nếu lấy lại thấy khác thì đối chiếu cấu hình phục vụ. Không tự nâng/ép số để test xanh. Trường server không công bố giữ unknown hoặc giá trị hợp lệ đã lưu. Sync giữ input override và ngân sách OCR, chặn xung đột; dimension embedding đổi khác cấu hình hiện hành cũng bị chặn để kiểm tra index trước.

Timeout/input riêng/OCR trong bảng được provider-setup bổ sung từ profile QNU khi cần; không ghi đè input/OCR đã có. Mở **nút bút chì cạnh model** nếu muốn kiểm tra hoặc thay đổi. Form chỉ gửi trường thay đổi. Nemotron dùng lại ngân sách đã có căn cứ khi server/processor/prompt không đổi: ảnh tối đa1664×2048, input upper bound4096, hash prompt theo lệnh dưới. Nếu đổi điều kiện này phải xác minh lại, không suy token ảnh từ Base64.

Các lệnh cURL thử inference không phải cấu hình capacity. `max_tokens` trong request là mức client yêu cầu, không chứng minh giới hạn server; `--max-time` là thời gian chờ. Địa chỉ `127.0.0.1:8000` trong lệnh chạy trên máy AI chỉ tới máy AI đó; QNU trên máy Windows vẫn dùng endpoint đã cấu hình trong ModelOps. Không suy capacity từ model ID, một ảnh mẫu hay vector đã trả về.

Để lấy riêng hash của prompt OCR trong mã hiện tại, từ root repo chạy (không gọi model):

```powershell
Push-Location backendV1
.\.venv\Scripts\python.exe -c "import hashlib; from qnu.domains.ocr.config import OCR_PROMPT; print(hashlib.sha256(OCR_PROMPT.encode('utf-8')).hexdigest())"
Pop-Location
```

Profile đã có hash và ngân sách OCR; lệnh này chỉ để đối chiếu. Hash chỉ nhận diện prompt, không đo ngân sách ảnh. Nếu chưa biết các giới hạn còn lại, lấy cấu hình khởi chạy model (`vllm serve`, Docker Compose hoặc cấu hình gateway), bỏ credential trước khi chia sẻ. Giữ trạng thái BLOCKED cho đến khi có đủ căn cứ.

Capacity không được lấy từ thông số AI giả lập: khai báo giới hạn input/output/context có căn cứ của server. Compiler/Review hiện có thể yêu cầu tới 8192 output token, nên cấu hình phải phù hợp với request thật; không nâng giả giới hạn chỉ để test xanh. Cấu hình OCR cần ngân sách ảnh/prompt (`ocr_page_input`) đúng prompt hiện hành, kích thước ảnh được phép và căn cứ token ảnh do server vận hành cung cấp. Nếu thiếu, navigation sẽ BLOCKED trước upload. OCR probe trên ảnh nhỏ đạt không chứng minh trang A4 của pipeline đủ ngân sách.

Nếu server không công bố dimension của BGE, chạy `model-embedding` trước để xem `observed_dimension`, sau đó cập nhật dimension trong ModelOps và chạy lại `model-embedding`. Mọi thay đổi endpoint/model/key/capacity/dimension làm kiểm định cũ hết hiệu lực: chạy lại các model liên quan trước navigation. Runner không tự đoán capacity/dimension. provider-setup tự áp dụng metadata server và phần khai báo tường minh của profile trước probe; giao diện vẫn có thể dùng để kiểm tra/chỉnh sửa.

## 3. Test model — cửa sổ PowerShell thứ hai

Chạy từng dòng theo thứ tự, chỉ chuyển tiếp khi đạt:

```powershell
.\test-v1-e2e.ps1 run model-discovery --headed
.\test-v1-e2e.ps1 run model-chat --headed
.\test-v1-e2e.ps1 run model-embedding --headed
.\test-v1-e2e.ps1 run model-rerank --headed
.\test-v1-e2e.ps1 run model-ocr --headed
```

Discovery kiểm đủ bốn model trong catalog; bốn lệnh sau thực sự gửi dữ liệu mẫu nhỏ tới model qua diagnostic API ModelOps. HTTP200 quản trị chưa đủ: outcome, upstream HTTP và schema adapter phải hợp lệ. Không có model/key thì BLOCKED, auth/timeout/phản hồi sai thì FAIL.

Các diagnostic giữ trong lịch sử ModelOps, kết quả quan sát nằm trong `model-observation.json` của từng lượt. Đây là kiểm tra hợp đồng inference, chưa phải đánh giá chất lượng tài liệu thật.

## 4. Chuẩn bị mặc định và chạy pipeline

Giữ nguyên phiên và cửa sổ serve. Chạy tiếp:

```powershell
# 7. Tạo workspace E2E, kiểm định còn hiệu lực, gắn đủ bốn model mặc định
.\test-v1-e2e.ps1 run navigation --headed

# 8. Upload PDF có chữ, PDF scan và DOCX vào thư mục thử
.\test-v1-e2e.ps1 run upload --headed

# 9. Chờ bóc tách, kiểm file gốc, sửa text và đọc MD/JSON dẫn xuất
.\test-v1-e2e.ps1 run extraction --headed

# 10. Biên soạn hai nguồn độc lập, kiểm citation và Compiler Review
.\test-v1-e2e.ps1 run compilation --headed

# 11. Duyệt, phát hành và tạo index bằng BGE embedding
.\test-v1-e2e.ps1 run publication --headed

# 12. Hỏi đáp bằng Qwen, hybrid + BGE rerank, kiểm đáp án/citation và trang hội thoại
.\test-v1-e2e.ps1 run chat --headed

# 13. Kiểm người ngoài workspace và tạo/gọi/xoay/thu hồi API key ứng dụng
.\test-v1-e2e.ps1 run permissions --headed

# 14. Chặn xóa nguồn published, dừng trợ lý/thu hồi, purge, kiểm nguồn còn lại và nạp lại
.\test-v1-e2e.ps1 run lifecycle --headed
```

Trong live mode, navigation bắt buộc provider-setup và cả năm chặng model đã PASS. Nó đọc lại đúng model/provider ID từ báo cáo thử và lịch sử current trong DB, kiểm capacity/dimension/OCR budget, rồi cấp riêng bốn model đó làm default theo capability cho workspace E2E. Không lấy model đầu tiên trong danh sách, không sửa default hệ thống hoặc workspace dev. Các chặng sau giữ lựa chọn này; chat kiểm trace để xác nhận Qwen và BGE rerank thực sự được dùng.

Navigation tạo quota tháng hiện tại **1.000.000 token** cho workspace E2E nếu chưa có, theo `test_monthly_token_limit` trong [profile thử](../../scripts/e2e_profiles/qnu-server.json). Đây là hạn mức thử hữu hạn, không phải thông số model; không đặt lại usage, tự tăng quota đã có hoặc bỏ khóa quota. Có thể hạ hạn mức trong profile trước khi chạy. Phạm vi tự cấp quota live này phục vụ yêu cầu chạy trọn pipeline của phiên thử, không áp dụng cho dev/production. Diagnostic upstream và các request pipeline thật có thể phát sinh usage trên server AI; quota QNU không phải giới hạn chi phí upstream toàn hệ thống.

Nếu muốn chạy cả nhóm thay vì từng lệnh, sau khi cấu hình model xong dùng:

```powershell
.\test-v1-e2e.ps1 models --headed
.\test-v1-e2e.ps1 all --headed
```

`models` chạy provider-setup và năm chặng model (có nhập khóa ẩn khi chưa có key); `all` chạy tám chặng nghiệp vụ. Chỉ chạy `all` khi `models` đã PASS; chưa đủ prerequisite thì runner BLOCKED. Không chạy song song hai lệnh. Có thể thay đầu lệnh bằng `make.ps1 v1-e2e`, ví dụ `make.ps1 v1-e2e run upload --headed`.

## 5. Khi lỗi, xem báo cáo và chạy tiếp

```powershell
.\test-v1-e2e.ps1 status
.\test-v1-e2e.ps1 report
```

Kết quả lưu tại `tmp/v1-e2e/<run_id>/runs/<stage>-<timestamp>/`. HTML ở `html/index.html`, JSON Playwright ở `results.json`; nhóm model có observation riêng. Không gửi key/secret/raw response khi chia sẻ lỗi.

- Chặng nào lỗi thì dừng tại đó, sửa nguyên nhân rồi chạy lại chặng đó trên cùng phiên nếu trạng thái còn tương thích. Không cần chạy lại các bước đã đạt chỉ vì một assertion test được sửa.
- Nếu thiếu capacity/dimension/OCR budget: sửa ModelOps, chạy lại probe liên quan, rồi chạy lại navigation trước pipeline. Rerun một probe model sẽ làm các kết quả pipeline hết hiệu lực để buộc gắn cấu hình lại; rerun provider-setup làm toàn bộ model/pipeline hết hiệu lực; rerun discovery còn làm cả bốn probe hết hiệu lực.
- Các tài nguyên đã tạo không tự được xóa khi kết quả hết hiệu lực. Nếu đã phát hành/index/chat rồi mới đổi model, hoặc dừng ở preview hết hạn/trạng thái nửa chừng, nên dùng phiên mới; không tự ghi đè generation hay revision cũ.
- Review có finding thì pipeline dừng để xem nội dung thật, không tự bỏ qua/acknowledge. Model thật có thể trả lời thiếu căn cứ, sai schema hoặc citation; giữ lỗi để xử lý, không đổi thành skip.
- Review `uncertain`/`chat_provider_uncertain` là kết quả chưa rõ, không phải job còn chạy. Test báo lỗi ngay; chạy lại compilation vẫn trỏ review đã lưu trong checkpoint, không tự gửi request mới. Cần xác minh upstream và quyết định recovery trước khi tạo lượt review khác; không xóa record hoặc tự approve để đi tiếp.
- Review hiện được gọi đồng bộ: thời hạn HTTP của bài test live lấy từ timeout model được chọn cộng30giây, tránh client ngắt trước model. Với Qwen timeout300giây trong phiên đang dùng, terminal báo thời hạn này khi bắt đầu review; một lượt có thể mất khoảng2phút. Đây là thời gian chờ, không phải progress giả. Không nâng token output hoặc tự retry để che lỗi.
- Review live mới dùng `structured_output=true` và yêu cầu 8192 token: JSON Schema ghim đủ source/draft ID, còn backend kiểm lại toàn bộ coverage và nội dung. `compilation PASS` chỉ xác nhận bản nháp và báo cáo hợp lệ; nếu verdict `needs_attention` phải xử lý nhận xét trước phát hành, không tự xác nhận finding để làm test xanh.
- `lifecycle` là chặng cuối, thật sự xóa nguồn thử. Sau khi đạt, phiên bị đánh dấu đã dùng cho purge; muốn chạy lại pipeline thì tạo phiên mới.

## 6. Kết thúc

Sau khi xong hoặc muốn bắt đầu phiên mới, ở cửa sổ thứ nhất nhấn Ctrl+C. Sau đó:

```powershell
.\test-v1-e2e.ps1 cleanup
```

Chỉ dọn project/volume E2E riêng, giữ báo cáo; cấu hình ModelOps của phiên thử cũng bị xóa theo DB thử. Không ảnh hưởng dữ liệu dev. Không cần sửa server.json thủ công nếu chỉ còn trạng thái serve cũ; cleanup kiểm khóa/cổng/kết nối trước khi dọn.

## Phạm vi kết luận

Đây là kiểm tra xuyên API/worker/storage với UI smoke và inference server QNU thật. Phần lớn thao tác ghi nghiệp vụ gọi API thật, không phải test mọi form/nút qua chuột. Chưa thay thế benchmark OCR/RAG độc lập, kiểm tra mọi vai trò hoặc tải đồng thời. Bộ mã được kiểm tĩnh/offline khi bổ sung; không được coi toàn luồng live PASS trước khi bạn thực chạy đủ các chặng.
