# Sao lưu đợt 2 — Nhập file, S3/MinIO, lịch và bản cũ

## Trạng thái và ranh giới

Đợt 2 giữ định dạng `.qnubak` v1 và mật khẩu thủ công không lưu. Theo lựa chọn người dùng, lịch dùng **bí mật bên ngoài** qua file được kho bí mật/máy vận hành mount riêng; nơi lưu ngoài là **S3/MinIO**. Không tích hợp API Vault/KMS trong phiên này. Không có restore-to-live/ghi đè, không tự chạy lại chatbot hoặc job, không replay Redis.

Sau cập nhật, khởi động lại BE/worker và F5 giao diện. Tại `/settings/backups` có Nhập file, Ghim/Bỏ ghim, Xóa, Chuyển S3 và trang `/settings/backups/policy`. Mọi thao tác cần phiên đăng nhập thực và vai trò AI.Admin vì bản sao lưu gồm mọi tenant và key escrow.

Lịch, S3 và tự dọn mặc định **tắt**. Chưa tự cấp bí mật, cấu hình/bật lịch hoặc chuyển bản thật của người dùng đi. Cần bảo vệ thư mục backup bằng quyền filesystem như đợt 1.

## Nhập và khôi phục thử

1. Chọn file `.qnubak` bằng Nhập file. Upload raw theo luồng, giới hạn mặc định 20 GiB qua `BACKUP_IMPORT_MAX_BYTES`, kiểm tra dung lượng còn trống và header; không dùng tên/path do file gửi lên để ghi ổ đĩa. Proxy/reverse proxy phải cho phép kích thước và thời gian upload tương ứng.
2. Record mới có ID riêng, trạng thái **Chưa kiểm chứng**, tự ghim. Header và SHA-256 upload chưa chứng minh mật khẩu/toàn vẹn archive; không giải nén ngay.
3. Mở chi tiết, bấm Kiểm tra và tự nhập mật khẩu. Giải mã/manifest/path/hash gates giữ như đợt 1. Không gửi mật khẩu trong chat.
4. Bấm Khôi phục thử khi đã cấp môi trường vận hành phù hợp. Đối soát PostgreSQL/file/key pool/vector/S3 trong tài nguyên mới rồi dọn. Không đổi dữ liệu live hoặc bật chatbot sandbox.

Trước tạo container, kiểm tra manifest có schema/major/vector metadata; production yêu cầu `APP_IMAGE_TAG` khớp release ghi trong backup. Development chưa thay cho compatibility gate đầy đủ của release/migration; giữ riêng image/source đúng phiên bản và đối soát RAG trên môi trường phục hồi hoàn chỉnh. Qdrant version vẫn phải khớp.

### Chuẩn bị relay cho môi trường khôi phục thử

Các target PG/Qdrant/MinIO nằm trong network Docker `--internal`, không publish cổng và không mount volume live. Runner truy cập qua relay TCP riêng, unprivileged/read-only, chỉ có một IP/port target cố định, publish `127.0.0.1`; không có secrets/app volumes hay lệnh động trong relay. Network/container dọn theo exact IDs và nhãn ownership. Không dùng network production cho target.

Build từ workspace trên **máy vận hành có Docker**, không cấp Docker socket cho backend production:

```powershell
docker build -f backend/tests/docker/backup_relay.Dockerfile -t qnu-backup-relay:424 .
$env:BACKUP_DRILL_RELAY_IMAGE = docker image inspect --format '{{.Id}}' qnu-backup-relay:424
$env:BACKUP_DRILL_ENABLED = 'true'
```

Ubuntu dùng cùng build, lấy image ID và cấp hai biến trên qua môi trường của CLI/BE vận hành. Yêu cầu image ID dạng `sha256:...`, không tự chọn tag latest. PG/MinIO/Qdrant images tương thích vẫn cần sẵn như runbook đợt 1. Khi thiếu relay, fail-closed; không tự fallback sang mạng có quyền đi ra ngoài. Chỉ dùng backup có nguồn gốc tin cậy; restore dump SQL không phải thao tác an toàn cho file tùy ý.

## Kho bí mật bên ngoài

Chỉ cấu hình **đường dẫn tuyệt đối**, không nội dung mật khẩu/khóa:

| Biến | Nội dung file bên ngoài |
|---|---|
| `BACKUP_SCHEDULE_SECRET_FILE` | Mật khẩu riêng cho lịch, UTF-8 một dòng 12–256 ký tự; lưu bản riêng để có thể khôi phục offline |
| `BACKUP_REMOTE_CREDENTIALS_FILE` | JSON có `access_key`, `secret_key`, tùy chọn `session_token`, do kho bí mật cấp |

File phải là file regular, không symlink, không nằm trong thư mục backup/storage/configs được capture, tối đa 16 KiB. Ubuntu kiểm tra owner là tài khoản app và không cấp quyền group/other (0400 hoặc 0600); Windows quản trị phải cấp ACL chỉ service account/nhóm vận hành tin cậy. Thư mục cha cũng phải được bảo vệ. Với secret volume có symlink, mount regular file/subPath phù hợp; không tự nới quyền kiểm tra.

BE và worker cần nhìn thấy cùng file/policy directory. Production Compose đã chuyển tiếp biến path nhưng **không tự mount file**; vận hành thêm read-only secret mounts trên các service cần dùng. Không đặt plaintext mật khẩu/khóa vào `.env`, repository, API request chính sách hoặc catalogue. SDK đọc bí mật lúc chạy; thiếu/không đọc được thì thông báo lỗi, không giả thành công. Bản sao lưu không bao gồm file secret mount này, nên phải quản lý vòng đời/khôi phục kho bí mật riêng.

## S3/MinIO ngoài máy

Tạo bucket riêng và tài khoản giới hạn cho bucket/prefix backup. Trang Chính sách chỉ nhập endpoint/bucket/prefix/region, không khóa. Không dùng cùng bucket nguồn của app; chọn nơi lưu độc lập, HTTPS với certificate tin cậy nếu không phải môi trường localhost mẫu. Endpoint khác chưa đảm bảo khác máy/ổ vật lý.

Bật Tự chuyển sau sao lưu hoặc bấm Chuyển S3 cho bản local đã đạt toàn vẹn. Upload multipart bounded memory rồi **đọc lại toàn bộ**, SHA-256 và kích thước phải khớp; không coi ETag multipart là checksum. Lưu object version ID khi có versioning, object key chứa ID và hash. Không tự tạo bucket, không tự xóa object remote. Giữ retention/versioning/immutability của remote theo chính sách vận hành riêng.

UI phân biệt bản local hoàn tất và S3 verified/failed. Khi chuyển S3 lỗi, giữ bản local và hiện thông báo riêng; có thể thử lại. Nếu local đã bị thay đổi, xóa chứng nhận toàn vẹn và báo lỗi local, không gắn nhãn thành công cho một file hỏng.

## Lịch và giữ bản cũ

Chọn hằng ngày/hằng tuần, giờ/phút, ngày tuần và UTC offset (Việt Nam = 420 phút). Tính lần kế tiếp bằng thời điểm timezone-aware; bật/sửa lịch không chạy bù quá khứ. Worker cron kiểm tra ở giây 10/40 mỗi phút, nhưng launch runner độc lập, **không giữ shared maintenance lock của worker xuyên capture**. Filesystem reservation lock và next_run_at chống hai lượt tick chạy trùng. Worker tắt thì lịch không chạy; không có OS scheduler/service tự khởi động app trong đợt này.

Nếu còn job/workflow pending/running/retryable hoặc backup đang chạy, hoãn, không tự hủy/đổi trạng thái/phát lại. Gửi tác vụ xong mới tiến tới lịch kế tiếp; lịch gửi thành công chưa đồng nghĩa bản backup hoàn tất. Lỗi lưu/gửi có thông báo an toàn, không lộ credential.

Giữ hợp nhất bản gần nhất của N nhóm ngày, tuần ISO và tháng, giữ thêm bản mới nhất/bản đã drill gần nhất/bản ghim. Chỉ thực hiện sau một lần create hoàn tất; nếu bật S3 mà chuyển lần mới thất bại thì không tự dọn. Bản cũ không có hash S3 khớp không bị gỡ khi S3 đang bật.

**Xóa và tự dọn hiện là gỡ có phục hồi**: chuyển đúng archive/metadata vào `.trash/<id>`, ghi actor/correlation/time. Không gỡ bản pinned, không gỡ khi có thao tác active, không xóa bản tốt cuối cùng. Không xóa vĩnh viễn nên **chưa giải phóng dung lượng**; chưa có nút phục hồi từ thùng tạm hoặc tự purge. Vận hành đối soát và phục hồi file theo audit khi cần; không tự chuyển đè bản mới. Giao diện nêu rõ giới hạn này, không gọi nó là retention remote.

## Tiến độ và kiểm chứng

Tách Mã hóa và Giải mã kiểm tra, hiện thời gian bước hiện tại, byte thực của upload/S3 khi có, lỗi bước và lỗi remote riêng. Phần trăm theo giai đoạn, không phải ETA; không giả tiến độ byte cho bước không đo. Upload có heartbeat/throttle metadata để không bị coi chết lúc chờ mạng và không ghi file lịch sử mỗi block. Windows atomic replace retry có giới hạn khi reader đang mở file; lỗi quyền thật vẫn báo lỗi.

Thử nghiệm chỉ dữ liệu mẫu: unit/security Windows+Ubuntu, Docker thật PG/MinIO/Qdrant, encrypted copy/readback, HTTP import+restore, lịch deferred/concurrent. Chưa thao tác restore/copy corpus thật khoảng 1 GB; UI browser test dừng tại sign-in, chưa kiểm chứng authenticated/mobile/dark. Xem nhật ký phiên 424 cho kết quả cuối và baseline của full suites.
