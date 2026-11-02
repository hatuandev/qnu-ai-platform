# Phiên 811 — Kiểm thử live thay tài liệu sau khi chốt FE

## Phạm vi đã thực hiện

Tiếp tục thứ tự người dùng đã chấp thuận: review FE, kiểm tra, push Gitea v1.0.3, rồi thử thay bản PDF/DOCX trong kho test riêng. Không thay lịch sử GitHub, không gộp thay đổi đồng thời vào nhánh chính, không dọn nguồn/OCR hoặc dữ liệu test cũ.

Mã FE đã push và xác minh trên Gitea: `f0a7ca3945c089d369de5196d5d0e672ba1f0faa`. Kiểm chứng tại phiên 810: 686 test / 77 suites PASS, build có TypeScript PASS, Biome 19 tệp PASS, kiểm tra khoảng trắng PASS. Có cảnh báo kích thước bundle; không gọi đó là lỗi build. Đây không phải kết quả full backend: baseline 806 vẫn có một lỗi cũ 716.

## Cách chạy live

- Khởi động lại đúng năm container hạ tầng của phiên E2E `93faa11f0caf` bằng compose hiện có; không cleanup/init, xóa volume hay migrate schema.
- Dùng mã của worktree v1.0.3 qua ASGI HTTP handlers và worker functions thật, DB/MinIO/Redis/Qdrant của phiên, provider và khóa đã lưu trong ModelOps. Không override dependency, mock model hay khởi động worker quét lại các job cũ.
- Tạo collection riêng `col_92502d96d51f`. Dùng PDF fixture hai trang hiện có; DOCX mới chỉ chuẩn bị ở thư mục tạm để thử cơ chế thay bản. Đây là fixture kỹ thuật, không phải thông báo tuyển sinh chính thức.
- Runner và receipt ở `tmp/replacement811/`. Có chặn gửi lại inference đã dispatch; không dùng retry hoặc chỉnh đáp án/assertion để xanh.
- Luồng dự kiến: bóc tách bản cũ, compiler, duyệt có xác nhận bỏ AI review, publish/index; thêm DOCX staged; thử hủy candidate index để giữ bản cũ; tạo hành động thay bản riêng, index thành công mới chuyển phục vụ; hỏi trước/sau và kiểm tra hash/lịch sử. Chưa đến các bước này không được coi là đã đạt.

## Kết quả thực tế

| Chặng | Kết quả |
| --- | --- |
| Upload PDF | PASS: một source/revision trong kho riêng |
| Bóc tách native PDF | PASS: 2/2 trang, 0,77 giây, dữ liệu mẫu được giữ |
| Compiler với Qwen thật | FAIL nghiệm thu: `uncertain`, `chat_provider_uncertain`, 300,56 giây |
| Thêm bản DOCX staged, duyệt, xuất bản, lập chỉ mục | NOT RUN do compiler chưa hoàn tất |
| Hủy candidate, chuyển bản đang phục vụ, hỏi đáp trước/sau | NOT RUN |

Run OCR: `ocr_032b38cbc86d`; compiler: `cmp_5701d4554c0e`. Cả hai attempt_count=1; chỉ một lần gọi compiler. Usage `usage_b9461ebe60af40cc` là `unknown`, total_tokens=null, không quy thành 0.

Snapshot cấu hình thực tế của chính run: model `qwen3.8-27b-q4`, output 8192; `enable_thinking=false` đã gửi theo policy. Provider snapshot vẫn có timeout_seconds=300. Adapter phân loại timeout/network thành uncertain; thời gian đo khớp mốc 300 giây. Chưa có response hoàn tất để kết luận model sinh bao nhiêu token hoặc server GPU đang làm gì. Đây không phải mã vượt input/output token, không phải lỗi tương tác FE. Không đổi giới hạn trong lúc gọi, không gửi lại run uncertain và không đổi provider để che kết quả.

## Bảo toàn và giới hạn

Read-only audit sau lỗi PASS: hash bytes PDF gốc khớp revision; source vẫn một revision; chưa đăng ký compiled document hoặc publication trong kho mới; provider grants giữ nguyên. API container dùng trong runner đã đóng, không có cổng API/Vite riêng được bind và không restart serve chính. Năm dịch vụ hạ tầng E2E được giữ chạy; lịch sử lỗi giữ nguyên.

Không thay mã ứng dụng ở phiên 811. Chưa nghiệm thu luồng thay tài liệu với model thật. Việc tiếp theo là xử lý chênh lệch timeout của cấu hình provider đang dùng và xác minh sức khỏe/độ trễ upstream, rồi quyết định lượt kiểm thử mới minh bạch; không tự động chạy lại lượt uncertain.
