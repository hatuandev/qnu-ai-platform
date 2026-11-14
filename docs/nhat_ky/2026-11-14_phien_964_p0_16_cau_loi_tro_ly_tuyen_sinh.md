# Phiên 964 — 2026-11-14 — P0 sửa 16 câu lỗi trợ lý Tuyển sinh 2026 (theo kế hoạch 2026-11-14)

## Yêu cầu và phạm vi

- Người dùng duyệt **P0** của `docs/ke_hoach/2026-11-14_ke_hoach_sua_16_cau_loi_tro_ly_tuyen_sinh.md`: "ok bạn triển khai P0 trước đi". **P1** (gọi lại khi bỏ trắng) và **P2** (đo lại 100 câu + quyết định model) **chưa được duyệt**, không triển khai.
- Mục tiêu P0: (1) hết 502 cứng do guard bảng/xuất trích, (2) chunk hạng 6–10 vào ngữ cảnh tùy chọn, (3) dung sai lookup ô lỗi một phần, (4) lỗi có `errors` + trace tối thiểu để vận hành nhìn thấy. Không reindex, không migration, không sửa dữ liệu nguồn, không nới guard số.
- Môi trường đo: trợ lý `ast_47f30aaf2665`, kho `col_9209e90d1a53`, `top_k=5`, `candidate_k=40`, `hybrid_rerank`, scope explicit, `context_max_bytes=32000`, model `qwen3.8-27b-q4` (mặc định hệ thống). API :8002 chạy từ mã mới; worker/FE không đụng.

## File đã sửa

| File | Thay đổi | Dòng |
|---|---|---|
| `backendV1/qnu/domains/rag/answer/context.py` | P0.1: dải hạng 6–10 `RANK_BAND = 5`, chỉ chunk văn bản (bảng đã đến qua table_support), claim theo ngân sách tài liệu, trace `context.rank_band` / `added kind="rank"` / `rank_band_tables_skipped`; sửa `known.add` cho lân cận cửa sổ để không trùng `chunk_id` (409) | +64/−0 |
| `backendV1/qnu/domains/rag/answer/cells.py` | P0.2: `materialize` bỏ từng lookup trùng (`duplicate_ignored`) hoặc ngoài catalog (`not_in_catalog_ignored`), chỉ ném `answer_cell_invalid` khi không còn lookup hợp lệ; `report["rejected_lookups"]` | +26/−19 |
| `backendV1/qnu/domains/rag/answer/table_support.py` | P0.3: bỏ `room = 4`; header/liên tục của bảng được chọn ô luôn gắn kèm; phần phụ khác giữ hạn mức; `unresolved` giữ nguyên nghĩa | +5/−7 |
| `backendV1/qnu/api/handlers.py` | P0.4: problem RFC 7807 có `errors={"validation": ["<path>:<type>", ...]}` (tối đa 20) từ `AppException.validation_issues` | +12/−0 |
| `backendV1/qnu/domains/rag/answer/service.py` | P0.4: event `answer.validation_failed` mang `context_trace` (primary_ids, added, rank_band, table_support, selection, bytes/packing, materialization) + `grounding`; không text nguồn | +46/−1 |

Ghi chú: `drafting.py` (prompt v29) và `schemas.py` (`message`) đã có diff từ việc phiên trước (#267/#268), **không thuộc P0**, không chỉnh thêm trong phiên này. pytest **NOT RUN** theo yêu cầu người dùng.

## Phương pháp đo

- Runner `%TEMP%/qnu_p0_16x3.py` (ngoài Git): 16 câu lỗi × 3 lượt qua API hội thoại thật (`Idempotency-Key`, hội thoại mới mỗi lượt), lưu đầy đủ `result_trace`; tổng 48 lượt. Kết quả `%TEMP%/qnu_p0_16x3_results.json`.
- Token G4 đọc **`result_trace.prompt_tokens`** (token model trả lời), không dùng `prompt_tokens` cấp lượt (876–896 token của model viết lại câu hỏi — không đổi theo nội dung ngữ cảnh).
- Baseline: bộ 100 câu ngày 2026-11-14 (`%TEMP%/qnu_questions_100_results.json`) + token từ `model_usage_records` của 12 hội thoại lỗi (`%TEMP%/qnu_p0_baseline_tokens.txt`, đọc từ DB qua `docker exec`, chỉ đọc).

## Kết quả cổng (mã cuối)

| Cổng | Kết quả | Chi tiết |
|---|---|---|
| G1 — 502 cứng | **FAIL 5/48** | `answer_table_value_not_extractive` ×3 (Q24 lần 3, Q41 lần 1 và 3), `answer_cell_invalid` ×1 (Q38 lần 2), `answer_coverage_invalid` ×1 (Q19 lần 2); 0 `answer_evidence_changed`; 43/48 HTTP 200, 34/48 `answered`; mỗi câu trong 16 câu có ≥1 lượt trả lời |
| G4 — token | **PASS** | So cặp (34 lượt có baseline): trung vị **+3,1%**; toàn bộ trung vị 5457 vs baseline 5203 = +4,9%; p90 9316, max 11951 |
| Độ trễ | **PASS** | 16 câu baseline trung vị 11,1 s/p95 17,4 s → nay 8,5 s/p95 12,4 s (−23%/−29%) |
| G5 — mã | **PASS** | Ruff sạch 5 tệp đã sửa; import/khởi động API OK |
| G6 — quan sát | **PASS** | 5/5 lượt lỗi có `answer.validation_failed` với `context_trace` + `issues` trong DB; 4/5 phản hồi có `errors.validation` (ca `answer_coverage_invalid` không có issue pydantic — đúng thiết kế) |
| G2 — chấm nội dung | **NOT RUN** | Cần chấm tay 16×3 theo PDF gốc; chưa làm trong phiên này |
| G3 — 84 câu đúng | **NOT RUN** | Cần chạy lại 100 câu (chờ duyệt) |
| pytest | **NOT RUN** | Theo yêu cầu thường trực — không phải PASS |

Lượt trả lời theo câu (`answered/3`): Q5 3, Q6 2, Q12 1, Q16 2, Q19 2, Q21 3, Q24 1, Q28 3, Q29 2, Q38 2, Q41 1, Q53 3, Q74 1, Q78 3, Q85 2, Q88 3.

## Bài học giữa chừng (đã sửa trong phiên)

- Bản đầu của P0.1 lấy **cả chunk bảng** trong dải 6–10: đo 48 lượt cho G1 **12/48** 502 cứng và G4 **+23,7%** token — bảng nguyên khối phình envelope. Bản lưu `%TEMP%/qnu_p0_16x3_band5.json`.
- Sửa: dải hạng chỉ nhận chunk **văn bản** (`kind != "table"`); bảng đã đi đường `table_support` theo ô được chọn. Đo lại: G1 5/48, G4 +3,1%. Đúng tinh thần kế hoạch mục 10 ("giảm dải hoặc tắt bằng hằng số") nhưng ở dạng chọn lọc theo loại chunk, không theo từ khóa câu hỏi.
- Phát hiện và sửa lỗi 409 `answer_evidence_changed` do lân cận cửa sổ thêm trùng `chunk_id` vào dải hạng (thiếu `known.add`).

## Đối chiếu kỳ vọng kế hoạch

- P0.1 (Q74, Q78): Q78 **3/3 answered**; Q74 1/3 — chunk luật ở hạng 6–10 đã có cơ hội vào prompt nhưng 2 lượt vẫn bỏ trắng/không đủ. Chưa chấm nội dung.
- P0.2 (Q38): 2/3 answered; 1 lượt vẫn `answer_cell_invalid` (không còn lookup hợp lệ — guard đúng).
- P0.3 (Q16, Q21, Q41): Q16 2/3, Q21 3/3, Q41 1/3 (2 lượt vẫn `answer_table_value_not_extractive` — số không chứng minh được từ ô, guard trung thực).
- P0.4: quan sát đạt (G6).
- 8 câu bỏ trắng trước đây: Q12 1/3, Q19 2/3, Q24 1/3, Q53 3/3, Q74 1/3, Q85 2/3, Q88 3/3, Q78 3/3 — cải thiện rõ nhưng chưa đều; đúng dự đoán kế hoạch rằng phần bỏ trắng cần P1 (chưa duyệt).

## Lệnh thật đã chạy

- Ruff: `backendV1/.venv/Scripts/python.exe -m ruff check qnu/domains/rag/answer/context.py qnu/domains/rag/answer/cells.py qnu/domains/rag/answer/table_support.py qnu/api/handlers.py qnu/domains/rag/answer/service.py` → sạch.
- API: dừng PID :8002 cũ, chạy `backendV1/.venv/Scripts/uvicorn.exe qnu.main:app --app-dir backendV1 --host 127.0.0.1 --port 8002` (nền); `/health` OK.
- Đo: chạy runner 48 lượt; đọc DB chỉ đọc qua `docker exec -i qnu_postgres bash -lc 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Atc "..."'` cho event/token baseline.
- Không in/xu lộ secret, token, nội dung nguồn; mọi file đo nằm trong `%TEMP%`, ngoài Git. Không commit/push/deploy; không reindex/migration.

## Rủi ro còn lại và bước sau

1. **G2/G3 chưa chấm** — cần duyệt chạy lại 100 câu một lượt và chấm tay 16×3 theo PDF.
2. **P1 chưa duyệt** — 8 câu bỏ trắng dù có dữ kiện vẫn cần cơ chế gọi lại 1 lần; kế hoạch mục 5 sẵn sàng.
3. 5/48 lượt 502 là guard trung thực (số không chứng minh được / không còn ô hợp lệ), không phải lỗi hạ tầng; muốn giảm phải xử lý ở tầng chứng minh số (task #163) hoặc chất lượng model.
4. 4 câu chất lượng nội dung (Q5, Q6, Q28, Q29) thuộc chất lượng sinh; P2 sẽ quyết định model qua ModelOps nếu còn lỗi.
