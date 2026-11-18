# Phiên 1014 — Chặng 3: tổ hợp môn từng dòng bảng vào retrieval_metadata.attributes + lọc theo thuộc tính

## Yêu cầu

- Sau báo cáo Chặng 1–2 (phiên 1013), người dùng duyệt **Chặng 3** của kế hoạch
  4 chặng: đưa danh sách tổ hợp môn của **từng dòng bảng** vào
  `retrieval_metadata.attributes`, để câu "ngành nào xét tổ hợp X" trở thành tra
  cứu thuộc tính và `attribute_scope` lọc được tập ứng viên trước khi truy xuất.
- Phê duyệt kèm quyền thực hiện chuỗi dữ liệu của chặng: biên dịch lại → đăng ký
  metadata → xuất bản → reindex corpus dev.
- Giữ quy ước từng chặng: triển khai, đo, báo cáo trung thực; Chặng 4 (hợp đồng
  trả lời eligibility) vẫn cần duyệt riêng.

## Bối cảnh

- Corpus đo: kho "Tuyển sinh 2026" (`col_279e00e8f7fb`, workspace
  `ws_623614ba7fb8`), tài liệu `cdoc_a17f6bb98d36` ("Thông tin TSĐH cập nhật.pdf",
  OCR `ocr_5479ad937cb9`, run biên dịch `cmp_09a395efedb4`), trợ lý
  `ast_44fc63a77512`, API `:8002`.
- Trước chặng: metadata chỉ có tên đơn vị và `issued_year`; không có khóa
  ngành/tổ hợp, nên Q11 ("ngành nào xét tổ hợp Toán, Văn, Địa?") phải dựa vào
  liệt kê của model trên các mảnh bảng — v37 đạt 5–6/8, có lượt thêm ngành sai.
- Bảng tổ hợp của tài liệu bị chia nhiều trang/khối; các trang 5–8 là bảng tiếp
  nối không lặp header, nên trước chặng này phần lớn dòng không lấy được nhãn cột.

## Thay đổi

### Trích xuất metadata

- **`backendV1/qnu/domains/knowledge/metadata.py`** (+214 dòng)
  - `value_parts`, `same_listed`, `attribute_contains`: so khớp metadata dạng
    danh sách phẩy như **tập không thứ tự** (tách phần tử theo `;` ở cấp ngoài);
    `matches_metadata` dùng `attribute_contains`.
  - `list_value`: nhận diện ô cột có dạng danh sách phần tử để chuẩn hóa giá trị.
  - Nối nhãn cho **bảng tiếp nối qua trang**: `_carried_first_row` (trang sau lặp
    lại dòng đầu), `_continues_numbering` (ô đầu các dòng chỉ gồm chữ số và tăng
    đơn điệu), `_local_header_labels`, `table_chain_labels(tables)` — nhận cặp
    bảng kề trang cùng run (`previous_page + 1 == page_number`), cùng số cột,
    bảng trước có nhãn; nhãn cột được thừa hưởng từ bảng header gốc, giữ tham
    chiếu header gốc ở mỗi dòng.
  - `_structural_attribute_proof`: chỉ phát metadata khi chứng minh được cấu
    trúc (nhãn + dòng/ô nguồn); không suy diễn khi thiếu căn cứ.
- **`backendV1/qnu/domains/knowledge/compilation/supplement.py`** (+84 dòng)
  - `RULE_VERSION` `qnu.compiler.metadata-rules/v10` → `v11`.
  - `_table_attribute_entries` dùng `table_chain_labels(draft["source_tables"])`
    để gắn thuộc tính dạng danh sách theo **từng dòng** cho cột có header dạng
    danh sách (ở corpus này: `Tổ hợp môn xét tuyển`), kể cả các dòng thuộc bảng
    tiếp nối trang 5–8 trước đây bị bỏ.

### Lọc theo thuộc tính

- **`backendV1/qnu/domains/knowledge/index/query_scope.py`** (+95 dòng)
  - `VERSION` `qnu.catalog-scope/v6` → `v8`.
  - `catalog_sets(structures)`: nhãn → tập các `frozenset` phần tử của mọi giá
    trị danh sách trong run đang phục vụ.
  - `SELECTION_CUE` (`\bnào\b`, `\bliệt\s+kê\b`, `\bdanh\s+sách\b`,
    `\bkể\s+tên\b`): tín hiệu câu hỏi chọn-liệt kê.
  - `_run_value`: đọc chuỗi ≥2 phần tử đã biết trong câu (bỏ qua khoảng trắng
    đầu), so **không thứ tự** qua `frozenset` với `sets[nhãn]`; chỉ trả giá trị
    khi khớp đúng một tập đã có.
  - `attribute_scope(query, catalog, sets)`: giữ đường chọn trực tiếp
    `nhãn:giá trị`/`nhãn là giá trị`; nếu không có selector trực tiếp **và** câu
    có `SELECTION_CUE` thì mới dò mở rộng tiền tố từng từ rồi `_run_value`; không
    biến tên trường không chọn ("số điện thoại"…) thành scope.
- Không đổi `chunking.py`, `hybrid.py`, `table_layout.py`, schema hay nguồn dữ
  liệu; không đổi prompt (giữ `qnu.rag.answer/v37`).

## Quy trình dữ liệu (được duyệt trong chặng)

- Biên dịch lại tài liệu → preview đăng ký metadata: **103 annotation, 0 xung
  đột**; nối chuỗi bảng giúp các trang 5–8 có nhãn cột (53 dòng tổ hợp được gắn
  thuộc tính). Preview sha được chốt qua decision commit.
- Xuất bản bản mới `cver_7dbc92d84d05` (duyệt `pdec_5d7f455446a6`, phát hành
  `pdec_fc8cc18eb316`, bundle `d7ededfd…`, `retrieval_metadata_sha256`
  `74be6aaf…`).
- Reindex chủ động: `idx_a88196a1f0ba`, generation 2, **184 chunk**; chặng dùng
  run này cho toàn bộ phép đo.

## Phương pháp đo

- API `:8002` khởi động lại từ venv dự án nạp mã v8; xác nhận
  `trace.retrieval.scope_resolution.version = qnu.catalog-scope/v8` ở mọi lượt.
- **Q11 ×3** (mỗi lượt hội thoại riêng): kiểm tra filter kích hoạt
  (`attributes: {"Tổ hợp môn xét tuyển": "Toán, Văn, Địa"}`,
  `metadata_eligible_chunks = 4`), chấm theo ground truth 8 ngành.
- **Kiểm tra độ chính xác phạm vi (read-only DB)**: với 184 chunk của run, lọc
  mọi chunk chứa bất kỳ hoán vị nào của Toán/Văn/Địa → đúng 4 chunk, trùng khớp
  tập 4 chunk mà filter trả về; không bỏ sót, không thừa.
- **Kiểm tra toàn vẹn bằng chứng (read-only DB)**: đọc 4 chunk đủ điều kiện; xác
  nhận đơn vị ngữ cảnh search `table:ocr_5479ad937cb9:ev_p004_b001:row:1` chứa
  các tổ hợp gồm "Văn, Địa, Toán", và JSON bảng thể hiện đúng dòng 1
  "Sư phạm Lịch sử - Địa lý" (7140249).
- **12 câu luật đầy đủ trên v8** (1 lượt/câu): đối chiếu trạng thái với baseline
  v37; xác nhận chỉ Q11 kích hoạt attribute filter, các câu khác `filters: [{}]`.
- Sau đo, lưu trữ 36/36 hội thoại kiểm thử qua lifecycle preview → accept; không
  xóa vĩnh viễn.

## Kết quả đo

- **Độ chính xác phạm vi đạt:** `metadata_eligible_chunks = 4`, đúng bằng tập
  chunk chứa tổ hợp trong run 184 chunk; 4/4 ứng viên dense/lexical nằm trong
  tập này — filter lọc trước truy xuất hoạt động đúng, không âm tính giả.
- **Bằng chứng đủ và hiển thị đúng:** cả 8 ngành ground truth đều có mặt trong 4
  chunk đủ điều kiện (kể cả "Sư phạm Lịch sử - Địa lý"); các lượt thiếu ngành là
  model liệt kê thiếu, không phải mất bằng chứng.
- **Q11 ×3 sau filter:** 7/8, 6/8, 1 lượt abstain (`model_abstained`); các lượt
  trả lời không có ngành sai (không còn false positive như v37). Thiếu sót tập
  trung ở "Sư phạm Lịch sử - Địa lý" và "Công tác xã hội".
- **12 câu v8 so với v37 (cùng prompt v37, index mới):**
  Q01 abstain (giữ nguyên); Q02 abstain (giữ nguyên v37; v35/v36 từng trả lời —
  dao động nền đã biết); Q03 trả lời đúng "Không được…" (v37 abstain — cải
  thiện); Q04 abstain đúng (giữ nguyên); Q05 trả lời (giữ nguyên); Q06/Q07 HTTP
  409 planner (giữ nguyên, có sẵn); Q08–Q12 trả lời (giữ nguyên). Lượt Q11 trong
  bộ 12 câu liệt kê 6/8, không ngành sai.
- **Không hồi quy do v8:** ngoài Q11, mọi câu có `filters: [{}]` — cơ chế
  `attribute_scope` mới không tự kích hoạt ở câu không chọn-liệt kê.
- **Kết luận chặng:** lớp dữ liệu (metadata tổ hợp từng dòng + lọc thuộc tính)
  hoạt động đúng và đo được; phần còn thiếu của Q11 và các câu phủ định
  (Q02/Q10/Q03) là trần của việc sinh câu trả lời — thuộc Chặng 4, chưa duyệt.

## Kiểm chứng

### Tĩnh

- Ruff `check` đạt trên `metadata.py`, `supplement.py`, `query_scope.py`,
  `drafting.py`.
- `ruff format --check` còn lỗi định dạng **có sẵn** ở `query_scope.py` (vùng
  regex/prefix-walk cũ) và `drafting.py` (từ phiên 1013); không do chặng này tạo
  ra, giữ nguyên theo quy tắc sửa tối thiểu — ghi nhận FAIL nền, không sửa.
- Biên dịch/preview đăng ký metadata chạy thật: 103 annotation, 0 xung đột.

### Sống (PASS)

- Xuất bản `cver_7dbc92d84d05` và reindex `idx_a88196a1f0ba` (generation 2, 184
  chunk) hoàn tất trên dev.
- Q11 ×3 + 12 câu v8 chạy thật trên API `:8002`; trace xác nhận
  `qnu.catalog-scope/v8`; Q11 có filter thuộc tính, eligible = 4.
- Kiểm tra chéo read-only: 4/4 chunk đủ điều kiện chứa tổ hợp; không bỏ sót
  chunk nào trong run.
- 36/36 hội thoại kiểm thử lưu trữ thành công qua lifecycle (`completed`).

### NOT RUN

- pytest / full suite: không chạy theo quy ước phiên.
- Commit/push/deploy: không chạy.
- Kiểm tra trình duyệt: không áp dụng (thay đổi thuần backend/dữ liệu).
- Chặng 4: chưa được duyệt.

## Rủi ro và bước sau

- Q11 vẫn dao động 6–7/8 hoặc abstain giữa các lượt dù bằng chứng đủ trong 4
  chunk; đây là giới hạn liệt kê của model, không sửa thêm bằng prompt ở chặng
  này. Chặng 4 (hợp đồng trả lời eligibility/liệt kê phía BE) là bước tiếp theo
  khi được duyệt.
- Heuristic nối bảng chỉ nhận cặp kề trang có cấu trúc chứng minh được; bảng
  không đủ căn cứ giữ unknown — không đoán nhãn.
- Q06/Q07 vẫn 409 `answer_scope_clarification_required` (guard vai trò năm của
  planner) — có sẵn từ trước, ngoài phạm vi chặng.
- Từng ghi nhận lỗi 500 do deadlock Postgres `FOR UPDATE` trên bảng workspaces
  (một lượt Q10 lặp trước đó) — có sẵn, ngoài phạm vi chặng, không sửa.
