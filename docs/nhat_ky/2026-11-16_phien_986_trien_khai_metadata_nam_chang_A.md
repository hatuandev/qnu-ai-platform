# Phiên 986 — Triển khai metadata năm và thời gian (Chặng A)

Triển khai [kế hoạch metadata năm và thời gian](../ke_hoach/2026-11-16_metadata_nam_va_thoi_gian_v1.md) theo thứ tự A → B → C. Phiên này hoàn tất **Chặng A** trên `backendV1/`; mã chưa commit, không reindex, không đổi bản phát hành đang phục vụ.

## Yêu cầu và giả định

- Số `1800` trong dòng liên hệ không được thành `data_year`; sửa theo cụm nguồn + dấu hiệu cấu trúc, không ngoại lệ riêng cho số/ngành/tên tệp.
- Bảng có tiêu đề năm nhưng thiếu header native phải dùng `typed_header`/`multitier_header` hiện có; ô năm đứng riêng chỉ có hiệu lực khi cấu trúc xác nhận (multitier, gộp cột, có hàng dữ liệu).
- Cùng kết quả cấu trúc cho bước đề xuất và `validate_annotations`; bằng chứng trỏ đúng ô năm và nhãn con; không sửa OCR gốc.

## File sửa

- `backendV1/qnu/domains/knowledge/compilation/supplement.py` — `RULE_VERSION` v3; `DATA` chỉ nhận năm hợp lý 19xx/20xx; thêm `NUMERIC_CLUSTER`, `CONTACT_LABEL` và `_data_years` loại năm nằm trong cụm số điện thoại/mã hoặc sau nhãn liên hệ.
- `backendV1/qnu/domains/knowledge/compilation/table_year.py` — thêm `bare_year`, `column_year_proof` (`allow_bare_year`); `header_year_scopes` fallback sang `multitier_header` khi thiếu header native, vẫn đòi hàng dữ liệu và một năm duy nhất.
- `backendV1/qnu/domains/knowledge/metadata.py` — `_header_refs` và `_require_table_year_proof` dùng chung `header_rows` hoặc `multitier_header`; bằng chứng cột gồm ô năm gộp; bỏ import không dùng.
- Test: `tests/unit/test_automatic_metadata_896.py` (+2 ca hotline, gồm đề xuất model cũ bị kiểm lại), `tests/unit/test_table_year_scope_947.py` (+3 ca multitier/mâu thuẫn cha–con/bảng thiếu tiêu đề), `tests/unit/test_year_proof_949.py` (+1 ca năm trong ô dữ liệu chỉ scope đúng ô). Không sửa `table_layout.py`, `chunking.py`, `hybrid.py` và các test được bảo vệ.

## Lệnh thật và kết quả

- `uv run pytest tests/unit/test_automatic_metadata_896.py tests/unit/test_table_year_scope_947.py tests/unit/test_vertical_merge_year_948.py tests/unit/test_year_proof_949.py -q -p no:cacheprovider` → **42 passed in 1.84s**. PASS.
- `uv run ruff check` trên 6 tệp thay đổi → **All checks passed**. PASS.
- Probe chỉ đọc trên bundle đã lưu (dev): sau sửa **PREVIEW_IMPLAUSIBLE []**, 21 annotation `data_year` (20 scope cột + 1 đoạn), toàn bộ replay `strict_roles=True` hợp lệ; chỉ còn 1 rule hit `ocr_7199f52c20db:ev_p001_b018` = 2025, không cụm số/không hotline (hợp lệ).
- Probe bảng: 24 bảng parsed, **0 header native, 3 multitier, 5 typed, 16 chưa phân giải**; đúng **3 bảng có ô năm**, sinh 20 scope: hai bảng 28×9 (cột 3–5 = 2024, 6–8 = 2025, ô gộp `2024`/`2025` span 3) và bảng 30×11 (cột 3–6 = 2023, 7/8/10 = 2024, ô gộp span 4; cột 9 không đủ hàng dữ liệu nên không scope).
- Khác biệt số liệu: kế hoạch ghi "8 bảng thiếu tiêu đề năm", probe hiện tại chỉ thấy 3 bảng chứa ô năm; phần còn lại là 16 bảng chưa phân giải không có ô năm hoặc thiếu cấu trúc. Đây là khác biệt cách đếm ở báo cáo khảo sát, không phải bảng bị bỏ sót.

## Chặng B — Lịch và hạn theo sự kiện

### B1–B2 — Hợp đồng và trích bằng quy tắc

- `backendV1/qnu/domains/knowledge/metadata.py` — thêm `EventMoment` (ngày đầy đủ hoặc thiếu năm/tháng, giữ `time`), `RelativeDeadline` (value/unit/from_event, không tự quy đổi ngày), `EventValue` (ba kind chuẩn, nhãn gốc, `moment`/`window_start`/`relative` loại trừ nhau, `intake/audience/method/clause/note/supersedes`), `MetadataValues.events` (tối đa 20) và `event_proved` kiểm nhãn + mọi mốc + scope trên hợp các đoạn trích; `validate_annotations(strict_roles=True)` kiểm từng sự kiện; sự kiện gắn `document` bị từ chối. Sửa lỗi shadowing `date` bằng `from datetime import date as Date`.
- `backendV1/qnu/domains/knowledge/compilation/supplement.py` — trích sự kiện theo dòng/`;`: nhãn đăng ký/thi – kết quả, mốc đầy đủ/thiếu năm/khoảng mở, connector `đến|tới|hết|-`, `từ` cho mốc mở đầu, `gia hạn|kéo dài|thay thế` giữ trong `note`, thời hạn tương đối chứng minh bằng đúng đoạn trích; nhãn `Đợt …` không bị biến thành thuộc tính tùy ý. `RULE_VERSION` v4.
- `backendV1/qnu/domains/knowledge/publication/automatic_metadata.py` — gộp sự kiện theo `(target, kind, intake, audience, method)`, dedupe theo digest, báo `conflicts` khi hai lịch khác giờ không có dấu hiệu gia hạn/thay thế; nguồn không bị sửa và kết quả lặp lại ổn định.
- Test: `tests/unit/test_event_schedule_986.py` (13 ca) phủ đủ điều kiện đạt của B: hai đợt hạn khác nhau, một đợt có thi + kết quả, thiếu năm giữ độ chính xác, khoảng vắt năm, gia hạn không mâu thuẫn, thời hạn tương đối không quy đổi, ngày chỉ nằm trong căn cứ pháp lý không thành sự kiện, hai lịch xung đột giữ cả hai + báo conflict, event `document` bị từ chối, event model lưu cũ được kiểm lại theo chính dẫn chứng, và `confirm` gộp đúng target.

### B3 — Đưa sự kiện vào hợp đồng LLM có cấu trúc

- `supplement.py` — `EventProposal` đặt trước `SupplementPart`; `SupplementPart.events` (tối đa 40); `owned_events(part, documents)` chỉ giữ đề xuất có `quote` nằm trong văn bản owned của đúng `citation`; prompt v3 mô tả hợp đồng sự kiện (ba kind, một cách biểu diễn thời gian, giữ nhãn gốc, `note/supersedes` cho gia hạn, không tính ngày từ `relative`, không dùng scope `document`).
- `backendV1/qnu/domains/knowledge/compilation/segments.py` — `PROMPT_VERSIONS` của supplement/selective lên **v3**; `parse_segment_draft` từ chối `citation` của sự kiện ngoài nguồn phần (`compilation_citation_invalid`) và trả `model_dump(mode="json")` để ngày serialize được vào draft JSON.
- `backendV1/qnu/domains/knowledge/compilation/execution.py` — gộp `draft["events"]` khi ghép các phần con; `_run_leaf` lọc `owned_events` trước khi lưu; `refinement.node_content` giữ nguyên khóa `events` nhờ spread `**draft`.
- Test: `tests/unit/test_supplement_events_llm_986.py` (9 ca): parse hợp lệ + serialize ngày; từ chối citation ngoài phần và kind lạ; prompt/schema cùng version v3 và cùng chứa hợp đồng; `owned_events` chỉ giữ quote thuộc nguồn owned; event model thành annotation `proposed` đúng đoạn; event không chứng minh được thì không lưu; chuỗi `attach → preview` trả sự kiện đúng đoạn.

### Quyết định đường đọc bản cũ

Bản cũ không có `events` vẫn đọc nguyên trạng: `SupplementPart.events` mặc định rỗng, `MetadataValues.events` là optional, `preview` dùng `values.get("events", [])`, còn quy tắc sự kiện luôn được trích lại từ nguồn khi preview. Bản đã xuất bản giữ nguyên `retrieval_metadata` đã lưu; không backfill, không reindex.

### Lệnh thật và kết quả

- `uv run pytest tests/unit/test_supplement_events_llm_986.py tests/unit/test_event_schedule_986.py tests/unit/test_automatic_metadata_896.py -q` → **33 passed in 1.96s**. PASS.
- `uv run pytest` nhóm 17 tệp biên soạn/metadata liên quan (compilation, compiler, publication nhanh, rag policy metadata) → **176 passed in 9.68s**. PASS.
- `uv run ruff check` 4 tệp thay đổi + test mới → **All checks passed**. PASS.
- `ruff format --check`: test mới và supplement/segments đã chuẩn; `execution.py` còn lệch định dạng ở `_write_partial` — vùng này thuộc sửa đổi chưa commit có trước của người dùng, không định dạng lại ngoài phạm vi. NOT FIXED (có chủ đích).

## Trạng thái

- Chặng A: PASS (unit + Ruff + probe dữ liệu thật chỉ đọc). Chưa chạy model thật, chưa restart API/worker, chưa đăng ký lại metadata trên bản phát hành.
- Chặng B: PASS ở mức unit (B1–B3 + 9 + 13 ca sự kiện, 176 ca hồi quy, Ruff). Chưa chạy model thật để xác nhận LLM tuân hợp đồng sự kiện mới; chưa restart API/worker.
- Chặng C: bắt đầu sau mục này; bổ sung vào nhật ký khi hoàn tất.

## Chặng C — Tự lưu, lập chỉ mục và kiểm tra RAG

### C1 — Nối bản xem trước metadata vào FE V2

- `frontendV2/src/api/documents/{types,endpoints,requests,queries}.ts` — thêm `automatic_metadata_sha256` vào hai request; type `AutomaticMetadataPreview`, `RetrievalAnnotation`, `MetadataEvent`, `EventMoment`; endpoint `registration-metadata/{run_id}` và hook `useRegistrationMetadataQuery`.
- `frontendV2/src/components/knowledge/publication-dialog.tsx` — tải bản xem trước khi mở hộp thoại đăng ký; chỉ hiển thị mục nghiệp vụ có nghĩa (không lộ nhãn kỹ thuật); thời hạn tương đối hiển thị dạng "trong N ngày kể từ …" chứ không tự tính ngày; gửi sha khi tạo mới và khi thêm phiên bản; lỗi `registration_metadata_changed` tự tải lại bản xem trước và báo người dùng đối chiếu; nút Tiếp tục khóa khi chưa có bản xem trước; client cũ không gửi sha vẫn đăng ký được.
- Lệnh: `npx biome check` (phạm vi tệp sửa) PASS; `npx tsc --noEmit` PASS; `npm run build` PASS (chỉ cảnh báo chunk >500 kB có sẵn). Live UI **NOT RUN**: trình duyệt báo không kết nối được QNU SSO tại localhost:5085 khi mở `/dashboard`; không thử đăng nhập vì không được in thông tin đăng nhập. NOT RUN không phải PASS.

### C2 — Phạm vi truy vấn theo metadata đã kiểm chứng

Lỗ hổng xác định trước khi sửa: (1) `year_choices` bắt buộc chữ "năm/year" nên "điểm chuẩn 2025" không tạo phạm vi; (2) catalog intake chỉ lấy `values.intake`, bỏ sót intake chỉ nằm trong sự kiện nên "hạn đăng ký đợt 2" không lọc được; (3) chọn ô bảng chỉ thu hẹp theo năm, chưa thu hẹp theo đợt ở hàng/cột.

- `qnu/domains/knowledge/index/query_scope.py` — `VERSION` lên `qnu.catalog-scope/v3`. Năm trần chỉ thành phạm vi khi (a) đúng là năm có trong catalog đã đóng băng, (b) không đứng sau cụm đếm (`có/gồm/khoảng/hơn/gần/đạt/chừng`), (c) không dính ngày/khoảng/mã (`30/6/2025`, `2024-2025`, `2025.5`). Năm trần có mặt ở cả hai vai trò vẫn hỏi làm rõ; chỉ một vai trò thì chọn đúng vai trò. Catalog intake lấy thêm `events[].intake` để hiểu câu hỏi, nhưng intake chỉ có trong sự kiện không tự kích hoạt hỏi làm rõ khi câu hỏi không nhắc đợt (giữ nguyên hành vi cũ với catalog cấp đơn vị).
- `qnu/domains/knowledge/metadata.py` — `matches_metadata` khớp `intake` khi đơn vị có `values.intake` hoặc bất kỳ `events[].intake` trùng; đơn vị không có chứng cứ đợt vẫn không khớp filter đợt.
- `qnu/domains/rag/answer/table_selection.py` — `VERSION` lên `qnu.rag.table-selection/v3`; thêm `requested_intakes` (đọc cả `any_of`), chứng cứ intake theo hàng/cột/ô từ chính annotation của nguồn (gồm intake trong sự kiện); ô đã chứng minh khác đợt bị loại, ô chưa rõ đợt vẫn giữ; khi có phạm vi, nối danh sách qua trang chỉ ghép mảnh có chứng cứ khớp; trace thêm `requested_intakes`, `intake_omitted_cells`.
- `qnu/domains/rag/answer/packing.py` — truyền `intakes=requested_intakes(metadata_filter)` vào `select_catalog`.
- Test mới `tests/unit/test_intent_scope_986.py` (9 ca): năm trần có/không chữ "năm"; cụm đếm và hotline 1800 không thành năm; năm trần ở cả hai vai trò vẫn hỏi làm rõ; intake chỉ trong sự kiện tạo đúng filter và khớp/không khớp đơn vị; `matches_metadata` khớp intake đơn vị hoặc sự kiện; hai đợt trong sự kiện không ép hỏi làm rõ khi câu hỏi không nhắc đợt; `requested_intakes` đọc flat/any_of; chọn ô bảng giữ hàng đợt 2 + ô chưa rõ đợt, loại hàng đợt 1.
- Giữ nguyên có chủ đích: kết quả rỗng không mở rộng phạm vi (`metadata_chunk_ids=[]` → `status=no_match`); câu hỏi so sánh vẫn sinh disjunction theo từng phía; câu đếm (`có 2030 người`) vẫn không thành năm; phạm vi cố định vẫn thắng hoặc báo xung đột.
- Test cập nhật: `tests/unit/test_contextual_scope_790.py` đổi kỳ vọng version trace sang v3.

### Lệnh thật và kết quả (C2)

- `uv run pytest tests/unit/test_intent_scope_986.py -q` → **9 passed in 1.91s**. PASS (trước khi sửa: ImportError thiếu `requested_intakes`).
- `uv run pytest tests/unit/test_contextual_scope_790.py tests/unit/test_table_year_scope_947.py tests/unit/test_table_grounding_770.py tests/unit/test_vertical_merge_year_948.py tests/unit/test_event_schedule_986.py tests/unit/test_intent_scope_986.py -q` → **81 passed in 2.43s**. PASS.
- `uv run pytest tests/unit/test_answer_cache_956.py tests/unit/test_rag_clause_context_856.py tests/unit/test_rag_context_908.py tests/unit/test_rag_table_siblings_935.py -q` → **67 passed in 2.23s**. PASS.
- `uv run ruff check` trên 5 tệp nguồn/test → **All checks passed**. PASS. `ruff format` áp cho `table_selection.py` và test mới; `query_scope.py` giữ nguyên định dạng.
- Chưa chạy lại bộ 100 câu; chưa restart API/worker; chưa đăng ký lại metadata trên bản phát hành.

## Chặng C3 — E2E cô lập, đo live và ma trận nghiệm thu

Corpus cô lập `col_14ba3e802039` (workspace `ws_623614ba7fb8`, dev); không đụng collection cũ `col_af3ea7d6d5fb`. Hai PDF (OCR `ocr_66956c993bcf`, `ocr_a56d558068a0`) biên dịch vào một tài liệu `cdoc_d6f24d08c35e`; DOCX biên dịch thành `cdoc_5cc051c067a5`; PDF hỏng `ocr_2da1de6b36a7` dừng đúng `failed/pdf_invalid`. PDF v1 đăng ký `cver_930776967afd` rồi xuất bản; trước-đo dùng index gen2 `idx_c4935f4226ca` (354 chunk). Bản v2 `cver_19f06411e7b6` đăng ký qua đúng endpoint thêm phiên bản với `automatic_metadata_sha256=fea0353c…`, gửi lại cùng payload trả cùng version (`created=false`), gửi trùng lượt biên dịch bị chặn `409 compiled_run_registered`. Sau xuất bản, index gen3 `idx_d2ae72f52446` (354 chunk) `ready`.

Kết quả biên dịch và metadata (đo thật):

- PDF v2: `source_first` (không gọi chat model; `usage_tokens=null`); xem trước 92 annotation — 71 annotation thuộc tính nhãn/giá trị và 21 `data_year`, trong đó `2024×10, 2025×7, 2023×4`; `issued_year`/`effective_*`/sự kiện đều 0; thời gian xem trước 0,512 s. Số `1800` của hotline chỉ nằm ở thuộc tính “5. Số điện thoại liên hệ tuyển sinh”, không có trong trường năm; cờ `hotline_as_year=true` của helper đo là dương tính giả do tìm chuỗi `1800` trong toàn bộ annotation.
- DOCX: lượt `ai_supplement` thất bại `compilation_draft_invalid`, tự lùi `source_first` (ghi `compile_mode=source_first_fallback`, `usage_tokens=null`); xem trước 7 annotation — `issued_year=2026` từ dòng “Quy Nhơn, ngày 10 tháng 6 năm 2026”, 5 `data_year` (`2024×2, 2025×2, 2026×1`), 1 thuộc tính, 0 sự kiện; thời gian xem trước 0,131 s. Dòng “Thời gian nhận hồ sơ đợt 1: …” bị bắt thành thuộc tính thay vì sự kiện vì `EVENT_BOUNDARY` không khớp khi nhãn có hậu tố “đợt 1” — ghi nhận là lỗi cần xử lý riêng, chưa sửa trong C3.
- Nhóm LLM cho metadata: 0 nhóm, 0 lượt gọi ở cả hai tài liệu (quy tắc đã phủ hết ứng viên). Token do provider báo: không có (`null`); ước tính hệ thống: không đủ căn cứ để báo — ghi NOT MEASURED, không quy đổi thành mức tiết kiệm.

Bộ 14 câu sau (10 PDF + 4 DOCX) chạy trên cùng revision/cấu hình/chính sách tìm kiếm với 5 câu trước và 1 câu dữ liệu cũ; nhãn đáp án/phạm vi được chốt trước khi gọi model. Chấm tự động đối chiếu chuỗi có chuẩn hóa dấu thập phân `,`⇄`.` và gộp biến thể cùng một số; kết quả: trước 3/5, sau 11/14, dữ liệu cũ 0/1. Chấm tay theo đáp án đã đăng ký:

- Đạt: P1b (17.75 đúng ô), P3 (phân biệt ban hành 2026 với số liệu 2024/2025), P4 (20/5–20/6/2026, đợt 1), P6 (22/8/2026, đợt 2), P8/P9 (thiếu căn cứ đúng), D1 (15/6–30/6, không tự suy năm), D2 (“5 ngày làm việc” kèm mốc gốc), D4 (120).
- Sai nội dung: P1a trả 17.75 nhưng mở đầu bằng chỉ tiêu 262/258 và gọi đó là “điểm trúng tuyển chính thức”, đồng thời bịa “Đại học Quốc gia thành phố Hồ Chí Minh (QNU)”; P5 trả cửa sổ 16/7–28/7/2025 thay vì 01/6–30/6/2025; D3 nêu thêm “75” (cột Chỉ tiêu 2025) dưới nhãn chỉ có “Năm 2025”, dù 25.1 đúng.
- Không đạt do trạng thái/guard: P2 trước trả đúng 10.0/9.0, sau chuyển `insufficient_evidence/model_abstained`; P7 (ô bị mất) trả `502 answer_table_value_not_extractive` thay vì thiếu căn cứ; câu dữ liệu cũ trên collection cũ trả `502 answer_response_invalid`, chưa chứng minh được đường đọc dữ liệu cũ.
- Phạm vi/dẫn chứng: mọi câu PDF chỉ dùng tài liệu PDF, mọi câu DOCX chỉ dùng tài liệu DOCX; `metadata_filter` rỗng ở cả trước và sau với P2 (bộ lọc C2 không lọc quá tay); dẫn chứng P1b/P4/D1/D3 mở đúng đơn vị bảng/đoạn tương ứng.

Đối chiếu ma trận §6: (1) một năm có/không chữ “năm” — P1b đạt, P1a sai nội dung; (2) so sánh 2024/2025 — trước đạt, sau abstain; (3) ban hành 2026 + số liệu năm trước — P3 đạt; (4) hiệu lực và hạn đăng ký — P9/P4/P6 đạt, P5 sai cửa sổ; (5) hạn đợt 2 — P6 đạt; (6) hạn tương đối thiếu ngày bắt đầu — D2 đạt; (7) năm/hạn sai hoặc thiếu căn cứ — P8/P9 đạt, P7 lỗi guard; (8) đăng ký mới/thêm phiên bản — đạt ở API, **live FE V2 NOT RUN**; (9) dữ liệu cũ thiếu metadata — L1 lỗi 502, **chưa đạt**. Không chạy lại bộ 100 câu; không reindex diện rộng; bản phát hành/index cũ giữ nguyên.

Lệnh thật: kịch bản `%TEMP%\qnu_c3_e2e.py` các chặng `setup|poll|broken|documents|before|after|legacy|report` (gọi API thật, không chứa bí mật trong repo); chặng `report` chỉ đọc `%TEMP%\qnu_c3_results.json` và chấm lại, không gọi model. Không chạy Pytest cho C3.

Tồn đọng: DOCX chưa sinh sự kiện do hậu tố “đợt 1” sau nhãn; P1a/P2/D3/P5 là lỗi nội dung trả lời; P7/legacy là lỗi guard 502 tái diễn; live FE cho đăng ký/phiên bản và loại trừ bản chưa xuất bản **NOT RUN**; collection dev-admin cũ `col_7b9cca1f8106` còn chờ duyệt xóa.

## Trạng thái

- Chặng A: PASS (unit + Ruff + probe dữ liệu thật chỉ đọc).
- Chặng B: PASS ở mức unit; nhánh LLM/token chưa có số đo thật (C3 xác nhận 0 nhóm/0 lượt gọi trên hai tài liệu này).
- Chặng C1: PASS static (Biome/tsc/build); live UI NOT RUN.
- Chặng C2: PASS mức unit + Ruff; live chỉ quan sát gián tiếp qua C3 (`metadata_filter` rỗng, không lọc quá tay).
- Chặng C3: đã chạy E2E cô lập. API/đăng ký/metadata/index đạt; chất lượng trả lời hỗn hợp 9/14 đạt chấm tay (11/14 chấm tự động), 3 lỗi nội dung, 2 lỗi guard 502; bảng ma trận có 2 mục NOT RUN (live FE, loại trừ bản chưa xuất bản) và 1 mục chưa đạt (dữ liệu cũ). Không tuyên bố PASS toàn chặng.


