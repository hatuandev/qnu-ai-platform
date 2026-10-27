# Sao lưu và phục hồi backendV1

Bộ công cụ `scripts/recovery_bundle.py` dành cho người vận hành có quyền quản trị
nền tảng, khác với ZIP bằng chứng của một workspace. Workspace vẫn là biên quyền
của v1. Công cụ xác thực access token bằng cùng cơ chế SSO/dev hiện có; model
không nhận credential hoặc quyền phục hồi.

## Phạm vi bản sao

- Toàn bộ 43 bảng thuộc backendV1, gồm membership, publication, review, ModelOps
  và credential đã mã hóa. Không đọc/ghi DDL hoặc dữ liệu của backend legacy.
- Tệp gốc, raw OCR/model, Markdown/JSON, review, manifest và evidence backup được
  tham chiếu; kiểm hash trước khi đóng gói. Tệp mồ côi không thuộc bản sao.
- Vector đã lưu trong DB và manifest đủ để dựng lại Qdrant mà không gọi embedding
  model thêm. Phục hồi sẽ dùng namespace mới cho **mọi** generation; chỉ dựng điểm
  cho generation đang active. Generation cũ cũng được remap để cleanup không thể
  chạm Qdrant nguồn. Manifest gốc giữ nguyên; manifest recovery là bản dẫn xuất.

Bundle là dữ liệu được mã hóa và xác thực bằng khóa recovery riêng, không chứa
SQL hay chương trình có thể chạy. Phục hồi dùng schema Alembic và insert có kiểu,
kiểm FK/constraint; không giải nén đường dẫn do archive cung cấp ra filesystem.

Master key ModelOps, khóa recovery, SSO/signing key và credential hạ tầng phải
được quản lý ở nơi lưu bí mật riêng. Master key ModelOps gốc được kiểm fingerprint
trước ghi để tránh phục hồi credential không giải mã được. Không lưu LLM API key
trong `.env`, log hoặc receipt. Không đặt khóa recovery cạnh bundle.

## Quy trình người vận hành

1. Chọn thời điểm dừng nhận ghi mới và chờ job đang chạy/queued kết thúc hoặc hủy
   bằng lifecycle. Công cụ từ chối snapshot khi còn job hoạt động. Không tự dừng
   API/worker. Snapshot metadata dùng MVCC repeatable-read và khóa workspace;
   tệp bất biến được đọc và kiểm checksum.
2. Cấp token quản trị qua `RECOVERY_ACCESS_TOKEN`, khóa recovery qua
   `RECOVERY_ENCRYPTION_KEY` từ secret store của môi trường. Khóa tối thiểu 32 ký tự.
3. Từ `backendV1`, tạo bundle ở thư mục riêng được bảo vệ:

   ```powershell
   uv run python scripts/recovery_bundle.py backup --bundle <duong-dan-rieng>/backup.qnu
   ```

4. Chọn **DB chưa tồn tại** có tên `qnu_v1_restore_<16 ký tự hex>`, cấu hình URL
   PostgreSQL async qua `RECOVERY_DATABASE_URL`. Chuẩn bị kho đích mới, trống.
   CLI hiện hỗ trợ đích local; service phục hồi dùng BlobStore nên có thể gọi với
   adapter S3 được cấu hình riêng. Qdrant có thể dùng hạ tầng chung nhưng chỉ tạo
   các namespace mới; không ghi đè/xóa collection nguồn.
5. Xem trước chính bundle và đích đó:

   ```powershell
   uv run python scripts/recovery_bundle.py preview --bundle <backup.qnu> --target-storage <thu-muc-moi> --target-qdrant <Qdrant-duoc-phep>
   ```

6. Đối chiếu DB/kho/hash bundle; dùng đúng `confirmation_sha256` trả về:

   ```powershell
   uv run python scripts/recovery_bundle.py restore --bundle <backup.qnu> --target-storage <thu-muc-moi> --target-qdrant <Qdrant-duoc-phep> --confirm-hash <hash-da-xem>
   ```

7. Kiểm receipt, tệp gốc, membership, giải mã credential, publication/citation và
   tìm kiếm trên bản phục hồi. Cấu hình xác thực/hạ tầng phù hợp ở môi trường mới.
   Chỉ chuyển lưu lượng và bật API/worker sau khi người vận hành chấp nhận kết quả.

Đích đã tồn tại, kho có dữ liệu, sai hash xác nhận, sai master key hoặc khác schema
đều bị từ chối. Không tự stamp revision. Nếu phục hồi lỗi sau khi tạo đích, giữ
DB/tệp để điều tra; không tự ghi đè để retry. Dùng đích mới hoặc dọn đúng tài nguyên
thử sau khi kiểm tra ownership. Công cụ không tự khởi động worker hay phục vụ dữ liệu.

Giới hạn bundle: 512 MiB, 10.000 object, 100.000 hàng mỗi bảng; quá giới hạn trả
lỗi, không xuất bản bản sao thiếu. Đây là recovery **backendV1**, chưa phải backup
toàn cluster PostgreSQL/legacy hay toàn bộ cấu hình máy chủ. Redis queue/cache
không được sao chép: snapshot yêu cầu hết job hoạt động và không tự resend uncertain.

## Bằng chứng hiện có

Đã restore DB/tệp/Qdrant thật trong môi trường riêng, giải mã credential và tìm
kiếm được; kiểm cả trường hợp dọn generation inactive sau restore vẫn giữ Qdrant
nguồn. Đã thử PDF được phép và server AI thật, phục hồi 18 tệp rồi tìm kiếm bằng
embedding thật. Đây là kiểm chức năng; chưa nghiệm thu chất lượng câu trả lời,
SSO QNU thật, chuyển lưu lượng production hoặc quy mô vượt giới hạn bundle.
