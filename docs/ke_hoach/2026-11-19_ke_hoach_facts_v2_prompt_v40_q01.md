# Kế hoạch Phase 1 — Facts tất định v2, prompt v40 và khôi phục Q11/Q02

- Ngày lập: 2026-11-19
- Phạm vi: `backendV1/qnu/domains/rag/answer` + test unit liên quan
- Trạng thái: **chờ duyệt** (chưa sửa mã, chưa restart, chưa chạy model)
- Liên quan: [Báo cáo Q01 phiên 1018](../nhat_ky/2026-11-18_phien_1018_bao_cao_Q01_quy_tac_thay_the.md), task #424/#425

## 1. Bối cảnh và bằng chứng hiện trạng

Q01 (dùng kết quả tổ hợp này thay cho tổ hợp khác) hiện chỉ đạt 6/11 lượt phủ định dứt khoát, 2 lượt rào "chưa có căn cứ", 2 lượt chỉ nêu "chờ quy đổi" — dù mọi lượt đều trích được câu quy tắc (E9). Nguyên nhân đã xác định:

1. Câu Q01 nêu hai tổ hợp nhưng không nêu tên ngành, nên `_subject` không khớp ([closed_set.py:136](../../backendV1/qnu/domains/rag/answer/closed_set.py)) và `list_membership` không phát.
2. `_option_runs` loại mọi run đứng trước từ nối: "Toán, Văn, Địa **nhưng**…" bị bỏ ([closed_set.py:104](../../backendV1/qnu/domains/rag/answer/closed_set.py)), nên không run nào được nhận.
3. Gate selectable bỏ facts từ bảng đã chọn ([packing.py:56-63](../../backendV1/qnu/domains/rag/answer/packing.py)): sau reindex Chặng B, toàn bộ bảng Mục 4 lọt ngân sách nên facts bị bỏ — Q11 còn 2/8 (`skipped_selectable: 8`), Q02 mất fact membership (`skipped_selectable: 14`).
4. Prompt v39 đã có luật thay thế ([drafting.py:193](../../backendV1/qnu/domains/rag/answer/drafting.py)) nhưng model phải tự suy từ ô bảng, không ổn định (6/11).

## 2. Mục tiêu và tiêu chí đạt

| Bài đo | Đạt khi |
|---|---|
| Q01 ×10 | ≥9/10 phủ định dứt khoát + dẫn chứng; 0 abstain; 0 lỗi |
| Q02 ×3 | phủ định tường minh ≥2/3 (3 lượt mới kết luận) |
| Q11 ×3 | liệt kê đủ 8/8 mỗi lượt; 0 dương tính giả |
| 12 câu hồi quy | Q03/Q04/Q05/Q06/Q07/Q08/Q09/Q10/Q12 giữ đúng như lượt 1018 |
| Chi phí | không thêm call/lượt; prompt tokens tăng ≤5%; bytes_used ≤32KB |

Nguyên tắc: facts tất định là thẩm quyền; model chỉ diễn đạt; mọi kết luận âm chỉ trong phạm vi bảng đã đóng gói và phải dẫn chứng dòng thật; không dùng từ điển hay từ khóa riêng của câu test.

## 3. Thiết kế facts v2 (`qnu.rag.closed-set/v2`)

### 3.1. Trích run cho câu thay thế

- Giữ nguyên `_option_runs` cho `list_membership`/`list_enumeration` (không đổi hợp đồng cũ).
- Thêm biến thể `_substitution_runs(question, vocabulary)`:
  - Quét occurrence có biên từ; gom run tham lam qua các dấu `,`/`và`/`hoặc`/`với` như hiện tại.
  - Chấp nhận run khi sau nó là kết thúc câu/dấu câu, **hoặc** một từ nối diễn ngôn generic: `nhưng | mà | để | vào | thì | nên | khi | nếu`. Đây là mẫu ngôn ngữ chung, có test với ≥3 cách diễn đạt; không thêm từ khóa riêng của Q01.
  - Giữ bộ lọc suffix (run bị cắt giữa danh sách dài không được tính) và yêu cầu ≥2 phần tử.
- Vocabulary lấy từ chính ô danh sách của cột trong bảng đã đóng gói, không lấy từ câu hỏi.

### 3.2. Tính `option_substitution`

Với từng family (tài liệu + version + quyết định phát hành + bảng nguồn) và từng cột danh sách:

1. Lấy các run hợp lệ thuộc cột (cả hai chiều).
2. Với mỗi cặp có thứ tự (nguồn A, đích B), A≠B:
   - `targets` = số dòng nhận B;
   - `targets_only` = số dòng nhận B mà **không** nhận A;
   - nếu `targets_only > 0` → phát fact:
     ```json
     {
       "source": ["toán", "văn", "địa"],
       "target": ["toán", "lý", "hóa"],
       "scope": "packed_table_fragments",
       "status": "no_substitution_in_closed_list",
       "targets": 12,
       "targets_only": 12,
       "evidence_ids": ["E10"]
     }
     ```
   - Không có dòng `targets_only` → không phát fact (không có căn cứ phủ định).
3. Chỉ ghép cặp trong cùng family + cùng cột để tránh cặp giả giữa hai bảng khác nhau.
4. Dedupe theo (family, cột, A, B); `evidence_ids` là dòng thật của bảng, không phải ID tự tạo.

Hai chiều được tính độc lập: A→B và B→A có thể cùng tồn tại nếu mỗi chiều có dòng đích riêng.

### 3.3. Hợp đồng dữ liệu và trace

- `computed_facts(...)` nhận thêm kết quả `option_substitution` trong dict facts; `facts = None` khi cả ba loại rỗng.
- Summary v2: `{version: "qnu.rag.closed-set/v2", status: computed|no_tables, tables, skipped_selectable (giữ, =0 sau gate), families, subject, memberships, enumerations, matches, runs, substitutions}`.
- Trace `context.computed` của lượt trả lời phản ánh đúng summary; không chứa văn bản nguồn.

## 4. Sửa gate selectable (#425)

Trong `packing.py`: bỏ khối `selectable` (3 dòng) và bỏ đối số `exclude_evidence_ids` khi gọi `computed_facts`; facts tính từ **mọi** mảnh bảng đã đóng gói.

- Lý do: bảng selectable giữ hợp đồng ô cho model, nhưng facts vẫn là kết luận riêng có dẫn chứng — bỏ đi làm mất Q11 (liệt kê tất định) và Q02 (membership) như đã đo.
- Không đổi cơ chế cắt byte-budget; `cells` vẫn dùng cho messages/evidence như cũ.
- Cập nhật test hợp đồng `test_selectable_tables_are_excluded` → `test_selectable_tables_also_computed`.

## 5. Prompt v40

`PROMPT_VERSION = "qnu.rag.answer/v40"`; giữ nguyên toàn bộ v39, thêm vào mục "KẾT QUẢ TÍNH SẴN":

- `option_substitution`: mỗi mục cho biết các bảng đã cấp có dòng nhận tập đích mà không nhận tập nguồn.
- Khi `status = no_substitution_in_closed_list`: câu kết luận đầu tiên phải nói rõ không được dùng tập nguồn thay cho tập đích trong phạm vi danh mục đã dẫn; dẫn `evidence_ids` của mục.
- Quy định quy đổi/tương đương chưa ban hành chỉ được nêu như ghi chú phụ sau kết luận; không dùng làm kết luận, không đổi status sang `insufficient_evidence`.
- Không tự ghép cặp ngoài các run trong `computed`; không kết luận ngoài danh mục.

## 6. Test unit

Tệp được sửa: `backendV1/tests/unit/test_closed_set_facts_1015.py`.

| Ca | Kỳ vọng |
|---|---|
| Selectable tables | Facts vẫn tính; `skipped_selectable == 0`; không còn `no_tables` vì bị loại |
| Thay thế synthetic (2 run, có "nhưng") | Fact A→B đúng evidence dòng đích; `targets_only` đúng số dòng |
| Không có dòng đích riêng | Không phát fact; facts `None` nếu các loại khác rỗng |
| Run trước từ nối | `_substitution_runs` nhận; `_option_runs` cũ vẫn từ chối (không đổi hợp đồng) |
| Liệt kê 1 run | `list_enumeration` giữ nguyên hành vi và thứ tự |
| Bảng lỗi hình học | Bỏ qua như hiện tại (`layout` errors) |

Fixtures là bảng tổng hợp, không dùng nguyên văn corpus. Không đụng 5 tệp test cấm: `test_answers_api_648.py`, `test_hybrid_655.py`, `test_answer_contract_788.py`, `test_hybrid_fusion_938.py`, `test_unselectable_prose_941.py`.

## 7. Kiểm chứng và đo

### 7.1. Tĩnh

- Ruff trên 4 tệp đã sửa; import smoke; UTF-8 no BOM/LF; đọc lại tiếng Việt.
- pytest: **NOT RUN** theo quy định hiện tại (chạy nhóm unit cụ thể nếu người dùng yêu cầu).

### 7.2. Live (cần duyệt riêng vì dùng model thật)

1. Restart API :8002 (kill PID, relaunch `--env-file ../.env`); worker không cần.
2. Đo: Q01 ×10; Q02 ×3; Q11 ×3; 12 câu một lượt — khoảng 28 lượt chính + router/appeal, ước 25–40 phút.
3. Chấm tay theo chuẩn đã chốt ở phiên 1018; không retry-to-green; lưu artifact `%TEMP%/qnu_facts_v2_*.json`.
4. So `prompt_tokens` và `stage_ms.generation` trung bình với lượt 1018 để chứng minh không phình context.
5. Dọn hội thoại đo qua lifecycle (mẫu `qnu_cleanup_*`).

### 7.3. Rollback

Revert 4 tệp + restart API. Không có migration, không đổi dữ liệu/index; không cần reindex.

## 8. Rủi ro và đối sách

| Rủi ro | Đối sách |
|---|---|
| Cặp run giả ở câu liệt kê 2 tổ hợp | Fact chỉ mang tính thông tin; prompt chỉ dùng khi câu hỏi yêu cầu thay thế; test âm |
| Kết luận vượt phạm vi bảng | `scope` đóng + evidence_ids dòng thật; prompt giới hạn "trong danh mục đã dẫn" |
| Q11 không trở lại 8/8 | Đo 3 lượt trước kết luận; nếu vẫn lỗi, chẩn đoán tiếp ở selection/name_id, không nới assertions |
| Prompt dài thêm gây lệch | Facts vài trăm byte; theo dõi `bytes_used` và token |
| Model vẫn không tuân thủ | Chỉ khi đó mới cân nhắc hậu kiểm (bước riêng, cần duyệt) |

## 9. Sau đo

Nhật ký 1019, snapshot, README nhật ký, memory, cập nhật báo cáo 1018; đóng #424/#425 nếu đạt. Không commit/push/deploy trong phạm vi này.

## 10. Phase 2 — spec LLM đề xuất facts lúc chuẩn bị (chưa code)

Sẽ soạn spec riêng sau khi Phase 1 đo xong, gồm: schema fact đề xuất; provenance ô/block; validator tất định; preview + duyệt như metadata 947–949; version/hash và tạo dẫn xuất khi đổi model; đo thời gian chuẩn bị trước–sau; tiêu chí chấp nhận. Không đụng mã Phase 1.

## 11. Việc cần người dùng duyệt

1. Sửa 4 tệp mã/test như trên (`closed_set.py`, `packing.py`, `drafting.py`, `test_closed_set_facts_1015.py`).
2. Restart API dev và chạy live ~28 lượt đo.
3. Phạm vi KHÔNG làm: migration, reindex, đổi dữ liệu nguồn, commit/push/deploy, đụng `.env`, đụng 5 tệp test cấm.
