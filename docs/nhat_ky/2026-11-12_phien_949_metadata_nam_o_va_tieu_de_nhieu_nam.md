# Phiên 949 — Duyệt lại đường năm của bảng DOCX/PDF: ô hợp lệ, ô số lượng và tiêu đề con nhiều năm

- **Yêu cầu / giả định.** Người dùng nêu ba trường hợp còn lỗi sau phiên 948 — P1 “Metadata năm hợp lệ của một ô bị từ chối” (`metadata.py:229`), P2 “Dẫn chứng năm vẫn có thể lấy từ ô số lượng” (`metadata.py:247`), P2 “Tiêu đề con nhiều năm vẫn bị gán một năm” (`table_year.py:60`) — rồi yêu cầu rà soát tiếp các đường năm của DOCX/PDF và xử lý. Giữ nguyên guard số liệu, guard citation và ngân sách truy xuất; không nới assertion hay bỏ guard; đường đọc bản đã đăng ký phải còn mở được; E2E Qwen thật đúng **một lượt mỗi câu**, ghi lần đầu, không retry để làm xanh; `NOT RUN` không phải `PASS`.

## Nguyên nhân

- **P1 — ô hợp lệ bị từ chối.** `metadata.target_refs` chỉ mở ref cho target `table:…:column:c` (mọi ô phủ cột + header) nhưng với target **ô** `table:…:row:r:column:c` lại chỉ trả ref của hàng/ô đích. Strict proof năm của ô không thấy ô header chi phối cột trong danh sách ref hợp lệ, nên đề xuất đúng vẫn bị loại ở preview/đăng ký.
- **P2 — dẫn chứng năm từ ô số lượng.** Với target cột, bước strict chỉ kiểm tra evidence thuộc header chi phối cột và chuỗi quote có chứa năm, không buộc quote đó nằm ở **chính ô header**. Một ô số lượng `2027` trong cột vẫn “chứng minh” được `data_year: 2027`; nhãn đọc trên văn bản tách nhãn (`data_year(text)`) lại bỏ qua toàn văn ô nên cụm “năm ban hành/hiệu lực” ở tiêu đề cha cũng lọt. Target **hàng** trước phiên này không có proof năm nào.
- **P2 — tiêu đề con nhiều năm gán một năm.** Khi ô header chi phối cột chứa tập năm hoặc khoảng năm (`2026, 2027`, `2026-2027`, viết tắt `2026-27`), detector cũ bỏ qua ô đó hoặc tách được một năm, rồi lấy năm đơn của tiêu đề cha phủ lên cột con mơ hồ. Hệ quả: cột không xác định bị gắn năm, dẫn đến lọc/chọn ô sai.

## Sửa gốc

- `backendV1/qnu/domains/knowledge/compilation/table_year.py`:
  - `year_mentions(text)` — mọi năm ô nêu, loại ngày `d/m/yyyy` và ô có vai trò (`ban hành|hiệu lực|ký|ngày|phát hành`); mở rộng khoảng năm (`2026-2027`, `2026-27`) thành tập.
  - `data_year(text)` — chỉ trả **một** năm khi mọi lần nhắc năm trong ô đều mang nhãn dữ liệu (“năm dữ liệu”, “niên độ báo cáo”, “mùa tuyển sinh”, “năm tuyển sinh”, “tuyển sinh năm”); tập năm, khoảng năm, ngày, vai trò → `None`.
  - `labelled_years(text)` — các năm có nhãn dữ liệu của một ô; `column_year(cells)` — gom toàn bộ ô header chi phối cột vật lý, chỉ trả năm khi **mọi** năm được nêu trùng đúng tập năm có nhãn và đúng một năm; ngược lại `unknown`.
  - `header_year_scopes` dùng `column_year`, chọn evidence là ô header thật sự nêu năm có nhãn; vẫn yêu cầu cột có ô dữ liệu.
- `backendV1/qnu/domains/knowledge/metadata.py`:
  - `_header_refs(entry, index)` — ref các ô header chi phối cột vật lý (theo `table_layout`, run-prefixed); target ô được cộng thêm các ref này, sửa P1.
  - `_mentions_year(text, year)` — so khớp năm theo ranh giới số trên **toàn văn** quote.
  - `_require_row_year_proof` — `data_year` cấp hàng phải được chứng minh bởi một ô **trong chính hàng** có tập năm có nhãn đúng `{year}` và quote chứa năm; sửa lỗ hổng hàng.
  - `_require_table_year_proof` — cho target ô/cột/hàng: năm cột lấy từ `column_year` của header chi phối; target ô được chấp nhận thêm năm có nhãn của chính ô đó; nếu tập năm xác định khác đúng `{year}` → `retrieval_metadata_invalid`; evidence phải có quote chứa năm ở đúng ô header chi phối hoặc chính ô nêu năm (chặn quote từ ô số lượng), sửa P2.
  - Kiểm tra chung cho các trường `*_year` dùng cùng phép khớp ranh giới số.
- **Áp dụng:** strict role chỉ ở `publication/automatic_metadata.preview` và `publication/service._register`; đường đọc `evidence.registered_bundle_hash`/`assert_pinned` giữ nguyên validate **không** strict — bản đã đăng ký vẫn mở và truy xuất bình thường.

## Rà soát tiếp DOCX/PDF (ngoài ba ca đã nêu)

- **DOCX:** tầng header chỉ đến từ dấu OOXML `w:trPr/w:tblHeader` (đọc ở `direct_docx.py:52-79`) và cờ Docling `column_header`/`row_header`. Hàng tiêu đề con không được đánh dấu **không** được suy đoán (giữ `unknown`) — đây là giới hạn có chủ đích, không phải lỗi nay sửa.
- **PDF scan (MinerU):** header chỉ từ `<th>` (`mineru_layout.py:95-114`); **PDF text/Docling:** LaTeX `\thead{...}`; `native_tables.py` không suy đoán header hoặc năm → bảng PDF native tiếp tục `unknown` năm.
- **Các dạng đã chặn thêm:** tiêu đề một tầng `2026-2027`/`2026-27`; tập nhiều năm; tiêu đề cha một năm không được phủ lên tiêu đề con nhiều năm; ô năm “ban hành/hiệu lực/ngày ký” không dùng làm năm dữ liệu; hàng chỉ được gán năm khi có ô nêu năm có nhãn trong hàng.
- **Regression mới** `backendV1/tests/unit/test_year_proof_949.py` (8 ca, dùng lại fixture 947/948): ô hợp lệ qua header chi phối; ô sai header bị từ chối; ô số lượng không chứng minh được năm (cột và hàng); hàng có ô “Mùa tuyển sinh 2027” được chấp nhận; tiêu đề cha một năm không đè tiêu đề con nhiều năm; header khoảng năm viết tắt/một tầng giữ `unknown`; tiêu đề cha nhiều năm không gán cho cột con.

## Kiểm thử cô lập

- **Red-first:** 8 ca viết trước, chạy đỏ đúng 5 lỗi dự kiến (P1, P2 cột, P2 hàng, tiêu đề con nhiều năm ×2) trên DB cô lập; sau sửa cả 8 ca xanh.
- **Batch trọng tâm** (949+947+948): **25 passed**, DB `qnu_v1_test_8d0e3fdb17704446`, đã dọn, exit 0.
- **Batch rộng 20 tệp** (unit + integration DOCX/metadata/publication/index/RAG): **265 passed / 710,92 giây**; receipt `{"database": "qnu_v1_test_05048a6608e3460e", "db_dropped": true, "legacy_sentinel_preserved": true, "pytest_exit": 0, "seconds": 719.59}`.
- **Ruff:** `All checks passed!` trên `metadata.py`, `table_year.py`, `test_year_proof_949.py`.

## Tương thích bản đã đăng ký

- Không sửa dữ liệu, chunk hay chỉ mục đang phục vụ; không re-index. Đường đọc không đổi độ chặt nên version cũ vẫn 200.
- **Điều kiện cần ghi nhận:** preview chặt hơn có thể làm `automatic_metadata_sha256` của một lượt compile thay đổi; client đang giữ sha cũ sẽ nhận `409 registration_metadata_changed` và phải mở lại hộp thoại đăng ký. Annotation thủ công gửi qua API đăng ký nay phải dẫn đúng ô header chi phối (cột), ô nêu năm có nhãn trong hàng (hàng) hoặc chính ô/header hợp lệ (ô).

## E2E Qwen thật trong collection mới

- Restart dev stack lúc 20:53–20:54 để nạp `metadata.py`/`table_year.py` mới (mtime 20:41); API `uvicorn` + worker ARQ 27 hàm + FE V2. Trợ lý `ast_6c87cbb43c6b`, provider `prv_902ce43408bb` (`qwen3.8-27b-q4`), collection mới `col_cf4c14e7c49d`.
- Hai nguồn: DOCX cũ `src_3734e1987c59`/`ocr_00e09488f417` (`sha e975e03599d0`, 37.226 byte) và DOCX gộp ô thật `src_c351a75b9b0b`/`ocr_f939e5e08866` (`sha 0760ca0707b0`, 37.251 byte).
- Sửa `95→157` tại `ev_p001_b006_c03_02` (version 0→1); compile `cmp_8c42e954e2ab`/`cmp_f906f89488d1`; đăng ký `cdoc_a9023e6a568e`/`cver_eb40b794a39c` (bundle `71b34773675f…`) và `cdoc_701c6fbc9cdd`/`cver_56547c7c1340` (bundle `66f9a7cc4c16…`), **4 annotation mỗi bản**; submit `rsub_177bf1c5498e`/`rsub_2fa691a58ac8`; duyệt `pdec_70f4a0752b85`/`pdec_768b4f7eb315`; xuất bản `pdec_3c16738338a1`/`pdec_97085736ee7c`.
- Annotation năm đã phát hành: bản cũ `table:ocr_00e09488f417:ev_p001_b006:column:2` = `data_year 2027`, chứng cứ `…c00_02`; bản mới `column:1` = `2026` chứng cứ `…c01_00`, `column:2` = `2027` chứng cứ `…c01_01`. Preview strict mới **không loại** annotation hợp lệ nào (P1 đã đúng trên luồng thật).
- Index **tự động** `idx_6c08b4028467` generation 2, **15 chunk**, `completed`; readiness `ready` cả hai version; `runs_in_collection=2`; script **không** gọi `POST /indexing-runs`.
- Năm câu hỏi, **mỗi ca một lượt, mỗi ca một hội thoại riêng**, ghi lần đầu, không gửi lại:

| Ca | Kết quả lần đầu | Lọc đã resolve | Token (prompt/completion) | Thời gian | Dẫn chứng ô |
|---|---|---|---|---|---|
| `new_2027` — “chỉ tiêu năm 2027 ngành Khoa học dữ liệu?” | `answered`: “Khoa học dữ liệu — Chỉ tiêu tuyển sinh / Chỉ tiêu năm 2027: **47** [E2]” | `data_year: 2027`, 3 chunk đủ điều kiện | 2448 (2328/120) | 8,08 giây (trace 6344 ms) | `E2:r2:k2`; source_cells gồm header `…c01_01`, chủ thể `…c00_00`, giá trị `…c02_02`; version/publication khớp; **31 không bị dẫn** |
| `new_2026` — “chỉ tiêu năm 2026 ngành Khoa học dữ liệu?” | `answered`: “Khoa học dữ liệu — Chỉ tiêu tuyển sinh / Chỉ tiêu năm 2026: **31** [E1]” | `data_year: 2026`, 1 chunk đủ điều kiện | 2150 (2040/110) | 6,87 giây (5500 ms) | `E1:r2:k1`; header `…c01_00`, giá trị `…c02_01`; **47 không bị dẫn** |
| `old_ai_2027` — DOCX cũ, ngành Trí tuệ nhân tạo | `answered`: “Trí tuệ nhân tạo — Chỉ tiêu năm 2027: **157** [E1]” | `data_year: 2027`, 3 chunk | 2329 (2261/68) | 6,58 giây (5250 ms) | `E1:r3:k2`; header `…c00_02`, giá trị `…c03_02` (đã sửa `157`); version/publication khớp |
| `old_httt_2027` — DOCX cũ, ngành Hệ thống thông tin | `answered`: “Hệ thống thông tin — Chỉ tiêu năm 2027: **120** [E1]” | `data_year: 2027`, 3 chunk | 2328 (2260/68) | 6,71 giây (5375 ms) | `E1:r2:k2`; header `…c00_02`, giá trị `…c02_02` |
| `old_ai_2030` — năm **không có** trong tài liệu | `insufficient_evidence`/`no_match` (từ chối trung thực) | `data_year: 2030`, **0 chunk** đủ điều kiện | không gọi model | 1,63 giây (312 ms) | không dẫn ô; không mượn 157/120/95/145/31/47 |

- **Tương thích bản cũ 947 (live):** GET version + draft của `cver_2a8d009a487c` đều **200**; `retrieval_metadata` không đổi; draft chứa `157` — bản đã đăng ký trước các sửa 948/949 vẫn mở và truy xuất bình thường.
- **Ghi nhận về yêu cầu xác nhận Qwen thật:** phiên 948 đã chạy Qwen thật và xác nhận **31/47** (journal 948); lần chạy hôm nay sau khi sửa 949 **tái xác nhận đúng 31/47** với annotation và ô dẫn chứng như bảng trên.

## Trạng thái và việc tiếp theo

- Đạt: 8 unit mới + 25 batch trọng tâm + 265 batch rộng + Ruff sạch + E2E 5/5 theo tiêu chí + compat 947; index tự động `ready`; không re-index; không đổi giá trị mặc định retrieval/prompt; không commit/push.
- Giới hạn: full backend suite **NOT RUN** (hai tiến trình pytest cũ PID 18888/22164 treo từ phiên trước, không dùng được; baseline lịch sử **FAIL 4/1627** phiên 928 giữ riêng); XLSX ngoài phạm vi; bảng PDF native và tầng header con không được đánh dấu vẫn `unknown` (đúng chủ đích); F13 và Q09 502 phiên 946 vẫn mở (Q09 đã truy trace: `duplicate` một ID hợp lệ trong `statements[0].evidence_ids`, không có ID ngoài tập — xem mục bổ sung), không liên quan sửa này. `NOT RUN ≠ PASS`; token PASS không đồng nghĩa nội dung đúng.
- Việc tiếp theo (chờ người dùng): rà diff và quyết định commit; nếu mở rộng, cân nhắc đường nhập metadata thủ công cho bảng không dấu header và bổ sung ca XLSX.

## Bổ sung cùng phiên — Truy trace Q09 502 (2026-11-12)

- **Nguồn đã đọc:** hai tệp phản hồi của harness `qnu_e2e_946_live_r1_Q09.json` và `qnu_e2e_946b_live_r1_Q09.json` (HTTP 502, `code: answer_citation_invalid`, `errors: null`, correlation `req-dfff9b831851` / `req-0d9d22cf238f`) và bản ghi audit `workspace_events` của DB dev (`action = answer.validation_failed`), đọc read-only, không in DSN/secret.
- **Kết quả:** toàn DB dev có đúng **2** biến cố `answer_citation_invalid`, tại 18:41:38 và 18:43:55 giờ địa phương; cả hai cùng dạng `issues = [{"path": ["statements", 0, "evidence_ids"], "type": "duplicate"}]` — **không có** bất kỳ issue `not_allowed` nào. Prompt v28, 3954 prompt token, 118/119 completion token, `finish_reason: stop`, `max_output_tokens: 32768`; output sha256 `251e821934126dd4…` và `fb3e0d01a8ab6b7f…`; `answer_id` `ans_b3b63299e7f54823adc265f136703ac8` và `ans_3f41a50c64c740bd9388d3fbcbb3a62a`.
- **Kết luận:** model **không dẫn ID ngoài tập evidence**; nó **lặp lại một ID hợp lệ** (alias E*) trong danh sách của statement 0 nên guard `parse_answer` từ chối theo hợp đồng `duplicate` (`qnu/domains/rag/answer/drafting.py`, nhánh `len(set(evidence_ids)) != len(evidence_ids)`).
- **Giới hạn bằng chứng:** sự kiện chỉ lưu path/type và sha256 output — không lưu văn bản model hay danh sách ID — nên **không thể nêu alias cụ thể** đã bị lặp từ bản ghi hiện có; muốn xác định cần ghi thêm alias ở lần lỗi sau (alias E* không phải nội dung nguồn, an toàn) hoặc chạy lại có kiểm soát — **chưa thực hiện**, không retry-to-green.
- **Đề xuất (chưa làm, chờ duyệt):** dedupe giữ thứ tự trong `parse_answer` trước khi kiểm `not_allowed` (không đổi tập chứng cứ, không hạ guard ID lạ) kèm regression test; hoặc siết prompt yêu cầu mỗi ID xuất hiện một lần mỗi statement. Không thay đổi mã, guard hay ngưỡng trong phiên này.
- **Cập nhật 2026-11-12 (phiên 950):** người dùng duyệt mục 1 và đã triển khai — dedupe giữ thứ tự trong `parse_answer`, `test_citation_dedupe_950.py` đỏ-trước 3 ca rồi xanh, Q09 live 200 `answered`; xem [nhật ký 950](2026-11-12_phien_950_dedupe_evidence_id.md). Mục 2 và mục 3 vẫn chưa làm.
- **Đính chính:** các câu “citation ngoài tập evidence” trong nhật ký 945/946 và snapshot 945 đã được sửa theo bằng chứng trên. F13 vẫn là hạng mục riêng, chưa sửa.

Lệnh kiểm chứng chính:

```bash
# từ backendV1/ — DB cô lập tự tạo/xóa, không dùng DB ứng dụng
set -a && . ../.env && set +a && MSYS_NO_PATHCONV=1 PYTHONIOENCODING=utf-8 \
  uv run python scripts/run_isolated_tests.py -q tests/unit/test_year_proof_949.py

set -a && . ../.env && set +a && MSYS_NO_PATHCONV=1 PYTHONIOENCODING=utf-8 \
  uv run python scripts/run_isolated_tests.py -q \
  tests/unit/test_year_proof_949.py tests/unit/test_table_year_scope_947.py \
  tests/unit/test_vertical_merge_year_948.py

# Batch rộng 20 tệp unit + integration (metadata/publication/index/RAG)
set -a && . ../.env && set +a && MSYS_NO_PATHCONV=1 PYTHONIOENCODING=utf-8 \
  uv run python scripts/run_isolated_tests.py -q \
  tests/unit/test_year_proof_949.py tests/unit/test_table_year_scope_947.py \
  tests/unit/test_vertical_merge_year_948.py tests/unit/test_automatic_metadata_896.py \
  tests/unit/test_contextual_scope_790.py tests/unit/test_multitier_table_941.py \
  tests/unit/test_table_row_attribution_944.py tests/unit/test_fact_attribution_946.py \
  tests/unit/test_dynamic_metadata_880.py tests/unit/test_rag_policy_metadata_672.py \
  tests/unit/test_index_chunking_647.py tests/unit/test_rag_table_siblings_935.py \
  tests/unit/test_table_context_769.py tests/unit/test_hybrid_fusion_938.py \
  tests/unit/test_unselectable_prose_941.py tests/integration/test_automatic_metadata_896.py \
  tests/integration/test_publication_646.py tests/integration/test_answers_api_648.py \
  tests/integration/test_hybrid_655.py tests/integration/test_index_api_647.py

uv run ruff check qnu/domains/knowledge/metadata.py \
  qnu/domains/knowledge/compilation/table_year.py tests/unit/test_year_proof_949.py

# E2E (dev stack 20:54, provider prv_902ce43408bb):
python "$TEMP/qnu_e2e_948_merged.py" all
```
