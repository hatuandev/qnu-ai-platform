# Context604 — Đối soát 24 proof bị báo thiếu ở Context603

Ngày 23/10/2026. Đây là đối chiếu nguồn do Codex thực hiện, chưa phải quyết định phê duyệt của người dùng.

24/24 span cũ khớp chính xác source revision, unit ID, start/end và SHA-256 nguyên văn trong catalog thử mới. ID proof đổi vì collection/binding thử khác; không ghép bằng cách đoán theo tên file. JSON đầy đủ nằm trong `backend/storage/context604/missed24-map-private.json` (bằng chứng local, không đưa corpus vào Git).

S1 = nguồn phương hướng 2024; S2 = báo cáo tư vấn tuyển sinh 2025 có nhãn dự thảo; S3 = thuyết minh tuyển sinh 2026. Cả ba là cùng bytes DOCX đã dùng ở Context602–603.

## Kết luận về nội dung

- **1 ngày ban hành** cần giữ role publication 2023, tách khỏi dữ liệu tuyển sinh 2024. Xác nhận nguồn ghi ngày không phải chứng nhận pháp lý độc lập.
- **20 dòng danh mục ngành** không chứa chỉ tiêu theo ngành. Chúng có thể hỗ trợ phạm vi nếu có association riêng được xác minh; không được tự sinh quota ngành hoặc gắn toàn bộ danh mục vào mọi assertion. Raw/canonical/proof vẫn giữ đủ.
- **1 đoạn nhập học** có tỷ lệ và mẫu số. Chưa có căn cứ riêng xác nhận mẫu số là tổng chỉ tiêu; không biến số đó thành quota chắc chắn. Kiểm tra toàn canonical S2 không tìm thấy phát biểu “chỉ tiêu” gắn số này.
- **1 căn cứ văn bản** có năm ban hành 2024 liên quan phương hướng 2025. Nó không cung cấp giá trị quota; không dùng năm ban hành làm năm dữ liệu.
- **1 chỉ tiêu đợt bổ sung** là metric khác với tổng chỉ tiêu đại học chính quy năm. Nếu biên soạn, phải giữ điều kiện đợt/phương thức và tách metric; không cộng vào tổng.

Vì vậy “24 cảnh báo” không đồng nghĩa “thiếu 24 dữ kiện chỉ tiêu”. Không xóa ledger gốc: artifact mới lưu review ban đầu, hai phân loại độc lập, repair nếu có và phần còn thiếu. Ngữ cảnh có association chưa đồng thuận chỉ là candidate_only/effective=false; thiếu fact hoặc điều kiện thực sự vẫn chặn.

## Ánh xạ từng span

| # | Nguồn | Unit | Start:end | Vai trò sau đối soát |
|---:|---|---|---|---|
| 1 | S1 | `qnu:p003` | `256:314` | Cần giữ ngày ban hành được nguồn ghi; role publication |
| 2 | S1 | `qnu:r009` | `5404:5437` | Ngữ cảnh danh mục, không có số chỉ tiêu ngành |
| 3 | S1 | `qnu:r007` | `5333:5368` | Ngữ cảnh danh mục, không có số chỉ tiêu ngành |
| 4 | S1 | `qnu:r008` | `5369:5403` | Ngữ cảnh danh mục, không có số chỉ tiêu ngành |
| 5 | S1 | `qnu:r006` | `5296:5332` | Ngữ cảnh danh mục, không có số chỉ tiêu ngành |
| 6 | S1 | `qnu:r010` | `5438:5470` | Ngữ cảnh danh mục, không có số chỉ tiêu ngành |
| 7 | S1 | `qnu:r011` | `5471:5504` | Ngữ cảnh danh mục, không có số chỉ tiêu ngành |
| 8 | S1 | `qnu:r012` | `5505:5540` | Ngữ cảnh danh mục, không có số chỉ tiêu ngành |
| 9 | S1 | `qnu:r013` | `5541:5575` | Ngữ cảnh danh mục, không có số chỉ tiêu ngành |
| 10 | S1 | `qnu:r014` | `5576:5610` | Ngữ cảnh danh mục, không có số chỉ tiêu ngành |
| 11 | S1 | `qnu:r015` | `5611:5644` | Ngữ cảnh danh mục, không có số chỉ tiêu ngành |
| 12 | S1 | `qnu:r016` | `5645:5681` | Ngữ cảnh danh mục, không có số chỉ tiêu ngành |
| 13 | S1 | `qnu:r017` | `5682:5726` | Ngữ cảnh danh mục, không có số chỉ tiêu ngành |
| 14 | S1 | `qnu:r018` | `5727:5770` | Ngữ cảnh danh mục, không có số chỉ tiêu ngành |
| 15 | S1 | `qnu:r020` | `5803:5841` | Ngữ cảnh danh mục, không có số chỉ tiêu ngành |
| 16 | S1 | `qnu:r055` | `7133:7179` | Ngữ cảnh danh mục, không có số chỉ tiêu ngành |
| 17 | S1 | `qnu:r050` | `6921:6958` | Ngữ cảnh danh mục, không có số chỉ tiêu ngành |
| 18 | S1 | `qnu:r054` | `7091:7132` | Ngữ cảnh danh mục, không có số chỉ tiêu ngành |
| 19 | S1 | `qnu:r052` | `7011:7045` | Ngữ cảnh danh mục, không có số chỉ tiêu ngành |
| 20 | S1 | `qnu:r051` | `6959:7010` | Ngữ cảnh danh mục, không có số chỉ tiêu ngành |
| 21 | S1 | `qnu:r053` | `7046:7090` | Ngữ cảnh danh mục, không có số chỉ tiêu ngành |
| 22 | S2 | `qnu:p016` | `2383:2681` | Số nhập học/tỷ lệ; vai trò quota của mẫu số chưa được chứng minh |
| 23 | S2 | `qnu:p009` | `513:742` | Căn cứ văn bản: tách năm ban hành và năm phương hướng |
| 24 | S3 | `qnu:p035` | `15469:15906` | Metric đợt bổ sung riêng, không cộng vào tổng năm |

Bảng trên xác nhận vai trò trong **chủ đề chỉ tiêu đang thử**, không tuyên bố các đoạn ấy vô ích đối với mọi câu hỏi. Đổi chủ đề phải phân loại lại; cache gắn topic/source/config hash. Không áp dụng semantic proposal hoặc xuất bản nguồn từ báo cáo này.

Kết quả lượt thực chạy cuối, các lỗi còn lại và giới hạn nghiệm thu: [VALIDATION_REPORT.md](./VALIDATION_REPORT.md).
