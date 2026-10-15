# Kiểm chứng migration trên database tạo sẵn

## Mục tiêu và thông tin được làm rõ

Người dùng muốn biết cấu trúc đã thay đổi nhiều có còn migrate được trên hạ tầng hiện có không; tạm gác reset, không thay luồng bootstrap. Người dùng ban đầu chọn câu trả lời “chung cả database”, sau đó gửi ảnh danh sách database cho thấy có `qnu_ai_platform` bên cạnh các DB SSO/Gitea/ứng dụng khác. Nhận định được điều chỉnh: ảnh xác nhận database QNU tồn tại trên PostgreSQL dùng chung; chưa xác nhận nội dung bảng hoặc `DATABASE_URL` thực tế của container. Nếu app trỏ đúng DB QNU, migration không chạy sang các database bên cạnh.

## Phép thử cô lập

Thêm harness `backend/scripts/audit_migrations_458.py`, chỉ tạo container PostgreSQL16.15 trên internal network tên ngẫu nhiên, storage tmpfs, không mount dữ liệu thật/không publish port. App image là bản 456 đã build, ID `sha256:0e2d3177d8d794d6807438d85aa3b856b4b268639f380c61ab7094ed8ded4feb`; migration và models nằm trong image không bị sửa. Credential toàn bộ là fixture. Script không đọc backend env và không nhận đích DB bên ngoài, tự cleanup theo exact name+label `qnu.audit=458`.

Trong môi trường thử, tạo database và bảng sentinel mô phỏng dữ liệu không thuộc QNU; không chạy bootstrap seed hay gọi model/AI. Nạp metadata cùng tập module như Alembic env để đối chiếu thiếu bảng/cột sau upgrade. Không kiểm tra toàn bộ datatype/default/index/constraint bằng phép so sánh này.

## Kết quả cuối

Chuỗi Alembic có **26 revisions**, một head `20261012_sync_struct_review`.

| Trường hợp | Kết quả |
| --- | --- |
| Database tạo sẵn, chưa có schema QNU | Upgrade head exit0; missing tables/columns rỗng; chạy lại head exit0 |
| Schema dựng từ migration mốc `20260926_reconcile_core_schema`, có provider tổng hợp | Nâng từ mốc cũ lên head exit0; missing tables/columns rỗng; provider sentinel giữ nguyên; chạy lại head exit0 |
| Alembic version của ứng dụng khác trong cùng DB | Exit255, `Can't locate revision identified by other_application_revision_458`, không tự stamp/reset |
| Có bảng `assistants` của ứng dụng khác, cấu trúc không tương thích | Exit1 tại guard reconcile: thiếu required columns, không tự xóa bảng để vượt lỗi |

Cả bốn trường hợp giữ nguyên sentinel dữ liệu ngoài QNU; trường hợp collision giữ nguyên row trong bảng trùng tên. Hai trường hợp thành công có 48 bảng public gồm bảng thử/sổ Alembic, không gọi chúng là 48 bảng ứng dụng. Kết quả lưu tại `backend/storage/migration_audit458.json`.

Hai lần harness ban đầu dừng do fixture insert provider không khớp schema cũ (`base_url` sai tên và thiếu priority/timeout); đã sửa fixture, không sửa runtime/migration. Chúng không phải bằng chứng migration thất bại. Kết quả bảng trên là lần chạy hoàn tất bốn trường hợp. Warning Qdrant compatibility khi import phát sinh vì không có Qdrant trong mạng test, không phải gọi model hoặc lỗi migration.

## Kết luận và giới hạn

Có bằng chứng thực tế rằng migration hiện tại chạy trên DB đã tạo sẵn và nâng được schema ở mốc 26/09, không cần reset chỉ vì code thay đổi. Không thể bảo đảm mọi DB cũ có dữ liệu/schema lệch đều nâng thành công; chưa có revision/schema dump của server thực tế. Kiểm tra `SELECT version_num FROM public.alembic_version` trong đúng DB QNU là bước read-only tiếp theo, sau đó xác định pending revisions và thử trên bản sao khi cần.

`check_db_schema` của app kiểm tra head và một tập bảng chính, không kiểm chứng hết cột hoặc chuyển đổi nghiệp vụ. Migration thành công không thay cho kiểm tra published snapshot/vector/object storage khi demo. DB cũ có thể chịu các migration dọn dữ liệu cụ thể đã nêu ở phiên455; sentinel tổng hợp không chứng minh mọi dữ liệu thật được bảo toàn.

## Thay đổi và kiểm chứng

Chỉ thêm harness chẩn đoán và cập nhật nhật ký/snapshot/PROJECT_CONTEXT/hai mục lục; không sửa migration, CLI, Compose, models, auth hoặc RAG. Ruff trên harness đạt. Phép thử PostgreSQL thật trong Docker hoàn tất, container và network nhãn458 đã dọn, không còn tài nguyên test chạy. Không chạy full Pytest/Vite vì không sửa ứng dụng và mục tiêu là chẩn đoán migration riêng. Không đọc secret thật, truy cập DB server, reset/seed/publish/restore/deploy hoặc commit/push.

Bài học: phân biệt dùng chung PostgreSQL server với dùng chung database; xác minh migration bằng DB thật tách biệt trước khi kết luận từ khả năng build hoặc test API.
