# Phiên 946 — Khóa từng số theo nhãn trong mệnh đề và chứng minh hội thoại dùng bản văn đã sửa

- **Yêu cầu / giả định.** Hai câu đảo giá trị trong **cùng một câu** vẫn lọt lớp xác minh v6: nguồn Alpha 2025=18/2026=22 nhưng chấp nhận “Alpha năm 2025 là 22, năm 2026 là 18”; nguồn Alpha Quy mô=100/Ghi nhận=50 nhưng chấp nhận “Alpha có Quy mô 50 và Ghi nhận 100”. Phải thêm 2 ca âm + 2 ca đúng tương ứng, **chạy đỏ trước khi sửa**, phủ dấu phẩy/“và” tiếng Việt và chủ thể bị tỉnh lược; rà `_table_support`, `_unsupported_numbers` và logic xung đột trường; xác minh **từng dự kiện** theo chủ thể, hàng, cột, năm/chỉ tiêu và giá trị ô nguồn. Không thêm từ khóa/regex đặc thù fixture, không nới kiểm tra dẫn chứng, giữ các ca đúng nhiều năm/nhiều chỉ tiêu/nhiều chủ thể. Sau khi sửa phải chạy bộ test cô lập liên quan bảng, chọn bằng chứng và API trả lời, chỉ nhận kết quả có mã thoát và phiên bản mã xác định; đo lại Q05/Q07/Q08/Q09/Q13 trên mã mới so với 944, đếm **lần thử đầu tiên**, giữ lỗi, không gửi lại để cải thiện điểm. Cuối cùng chứng minh bằng một collection cô lập rằng hội thoại thật dùng **bản văn đã hiệu đính**: upload tài liệu tiếng Việt, sửa tay một giá trị, lưu phiên bản, duyệt, xuất bản, chờ **index tự động** đúng phiên bản đã xuất bản, tạo hội thoại bình thường với trợ lý gắn collection và hỏi mà không chèn giá trị mới; báo lần đầu, thời gian, token.

## Nguyên nhân

- Phiên 945 đã xác minh số theo **hàng chủ thể** và **cột/năm/chỉ tiêu**, nhưng trong một mệnh đề nhiều nhãn, `_table_support` vẫn dùng chung một tập `claimed_tokens` cho cả đoạn chủ thể. Khi cả hai năm (hoặc hai nhãn chỉ tiêu) và cả hai giá trị nằm trong cùng câu, mỗi giá trị có thể khớp **một token khác** trong tập: 22 khớp token 18 và ngược lại, nên hoán vị vẫn được chấp nhận.
- Lỗi nằm ở **ràng buộc từng số với nhãn của chính mệnh đề chứa nó**, không phải ở ngưỡng, top-k hay dẫn chứng. Vì vậy không sửa retrieval, không re-index, không đổi parser/chunking.

## Sửa gốc (`backendV1/qnu/domains/rag/answer/cells.py`)

- `_clause_claims(text)`: tách câu thành mệnh đề bằng `[;:]|,(?!\d)` — dấu phẩy thập phân (`93,3`) và ngày (`30/11/2026`) không bị cắt; mỗi token số nhận **nhãn năm/chỉ tiêu gần nhất về phía trước trong cùng mệnh đề**, nếu không có thì lấy nhãn kế tiếp trong mệnh đề; nhãn ở mệnh đề khác không áp dụng. Token năm tự nhận chính nó để ngày tháng giữ nguyên khối.
- `_occurrences(text, needle)` và `_nearest_label(labels, position)`: hỗ trợ ghép nhãn theo vị trí, không dùng danh sách từ khóa của fixture.
- `_subject_segments(statement, facts)`: chia câu theo mốc chủ thể đã khớp, mỗi đoạn giữ danh sách `(token, năm, chỉ tiêu)` từ `_clause_claims`.
- `_claim_binds(year, metric, col_years, col_metrics, said_years, said_metrics)`: giá trị **có nhãn cục bộ** phải khớp năm/chỉ tiêu của cột; giá trị **không có nhãn cục bộ** vẫn có thể buộc qua nhãn của cả câu (kiểm tra bảo thủ cũ); cột chưa rõ năm/chỉ tiêu thì để mở.
- `_table_support`: mỗi số phải nằm trong `claimed_tokens` của đúng đoạn chủ thể **và** tự qua `_claim_binds`; chỉ khi câu chỉ có một đoạn chủ thể mới fallback về toàn bộ claim của câu. Số trong đoạn văn được dẫn không thay thế xác minh ô bảng (`_unsupported_numbers` giữ nguyên nguyên tắc này).
- **Tăng phiên bản:** `VERSION` và `PROJECTION_VERSION` từ `qnu.answer-cells/v6` / `qnu.answer-projection/v6` lên **v7**. Cần thiết để trace/kiểm thử/audit phân biệt hành vi cũ–mới; đường trả lời không có cache trả lời bền vững (chỉ có cache nội bộ một request ở `source_text.py`), nên không cần migrate/xóa cache.
- Ghi chú rà soát: **không tìm thấy `_field_conflicts`** trong mã hiện tại (grep toàn module và `git log -S` đều rỗng); đã rà `_table_support`, `_claim_binds`, `_unsupported_numbers`, `_column_texts`/`_column_year`/`_column_metric` và trạng thái `conflicting` của `coverage.py` (không đổi). Không mở thêm abstraction.

## Test đỏ → xanh (DB cô lập, có mã thoát)

Bốn hàm mới trong `backendV1/tests/unit/test_fact_attribution_946.py`, mỗi hàm chạy hai biến thể `[False, True]` (không có / có dấu header kèm citation):

| Thời điểm | DB cô lập | Kết quả | Exit |
|---|---|---|---|
| Trước sửa — chạy đỏ đúng tệp 946 | `qnu_v1_test_6e0924ed7f6746bb` | **4 failed, 17 passed**; đúng 2 hàm âm × 2 biến thể: `test_swap_within_one_multi_year_statement_rejected[False/True]`, `test_swap_within_one_multi_metric_statement_rejected[False/True]`. Hai hàm đúng cùng cặp đạt. | **1** |
| Sau sửa — tệp 946 | `qnu_v1_test_42e107b0d2e545ef` | **21 passed** / 1,46 s | 0 |
| Bộ rộng phát hiện hồi quy (18:31) | `qnu_v1_test_4cc85a9bfa634be5` | **1 failed, 60 passed** — `test_unselectable_prose_941.py::test_unselectable_table_keeps_decimal_comma_and_date_tokens_verbatim` (dấu phẩy thập phân/ngày bị tách mệnh đề) | **1** |
| Sửa tiếp (token năm tự nhận) và chạy lại 6 tệp bảng/chọn bằng chứng | `qnu_v1_test_d92faca68375444e` | **82 passed** / 1,87 s | 0 |
| API trả lời (pins v6→v7) | `qnu_v1_test_2ed2431c89764911` | **31 passed**, 2 warnings / 322,44 s | 0 |
| Baseline trước khi thêm ca (6 tệp, mã v6) | `qnu_v1_test_d451d73762e74227` | **63 passed** | 0 |
| Sau khi `ruff format` tệp test mới — chạy lại | `qnu_v1_test_6384752a4ce14a4b` | **21 passed** / 1,37 s | 0 |

Cả 7 lượt đều ghi `db_dropped: true`, `legacy_sentinel_preserved: true`. Các tệp trong lượt 82 ca: `test_answer_projection_764.py`, `test_fact_attribution_946.py`, `test_multitier_table_941.py`, `test_rag_table_siblings_935.py`, `test_table_row_attribution_944.py`, `test_unselectable_prose_941.py`. Lượt 63 ca trước sửa còn có `test_hybrid_fusion_938.py` và `test_rag_recall_941.py`; phiên này **không sửa mã retrieval** nên hai tệp đó không chạy lại trên mã cuối — ghi nhận riêng, không tuyên bố đã chạy lại.

Ca mới giữ đúng hợp đồng: câu đảo bị từ chối bằng `answer_table_value_not_extractive` (không có câu nào xác minh được), câu đúng cùng dữ liệu được chấp nhận nguyên văn; dùng dấu phẩy trong ca nhiều năm và “và” trong ca nhiều chỉ tiêu, chủ thể “Alpha” chỉ xuất hiện một lần (tỉnh lược ở mệnh đề sau). Các ca đúng cũ (nhiều hàng, nhiều năm, nhiều chỉ tiêu, số trong đoạn văn không thay thế ô bảng, giữ câu đúng và báo thiếu) vẫn đạt.

## Đo live trên mã cuối so với 944

Môi trường: `ws_39c202a81045`, collection phiên 940 `col_0daa6e0ed137`, index `idx_bfd36fae5a30` generation 1 (465 chunk, không re-index), `hybrid_rerank`, `top_k=5`, `candidate_k=30`, `rrf_k=60`, embedding bge-m3, rerank `bge-reranker-v2-m3` (`prv_8f5c1f17c932`), chat `qwen3.8-27b-q4` (`prv_902ce43408bb`), prompt `qnu.rag.answer/v28`, grounding **`qnu.answer-cells/v7`** (trace xác nhận).

| Câu | 944 (2 vòng, v5) | 946 lần thử đầu (v7) | Ghi chú |
|---|---|---|---|
| Q05 | 2/2 (4416/5,75 s; 4416/7,70 s) | **1/1 answered**, 4416 token, 7,15 s | chủ thể đúng, không lẫn giá trị đối chứng |
| Q07 | 2/2 (2970/5,89 s; 3053/8,29 s) | **1/1**, 2990 token, 6,35 s | |
| Q08 | 2/2 (9430/9,49 s; 9473/10,17 s) | **1/1**, 9501 token, 8,11 s | `AM-0029`/`127` có trong rerank và top-5 cuối |
| Q09 | 2/2 | **0/1 — HTTP 502 `answer_citation_invalid`**, 6,58 s | lỗi hợp đồng đầu ra của model — bản ghi `answer.validation_failed` ngày 2026-11-12 cho thấy `duplicate` tại `statements[0].evidence_ids` (lặp một ID hợp lệ; **không** có `not_allowed`), không phải citation ngoài tập; giữ nguyên, không chạy lại để làm xanh |
| Q13 | 2/2 (3298/9,35 s; 3415/10,68 s) | **1/1**, 3355 token, 10,22 s | chunk công thức `ich_18e57e5dec06` ở rerank hạng 2 và được dẫn |

**Lần thử đầu tiên trên v7: 4/5** (944 là 5/5 nhưng trên grounding v5). Q09 là lỗi đã biết từ phiên 945, không do lớp xác minh số. Có thêm **một lượt đo bổ sung** chỉ cho Q09/Q13 lúc 18:44 (không phải lần đầu): Q09 lặp lại 502 trong 5,98 s; Q13 `answered` 3391 token/9,46 s, chunk công thức vẫn hạng 2 và được dẫn. Lượt này chỉ để xác nhận lỗi trên mã cuối, **không ghi đè kết quả lần đầu** và không dùng để tuyên bố đạt.

## Chứng minh hội thoại dùng bản văn đã hiệu đính

Hai collection cô lập mới trong cùng workspace; API và worker đã chạy mã v7 trước khi đo (trace grounding v7). Không đụng collection phục vụ `col_0daa6e0ed137`, không reset DB, không tạo index thủ công.

### Lượt 1 — DOCX, thất bại lần đầu (giữ nguyên, không gửi lại)

- Collection `col_042b8acbb9bb`; nguồn `src_f002d9274254`/`rev_e81cf09c6bdf`, OCR `ocr_afcd32314f61`; tài liệu `cdoc_46e0b840f05c`, phiên bản `cver_f73206669f7d`.
- Sửa tay ô `ev_p001_b006_c03_02`: `95` → `157` (text version 0→1, `txt_c5b86812a5b9`; SHA-256 `cc086016…` → `2d8f0c62…`, lưu 18:45:14). Duyệt `pdec_eb3a9d49f98e`, xuất bản `pdec_29656aaa7dac` lúc 18:45:20.
- Index **tự động** `idx_18a13bc8d3c1` generation 1, 8 chunk, `manual_creation: false`; readiness `ready` đúng `cver_f73206669f7d`/`pdec_29656aaa7dac`/bundle `73dc1b28…`, `version_state 3`.
- Trợ lý `ast_4c21acb478dd`, hội thoại `cnv_d49909f9fd28`; hỏi chỉ tiêu Trí tuệ nhân tạo 2027 qua API hội thoại thường, một lần: HTTP 200, turn `completed`, 5,44 s, 2072 token (2016/56), nhưng kết quả `insufficient_evidence`, `reason=model_abstained`, không có nguồn, câu trả lời rỗng.
- **Nguyên nhân đã chỉ ra:** catalog scope v2 đặt `data_year: 2027`; chunk bảng `ich_321aa7497a45` (chứa hàng “Trí tuệ nhân tạo 7480107 157” kèm header) có `units: []` nên **không mang metadata năm**, bị loại; chỉ đoạn mở đầu `ich_b7ae49f355fc` được đóng gói (368 byte), `available_cells: 0`, yêu cầu coverage `missing`. Model từ chối thay vì bịa — hành vi đúng với ngữ cảnh được cấp, nhưng mục tiêu chứng minh **không đạt**. Bản đã xuất bản vẫn chứa `157` và không còn `95` (`served_text_has_edited_value: true`), nên đây là **khoảng trống metadata năm cho chunk bảng**, không phải phục vụ bản cũ. Không gửi lại câu này.

### Lượt 2 — PDF văn bản, đạt lần đầu

- Collection `col_f813d479b31f`; nguồn `src_961a0cc80b35`/`rev_84dd1f2f881c`, OCR `ocr_d81a39b4eae8`; tài liệu `cdoc_ba2e76c373a6`, phiên bản `cver_f13efc50cb15`.
- Sửa tay đoạn `ev_p001_b009`: “Điều 3. Hạn nộp hồ sơ xét học bổng là 16 giờ 30 phút ngày **25/09/2026**.” → “… ngày **27/09/2026**.” (text version 0→1, `txt_f23d8be11859`; SHA-256 `4f66f8de…` → `0c4889f2…`, lưu 18:48:15). Duyệt `pdec_dfdec5cb8432`, xuất bản `pdec_b80b361ba6dc` lúc 18:48:22.
- Index **tự động** `idx_68ab1fc099e8` generation 1, 18 chunk, `manual_creation: false`; readiness `ready` đúng `cver_f13efc50cb15`/`pdec_b80b361ba6dc`/bundle `e2e10afa…`, `version_state 3`.
- Trợ lý `ast_61ba462b168f` (chat `prv_902ce43408bb`, cùng ModelOps), hội thoại `cnv_5279ef38517b`; hỏi qua API hội thoại thường (`POST /turns`, `expected_turn_no 0`, `Idempotency-Key`), **không chèn giá trị mới**: “Theo Quyết định 27/QĐ.HB, hạn nộp hồ sơ xét học bổng là ngày nào?”
- **Lần đầu:** HTTP 200, turn `completed`, 6,71 s, 2996 token (2893/103), `answered`: “Theo Quyết định 27/QĐ.HB, hạn nộp hồ sơ xét học bổng là 16 giờ 30 phút ngày **27/09/2026**. [E1] [E7]”.
- Kiểm tra: giá trị đã sửa có mặt, giá trị cũ **không** xuất hiện; cả 5 nguồn được dẫn đều `version_id = cver_f13efc50cb15` và `publication_decision_id = pdec_b80b361ba6dc`; bản nháp đã xuất bản chứa `27/09/2026`, không chứa `25/09/2026`; scope không lọc năm (`filters: [{}]`), dense 18 → top-5, grounding `qnu.answer-cells/v7` + projection v7, prompt v28, coverage yêu cầu `covered` với `E1`/`E7`.

## Kiểm chứng kỹ thuật

- **Ruff check** trên 4 tệp đã sửa trong phiên (`cells.py`, `test_fact_attribution_946.py`, `test_answers_api_648.py`, `test_unselectable_prose_941.py`): `All checks passed!`. `ruff format` chỉ áp cho tệp test mới; 3 tệp còn lại đã đúng định dạng.
- **Full Pytest: NOT RUN** — hai tiến trình full-suite cũ từ cửa sổ trước (PID 18888/22164) vẫn treo, không can thiệp; baseline lịch sử **FAIL 4/1627** (phiên 928) giữ riêng. **NOT RUN ≠ PASS**.
- **XLSX: NOT RUN** — không có fixture/đường kiểm thử XLSX trong đợt này.
- Không kill tiến trình lạ, không reset DB, không re-index collection đang phục vụ, không commit/push.

## File sửa trong phiên

- `backendV1/qnu/domains/rag/answer/cells.py`: `_clause_claims`, `_occurrences`, `_nearest_label`, `_subject_segments` dùng claim theo mệnh đề, `_claim_binds` theo từng token, `_table_support` yêu cầu buộc nhãn cục bộ; tăng `VERSION`/`PROJECTION_VERSION` lên v7.
- `backendV1/tests/unit/test_fact_attribution_946.py`: thêm 2 ca âm + 2 ca đúng (parametrized `[False, True]`), định dạng lại tệp.
- `backendV1/tests/integration/test_answers_api_648.py`: cập nhật pin phiên bản v6 → v7.
- Tài liệu: `docs/WORK_LOG.md`, `docs/nhat_ky/README.md`, `docs/memory/PROJECT_CONTEXT.md`, nhật ký này và snapshot `docs/memory/snapshots/2026-11-12_session_946.md`.

## Rủi ro / bước sau

- **Chunk bảng thiếu metadata năm** (DOCX): chunk bảng native có `units: []` nên không mang `data_year`; câu hỏi có năm bị catalog scope loại đúng chunk chứa câu trả lời. Cần lan truyền năm theo cột/ô từ cấu trúc bảng sang metadata chunk (kèm bằng chứng), và sẽ phải re-index có kiểm soát khi triển khai — **chưa thực hiện** trong phiên này.
- **Q09 502 `answer_citation_invalid`** vẫn mở ở lớp hợp đồng đầu ra của model (đính chính 2026-11-12 theo bản ghi sự kiện: lỗi là `duplicate` — lặp một ID hợp lệ trong `statements[0].evidence_ids`; không có `not_allowed`/ID ngoài tập), độc lập với xác minh số; không hạ guard, không retry để làm xanh.
- F13 (chất lượng câu trả lời thiếu ý), G3/G4 và các câu Q12/Q18/Q20/Q24/Q27 vẫn là hạng mục riêng, chưa sửa trong phiên này.
- Kết quả đo là kiểm chứng kỹ thuật trên corpus phiên 940 và hai collection cô lập, không phải benchmark chất lượng toàn diện; nhãn câu hỏi vẫn cần người duyệt.
