# Phiên 495 — Ba lỗi review: stream fallback, ngân sách repair, mã overflow cấu trúc

Ngày: 2026-10-16. Tiếp từ mã phiên 494, giữ nguyên mọi thay đổi chưa commit.
Không sửa retrieval/OCR/nguồn/vector/rule điểm/UI; không đè báo cáo 493/494.
Không gọi LLM, không benchmark 10/20/82.

## 1. Lỗi 1 — Nối fallback sau khi stream đã phát (inference_service.py)

Nguyên nhân: nhánh overflow trong `generate_stream` `break` thẳng sang route/provider
tiếp theo mà bỏ qua guard `yielded_any`, nên luồng gồm phần đầu của primary nối tiếp
đáp án fallback — đúng lỗi review chỉ ra.

Cách sửa: sau khi release lease (không ghi circuit, không chạm credential), nếu
`yielded_any` thì `raise` lỗi gốc như mọi lỗi mid-stream khác (giữ phần đã phát nguyên
vẹn, không phát thông báo lỗi như nội dung); chỉ `break` sang route khác khi chưa phát
token nào (đúng policy fallback hiện có). Rà soát mọi đường thoát: success →
complete_success; cancel → release + raise; lỗi thường → complete_failure rồi mới xét
raise; overflow → release đúng một lần rồi raise/break. Các nhánh loại trừ nhau.

## 2. Lỗi 3 — Mã overflow cấu trúc (key_rotation.py)

Nguyên nhân: chỉ xét `error.message`, bỏ sót HTTP 400 có `error.code =
context_length_exceeded` mà message chỉ ghi "Input is too long".

Cách sửa: `_structured_overflow_code` khớp chính xác trên trường chuyên dụng
`code`/`type` (tái dùng `_extract_response` cho wrapped exception), giữ nguyên hỗ trợ
message rõ ràng hiện có. Không dò chuỗi "context" chung chung. Cổng 400 giữ nguyên nên
auth/quota/rate-limit/502/payload sai cấu trúc/thông báo mơ hồ không bị phân loại sai.
Áp dụng chung cho generate và streaming (cùng hàm). Không log raw response/prompt/
credential/tài liệu (dùng `describe_provider_failure` sẵn có).

## 3. Lỗi 2 — Ngân sách repair (evidence_model.py)

Nguyên nhân: công thức cũ `min(base, len(text)//4 + 256)` bỏ qua Δ input (repair note)
và cửa sổ model; output lỗi dài thì ngân sách giữ nguyên trong khi prompt tăng.

Khảo sát cơ chế hiện có: ModelOps không expose cửa sổ/tokenizer tĩnh cho tầng này
(chỉ fit phản ứng `/tokenize` trong adapter — đã đo 404 ở server nội bộ phiên 494 —
và capability `minimum_output_tokens`/`token_parameter`); heuristic `chars//4` của
codebase KHÔNG bảo thủ cho tiếng Việt. Không hardcode 8192, không thêm lượt gọi LLM
(vẫn tối đa 2 attempt), không cắt bằng chứng.

Cách sửa — chính sách hai track (ước lượng, không bảo đảm, có trace log số liệu):
- Mọi track: `out_2 = base − Δ − reserve(256)`, Δ đo từ repair note thực tế bằng
  `chars//3` (hướng an toàn cho chữ có dấu). Attempt 0 đã vừa cửa sổ nên tổng repair
  nhỏ hơn tổng attempt 0 là vừa một cách chứng minh được — không coi "attempt đầu vừa"
  là bằng chứng repair không giới hạn cũng vừa.
- Track relaxed (input ước lượng ≤ 4000 tokens — một nửa cửa sổ NHỎ NHẤT ĐO ĐƯỢC ở
  deployment này (8192, live 2026-10-16), không phải claim cho mọi model):
  `out_2 = min(base, max(256, base−Δ−reserve))`, không bao giờ skip.
- Track strict (trên 4000): thiếu `out_2 ≥ 256` thì dừng bằng
  `EVIDENCE_MODEL_CONTRACT_INVALID` kèm `repair_skipped` (input/growth/budget/floor) —
  đúng bản chất, không cắt bằng chứng, không xin output không thể hoàn thành hợp đồng.
- Floor 256 là ngưỡng viability độc lập, không suy từ độ dài output sai.

Giới hạn còn lại (ghi rõ): không có cửa sổ/tokenizer đo được nên mọi con số là ước
lượng bảo thủ + số học envelope, không phải bảo đảm vừa; capability
`minimum_output_tokens` của adapter nằm ngoài tầm tầng này (ghi nhận, chưa nối);
track relaxed chấp nhận vượt envelope một lượng giới hạn cho input nhỏ theo lý do trên.

## 4. Kiểm tra thực chạy

- Ruff scoped: sạch (6 file app/test).
- Regression mới + lân cận: `test_inference_context_overflow.py` (5: overflow đơn,
  overflow+kẻ khác, skip lease, stream-sau-yield, stream-trước-yield),
  `test_evidence_claims.py` (budget theo Δ, skip strict, room strict, echo hint),
  `test_modelops_key_rotation.py` (code-only, wrapped, 9 negatives),
  `test_evidence_scope_452.py`, `test_modelops.py`, batch492/rows/enumeration/acts —
  PASS toàn bộ ở lượt trọng tâm (214).
- Full backend 1 lần trên mã chốt: **11 failed, 1779 passed, 17 skipped**; 11 failed
  đều thuộc baseline (consulting×2, publishing×6, truth×1, trust×1, tools×1).
  Giữa chừng full từng lộ 2 fail mới ở `test_evidence_scope_452` (repair nhỏ-budget là
  hành vi spec có sẵn) — đã sửa policy sang hai track, full cuối 0 lỗi mới. Tổng FAIL
  do lỗi nền (ghi FAIL theo quy định).
- NOT RUN: live LLM/benchmark (cấm theo phạm vi); 493§4.x ngoài batch giữ nguyên.

Artifacts: chỉ mã + test + 2 file docs này. Không nguồn/vector/config/model/preset;
không migration/restart/reindex/deploy/commit/push.
