# QNU AI Platform — V1

Môi trường dev mặc định dùng **backendV1/** (FastAPI/Python 3.12) và **frontendV2/** (React/TypeScript/Vite). **frontendV2 là giao diện duy nhất**; frontendV1 và hai thư mục backend/frontend cũ đã được gỡ khỏi checkout. Mã đã commit còn trong lịch sử Git, dữ liệu ignored được lưu riêng trước khi gỡ.

## Chạy trên laptop

Cần Python3.12, uv, Node.js22.12+ và Docker Desktop. Bản đã có dữ liệu: giữ nguyên `.env`, khóa mã hóa và đích lưu trữ; không chép template đè lên cấu hình đang dùng.

```powershell
.\make.ps1 help
.\make.ps1 check
.\make.ps1 dev
```

`dev` chạy API V1 ở cổng 8002, worker V1 và [Frontend V2 ở cổng 3002](http://127.0.0.1:3002/). Lệnh kiểm tra hạ tầng và schema trước khi chạy. Ctrl+C dừng các tiến trình của phiên này. Nếu cổng đang bận, dừng đúng phiên cũ trước.

Máy mới cài backend bằng `.make.ps1 install-be` và chạy `npm ci` trong `frontendV2`. Thiết lập hạ tầng và schema theo [hướng dẫn chạy local](docs/quy_trinh/38_huong_dan_chay_qnu_v1.md).

| Tác vụ | Lệnh |
| --- | --- |
| API / worker / Frontend V2 riêng | `.\make.ps1 be` / `worker` / `fe2` |
| Hạ tầng local | `.\make.ps1 infra-up` / `infra-status` / `infra-down` |
| Xem revision / nâng schema V1 | `.\make.ps1 db-check` / `migrate` |
| Test BE cô lập | `.\make.ps1 test-be` |
| Kiểm mã / TypeScript / build FE | `.\make.ps1 lint` / `typecheck` / `build` |

CMD dùng `make.bat`, Bash dùng `./make`, GNU Make dùng `make`. Xem kế hoạch bằng `.\make.ps1 dev --dry-run` hoặc `make dev ARGS=--dry-run`.

`seed`, `reset-db`, `reseed`, `reconcile`, `reindex` legacy không còn được chạy từ root runner. Việc thay tài liệu, lập chỉ mục và quản trị model dùng các thao tác có quyền trong UI V1.

## Docker và server demo

[Quy trình Dokploy V1](docs/trien_khai/02_quy_trinh_trien_khai_dokploy.md) dùng root `docker-compose.yml`: bootstrap chỉ nâng schema V1, API/worker dùng package `qnu`. Compose hiện chỉ có backend/worker vì frontendV2 chưa có SSO production; website trên server vẫn giữ bản cũ cho tới khi V2 có đăng nhập thật.

`.env.dokploy.example` là template server; không dùng nguyên placeholder để deploy. Hạ tầng server có sẵn, giữ DB/bucket/volume và khóa mã hóa. Không tự chuyển dữ liệu legacy thành dữ liệu V1. Production yêu cầu SSO và tắt dev login. App/worker không tự chạy migration.

MinerU là giao thức OCR task PDF trong ModelOps; cấu hình URL/key/model, quyền và default qua UI. Nguồn, ZIP OCR, bảng/ảnh, bản sửa và lịch sử được giữ. Xem [MinerU V1](docs/quy_trinh/V1_MINERU_OCR_MAC_DINH.md).

## Cấu trúc hiện hành

- `backendV1/qnu/`: API, domain/service, adapter và worker.
- `backendV1/alembic/`: chuỗi migration riêng `alembic_version_backendv1`.
- `frontendV2/`: giao diện duy nhất, chạy dev ở cổng 3002.
- `scripts/run_v1.py`: runner dùng chung cho backend và Frontend V2.
- `docker-compose.infra.yml`: PostgreSQL/Redis/Qdrant/MinIO/Gotenberg local, giữ named volumes hiện có.
- `docs/`: quy trình, nhật ký và bằng chứng. Nhật ký cũ có thể mô tả runtime legacy.

Chỉ báo PASS cho kiểm tra thực chạy; code build được không chứng minh chất lượng OCR hoặc câu trả lời của model.
curl -I http://qnu-qdrant:6333/collections -H "api-key: gm9nwafg3rjyp9jbtvwyop9kofyrhzyx"

Tư vấn đề án tuyển sinh, chỉ tiêu, tổ hợp môn, phương thức xét tuyển và học phí của Trường Đại học Quy Nhơn.

Bạn là Trợ lý tư vấn tuyển sinh chính thức của Trường Đại học Quy Nhơn (QNU).

1. Phong cách & Xưng hô:
- Luôn giữ văn phong thân thiện, nhiệt tình, chuẩn mực sư phạm và truyền cảm hứng.
- Xưng hô: xưng "mình" hoặc "Trợ lý Tuyển sinh QNU", gọi người hỏi là "bạn" (hoặc "em" nếu người hỏi xưng là học sinh/thí sinh).

2. Nguyên tắc thông tin:
- Trả lời trung thực, chính xác và bám sát 100% thông tin trong các đề án, thông báo và tài liệu tuyển sinh chính thức được cung cấp.
- Tuyệt đối không tự bịa đặt, suy đoán điểm chuẩn, chỉ tiêu hoặc quy định không có trong văn bản.
- Nếu tài liệu chưa có thông tin hoặc người hỏi chưa nêu rõ năm/ngành, hãy giải thích rõ và hướng dẫn cụ thể cách đặt câu hỏi.

3. Cách trình bày:
- Mở đầu nhã nhặn, đi thẳng vào trọng tâm câu hỏi.
- Khi liệt kê các ngành, tổ hợp môn hoặc tiêu chí, hãy phân nhóm rõ ràng và sử dụng gạch đầu dòng để dễ đọc.
- Kết thúc câu trả lời bằng lời dặn dò, động viên và gợi ý thí sinh đặt câu hỏi tiếp theo nếu cần thêm chi tiết.