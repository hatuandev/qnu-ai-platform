# Phiên 513 — Chỉnh prompt tuyển sinh

## Phạm vi

Người dùng duyệt bước 1: chỉnh prompt chatbot, không làm bước chuẩn hóa hay
nạp tài liệu. Dùng skill chatbot-builder để đối chiếu contract/tool thực tế,
backend và clean-code để giữ thay đổi có phạm vi. Không thay routing hoặc guard.

## Thực hiện

- Đọc DB local: prompt admissions khớp bản mẫu cũ, SHA256
  `11c9e393f7460608ee94169a506ea4c376e995045a810e42dfdeb4f3e144f194`.
- Sửa riêng prompt admissions trong `backend/app/modules/assistants/seeder.py`:
  bỏ biên điểm/đảm bảo trúng tuyển và ví dụ nghề nghiệp không nguồn; phép tính cần
  rule duyệt và công cụ thực chạy; xuất tệp chỉ khi có kết quả thật; không ép
  khối gợi ý cuối đáp án. Giữ giọng mình/bạn, đúng trọng tâm, năm/phương thức,
  follow-up và trích dẫn; phân biệt thiếu căn cứ với lỗi hệ thống.
- Áp dụng bằng local administrator qua `assistant_service.update_assistant`,
  `AssistantUpdateRequest` chỉ chứa `system_prompt`. Trước ghi dùng row lock và
  so khớp hash đã đọc; sao lưu mã hóa trước và sau thay đổi. Không chạy script
  đồng bộ prompt toàn bộ trợ lý.
- Đọc lại: SHA256 mới
  `e3136f28d5c864356c494ad5eb57c4ebfd27c0e85ee66d47ed06f2d4fa4f9445`,
  5.111 ký tự. Mọi cột ngoài prompt/updated_at của admissions và cả bốn trợ lý
  khác không đổi. Runtime profile chứa prompt mới và revision mới; fingerprint
  cache hiện có bao gồm prompt/revision nên không cần xóa cache chung.
- Seed vẫn chỉ tạo trợ lý thiếu, không ghi đè cấu hình người dùng. DB server
  Dokploy không nằm trong lần áp dụng local này.

## Sao lưu mã hóa qua StorageDriver (S3)

Trước sửa:
`snapshots/configuration-seed/20261017T090800Z_6cb9ce47b7b545d7b7c7de98143d2915.enc`

SHA256: `a5c2890caf5085f4b661b227a63e33218dcafcab718d9c1a14dd804e1b844525`.

Bản mới nhất, có prompt đã sửa:
`snapshots/configuration-seed/20261017T090801Z_b1bce2571b7e40e99dd20e07488f5da1.enc`

SHA256: `3c600195af2cd8fc592ff35cf6ef7a04e6080d7aa697c04cfd3fb174e386c0f2`.

Mỗi capture đã đọc lại/giải mã; 5 trợ lý, 12 provider configs, 5 collections,
5 bộ workflow, 37 document types. Không chứa tệp nguồn/vector. Phải giữ khóa
giải mã hạ tầng; restore hiện tại chỉ nhận DB cấu hình rỗng, không dùng restore
toàn gói để rollback một prompt trong DB đang sử dụng.

## Kiểm chứng

CWD: `backend`, dùng `.venv/Scripts/python.exe`.

- `-m pytest tests/test_admissions_prompt_513.py tests/test_assistants.py -q
  --tb=short --basetemp=storage/prompt513-focus-temp
  --junitxml=storage/prompt513-focus.xml`: exit 0, **14 PASS**.
- `-m pytest tests/test_admissions_prompt_513.py -q --tb=short
  --basetemp=storage/prompt513-final-temp`: exit 0, **2 PASS** sau chỉnh timezone
  fixture (Ruff lần đầu phát hiện DTZ001; đã sửa, không đổi assertion).
- `-m ruff check app/modules/assistants/seeder.py
  tests/test_admissions_prompt_513.py`: exit 0, **PASS**.
- `-m pytest -q --tb=short --basetemp=storage/prompt513-full-temp
  --junitxml=storage/prompt513-full.xml`, output `storage/prompt513-full.txt`:
  exit 1, **1.944 PASS / 11 FAIL / 17 SKIP**, 210,38 giây. Exact test IDs so XML
  với phiên512 trùng cả 11; tổng suite vẫn **FAIL**, không sửa lỗi nền:
  - `tests.test_consulting_dispatcher::test_dispatch_admissions_with_export`
  - `tests.test_consulting_dispatcher::test_dispatch_regulations_with_export`
  - `tests.test_publishing_v2_cutover_and_gc::test_gc_api_endpoint`
  - `tests.test_publishing_v2_cutover_and_gc::test_canary_policy_get_and_update_api`
  - `tests.test_publishing_v2_decommissioning_and_system_gc::test_direct_upload_blocked_when_flag_disabled`
  - `tests.test_publishing_v2_decommissioning_and_system_gc::test_direct_upload_allowed_when_flag_enabled`
  - `tests.test_publishing_v2_decommissioning_and_system_gc::test_rest_api_system_wide_gc_and_decommissioning_audit`
  - `tests.test_publishing_v2_e2e_canary::test_api_routes_canary_and_rollback`
  - `tests.test_rag_data_truth_and_lifecycle::test_reconciliation_detects_discrepancies`
  - `tests.test_trust_boundary_and_hitl::test_auth_session_cookie_actor_claims`
  - `tests.test_universal_tools::test_dispatch_admissions_with_dynamic_facts`
- Actual DB write/readback, all-column comparison và runtime profile: **PASS**.
- Live model/UI/benchmark: **NOT RUN**. Test hợp đồng prompt không chứng minh
  model luôn tuân thủ, không khẳng định sửa được các lỗi retrieval/packing cũ.

Không reset/seed-all, không reindex, không đổi model/Top K/config, không
restart/deploy/commit/push. Không lưu prompt riêng hay secret trong nhật ký.
