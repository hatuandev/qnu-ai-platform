# Phiên #357 — Tự seed khóa vLLM sau reset DB local

## Mục tiêu

Người dùng muốn reset DB rồi kiểm tra kết nối mà không phải nhập lại khóa vLLM. Không hardcode secret vào source hoặc seed catalog.

## Triển khai

- Thêm `backend/app/modules/modelops/services/local_seed_credentials.py`: seed local đọc ciphertext từ `backend/storage/modelops-bootstrap/credentials.json`, kiểm tra mã hóa/giải mã trước khi nạp vào primary và authoritative ProviderApiKey. Không log token.
- Seed mặc định và script seed AI server gọi helper chỉ khi tạo provider mới. Cấu hình/provider/khóa đã có không bị ghi đè. Production bỏ qua bootstrap; runtime tiếp tục đọc DB.
- `.gitignore` loại toàn bộ thư mục bootstrap. Đã lấy bản mã hóa của khóa người dùng đã lưu #356, không ghi plaintext. Tệp này không được track trong Git.
- `make reset-db`/`make.ps1 reset-db`/reset script hiện có đều gọi `run_db_seed(seed_all=True)`, nên đi qua helper mới. Reset này không xóa thư mục bootstrap.
- PaddleOCR vẫn không có khóa.

## Kiểm chứng

- 24 test trọng tâm đạt, gồm seed DB rỗng, khóa primary/pool, reseed không thêm trùng, plaintext bị từ chối và production bỏ qua bootstrap.
- Ruff toàn backend đạt; cảnh báo permission các thư mục runtime không thuộc thay đổi.
- FullBE: 853 passed, 13 failed nền như #355, 2 skipped; ca seed+reread bổ sung sau full suite đã chạy trong 24 focused.
- Kiểm tra bootstrap thật giải mã được và chỉ chứa ciphertext. Git check-ignore đạt; git ls-files xác nhận không track.
- Không thực hiện reset DB thật, không xóa dữ liệu, không restart hay sửa qnu-sso. Không có thay đổi FE nên không chạy build FE.

## Điều kiện vận hành

- Giữ tệp bootstrap cục bộ và giữ `PROVIDER_ENCRYPTION_KEY`/`SECRET_KEY` (hoặc khóa cũ phù hợp) để giải mã sau reset.
- Tệp không đi theo Git sang máy khác. Nếu xóa thư mục hoặc đổi khóa mã hóa không có fallback, cần cấu hình lại bootstrap/nhập khóa qua ModelOps.
- Chỉ seed lúc tạo preset mới; không tự thay khóa cũ sau khi người dùng đổi key trong ModelOps. Nếu đổi key server, cập nhật bootstrap hoặc bỏ bootstrap để không phục hồi khóa hết hiệu lực ở lần reset sau.
