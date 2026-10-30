# V1 — Chạy tiếp sau tắt máy hoặc test lại từ đầu

Chạy tại `D:\DuAnPhanMem\qnu-ai-platform`. Chọn đúng một trong hai cách sau. Tắt máy không đồng nghĩa phải xóa phiên thử.

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

Chạy lại một chặng đã đạt thường đọc lại dữ liệu/report đã lưu, không nhất thiết gọi model lại. Muốn kiểm toàn bộ lượt sinh từ đầu thì dùng cáchB. Lượt review failed/uncertain không tự được gửi lại chỉ bằng việc lặp compilation.

## B. Tạo phiên mới để test lại toàn bộ

Mở Docker Desktop. Nếu serve cũ còn chạy, dừng serve đó trước. `cleanup` xóa DB/nguồn/cấu hình ModelOps và khóa đã lưu của **phiên E2E**, giữ báo cáo; không dùng lệnh này nếu muốn tiếp tục phiên cũ. Sau khi vừa bật máy, chưa mở serve, có thể dọn phiên cũ như sau.

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

Nhập key tại lời nhắc ẩn. Sau đó mở URL FE của phiên mới, vào Nhà cung cấp → chi tiết → sửa từng model để khai báo capacity. Phiên mới không kế thừa cấu hình ModelOps cũ.

Các giá trị đã được người vận hành cung cấp/test trong phiên hiện tại, chỉ dùng lại khi server vẫn giữ cùng cấu hình:

| Model | Context | Input riêng | Output tối đa | Khác |
| --- | ---: | ---: | ---: | --- |
| Qwen | 131072 | để trống | 16384 | timeout300giây; Compiler/Review yêu cầu8192 |
| BGE-M3 | 8192 | 8192 | để trống | dimension1024 |
| BGE reranker | 8192 | 1024 | để trống | — |
| Nemotron | 16384 | để trống | 8192 | ngân sách ảnh bên dưới |

Nemotron: rộng tối đa1664, cao2048, cận trên input4096. Lấy đúng hash prompt hiện hành bằng lệnh sau:

```powershell
Push-Location backendV1
.\.venv\Scripts\python.exe -c "import hashlib; from qnu.domains.ocr.config import OCR_PROMPT; print(hashlib.sha256(OCR_PROMPT.encode('utf-8')).hexdigest())"
Pop-Location
```

Ngân sách4096 có căn cứ phép đo ảnh tối đa3336token và processor của server đã kiểm; nếu đổi model/processor/prompt/kích thước ảnh phải xác minh lại. Không suy từ Base64 hoặc điền số để bỏ guard.

Sau khi lưu cấu hình:

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

Không paste cả khối để bỏ qua lỗi: dừng tại FAIL/BLOCKED, xem `status`/`report`. Review có finding cần đối chiếu trước publication, không tự acknowledge để test xanh. Lifecycle thực sự xóa tài liệu thử.

## Ba nhận xét hình ảnh trong phiên hiện tại là gì?

Chúng cùng liên quan một vùng hình ở `thong_bao_scan_2024.pdf`: canonical block loại figure, text rỗng, bbox gần phủ toàn trang. Ba vị trí bản nháp bị đánh dấu uncertain là tiêu đề Hình ảnh, đoạn ghi hình chưa có text OCR và mục unknown về nội dung hình.

Mã tạo source_units cho review hiện chỉ thêm block thường khi `block.text` có giá trị. Block figure rỗng bị bỏ qua; context review cũng không gửi toàn bộ pages/evidence. Vì vậy reviewer không nhận source unit cho citation hình mà bản nháp nhắc tới. Đây là thiếu bằng chứng được chuyển sang review, đồng thời phần ảnh chưa có văn bản OCR; không phải ba ảnh hỏng hay ba lần kết nối lỗi. Chưa kết luận nội dung ảnh đã được OCR chính xác.

Compilation PASS xác nhận draft/citation/report hợp lệ về hợp đồng; không khẳng định report không có finding. Hiện chưa phát hành. Bước xử lý tiếp là đối chiếu trang gốc, kết quả OCR và cách đưa metadata block không text vào review, giữ unknown cho phần chưa đọc được.

Hướng dẫn chi tiết: [Model → pipeline live](./V1_TEST_TOAN_LUONG_MODEL_QNU.md).
