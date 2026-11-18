# Phiên 1015 — Chặng 4: hợp đồng trả lời eligibility tính sẵn từ bảng (closed-set facts)

## Yêu cầu

- Sau Chặng 1–3, người dùng duyệt **Chặng 4** của kế hoạch 4 chặng: backend
  **tính sẵn kết luận đóng (closed set)** từ bằng chứng bảng đã đóng gói; model
  chỉ diễn giải và trích dẫn. Mục tiêu: (a) câu phủ định (Q02/Q10/Q03), (b) câu
  liệt kê đầy đủ (Q11).
- Chặng 4 là thay đổi **thuần lớp trả lời**: không đổi dữ liệu nguồn, không
  biên dịch lại, không reindex, không đổi schema hay prompt của Chặng 1–3.
- Giữ quy ước từng chặng: triển khai, đo, báo cáo trung thực.

## Bối cảnh

- Corpus đo giữ nguyên từ Chặng 3: kho "Tuyển sinh 2026"
  (`col_279e00e8f7fb`, workspace `ws_623614ba7fb8`), tài liệu
  `cdoc_a17f6bb98d36`, bản xuất bản `cver_7dbc92d84d05`, index
  `idx_a88196a1f0ba` (generation 2, 184 chunk), trợ lý `ast_44fc63a77512`,
  API `:8002`.
- Trước chặng: prompt v37 đã có quy tắc tập không thứ tự và phản hồi phủ định
  theo danh sách, nhưng Q11 vẫn 5–6/8 (có lượt thêm ngành sai) hoặc abstain;
  Q02/Q10/Q03 chưa đạt phủ định ổn định.
- Quan sát thiết kế: bảng có ô (selectable) đã có hợp đồng trích dẫn theo ô;
  các mảnh bảng tiếp nối trang 5–8 là fragment không chọn được ô
  (unselectable), phù hợp để BE tính fact thay vì để model tự đọc hiểu.

## Thay đổi

### Module mới — `backendV1/qnu/domains/rag/answer/closed_set.py`

- `VERSION = "qnu.rag.closed-set/v1"`. `computed_facts(question, sources,
  enumeration_requested, exclude_evidence_ids)` tính fact từ **fragment bảng
  không chọn được ô** trong bằng chứng đã đóng gói của lượt:
  - `list_membership`: hàng có tên nguyên văn xuất hiện trong câu và bộ phương
    án (run tổ hợp) **không** có trong các ô danh sách của hàng →
    `present: false` kèm `evidence_ids`; chỉ kết luận vắng mặt trong danh sách
    nguồn, không suy ngoài danh mục.
  - `list_enumeration`: khi câu có tín hiệu chọn/liệt kê, mọi hàng khớp run →
    danh sách tên nguyên văn + `evidence_ids` từng tên, `unknown_rows` (hàng
    không có ô danh sách) và `scope: "packed_table_fragments"`.
  - Dedupe run hậu tố (ví dụ `(văn, địa)` nằm trong `(toán, văn, địa)`) qua
    `_suffix_of`; bỏ nhóm chỉ gồm chữ số (mã ngành); fragment có lỗi hình học
    bảng bị loại; so khớp danh sách dạng tập không thứ tự.
- Chỉ tính từ fragment **không selectable** (`exclude_evidence_ids` = E-id
  bảng có ô + `omitted_tables`): bảng selectable giữ hợp đồng trích dẫn theo
  ô, không chồng lấn hai hợp đồng trên cùng một bảng.

### `backendV1/qnu/domains/rag/answer/packing.py`

- Import `SELECTION_CUE` (dùng lại từ `query_scope`) và `computed_facts`.
- Trong vòng lặp ngân sách: tính `selectable` từ `cells` rồi
  `computed, computed_summary = computed_facts(...)`; truyền `computed=` vào
  `messages_for`; khóa `"computed"` nằm trong khối evidence tính byte.
- Khi envelope vừa ngân sách: `context["computed"] = computed_summary` để trace
  hiển thị trạng thái fact của lượt.
- Gate liệt kê: `include_names or bool(SELECTION_CUE.search(question))` vì
  `question_needs["enumeration"]` không khớp câu "Ngành nào…".

### `backendV1/qnu/domains/rag/answer/drafting.py` — prompt v38

- `PROMPT_VERSION` `qnu.rag.answer/v37` → **`qnu.rag.answer/v38`**.
- Thêm mục **KẾT QUẢ TÍNH SẴN** trong SYSTEM_PROMPT: `computed` là dữ kiện BE
  tính trực tiếp trên bảng được cấp; `list_membership` present=false → trả lời
  rõ đối tượng không có phương án đó trong danh sách nguồn kèm `evidence_ids`,
  không thay bằng việc chỉ liệt kê phương án khác; `list_enumeration` → liệt kê
  đủ mọi `name` nguyên văn, không thêm tên ngoài matches, không đánh số, không
  thêm số lượng không có trong nguồn; `unknown_rows > 0` → nêu rõ phạm vi chỉ
  là các mảnh bảng hiện có.
- `messages_for(..., computed: dict | None = None)`; chỉ gắn `payload["computed"]`
  khi có fact. `PAYLOAD_VERSION` giữ `qnu.answer-payload/v4` (không đổi hợp đồng
  wire).
- Không đổi `chunking.py`, `hybrid.py`, `table_layout.py`, `query_scope.py`,
  schema hay nguồn dữ liệu.

## Phương pháp đo

- Khởi động lại API `:8002` từ venv dự án nạp mã v38; mọi lượt trace xác nhận
  `prompt_version = qnu.rag.answer/v38`.
- **Bộ 12 câu luật** (giữ nguyên bộ của Chặng 3) × 1 lượt; sau đó **lặp 3 vòng ×
  5 câu trọng tâm** {Q02, Q03, Q10, Q11, Q08} (mỗi lượt hội thoại riêng).
- Lượt suite Q05 abstain → chạy **chẩn đoán Q05 ×3** để phân biệt hồi quy hệ
  thống với dao động model.
- Chấm theo ground truth 8 ngành của Q11; ghi `turn_status`, `error_code`,
  `result_status`, `trace.context.computed` (status/tables/skipped_selectable/
  enumerations/matches) cho từng lượt.
- Sau đo, lưu trữ **30/30 hội thoại kiểm thử** qua lifecycle preview → accept;
  không xóa vĩnh viễn.

## Kết quả đo

- **Q11 đóng phần liệt kê:** 4/4 lượt (1 suite + 3 lặp) đều có
  `trace.context.computed = {status: computed, tables: 4, skipped_selectable: 0,
  families: 4, enumerations: 1, matches: 8}` và câu trả lời liệt kê **đủ 8/8**
  ngành ground truth nguyên văn, trích [E1]–[E4], không đánh số, không thêm
  ngành sai. Baseline v37: 5–6/8, có lượt thêm ngành sai. Cải thiện được quy
  trực tiếp cho cơ chế enumeration tính sẵn + mục prompt v38.
- **Q02 — phủ định đúng 4/4 lượt nhưng không đến từ đường fact:** cả 4 lượt trả
  lời tường minh "Tổ hợp (Toán, Văn, Địa) không nằm trong danh sách các tổ hợp
  xét tuyển của ngành này" kèm dẫn chứng ô; tuy nhiên `computed` **không kích
  hoạt** (`skipped_selectable: 16`, `tables: 0`) vì toàn bộ 16 fragment bảng
  của lượt đều selectable — theo thiết kế, bảng selectable giữ hợp đồng ô và
  bị loại khỏi đường fact. Cải thiện quan sát được so với v37 (abstain ở lượt
  đo Chặng 3) nhưng ghi nhận trung thực: đến từ model + hợp đồng ô, không phải
  closed-set; không loại trừ dao động nền (v35/v36 từng trả lời).
- **Q03 còn dao động:** 2/4 lượt trả lời phủ định đúng (suite + lặp vòng 2), 2/4
  abstain (lặp vòng 1 và 3). Lượt suite có thêm nhận định "không có ngành nào
  chỉ xét duy nhất (Toán, Lý, Hóa) mà không kèm tổ hợp khác" — đúng theo danh
  mục hiện có nhưng là suy luận của model từ ô, không phải fact tính sẵn.
- **Q10 vẫn mở:** suite abstain; 3 lượt lặp trả lời, trong đó vòng 1 phủ định
  tường minh ("không có căn cứ xác nhận việc được phép sử dụng chứng chỉ IELTS
  thay thế điểm môn Tiếng Anh khi xét tuyển theo Phương thức 3", [E1][E13][E14]);
  vòng 2–3 chỉ nêu "áp dụng khi xét tuyển theo Phương thức 1 và phương thức 2"
  (phủ định ngầm). `computed` có chạy (`tables: 2`) nhưng 0 fact: luật nằm ở
  văn xuôi, không có cột danh sách để tính — giới hạn đã biết của chặng.
- **Q05:** suite abstain; 3/3 lượt chẩn đoán trả lời đúng (không khẳng định đỗ,
  không tự nêu ngưỡng) → dao động model, **không phải** hồi quy hệ thống.
- **Không hồi quy phần còn lại:** Q01/Q04 giữ nguyên insufficient (mở từ
  baseline); Q06/Q07 giữ nguyên HTTP 409 `answer_scope_clarification_required`
  (guard vai trò năm của planner, có sẵn); Q08 đối chứng 4/4 trả lời đúng;
  Q09/Q12 trả lời đúng. Ngoài Q11, mọi lượt đều `computed: no_tables` (hoặc
  0 fact) — cơ chế mới không tự kích hoạt ở câu không chọn-liệt kê.
- **Kết luận chặng:** hợp đồng eligibility tính sẵn hoạt động đúng ở phạm vi
  fragment bảng unselectable; Q11 từ "liệt kê thiếu/ngành sai" thành liệt kê
  đủ 8/8 ổn định 4/4. Phủ định Q02 đạt nhưng nhờ model/hợp đồng ô; Q10 (văn
  xuôi) và dao động Q03/Q05 vẫn là giới hạn còn mở.

## Kiểm chứng

### Tĩnh

- Ruff `check` đạt trên `closed_set.py`, `packing.py`, `drafting.py`.
- `closed_set.py` (file mới) đã được `ruff format` — chỉ xuống dòng, không đổi
  hành vi sau khi đo.
- `ruff format --check` còn lỗi định dạng **có sẵn** ở `packing.py` (vùng
  `anchors`/khối key cũ) và `drafting.py` (từ phiên 1013); không do chặng này
  tạo ra, giữ nguyên theo quy tắc sửa tối thiểu — ghi nhận FAIL nền, không sửa.
- Git đúng 3 file: `M drafting.py`, `M packing.py`, `?? closed_set.py`; không
  file dữ liệu/schema nào bị thay đổi.

### Sống (PASS)

- API `:8002` nạp mã v38; 30 lượt chạy thật (12 suite + 15 lặp + 3 chẩn đoán),
  trace xác nhận `qnu.rag.answer/v38` và `trace.context.computed` hiện diện.
- Q11: `enumerations: 1, matches: 8` × 4 lượt; câu trả lời đủ 8/8 ngành.
- 30/30 hội thoại lưu trữ thành công qua lifecycle preview → accept
  (`completed`).

### NOT RUN

- pytest / full suite: không chạy theo quy ước phiên.
- Commit/push/deploy: không chạy.
- Biên dịch lại / đăng ký metadata / xuất bản / reindex: không áp dụng (chặng
  thuần lớp trả lời; dùng nguyên corpus và index của Chặng 3).
- Kiểm tra trình duyệt: không áp dụng (thay đổi thuần backend).

## Rủi ro và bước sau

- Fact chỉ phản ánh **các fragment bảng đã đóng gói trong lượt**, không phải
  toàn corpus; `scope: packed_table_fragments` và `unknown_rows` ghi rõ giới
  hạn. Nếu retrieval lấy thiếu fragment, enumeration cũng thiếu — cần đủ
  fragment trước khi tính.
- Bảng selectable không đi đường fact (theo thiết kế hợp đồng ô); Q02 đạt nhờ
  model. Muốn fact cho bảng selectable cần thiết kế riêng — chưa duyệt.
- Q10 (luật văn xuôi, không có cột danh sách) và Q01/Q04 vẫn mở; Q03/Q05 còn
  dao động lượt — ứng viên cho chặng tiếp theo nếu người dùng duyệt.
- Gate liệt kê chỉ nhận các tín hiệu chọn/liệt kê đã biết (`nào`, `liệt kê`,
  `danh sách`, `kể tên`); cách diễn đạt khác ("bao gồm những…") chưa phủ.
