# Context695 — Nhóm khóa, dự phòng theo tác vụ và registry ModelOps V1

Ngày: 28/10/2026. Người dùng yêu cầu triển khai tiếp mục3–5 từ nghiên cứu9router
(Context693), sau discovery/probe của Context694. Baseline source HEAD
`f37f740a`, nhánh `v1.0.2`; giữ các sửa đổi tài liệu đang có của phiên694.

## Kết quả và phạm vi

- Nhóm khóa dùng các cột lease/cooldown/failure hiện có, chủ sở hữu UUID có
  fencing trong JSON bảo vệ của provider. Chọn khóa nguyên tử bằng khóa hàng
  PostgreSQL, không giữ transaction trong lúc gọi model. Revoke/rotate dùng
  cùng thứ tự provider → key để tránh deadlock của audit FK.
- Tối đa3lượt trong cùng deadline, chỉ401/429 được đổi khóa cùng provider/model;
  có usage dương thì không thử lại. Lỗi400/403/422,5xx chưa rõ, timeout và hủy
  không đổi khóa. Gateway/9router chịu retry thì QNU chỉ gửi một lần.
- Chuỗi dự phòng tường minh theo tác vụ, chỉ chọn trước dispatch/đặt ngân sách.
  Model chọn cụ thể được ghim; mỗi candidate kiểm grant/capability/adapter,
  capacity theo model được chọn và quota vẫn kiểm như cũ. Không tự đổi model
  embedding trong generation hoặc model OCR/Compiler giữa run.
- Nối container thật cho chat/OCR/embedding/rerank; scope nội bộ mang factory
  của DB người gọi. Attempt liên kết usage đã reserve, có thời gian/model/khóa/
  mã lỗi/token quan sát, không lưu prompt/ảnh/raw response/credential trong audit.
- Registry BE → FE mô tả adapter, schema request chưa chứng nhận model, ảnh/
  input nhiều phần tử, Responses/tools/streaming chưa hỗ trợ. Gemini/PaddleOCR
  giữ cấu hình nhưng không giả có adapter. Không ép đổi schema endpoint+model.
- FE có **Khóa và dự phòng**, lựa chọn task/chuỗi, bên quản lý retry, cooldown,
  trạng thái khóa và **Lượt gọi gần đây**. Draft cách ly provider/session; lỗi/
  chờ/trống trung thực, token unknown tách với0. Biểu mẫu provider đọc registry.
- Fingerprint chẩn đoán dùng danh tính credential thay cho updated_at vận hành;
  lease/cooldown không làm cũ kết quả mới. Kết quả từ trước nâng cấp có thể cần
  chạy thử lại một lần. Không tự chạy inference để làm mới lịch sử đó.

Không migration mới, dependency mới, sửa .env/khóa thật, đổi default/grant/quota,
reindex, restart tiến trình người dùng, commit hoặc push. Chính sách mặc định
tắt; chưa thiết lập backup model không tồn tại. Không gửi corpus hay gọi model
server AI trong phiên này.

## Bằng chứng và kiểm tra

Artifact: `storage/artifacts/context695-modelops-resilience/` gồm baseline hash,
diff manifest, log/receipt, ảnh desktop và mobile dark. Test DB mới riêng cho
mỗi lượt; không sao chép hàng/credential từ DB ứng dụng; network ngoài loopback
bị chặn trong tiến trình test. Redis test dùng DB15 và queue có tên riêng.

| Kiểm tra | Kết quả |
| --- | --- |
| Replay phương thức revoke/rotate từ HEAD trước sửa, cùng test race và DB thật | FAIL có chủ đích:2ca giữ khóa key trước provider; `lock-order-replay.log` |
| Regression ModelOps + diagnostics | PASS63ca, gồm30ca mới; `final-guards.log` |
| Khôi phục đầy đủ vào DB/storage/vector mới | PASS1ca Proactor; `be-recovery-verified.log` |
| Full BE, Selector và Redis test, tách ca subprocess recovery | PASS715ca,1deselected (recovery tách riêng); `be-full-verified.log` |
| OCR + pool regression sau sửa tái sử dụng kết quả | PASS61ca, gồm31ca mới; `ocr-resilience-final.log` |
| Full FE cuối, tối đa4worker | PASS400ca/40tệp; `fe-tests-verified.log` |
| FE regression mới + diagnostics | PASS14ca; `fe-last-regression.log` |
| Vite build + TypeScript | PASS exit0; `fe-build-verified.log` |
| Ruff có phạm vi / Biome có phạm vi | PASS44tệp Python /10tệp FE |
| Browser thật | PASS: draft pool/gateway về1lượt, reload bỏ draft; desktop light/mobile light+dark, không tràn ngang |
| Fallback giữa nhiều model thật / benchmark chất lượng | NOT RUN; không có backup model thật được cấu hình |

Lệnh chính từ root:

```powershell
uv run --project backendV1 --frozen --extra dev --no-sync python storage/artifacts/context695-modelops-resilience/run_checks.py selector tests/integration/test_modelops_resilience_695.py tests/integration/test_modelops_diagnostics_api.py tests/unit/test_provider_diagnostics.py -q --tb=short
uv run --project backendV1 --frozen --extra dev --no-sync python storage/artifacts/context695-modelops-resilience/run_checks.py selector tests -v --deselect=tests/integration/test_recovery_666.py::test_full_recovery_into_new_targets_keeps_originals_credentials_and_search
uv run --project backendV1 --frozen --extra dev --no-sync python storage/artifacts/context695-modelops-resilience/run_checks.py proactor tests/integration/test_recovery_666.py::test_full_recovery_into_new_targets_keeps_originals_credentials_and_search -q --tb=short
```

Trong `frontendV1`: `npm test -- --maxWorkers=4 --reporter=dot`, `npm run build`
và Biome trên các tệp sửa. Runner kiểm tra trong artifact không phải script
triển khai ứng dụng; nó dùng harness DB dùng một lần hiện có.

Các lượt đầu có lỗi fixture/import test và đã sửa rồi chạy lại. FE lần đầu
392PASS/1FAIL timeout tại `maintenance-evaluation-ui-679.test.tsx` / `evaluation
caps the editable question list at twenty`; lượt4worker cuối400PASS, không sửa
assertion hay mã của bài kiểm tra đó. Recovery ban đầu FAIL do runtime đọc
reservation ở DB gốc; đã sửa theo DB của người gọi và tái hiện qua đúng luồng
restore đạt. Một lượt BE tổng đang chạy bị dừng ở tiến trình test riêng khi phát
hiện lỗi này để sửa trước gate cuối; harness đã dọn DB và giữ sentinel.

Sau gate715ca, bổ sung test API tái sử dụng OCR qua provider dự phòng khi primary vẫn tắt: tái hiện409 trước sửa (`ocr-reuse-red.log`), rồi sửa `_reusable_run` dùng cùng chính sách chọn target. Lượt61ca chạy sau thay đổi này gồm toàn bộ31ca ModelOps mới và30ca OCR cũ; tất cả PASS. Không chạy lại toàn suite sau thay đổi có phạm vi này.

Hai guard về OCR anonymous và phân biệt khóa cooling được kiểm trong lượt63ca
cuối; không đổi lỗi hạ tầng thành câu trả lời rỗng. Raw OCR cuối vẫn do domain
OCR lưu; các lần từ chối credential chỉ lưu metadata an toàn trong attempt audit.

## Vận hành và tài liệu

Đã đóng tab/preview server riêng8014/3004, trả viewport/theme thử về mặc định.
Tiến trình người dùng8002/3001 giữ nguyên. Phiên `v1-dev` cũ không tự nạp BE;
người dùng chạy lại đúng phiên đó khi muốn dùng mã mới. Không cần chạy migration.

- [Hướng dẫn40](../quy_trinh/40_modelops_khoa_va_du_phong.md).
- [Hợp đồng BE](../../backendV1/docs/modelops-resilience.md).
- [OpenAPI](../../backendV1/docs/openapi-v1.json) được xuất lại từ app thực.

Giới hạn chủ ý: không chuyển model sau HTTP, không tự nới quyền/quota/context,
không cloud fallback embedding, không auto health polling hoặc tuyên bố model
đã đạt strict JSON chỉ vì adapter gửi được schema.
