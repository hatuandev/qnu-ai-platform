# Vận hành tác vụ và sao lưu bằng chứng — Backend v1

API nằm tại `/platform/v1alpha1/workspaces/{workspace_id}/operations`.
Workspace là biên giới quyền của v1: server kiểm membership/role trước khi đọc
tài nguyên. Mọi phản hồi đặt `private, no-store`.

## Theo dõi và phục hồi

| API | Nội dung |
|---|---|
| `GET /jobs?kind=ocr&status=completed&limit=20&offset=0` | Danh sách/phân trang; lọc collection nếu được cấp quyền |
| `GET /jobs/{kind}/{job_id}` | Trạng thái, lỗi, lease, attempts và tiến độ quan sát |
| `GET /summary` | Số tác vụ theo trạng thái và usage thực ghi nhận |
| `POST /jobs/{kind}/{job_id}/recovery-preview` | Xem trước giao lại job với `{"reason":"..."}` |
| `POST /actions` | Chấp nhận `preview_id/preview_sha256`, bắt buộc `Idempotency-Key` |
| `GET /actions/{id}` | Theo dõi intent vận hành bền vững |

Các loại: OCR, Compiler, index, auto-review, review thủ công, gợi ý chính tả,
lượt hội thoại và backup. Editor/admin/reviewer đọc danh sách; editor/admin
thực hiện phục hồi. Backup yêu cầu admin. Người giao việc nền phải còn membership
DB phù hợp, kể cả khi token hiện tại có quyền quản trị nền tảng.

OCR hiển thị số trang đã xử lý; index hiển thị số chunk đã có vector. Những bước
không có mẫu số giữ `null`, không tạo phần trăm giả. Token/cost chưa quan sát
cũng giữ `null`; tổng usage phân biệt reservation với token/cost đã biết.

Chỉ job `queued` hoặc `running` hết lease có executor phù hợp mới được giao lại.
Worker gốc vẫn kiểm quyền, snapshot, provider và checkpoint. Không đổi job
`failed/uncertain` thành queued; không tự gửi lại lượt model chưa rõ kết quả.
Review/gợi ý/turn đồng bộ không có thao tác resend qua operations.

Preview ghim actor, workspace, job, trạng thái/hash, lý do và thời hạn. Sau khi
chấp nhận, intent `pending` được commit trước queue I/O. Queue lỗi giữ intent;
cron reconcile trên ARQ v1 giao lại bằng ID cố định. Quyền hoặc trạng thái đích
đổi thì intent bị superseded. Replay cùng key không tạo thao tác mới.

## Bản sao bằng chứng

| API | Nội dung |
|---|---|
| `POST /backups` | Body `{}` giữ vô thời hạn, hoặc `{"retention_days":30}`; có idempotency |
| `GET /backups` và `GET /backups/{id}` | Danh sách/trạng thái; không lộ storage key |
| `GET /backups/{id}/verify` | Kiểm SHA, inventory, snapshot và từng object |
| `GET /backups/{id}/download` | ZIP đã kiểm, chỉ admin |
| `GET /retention` | Chính sách và backup đã hết hạn có thể đề nghị xóa |
| `POST /backups/{id}/delete-preview` | Đề nghị xóa backup hết hạn; chấp nhận qua `/actions` |

Worker chụp metadata của một workspace trong MVCC snapshot, đọc lại tệp và kiểm
checksum rồi tạo ZIP. Gói gồm nguồn gốc, raw OCR, bản hậu OCR đã lưu, Compiler,
review và manifest/receipt chỉ mục được tham chiếu trong snapshot. Bảng provider,
credential và khóa mã hóa toàn cục được loại. Gói vẫn chứa nội dung tài liệu và
dữ liệu workspace, nên phải được lưu như dữ liệu riêng có kiểm soát quyền.

Giới hạn hiện tại: 256 MiB, 10.000 object, tối đa 100.000 row mỗi bảng. Vượt giới
hạn hoặc thiếu/hỏng nguồn trả lỗi; không công bố bản sao thiếu tệp. ZIP được
kiểm lại sau khi lưu; mất lease không được đánh dấu completed.

ZIP workspace này là bản sao **bằng chứng**, không dùng để khôi phục database,
credential hoặc Qdrant. Bộ [recovery backendV1](recovery.md) riêng đã hỗ trợ bundle
mã hóa toàn dữ liệu v1 và phục hồi vào DB/kho/namespace vector mới.

Nguồn gốc/raw được giữ vô thời hạn; không có cron xóa tự động. Xóa chỉ áp dụng
backup đã hết retention, theo preview/acceptance/idempotency/audit; không xóa
nguồn OCR, bản biên soạn hay chỉ mục. Blob dẫn xuất mồ côi có
[preview/xác nhận dọn](storage-cleanup.md); generation vector cũ dùng lifecycle.
Không tự purge nguồn gốc hoặc raw.

Kiểm tra dependency, worker và cấu hình ModelOps qua [readiness](readiness.md).

Baseline `0001_initial_schema` đã bao gồm hai bảng `ops_actions/ops_evidence_backups`.
Migration `0002_operational_readiness` thêm biên nhận dọn dẫn xuất và review ack.
Chỉ áp vào database đã xác nhận ownership. Batch triển khai này dùng DB thử riêng.
