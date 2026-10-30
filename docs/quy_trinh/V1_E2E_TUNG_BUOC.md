# Chạy kiểm tra V1 theo từng lệnh

Với server AI QNU thật, ưu tiên [hướng dẫn tổng hợp model → toàn bộ pipeline](./V1_TEST_TOAN_LUONG_MODEL_QNU.md), có đủ lệnh và model mặc định theo thứ tự. Tài liệu này tiếp tục mô tả workflow giả lập và cách vận hành runner.

Bộ lệnh dành cho Windows PowerShell, chạy tại thư mục gốc repo. Bạn tự chạy từng chặng và gửi lỗi của chặng đó để xử lý. Chưa nghiệm thu E2E: lần bổ sung mã này chỉ kiểm tra tĩnh, chưa chạy Docker, migration, browser test hay model.

## 1. Chuẩn bị

- Mở Docker Desktop và chờ Docker sẵn sàng.
- Cài môi trường backendV1 và frontendV1 theo hướng dẫn V1 đang có. Runner sử dụng `backendV1/.venv/Scripts/python.exe`, Node và Playwright trong `frontendV1/node_modules`.
- Cài Chromium một lần nếu chưa có:

```powershell
cd D:\DuAnPhanMem\qnu-ai-platform\frontendV1
npx playwright install chromium
cd ..
```

Không cần dừng ứng dụng dev đang chạy. Mỗi phiên E2E tạo Docker Compose project riêng, cổng riêng và dữ liệu riêng; không dùng DB/Redis/MinIO/Qdrant của `v1-dev`. MinIO thử dùng `pgsty/minio:RELEASE.2026-06-18T00-00-00Z`. Khi chạy `serve`, runner chỉ migrate DB vừa tạo cho phiên thử.

## 2. Tạo và mở môi trường thử — cửa sổ PowerShell thứ nhất

```powershell
.\test-v1-e2e.ps1 init
.\test-v1-e2e.ps1 serve
```

Giữ nguyên cửa sổ `serve`. Chờ dòng `E2E workflow: http://127.0.0.1:...` rồi mở cửa sổ PowerShell thứ hai tại repo.

`workflow` là chế độ mặc định: PostgreSQL, Redis, MinIO, Qdrant, Gotenberg, API, worker và frontend đều chạy thật; upstream AI được giả lập theo hợp đồng. Chế độ này kiểm tra việc nối luồng, lưu kết quả và truy vết, không chứng minh chất lượng OCR/LLM hay model thật hoạt động.

## 3. Chạy từng chặng — cửa sổ thứ hai

Chạy từng dòng theo thứ tự. Chỉ chuyển tiếp khi chặng trước PASS.

```powershell
.\test-v1-e2e.ps1 run navigation --headed
.\test-v1-e2e.ps1 run upload --headed
.\test-v1-e2e.ps1 run extraction --headed
.\test-v1-e2e.ps1 run compilation --headed
.\test-v1-e2e.ps1 run publication --headed
.\test-v1-e2e.ps1 run chat --headed
.\test-v1-e2e.ps1 run permissions --headed
.\test-v1-e2e.ps1 run lifecycle --headed
```

Bỏ `--headed` để trình duyệt chạy ẩn. Có thể dùng `make.ps1`, ví dụ:

```powershell
.\make.ps1 v1-e2e run upload --headed
```

| Chặng | Phạm vi kiểm tra được viết trong mã |
| --- | --- |
| `navigation` | Đăng nhập qua cầu nối local, tạo workspace thử, chuẩn bị quota hữu hạn cho workflow, cấp provider theo capability, mở trang kho và kiểm tra menu chính. |
| `upload` | Tạo kho/thư mục thử, upload PDF có chữ, PDF scan và DOCX; kiểm tra tạo processing run, từ chối nội dung trùng; mở giao diện kho và nút tải tài liệu. |
| `extraction` | Chờ tiến độ trang và kết quả thật; so hash tệp gốc, lưu sửa văn bản, đọc Markdown/JSON dẫn xuất và kiểm tra tệp gốc giữ nguyên. |
| `compilation` | Biên soạn hai nguồn độc lập, kiểm tra nội dung/citation thuộc nguồn; chạy Compiler Review và đọc báo cáo. |
| `publication` | Đọc review gate, duyệt và phát hành qua preview/commit, tạo chỉ mục và kiểm tra chỉ mục hoạt động có chunk. Có finding thì dừng, không tự bỏ qua. |
| `chat` | Tạo trợ lý/hội thoại, hỏi dữ kiện trong fixture, kiểm tra câu trả lời và citation đúng phiên bản, mở hội thoại trên FE. |
| `permissions` | Người ngoài workspace bị từ chối; tạo API key ứng dụng, gọi models/chat gateway, không lộ secret trong danh sách; xoay/thu hồi và kiểm tra khóa cũ bị chặn. |
| `lifecycle` | Chặn xóa nguồn đang phát hành; dừng trợ lý, thu hồi bản phát hành rồi purge; kiểm tra PostgreSQL, mọi S3 object version/delete marker đã ghi nhận và point Qdrant; nguồn khác vẫn tải/hỏi đáp được; nạp lại cùng tệp. |

Đây là kiểm tra kết hợp giao diện Playwright và gọi API thật. Các bước ghi nghiệp vụ chủ yếu gọi API để kiểm tra worker/storage xuyên suốt. Bộ này chưa bao phủ mọi thao tác chuột trên từng form, mọi vai trò/quota, responsive hay chất lượng RAG. Các spec khung cũ ở `frontendV1/e2e/01_...09_...` được giữ lại, nhưng không thuộc suite mặc định `e2e/stages`.

Nếu muốn chạy liên tiếp, dùng lệnh sau trên phiên mới:

```powershell
.\test-v1-e2e.ps1 all --headed
```

## 4. Xem kết quả và chạy lại

```powershell
.\test-v1-e2e.ps1 status
.\test-v1-e2e.ps1 report
```

Mỗi chặng có kết quả riêng: PASS, FAIL hoặc BLOCKED; chưa chạy là NOT RUN. Runner chỉ ghi PASS khi Playwright thực chạy đúng một bài, không có skip/flaky/failure. Lệnh dừng ở lỗi đầu tiên; thiếu chặng tiên quyết sẽ BLOCKED.

Kết quả nằm trong `tmp/v1-e2e/<run_id>/runs/<stage>-<timestamp>/`: báo cáo HTML trong `html/index.html`, JSON trong `results.json`, ảnh lỗi giao diện nếu có. `report` in đường dẫn, không tự khởi động server báo cáo. Trace/video tắt để tránh ghi token và secret vào bản ghi mạng. Chặng API key cũng tắt ảnh chụp.

Trạng thái tài nguyên thử được lưu trong `checkpoint.json`; không phải transcript hay session của ứng dụng thật. Sau khi sửa nguyên nhân, có thể chạy lại chặng thất bại trên cùng phiên. Các thao tác có checkpoint hoặc khóa chống lặp; không phải mọi tình huống mất kết nối giữa response và ghi checkpoint đều tự phục hồi. Nếu gặp preview hết hạn, trạng thái nửa chừng hoặc muốn bắt đầu sạch, dừng `serve`, `cleanup`, rồi `init` phiên mới. Chạy lại chặng trước sẽ làm các kết quả chặng sau hết hiệu lực.

Nếu phiên workflow tạo bằng mã cũ đã dừng ở `extraction` với `quota_not_configured`, giữ `serve` đang chạy và chạy lại chính chặng này:

```powershell
.\test-v1-e2e.ps1 run extraction --headed
```

Chặng này kiểm tra mã workspace thuộc đúng phiên thử, tạo quota tháng hiện tại là 1.000.000 token nếu chưa được cấu hình, rồi tạo một lượt bóc tách `auto` mới cho nguồn đã lỗi đúng mã trên. Lưu ID lượt lỗi trước trong checkpoint, không sửa raw OCR hay tệp gốc. Chỉ phục hồi tự động một lần mỗi nguồn; lỗi khác vẫn FAIL, quota đang khóa/hết vẫn BLOCKED, không tự tăng hạn mức hoặc đặt lại usage. Nếu đã có bản biên soạn hoặc đang ở live mode, không tự đổi lượt xử lý nguồn. Sau khi extraction PASS, tiếp tục compilation và các chặng còn lại, không cần chạy lại navigation/upload.

Sau khi `lifecycle` PASS, phiên đã được dùng để xóa/nạp lại nên runner không cho chạy lại các chặng trên dữ liệu đó. Tạo phiên mới cho vòng tiếp theo. Nếu lệnh bị tắt cưỡng bức và còn `stage.lock`, chỉ gỡ khóa trong thư mục phiên sau khi đã xác nhận không còn bài test đang chạy.

Các tệp `private-env.json`, `compose.json` và log dịch vụ nằm trong thư mục `tmp` đã bỏ qua bởi Git. Chúng có credential hạ tầng thử; không đưa cả thư mục này lên Git hoặc gửi công khai. Khi cần hỗ trợ, gửi tên chặng, HTTP/error code và phần báo lỗi đã loại secret.

## 5. Dừng và dọn dữ liệu thử

Ở cửa sổ thứ nhất, nhấn Ctrl+C để dừng API/worker/FE thử. Sau đó:

```powershell
.\test-v1-e2e.ps1 cleanup
```

Lệnh chỉ dọn Docker project và volume của phiên E2E đã xác minh; giữ báo cáo/checkpoint cục bộ. Không có `FLUSHDB` trên Redis dev. Nếu `serve` bị tắt cưỡng bức, kiểm tra và dừng các dịch vụ của phiên trước khi dọn; runner không tự giết tiến trình không xác định.

Nếu `server.json` còn ghi đang chạy sau khi cửa sổ serve đã đóng, bản runner mới kiểm tra khóa tiến trình, ba cổng phục vụ và các kết nối local tới cổng hạ tầng của phiên. Nếu tất cả đã dừng, `cleanup` tự nhận diện trạng thái cũ và cho dọn; không cần sửa JSON thủ công. Nếu còn dịch vụ/worker kết nối, lệnh từ chối và báo tên cổng hoặc PID; nếu không đọc được thông tin kết nối cũng từ chối. `serve` mới giữ khóa hệ điều hành suốt khởi động/chạy/dừng, đồng thời cập nhật trạng thái khi preflight thất bại, để không kẹt lại cờ đang chạy. Không có thao tác tự kill tiến trình.

## 6. Thử model thật sau này

Đã có nhóm `model-*` để thử riêng bốn model QNU sau khi thêm qua ModelOps. Xem [hướng dẫn test model QNU](./V1_TEST_MODEL_QNU.md) trước khi chạy pipeline live. Nhóm này dùng diagnostic API thật, không AI giả lập.

Tạo phiên khác sau khi dọn phiên trước:

```powershell
.\test-v1-e2e.ps1 init --mode live
.\test-v1-e2e.ps1 serve
```

Mở URL frontend E2E do `serve` in ra. Cấu hình provider/key/capacity/dimension/OCR budget cho bốn model QNU trong ModelOps của phiên thử, rồi chạy provider-setup và đủ nhóm model-* trước. Bước provider-setup đã tự kiểm tạo provider/key/model, nhận key bằng nhập ẩn trong terminal; chỉ capacity/dimension/ngân sách ảnh cần khai báo theo server thật. Navigation live sẽ kiểm lịch sử còn current, gắn đúng model đã test làm default workspace và cấp quota thử hữu hạn nếu chưa có theo profile. Không sửa quota đã có, không lấy LLM key từ `.env` hay sao chép credential DB dev. Làm theo [hướng dẫn tổng hợp](./V1_TEST_TOAN_LUONG_MODEL_QNU.md) để có đầy đủ thứ tự lệnh.

Model thật có thể trả review finding hoặc nội dung khác fixture; giữ lỗi để điều tra, không đổi assertion thành skip. Live mode không chạy mock AI và có thể phát sinh usage. Chỉ dùng endpoint và dữ liệu mà bạn cho phép. Phạm vi chặng live giống workflow; không thay thế benchmark độc lập.

## 7. Khi gặp lỗi khởi động

### Phiên cũ lỗi `docx_conversion_failed` với DOCX mẫu

Bản fixture DOCX ban đầu thiếu khai báo OPC bắt buộc (`[Content_Types].xml` và root relationship), khiến LibreOffice trong Gotenberg trả 500. Bản sửa tạo đủ package, styles, bảng và footnote, kèm kiểm tra cấu trúc trước upload. Đây là lỗi fixture, không phải cấu hình server AI. Việc kiểm tra XML không thay thế nghiệm thu chuyển đổi LibreOffice thực tế.

Vì DOCX hỏng đã được upload/lưu thành revision gốc, cần phiên thử mới để lấy file sửa; retry OCR trên cùng revision không thay đổi bytes. Ở cửa sổ `serve` cũ, nhấn Ctrl+C. Sau đó tại repo:

```powershell
.\test-v1-e2e.ps1 cleanup
.\test-v1-e2e.ps1 init
.\test-v1-e2e.ps1 serve
```

Giữ cửa sổ `serve`; ở cửa sổ thứ hai chạy lại `navigation`, `upload`, `extraction` theo mục 3. Bản sửa quota được áp dụng ngay ở navigation. Không chạy `v1-dev`, không phải gửi API key/model server thật. Cleanup giữ báo cáo cũ và chỉ dọn project E2E riêng. Runner không ghi đè fixture/revision cũ; mở lại `serve` trên phiên có fixture không hợp lệ sẽ báo lỗi để tạo phiên mới.

### Các lỗi khác

- Nếu `permissions` từng dừng ở kỳ vọng 401 nhưng nhận 403 sau xoay/thu hồi khóa: backend hiện trả `403` kèm `error.code=api_key_inactive` cho khóa đã có nhưng ngừng hoạt động; khóa không tồn tại trả `401/invalid_api_key`. Spec đã sửa để kiểm tra chính xác từng cặp status/code, kiểm tra khóa mới vẫn gọi được models sau xoay. Giữ serve và chạy lại `run permissions --headed`; không cần tạo phiên mới hoặc chạy lại các chặng đã đạt. Chỉ chạy `lifecycle` khi permissions PASS.

- Docker chưa mở/image chưa kéo được: đọc lỗi `init`; có thể kiểm tra project bằng tên `qnu-e2e-<run_id>` trong Docker Desktop, dọn phiên rồi tạo lại.
- API/worker/frontend dừng: đọc `service-0.log`, `service-1.log`, `service-2.log` trong thư mục phiên; không gửi nguyên log chứa thông tin riêng.
- Thiếu browser: chạy `npx playwright install chromium` trong `frontendV1`.
- Thiếu font tiếng Việt: đặt `E2E_FONT_PATH` trỏ đến tệp font Unicode trước `serve`; Windows mặc định dùng Arial.
- Cổng bị chiếm: runner từ chối khởi động; kiểm tra tiến trình hoặc tạo phiên mới. Không tự đổi cấu hình dev.
