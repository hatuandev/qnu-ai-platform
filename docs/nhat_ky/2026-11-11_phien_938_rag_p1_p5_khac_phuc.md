# NHẬT KÝ LÀM VIỆC: RAG P1–P5 — recall, grounding bảng, lỗi, trace và tách text embedding

- **Thời gian**: 2026-11-11
- **Mục tiêu phiên (Goals)**:
  - Triển khai lần lượt P1–P5 theo kế hoạch khắc phục RAG sau phiên 937, mỗi đợt có test trọng tâm và Ruff.
  - Sau khi xong cả 5 đợt, chạy lại đúng 10 câu phiên 935 một lượt với model thật, giữ nguyên tham số, không retry để làm xanh kết quả.
- **Ràng buộc**: Không retry câu hỏi model, không nới assertion/bỏ guard; lỗi nền giữ riêng; `NOT RUN` không phải `PASS`; F13 vẫn mở; không test trên DB ứng dụng; không commit/push/deploy; không in secret.

## 1. P1 — Khôi phục recall rerank/fusion và lexical

- **Nguyên nhân** (đo read-only trên index generation 2):
  - Chunk đáp án Q6 `ich_e45d3a98814b` ("Tổng số lượng tuyển sinh: 5.173") nằm trong index nhưng lexical OR rộng xếp hạng 39, ngoài `candidate_k=30`; truy vấn bigram liền kề xếp hạng 11.
  - Q7: các đoạn đáp án 402A/402B/405 có trong index; OR rộng chỉ thấy 402B hạng 39; bigram thấy header 1, 402B 8, 405 13, 402A 17.
  - Rerank cũ chỉ trả `min(top_k, len(hits))` ứng viên và thay toàn bộ danh sách fused, làm mất recall trước rerank.
- **Thay đổi**:
  - `backendV1/qnu/domains/knowledge/index/hybrid.py`: thêm `lexical_expression()` (token rời hoặc cặp bigram liền kề, khử trùng lặp), `lexical(..., phrases=True)`; `fuse()` nhận trọng số; rerank gửi toàn bộ ứng viên (`len(hits)`) rồi weighted-RRF giữa thứ hạng fused cũ và thứ hạng rerank (`RERANK_WEIGHT = 2.0`), cắt `top_k`.
  - `backendV1/qnu/domains/knowledge/index/search.py`: thêm nhánh phrase lexical và fusion ba nhánh dense + lexical + phrase; trace ghi riêng từng tầng.
- **Kiểm chứng P1**:
  - Ruff 2 tệp mã + 2 tệp test: `All checks passed!`
  - Unit `test_hybrid_fusion_938.py` + `test_hybrid_fts_index_934.py`: **4 passed / 2,31 giây**.
  - Integration cô lập `tests/integration/test_hybrid_655.py`: **12 passed / 131,95 giây**; harness 141,72 giây; DB `qnu_v1_test_a78fb37b133e44dc` đã xóa; sentinel giữ; pytest exit 0.
  - Chưa chạy API/model thật cho P1 (gộp vào lượt 10 câu cuối).

## 2. P2 — Grounding bảng và cell catalog

- **Nguyên nhân**: payload bảng gửi model lặp `cell_id` đầy đủ cho từng ô, phình rất nhanh với bảng nhiều hàng/cột và dễ đẩy envelope vượt ngân sách; đồng thời contract `cell_id` chưa được diễn đạt rõ nên model dễ trả khóa cột hoặc ID sai.
- **Thay đổi**:
  - `backendV1/qnu/domains/rag/answer/cells.py`: `prompt_catalog` gửi bảng dạng gọn `{"id","columns","rows":[{"row","subject","cells":{"kM": value}}]}`; catalog server vẫn giữ đầy đủ `cell_id`, hình học, `source_cells` để materialize. Prompt (v22) nói rõ `cell_id` đầy đủ là `id:row:key`.
  - `table_selection.select_catalog`: chỉ thu hẹp theo subject được nêu chính xác trong cùng family/phiên bản nguồn; không đoán.
  - `materialize` chỉ nhận đúng `cell_id` server dạng `E:rN:kM`.
- **Kiểm chứng**:
  - Unit `test_table_grounding_770.py` (compact rows vẫn materialize từ ID đầy đủ; family 5 bảng × 12 hàng nằm trong ngân sách 8.000 byte; chặn vượt ngân sách trước khi gọi provider) + `test_answer_contract_788.py` + `test_answer_projection_764.py` + `test_rag_context_908.py`.
  - Integration lượt 1 sau P2–P4: **33 failed / 40 passed** — toàn bộ do fixture `FakeAnswerChat` dựng `cell_id` từ khóa compact (`k2`) thay vì ID đầy đủ, vi phạm pattern `CellSelection`. Đã sửa fixture để ghép `id:row:key` đúng prompt v22 và siết assertion compact bằng regex ID đầy đủ; không nới assertion.
  - Integration lượt 2: **72 passed / 1 failed** — ca `test_assistant_chat_uses_persisted_hybrid_rerank_policy_and_checks_provider_access` dùng `top_k=1` nên prompt không có bảng; fixture đọc `incoming["tables"]` vô điều kiện và crash `KeyError`. Đã cho fixture fallback trả statement văn bản khi prompt không có bảng (đúng hành vi model với prompt thực tế); không đổi assertion.
  - Integration lượt 3 (sau sửa fixture): **73 passed / 0 failed**, 841,02 giây; harness 850,36 giây; DB `qnu_v1_test_4e102efc6f20418d` đã xóa; sentinel giữ; `pytest_exit=0`.
  - Batch unit P2–P5 (6 tệp): **79 passed / 2,19 giây**; Ruff các tệp P2–P4: `All checks passed!` (format: 9/10 tệp đã chuẩn; `test_answer_projection_764.py` còn một dòng cũ không thuộc diff).

## 3. P3 — Ngữ nghĩa lỗi, verification và scope hội thoại

- **Nguyên nhân** (log phiên 937): Q1/Q2 502 do `ModelAnswer.consistent_status` (status `answered` nhưng statements/lookups rỗng) nhưng title trả mặc định "Yêu cầu không hợp lệ"; Q4 502 do `cell_id` sai pattern; audit thiếu đường dẫn cụ thể nên khó phân biệt lỗi hợp đồng model với lỗi client.
- **Thay đổi**:
  - `drafting.parse_answer`: 502 title "Phản hồi mô hình không hợp lệ"; citation kiểm theo index và ghi `duplicate` / `not_allowed` (mã `answer_citation_invalid`).
  - `cells.materialize`: kiểm cell theo index (`duplicate` / `not_in_catalog`), title "Ô bảng mô hình chọn không hợp lệ"; các nhánh `answer_cell_selection_required`, `answer_source_text_invalid`, `too_many_statements` có `validation_issues` path/type an toàn.
  - `coverage`, `verification`, `conversations/rewriting`: title 502 rõ nghĩa; không đổi luồng từ chối/làm rõ.
  - Prompt v22 thêm ràng buộc: `answered` phải có ít nhất một statement hoặc lookup; `cell_id` đúng ba phần.
  - Không chuyển lỗi hợp đồng thành abstain giả; audit chỉ lưu path/type, hash output và số token, không lưu nội dung nguồn.
- **Kiểm chứng**:
  - Unit `test_answer_contract_788.py` thêm 3 ca: `answered` rỗng là lỗi hợp đồng `value_error`; `cell_id` sai pattern ghi đúng `["lookups",0,"cell_id"]`; citation sai ghi `not_allowed`/`duplicate`.
  - `test_table_grounding_770.py` siết title và issue của lookups giả/trùng.
  - Integration cô lập 3 tệp (`test_answers_api_648.py`, `test_rag_verification_policy_672.py`, `test_conversations_649.py`): **73 passed / 0 failed** trong lượt 3 (số liệu đầy đủ ở mục P2).

## 4. P4 — Hiệu năng, trace và đo lường RAG

- **Hiện trạng**: retrieval trace đã có `query_embedding_ms`, `dense_ms`, `lexical_ms`, `lexical_phrases_ms`, `retrieval_ms`; answer trace chỉ có retrieval/context/generation/validation/verification.
- **Thay đổi**: `backendV1/qnu/domains/rag/answer/service.py` đo thêm `stage_ms`:
  - `packing` (`_pack_messages`), `proof` (`validate_results` lần đầu), `model_prepare` (`prepare_chat_request`), `total` (toàn request, gồm cả nhánh không có evidence).
- **Kiểm chứng**: integration `test_answer_returns_only_server_bound_sources` siết thêm: đủ bộ khóa stage, mọi giá trị ≥ 0, `total ≥ generation`. Kết quả: nằm trong lượt 3 **73 passed**.

## 5. P5 — Tách text embedding khỏi text phục vụ

- **Hiện trạng**: cơ chế đã có và đang bật trên generation 2 — `contextual.enrich` ghép prefix JSON vào `chunk.text` để embed, lưu `structure.search_context.original_text` + hash; `presentation.reading_text` và `projection.evidence_item` khôi phục nguyên văn; `execution._embed_pending` embed `row.text` (đã enrich).
- **Đo read-only** trên collection `col_da0fa3ca3177`, run `idx_f8d44c0ec319` generation 2 (`search_context_version = qnu.search-context/v1`): **301/301 chunk** có `search_context` và `original_text`, gồm 32 chunk bảng; mẫu có prefix 173 ký tự, `original_text()` khôi phục đúng và hash khớp.
- **Kết luận**: không cần reindex hay đổi schema cho cơ chế tách text; giữ nguyên generation đang phục vụ.
- **Kiểm chứng**: unit `test_contextual_scope_790.py` (nguồn/bằng chứng, scope, glossary, khôi phục `original_text` và từ chối structure bị sửa) trong batch 79 passed.

## 6. Chạy lại 10 câu sau P1–P5 (một lượt, model thật)

- API khởi động lại lúc `2026-11-11T16:07:45Z` để nạp P1–P4; P5 không đổi mã phục vụ. Tham số giữ nguyên phiên 935: collection `col_da0fa3ca3177`, workspace `ws_686011c2a0af`, `hybrid_rerank`, `top_k=5`, `candidate_k=30`, `rrf_k=60`, rerank `prv_adff3afa1648`, verification off, generation 2 `idx_f8d44c0ec319`, model `qwen3.8-27b-q4`/`prv_76af5b1d51eb`.
- Mỗi câu gửi đúng một lần, `PYTHONIOENCODING=utf-8`; kết quả `%TEMP%\qnu_e2e_935_p1p5_results.json`.

| Câu | 935 lần đầu | 937 (P0) | 938 (P1–P5) | Ghi chú |
| --- | --- | --- | --- | --- |
| Q1 | 502 | 502 | **PASS** | 200 `answered`, nêu 5800 và 1600 |
| Q2 | PASS | 502 | **FAIL** | 502 `answer_response_invalid`, vẫn lỗi hợp đồng model |
| Q3 | 502 | PASS theo token (còn trộn mục tiến sĩ) | **PASS** | 200, 51 ngành + 01 CLC Kế toán + 2 ngành dự kiến mở, không còn đoạn tiến sĩ |
| Q4 | PASS | 502 | **PASS** | 200, ngưỡng 18.0 và cách tính điểm trung bình 3 môn |
| Q5 | abstain sai | abstain | **FAIL** | `insufficient_evidence`, thiếu 730/24/2 đợt |
| Q6 | retrieval miss | abstain | **FAIL** | `insufficient_evidence`, vẫn thiếu `5.173` dù P1 tăng recall |
| Q7 | retrieval miss | abstain | **PASS** | 200, đủ 6 phương thức/mã, nêu loại trừ giáo viên với PT2/PT3 |
| Q8 | PASS kèm lỗi phụ | abstain | **PASS** | 200, đủ 83/97/112,3/1,5 lần |
| Q9 | 422 | 422 | **FAIL** | 422 `answer_context_budget_exceeded` |
| Q10 | 422 | 422 | **FAIL** | 422 `answer_context_budget_exceeded` |

- Tổng: **5/10 PASS theo bộ kiểm tra token** (935: 4/10; P0: 1/10). Thời gian 10 lượt gồm cả lỗi: trung bình 12,30 giây, trung vị 12,88, cao nhất 17,80.
- Q9/Q10 vẫn 422 tại `pack_messages`: envelope bắt buộc vượt 16.000 byte. P2 giảm ID lặp trong catalog nhưng không đặt trần tổng byte catalog, nên bảng lớn vẫn vượt ngân sách; đây là lỗi mở, không phải P1/P3.
- Q5/Q6 vẫn abstain; Q6 vẫn thiếu `5.173` nên chưa thể quy hết cho grounding — cần tách riêng recall/rerank và hành vi model ở vòng sau.
- Q2 là lỗi hợp đồng model (P3 chỉ làm rõ title/mã lỗi, không retry câu hỏi).

### Hiệu năng đo được (P4)

- Trung bình 7 câu có trace: retrieval 5.304 ms, context 2.080 ms, packing 0–16 ms, proof 658 ms, model_prepare 15–32 ms, generation 4.806 ms, validation 689 ms, total 14.359 ms.
- Trong retrieval: query embedding 246 ms, dense 85 ms, lexical 165 ms, phrase 174 ms, rerank 902 ms; `retrieval_ms` nội bộ 2.929 ms. Chênh lệch ~2,4 giây là `validate_results` cuối trong `search()`.
- Mỗi câu trả lời gọi `validate_results` khoảng 6 lần (2 checkpoint rerank, 1 cuối search, 1 proof, 1 trước khi gọi model, 1 `safety_check`); mỗi lần đọc manifest từ blob, đọc lại published bundle và băm toàn bộ chunk. Đây là chi phí ứng dụng lớn nhất, không phải Qdrant/FTS/model.
- Kết luận: P1–P5 cải thiện chất lượng và chẩn đoán nhưng **RAG chưa tối ưu hiệu năng**. Hướng tiếp theo (chưa triển khai): cache manifest/eligibility theo request và chỉ giữ một lần recheck trước dispatch, song song hóa dense/lexical/phrase, đặt trần catalog bảng cho Q9/Q10.
- Giới hạn: full Pytest **NOT RUN**; baseline lịch sử FAIL 4/1627 (phiên 928) giữ riêng; F13 vẫn mở; chưa commit/push/reindex; đây là kịch bản chẩn đoán một lượt, không phải benchmark.

## 7. Vòng tối ưu tiếp theo — ngân sách evidence, bỏ validate trùng, chạy lại 10 câu

### 7.1 Vì sao 422 dù Qwen có 163.840 token ngữ cảnh

- 422 `answer_context_budget_exceeded` phát sinh trong `pack_messages` khi envelope gửi model (narrative + bảng/cell catalog + evidence bắt buộc) vẫn vượt `RagPolicy.context_max_bytes` sau khi đã cắt các phần mở rộng tùy chọn. Mặc định cũ là **16.000 byte**; đây là giới hạn nội bộ của QNU, không liên quan `max_model_len: 163840` của `qwen3.8-27b-q4`.
- Đo trên trace Q9/Q10 của phiên 938: Q9 có envelope 17.800 byte (narrative 2, bảng 16.530, evidence 1.247; prompt 8.302 token); Q10 có 46.393 byte khi gồm 120 phần mở rộng, riêng phần bắt buộc là 19.910 byte (prompt 19.069 token). Cả hai vượt 16.000 byte trong khi số token vẫn rất thấp so với trần model.
- Sửa: mặc định `context_max_bytes` **16.000 → 32.000** (trần vẫn 128.000, không đổi); đồng bộ ba mặc định frontend từ 16.000 sang 32.000 (`features/rag/types.ts`, `features/rag/schemas.ts`, `features/assistants/assistant-form-dialog.tsx`). Không đổi prompt, retrieval, rerank hay guard.
- Sau sửa: Q9 và Q10 đều trả 200, không còn 422; Q10 dùng 71 phần mở rộng với prompt 12.838 token, vẫn rất xa trần 163.840 token.

### 7.2 Bỏ một lần validate trùng trong luồng answer

- `search(..., verify=False)` khi answer gọi retrieval; answer vẫn validate ngay sau packing (`proof`), recheck trước khi gọi model và `safety_check` sau sinh. Các checkpoint rerank giữ nguyên. Mục tiêu là bỏ lần đọc manifest/băm chunk trùng ở cuối `search()`, không nới guard nào.
- Test: thêm `test_answer_retrieval_forwards_skipped_final_validation` và mở rộng `test_added_reading_context_is_included_in_budget_before_dispatch`; cập nhật test mặc định ngân sách 32.000. Unit 54 + 104 đạt; integration cô lập **38 passed** (7:00), `db_dropped=true`, legacy sentinel preserved; Ruff đạt; frontend Biome + `tsc --noEmit` đạt.
- Chưa kết luận cải thiện tốc độ từ một lượt chạy; stage `proof`/`validation` vẫn chiếm ~0,6–0,9 giây mỗi câu.

### 7.3 Chạy lại 10 câu đúng kịch bản đóng băng (một lượt)

- Lần chạy đầu đọc nhầm `qnu_e2e_2pdf_state.json` (collection `col_b7f90da4422d` của E2E sau) nên **bị loại**, không dùng làm kết quả. Lần chạy đúng dùng `qnu_e2e_935_rag.py` với `col_da0fa3ca3177`/`idx_f8d44c0ec319`, generation 2, `hybrid_rerank`, `top_k=5`, `candidate_k=30`, `rrf_k=60`, rerank `prv_adff3afa1648`, verification off; API khởi động lại lúc 23:33 (giờ máy) để nạp mã mới. Kết quả: `%TEMP%\qnu_e2e_935_rag_results.json`; bản cũ được giữ tại `qnu_e2e_935_rag_results_1858.json`.

| Câu | 938 (16.000 byte) | Vòng này (32.000 byte) | Ghi chú |
| --- | --- | --- | --- |
| Q1 | PASS | **PASS** | 200, prompt 5.667 → 8.357 token |
| Q2 | PASS | **FAIL** | 502 `answer_response_invalid`, status/statements không khớp; cũng từng 502 ở 935/937 |
| Q3 | PASS | **PASS** | 200, prompt 5.313 → 8.348 token |
| Q4 | PASS | **FAIL** | 502 `answer_response_invalid`, cùng lớp lỗi hợp đồng model |
| Q5 | FAIL abstain | **FAIL** | vẫn `insufficient_evidence`, thiếu 730/24/2 đợt |
| Q6 | FAIL abstain | **FAIL** | vẫn thiếu `5.173` |
| Q7 | PASS | **FAIL** | abstain; prompt 5.764 → 9.105 token |
| Q8 | PASS | **FAIL** | abstain; prompt **giữ nguyên 4.156 token** nhưng đổi kết quả |
| Q9 | 422 | **FAIL** | 200 nhưng chỉ nêu IELTS, thiếu bảng VSTEP |
| Q10 | 422 | **PASS** | 200 `insufficient_evidence`, không nêu 15.00 (đạt probe) |

- Tổng: **3/10 PASS** (938: 5/10); thời gian trung bình 12,30 giây, trung vị 11,94, cao nhất 17,40.
- Prompt token tăng ở các câu có nhiều continuation: Q1 5.667→8.357, Q3 5.313→8.348, Q5 5.336→8.349, Q6 5.924→9.038, Q7 5.764→9.105. Nguyên nhân trực tiếp là ngân sách 32.000 cho phép thêm continuation (Q1 53→98, Q7 62→110). Q8 có prompt không đổi nhưng vẫn đổi từ answered sang abstain, cho thấy biến thiên của model là đáng kể và không thể quy toàn bộ chênh lệch cho ngân sách.
- Đánh giá trung thực: **422 đã hết** và Q10 đạt probe abstention; Q9 có câu trả lời nhưng vẫn thiếu bảng VSTEP do hợp nhất rerank/fusion (`ich_d2db494cb517` rerank hạng 2 nhưng fusion hạng 23, ngoài top-5) — lỗi chất lượng riêng, chưa sửa. Q2/Q4 là lỗi hợp đồng model (`ModelAnswer` status/statements không khớp, completion 38–54 token), không retry câu hỏi. Không tuyên bố cải thiện tổng thể: mẫu một lượt 3/10 so với 5/10, trong đó hai lỗi 502 và một ca prompt không đổi bị abstain cho thấy nhiễu model; cần A/B nhiều lượt mới kết luận.
- Hướng tiếp theo (chưa triển khai): tách ngân sách mở rộng tùy chọn khỏi ngân sách tổng (trần continuation riêng) để nới budget mà không tăng prompt tràn lan; A/B trọng số RRF/rerank cho Q9; điều tra lớp 502 contract bằng schema/prompt của model.
- Giới hạn: full Pytest **NOT RUN**; F13 vẫn mở; chưa commit/push/reindex; đây là kịch bản chẩn đoán một lượt, không phải benchmark.
