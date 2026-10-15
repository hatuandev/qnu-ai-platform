# Workflow và memory

Đầu task đọc `docs/memory/PROJECT_CONTEXT.md` và diff liên quan. Đối chiếu mọi trạng thái cũ với mã/config/test thật; không coi memory là bằng chứng nghiệm thu hiện tại.

Cuối task có thay đổi, đồng bộ:

1. Nhật ký mới `docs/nhat_ky/YYYY-MM-DD_phien_NNN_noi_dung.md`: yêu cầu/giả định, file sửa, phương pháp, lệnh thật, PASS/FAIL/NOT RUN, rủi ro và bước sau.
2. Thêm liên kết ở `docs/nhat_ky/README.md` và dòng đầu danh sách `docs/WORK_LOG.md`.
3. Thêm mốc mới ở mục phiên gần nhất của `docs/memory/PROJECT_CONTEXT.md`, giữ các mốc và trạng thái vận hành đang tồn tại.
4. Thêm snapshot `docs/memory/snapshots/YYYY-MM-DD_session_NNN.md`. Chọn số chưa dùng sau khi đọc lại danh mục; không xóa hoặc ghi đè snapshot cũ.
5. Chỉ cập nhật `docs/quy_trinh/` nếu luồng nghiệp vụ/kỹ thuật thay đổi; nếu thêm luồng mới thì thêm tài liệu và mục lục tương ứng.

Các đường dẫn trên tính từ root repo. Khi chạy nhiều phiên, đọc lại và kiểm tra hash/diff trước ghi; cập nhật có phạm vi, không thay toàn PROJECT_CONTEXT bằng snapshot đã cũ. Nếu số phiên đã được dùng, chọn số kế tiếp trước khi tạo file.

Không lưu secret, credential, PII, prompt riêng, Base64 hoặc corpus nội bộ trong nhật ký/memory. Không sao chép bộ tài liệu ZIP hoặc dữ liệu benchmark vào Git nếu chưa được yêu cầu. Chỉ ghi kết quả đã thực chạy; test cũ phải gắn nhãn lịch sử.
