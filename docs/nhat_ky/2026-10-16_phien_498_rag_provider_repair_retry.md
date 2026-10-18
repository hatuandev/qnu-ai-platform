# Phiên 498 — Phạm vi provider RAG, repair JSON và lỗi inference

Ngày: 2026-10-16.

## Yêu cầu, quyền và phương pháp

Người dùng cho phép xử lý theo thứ tự: chặn fallback ngoài phạm vi nội bộ ở backend,
sửa ngân sách repair, bổ sung log an toàn rồi thêm retry tạm thời hữu hạn. Người dùng
xác nhận riêng chỉ cho phép provider `prov_rtx5090_vllm` cho các lượt gọi LLM RAG.

Dùng hướng dẫn Clean Code, Backend, ModelOps và RAG của repo. Giữ thay đổi chưa
commit, không sửa 11 lỗi nền, nguồn/vector/OCR/UI hoặc công cụ quy đổi điểm.
Không gọi benchmark/model thật, không sửa DB/config model, migration, restart,
reindex, deploy, commit hay push. Có bổ sung **cấu hình chính sách máy chủ** đúng
provider người dùng vừa phê duyệt; không thêm secret hoặc ép tên model trong code.

## Nguyên nhân và thay đổi

### 1. Chặn fallback ở backend

Runner gọi API chat nên monkeypatch của runner không ràng buộc tiến trình backend.
Danh sách provider DB có thể đưa cloud fallback vào chuỗi inference.

- Thêm `configs/rag_inference_policy.json` chứa danh sách provider được cho phép;
  đọc theo `get_configs_dir()` tương thích Windows/Ubuntu và image Docker hiện có.
- Thêm `modelops/services/inference_policy.py`: tải file bất đồng bộ, fail-closed,
  ContextVar theo request, không tin giá trị từ client/model/history.
- `RagService.ask` cài phạm vi trước conversation resolver; structured call độc lập
  cũng cài phạm vi. `InferenceService` lọc route trước khi dựng adapter trong cả
  generate và streaming. Sau lỗi primary, cloud không được gọi.
- Model, credential và thứ tự route còn lại vẫn lấy từ ModelOps DB; không sửa DB.
- Đây là policy cho **LLM RAG**, không tuyên bố chặn OCR/embedding/reranker toàn app.

### 2. Bỏ heuristic repair sai

Công thức cũ vừa có thể vượt envelope khi ép floor 256, vừa làm JSON bị cắt khi
hợp đồng cần nhiều output hơn. Không có cửa sổ/tokenizer đo được ở tầng này, nên
không dùng số ký tự để chứng minh ngân sách an toàn.

- Giữ ngân sách output ban đầu cho cả hai attempt; bỏ ngưỡng 4000/256/ước lượng
  ký tự. Không cắt bằng chứng/quote và không suy độ dài JSON đúng từ output lỗi.
- Cửa sổ chưa biết: thực hiện tối đa một repair với ngân sách nguyên vẹn, để provider
  xác nhận request mới. Không tuyên bố chắc chắn vừa trước khi gửi.
- Structured call cấm adapter context-fit tự giảm output; không gọi tokenizer vô ích
  khi không được phép giảm. Context rejection tiếp tục qua ModelOps với mã riêng,
  không tính circuit/key failure. JSON không hợp lệ vẫn fail-closed.

### 3. Log chỉ metadata

- Thêm `provider_failure_diagnostics`: loại exception, HTTP status, reason phân loại,
  upstream request ID chỉ khi đúng UUID. Không ghi body/prompt/quote/key/URL.
- Áp dụng ở generate và streaming. Không đưa message upstream vào fallback trace.
- Log lỗi hợp đồng chỉ ghi stage/attempt/số lỗi/provider/model, không ghi tên field
  tùy ý do model sinh. Diagnostics phản hồi cho caller vẫn giữ contract lỗi hiện có.
- Không khẳng định nguyên nhân router/OOM: muốn xác minh cần log máy AI; metrics
  tổng số `status=error` không tương đương số HTTP 502 hay tỷ lệ riêng benchmark.

### 4. Một retry dùng chung, không nhân tầng

- Mỗi request RAG dùng chung một retry transport 502/503; ModelOps độc lập có scope
  riêng. Không reset retry tại từng structured stage/key/fallback.
- Quota/auth/400/429 không retry. Tôn trọng Retry-After dạng số và deadline transport;
  header không giải nghĩa được/vượt budget thì bỏ retry, không chờ vô hạn.
- Không đổi payload để retry. Không retry JSON/schema/claim failure.
- Streaming chỉ retry HTTP rejection trước nội dung. Đã phát token thì giữ guard
  dừng; wrapper dùng `aclosing` để dọn stream/lease khi consumer đóng.
- Không thêm retry UI/runner, không hứa server AI hết 502 nhờ retry.

## Phạm vi file

- Mới: `configs/rag_inference_policy.json`,
  `backend/app/modules/modelops/services/inference_policy.py`,
  `backend/tests/test_rag_inference_safety_498.py`.
- Sửa đúng điểm nối: `rag/service.py`, `rag/evidence_model.py`,
  `modelops/services/inference_service.py`, `modelops/services/key_rotation.py`,
  `modelops/providers/chat_contract.py`, `modelops/providers/openai_adapter.py`.
- Test cập nhật: `test_evidence_claims.py` theo policy repair mới;
  `test_phase1_runtime.py` vẫn kiểm tra đúng route, thêm đúng một primary retry.
- Quy trình: `docs/quy_trinh/10_rag_inference_an_toan.md` và mục lục.

## Kiểm chứng đã chạy

CWD cho các lệnh Python/Ruff: `backend`. Dùng `.venv/Scripts/python.exe` trên Windows,
ngoài sandbox khi asyncio loopback bị hạn chế; fake adapters/MockTransport, không
live LLM. Test temp nằm trong `backend/storage/`, không xóa dữ liệu khác.

1. Regression mới trước sửa: **6 FAIL** (4 tính năng/module chưa có, 1 helper chưa có,
   1 tái hiện rõ repair 500→256). Không gọi đây là sáu lỗi runtime đã tái hiện.
2. Gate ban đầu: **108 PASS / 1 FAIL**; sửa thiếu token parameter trong nhánh kiểm tra
   context khi transport nhận payload tối giản ở test. Không nới guard.
3. Regression mở rộng sau sửa: **135 PASS**, Ruff scoped PASS.
4. Full đầu: **1793 PASS / 13 FAIL / 17 SKIP**, exit 1, khoảng 199 giây.
   Hai fail ngoài baseline là expectation cũ của
   `test_real_adapter_failover_only_calls_configured_chat_routes[False/True]`:
   hiện có thêm đúng một primary retry cho 503. Đã cập nhật expectation theo hành vi
   được yêu cầu, giữ nguyên kiểm tra không gọi embedding/default/unconfigured route.
5. Gate tập trung cuối: **148 PASS**, exit 0; Ruff scoped PASS. Các tình huống gồm
   policy thiếu/task isolation, chặn external fallback tại inference boundary,
   giữ nguyên payload/output, quote dài, context rejection không squeeze output,
   retry hữu hạn/Retry-After/cancellation và streaming trước/sau token.
6. Full xác nhận sau thay đổi: **1795 PASS / 11 FAIL / 17 SKIP**, exit 1, khoảng
   203 giây. Exact 11 failure IDs trùng `quality_492/verified-full.xml`, 0 chênh lệch.
   Tổng suite vẫn **FAIL**, không tuyên bố toàn bộ backend PASS. Artifact đầu:
   `backend/storage/safety498-final-full.xml`; artifact xác nhận:
   `backend/storage/safety498-final-verified.xml`. Không đưa log runtime/corpus vào Git.
7. UTF-8 không BOM/LF, JSON policy, liên kết snapshot/mục lục và diff đã kiểm tra.
   Chỉ chuẩn hóa newline ở hai file thuộc phạm vi vốn có CRLF; không đổi ký tự nguồn.

Exact IDs lỗi nền:

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

## Giới hạn và bước tiếp theo

- NOT RUN: live inference, UI, Docker build, benchmark 10/20/82 và log server AI.
- Chưa sửa model echo schema, verdict thiếu ID, 11 lỗi nền hoặc các nhóm ngoài batch
  trong báo cáo 493. Không tuyên bố độ chính xác 80% hoặc toàn RAG ổn định.
- Provider nội bộ vẫn có thể lỗi thật. Khi đưa mã vào vận hành, phải có cả file policy;
  không mở cloud khi gặp lỗi. Không tự restart/deploy trong task này.
- Đổi endpoint/model phía sau provider tin cậy cần quản trị rà lại nơi gửi dữ liệu.
- Không có tokenizer/window đáng tin thì không có bảo đảm token trước request; policy
  giữ nguyên hợp đồng và nhận lỗi provider, không giả vờ có phép đo.
