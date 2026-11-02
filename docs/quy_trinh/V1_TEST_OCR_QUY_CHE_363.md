# Kiểm tra PDF scan Quy chế tuyển sinh 363

Chặng này kiểm riêng OCR, không thay bộ 53 câu, collection đã xuất bản hoặc index hiện tại.

Nguồn: `docs/tai_lieu/tuyen_sinh/Quy chế tuyển sinh đại học 2026 - 363.pdf`, 32 trang,
SHA256 `59444d277a5e904808537ce70544c1fc83c0bf0a2f2653b78af362af59d5cccc`.
PDF không có lớp chữ. Nhãn trong `frontendV1/e2e/data/admissions-scan-ocr.json`
là mẫu được đối chiếu ảnh ở 7 trang, không phải bản chép đủ để tính CER/WER.

## Chạy

Giữ phiên E2E live đang có. Cần `provider-setup`, `model-discovery`, `model-ocr`,
`navigation` đạt và `serve` đã nạp mã backend hiện tại. Không cần cleanup/init hoặc
chạy lại compiler/review của các tài liệu cũ.

```powershell
.\test-v1-e2e.ps1 run admissions-scan-ocr --headed
```

Chặng upload vào collection thử riêng, lưu raw OCR, canonical JSON, Markdown,
manifest và báo cáo. Lượt đã có được đọc lại, không tự gọi lại model khi chất lượng
không đạt. Mỗi report nằm trong thư mục `runs` riêng của phiên.

Thí nghiệm thay mật độ ảnh phải được chọn rõ ràng, ví dụ:

```powershell
.\test-v1-e2e.ps1 run admissions-scan-ocr --headed --ocr-dpi 176
```

176 DPI phù hợp kích thước PDF này trong biên ảnh 1664 × 2048 đang khai báo; không
phải mặc định cho mọi PDF/model. API vẫn kiểm ngân sách và giới hạn ảnh. Lượt DPI
khác tạo thế hệ có cấu hình ghim riêng; checkpoint giữ lượt đầu và `experiments`.
Không gỡ cờ `dispatched` khi chưa rõ kết quả để gửi lại.

## Đọc kết quả

- `technical_pass`: đủ trang, đúng hash, có nội dung, bbox hợp lệ và evidence mapping.
- `sample_quality_pass`: chữ trên các mẫu đúng dấu, số, ký hiệu; bảng có cấu trúc và ô rỗng.
- HTTP hoàn tất không chứng minh OCR chính xác. Chặng vẫn FAIL khi mẫu chữ hoặc bảng sai.
- `column_spec_reconciled` là cảnh báo cần đối chiếu: các hàng cùng số ô nhưng khai báo
  số cột mâu thuẫn. Parser v2 giữ ô và raw, không tự sửa chính tả hay đoán bảng lệch hàng.

Nemotron được gọi bằng alias trong ModelOps. Tên model gốc/revision cần căn cứ vận
hành; alias riêng không chứng minh checkpoint nào đang chạy. Tham khảo
[model card NVIDIA](https://huggingface.co/nvidia/Nemotron-3.5-Parse) để đối chiếu
prompt và giới hạn hình ảnh.

## Chính tả và các bước sau

### Người dùng xem và xác nhận trước khi chuyển bước

1. Mở văn bản OCR, đối chiếu ảnh và sửa trực tiếp vào nháp; kiểm tra chính tả AI
   là bước hỗ trợ, không tự lưu thay đổi. Xem trước các sửa đổi rồi xác nhận lưu.
2. Sau khi lưu, màn hình chuyển sang đúng phiên bản server vừa trả về. Bấm
   **Dùng để biên soạn** sẽ ghim phiên bản này; nếu còn nháp chưa lưu thì phải lưu
   hoặc hủy nháp trước. Việc chọn lịch sử để xem lại vẫn được giữ riêng.
3. Compiler hoàn tất: xem bản biên soạn, dẫn chứng và báo cáo AI nếu có. Trong tab
   **Rà soát & Đánh giá**, nút **Xem và chỉnh sửa bản biên soạn** đưa người có quyền
   vào trình sửa. Có thể sửa chính tả, tiêu đề, mục và đoạn văn; giữ nguồn trích dẫn.
4. Bấm **Xem trước thay đổi**, đối chiếu nội dung rồi **Xác nhận tạo bản mới**.
   Bản sửa là lượt dẫn xuất mới có liên kết bản trước; không ghi đè bản cũ và không
   tự xuất bản. Đăng ký đúng bản mới đã kiểm tra, sau đó Duyệt & Phát hành theo quyền.

Người chỉ có quyền xem không được chuyển sang sửa. Bỏ qua AI review theo chế độ
đã được cho phép vẫn giữ quyết định xác nhận của người dùng; không đồng nghĩa
AI tự phê duyệt nội dung. Không cần sửa nếu bản biên soạn đã đúng.

Ứng dụng đã có luồng `text-review/checks` → gợi ý → lưu `text-review`. Lượt kiểm tra
chính tả tự nó không ghi văn bản. Phiên test797 được người dùng cho phép áp dụng
các gợi ý hợp lệ tự động, chỉ với nguồn thử này; không đổi quy trình hoặc mặc định UI.

Lưu thay đổi qua API hiện có với version/hash trước sửa và idempotency key. Giữ số,
mã, năm, đơn vị; không tự điền ô trống hoặc sửa cấu trúc bảng bằng chính tả. Giữ raw
và canonical gốc; bản sửa là JSON/Markdown dẫn xuất có version riêng. Compiler nhận
`text_versions[ocr_run_id]` của bản đã lưu. Kết quả OCR gốc và bản sau sửa phải báo
riêng, không thay nhãn tham chiếu để đạt PASS.

Kiểm tra chính tả dùng JSON Schema và giới hạn evidence ID trong các đoạn đã chọn
(`qnu.ocr.spelling/v4`; lượt cũ v3 giữ nguyên lịch sử). Máy chủ kiểm vị trí bằng chuỗi gốc khớp chính xác; chỉ căn
lại vị trí khi chuỗi xuất hiện duy nhất, hoặc mọi lần xuất hiện đều được đề xuất một
lần với cùng bản sửa. Chuỗi mơ hồ, khác số, chồng lấn hoặc không thuộc đoạn nguồn
vẫn bị chặn. Không có fuzzy match hoặc từ điển sửa theo câu test.

V4 gửi nguyên văn các đoạn/ô được chọn, kèm tiêu đề gần nhất, đoạn lân cận và
header/hàng thuộc đúng bảng của cùng bản nguồn. Ngữ cảnh chỉ đọc được giới hạn
8.000 ký tự tổng, 1.500 ký tự/mục; nếu bị rút gọn có cờ rõ ràng, không cắt văn bản
được sửa. Đoạn ở ranh giới trang chỉ là ngữ cảnh ứng viên, không mặc định nối câu
hoặc ô bảng. Toàn bộ request vẫn qua kiểm ngân sách ModelOps.

Mỗi gợi ý mới phải có `context_before` trích nguyên văn từ đoạn được sửa và
`context_after` chỉ chứa đúng thay thế đó. Trích dẫn không khớp, đổi thêm dữ kiện,
khác số, sai phạm vi hoặc chồng lấn làm lượt kiểm tra thất bại; không tự gửi lại.
Gợi ý thay đổi chữ cơ sở, dấu câu hoặc ranh giới từ được giữ trong
`withheld_suggestions` để đối chiếu ảnh; không xuất hiện trong danh sách áp dụng.
Các thay đổi dấu/viết hoa còn lại vẫn chỉ là đề xuất, không phải xác nhận đúng nghĩa.
Đây là kiểm tra bảo thủ theo Unicode, không phải từ điển tự thay thế.

Model chat hiện chỉ nhận văn bản; chưa có inference đối chiếu ảnh tự động. Người
dùng xem ảnh bằng luồng đọc nguồn hiện có, sửa nháp và Lưu để tạo phiên bản mới.
Không tự thay nhà cung cấp hoặc giả cờ `source_image_verified`. V4 không làm tăng
số lượt gọi model cho một lần kiểm tra; chưa có benchmark model thật chứng minh
tỷ lệ cải thiện. Muốn dùng mã mới cần khởi động lại serve sau khi các tác vụ đang
chạy hoàn tất; không đổi phiên bản đầu vào của compiler đã được tạo.

ModelOps hỗ trợ cấu hình reasoning riêng cho tác vụ `ocr_review`; thêm khả năng này
không tự tắt reasoning cho provider. Lượt test797 tạm dùng chính sách đã khai báo
để tắt suy luận, giữ nguyên nhà cung cấp/model và các tác vụ khác.

## Kiểm tra bản OCR gốc khi đã có bản sửa

`POST /text-review/checks` nhận tùy chọn `source_version` (0 là OCR gốc). Khi
không truyền/null, máy chủ vẫn kiểm tra bản mới nhất với optimistic lock như cũ.
Khi chọn lịch sử, `expected_version` và `expected_sha256` phải khớp chính bản đó;
không được lấy hash của bản khác, tự chuyển latest hoặc tự lưu kết quả. Lượt kiểm
tra lưu đúng version/hash đã chọn, UI chỉ áp dụng vào bản nháp khớp version/hash.
Idempotency của request cũ không có `source_version` được giữ nguyên.

Lượt model thật802 dùng API thử riêng, không restart serve chính: nguồn gốc v0,
7 trang/114 đoạn-ô,8 request/8 upstream attempt,17.571 tokens,60,95 giây cộng request.
4 request hoàn tất và4 failed `ocr_spelling_invalid`; probe `cơ bán` bỏ sót.
**Chất lượng chưa đạt**, không có lỗi token limit hoặc quota trong cohort này.
Một gợi ý `he → hệ` đúng ảnh nhưng dòng đó còn lỗi khác bị bỏ sót. Không tự áp dụng
hoặc lấy riêng gợi ý hợp lệ từ các batch failed. Bản29 và compiler cũ giữ nguyên;
policy reasoning đã restore. Đây không phải nghiệm thu toàn32trang hoặc CER/WER.
