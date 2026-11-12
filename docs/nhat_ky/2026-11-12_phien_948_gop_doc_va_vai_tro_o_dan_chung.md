# Phiên 948 — Lệch cột khi header gộp dọc và xác thực vai trò ô dẫn chứng năm

- **Yêu cầu / giả định.** Chỉ xử lý hai lỗi Backend V1: (1) lệch cột khi hàng tiêu đề có ô gộp dọc — `compilation.table_year` và `metadata.target_refs` đếm cột cục bộ theo hàng; (2) `data_year` gắn cho cột có thể được “chứng minh” bằng ô số lượng chứa đúng số năm. Tái sử dụng `index.table_layout.layout` để nhận diện năm và xác thực dẫn chứng dùng **cùng tọa độ cột vật lý** (`row_span`/`col_span`), vẫn map về ô nguồn; cấu trúc lỗi hoặc header mâu thuẫn → năm `unknown`. Với `data_year` cấp cột, dẫn chứng phải là ô header chi phối cột và đọc **toàn văn** ô để không mất ngữ cảnh “năm ban hành/hiệu lực”; áp dụng cho cả metadata tự động và metadata qua API đăng ký. Giữ nguyên guard số liệu, guard citation, ngân sách truy xuất và dữ liệu/chỉ mục đang phục vụ. E2E Qwen thật trong collection mới, **đúng một lượt mỗi câu**, ghi lần đầu; không retry để làm xanh, không nới assertion/guard; `NOT RUN` không phải `PASS`.

## Nguyên nhân

- **Lỗi 1 — lệch cột.** `table_year._covering` và `metadata` đếm cột bằng vị trí phần tử trong danh sách ô **cục bộ của từng hàng**. Với ô tên ngành gộp dọc qua hai hàng tiêu đề, hàng tiêu đề thứ hai bắt đầu ở cột vật lý kế tiếp nhưng hàm vẫn đánh số từ 0, nên năm của cột 2027 bị gắn sang cột 2026 (và annotation `column:c` trỏ sai ô khi xác thực).
- **Lỗi 2 — sai vai trò ô.** `validate_annotations` chỉ kiểm tra ref dẫn chứng thuộc target và số/nhãn xuất hiện trong nguồn; không kiểm tra ô được dẫn có phải **header chi phối cột** hay không. Vì vậy một ô số lượng chứa `2027` trong chính cột đó vẫn “chứng minh” được `data_year: 2027`; trích đoạn ngắn cũng có thể bỏ mất vai trò “năm ban hành/hiệu lực”.

## Sửa gốc

- `backendV1/qnu/domains/knowledge/index/table_layout.py`: giữ `table_structure()`/`layout()`/`header_rows()` làm nguồn tọa độ duy nhất (`table_structure` đọc đúng trường `row_count`/`column_count` của OCR).
- `backendV1/qnu/domains/knowledge/compilation/table_year.py`: bỏ cách đếm cục bộ; dựng lưới bằng `table_structure` + `layout`, duyệt header rows; năm đặt theo **cột vật lý** (`position.column <= column < column + col_span`); cột phải có ô dữ liệu; nhiều tầng header mâu thuẫn hoặc lỗi hình học → không gắn năm (`unknown`). Trả `{table, column, year, evidence_citation, evidence_quote}` với citation về đúng ô header nguồn.
- `backendV1/qnu/domains/knowledge/metadata.py`: `_grid`/`_refs`/`_column_refs` dùng ref lưới theo tọa độ vật lý; `target_refs` trả **hợp** ref lưới ∪ ref hàng cục bộ cũ để bản đã đăng ký vẫn đọc được; thêm `_require_column_year_proof(item, content)` cho `table:…:column:c` có `values.data_year`: dẫn chứng phải thuộc ô header chi phối cột (trong danh sách `header_refs`, phủ cột theo `col_span`) và `data_year(toàn văn ô)` phải đúng bằng năm khai báo; ô số lượng, header cột khác, hay “Năm ban hành 2027” bị từ chối `retrieval_metadata_invalid`.
- `backendV1/qnu/domains/knowledge/compilation/supplement.py`: `_targets` sinh ref cột theo lưới vật lý, chỉ fallback tọa độ hàng cục bộ khi cấu trúc lỗi.
- `backendV1/qnu/domains/knowledge/publication/automatic_metadata.py` và `publication/service.py` (`_register`): gọi `validate_annotations(..., strict_roles=True)` — áp dụng cho cả preview metadata tự động lẫn metadata gửi qua API đăng ký.
- Đường đọc không đổi: `publication/evidence.py` `registered_bundle_hash` vẫn gọi `validate_annotations` **không** `strict_roles`; `assert_pinned` được dùng ở `reading.py`, `source_text.py`, `table_context.py`, `decisions.py`, `replacement.py`, `review_gate.py`.

## Tương thích bản đã đăng ký

- Phiên bản đã lưu **không bị kiểm lại** bằng luật chặt: mở version/draft của bản 947 vẫn 200; `retrieval_metadata` giữ nguyên; draft đã phục vụ vẫn có `157`. Không sửa dữ liệu, chunk hay chỉ mục đang phục vụ; không re-index.
- **Điều kiện cần ghi nhận:** preview chặt hơn có thể làm `automatic_metadata_sha256` của một lượt compile thay đổi; client đang giữ sha cũ sẽ nhận `409 registration_metadata_changed` và phải mở lại hộp thoại đăng ký. Metadata cột gửi thủ công nay bắt buộc dẫn header chi phối cột; annotation đã lưu trước đây không bị ảnh hưởng.

## Kiểm thử cô lập

- **Red-first:** hai ca tái hiện trong `backendV1/tests/unit/test_vertical_merge_year_948.py` (lệch cột khi ô ngành gộp dọc; ô số lượng `2027` làm chứng cứ `data_year` cột) được viết và chạy đỏ trước khi sửa; sau sửa toàn bộ 10 ca xanh — receipt mới: **10 passed / 1,32 giây**, DB `qnu_v1_test_f9a0903252474988`, `db_dropped: true`, sentinel giữ, `pytest_exit: 0` (8,75 giây tổng).
- Batch 10 tệp DOCX/metadata/publication/RAG (`test_automatic_metadata_896.py`, `test_answers_api_648.py`, `test_hybrid_655.py`, `test_publication_646.py`, `test_preparation_publication_chain.py`, `test_publication_index_sync_878.py`, `test_native_extraction_710.py`, `test_docx_fixture_737.py`, `test_docx_fragments_872.py`, `test_ocr_docx_html.py`): **114 passed / 707,86 giây**; receipt `{"database": "qnu_v1_test_622ef332b3c04f24", "db_dropped": true, "legacy_sentinel_preserved": true, "pytest_exit": 0, "seconds": 720.28}`.
- Ruff trên 7 tệp sửa: `All checks passed!`.
- Full backend suite **NOT RUN** — hai tiến trình pytest cũ PID 18888/22164 treo từ phiên trước, không dùng được; baseline lịch sử **FAIL 4/1627** phiên 928 giữ riêng.

## E2E Qwen thật trong collection mới

- Restart dev stack lúc 20:27 để nạp mã mới (API `uvicorn` + worker ARQ + FE V2); không đụng tiến trình khác. Trợ lý dùng `chat_provider_id=prv_902ce43408bb` (`qwen3.8-27b-q4`), collection mới `col_853a15b89a4a`.
- Hai nguồn trong cùng collection: DOCX cũ `ke_hoach_12_kh_dt_chi_tieu_2027.docx` (`src_c1d35cc2d368`, OCR `ocr_d163928dcc7a`) và DOCX gộp ô `ke_hoach_14_kh_dt_chi_tieu_2026_2027_gop_o.docx` (`src_5ef86c53600b`, OCR `ocr_69205b6a6cbe`, 37.251 byte). DOCX gộp ô là tệp thật do Docling parse: ô “Ngành đào tạo” gộp dọc qua hai hàng tiêu đề, hàng tiêu đề thứ hai có “Chỉ tiêu năm 2026”/“Chỉ tiêu năm 2027”, hàng dữ liệu `Khoa học dữ liệu` = **31**/**47**.
- Sửa `95→157` tại unit `ev_p001_b006_c03_02` của DOCX cũ bằng API rà soát văn bản (version 0→1).
- Compile `cmp_77bf86547d80` (cũ) / `cmp_20d20ff0d080` (mới); đăng ký `cdoc_aa603b538fa2`/`cver_ff33bf7d445e` (bundle `59458e7b057f70b1…`) và `cdoc_b8cc7e1e2f7a`/`cver_ddde9026bc62` (bundle `1d8910f59ee8d3e6…`); submit `rsub_85128c4f8364`/`rsub_436f59e2fac9`; duyệt `pdec_245cbd069aa9`/`pdec_385d37dbc8e1`; xuất bản `pdec_3bd5d7b897c4`/`pdec_c681acbf484c`.
- Annotation năm đã phát hành: bản cũ `table:ocr_d163928dcc7a:ev_p001_b006:column:2` = `data_year 2027`, chứng cứ `…c00_02`; bản mới `column:1` = `2026` chứng cứ `…c01_00`, `column:2` = `2027` chứng cứ `…c01_01` — đúng cột vật lý dưới ô gộp dọc; strict role chỉ chấp nhận ô header hàng 1, không phải ô số lượng.
- Index **tự động** `idx_31f0c4127663` generation 2, **15 chunk**, `completed`; readiness `ready` cho cả hai version; `runs_in_collection=2`; script **không** gọi `POST /indexing-runs` (`manual_index_request_issued_by_script: false`).
- Năm câu hỏi, **mỗi ca một lượt, mỗi ca một hội thoại riêng**, ghi lần đầu, không gửi lại:

| Ca | Kết quả lần đầu | Lọc đã resolve | Token (prompt/completion) | Thời gian | Dẫn chứng ô |
|---|---|---|---|---|---|
| `new_2027` — “chỉ tiêu năm 2027 ngành Khoa học dữ liệu?” | `answered`: “Khoa học dữ liệu — Chỉ tiêu tuyển sinh / Chỉ tiêu năm 2027: **47** [E1]” | `data_year: 2027`, 3 chunk đủ điều kiện | 2393 (2328/65) | 7,55 giây (trace 5813 ms) | `E1:r2:k2`; source_cells gồm header `…c01_01`, chủ thể `…c00_00`, giá trị `…c02_02`; version/publication khớp; **31 không bị dẫn** |
| `new_2026` — “chỉ tiêu năm 2026 ngành Khoa học dữ liệu?” | `answered`: “Khoa học dữ liệu — Chỉ tiêu tuyển sinh / Chỉ tiêu năm 2026: **31** [E1]” | `data_year: 2026`, 1 chunk đủ điều kiện | 2150 (2040/110) | 6,96 giây (5594 ms) | `E1:r2:k1`; header `…c01_00`, giá trị `…c02_01`; **47 không bị dẫn** |
| `old_ai_2027` — DOCX cũ, ngành Trí tuệ nhân tạo | `answered`: “Trí tuệ nhân tạo — Chỉ tiêu năm 2027: **157** [E1]” | `data_year: 2027` | 2358 (2261/97) | 6,96 giây (5641 ms) | `E1:r3:k2`; header `…c00_02`, giá trị `…c03_02` (đã sửa `157`); version/publication khớp |
| `old_httt_2027` — DOCX cũ, ngành Hệ thống thông tin | `answered`: “… năm 2027 cho ngành Hệ thống thông tin … là **120** [E2] …: 120 [E1]” | `data_year: 2027` | 2373 (2260/113) | 7,68 giây (6297 ms) | `E1:r2:k2`; header `…c00_02`, giá trị `…c02_02` |
| `old_ai_2030` — năm **không có** trong tài liệu | `insufficient_evidence`/`no_match` (từ chối trung thực) | `data_year: 2030`, **0 chunk** đủ điều kiện | không gọi model | 1,67 giây (313 ms) | không dẫn ô; không mượn 157/120/95/145/31/47 |

- **Tương thích bản cũ 947 (live):** GET version + draft của `cver_2a8d009a487c` đều **200**; `retrieval_metadata` không đổi; draft chứa `157` — bản đã đăng ký trước sửa vẫn mở và truy xuất bình thường.
- **Sự cố harness, ghi trung thực:** lần chạy `index_auto` đầu gọi `/versions/{id}/index-readiness` → **404** vì endpoint đúng là cấp tài liệu (`index/router.py:125`); index vẫn đã tự động hoàn tất, **chưa câu hỏi nào được gửi**. Chỉ sửa URL trong script (và cho kết quả compat đổi `RESULT` khi fail), không đổi sản phẩm; cờ FAIL cũ trong state được xóa sau khi xác định nguyên nhân nằm ở harness. Năm câu hỏi chỉ được gửi một lần sau đó.

## Trạng thái và việc tiếp theo

- Đạt: 10 unit + 114 batch + Ruff sạch + E2E 5/5 theo tiêu chí + compat 947; index tự động `ready`; không re-index, không đổi giá trị mặc định retrieval/prompt; không commit/push.
- Giới hạn: full backend suite **NOT RUN**; XLSX ngoài phạm vi; detector vẫn chỉ gắn năm khi hàng header được đánh dấu rõ và nêu đúng một năm dữ liệu (hàng/header mơ hồ → `unknown`); F13 và Q09 502 của phiên 946 vẫn mở, không liên quan sửa này. `NOT RUN ≠ PASS`; token PASS không đồng nghĩa nội dung đúng.
- Việc tiếp theo (chờ người dùng): rà diff và quyết định commit; nếu mở rộng, cân nhắc đường nhập metadata thủ công cho bảng không có dấu header và bổ sung ca XLSX.

Lệnh kiểm chứng chính:

```bash
# từ backendV1/ — DB cô lập tự tạo/xóa, không dùng DB ứng dụng
set -a && . ../.env && set +a && MSYS_NO_PATHCONV=1 PYTHONIOENCODING=utf-8 \
  uv run python scripts/run_isolated_tests.py -q tests/unit/test_vertical_merge_year_948.py

set -a && . ../.env && set +a && MSYS_NO_PATHCONV=1 PYTHONIOENCODING=utf-8 \
  uv run python scripts/run_isolated_tests.py -q \
  tests/integration/test_automatic_metadata_896.py \
  tests/integration/test_answers_api_648.py \
  tests/integration/test_hybrid_655.py \
  tests/integration/test_publication_646.py \
  tests/integration/test_preparation_publication_chain.py \
  tests/integration/test_publication_index_sync_878.py \
  tests/unit/test_native_extraction_710.py \
  tests/unit/test_docx_fixture_737.py \
  tests/unit/test_docx_fragments_872.py \
  tests/unit/test_ocr_docx_html.py

uv run ruff check qnu/domains/knowledge/compilation/table_year.py \
  qnu/domains/knowledge/compilation/supplement.py \
  qnu/domains/knowledge/index/table_layout.py qnu/domains/knowledge/metadata.py \
  qnu/domains/knowledge/publication/automatic_metadata.py \
  qnu/domains/knowledge/publication/service.py tests/unit/test_vertical_merge_year_948.py

# E2E (dev stack 20:27, provider prv_902ce43408bb):
python "$TEMP/qnu_e2e_948_merged.py" <create|upload|process|review_edit|compile|register|submit|publish|index_auto|assistant|ask|verify|compat>
```
