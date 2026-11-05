# Giữ cấu hình khi seed hoặc chuẩn bị reset dữ liệu

> **TÀI LIỆU LỊCH SỬ — không phải hiện trạng V1.** Nội dung dưới đây mô tả hệ thống `backend/` + `frontend/` trước V1 (hai thư mục đã gỡ khỏi checkout) và chỉ dùng để truy vết. Bản đang chạy là [`backendV1/`](../../backendV1) + [`frontendV1/`](../../frontendV1); xem [bản đồ tài liệu](../README.md).

## Phân biệt ba thao tác

- **Seed mặc định** chỉ bổ sung preset còn thiếu; không dùng để sao lưu cấu hình
  đã tùy chỉnh. Seed trợ lý nay không ghi đè prompt/config/name/description của
  trợ lý tồn tại. Script `sync_assistant_prompts.py` vẫn là thao tác ghi đè rõ ràng,
  không được dùng để giữ tùy chỉnh.
- **Gói configuration-seed** giữ cấu hình hiện tại đã mã hóa, để khôi phục vào
  DB đã migrate nhưng các bảng cấu hình còn rỗng. Không tự reset hoặc ghi đè DB.
- **Full backup** giữ cả dữ liệu/tệp/vector và cần quy trình backup hiện có.
  Gói cấu hình không thay thế full backup và không phục hồi 22 tài liệu.

## Nội dung gói cấu hình

Giữ assistants và phiên bản cấu hình, providers/model defaults và khóa provider,
collections, workflow definition/draft/version, tool definitions, danh mục loại
văn bản, thuật ngữ/settings/audit. Gói không chứa conversation, tài liệu,
canonical, chunks, vector hoặc executable rule publication.

Toàn payload được mã hóa bằng cơ chế `enc:v1:` của ứng dụng và lưu qua
StorageDriver; không xuất JSON prompt/key dạng rõ ra source hay nhật ký.
Phải sao lưu bảo mật `PROVIDER_ENCRYPTION_KEY` và khóa tương thích từ cấu hình
hạ tầng riêng ngoài DB. Nếu đang dùng fallback `SECRET_KEY` để mã hóa, phải giữ
khóa đó. **Mất khóa giải mã thì gói không dùng được. Không đưa khóa vào Git.**

## Lệnh (cwd `D:/DuAnPhanMem/qnu-ai-platform/backend`)

Tạo gói trước reset, khi DB còn nguyên:

```powershell
.venv/Scripts/python.exe -m scripts.configuration_seed capture --actor local-admin-cli
```

Kết quả chỉ trả StorageDriver key, SHA-256, số bản ghi và schema revision. Gói
được đọc lại và giải mã kiểm tra trước khi báo thành công. Giữ key/SHA và bản sao
tệp mã hóa ở nơi bền vững. Nếu dùng S3/MinIO, key nằm trong bucket đang cấu hình,
không phải một đường dẫn local hoặc public download URL.

Xem trước khôi phục (không ghi DB):

```powershell
.venv/Scripts/python.exe -m scripts.configuration_seed restore --actor local-admin-cli --path <StorageDriver-key> --sha256 <SHA-256>
```

Chỉ khi đã có yêu cầu reset riêng và target đúng, sau khi migrate schema nhưng
**trước seed/bootstrap/startup tự seed**, chạy lại lệnh preview với `--apply` để
khôi phục. Gói và DB phải cùng Alembic revision/cột; khác schema thì dừng, không
tự migrate, merge hoặc xóa. DB có bất kỳ cấu hình nào trong phạm vi sẽ bị chặn
`CONFIG_SEED_TARGET_NOT_EMPTY`. Không xóa dữ liệu chỉ để làm lệnh chạy được.

Trong lần khôi phục được cho phép, giữ backend/worker không ghi đồng thời theo
quy trình vận hành. Công cụ dùng bootstrap advisory lock, table locks, transaction
và giới hạn thời gian; lỗi giữa chừng rollback toàn bộ. Không có HTTP restore
endpoint hoặc tùy chọn overwrite. Actor CLI được ghi trong metadata recovery.

## Sau khôi phục

- Giữ prompt, model/provider, Top K, tham số và tùy chỉnh. Không tự đổi model,
  fallback hoặc gửi dữ liệu sang provider ngoài.
- Không khôi phục active vector generation/counter cũ vào collection rỗng.
  Phải nạp nguồn, kiểm tra staging và xuất bản riêng.
- Công thức/quy tắc tính điểm được giữ trong gói gốc và trường metadata
  `configuration_recovery_archive`, **không khôi phục vào registry đang hoạt động**.
  Sau nạp nguồn mới, đối chiếu/remap source/index/fact IDs rồi qua quy trình duyệt
  và kích hoạt hiện có. Công cụ không giả duyệt hoặc tự kích hoạt lại.
- Thuật ngữ giữ bản ghi và lịch sử; toggle collection được tắt để rà lại scope
  nguồn sau nạp lại tài liệu. Tắt toggle không xóa thuật ngữ.
- Chỉ xóa lease tạm thời của provider key, không reset usage/quota để vượt hạn mức.
- Giữ lại các tệp config/policy hạ tầng và `.env` bằng quy trình bảo mật riêng;
  gói này chỉ chứa các bảng cấu hình đã liệt kê, không tự sao lưu toàn máy.

Mã mới không tự chạy capture/restore ở startup. Người vận hành chọn và preview
gói rõ ràng; không tự dùng “snapshot mới nhất” vì có thể sai môi trường.
