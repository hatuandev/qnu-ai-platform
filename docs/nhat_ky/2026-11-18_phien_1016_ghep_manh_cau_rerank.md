# Phiên 1016 — Chặng A: ghép mảnh câu cho đầu vào rerank (không reindex)

Ngày: 2026-11-18. Phạm vi được duyệt: chỉ lớp trình bày/rerank, không reindex, không đổi dữ liệu.

## Yêu cầu và giả định

- Triệu chứng: đoạn văn luật bị chunk theo từng dòng PDF; một câu quy tắc nằm rải ở các ordinal 59/60/61, và đầu vào rerank trước đây là nguyên phong bì JSON + heading kế thừa cũ + một dòng thân, nên mảnh bị cross-encoder chấm gần 0 (score 0.0136, hạng 31/40 ở baseline c3_v8).
- Chặng A (được duyệt): (1) ghép cửa sổ câu lân cận cho **đầu vào rerank**; (2) hiển thị văn bản tự nhiên thay phong bì JSON; chỉ sửa `presentation.py`, `search.py`, đúng một dòng + một tham số `hybrid.py`; **không reindex, không đổi dữ liệu**.
- Giả định kiểm chứng được: nếu reranker thấy câu đầy đủ, mảnh luật sẽ vào top-8 và Q01 ổn định hơn. Đây là giả định đo được — kết quả bên dưới phủ định một phần.

## Thay đổi mã (4 tệp, +165/−8)

- `backendV1/qnu/domains/knowledge/index/presentation.py`: `PRESENTATION_VERSION` lên `qnu.evidence-reading/v3`; thêm `paragraph_body` (bỏ header title/heading kế thừa, giữ nguyên văn gốc có kiểm hash), `paragraph_title`, `_ends_sentence`, `_starts_numbered_item`, `stitch_window` với biên cứng `STITCH_MAX_PARTS=4`, `STITCH_MAX_SIDE=2`, `STITCH_MAX_BYTES=800`. `reading_text`/`rerank_text` **không đổi** — bằng chứng đưa vào model giữ nguyên.
- `backendV1/qnu/domains/knowledge/index/search.py`: `_stitch_documents` đọc **read-only** chunk lân cận theo `(run_id, input_id, ordinal ± 2)` qua `AsyncSession`, ghép cửa sổ theo anchor, gắn tiền tố title tài liệu; chỉ áp cho anchor `kind=paragraph`; nhánh rerank ghi `trace["rerank_stitched"]` và truyền `prepared=`.
- `backendV1/qnu/domains/knowledge/index/hybrid.py`: đúng thay đổi tối thiểu đã duyệt — thêm tham số `prepared=None` và `documents = [(prepared or {}).get(h.chunk_id) or rerank_text(h) for h in hits]`.
- `backendV1/qnu/domains/knowledge/index/contextual.py`: tách `original_text_fields(text, structure)` để dùng lại phần xác minh `version/prefix+original/sha256` từ ngoài `SearchHit`; `original_text` giữ nguyên hành vi.
- `backendV1/tests/unit/test_rerank_stitch_1018.py` (mới, 5 hàm): cửa sổ cơ bản, chặn gộp ngược khi câu trước đã kết thúc, mục đánh số kết thúc walk, vượt biên byte → `None`, anchor ngoài map → `None`. Tên tệp giữ hậu tố 1018 theo lần tạo trước; nội dung độc lập số phiên.

Không đổi `chunking.py`, `table_layout.py`, schema, prompt v38, dữ liệu/index; không commit/push.

## Kiểm chứng mã (PASS)

- `ruff check` 4 tệp nguồn + tệp test: PASS.
- Chạy trực tiếp 5 hàm test (không pytest, theo quy định): 5/5 PASS.
- Import smoke `qnu.domains.knowledge.index.search` + `hybrid`: PASS; API `:8002` khởi động lại nạp mã mới.

## Đo live (12 câu luật + Q01 lặp 3 lượt)

Corpus/index giữ nguyên: `col_af3ea7d6d5fb`, `idx_a88196a1f0ba` (gen 2, 184 chunk), assistant `ast_44fc63a77512`, workspace `ws_623614ba7fb8`.

- **Trace xác nhận cơ chế chạy**: mọi lượt hoàn tất có `rerank_presentation = qnu.evidence-reading/v3` và `rerank_stitched > 0` cho câu có anchor đoạn văn (Q01=18, Q02=19, Q03=17, Q04=23, Q05=16, Q08=20, Q09=26, Q10=22, Q12=28); Q11=0 vì toàn ứng viên là bảng — đúng kỳ vọng.
- **Trạng thái 12 câu (gộp lượt đuôi Q09–Q12 chạy lại sau khi token SSO hết hạn giữa chừng)**: Q01/Q02/Q03/Q05/Q08/Q09/Q10/Q11/Q12 `answered`; Q04 `insufficient_evidence` (đúng — "Quản trị hàng không" không có trong danh mục); Q06/Q07 409 `answer_scope_clarification_required` (giữ nguyên như mọi baseline v35/v36/c3_v8). So với c4_v1 (Q01/Q05/Q10 abstain): Q01/Q05/Q10 chuyển sang trả lời; do bằng chứng đưa vào model không đổi (v3 không sửa `reading_text`), các đảo trạng thái này là **dao động model**, không quy công cho Chặng A.
- **Q01 là điểm mở**: 12Q trả lời đúng "không thể dùng 15 điểm thay cho tổ hợp 13 điểm" với [E13][E14]; nhưng 3 lượt lặp trong cùng mã đều `insufficient_evidence`/`model_abstained` → **1/4 lượt trả lời**. Bốn lượt có cùng 40 ứng viên, cùng top-8 được chọn và cùng điểm rerank đến 4 chữ số thập phân — khác biệt duy nhất là quyết định của model ⇒ abstain là ngẫu nhiên phía sinh, không phải truy xuất.
- **Hiệu ứng lên mảnh luật (đo trên trace)**: ordinal 60 — trước (v2, c3_v8) hạng 31/40 score 0.0136; sau (v3, ghép cửa sổ) hạng **24/40** score 0.0130. Ordinal 62 hạng 23/0.0327; ordinal 59/61 không nằm trong 40 ứng viên. Cửa sổ ghép **có tồn tại** nhưng **không vào top-8**; top-8 được chọn toàn bộ là bảng ordinal 159–170. Kết luận trung thực: Chặng A sửa đúng lỗi trình bày đầu vào rerank, nhưng **chưa đủ để đổi kết quả Q01**; câu trả lời đúng duy nhất đến từ bằng chứng bảng + diễn giải của model.

## Không chạy / chưa chứng minh

- **12 câu Kiri một lượt: NOT RUN** — bộ câu hỏi ledger Kiri 2026-11-16 không còn trong `%TEMP%` (đã bị dọn) và không được lưu trong `docs/nhat_ky`; ledger cũ chạy trên đúng workspace/kho này nhưng danh sách câu không thể tái lập trung thực nên không chạy lại bằng câu hỏi suy đoán.
- **pytest/full suite: NOT RUN** (theo quy định hiện hành, chỉ chạy test hàm trực tiếp).
- **Chặng B** (kế thừa heading lúc biên dịch + biên dịch lại/reindex): chưa được duyệt, chưa làm.
- **Đường nhiều kho** (`multi.py::search_collections`) **không đi qua ghép cửa sổ** — khoảng trống đã biết, trợ lý một kho hiện tại không bị ảnh hưởng.
- Không commit/push/deploy; không đổi `.env`.

## Rủi ro và bước sau

- Ghép cửa sổ chỉ tác động thứ hạng rerank; nếu mảnh luật vẫn đứng sau bảng ở top-8 thì Q01 còn phụ thuộc model. Hướng tiếp theo cần duyệt riêng: Chặng B (heading/biên dịch) hoặc mở rộng selection theo cửa sổ đoạn văn — cả hai đều ngoài phạm vi Chặng A.
- Cần đo lại Q01 nhiều lượt sau khi có thay đổi truy xuất thật; hiện tại không được mô tả Chặng A là "đã sửa Q01".
