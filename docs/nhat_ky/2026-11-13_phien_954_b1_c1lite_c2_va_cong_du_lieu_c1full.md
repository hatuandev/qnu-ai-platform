# Phiên 954 — B1, C1-lite, C2 và đóng C1-full theo cổng dữ liệu Phase 0

## 1. Yêu cầu và giả định

- Người dùng duyệt thứ tự **B1 → C1-lite → C2 → C1-full → B3/C3** và giao thực hiện tuần tự từng đợt.
- B1 = đọc đủ họ bảng cha cho câu liệt kê/đếm, có chứng minh đủ/thiếu dòng.
- C1-lite = dùng khoảng hiệu lực `effective_from/effective_until` đã có trong metadata để lọc theo mốc thời gian.
- C2 = cache câu trả lời chính xác (không phải semantic cache), key gắn đầy đủ ngữ cảnh và vẫn kiểm chứng lại khi trúng.
- C1-full only-if: kế hoạch đã duyệt ghi rõ **chỉ làm nếu Phase 0 thấy văn bản sửa đổi/thay thế chéo thật**; nếu không thì đóng hạng mục, ghi lý do.
- Giả định chung: không re-index, không migrate dev DB (vẫn `0025_index_fts_gin`, `SCHEMA_HEAD=0026` chờ duyệt), không commit/push, không đụng diff chưa commit của người dùng.

## 2. Thay đổi mã

### B1 — mở rộng đúng họ bảng khi câu hỏi liệt kê/đếm
- `rag/answer/structure_context.py`: thêm `table_family_groups(rows, hits, scopes)` nhóm mọi chunk đã index của đúng bảng vật lý được trúng (`kind: "table_family"`), giữ thứ tự nguồn, trần `MAX_TABLE_FAMILY_CHUNKS`; `VERSION` v5→`qnu.rag.structure/v6`.
- `rag/answer/context.py`: khi `needs["enumeration"] or needs["count"]` và có hit bảng, thêm group họ bảng; từng ứng viên đi qua `claim(...)` ngân sách byte, vượt ngân sách thì đánh dấu `truncated` + số dòng thiếu rồi dừng, không im lặng cắt.
- `rag/answer/selection.py`: thêm `_COUNT` và `_METRIC` để chỉ câu hỏi **đếm dòng** mới mở họ bảng; câu hỏi số liệu (chỉ tiêu, điểm chuẩn, học phí…) không mở rộng.
- Test mới `tests/unit/test_rag_table_family_954.py` (9 ca): bảng 30 dòng, thứ tự nguồn, cắt ngân sách kèm `truncated`, không mở rộng cho câu không liệt kê/đếm, tôn trọng scope năm/metadata.

### C1-lite — khoảng hiệu lực mở hai đầu
- `knowledge/metadata.py::matches_metadata`: nhánh `effective_on` coi phía thiếu là mở (`not start or start <= value`, `not end or value <= end`); đơn vị không có cả hai mốc vẫn là unknown và **không khớp**; vẫn chỉ kết hợp trong cùng một annotation.
- Test mới `tests/unit/test_effective_scope_955.py` (5 ca): chỉ `from`, chỉ `until`, khoảng đóng bao gồm hai biên, unknown không khớp, ngày hiệu lực không trộn sang annotation khác.
- Cập nhật 4 dòng kỳ vọng cũ trong `tests/unit/test_rag_policy_metadata_672.py` theo hợp đồng mở hai đầu.

### C2 — cache câu trả lời chính xác trong Redis
- `rag/answer/cache.py` (mới): `VERSION = "qnu.rag.answer-cache/v1"`, `Entry` (version/content/contract/usage_id/total_tokens), `ttl_seconds()`, `key(material)`; `load/store/discard` là no-op kèm warning khi Redis lỗi, entry hỏng bị loại bỏ (ValidationError → discard).
- `platform/config.py`: `ANSWER_CACHE_TTL_SECONDS` mặc định **0 = tắt**, trần 86400.
- `rag/answer/schemas.py`: `AnswerTrace.cache` để trace hit/miss/lưu.
- `rag/answer/service.py`:
  - Key gồm version, workspace/collection, câu hỏi, `retrieval_query`, persona, `document_ids` sắp xếp, toàn bộ tham số retrieval + metadata filter đã resolve, `index_run_id`/generation/manifest, provider + configuration/inference hash, `PROMPT_VERSION`, hash messages/schema/evidence/catalog. Chỉ tạo key khi TTL > 0.
  - Tra cache **sau** khi đã chứng minh evidence và `prepare_chat_request`, **trước** khi reserve usage.
  - Khi trúng: parse/materialize/assess lại trên nguồn và cell hiện tại, chạy lại verification mới; không reserve/settle usage, `generation=0`; lỗi hợp đồng thì discard và đi đường thường.
  - Chỉ lưu khi `status == "answered"` và verification `not_run`/`supported`; abstain, unsupported, lỗi đều không lưu.
  - Lỗi Redis chỉ degrade về trả lời thường, không đổi kết quả.
- Test mới `tests/unit/test_answer_cache_956.py` (13 ca): ổn định/độ nhạy key, tái dùng đúng một lần gọi chat, cô lập workspace/collection/câu hỏi/metadata/document_ids/generation/proof/runtime, không cache abstain/unsupported, TTL=0 và Redis hỏng không chặn, entry hỏng bị loại và sinh lại.

## 3. Kiểm chứng

- Ba tệp test của ba phase, chạy lại trên mã cuối: `954` **9 passed** (1,73 s), `955` **5 passed** (0,21 s), `956` **13 passed** (1,82 s) — tổng **27 passed/1,98 s**.
- Bằng chứng regression rộng hơn của C2 (đợt trước trong cùng phiên): **147 passed** trên nhóm answer/verification/coverage/selection/conversation/table-family/effective-scope/siblings và chat adapter/admission/cache; full `tests/unit` **1140 passed** kèm **24 lỗi môi trường** `PermissionError [WinError 5]` ở các tệp dùng `tmp_path` (ACL Windows, không liên quan RAG, không sửa ngoài phạm vi).
- Ruff check sạch trên toàn phạm vi diff; `ruff format --check` sạch cho 11 tệp mới/sửa của phiên (tệp test B1 được format lại khi rà diff cuối). Riêng `metadata.py` còn một vùng định dạng cũ ở `_require_row_year_proof` (dòng 258–268, ngoài hunk C1-lite, không sửa để giữ diff tối thiểu).
- **NOT RUN:** live E2E cho B1/C1-lite/C2 (API dev :8002 đang tắt), full suite cô lập, benchmark G4; `NOT RUN ≠ PASS`.

## 4. C1-full — Phase 0 (chỉ đọc, chỉ in số đếm)

- Dev DB `0025_index_fts_gin`; **11 nguồn / 11 bản đã xuất bản / 7 bộ sưu tập / 606 chunk / 10 lượt index** (3 failed, 7 completed).
- Tiêu đề nguồn hoặc tên tệp chứa "sửa đổi/thay thế/bãi bỏ/hợp nhất": **0**.
- Bản published/superseded có metadata `effective_*`: **0** (metadata chỉ có khóa evidence/target/values).
- Chunk văn bản có cụm "sửa đổi" (13) + "thay thế" (19) = **31 chunk**, tất cả thuộc **một** tài liệu "Kế hoạch 07/KH-AM (mô phỏng)…", tất cả chỉ nhắc mã của chính nó; **0** chunk nhắc mã tài liệu khác (27/QĐ.HB, 08/TB.ĐT, 12/KH.ĐT, 14/KH.ĐT đều 0).
- **Kết luận:** không có dữ liệu sửa đổi/thay thế **chéo văn bản** thật ⇒ đóng C1-full theo cổng dữ liệu. Không tạo bảng `document_relations`, không migration 0027, không sửa retrieval/citation/UI. Hạng mục mở lại được khi kho thật có văn bản sửa đổi/thay thế chéo.

## 5. Rủi ro, giới hạn và bước sau

- C2 mặc định tắt cho tới khi kênh công khai có rate limit; khi bật, cache hit bỏ qua quota theo thiết kế và luôn kiểm chứng lại nguồn/cell/verification.
- B1 mới chứng minh bằng unit trên fixture; chưa đo live câu liệt kê/đếm trên corpus thật sau khi API dev bật lại.
- C1-lite chỉ tác động bộ lọc metadata do người dùng đặt; chưa có tự động gắn hiệu lực cho văn bản mới.
- Chưa commit/push; dev DB chưa migrate 0026; chưa re-index.
- B3 và C3 giữ nguyên trạng thái chờ duyệt riêng (B3 cần generation index mới + chi phí 97×2 lượt model thật; C3 chưa cần cho MVP).
