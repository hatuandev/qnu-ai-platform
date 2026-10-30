# Kiểm thử PDF thật — TB điểm sàn 26

Compiler/review đã có nhánh chia phần và checkpoint: xem [triển khai, migration và cách chạy tiếp](V1_COMPILER_TAI_LIEU_LON.md). Restart serve để nạp mã và migration trước khi chạy lại compilation; chưa có kết quả nghiệm thu cho nhánh này.

## Chạy tiếp sau lỗi output ở compilation

Lượt lỗi đã dùng hết8192token cho suy luận, chưa có JSON. Đã sửa planner chia theo ngân sách đầu ra, phân định owned/context và bật JSON Schema. Lần chạy lại chặng được phép tạo một recovery riêng theo giới hạn output ModelOps, giữ lịch sử lượt lỗi; mặc định compiler8192 không đổi. Không tự chạy model lại khi đang uncertain.

Tại cửa sổ serve nhấn Ctrl+C rồi chạy ` .\test-v1-e2e.ps1 serve ` để nạp mã mới. Ở cửa sổ thứ hai:

```powershell
.\test-v1-e2e.ps1 run admissions-compilation --headed
```

Không cleanup/init, upload hoặc OCR lại. Chỉ sau PASS mới chạy admissions-publication và admissions-chat. Nếu recovery vẫn lỗi thì giữ trạng thái để xem nguyên nhân, không thử lặp đến khi xanh. Các thay đổi này chưa chạy nghiệm thu.

## Phạm vi

Upload nguyên file `docs/tai_lieu/tuyen_sinh/TB điểm sàn 26.pdf` (8 trang), bóc tách, biên soạn, review độc lập, phê duyệt/xuất bản/lập chỉ mục, rồi hỏi 19 câu. Có kho và trợ lý riêng, dùng bốn model đã cấu hình qua ModelOps; không trộn dữ liệu giả của bộ test 14 chặng vào kho này.

[Bộ câu hỏi, đáp án và số trang](../kiem_thu/V1_CAU_HOI_TB_DIEM_SAN_26.md). Dữ liệu máy đọc: `frontendV1/e2e/data/admissions-floor-2026.json`. Nhãn hiện là draft từ việc đọc PDF; cần người duyệt độc lập nếu dùng làm benchmark chính thức.

## Chuẩn bị phiên mới

Phiên trước đã chạy lifecycle nên cần phiên mới. Tại cửa sổ serve cũ nhấn Ctrl+C; không xóa phiên khác hoặc chỉnh checkpoint thủ công. Cleanup dưới đây chỉ dọn phiên E2E đang chọn, gồm DB/khóa/provider của phiên đó; giữ báo cáo.

PowerShell thứ nhất, tại thư mục repo:

```powershell
.\test-v1-e2e.ps1 cleanup
.\test-v1-e2e.ps1 init --mode live
.\test-v1-e2e.ps1 serve
```

Chờ dòng sẵn sàng và giữ cửa sổ này mở. PowerShell thứ hai: chạy từng lệnh, PASS mới chuyển bước tiếp; provider-setup có thể yêu cầu nhập lại khóa tại nơi nhập ẩn như quy trình cũ.

```powershell
.\test-v1-e2e.ps1 run provider-setup --headed
.\test-v1-e2e.ps1 run model-discovery --headed
.\test-v1-e2e.ps1 run model-chat --headed
.\test-v1-e2e.ps1 run model-embedding --headed
.\test-v1-e2e.ps1 run model-rerank --headed
.\test-v1-e2e.ps1 run model-ocr --headed
.\test-v1-e2e.ps1 run navigation --headed
```

Không chạy nhóm `upload/extraction/compilation/publication/chat/lifecycle` dữ liệu giả trong kịch bản này. Chạy nhóm mới:

```powershell
.\test-v1-e2e.ps1 run admissions-upload --headed
.\test-v1-e2e.ps1 run admissions-extraction --headed
.\test-v1-e2e.ps1 run admissions-compilation --headed
.\test-v1-e2e.ps1 run admissions-publication --headed
.\test-v1-e2e.ps1 run admissions-chat --headed
```

## Điều kiện đạt và khi dừng

- Upload: đúng hash PDF đã chốt; tải lại bytes nguồn vẫn giữ nguyên. Thay file sẽ BLOCKED để soạn/đối chiếu lại nhãn.
- Extraction: đủ 8 trang, kết quả sẵn sàng. Không tự sửa văn bản hay điền điểm từ đáp án test vào OCR.
- Compilation: dùng toàn bộ tài liệu, giữ bảng/ngành/phương thức/chú ý/ngoại lệ; review chỉ đạt khi không còn finding. Giữ ngân sách biên soạn hiện tại, output review theo capacity.
- Publication: preview và quyết định theo API có kiểm tra quyền; review gate không có finding; phiên bản published và chỉ mục active. Không tự xác nhận bỏ qua lỗi.
- Chat: mỗi câu một hội thoại để không nhận gợi ý từ câu trước; không đưa expected answer vào prompt. Câu có đáp án phải có số/điều kiện đã chọn và citation đúng phiên bản, hash nguồn, revision và trang; statement chỉ trỏ evidence hợp lệ. Câu ngoài dữ liệu phải trả insufficient_evidence.

PDF 8 trang nhiều ô bảng có thể làm review chạm giới hạn context/output hoặc timeout của model. Khi đó chặng phải FAIL/BLOCKED thật, không tự tăng capacity, cắt nguồn, bỏ nhận xét hay xuất bản tiếp. Gửi log của chặng lỗi để phân tích ngân sách/khả năng xử lý. Thời hạn stage là trần, không phải thời gian bắt buộc phải chờ.

Nếu đã FAIL, giữ phiên và chạy lại đúng chặng sau khi xử lý nguyên nhân. Lượt gửi có idempotency, không tạo lượt mới để thử đến khi xanh. Nếu POST đã trả lỗi model, cùng khóa sẽ giữ lỗi/lượt cũ; cần quyết định xử lý cụ thể thay vì tự retry. Không tự xóa dữ liệu hay purge sau kịch bản; có thể mở kho/trợ lý để thử thêm câu hỏi bằng tay.

## Báo cáo

Mỗi chặng có HTML/JSON tại đường dẫn runner in ra. Chặng chat thêm `admissions-answers.json`: từng ID, câu trả lời/tham chiếu, PASS/FAIL/NOT_RUN, tổng expected/passed/failed/not_run. Dừng ở câu đầu lỗi, các câu còn lại vẫn được đếm NOT_RUN.

PASS chỉ là các kiểm tra tự động đã khai báo, không chứng minh mọi câu diễn giải đúng toàn bộ quan hệ và/hoặc hay OCR chính xác tuyệt đối. Đọc thêm rubric từng câu, đặc biệt F11–F16. `semantic_review=NOT_RUN` giữ nguyên đến khi có đánh giá thực. Không dùng kết quả chưa chạy để báo PASS.
