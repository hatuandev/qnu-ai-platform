# Phiên 494 — Tiếp batch 5 luồng RAG (A–E) sau phiên 492

Ngày: 2026-10-16. Không đè báo cáo phiên 493; các mục ngoài batch (concurrency AsyncSession,
thống nhất quyết định đủ căn cứ, ngân sách lượt gọi/timeout toàn cục, conversation state,
nhãn Faithfulness UI) chỉ ghi nhận, xử lý sau theo thứ tự phiên 493 đã đề xuất.

## 1. Nguyên nhân thật (có bằng chứng trước khi sửa)

- **A/Q17**: tái hiện offline catalog có 6 bảng / 29 cells `rXcY` / 33 contexts `rXpY`,
  payload 8749 ký tự; ô đúng tồn tại (r0c5/r0c8/r1c5/r1c8 — điểm trúng tuyển 2024/2025
  SP Toán/CNTT). Auditor 2/3 lượt trả ID ngoài catalog, lượt còn lại REJECTED — cùng
  code/snapshot/model cho 3 kết quả khác nhau. Không gian ID trộn `r0c5` (cell) với
  `r0p0` (context) cùng tiền tố. Nhánh INVALID_CELLS không log ID vi phạm.
  Dòng "Dense search failed" ở Q17 thuộc stage candidate-collection khác; row path thuần
  FTS/cấu trúc nên không liên quan — không sửa retrieval vì đó.
- **B**: Q10/Q11-490 guard số làm đúng. Oan thật duy nhất: `validate_assertions` đòi
  `evidence_quote in proof` khớp tuyệt đối nên quote reflow (ngắt dòng) bị loại.
- **C**: closure/scope-audit/packing đúng thiết kế qua review mã; Q03/Q18 chờ live run.
- **D/Q15**: `row_identities` nhặt code "7520201TA" vào vị trí tên; render trộn 39 mục chung
  một bảng, câu mở đầu dễ đọc thành 39 ngành.
- **E**: Q05/Q08/Q18 = vLLM HTTP 502 giữa pipeline (sau 1–3 calls tốt) + fallback CF bị
  harness chặn 403; Q16-492 = ReadError. Q11-492 = repair attempt-2 tự tràn context
  (6593 in + 1600 out > 8192) rồi 400 bị coi như lỗi provider (ghi circuit, xoay fallback,
  báo ALL_UNAVAILABLE sai bản chất). Q03-492 mất dấu route vLLM ở mức INFO.
  Probe phiên này: vLLM khả dụng, nhưng `/tokenize` trả 404 — vòng `fit_rejected_context`
  ở adapter không bao giờ chạy được trên server này.

## 2. Thay đổi mã (không thêm lượt model, framework, DAG; giữ guard)

- `backend/app/modules/rag/row_answer.py`: SELECT/AUDIT thêm quy tắc hình dạng ID
  (cell `r{row}c{column}` chỉ trong catalog lượt hiện tại; context `r{row}p{position}`
  không bao giờ là cell). Nhánh INVALID_CELLS ghi diagnostics: `invalid_cell_ids`,
  `invalid_id_kinds` (`context_shaped`/`non_cell_id` theo hình dạng, không suy đoán nguồn),
  `cell_count`/`context_count`/`table_count`. Server-side check giữ nguyên bắt buộc.
- `backend/app/modules/rag/response_audit.py`: `quote_supported` — khớp tuyệt đối trước,
  rồi containment sau chuẩn hóa whitespace cùng quy tắc hai phía; giữ nguyên chữ/số/dấu,
  không fuzzy/sửa OCR/bỏ dấu; citation và provenance vẫn dùng quote gốc; giữ nguyên
  kiểm chứng số và bao phủ khẳng định.
- `backend/app/modules/rag/combination_enumeration.py`: `render_records` tách bảng chính
  (ngành đã xác minh mã+tên) và mục "Cần đối chiếu thêm" (thiếu mã hoặc tên trùng mã,
  giữ nguyên cách ghi + nguồn từng mục). Câu mở đầu đếm 3 con số có định nghĩa:
  bản ghi nguồn / cách ghi mã+tên phân biệt / ngành đã xác minh. Quyết định partial
  và trace `records` giữ nguyên.
- `backend/app/modules/modelops/services/key_rotation.py`:   `is_context_overflow_error`
  — chỉ HTTP 400 kèm bằng chứng cửa sổ rõ ràng (`maximum context length`, ...),
  còn lại vẫn là lỗi provider thường.
- `backend/app/modules/modelops/services/inference_service.py` (`generate` +
  `generate_stream`): overflow thì fail-fast, không ghi circuit, release lease, break vòng
  key (cùng prompt không thể thành công ở key khác), vẫn cho fallback route khác thử;
  hết routes mà chỉ có overflow → `MODEL_CONTEXT_EXCEEDED` (502), thay vì
  `ALL_PROVIDERS_UNAVAILABLE`. Skip route nâng lên WARNING với reason
  (`circuit_breaker_open` / `key_lease_unavailable` / `no_credentials_configured` /
  `no_available_credentials`) + số key trong pool, không lộ credential/nội dung.
- `backend/app/modules/rag/evidence_model.py`: repair attempt-2 chỉ xin
  `min(budget_gốc, completion_thực_tế_attempt1 + 256)` output — vì attempt-1 đã chứng minh
  vừa cửa sổ, repair nhỏ hơn chắc chắn vừa hơn; bằng chứng không bao giờ bị cắt.
  Thêm câu chỉ đích danh schema-echo (`"properties"`/`"$defs"`) khi phát hiện.
  ModelOps không expose giới hạn context/to simple estimator nào ngoài cơ chế
  `/tokenize` phản ứng (đã chết 404 ở server này) — ước lượng bảo thủ dùng heuristic
  `chars//4` sẵn có của codebase cho quota, và lấy envelope attempt-1 đã vừa làm chuẩn.

## 3. Kiểm chứng

- Ruff scoped sạch trên mọi file sửa + test mới.
- Regression trọng tâm: 237 passed (A2/B/D1/E1/E2 + lân cận), gồm negative cases
  (ID lạ hình context/malformed, reflow, overflow 400/502/bọc ngoài, repair cap,
  tách mục review).
- Full backend 1 lần trên mã chốt: **11 failed, 1764 passed, 17 skipped**; 11 failed đều
  thuộc tập baseline (consulting×2, publishing×6, truth×1, trust×1, tools×1). 0 regression.
- Probe tối thiểu (không corpus): vLLM qwen3.5-9b OK, không fallback; `/tokenize` 404.
- Bộ10 cố định (`run_quality.py` phiên 492, output `storage/quality_494`, Q15→Q16 giữ chuỗi,
  fingerprint config/metadata/snapshot/sources/rag_code unchanged trong lượt):
  6 completed (Q03/Q10 đúng; Q15/Q17 partial; Q16/Q19 đúng), 4 lỗi hạ tầng
  (Q05/Q08/Q11/Q18: calls tốt rồi vLLM 502 + fallback bị chặn — dừng live test, NOT VERIFIED).
  - Q03 lần đầu trả đúng quan hệ cập nhật: 5.173 (TB 1906/31-05-2026) thay 4.500
    (TB 263/12-02-2026) + phân biệt 53/56, có citation.
  - Q17 lần đầu đi đường partial thiết kế: 6 ô đồng thuận + nêu rõ 2 cột chưa chốt,
    diagnostics đủ ID/counts, không còn INVALID_CELLS ở lượt này (biến động còn: 4 lượt
    REJECTED/INVALID/INVALID/PARTIAL — guard giữ mọi lần).
  - Q16 lần đầu thấy happy path: giải thích số lượng theo lượt trước, không đổ lại bảng.
  - Q11 vẫn lỗi nhưng đổi mode: 4 calls tốt (gồm call 5189 tokens — repair đã vừa),
    chết ở 502 sau đó, không còn vòng repair tràn context.

## 4. Còn lại / chưa kiểm chứng

- Q05/Q08/Q11/Q18: NOT VERIFIED (hạ tầng lặp lại 4 lượt; không retry săn kết quả đẹp).
- Q03/Q18 kiểm chứng đoạn cập nhật: Q03 đã thấy đúng 1 lượt; Q18 chưa có lượt nào (hạ tầng).
- Q17 còn biến động giữa các lượt model — cần thêm mẫu nhưng chỉ khi provider ổn định.
- Ngoài batch (theo phiên 493): concurrency session, thống nhất đủ/thiếu căn cứ, ngân sách
  lượt gọi/timeout, conversation state, nhãn Faithfulness UI.
- Không đổi nguồn/vector/config DB/model/preset; không migration/reindex/restart/deploy/
  commit/push. `WORK_LOG.md`, `PROJECT_CONTEXT.md`, index `nhat_ky/README.md` không chạm do
  mojibake có sẵn (tiền lệ phiên 484); mục lục nhật ký bổ sung sau khi sửa encoding.

Artifacts riêng tư: `backend/storage/quality_494/` (results.json, source_snapshot.json).
Không đưa corpus/log runtime vào Git. Không gửi tài liệu ra provider ngoài.
