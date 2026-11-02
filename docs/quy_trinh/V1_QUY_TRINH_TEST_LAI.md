# V1 — Chạy tiếp sau tắt máy hoặc test lại từ đầu

Chạy tại `D:\DuAnPhanMem\qnu-ai-platform`. **Muốn test lại từ đầu, làm mục B theo đúng thứ tự.** Mục A chỉ dành cho tiếp tục phiên cũ sau khi bật máy. Tắt máy không bắt buộc xóa phiên thử.

Profile QNU/9router bật `wait_for_completion` cho model chat khi chạy `provider-setup`: thời gian chờ phản hồi model không còn bị cắt ở 300 giây. Trường `timeout_seconds` vẫn dùng cho kết nối/gửi dữ liệu; không đặt thành 0. Trong ModelOps → model → chính sách vận hành, bật **Chờ model xử lý xong** cho provider khác nếu cần. Thay đổi áp dụng cho lượt mới; không gửi lại lượt `uncertain` tự động. Worker hiện còn giới hạn tác vụ riêng 30 phút; đây không phải timeout phản hồi model và chưa được bỏ trong thay đổi cấu hình này.

Nếu muốn kiểm riêng PDF thật “TB điểm sàn 26” và hỏi đáp sau xuất bản, dùng [hướng dẫn riêng](V1_TEST_TB_DIEM_SAN_26.md); không dùng các fixture mặc định của mục B để thay file thật.

## A. Bật máy và tiếp tục phiên đang có

1. Mở Docker Desktop, chờ sẵn sàng.
2. Mở PowerShell thứ nhất, xem phiên:

```powershell
.\test-v1-e2e.ps1 status
```

3. Nếu chưa có serve và cần bật lại container cũ:

```powershell
$e2eRun = (Get-Content .\tmp\v1-e2e\active.json | ConvertFrom-Json).run_id
docker compose -f ".\tmp\v1-e2e\$e2eRun\compose.json" -p "qnu-e2e-$e2eRun" start
.\test-v1-e2e.ps1 serve
```

Giữ cửa sổ thứ nhất. Chờ dòng `E2E live: http://127.0.0.1:...`. Nếu serve đã chạy thì dùng phiên đó, không mở thêm.

4. Mở PowerShell thứ hai và chạy từ chặng chưa đạt. Giữ cấu hình/nguồn/run cũ; không `cleanup`/`init`. Những chặng đã đạt được giữ trong checkpoint. Sau khi lifecycle đạt, phiên đã purge xong và không dùng để replay pipeline; chuyển sang cáchB.

Chạy lại một chặng đã đạt thường đọc lại dữ liệu/report đã lưu, không nhất thiết gọi model lại. Muốn kiểm toàn bộ lượt sinh từ đầu thì dùng cáchB. Lượt review uncertain hoặc lỗi cùng ngân sách không tự được gửi lại. Ngoại lệ: khi chủ động chạy lại compilation, review lỗi `chat_output_truncated` được tạo lượt mới nếu vẫn cùng provider và giới hạn output model hiện tại lớn hơn ngân sách lượt lỗi; lượt cũ được giữ nguyên.

Review mặc định dùng capacity của model và phần context còn lại, thay mức cố định 8192. Có thể nhập giới hạn riêng khi cần; ngân sách biên soạn vẫn giữ cấu hình hiện tại. Sau khi cập nhật mã, nhấn Ctrl+C ở cửa sổ `serve`, chạy lại `.\test-v1-e2e.ps1 serve`, rồi ở cửa sổ khác chạy `.\test-v1-e2e.ps1 run compilation --headed`. Giữ phiên hiện tại, không cleanup/init để tiếp tục lượt đang dở.

Nếu publication bị chặn vì review phát hiện khối cần kiểm tra nhưng chưa có text và bản nháp cũ chưa ghi giới hạn này: sau khi restart serve với bản sửa phiên 740, chạy lại `run compilation --headed`, rồi `run publication --headed`. Chặng compilation chỉ tạo bản biên soạn mới cho trường hợp này, giữ bản cũ trong lịch sử; bản mới ghi chú giới hạn có citation và được review lại. Publication đăng ký phiên bản mới trong cùng tài liệu. Không tự chấp nhận finding hoặc suy nội dung ảnh; nếu review mới vẫn có finding thì vẫn dừng để kiểm tra.

Sau khi cập nhật mã backend, runner sẽ yêu cầu restart `serve` nếu mã đang phục vụ chưa được xác nhận hoặc đã khác mã trên đĩa. Dừng bằng Ctrl+C tại đúng cửa sổ serve, chạy `.\test-v1-e2e.ps1 serve` và chờ dòng sẵn sàng, sau đó mới chạy lại chặng. Nếu lần trước đã tạo bản trung gian bằng mã cũ rồi lỗi `Expected retained / Received undefined`, bản sửa phiên 741 lấy finding của bản gốc trong lịch sử cùng tài liệu để tạo lượt sửa mới bằng khóa riêng; không dùng lại kết quả cũ của khóa `source-limits-v1`. Không cleanup/init hoặc chỉnh checkpoint bằng tay.

## B. Tạo phiên mới để test lại toàn bộ

Mở Docker Desktop và chờ sẵn sàng. Nếu còn bài test đang chạy, chờ kết thúc; đóng tab trình duyệt của phiên cũ và nhấn Ctrl+C tại đúng cửa sổ serve cũ trước khi dọn. `cleanup` xóa DB/nguồn/cấu hình ModelOps và khóa đã lưu của **phiên E2E**, giữ báo cáo; không dùng lệnh này nếu muốn tiếp tục phiên cũ. Sau khi vừa bật máy, chưa mở serve, có thể dọn phiên cũ như sau.

PowerShell thứ nhất:

```powershell
.\test-v1-e2e.ps1 cleanup
.\test-v1-e2e.ps1 init --mode live
.\test-v1-e2e.ps1 serve
```

Nếu chưa từng có phiên cũ thì bỏ cleanup. Chỉ init một lần. Giữ cửa sổ serve, đợi URL sẵn sàng.

PowerShell thứ hai — chạy từng dòng, chỉ sang dòng sau khi PASS:

```powershell
.\test-v1-e2e.ps1 run provider-setup --headed
```

Điền E2E_QNU_API_KEY và E2E_9ROUTER_API_KEY một lần trong `.env` ở root để provider-setup nạp qua ModelOps khi phiên chưa có key active; biến trống thì nhập ẩn trong terminal. Không commit file này. **provider-setup hiện tự lấy và lưu capacity từ server**, đồng thời bổ sung các mục E2E đã khai báo trong profile QNU (timeout, giới hạn input thử và ngân sách ảnh OCR đã xác minh). Sau khi PASS, tiếp tục các lệnh model bên dưới; **không còn bước bắt buộc nhập capacity thủ công trong giao diện**.

Profile dùng **key QNU → key 9router → chọn 1 Qwen hoặc 2 Luna (`cx/gpt-6-luna`)**. Hai key lấy từ ModelOps hoặc hai biến E2E trong `.env` ở root; chỉ hỏi nhập ẩn khi thiếu. Chat/Compiler/review dùng lựa chọn đó; OCR/embedding/rerank giữ QNU. Nếu chọn 9router mà catalog thiếu context/output, terminal sẽ hỏi thông số upstream thực tế, không tự đoán; để trống thì dừng an toàn. Không gửi key vào chat/source/report. Chi tiết và phạm vi ngoại lệ E2E tại [chọn provider chat](./V1_TEST_TOAN_LUONG_MODEL_QNU.md#chọn-qwen-hoặc-luna-qua-9router).

Nếu gặp lỗi 9router trả HTTP 200 nhưng danh sách không hợp lệ ở bản trước phiên 753: backend cũ chỉ nhận tối đa 500 model, trong khi catalog đã quan sát có 638 model. Bản sửa nhận tối đa 5000 model, vẫn kiểm tra từng ID/metadata và không cắt mất model cuối danh sách. Nhấn Ctrl+C tại cửa sổ `serve`, chạy lại `.\test-v1-e2e.ps1 serve`, đợi dòng `E2E live`, rồi chạy lại `.\test-v1-e2e.ps1 run provider-setup --headed` ở cửa sổ thứ hai. **Không cleanup/init**; key đang hoạt động được dùng lại. Chọn `2` và nhập context/output upstream thực tế nếu được hỏi. Hai thông số này chưa có trong catalog 9router đã kiểm tra; không lấy giới hạn Qwen để điền thay.

Nếu `model-chat` chỉ lỗi so sánh `cx/gpt-6-luna` với `gpt-6-luna`, profile hiện khai báo cặp tên này từ quan sát model thật phiên 805. Tên yêu cầu vẫn phải khớp hoàn toàn; phản hồi chỉ được nhận tên gốc hoặc alias đã khai báo đúng provider/model. Sau khi chặng đang chạy kết thúc, chạy lại `.\test-v1-e2e.ps1 run model-chat --headed`; không cần restart serve, cleanup/init hoặc chạy lại các chặng đã PASS. Báo cáo giữ cả requested_model và observed_model; tên upstream do gateway báo không tự chứng minh danh tính model thực tế.

Phiên mới có DB ModelOps mới. Script đăng ký model mới kèm snapshot discovery và đồng bộ model đã có; không tự đoán capacity khi server thiếu metadata. Profile QNU chỉ phục vụ endpoint/model này, không áp dụng thành mặc định cho nhà cung cấp khác.

### Kiểm tra thông số đã lưu (tùy chọn)

Mở đúng URL FE mà cửa sổ serve vừa in để kiểm tra. Nếu cần tự lấy lại hoặc điều chỉnh thông số:

1. Vào **Nhà cung cấp → Server AI QNU → Nhập từ /models**.
2. Bấm **Lấy lại** để đọc metadata hiện tại từ server.
3. Chọn **cả bốn model đã được provider-setup tạo**, rồi bấm **Áp dụng**. Đây là đồng bộ thông số, không thêm lại model. Nếu báo xung đột thì dừng kiểm tra cấu hình; không điền số khác chỉ để bỏ lỗi.
4. Kiểm tra thông số dự kiến dưới đây. Nếu server trả khác, đối chiếu cấu hình phục vụ trước khi tiếp tục.

| Model | Context lấy từ server | Output lấy từ server | Dimension lấy từ server |
| --- | ---: | ---: | ---: |
| qwen3.8-27b-q4 | 131072 | 16384 | không áp dụng |
| bge-m3 | 8192 | không công bố | 1024 |
| bge-reranker-v2-m3 | 8192 | không công bố | không áp dụng |
| nemotron-parse | 16384 | 8192 | không áp dụng |

Các trường không công bố giữ trống/chưa biết. **Không phải nhập tay lại context/output/dimension trong bảng** khi lấy thành công. Context của BGE đã cung cấp giới hạn token dùng chung, không cần tự đặt thêm output cho embedding/rerank.

### Thông số E2E bổ sung từ profile

provider-setup áp dụng các cấu hình sau từ [profile QNU](../../scripts/e2e_profiles/qnu-server.json). Input/OCR đã được người vận hành lưu thì được giữ nguyên. Có thể dùng nút bút chì cạnh model để kiểm tra hoặc sửa nếu cấu hình vận hành đã đổi:

| Model | Cấu hình bổ sung cho lượt E2E này |
| --- | --- |
| Qwen | Timeout 300 giây; input riêng để trống. Compiler/Review vẫn yêu cầu 8192 token mỗi lượt, thấp hơn output model 16384. |
| BGE-M3 | Timeout 60 giây; input riêng có thể để trống vì đã có context 8192. |
| BGE reranker | Timeout 60 giây; nếu dùng lại chính sách thử cũ thì giữ input riêng 1024. Đây là giới hạn khai báo riêng, không suy từ metadata. |
| Nemotron | Timeout 180 giây; bổ sung đủ ngân sách ảnh bên dưới. Input riêng để trống. |

Timeout là thời hạn chờ của QNU, không phải capacity. `/v1/models` hiện không công bố timeout, giới hạn input riêng hoặc ngân sách token ảnh.

**Ngân sách ảnh Nemotron được profile điền khi còn thiếu:** rộng tối đa 1664, cao 2048, cận trên input 4096 và hash prompt đã ghim. Không cần chạy lệnh lấy hash để lưu tay nữa. Lệnh dưới chỉ dùng đối chiếu khi prompt hoặc server thay đổi:

```powershell
Push-Location backendV1
.\.venv\Scripts\python.exe -c "import hashlib; from qnu.domains.ocr.config import OCR_PROMPT; print(hashlib.sha256(OCR_PROMPT.encode('utf-8')).hexdigest())"
Pop-Location
```

Ngân sách 4096 có căn cứ phép đo ảnh tối đa 3336 token và processor của server đã kiểm; nếu đổi model/processor/prompt/kích thước ảnh phải xác minh lại. Không suy từ Base64 hoặc điền số để bỏ guard.

### Chạy các chặng còn lại

Sau provider-setup PASS, tiếp tục trong PowerShell thứ hai. Chạy **từng dòng**, chờ PASS rồi mới chạy dòng tiếp theo. Các lệnh dưới đây tiếp tục chặng2–14; provider-setup ở trên là chặng1:

```powershell
.\test-v1-e2e.ps1 run model-discovery --headed
.\test-v1-e2e.ps1 run model-chat --headed
.\test-v1-e2e.ps1 run model-embedding --headed
.\test-v1-e2e.ps1 run model-rerank --headed
.\test-v1-e2e.ps1 run model-ocr --headed

.\test-v1-e2e.ps1 run navigation --headed
.\test-v1-e2e.ps1 run upload --headed
.\test-v1-e2e.ps1 run extraction --headed
.\test-v1-e2e.ps1 run compilation --headed
.\test-v1-e2e.ps1 run publication --headed
.\test-v1-e2e.ps1 run chat --headed
.\test-v1-e2e.ps1 run permissions --headed
.\test-v1-e2e.ps1 run lifecycle --headed
```

Không paste cả khối để bỏ qua lỗi: dừng tại FAIL/BLOCKED, xem `status`/`report`. Compilation PASS chưa bảo đảm được phát hành: nếu review là needs_attention hoặc có finding, dừng để đối chiếu trước publication; không tự acknowledge để test xanh. Lifecycle thực sự xóa tài liệu thử.

Nếu đang dùng phiên cũ tạo trước bản sửa tự đồng bộ và còn lỗi capacity: khi chưa upload, chạy lại provider-setup, rồi chạy lại năm chặng model trước navigation. Nếu đã upload thì giữ phiên và kiểm tra cấu hình, không bật/tắt provider qua provider-setup.

Nếu một chặng FAIL/BLOCKED, giữ cửa sổ serve và xem:

```powershell
.\test-v1-e2e.ps1 status
.\test-v1-e2e.ps1 report
```

Gửi tên chặng/mã lỗi đã bỏ secret để xử lý. Không lặp init, xóa lock hoặc chạy
chặng sau khi prerequisite chưa đạt. `uncertain` của review cần kiểm tra kết quả
upstream trước khi quyết định tạo lượt mới; chạy lại compilation không tự retry.

## Ghi chú: ba nhận xét hình ảnh ở lượt thử trước

Chúng cùng liên quan một vùng hình ở `thong_bao_scan_2024.pdf`: canonical block loại figure, text rỗng, bbox gần phủ toàn trang. Ba vị trí bản nháp bị đánh dấu uncertain là tiêu đề Hình ảnh, đoạn ghi hình chưa có text OCR và mục unknown về nội dung hình.

Ở mã cũ, source_units chỉ thêm block thường khi `block.text` có giá trị, làm mất block figure rỗng mà bản nháp nhắc tới. Từ phiên 736, review giữ cả block rỗng cùng ID, vị trí, loại, nguồn trích xuất và cờ cần rà soát. Text rỗng của một block không chứng minh cả trang không có chữ OCR; cùng trang có thể có các block chữ khác.

Review kiểm bản nháp có trung thành với dữ liệu trích xuất đã cấp hay không. Nếu bản nháp ghi đúng giới hạn/unknown thì nguồn có thể được ghi nhận là đã thể hiện giới hạn đó; điều này không xác nhận OCR đúng từ ảnh gốc. Nếu tự đoán nội dung hoặc vẫn không đối chiếu được thì phải giữ finding. Không tự xác nhận bỏ qua finding để chạy tiếp.

Compilation PASS xác nhận draft/citation/report hợp lệ về hợp đồng; không khẳng định report không có finding. Publication chỉ chạy tiếp khi gate phù hợp. Bản sửa review áp dụng cho lượt review mới sau khi API nạp mã mới; báo cáo cũ được giữ nguyên. Chạy lại compilation dùng checkpoint cũ nên không tự tạo review thay thế.

Hướng dẫn chi tiết: [Model → pipeline live](./V1_TEST_TOAN_LUONG_MODEL_QNU.md).
