# Phiên 500 — Đầu ra dữ liệu JSON và ID kiểm chứng

Ngày: 2026-10-16. Tiếp batch 499 theo yêu cầu người dùng.

## Phạm vi và phương pháp

Xử lý hai nhóm: model chép JSON Schema thay vì dữ liệu và verdict thiếu/trùng/sai
claim ID. Dùng hướng dẫn Clean Code, Backend, RAG và ModelOps: thay đổi cục bộ,
giữ kiểm chứng độc lập, provider động và fail-closed. Code trước, kiểm tra trọng tâm
sau batch; không chạy lại 82 câu hay mở rộng sang completeness/hội thoại.

Không sửa nguồn/OCR/vector/publication, DB, model/config, policy provider hoặc UI.
Không gọi model thật, migration/reindex/restart/deploy/commit/push.

## Luồng thật và nguyên nhân

`structured_call` phục vụ resolver/planner/proposal/verifier và audit. Model nhận
JSON Schema nguyên khối trong system message; có nhánh phát hiện echo ở lượt
repair nhưng lần đầu vẫn có nguyên mẫu schema để chép. Đây là điểm cần giảm
kích thích echo, không đủ để kết luận mọi lỗi phát sinh chỉ từ prompt.

`verify_bound_answer` trước đây dùng `VerificationResult` có `claim_id: str` và
verdicts có mặc định rỗng. Thiếu/trùng/ID lạ có thể qua validation JSON và chỉ bị
chặn sau `structured_call`, khi lượt sửa định dạng đã kết thúc. Indexed audit có
Literal cho ID nhưng chưa bắt tập đủ/duy nhất ngay trong contract.

## Thay đổi

1. Thêm `backend/app/modules/rag/evidence_contracts.py`:
   - Sinh hướng dẫn trường dữ liệu từ schema Pydantic, mô tả kiểu/required/optional,
     trường lồng nhau, enum, nullable, map, giới hạn và pattern. Không đặt nguyên
     JSON Schema `$defs`/`properties` vào prompt, không tạo ví dụ đáp án giả.
   - Pydantic vẫn là validator cuối; không bỏ kiểm tra strict/quote/provenance.
   - Contract verifier gắn Literal với ID của chính các claim đã qua scope, yêu
     cầu đủ số mục và mỗi ID đúng một lần. Không ánh xạ bằng vị trí, không tự điền
     verdict thiếu hay chọn một verdict trong các bản trùng.
2. `evidence_model.py`: dùng hướng dẫn trường dữ liệu, giữ tối đa hai attempt và
   nguyên payload/budget/ModelOps routing. Hướng dẫn sửa ID yêu cầu kiểm tra lại
   từng claim từ bằng chứng, không mặc định true. Log thêm loại lỗi validation,
   không ghi raw completion, quote hoặc prompt.
3. `evidence_verification.py`: dùng contract request-bound cho cả lần kiểm chứng
   đầu và lần kiểm chứng supersession hiện có. Sai ID được sửa trong hai attempt
   hiện có; hết lượt báo `EVIDENCE_VERIFICATION_INVALID` (502), không thành missing.
   Nhánh supersession không được thêm vòng lặp ngoài chính sách cũ.
4. `evidence_indexed_audit.py`: kiểm tra đủ/duy nhất claim IDs ngay trong contract,
   vẫn giữ Literal của passage/retained_by và các guard phía sau làm phòng vệ.
5. Test lịch sử `test_historical_reference_449.py`: mock nhận subclass của
   `VerificationResult` thay vì đồng nhất chính xác lớp gốc; giữ mọi assertion
   sai/đúng năm, claim và provenance hiện có.

Không thêm native structured-output capability hoặc ép `response_format` khi
provider chưa được xác nhận hỗ trợ. Đây là hướng dẫn đầu ra + validation phía app,
không phải constrained decoding của engine.

## Kiểm chứng đã chạy

Trong `backend`, dùng venv Python 3.12 hiện có:

```powershell
.\.venv\Scripts\ruff.exe check app/modules/rag/evidence_contracts.py app/modules/rag/evidence_model.py app/modules/rag/evidence_indexed_audit.py app/modules/rag/evidence_verification.py tests/test_evidence_contracts_500.py tests/test_historical_reference_449.py
.\.venv\Scripts\python.exe -m pytest tests/test_evidence_contracts_500.py tests/test_evidence_claims.py tests/test_evidence_completeness_437.py tests/test_evidence_quality_444.py tests/test_historical_reference_449.py tests/test_rag_inference_safety_498.py -q --tb=short -p no:cacheprovider --basetemp $focus500
.\.venv\Scripts\python.exe -m pytest -q --tb=short -p no:cacheprovider --basetemp $full500 --junitxml=storage/contracts500-full.xml
```

Basetemp là thư mục riêng có hậu tố UUID. Lần sandbox bị chờ asyncio đã dừng,
chạy lại với quyền công cụ phù hợp. Ruff scoped **PASS**. Focused **128 PASS**,
exit 0, 5,58 giây. Lần focused trước có một lỗi fixture kỳ vọng 2400 tokens trong
khi request đặt 2000; sửa assertion theo `min(contract_budget, request_budget)`,
không thay chính sách budget của app hoặc giảm guard.

Các ca mới kiểm tra:

- Hướng dẫn trường lồng nhau, enum/map/nullable và giới hạn; không có schema blob.
- Schema echo → một lượt sửa; lặp echo → lỗi, không có câu trả lời thiếu dữ liệu giả.
- Thiếu/trùng/ID lạ ở verifier và audit bị validation từ chối.
- Kiểm chứng thật qua `verify_bound_answer` và `structured_call` với fake ModelOps:
  sửa ID trùng, giữ payload/budget/routes, giữ nguyên provenance; verdict false
  vẫn bị loại, không bị gán sang claim khác khi model đổi thứ tự.
- Hai lần ID sai ở verifier hoặc audit → lỗi 502 đúng loại, không thêm attempt.
- Lỗi provider 503 truyền nguyên trạng, không dùng JSON repair che lỗi hạ tầng.

### Full backend

**1815 PASS / 11 FAIL / 17 SKIP**, 219,99 giây, exit 1: tổng suite vẫn **FAIL**.
16 ca mới đều PASS. So sánh classname + testcase với
`backend/storage/session-safety499-full.xml`: exact failure IDs trùng hoàn toàn,
không thêm/bớt ID lỗi. Artifact: `backend/storage/contracts500-full.xml`.

Các ID lỗi nền giữ nguyên (không sửa hoặc bỏ qua để làm xanh suite):

```text
tests.test_consulting_dispatcher::test_dispatch_admissions_with_export
tests.test_consulting_dispatcher::test_dispatch_regulations_with_export
tests.test_publishing_v2_cutover_and_gc::test_canary_policy_get_and_update_api
tests.test_publishing_v2_cutover_and_gc::test_gc_api_endpoint
tests.test_publishing_v2_decommissioning_and_system_gc::test_direct_upload_allowed_when_flag_enabled
tests.test_publishing_v2_decommissioning_and_system_gc::test_direct_upload_blocked_when_flag_disabled
tests.test_publishing_v2_decommissioning_and_system_gc::test_rest_api_system_wide_gc_and_decommissioning_audit
tests.test_publishing_v2_e2e_canary::test_api_routes_canary_and_rollback
tests.test_rag_data_truth_and_lifecycle::test_reconciliation_detects_discrepancies
tests.test_trust_boundary_and_hitl::test_auth_session_cookie_actor_claims
tests.test_universal_tools::test_dispatch_admissions_with_dynamic_facts
```

## Giới hạn và việc còn lại

- NOT RUN: live inference, benchmark 10/20/82, UI, Docker build và log server AI.
  Fake ModelOps chứng minh biên xử lý, không chứng minh model nội bộ đã hết echo
  hoặc chất lượng câu trả lời tăng. Không báo tỷ lệ accuracy/80%.
- Prompt dùng chung nhiều structured stage: cần kiểm tra model thật trên một bộ
  nhỏ trước khi kết luận hiệu quả. Không tự tăng context/output budget hoặc đổi model.
- Policy server chỉ cho `prov_rtx5090_vllm` vẫn giữ nguyên; không mở cloud khi lỗi.
- Các nhóm completeness/điều kiện trả lời, câu trả lời gọn và hội thoại của báo cáo
  493 còn ngoài batch. Báo cáo 493 được giữ nguyên làm mốc lịch sử.
