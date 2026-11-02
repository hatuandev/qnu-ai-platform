# QNU AI Platform — V1

Mã đang được phát triển và các lệnh mặc định dùng **backendV1/** (FastAPI/Python3.12) và **frontendV1/** (React/TypeScript/Vite). Backend/frontend cũ còn trong repository để giữ dữ liệu và lịch sử; lệnh mặc định không chạy chúng.

## Chạy trên laptop

Cần Python3.12, uv, Node.js22.12+ và Docker Desktop. Bản đã có dữ liệu: giữ nguyên `.env`, khóa mã hóa và đích lưu trữ; không chép template đè lên cấu hình đang dùng.

```powershell
.\make.ps1 help
.\make.ps1 check
.\make.ps1 dev
```

`dev` chạy API8002, worker V1 và giao diện3001 ở foreground. Ctrl+C dừng riêng các tiến trình của phiên này. Lệnh kiểm hạ tầng/schema trước, không tự migration hoặc seed. Nếu cổng đang bận, dừng đúng phiên cũ trước.

Máy mới xem [hướng dẫn V1](docs/quy_trinh/38_huong_dan_chay_qnu_v1.md): tạo cấu hình riêng từ `.env.example`, cài `install-be`/`install-fe`, khởi động `infra-up`, chủ động `migrate` sau khi xác nhận database, rồi `check` và `dev`.

| Tác vụ | Lệnh |
| --- | --- |
| API / worker / giao diện riêng | `.\make.ps1 be` / `worker` / `fe` |
| Hạ tầng local | `.\make.ps1 infra-up` / `infra-status` / `infra-down` |
| Xem revision / nâng schema V1 | `.\make.ps1 db-check` / `migrate` |
| Test BE cô lập / test FE | `.\make.ps1 test-be` / `test-fe` |
| Kiểm mã / TypeScript / build FE | `.\make.ps1 lint` / `typecheck` / `build` |
| E2E từng chặng | `.	est-v1-e2e.ps1 help` |

CMD dùng `make.bat`, Bash dùng `./make`, GNU Make dùng `make`. Tên `v1-*` vẫn tương đương. `--dry-run` chỉ in kế hoạch, ví dụ `.\make.ps1 dev --dry-run`. GNU Make dùng `make dev ARGS=--dry-run`.

`seed`, `reset-db`, `reseed`, `reconcile`, `reindex` legacy không còn được chạy từ root runner. Việc thay tài liệu, lập chỉ mục và quản trị model dùng các thao tác có quyền trong UI V1.

## Docker và server demo

[Quy trình Dokploy V1](docs/trien_khai/02_quy_trinh_trien_khai_dokploy.md) dùng root `docker-compose.yml`: bootstrap chỉ nâng schema V1, API/worker dùng package `qnu`, frontend build từ frontendV1 và Nginx proxy nguyên đường dẫn `/platform/v1alpha1`.

`.env.dokploy.example` là template server; không dùng nguyên placeholder để deploy. Hạ tầng server có sẵn, giữ DB/bucket/volume và khóa mã hóa. Không tự chuyển dữ liệu legacy thành dữ liệu V1. Production yêu cầu SSO và tắt dev login. App/worker không tự chạy migration.

MinerU là giao thức OCR task PDF trong ModelOps; cấu hình URL/key/model, quyền và default qua UI. Nguồn, ZIP OCR, bảng/ảnh, bản sửa và lịch sử được giữ. Xem [MinerU V1](docs/quy_trinh/V1_MINERU_OCR_MAC_DINH.md).

## Cấu trúc hiện hành

- `backendV1/qnu/`: API, domain/service, adapter và worker.
- `backendV1/alembic/`: chuỗi migration riêng `alembic_version_backendv1`.
- `frontendV1/`: giao diện và client V1.
- `scripts/run_v1.py`: runner dùng chung; `scripts/v1_e2e_*`: E2E cô lập.
- `docker-compose.infra.yml`: PostgreSQL/Redis/Qdrant/MinIO/Gotenberg local, giữ named volumes hiện có.
- `docs/`: quy trình, nhật ký và bằng chứng. Nhật ký cũ có thể mô tả runtime legacy.

Chỉ báo PASS cho kiểm tra thực chạy; code build được không chứng minh chất lượng OCR hoặc câu trả lời của model.
