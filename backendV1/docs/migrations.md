# Migration backendV1

Baseline `0001_initial_schema` thay thế15revision phát triển0001–0015 ngày
2026-10-27 theo yêu cầu người dùng, gồm vòng đời tài liệu/chatbot. DDL baseline
vẫn giữ nguyên. Chuỗi hiện hành thêm `0002_operational_readiness`: một cột JSONB
review acknowledgement và bảng `ops_storage_cleanup_actions`.
`0003_rag_policy_metadata` thêm JSONB rag_policy ở chat_assistants,
retrieval_metadata ở kb_compiled_versions và metadata_filter ở chat_turns.
`0004_application_api_keys` thêm ứng dụng, API key inbound và nhật ký request.
`0005_provider_connections` thêm nhà cung cấp cha/model con và phạm vi credential,
chuyển các model cũ theo endpoint nhưng giữ ID và ciphertext của khóa. Xem
[quy trình chuyển dữ liệu](../../docs/quy_trinh/42_modelops_nha_cung_cap_va_model.md).
Không đổi các revision cũ; thay đổi schema tiếp theo dùng revision mới.

## Tạo DB mới

Sau khi chọn `DATABASE_URL` và kiểm tra quyền sở hữu, từ `backendV1` chạy:

```powershell
uv run alembic upgrade head
uv run alembic current
```

Revision mong đợi: `0005_provider_connections`. DB cũ chạy các revision còn thiếu;
DB mới chạy baseline và bốn revision bổ sung. Chạy lại upgrade là no-op ở head.
Migration tạo bảng version riêng `alembic_version_backendv1`, giữ nguyên version
và bảng của `backend/`. Nếu trùng bất kỳ tên bảng v1 ngoài lịch sử hiện hành,
baseline dừng trước DDL; không tự nhận bảng đó hoặc sửa dữ liệu.

DDL được đóng băng trong file migration, lấy từ DB PostgreSQL thử đã chạy đủ
chuỗi cũ. Migration không import model ứng dụng hay dùng `Base.metadata.create_all()`;
thay đổi ORM sau này không làm baseline thay đổi theo. Có thể xuất SQL bằng
`uv run alembic upgrade head --sql` để xem trước.

## Các revision phát triển cũ

Nguồn15file được lưu nguyên bytes trong
[`alembic/archive/0001-0015_20261027.zip`](../alembic/archive/0001-0015_20261027.zip).
ZIP không nằm trong thư mục `versions`, không được Alembic nạp. Đây là bản sao
nguồn migration, không chứa dữ liệu DB hoặc credential.

Tên0005,0009,0015 trong báo cáo/nhật ký cũ là lịch sử, không phải revision có thể
chạy riêng trong chuỗi mới. Mọi chức năng đến0015 đã nằm trong baseline mới.

DB có `alembic_version_backendv1` trỏ một revision cũ sẽ bị Alembic từ chối do
revision đó không nằm trong chuỗi hiện hành. Không dùng `stamp head`, xóa bảng
version hoặc dựng lại DB để bỏ qua. Cần giữ backup, kiểm schema/data thực tế và
lập chuyển tiếp riêng nếu gặp môi trường như vậy. Lần gộp này chỉ thay mã và chạy
DB thử riêng; không chuyển revision hay áp DDL lên DB đang phục vụ.

## Kiểm chứng và lưu bằng chứng

- So sánh DB từ chuỗi cũ với DB từ baseline: column/type/default/nullability,
  PK, FK, unique/check constraint và index, gồm điều kiện index một phần.
- So sánh migration với ORM; giữ legacy sentinel và version table.
- Kiểm tra trùng bảng dừng an toàn, upgrade lặp không đổi và downgrade không
  giả thành công. Baseline từ chối downgrade để giữ dữ liệu bằng chứng.
- Kiểm thử tích hợp dùng DB `qnu_v1_test_*`, không dùng DB phục vụ.

Các tài liệu chức năng trỏ baseline này; lịch sử kiểm chứng cũ được giữ nguyên.
