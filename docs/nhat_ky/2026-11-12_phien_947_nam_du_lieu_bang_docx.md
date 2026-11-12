# Phiên 947 — Năm dữ liệu theo cột header bảng DOCX: từ metadata phát hành đến dẫn chứng hội thoại

- **Yêu cầu / giả định.** Sửa tận gốc lỗi năm dữ liệu bảng DOCX trong Backend V1, từ `compilation.supplement` qua publication, chunk chỉ mục, lọc truy xuất đến dẫn chứng hội thoại. Tái hiện lỗi bằng regression trước khi sửa; lần theo `automatic_entries` → `automatic_metadata` → `build_chunks` → `metadata_chunk_ids`; xác định năm thiếu ở khâu nhận diện, kiểm tra dẫn chứng hay gắn vào chunk. Khi header cột nêu rõ năm dữ liệu (ví dụ “Chỉ tiêu năm 2027”), gắn năm vào đúng phạm vi cột/ô bằng quan hệ header–ô sẵn có (kể cả header nhiều tầng, ô gộp); giữ dẫn chứng header và ô dữ liệu của bản đã xuất bản. Bảng nhiều năm phải chọn đúng cột năm; giữ `unknown` khi nguồn thiếu/mâu thuẫn; năm trong tên tệp, ngày ký, đoạn giới thiệu rời rạc **không** đủ gắn cho cả bảng. Giữ nguyên bộ lọc phạm vi, numeric guard, citation guard và luồng index tự động; không thêm lượt gọi LLM, không tăng `top_k`/ngân sách ngữ cảnh để bù chunk bị lọc; không đổi dữ liệu phục vụ hiện hữu. Kiểm thử: bảng một năm, bảng hai năm hai giá trị khác nhau, header nhiều tầng gộp ô, cột không rõ năm; lọc giữ đúng ô, loại sai năm, dẫn chứng truy đúng header và ô nguồn. E2E Qwen thật trong collection mới: upload DOCX → chuẩn bị nội dung → sửa `95`→`157` bằng API rà soát chuẩn → duyệt/phát hành → chờ index tự động `ready` → hỏi qua `/turns`, **đúng một lần mỗi ca**, ghi lần đầu; không retry để làm xanh, không nới assertion/guard, `NOT RUN` không phải `PASS`.

## Nguyên nhân

- Phiên 946 đã chứng minh bản văn đã sửa được phục vụ, nhưng câu hỏi DOCX trả `insufficient_evidence`/`model_abstained`: catalog scope đã resolve `data_year: 2027` nhưng `metadata_eligible_chunks: 1` — chỉ còn đoạn giới thiệu; chunk bảng `ich_321aa7497a45` bị loại vì **không có metadata năm**, `units: []`.
- Năm **có** trong ô header (`Chỉ tiêu năm 2027`, `ev_p001_b006_c00_02`) nhưng khâu nhận diện chỉ đọc mẫu “năm …” trên văn bản nguồn và gắn vào target **document/section/table**, chưa có khái niệm target **cột**. Vì vậy năm không được phát hành vào `retrieval_metadata` của phiên bản, không vào chunk, và bộ lọc năm loại oan chunk bảng. Lỗi nằm ở **nhận diện/gắn phạm vi metadata**, không ở parser, retrieval hay prompt.
- Kiểm tra dẫn chứng lúc trả lời chỉ nhận ref của ô đích; quan hệ ô dữ liệu ↔ ô header cùng cột chưa được mở nên không thể dẫn header làm căn cứ.

## Sửa gốc

- `backendV1/qnu/domains/knowledge/compilation/table_year.py` (mới): detector chỉ dùng **hình học và nhãn**. `_header_rows` lấy các hàng đầu có ô được đánh dấu header; `_covering` tôn trọng `col_span`; `_year` chỉ nhận đúng **một** năm có nhãn dữ liệu (`năm`, `năm dữ liệu`, `niên độ`), loại vai trò `ban hành/hiệu lực/ký/ngày/phát hành` và ngày `d/m/yyyy`; cột phải có ô dữ liệu. Trả `{table, column, year, evidence_citation, evidence_quote}` — không dùng tên tệp, ngày ký hay đoạn giới thiệu.
- `compilation/supplement.py`: thêm ứng viên **cấu trúc** `data_year` từ `header_year_scopes`, target `table:<citation>:column:<c>`; `_proposal_values(..., structural=True)` chỉ nhận khi chính quote header chứa năm. Các nhánh scope document/section/row cũ giữ nguyên.
- `knowledge/metadata.py`: nhánh target cột trả ref của bảng + **mọi ô phủ cột** (kể cả ô gộp), `validate_annotations` chấp nhận grammar `table:(.+):column:(\d+)`, `chunk_metadata` lọc annotation theo target của chunk.
- `knowledge/index/chunking.py`: chunk bảng khai báo thêm target cột (`:column:c`) để annotation cột được gắn vào chunk; `CHUNKER_VERSION` giữ `qnu.published-chunks/v6` (dữ liệu chunk không đổi định dạng).
- `rag/answer/table_selection.py` lên `qnu.rag.table-selection/v2`: `requested_data_years(metadata_filter)` đọc năm yêu cầu từ scope đã resolve; `_year_scopes` dựng phạm vi năm từ chứng cứ **cột/hàng/ô** của `structure.retrieval_metadata`; ô chưa chứng minh năm vẫn chọn được; `select_catalog(..., data_years=...)` thu hẹp sau bước chủ thể và trả `requested_years`/`year_omitted_cells`.
- `rag/answer/packing.py`: truyền `data_years=requested_data_years(options.get("metadata_filter"))` vào `select_catalog`; với trợ lý catalog, `service.py` đã đưa scope resolve dạng `{"any_of": [...]}` nên bộ lọc năm tới đúng chỗ. Không tăng `top_k`, không đổi ngân sách, không thêm lượt gọi model.
- Dẫn chứng: `cells.py` sẵn có dựng `source_cells` gồm ref ô dữ liệu, ô chủ thể và ô header cột; với annotation cột mới, proof của ô `E1:r3:k2` chứa cả `…c00_02` (header năm) và `…c03_02` (giá trị) — không cần nới guard.

## Kiểm thử cô lập

- Regression mới `backendV1/tests/unit/test_table_year_scope_947.py` (7 ca): một năm + chunk annotation + `units`; năm chỉ ở đoạn giới thiệu **không** tạo scope; bảng hai năm (2027/2028) resolve filter và `select_catalog(data_years={2027})` giữ `95/120`, loại `100/90`; header nhiều tầng gộp `col_span=2`; header mơ hồ/vai trò → unknown; hàng đầu không đánh dấu header → không scope; chứng cứ chéo cột bị từ chối `retrieval_metadata_invalid`. Chạy đỏ trước khi sửa, sau sửa **7 passed**.
- Bộ unit liên quan (18 tệp) trên DB cô lập: **265 passed**; Ruff sạch trên các tệp đã sửa.
- Batch integration 9 tệp (metadata, chunking, publication, answers API, PDF-text liên quan): **98 passed / 869,93 giây**, receipt `{"database": "qnu_v1_test_11a1de49a14349fc", "db_dropped": true, "legacy_sentinel_preserved": true, "pytest_exit": 0, "seconds": 882.31}`.
- PDF text không hồi quy: `tests/integration/test_auto_extraction_710.py` **14 passed / 47,48 giây**, receipt `{"database": "qnu_v1_test_33cac99af9e441de", "db_dropped": true, "legacy_sentinel_preserved": true, "pytest_exit": 0, "seconds": 56.33}`.
- Lệnh (từ `backendV1/`): `set -a && . ../.env && set +a && MSYS_NO_PATHCONV=1 PYTHONIOENCODING=utf-8 uv run python scripts/run_isolated_tests.py -q <tệp>`; DB ứng dụng không bị chạm. Full backend suite **NOT RUN** (hai tiến trình pytest cũ PID 18888/22164 còn treo, không dùng được; baseline lịch sử **FAIL 4/1627** phiên 928 giữ riêng).

## E2E Qwen thật trong collection mới

- Dev stack restart lúc 19:42 (API `uvicorn` mới, worker ARQ 27 hàm) để nạp mã mới; không đụng tiến trình khác. Trợ lý dùng `chat_provider_id=prv_902ce43408bb` (`qwen3.8-27b-q4`), collection `col_3eb45a408346`.
- Luồng: source DOCX `ke_hoach_12_kh_dt_chi_tieu_2027.docx` → OCR `ocr_3ab24a5ecd04` → soát/chuẩn bị → **sửa `95`→`157`** tại unit `ev_p001_b006_c03_02` bằng API rà soát văn bản (version 0→1, SHA `896a1812423a`→`7f09d23e7f92`) → compile `cmp_936ce250dd4c` → đăng ký `cdoc_3922cc33c264`/`cver_2a8d009a487c` (bundle `a2a27474a694…`) → duyệt `pdec_65b8464dc11d` → xuất bản `pdec_a6f521335b85`.
- Phiên bản đã phát hành có annotation `table:ocr_3ab24a5ecd04:ev_p001_b006:column:2` = `data_year: 2027`, chứng cứ **`ocr_3ab24a5ecd04:ev_p001_b006_c00_02`** (“Chỉ tiêu năm 2027”); draft đã phục vụ chứa `157`, không còn `95`.
- Index **tự động** `idx_802830536f70` generation 1, **8 chunk**, `ready`; `runs_in_collection=1`; script không hề gọi `POST /indexing-runs` (`manual_index_request_issued_by_script: false`).
- Ba câu hỏi, **mỗi ca một lượt, mỗi ca một hội thoại riêng**, không gửi lại:

| Ca | Kết quả lần đầu | Lọc đã resolve | Token (prompt/completion) | Thời gian | Dẫn chứng ô |
|---|---|---|---|---|---|
| `ai_2027` — “chỉ tiêu năm 2027 ngành Trí tuệ nhân tạo?” | `answered`: “Trí tuệ nhân tạo — Chỉ tiêu năm 2027: 157 [E1]” | `data_year: 2027`, 2 chunk đủ điều kiện | 2193 (2128/65) | 4,34 giây | `E1:r3:k2`; source_cells gồm header `…c00_02`, `…c00_00`, chủ thể `…c03_00`, giá trị `…c03_02`; version/publication dẫn đúng bản đã phát hành |
| `httt_2027` — “chỉ tiêu năm 2027 ngành Hệ thống thông tin?” | `answered`: “Hệ thống thông tin — Chỉ tiêu năm 2027: 120 [E1]” | `data_year: 2027` | 2209 (2127/82) | 4,24 giây | `E1:r2:k2`; `…c00_02`, `…c02_00`, `…c02_02`; version/publication khớp |
| `ai_2030` — năm **không có** trong tài liệu | `insufficient_evidence`/`no_match` (từ chối trung thực) | `data_year: 2030`, **0 chunk** đủ điều kiện | không gọi model (188 ms) | 0,19 giây | không dẫn ô; không số nào của 2027/2026 bị mượn |

- So sánh ca cũ phiên 946 (`col_042b8acbb9bb`): cùng câu hỏi AI 2027 trả `insufficient_evidence`/`model_abstained`, `metadata_eligible_chunks: 1`, chunk bảng thiếu `units`; ca mới trả `157` với `metadata_eligible_chunks: 2` — chứng minh sửa đúng tầng metadata, không phải đổi retrieval/prompt.
- **Sự cố harness, ghi trung thực:** lần chạy đầu dừng ở bước tạo trợ lý vì API `/modelops/providers` trả `kind: null` còn script lọc cứng `kind == "chat"`; **chưa câu hỏi nào được gửi**, pipeline và index đã hoàn tất. Sửa riêng bước chọn provider trong script (ưu tiên `kind == "chat"`, fallback provider duy nhất `qwen3.8-27b-q4`), chạy tiếp từ trạng thái đã lưu với đúng collection/index đó; ba câu hỏi chỉ được gửi một lần sau đó.
- **Sửa cách chấm, không sửa câu trả lời:** bộ chấm ban đầu đòi `version/publication` cho cả ca `ai_2030`, nhưng một lần từ chối đúng không thể có dẫn chứng. Quy tắc cho ca vắng năm được viết lại theo đúng tiêu chí nghiệm thu (resolve năm 2030, 0 chunk, không mượn số, không chọn ô); **chấm lại đúng lượt đã ghi**, không gửi lại câu hỏi, không đổi dữ liệu lần đầu. Hai ca bảng vẫn giữ nguyên bộ kiểm tra dẫn chứng/version chặt như trước.

## Trạng thái và việc tiếp theo

- Đạt: regression đỏ→xanh, batch cô lập và PDF-text xanh, E2E thật 3/3 theo tiêu chí, index tự động `ready`, dẫn chứng header + ô dữ liệu + đúng version/publication. Không re-index collection cũ, không đổi giá trị mặc định retrieval/prompt, không commit/push.
- Giới hạn: detector **chỉ** gắn năm khi header được đánh dấu nêu đúng một năm dữ liệu; hàng/nhãn năm trong câu văn, tên tệp, ngày ký vẫn để `unknown` (đúng chủ đích). Chưa E2E ca header nhiều tầng gộp ô và cột unknown ngoài đơn vị. XLSX ngoài phạm vi. F13 và Q09 502 của phiên 946 vẫn mở, không liên quan sửa này. Full backend suite **NOT RUN**; `NOT RUN ≠ PASS`, token PASS không đồng nghĩa nội dung đúng.
- Việc tiếp theo (chờ người dùng): rà diff và quyết định commit; nếu mở rộng, cân nhắc phạm vi năm theo **hàng** cho bảng dọc và bổ sung ca E2E header gộp ô.

Lệnh kiểm chứng chính:

```bash
# từ backendV1/ — DB cô lập tự tạo/xóa
set -a && . ../.env && set +a && MSYS_NO_PATHCONV=1 PYTHONIOENCODING=utf-8 \
  uv run python scripts/run_isolated_tests.py -q \
  tests/unit/test_table_year_scope_947.py
uv run ruff check qnu/domains/knowledge/compilation qnu/domains/knowledge/index/chunking.py \
  qnu/domains/knowledge/metadata.py qnu/domains/rag/answer/table_selection.py \
  qnu/domains/rag/answer/packing.py tests/unit/test_table_year_scope_947.py
```
