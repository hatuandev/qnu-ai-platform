# Context641 — Capacity ModelOps backendV1

Ngày 2026-10-26. Người dùng đang chạy prompt OCR ở tác vụ khác và giao xử lý ngay
capacity khi tạo model. Kết quả: phần đăng ký/kiểm ngân sách capacity đã hoàn thành,
regression trọng tâm PASS; **full suite vẫn FAIL**, chi tiết bên dưới.

## Thay đổi

- API POST/PATCH provider nhận `token_limits`: context_window_tokens,
  max_input_tokens, max_output_tokens. Số nguyên dương, không trần8K/32K dùng chung.
  Context dùng chung và input/output độc lập giữ đúng nghĩa; unknown/null không
  phải unlimited. Test giá trị1.048.576/65.536 là khai báo tổng hợp, không chứng minh
  capacity của một model thật.
- Response thêm token_limits/capacity_status/capacity_basis. Profile lưu trong
  JSONB hiện có, ghim endpoint/model ở server, basis operator_configured. Đổi đích
  vô hiệu profile; đổi lại không tự phục hồi. PATCH bỏ qua giữ nguyên, null xóa
  tường minh. Không cho client tự khai verified/provider_reported.
- Public API `resolve_model_capacity` kiểm quyền/grant/capability/active và trả
  snapshot cùng configuration_hash; `plan_model_request` tính input+reserve+output
  theo đúng giới hạn đã biết, báo lỗi khi unknown/vượt capacity, không cắt nguồn
  hoặc clamp yêu cầu đầu ra tường minh. Token ảnh/framing phải do runtime tính đúng
  protocol; không đếm Base64 thành token ảnh.
- Gỡ trần validation32768 vừa được phần OCR thêm vào OCR_MAX_OUTPUT_TOKENS. Mặc
  định8192 vẫn là ngân sách workflow được ghim, không phải context hoặc capacity.
- Giữ các sửa OCR đồng thời trong public_api/config. Không sửa migration, schema
  bảng hoặc code legacy;475file backend/app giữ hash so đầu phiên.

Files chính: `backendV1/qnu/domains/modelops/capacity/`, schemas.py,
providers/service.py, public_api.py, platform/config.py và hai test_model_capacity_641.py.
OpenAPI được xuất lại, có39path gồm phần OCR đồng thời; capacity chỉ thêm field.

## Kiểm chứng đã chạy

| Lượt | Kết quả |
|---|---|
| Baseline API capacity, trước sửa |3FAIL/2,99s/exit1: trường chưa được nhận hoặc response chưa có capacity |
| Baseline riêng trần OCR32768 |1FAIL/0,51s/exit1: cấu hình65536 bị validation chặn |
| Focused lần đầu |43PASS/17,34s/exit0 |
| Focused cuối |**44PASS/0FAIL/0SKIP**,15,33s,exit0;33ca mới +11ca ModelOps boundary sẵn có |
| Full v1 trên snapshot đã seal |**152PASS/2FAIL/0SKIP**,51,70s,exit1;33ca capacity mới đều PASS |
| Ruff/format phạm vi10file |PASS/exit0 |
| OpenAPI export + kiểm capacity schema |PASS/exit0; không có maximum chung cho token limits |

Lệnh focused, cwd `backendV1`, đúng venv đã khóa:

```powershell
.venv\Scripts\python.exe -X utf8 scripts/run_isolated_tests.py tests/unit/test_model_capacity_641.py tests/integration/test_model_capacity_641.py tests/integration/test_workspace_model_boundaries.py -q --tb=short
.venv\Scripts\ruff.exe check qnu/domains/modelops/capacity qnu/domains/modelops/schemas.py qnu/domains/modelops/providers/service.py qnu/domains/modelops/public_api.py qnu/platform/config.py tests/unit/test_model_capacity_641.py tests/integration/test_model_capacity_641.py
.venv\Scripts\python.exe -X utf8 scripts/export_openapi.py
```

Full chạy cùng venv gốc với `scripts/run_isolated_tests.py tests -q --tb=short`, cwd
`backendV1/storage/context641/full-snapshot`. Snapshot219file source/test/config
được seal trước lượt chạy để thay đổi OCR đồng thời không chen giữa lượt; không
copy .env/credential. Đây là full của snapshot đó, không phải chứng nhận mọi file
OCR mới được tác vụ khác thêm sau khi chụp.

Hai test còn FAIL trong full:

1. `tests/integration/test_knowledge_regressions_639.py::test_downgrade_cannot_mark_success_and_block_next_upgrade`:
   test kỳ vọng thông báo Knowledge evidence và version0005; migration0006 OCR mới
   chặn downgrade trước với OCR evidence. Không sửa/nới test ngoài phạm vi capacity.
2. `tests/integration/test_knowledge_regressions_639.py::test_same_key_writers_do_not_fail_storage_under_contention`:
   WinError5 khi replace, tiếp theo PermissionError lúc đọc file đích. Driver local
   giữ nguyên hash đầu phiên; lỗi thuộc nhánh ghi file đồng thời, chưa sửa ở641.

Không gọi hai lỗi này là baseline đã được đối chứng trước/sau; chỉ xác nhận exact
IDs/cause và source liên quan ngoài diff capacity. Toàn suite vẫn FAIL.

DBtest của phiên: c8253cc94b4447c6,9bcc579fd34e4943,fdd90d6554bd4d18 và
5f9ed8923442493d (prefix qnu_v1_test_). Cả4được dọn, sentinel/version legacy giữ,
đối soát catalog0còn lại. Không đụng DBtest tác vụ khác; DB chính chưa version v1.
Log/XML/receipt/source seal được Git ignore dưới storage/context641 và context636.

## Điểm nối và giới hạn

Phần này chưa tự động discovery metadata provider, chưa đo token ảnh hoặc gọi
Nemotron thật. Profile quản trị không được báo verified. Tác vụ OCR đang viết phải
gọi guard trước HTTP và ghim/check configuration_hash khi chạy lại. Hiện helper
chưa được OCR execution gọi; không tuyên bố đã bỏ ngân sách workflow8192 hoặc đã
kiểm context OCR đầu-cuối. Không tự sửa execution.py đang thuộc tác vụ kia.

Không migrate DB phục vụ, restart/deploy, đổi default/provider/key hoặc commit/push.
[Hợp đồng tích hợp](../../../backendV1/docs/model-capacity.md) ·
[ADR010](../../../backendV1/docs/decisions/ADR-010-model-token-capacity.md).
