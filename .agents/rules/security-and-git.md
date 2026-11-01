# Bảo mật, dữ liệu và Git

- Ngoại lệ E2E được người dùng xác nhận ngày 01/11/2026: runner provider-setup được đọc riêng E2E_QNU_API_KEY và E2E_9ROUTER_API_KEY từ .env ở root để nạp khóa qua API ModelOps của phiên thử khi chưa có key active. Không export các giá trị từ file này sang tiến trình con, checkpoint hoặc report; không dùng làm fallback/override runtime DB/UI. .env vẫn bị Git ignore, chỉ .env.example chứa giá trị trống. Khóa đã active trong ModelOps được ưu tiên và không tự xoay theo file. Ngoại lệ không áp dụng production hoặc các biến LLM key khác.

- Không hardcode secret/key/password/connection string; không log hoặc trả secret qua DTO/error. LLM credential quản lý qua ModelOps DB có mã hóa/quyền phù hợp, không thêm API key LLM trong .env để vượt cấu hình UI. Bí mật hạ tầng lấy từ cơ chế môi trường/secret store đã có; .env không được commit. Không công bố raw reference nếu nó chứa credential.
- Giữ `DEV_AUTH_ENABLED=False` ở production. Actor/tenant/workspace lấy và kiểm tra ở server. Custom endpoint, discovery, probe và runtime áp cùng egress/auth policy; model không được chọn URL/secret tùy ý.
- Không xuất bản, gửi corpus nội bộ ra ngoài, chạy công cụ ghi, reindex/chuyển active publication, reset DB, deploy hoặc restart dịch vụ nếu ngoài phạm vi người dùng đã cho phép. Có phê duyệt trước đó thì dùng đúng phạm vi, không hỏi lặp. Ngoại lệ trong repo khác không áp dụng ở đây.
- Không commit ảnh scan/PDF/DOCX nguồn, model weights, dataset nội bộ, cache, node_modules, dist hoặc test-results. Nguồn lớn dùng MinIO/S3 hoặc Git LFS nếu người dùng yêu cầu version. Trước khi stage tệp mới trên 500KB phải có yêu cầu/phê duyệt phù hợp.
- Mọi upload/đầu ra tài liệu phải qua StorageDriver được cấu hình (Local dev/S3), có nguồn bền vững trước bước xử lý sau. Không ghi file vào code rồi coi là đã lưu lên object store.
- Không commit/push hoặc đổi remote chỉ để hoàn tất task không yêu cầu Git. Kiểm tra diff và secret trước commit đã được cho phép.

Chính sách remote hiện có (chỉ áp khi thực hiện Git sync được yêu cầu): fetch/pull ưu tiên Gitea `https://qnu-gitea.duckdns.org/admin/qnu-ai-platform.git`; push theo thứ tự Gitea rồi GitHub `https://github.com/hatuandev/qnu-ai-platform.git`, dừng nếu Gitea lỗi. Kiểm tra remote thật trước thao tác; không tự cấu hình lại. Remote phụ `gitea`/`github` giữ như hiện tại.
