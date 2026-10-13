# Sao lưu và khôi phục thử — Đợt 1

> Phạm vi đã mở rộng ở [runbook đợt 2](05_sao_luu_dot_2.md): nhập file, S3/MinIO, lịch qua bí mật ngoài và soft removal. Khôi phục thử phiên bản mới cần relay image pinned cho mạng internal; các mục “chưa có” dưới đây mô tả baseline đợt 1.

## Phạm vi

Sao lưu toàn bộ **bản cài đặt**, gồm mọi tenant: PostgreSQL (schema/data/sequence), file current-version trong bucket S3/MinIO, các thư mục local nghiệp vụ, cấu hình runtime, namespace vector Qdrant của app và khóa giải mã ModelOps. Không phải export một tenant/kho tri thức.

Giữ bản gốc, snapshots nguồn độc lập, Markdown/cấu trúc đã sửa và duyệt, facts, phiên bản DAG/trợ lý, hội thoại và các con trỏ xuất bản qua bản dump PostgreSQL và kho file. Vector phục hồi từ snapshot, không gọi embedding/OCR lại.

Không bao gồm lịch sử S3 version bị thay thế/delete marker, Redis cache/lease/circuit breaker, Docker image/mã nguồn đầy đủ, dịch vụ QNU SSO, 9router hoặc trọng số/cấu hình server AI bên ngoài. Giữ riêng release ứng dụng/migration tương ứng; không bootstrap/seed dữ liệu lên bản khôi phục. Backup không tự sửa lỗi hay xóa trạng thái lỗi nghiệp vụ trong DB.

## Điều kiện trước lần dùng đầu

1. Khởi động lại **tất cả** backend replica và worker với mã mới, không để tiến trình cũ tiếp tục ghi dữ liệu. Không chạy migration, seed, script ghi DB hay sửa trực tiếp MinIO/Qdrant trong lúc backup. Khóa chỉ bảo vệ API/worker đã tích hợp.
2. Đăng nhập thật với vai trò `AI.Admin`. Anonymous dev-admin không được xem/tạo/tải backup. Hệ thống đa tenant cần coi đây là quyền quản trị bản cài đặt, không cấp cho quản trị riêng một tenant.
3. PostgreSQL đang truy cập được; `pg_dump` phải cùng major version. Local Windows không có pg_dump dùng Docker `BACKUP_PG_CONTAINER=qnu_postgres`; chương trình kiểm tra container và DATABASE_URL cùng PostgreSQL system identifier trước khi dump. Cần quyền đọc `pg_control_system()` cho đường Docker, hoặc dùng pg_dump native.
4. Chỉ Qdrant single-node được hỗ trợ đợt này; cluster phân tán bị từ chối, không tạo bản thiếu shard. Namespace active thiếu hoặc file DB tham chiếu thiếu sẽ chặn backup.
5. Worker phải xử lý xong job queued/running/retryable; workflow running cần hoàn tất/đối soát. Không tự hủy job để backup. Chờ khóa API/worker tối đa `BACKUP_DRAIN_SECONDS`.
6. Thư mục backup có quyền truy cập hạn chế cho tài khoản chạy backend/runner. Trên Windows, quản trị cấu hình ACL của thư mục; trên Linux scratch được tạo riêng với quyền owner. Scratch chứa dữ liệu giải mã trong quá trình kiểm tra, không đặt trên thư mục chia sẻ công khai. Scratch được dọn bình thường; nếu máy/process mất điện có thể còn thư mục `.backup-scratch-*`, cần quản trị đối soát trước khi dọn, không xóa khi tiến trình còn chạy.

## Cấu hình

| Thiết lập | Mặc định / Ý nghĩa |
|---|---|
| `BACKUP_DIRECTORY` | `./storage/backups`, đường dẫn tính từ working directory backend; production `/app/storage/backups` trên volume `qnu_platform_storage` |
| `BACKUP_PG_CONTAINER` | `qnu_postgres` cho dev Windows; production Compose để rỗng và dùng pg_dump native |
| `BACKUP_LOCAL_PREFIXES` | JSON array `documents`, `uploads`, `snapshots`, `ocr_cache`, `artifacts`; bổ sung prefix nếu DB/file nghiệp vụ dùng chỗ khác |
| `BACKUP_TIMEOUT_SECONDS` | 3600 giây; khi hủy chờ thao tác blocking đang chạy kết thúc an toàn trước khi giải phóng khóa/dọn scratch, nên cleanup có thể vượt deadline |
| `BACKUP_DRAIN_SECONDS` | 120 giây chờ API/worker kết thúc |
| `BACKUP_MIN_FREE_BYTES` | 1 GiB tối thiểu dự phòng; cần thêm chỗ cho dump, bản copy S3/Qdrant, archive và giải nén kiểm tra |
| `BACKUP_DRILL_ENABLED` | `false`; bật `true` trên host có Docker để dùng nút khôi phục thử |
| `APP_IMAGE_TAG` | Release triển khai ghi trong manifest; phải giữ image/source và migration tương ứng riêng |

Nơi lưu không được là thư mục gốc, working directory hoặc nằm trong prefix dữ liệu sẽ capture. Cần cấu hình storage đúng nơi app thực sự ghi; không tự dò/copy toàn bộ máy hay cả `.env`. Production Dockerfile có pg_dump/pg_restore 16 và các thư viện cần thiết, nhưng image build chưa được kiểm chứng trong phiên này.

Không gắn Docker socket vào backend production để bật drill. Hãy tải `.qnubak` rồi dùng CLI trên máy vận hành có Docker. Drill dùng image PostgreSQL cùng major, image ID của `qnu_qdrant`/`qnu_minio` hiện có; PostgreSQL image cần sẵn local (`--pull=never`). Qdrant sandbox phải đúng version ghi trong manifest. Endpoint S3/Qdrant live có thể ở xa; drill hiện cần các container tham chiếu local để xác định image.

## Thao tác giao diện

Vào **Nâng cao → Sao lưu**, hoặc `/settings/backups`.

1. Bấm **Sao lưu**, nhập mật khẩu riêng 12–256 ký tự (không xuống dòng), nhập lại và gõ `XÁC NHẬN`.
2. App gửi thao tác và trả về ngay; runner riêng thực hiện, không qua Redis/ARQ. API nghiệp vụ trả 503 kèm Retry-After khi khóa bảo trì được giữ; lịch sử sao lưu/auth/health vẫn truy cập được. Tiến độ thể hiện các giai đoạn, không phải ETA hoặc phần trăm byte chính xác.
3. Chỉ khi toàn bộ dump/file/vector, mã hóa và kiểm tra checksum hoàn tất mới đổi `.qnubak.partial` thành `.qnubak` và báo **Đã kiểm tra toàn vẹn**.
4. Mở trang chi tiết `/settings/backups/<id>` để tải xuống, kiểm tra hoặc khôi phục thử. Lịch sử thao tác lưu ngoài PostgreSQL cùng catalogue, có actor/correlation ID; mật khẩu không được lưu.
5. Tải/chuyển file sang ổ ngoài/NAS/máy độc lập. Tải file dùng cookie HttpOnly phạm vi một backup, TTL 90 giây; không lộ token URL và không buffer toàn bộ archive thành Blob trong trình duyệt.

Mất mật khẩu không có chức năng lấy lại. Master key ModelOps/khóa cũ nằm trong `secrets.json` **bên trong archive đã mã hóa bằng mật khẩu backup**, không xuất vào catalogue/log. Nên lưu mật khẩu ở nơi riêng; không gửi trong chat/email hay commit vào repository.

## Khởi chạy trên Windows và Ubuntu

Launcher dùng tiến trình độc lập qua luồng riêng, không phụ thuộc hỗ trợ subprocess của event loop API. Windows chạy ẩn, tương thích Uvicorn `--reload`/SelectorEventLoop; Ubuntu dùng phiên tiến trình riêng. Không cần bỏ reload hoặc sửa event-loop policy toàn app. Mật khẩu có dấu được truyền/đọc nhất quán UTF-8 qua stdin; không đặt vào dòng lệnh hay biến môi trường.

Sau cập nhật launcher, khởi động lại backend rồi F5 trang và tạo thao tác mới. Lịch sử failed cũ vẫn giữ nguyên; không reset DB/xóa Redis hoặc tự retry bằng mật khẩu đã lưu. Nếu spawn thất bại, thông báo kèm loại lỗi an toàn (ví dụ `FileNotFoundError`), không nội dung exception thô. HTTP 202 chỉ xác nhận nhận việc; hãy chờ trạng thái hoàn tất/kiểm tra toàn vẹn.

Đã kiểm chứng Windows và Ubuntu 24.04 container bằng dữ liệu mẫu. Không thay thế điều kiện pg_dump đúng major, quyền thư mục, storage và Docker khi dùng drill; chưa xác nhận image production hoặc corpus thật trên Ubuntu.

## Khôi phục thử và kiểm tra offline

Không có API ghi đè DB/bucket/Qdrant đang dùng. Drill chỉ tạo container ID/name ngẫu nhiên, có nhãn ownership, cổng bind `127.0.0.1`, không mount volume live; dọn đúng ID/label bằng `docker rm --volumes` sau cùng. Worker/chatbot sandbox không được khởi động nên không tự replay job hay phát sinh gọi AI.

Drill phục hồi PostgreSQL và đối soát schema/số hàng/tham chiếu file; thử giải mã các khóa provider và key pool mà không in plaintext; upload snapshots Qdrant, đối soát exact point counts, phục hồi aliases; MinIO phục hồi theo object key gốc và đối soát SHA-256. Local files được giải nén vào scratch và kiểm tra từng checksum. Kết quả không thay cho kiểm thử chatbot/RAG trên môi trường khôi phục hoàn chỉnh.

Nếu backend hoặc DB đã mất kết nối, có thể kiểm tra file trên host vận hành mà không cần Redis/DB live:

```powershell
# Chạy từ thư mục backend; CLI hỏi mật khẩu bằng getpass, không nhận mật khẩu qua argv.
uv run python -m app.modules.backups.cli verify "D:\Backups\bkp_<id>.qnubak"

# Chỉ host có Docker/images phù hợp; thiết lập có hiệu lực trong PowerShell hiện tại.
$env:BACKUP_DRILL_ENABLED = 'true'
uv run python -m app.modules.backups.cli drill "D:\Backups\bkp_<id>.qnubak"
```

Không cần catalogue còn nguyên để CLI kiểm tra/drill; manifest nằm trong archive. UI chỉ liệt kê 100 bản mới nhất đợt này. Chưa có lịch tự động, retention, remote transfer, restore-to-live hay file import trên UI.

## Khi cần khôi phục thật

Thực hiện runbook có người vận hành: giữ bản dữ liệu hiện tại, khôi phục thử trước, dựng release/schema phù hợp ở DB/bucket/Qdrant mới, cấu hình khóa từ escrow an toàn, kiểm tra tài liệu/trạng thái duyệt/published pointer và RAG, rồi mới chuyển endpoint. Tạo Redis namespace sạch và đối soát job/checkpoint/provider leases trước khi bật worker. Không chép nguyên Redis cũ, không seed/re-OCR/nạp lại vector theo model khác. Thao tác này **chưa được tự động hóa trong đợt 1**.

## Kiểm chứng

- Unit/security: mã hóa streaming nhiều block, mật khẩu sai, sửa/cắt/trailing ciphertext, traversal/link, giới hạn giải nén, catalogue, auth và ticket download.
- Launcher/HTTP 202/real runner: Windows default và Selector reload, Ubuntu 24.04, mật khẩu tiếng Việt, executable thiếu; Windows 30 passed, Ubuntu 27 passed/3 ca riêng Windows skipped. Harness tại `backend/tests/docker/backup_launcher.Dockerfile`, không mount volume thật và chạy với `--network none`.
- Integration opt-in `QNU_TEST_BACKUP_DOCKER=1`: container PG16/MinIO/Qdrant thật, independent subprocess tạo+verify+drill, giữ Unicode/review state/key pool/vector; khóa giữ xuyên SSE, worker lỗi giải phóng khóa; job pending/thiếu file từ chối. Chỉ dữ liệu mẫu, không backup/restore dữ liệu thật trong phiên phát triển.
- Các container mẫu được dọn có kiểm tra nhãn ownership; file fixture encrypted/catalogue vẫn giữ trong thư mục test để đối soát.
- Chưa chạy backup corpus thật, chưa build Docker production, chưa UI E2E authenticated (trình duyệt chuyển về sign-in), chưa cam kết RPO/RTO.

Tham khảo: [PostgreSQL pg_dump 16](https://www.postgresql.org/docs/16/app-pgdump.html), [Qdrant snapshots](https://qdrant.tech/documentation/tutorials-operations/create-snapshot/). Volume/đồng bộ mirror không thay thế backup được kiểm chứng và lưu ngoài máy.
