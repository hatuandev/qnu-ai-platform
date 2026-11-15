# Kế hoạch sửa 16 câu lỗi của trợ lý Tuyển sinh 2026 (P0–P2)

- Ngày lập: 2026-11-14
- Trạng thái: **P0 ĐÃ TRIỂN KHAI (phiên 964); P1 ĐÃ TRIỂN KHAI (phiên 965); P1.1 ĐÃ TRIỂN KHAI (phiên 966); G3 ĐÃ CHẠY (phiên 967) — FAIL cổng: 7/84 câu đúng cũ lệch đã xác định, nguyên nhân là guard sinh câu trả lời ngẫu nhiên theo lượt (có sẵn từ baseline) + 1 ca định tuyến, không phải upload/OCR/chunk/retrieval/packing** — P2 chưa duyệt. Kiểm chứng độc lập phiên 970 trên mã v35 (API tạm 8017, 16 câu / 1 lượt): **15/16 câu trả lời đúng nội dung**, 7 ca lệch cổng cũ đều đạt; **Q41 còn lỗi chập chờn (1/4 lượt 200)**; full 100 câu, pytest **NOT RUN**. Kết quả P0: G1 5/48 502 (FAIL, toàn guard trung thực), G4 +3,1% token (PASS), độ trễ −23%/−29% (PASS), G5/G6 PASS, G2/G3 NOT RUN. Kết quả P1: abstain 6→0, appeal 4/4 answered nhưng G2 3/8 đúng trọn (FAIL), 0 số bịa, 502 4/24. Kết quả P1.1: Q74 có hàng quyết định trong envelope cả 3/3 lượt và 2/3 trả lời đúng; answered 20→22, 502 4→1, appeal 3 (2 answered đúng, 1 invalid giữ abstain), 0 `skipped_structure`, G2 vẫn FAIL 3/8 (Q12/Q85/Q88), 0 số bịa, token +0,15%, độ trễ −6%. Kết quả G3: answered 89/100, 2 insufficient (Q53, Q99), 9 lỗi (Q2 409 clarify; Q26/Q28/Q33/Q40/Q41/Q44/Q45/Q73 guard 502); +6 câu cũ PASS trọn (Q12/Q19/Q21/Q38/Q85/Q88) và Q5 đủ 3 website; độ trễ trung vị 10,2 s (baseline 10,9 s); chấm lại nội dung đầy đủ 77 câu còn lại NOT RUN. Chi tiết mục 13–16 và nhật ký phiên 964–967.
- Phạm vi chạy: `backendV1/` (API :8002) + cấu hình trợ lý `ast_47f30aaf2665`, kho `col_9209e90d1a53`
- Tài liệu liên quan: `docs/ke_hoach/`, `docs/memory/PROJECT_CONTEXT.md`, báo cáo 100 câu ngày 2026-11-14

## 1. Mục tiêu

Đưa bộ 100 câu kiểm thử tuyển sinh từ **84 đúng / 2 tạm đạt / 2 sai / 8 thiếu căn cứ / 4 lỗi 502 cứng** lên mức chấp nhận được cho demo:

1. Không còn lỗi 502 cứng nào trong bộ 100 câu (3 lần chạy lặp).
2. Phần lớn 8 câu "thiếu căn cứ" (dù dữ kiện đã nằm trong tài liệu gửi cho model) được trả lời đúng, không bịa số.
3. Không làm hỏng 84 câu đang đúng; chi phí token và độ trễ không tăng quá mức đã định.

Nói bằng hình ảnh: model là thí sinh được phát đề + tập tài liệu photo. Ba lỗi đang xảy ra là (a) không được phát đủ trang liên quan, (b) bị giám thị thu bài vì ghi số trong ô bảng không đúng biểu mẫu, (c) bỏ trắng bài dù tài liệu có đáp án. Kế hoạch sửa đúng ba lỗi đó, không hạ thấp tiêu chuẩn chống bịa số.

## 2. Bằng chứng chẩn đoán (đã xác minh, không phải phỏng đoán)

| Nhóm lỗi | Câu | Nguyên nhân gốc đã truy vết |
|---|---|---|
| 502 cứng | Q16, Q21, Q41 | Chunk chứa dữ kiện không có header bảng được gắn kèm → bảng thành "không chọn ô được" → mọi câu chứa số bị loại → guard ném `answer_table_value_not_extractive`. Gốc: `table_support.py` giới hạn `room = 4` cho **cả** header bắt buộc lẫn phần phụ, nên header bị đẩy sang `unresolved_support_ids`. |
| 502 cứng | Q38 | Model chọn `cell_id` trùng/không có trong catalog → guard ném `answer_cell_invalid` và hủy cả câu trả lời, dù phần lớn nội dung đúng. |
| Bỏ trắng dù có dữ kiện | Q12, Q19, Q53, Q85, Q88 (và một phần Q24) | Dữ kiện nằm trong envelope gửi model (ord 46/56/88/98/71, bảng 165…) nhưng model trả `insufficient_evidence`, 0 statement. Prompt v29 đã yêu cầu trả lời phần có căn cứ; model 27B cục bộ không tuân thủ ổn định. |
| Thiếu ngữ cảnh do top_k=5 | Q74, Q78 | Chunk chính sách nằm ở hạng rerank 6 và 8; chỉ top-5 vào prompt nên không có căn cứ. |
| Chất lượng nội dung | Q5, Q29 (tạm đạt), Q6, Q28 (sai) | Model chọn đúng chủ đề nhưng bỏ ý/trả lời chung thay vì dòng bảng cụ thể. Thuộc chất lượng sinh, không phải pipeline. |

Các khâu upload → OCR → bóc tách → chunk → index đã được loại trừ: mọi dữ kiện cần thiết đều tồn tại nguyên văn trong `kb_index_chunks` và đã từng lọt vào prompt.

## 3. Nguyên tắc bất di bất dịch khi sửa

- Không reindex, không migration, không xóa/sửa dữ liệu nguồn.
- Không nới guard theo kiểu "chấp nhận mọi con số": số trong bảng vẫn chỉ được lấy qua ô đã đối chiếu.
- Không vá prompt bằng từ khóa của câu test; mọi sửa ở cấu trúc/trace hoặc quy tắc tổng quát.
- Không thêm dependency; giữ UTF-8 không BOM, LF.
- Không đụng file người dùng đang sửa: `chunking.py`, `hybrid.py` (diff người dùng), `table_layout.py`, và các test `test_answers_api_648.py`, `test_hybrid_655.py`, `test_answer_contract_788.py`, `test_hybrid_fusion_938.py`, `test_unselectable_prose_941.py`.
- Không chạy pytest trừ khi được yêu cầu riêng (ghi nhận NOT RUN, không coi là PASS).
- Không in/ghi log secret, PII, nội dung nguồn, Base64 OCR.

## 4. P0 — Sửa tất định trong mã (không cần duyệt dữ liệu)

### P0.1 — Dải hạng 6–10 làm ngữ cảnh tùy chọn (mục tiêu Q74, Q78)

- **Vì sao:** `search.py` cắt `hits[:top_k]` sau rerank (dòng 489/491) nhưng `trace["rerank_ranked_ids"]` vẫn giữ đủ thứ hạng (hybrid.py:222). Chunk chính sách của Q74 ở hạng 6, Q78 ở hạng 8 — đã tìm thấy nhưng bị cắt.
- **Sửa ở đâu:**
  - `qnu/domains/rag/answer/context.py` — trong `expand_context`, sau khi có `result.trace["rerank_ranked_ids"]`, lấy thêm tối đa 5 id kế tiếp (vị trí `top_k…top_k+5`, không vượt `candidate_k`), nạp chunk theo đúng run + `allowed` (dùng lại cách dựng `VectorHit` như `_neighbor_hit`/`_hits`), gắn `kind: "rank"` vào `trace["added"]` với `primary_chunk_id` = mục gần nhất trong top-k để xếp hạng cắt.
  - Không đổi `top_k` của retrieval; primaries vẫn 5, phần thêm là **optional**.
- **Hành vi sau sửa:** `pack_messages` (`packing.py:14-70`) tự cắt các item `kind="rank"` khi envelope vượt `context_max_bytes` theo thứ hạng neo. Không tiêu ngân sách của evidence bắt buộc.
- **Trace mới:** `context.rank_band = {ids, skipped}` (chỉ id/số lượng).
- **Rủi ro:** tăng nhẹ prompt token khi ngân sách còn trống. Có thể khử bằng ngân sách byte sẵn có, không cần cấu hình mới.
- **Kiểm nhanh trước khi sửa mã (tùy chọn, cần duyệt):** nâng `top_k` trợ lý 5 → 8 qua UI/API, chạy lại Q74/Q78. Nếu đúng cả hai thì giả thuyết được xác nhận; sau đó vẫn làm P0.1 vì cách này không kéo 8 chunk cứng vào mọi câu.

### P0.2 — Dung sai `cell_id` khi model trả lookup lỗi một phần (mục tiêu Q38)

- **Vì sao:** một `cell_id` trùng hoặc không thuộc catalog đang hủy toàn bộ câu trả lời (`cells.py:684-704`), dù các lookup còn lại hợp lệ.
- **Sửa ở đâu:** `qnu/domains/rag/answer/cells.py`, hàm `materialize`:
  - `cell_id` trùng → giữ lần xuất hiện đầu, ghi report `duplicate_ignored`.
  - `cell_id` không thuộc catalog → loại khỏi danh sách, ghi report `not_in_catalog_ignored`.
  - Chỉ ném `answer_cell_invalid` khi **không còn lookup hợp lệ nào** và vẫn còn số không chứng minh được (hoặc theo đúng điều kiện guard hiện có).
  - Các guard khác giữ nguyên: `answer_cell_selection_required` (có số bảng nhưng không chọn ô), `answer_table_value_not_extractive` (không chứng minh được số), `source_cell_not_displayable`, giới hạn statement.
- **Bất biến được giữ:** mọi số trong bảng vẫn phải đi qua ô hợp lệ; phần bị loại được ghi vào `trace.context.materialization` và hiển thị trong báo cáo/assessment, không im lặng.
- **Phối hợp:** task #163 (nhóm 502 extractive-guard) đang xử lý nhánh chứng minh số/header khác (Q07/Q09/Q08 của bộ 30 câu). Kế hoạch này **không mở lại** các phase #164–#167; chỉ chỉnh chính sách lookup trong `materialize`.

### P0.3 — Header bảng là phụ thuộc bắt buộc, không tranh suất với phần phụ (mục tiêu Q16, Q21, Q41)

- **Vì sao:** `table_support.attach_table_support` dùng `room = 4` (dòng 174) cho **mọi** phần thêm. Khi một câu cần nhiều mảnh bảng (catalog ngành tách 8 mảnh, mục 11 tách 8 mảnh), header bị đẩy sang `unresolved_support_ids`; bảng mất header → thành `unselectable` trong catalog → mọi statement chứa số bị loại → 502.
- **Sửa ở đâu:** `qnu/domains/rag/answer/table_support.py`:
  - Tách hai loại phần thêm: (a) **phụ thuộc header/liên tục** của bảng được chọn ô — luôn gắn, kể cả vượt `room`, vì đây là điều kiện để số được phép trích; (b) phần phụ khác — giữ hạn mức hiện có.
  - Header thật sự thiếu hoặc sai scope vẫn `unresolved` (trung thực), bảng vẫn `unselectable`; guard không bị nới.
  - Ghi trace rõ: `table_support` = resolved/partial, id header đã gắn.
- **Rủi ro:** số chunk thêm tăng ở câu liệt kê bảng lớn; đã có ngân sách byte và packing cắt optional, nên không vượt envelope.

### P0.4 — Nhìn thấy được lỗi (không sửa hành vi trả lời)

- **Vì sao:** khi 502, phản hồi RFC 7807 có `errors: null` (`handlers.py:61-73` không đưa `validation_issues` ra), và lượt lỗi không lưu trace → không thể phân biệt lỗi model với lỗi guard khi vận hành.
- **Sửa ở đâu:**
  - `qnu/api/handlers.py` — nếu `exc` có `validation_issues`, đưa vào `ProblemDetail.errors` dưới dạng `{"validation": ["<path>:<type>", ...]}` (chỉ path/type, không text nguồn, không PII).
  - `qnu/domains/rag/answer/service.py` — trong nhánh `except AppException` hiện có (dòng 364-388), bổ sung snapshot trace tối thiểu vào workspace event (id chunk, số lượng, sha, thứ hạng; không text nguồn).
- **Không đổi:** mã lỗi, HTTP status, hành vi nghiệp vụ.

## 5. P1 — "Gọi lại" một lần khi model bỏ trắng dù có dữ kiện (mục tiêu Q12, Q19, Q53, Q85, Q88, Q24) — cần duyệt riêng

- **Điều kiện kích hoạt (hẹp):** chỉ khi `status = insufficient_evidence` sau `materialize` + `assess`, và lượt gọi đầu không lỗi provider/quota/hạ tầng (đúng bất biến 5: lỗi quota/hạ tầng không retry).
- **Cách làm:** một lần gọi thứ hai, tối đa 1, dùng đúng envelope + catalog đã pack (không đổi evidence), thêm chỉ dẫn yêu cầu đánh giá lại từng ý và trả lời phần có căn cứ. Không nới schema, không thả lỏng kiểm chứng số.
- **Sửa ở đâu:** `qnu/domains/rag/answer/service.py` (điều phối lần gọi 2, settle usage, trace `appeal = {attempted, outcome}`), `qnu/domains/rag/answer/drafting.py` (hàm dựng message bổ sung; giữ `PROMPT_VERSION` cho lần gọi đầu, không sửa v29 nếu không cần).
- **Chi phí:** chỉ câu bỏ trắng chịu thêm 1 lượt; trong bộ 100 câu là 8/100 lượt. Token/latency của câu trả lời bình thường không đổi.
- **Nếu vẫn bỏ trắng:** chấp nhận kết quả insufficient (trung thực), không lặp vô hạn.

## 6. P2 — Đo lại toàn bộ và quyết định model (không sửa mã pipeline)

- Chạy lại 16 câu lỗi × 3 lần trên bản mã P0 (+P1 nếu được duyệt) → chấm tay theo PDF gốc.
- Chạy lại 100 câu một lượt, so baseline 84/2/2/8/4.
- Nếu còn lỗi chất lượng nội dung (Q5, Q6, Q28, Q29) sau P0+P1: trình phương án chọn model trả lời mạnh hơn **qua ModelOps của UI** để người dùng quyết định; không vá prompt theo câu test.

## 7. Phạm vi file dự kiến

| File | Thay đổi | Mức |
|---|---|---|
| `backendV1/qnu/domains/rag/answer/context.py` | dải hạng 6–10 optional + trace | ~40 dòng |
| `backendV1/qnu/domains/rag/answer/cells.py` | dung sai lookup trong `materialize` | ~20 dòng |
| `backendV1/qnu/domains/rag/answer/table_support.py` | header bắt buộc tách khỏi `room` | ~25 dòng |
| `backendV1/qnu/api/handlers.py` | đưa `validation_issues` vào problem | ~8 dòng |
| `backendV1/qnu/domains/rag/answer/service.py` | trace lỗi tối thiểu; P1 appeal (nếu duyệt) | ~15 / ~50 dòng |
| `backendV1/qnu/domains/rag/answer/drafting.py` | message appeal (chỉ P1) | ~15 dòng |

Không file nào cần migration; mọi trace là JSON sẵn có.

## 8. Runbook thực hiện (đánh số, từng bước có cổng duyệt)

1. **[Cần duyệt]** Chốt kế hoạch này (anh xem và trả lời "duyệt P0" / "duyệt P0+P1").
2. Chụp baseline: xác nhận Git sạch phần liên quan, lưu kết quả 100 câu hiện có làm mốc so sánh.
3. **[Cần duyệt — tùy chọn, 5 phút]** Thử nhanh giả thuyết Q74/Q78: nâng `top_k` trợ lý 5 → 8 qua UI/API, chạy 2 câu, rồi trả cấu hình về 5. Ghi kết quả vào nhật ký.
4. Triển khai P0.1 → P0.4 theo thứ tự trên; sau mỗi việc chạy Ruff riêng file vừa sửa:
   `uv run ruff check qnu/domains/rag/answer/context.py qnu/domains/rag/answer/cells.py qnu/domains/rag/answer/table_support.py qnu/api/handlers.py qnu/domains/rag/answer/service.py`
5. Khởi động lại API nền (:8002) để nạp mã mới (dừng PID đang chạy rồi chạy lại đúng lệnh dev hiện hành; không đụng worker, không đụng FE).
6. Chạy 16 câu lỗi × 3 lần qua API chat thật (token đọc từ file tạm, không in giá trị). Ghi từng lượt: status, số statement/lookup, guard code nếu có, trace id.
7. Chấm tay 16 × 3 theo PDF gốc; đối chiếu từng con số với ô/mảnh bảng được dẫn.
8. **[Cổng duyệt — nếu chọn P0+P1]** Triển khai P1, Ruff, restart API, chạy lại nhóm 8 câu bỏ trắng × 3.
9. Chạy lại 100 câu một lượt trên cùng cấu hình; lưu báo cáo so sánh baseline (đúng/tạm đạt/sai/thiếu/502, token p50–p95, latency p95).
10. Chấm và viết báo cáo PASS/FAIL theo mục 9; cập nhật nhật ký/snapshot/PROJECT_CONTEXT theo workflow.
11. **[Chỉ khi cần]** Trình phương án đổi model qua ModelOps cho 4 câu chất lượng nội dung; không tự đổi.

## 9. Tiêu chí nghiệm thu (PASS/FAIL/NOT RUN)

| Cổng | PASS | Ghi chú |
|---|---|---|
| G1 — 502 cứng | 0 lượt `answer_cell_invalid` / `answer_table_value_not_extractive` trong 16 câu × 3 lần | Lỗi hạ tầng/provider khác báo riêng, không tính là PASS |
| G2 — Câu bỏ trắng (sau P1) | ≥ 7/8 câu trước đây bỏ trắng trả lời đúng dữ kiện, **0 số bịa** | Chấm tay theo PDF; token-level đạt chưa đủ để coi là đúng nội dung |
| G3 — Không hồi quy | 84 câu đúng cũ giữ nguyên đúng (cho phép tối đa 1 ca lệch có giải trình) | Chạy lại 100 câu |
| G4 — Chi phí | Prompt token trung vị tăng ≤ 20%; latency p95 tăng ≤ 15% | Đo trên cùng model/provider |
| G5 — Mã | Ruff sạch trên đúng các file đã sửa; import smoke API OK | pytest: **NOT RUN** (theo yêu cầu) — không phải PASS |
| G6 — Quan sát | Lượt lỗi có `errors.validation` trong phản hồi và event lưu trace tối thiểu | Kiểm bằng 1 ca lỗi cố ý |

## 10. Rủi ro và cách lùi

| Rủi ro | Xác suất | Cách xử lý |
|---|---|---|
| Thêm chunk hạng 6–10 làm model xao nhãng, câu cũ sai đi | Thấp–vừa | Packing đã cắt optional theo thứ hạng; nếu G3 vỡ, giảm dải còn 3 hoặc tắt bằng hằng số trong một dòng |
| P0.2 che lỗi model chọn sai ô | Thấp | Chỉ bỏ lookup lỗi khi còn lookup hợp lệ; phần bỏ ghi report; guard số giữ nguyên |
| Gắn header vượt `room` làm phình prompt | Thấp | Phụ thuộc thật của header có trần tự nhiên (header + previous mỗi bảng); byte budget chặn cuối |
| P1 làm tăng chi phí/thời gian ở câu bỏ trắng | Vừa | Chỉ 1 lần gọi thêm, chỉ khi insufficient; theo dõi ở G4 |
| Rollback | — | `git diff` chỉ 5–6 file; revert + restart API. Không có thay đổi dữ liệu/DB nên không cần khôi phục kho |

## 11. Ước lượng và thứ tự

- P0: khoảng 1 ngày làm việc gồm sửa, Ruff, restart và đo 16×3.
- P1: khoảng nửa ngày nếu được duyệt, gồm đo nhóm 8 câu.
- P2: 2–3 giờ chạy 100 câu, chấm và viết báo cáo.
- Thứ tự bắt buộc: P0 → đo → (P1 nếu duyệt) → đo → P2.

## 12. Điểm cần anh chốt trước khi tôi bắt đầu

1. Duyệt **P0** hay **P0 + P1** (P1 tốn thêm 1 lượt gọi cho câu bỏ trắng).
2. Có làm bước thử nhanh `top_k = 8` (mục 3) trước khi sửa mã không?
3. Sau khi xong, có muốn tôi chạy lại **toàn bộ 100 câu** hay chỉ nhóm lỗi + 20 câu đúng đại diện?

## 13. Kết quả triển khai P0 (2026-11-14, phiên 964)

- **Phạm vi đã sửa (5 tệp):** `context.py` (dải hạng 6–10 optional, chỉ chunk văn bản), `cells.py` (dung sai lookup trong `materialize`), `table_support.py` (header bắt buộc tách khỏi hạn mức), `handlers.py` (`errors.validation`), `service.py` (trace lỗi tối thiểu). Không reindex/migration; `drafting.py`/`schemas.py` giữ diff cũ (prompt v29/message), không thuộc P0.
- **Đo:** 16 câu lỗi × 3 lượt = 48 lượt qua API thật, model `qwen3.8-27b-q4`, cùng cấu hình trợ lý. Kết quả `%TEMP%/qnu_p0_16x3_results.json` (ngoài Git).
- **Cổng:** G1 **FAIL 5/48** (`answer_table_value_not_extractive` ×3: Q24, Q41×2; `answer_cell_invalid` ×1: Q38; `answer_coverage_invalid` ×1: Q19) — đều là guard trung thực, 0 `answer_evidence_changed`; 43/48 HTTP 200, 34/48 answered, mỗi câu có ≥1 lượt trả lời. G4 **PASS** (+3,1% trung vị so cặp n=34; toàn bộ +4,9%). Độ trễ **PASS** (trung vị 8,5 s vs 11,1 s; p95 12,4 s vs 17,4 s). G5 **PASS** (Ruff + import smoke). G6 **PASS** (5/5 event có trace/issues; 4/5 phản hồi có `errors.validation`). G2/G3 **NOT RUN**; pytest **NOT RUN**.
- **Điều chỉnh so với mục 4.1:** dải hạng chỉ nhận chunk `kind="table"` bị loại — bản lấy cả bảng gây 12/48 502 và +23,7% token (lưu `%TEMP%/qnu_p0_16x3_band5.json`); bảng vẫn đến qua `table_support` theo ô được chọn.
- **Việc tiếp theo:** chấm tay G2 (16×3 theo PDF), chạy lại 100 câu cho G3 (cần duyệt), và quyết định P1 (gọi lại khi bỏ trắng, mục 5) — chưa triển khai.

## 14. Kết quả triển khai P1 (2026-11-14, phiên 965)

- **Phạm vi đã sửa (3 tệp):** `drafting.py` (`APPEAL_VERSION`, `APPEAL_INSTRUCTION`, `appeal_messages()`), `schemas.py` (`AnswerTrace.appeal`), `service.py` (khối appeal 406–507: chỉ khi `insufficient_evidence`, usage/idempotency riêng, chỉ thay kết quả khi appeal `answered`, mọi lỗi giữ abstain lần 1, cache key có `appeal_version`). Không đổi mã P0; không reindex/migration.
- **Đo:** 8 câu bỏ trắng (Q12, Q19, Q24, Q53, Q74, Q78, Q85, Q88) × 3 = 24 lượt qua API thật, cùng cấu hình P0. Kết quả `%TEMP%/qnu_p1_8x3_results.json` (ngoài Git); envelope bằng chứng giống hệt nhau giữa 3 lượt từng câu.
- **Cổng:** mục tiêu hẹp P1 **PASS** — abstain 6→0, appeal 4/4 → `answered`, 0 `still_insufficient`. **G2 FAIL** — 3/8 đúng trọn (Q12, Q19, Q88), Q78 partial 3/3, Q53 1/3, Q85 1/3, Q74 0/3, Q24 0/3; 0 số bịa nhưng 3/4 kết quả appeal tự tin sai. 502 4/24 toàn model-output/guard thiết kế (0 `evidence_changed`, 0 lỗi provider). Token trả lời từng câu trùng khít P0; appeal thêm 20.612 token trên 4/24 lượt (≈ +26% nhóm này); độ trễ trung vị 8,0→9,1 s. G5/G6 PASS; G3/pytest NOT RUN.
- **Finding mới:** Q74 — PHỤ LỤC 1 tách 3 block, hàng "Tiếng Trung | Ngôn ngữ Trung Quốc | 7220204" (ord 181, trang 14, `ev_p014_b003`) không được pack do đứt liên kết bảng qua trang; đề xuất P1.1 (nối tiếp bảng qua trang ở tầng trả lời, không reindex) — chưa duyệt.
- **Việc tiếp theo:** duyệt G3 (chạy lại 100 câu); quyết định P1.1 và hướng siết điều kiện appeal; P2 quyết định model qua ModelOps.

## 15. Kết quả triển khai P1.1 (2026-11-14, phiên 966)

- **Bối cảnh:** sau P1, người dùng chọn phương án 2 — nối bảng phụ lục qua trang cho Q74 (P1.1a) + siết điều kiện gọi lại (P1.1b). P2 và G3 chưa duyệt.
- **Phạm vi đã sửa (3 tệp):**
  - `table_context.py`: `PAGE_BAND_BASIS = "native_page_band_continuation/v1"`; `page_continuations(document, proven)` chỉ nhận cặp trang liền kề khi bảng trái là bảng native đã parse, chạm đáy trang (y1 ≥ 0,88), bảng phải mở đầu trang kế (y0 ≤ 0,12), thẳng cột và không có proof số/typed/multitier nào; chỉ `setdefault` trong `bound_dependencies` nên không ghi đè proof thật. Link phải cố ý dùng `header = left_ref` để `_support_link` kéo cả header lẫn chunk trước.
  - `coverage.py`: `plan_ready(plan)` = không `unresolved_references` và mọi group không `unprovided_units`.
  - `service.py`: chỉ appeal khi `insufficient_evidence` **và** `plan_ready`; ngược lại ghi `trace.appeal = {version, attempted: False, outcome: "skipped_structure"}` và giữ abstain, không gọi model.
- **Đo:** cùng 8 câu × 3 = 24 lượt qua API thật, cùng cấu hình P1 (`ast_47f30aaf2665`, `qwen3.8-27b-q4`, API PID 10436). Kết quả `%TEMP%/qnu_p11_8x3_results.json` (ngoài Git).
- **Kết quả chính:**
  - **Q74 PASS mục tiêu hẹp:** `ich_676e38631065` (ord 181, `ev_p014_b003`) trong `support_ids` cả 3/3 lượt; `table_links` 6 với 3 link basis mới; `table_support: resolved`; nội dung 2/3 đúng (lượt 1 over-claim Đông phương học). P1 từng 0/3 vì phủ định sai "không có ngành Ngôn ngữ Trung Quốc".
  - answered **20→22/24**; abstain 0→1 (trung thực, giữ sau appeal lỗi); 502 **4→1** (`answer_table_value_not_extractive` Q24#3); 0 `answer_evidence_changed`, 0 lỗi provider.
  - Appeal: 3 lượt — Q88#2–3 `answered` đúng nội dung; Q24#1 `invalid` (`lookups[0].cell_id`) giữ abstain; **0 `skipped_structure`** ⇒ cổng siết mới chỉ chứng minh cơ chế, **chưa quan sát được tác dụng giảm trả lời liều** trên mẫu này.
  - **G2 FAIL: 3/8 đúng trọn** (Q12, Q85, Q88); Q74 2/3, Q78 2/3, Q19 1/3, Q53 1/3, Q24 0/3; **0 số bịa**.
  - Token/lượt trả lời 4.819,6→4.826,7 (+0,15%); tối đa 8.308→8.129; độ trễ trung bình 9,5→8,9 s. G5/G6 PASS; G3/pytest NOT RUN.
- **Đính chính mục 14:** danh sách "3/8 đúng trọn (Q12, Q19, Q88)" là chưa chặt — Q12 chỉ 2/3 lượt trả lời được (1 lượt 502). Danh sách khớp dữ liệu là **Q19, Q78, Q88** (Q78 vẫn kèm ghi chú thiếu điều kiện phụ); G2 vẫn FAIL 3/8, không đổi kết luận.
- **Giới hạn:** rule bỏ qua trang trích `hybrid` nên khoảng `ev_p011_b014` → `ev_p012_b001` (trang 12) chưa nối; Q24/Q19/Q53/Q78 là lỗi chọn dòng/thiếu vế của model trên envelope đã đủ, thuộc P2 nếu được duyệt.
- **Việc tiếp theo:** duyệt G3 (chạy lại 100 câu); P2 quyết định model qua ModelOps; cân nhắc mở rule nối trang cho `hybrid` khi có bằng chứng.

## 16. Kết quả G3 — chạy lại 100 câu trên mã P1.1 (2026-11-14, phiên 967)

- **Phê duyệt:** "vậy chạy lại 100 câu đi, nếu phát triển lỗi nữa thì phân tích tìm hiểu nguyên nhân ở quy trình chỗ nào". Chạy trên mã P0+P1+P1.1 chưa commit; không sửa mã, không reindex/migration.
- **Cách chạy:** 100 câu, **1 lượt/câu** (không retry trong lượt đo), mỗi câu một hội thoại mới, idempotency `g3-100-{n}-{uuid}`, cùng trợ lý `ast_47f30aaf2665` rev 3 / kho `col_9209e90d1a53` / `qwen3.8-27b-q4` / hybrid_rerank / top_k 5 / candidate_k 40 / context 32 KB / scope explicit / verification off; API PID 10436. Kết quả `%TEMP%/qnu_g3_100_results.json`, so mốc baseline `%TEMP%/qnu_questions_100_results.json` (không ghi đè).
- **Tổng:** answered **89/100**; insufficient 2 (Q53 và Q99 đều giữ trạng thái như baseline); lỗi 9 (Q2 409; Q26, Q28, Q33, Q40, Q41, Q44, Q45, Q73 502).
- **Mã lỗi đọc từ `chat_turns.error_code` (DB, chỉ đọc):** `answer_table_value_not_extractive` ×3 (Q26, Q41, Q73); `answer_cell_invalid` ×2 (Q28, Q40); `answer_coverage_invalid` ×3 (Q33, Q44, Q45); `conversation_clarification_required` ×1 (Q2). 0 `answer_evidence_changed`, 0 lỗi provider.
- **Cổng:** **FAIL theo chữ** — 7 câu thuộc nhóm 84 đúng cũ bị lệch đã xác định (Q2, Q26, Q33, Q40, Q44, Q45, Q73), trong khi cổng chỉ cho phép 1 ca lệch có giải trình. (Q45 thuộc nhóm 84 sau lần thử lại ở baseline. Q99 cùng trạng thái thiếu căn cứ ở hai lần.)
- **Chẩn đoán theo công đoạn (bằng chứng đọc lại từ trace/event, không phỏng đoán):**
  - **Phạm vi chẩn đoán:** sáu câu có lượt thử lại dùng cùng danh sách nguồn, danh mục ô, schema và model. Các câu guard lỗi nhận envelope đầy đủ (event ghi 225 ô bảng – Q26, 271 ô – Q33, đơn vị plan đủ); 6 câu từng đúng ở baseline được chạy lại trên cùng envelope và cho đáp án khớp baseline; Q28/Q41 là lỗi lặp lại từ baseline (Q26 Kỹ thuật điện tử – viễn thông (Thiết kế vi mạch); Q33 Sư phạm Toán có tổ hợp Toán–Tin–Anh; Q40 Quản lý đất đai 7850103 với 9 tổ hợp đều có Địa; Q44 SP KHTN nhận Toán–Sinh–Anh; Q45 SP Lịch sử–Địa lý; Q73 danh mục Phụ lục 1). Lỗi nằm ở **sinh câu trả lời + materialize/guard** (guard trung thực chặn output không trích được/bind sai ô/mã dẫn chứng trùng hoặc ngoài danh sách trong assessment) và ở **định tuyến hội thoại** cho Q2.
  - **Q2:** route v4 tự đánh dấu câu hỏi đứng một mình "Thông báo tuyển sinh này…" là cần làm rõ → 409 trước truy xuất; 4/5 lượt chạy lại định tuyến đúng và trả lời đúng (Chính quy). `rewriting.py` không nằm trong phạm vi P0/P1/P1.1.
  - **Dấu vết P1.1 ở nhóm lỗi:** không envelope lỗi nào chứa link `native_page_band_continuation/v1`; link trang chỉ tác động Q74 (nay trả lời được, nội dung 2/3). **P0:** mọi envelope G3 có `rank_band: 5` (+5 chunk văn bản, +3–4% token prompt) ở cả lượt đúng và lượt lỗi; chưa thể loại trừ gia tăng nhỏ xác suất guard nếu không có A/B (chưa duyệt).
  - **Lỗi guard là ngẫu nhiên theo lượt, có sẵn từ baseline:** hai tệp baseline ghi 10/100 lượt đầu và 4/10 lượt thử lại bị guard 502 (14/110 gộp) trên Q16, Q21, Q25, Q31, Q38, Q41, Q45, Q47, Q49, Q97 lần đầu (chính vì vậy baseline phải retry nhóm transient); G3 single-shot có 8/100 guard. Chạy chẩn đoán thêm 4 lượt × 7 câu (28 lượt, `%TEMP%/qnu_g3_diag_results.json`): HTTP 200 ở Q2 4/4, Q26 2/4, Q33 3/4, Q40 3/4, Q44 2/4, Q45 2/4, Q73 2/4. Một lượt Q40 trả về chỉ tiêu thay vì yêu cầu về môn Địa.
- **Cải thiện trong nhóm 16 câu lỗi cũ (chấm tay):** PASS trọn Q12, Q19, Q21, Q38, Q85, Q88; Q5 đủ 3 website (trước 1, mức tạm đạt); partial Q16 (lẫn 402/402A), Q29 (thiếu chỉ tiêu CNTT), Q74, Q78, Q6; Q24 sai nội dung (học phí thay vì mục/chỉ tiêu – trước đó abstain); Q53 giữ insufficient; Q28/Q41 vẫn lỗi (baseline: sai nội dung / 502 cứng, nên không phải hồi quy câu đúng); Q99 đổi sang insufficient với nội dung tương đương "chưa thể khẳng định" → lệch theo tiêu chí trạng thái, không lệch nội dung.
- **Hiệu năng:** độ trễ mean/median/max 12,7/10,9/29,6 s (baseline) → 10,4/10,2/18,8 s (G3). Token prompt +3–4% so envelope baseline do dải hạng P0.
- **Giới hạn / NOT RUN:** chấm lại nội dung đầy đủ 77 câu còn trả lời được của nhóm 84 cũ **NOT RUN** (mới so trạng thái, đối chiếu token số và spot-check); pytest **NOT RUN**; A/B tách ảnh hưởng P0 **NOT RUN**; chưa commit/push.
- G3 **FAIL**. Trace ghi 8 lỗi kiểm tra đầu ra và 1 lỗi định tuyến. Sáu ca bảng đã đối chiếu có cùng danh sách nguồn và danh mục ô giữa lượt đúng và lượt lỗi. Kết luận này áp dụng cho các ca có trace tương ứng.


## 17. Xử lý sau G3

Xử lý nhóm câu còn lại của G3 theo phạm vi chốt với người dùng. Backend tra cứu tham chiếu nguồn ở lượt đầu, giữ đúng danh tính dòng có mã xuống dòng, ghép đoạn văn và ô danh sách có bằng chứng nối, cho chọn tên từng dòng khi liệt kê. Đính chính G3 lịch sử. Chỉ đo nhóm trọng điểm và đối chứng. [Kết quả chi tiết](../nhat_ky/2026-11-14_phien_969_xu_ly_ca_trong_diem_g3.md).

## 18. Kiểm chứng độc lập sau sửa — phiên 970

- Trên mã commit `c7942a31` (prompt v35), API tạm 8017, 16 câu trọng điểm + đối chứng, 1 lượt/câu: **15/16 HTTP 200 và đúng nội dung**; 7 ca từng lệch cổng (Q2, Q26, Q33, Q40, Q44, Q45, Q73) đều đạt; repair 3/3 lượt cần đều `answered` (Q12/Q26/Q85, +4,7–5,9 s).
- **Q41 chưa ổn định:** chỉ 1/4 lượt độc lập trả 200 (lượt đó thừa "Quản lý giáo dục"), 3/4 lượt 502 `answer_table_value_not_extractive`; không tái hiện được tuyên bố đã sửa của phiên 969 (quan sát 1 lượt).
- Cổng G3 đính chính **7/84** (Q99 baseline cũng `insufficient_evidence` nên không thuộc nhóm 84). Full 100 câu, pytest, chấm 76–77 câu còn lại **NOT RUN**; không kết luận G3 PASS. [Chi tiết](../nhat_ky/2026-11-14_phien_970_kiem_chung_doc_lap_g3.md).
