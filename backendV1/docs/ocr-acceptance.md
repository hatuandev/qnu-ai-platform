# Kiểm chứng và theo dõi luồng OCR

Áp dụng cho upload PDF/DOCX → revision gốc → job → render → Nemotron qua ModelOps
→ raw/canonical/Markdown/manifest → đọc qua API. Học cách đo từng thành phần và toàn
luồng từ Haystack; không thêm dependency Haystack, không đổi schema hoặc cấu hình
phục vụ. Compiler và evaluation RAG nằm ngoài đợt này.

## Dấu vết runtime

`ocr_run_requested` nối yêu cầu với revision đã lưu. `ocr_stage_started` và
`ocr_stage_finished` dùng schema `qnu.ocr.trace/v1` với danh sách trường tường minh:

- `run_id`, `workspace_id`, `collection_id`, `source_id`, `revision_id`,
  `source_sha256`, `generation`, `attempt`, `config_fingerprint`.
- `provider_id`, `model_name`, `provider_configuration_hash` khi đã phân giải.
- `stage`, `page_number`/`artifact_kind` nếu có, `duration_ms` đo bằng đồng hồ đơn
  điệu, trạng thái và mã lỗi. Count, số byte, hash và token chỉ ghi khi đã quan sát.

Các bước: `dispatch`, `authorize`, `resolve_model`, `load_revision`, `render`,
`provider_preflight`, `reserve_usage`, `ocr_page`, `parse_page`, `store_artifact`,
`assemble`, `read_artifact`. Bước chưa chạy không có duration giả. Một run retry có
cùng ID nhưng khác `attempt`; trang đã hoàn tất không bị gọi lại chỉ để có trace.

`completed` của từng bước nghĩa là bước đó thành công. Ví dụ raw có thể lưu thành
công, trong khi parse và assemble thất bại. Timeout provider ghi `uncertain`;
cancellation được ghi và truyền tiếp, không biến thành thành công.

Không ghi requester, endpoint, credential, prompt, ảnh/Base64, nội dung OCR hoặc
chi tiết exception vào các sự kiện này. Dùng hash/ID để mở bằng chứng qua API có
quyền. Các sự kiện được gửi tới logger có sẵn; chưa có timeline lưu trong DB hay
API truy vấn lịch sử trace. Thời hạn lưu log phụ thuộc hệ thống vận hành hiện hữu.

## Đọc raw nguyên bản

`GET /platform/v1alpha1/workspaces/{workspace_id}/collections/{collection_id}/sources/{source_id}/revisions/{revision_id}/processing-runs/{run_id}/pages/{page_number}/raw`

Đọc đúng bytes provider trả về, cả khi run thất bại do malformed/truncated/layout.
Không yêu cầu run completed; không phục vụ raw đó như canonical đã hoàn tất.
Kiểm quyền và toàn bộ chuỗi tài nguyên trước đọc, kiểm kích thước/checksum khi đọc.
Trả `application/octet-stream`, `ETag` theo SHA256, `private, no-store`, `nosniff`.
Chưa xác thực trả401; người ngoài workspace hoặc trang/phiên bản không tồn tại
trả404; checksum hỏng trả502. Client không truyền blob path để chọn tệp tùy ý.

## Nghiệm thu kỹ thuật

Từ thư mục `backendV1`, dùng môi trường test và PostgreSQL loopback đã được phép.
`TEST_REDIS_URL` phải trỏ Redis loopback được phép nếu muốn chạy kiểm tra transport
thật. Test dùng queue `qnu:v1:test:ocr:<nonce>`, chỉ dọn chính queue/key do nó tạo;
không flush Redis, không chạy cron của ứng dụng. OCR vẫn là HTTP provider giả lập.

```powershell
.venv/Scripts/python.exe scripts/run_isolated_tests.py
.venv/Scripts/python.exe scripts/ocr_acceptance_report.py --junit storage/context636/RUN_ID/result.xml --receipt storage/context636/RUN_ID/receipt.json --output storage/ocr-acceptance/report.json
```

Thay `RUN_ID` bằng tên database tạm mà harness in ra. Harness tạo/migrate đúng DB
test, chặn kết nối bên ngoài, giữ sentinel legacy và tự dọn DB. Không migrate DB
phục vụ để chạy nghiệm thu. Khi thiếu Redis test, ca transport SKIP và nhóm job
trong báo cáo là NOT RUN.

Reporter chỉ đọc JUnit và receipt, không gọi DB/provider. Nó xuất JSON + Markdown,
ghim SHA256 hai đầu vào, kiểm đủ ID bắt buộc theo sáu nhóm: upload/revision, job,
render, ModelOps, raw/dẫn xuất, API/trace. Thiếu/SKIP là NOT RUN; ID trùng, test lỗi
kể cả ngoài nhóm, hoặc receipt chưa xác nhận isolation/cleanup thì FAIL. Không chọn
lượt tốt nhất hoặc bỏ ca lỗi để tăng điểm. Đây là báo cáo kiểm thử đã ghi nhận,
không tự xác minh lại hạ tầng từ một tệp JUnit.

## Nemotron thật và chất lượng OCR

Reporter kỹ thuật luôn ghi hai phần này NOT RUN. Muốn đánh giá riêng cần runtime
được phép, provider/credential/quota/capacity hợp lệ qua ModelOps và mẫu có
ảnh nguồn/đáp án đã đối soát. So chữ, số, thứ tự trang/block, ô bảng, header,
footnote và phần thiếu. Lưu nguồn/phiên bản, cấu hình và kết quả từng mẫu; unknown
giữ unknown. Phản hồi OCR replay hoặc provider giả lập không chứng minh chất lượng
so với ảnh và không thay lần gọi Nemotron thật.

Snapshot `/evidence` vẫn ghim revision/generation/hash và validation để bàn giao
về sau. Run completed, trace thành công và báo cáo kỹ thuật PASS đều không phê
duyệt nội dung hoặc gọi Compiler tự động.
