# Phiên 945 — RAG trả lời đúng nguồn đã xuất bản: xác minh số theo hàng, neo fusion, giữ thứ tự rerank và E2E ba tài liệu mới

- **Yêu cầu / giả định.** Người dùng yêu cầu cải thiện RAG trong `backendV1/` để câu trả lời đúng, đủ và dẫn đúng nguồn đã xuất bản, dùng pipeline và model ModelOps hiện hành. Phải kiểm chứng bằng luồng thật upload → duyệt → xuất bản → index → hỏi, với ba tài liệu mới: PDF text tiếng Việt, PDF scan và DOCX. Không tăng `top_k`/`context_window`/ngân sách prompt toàn cục, không thêm một lời gọi LLM cho mỗi câu, không re-index hay đổi parser/chunking khi chưa có bằng chứng lỗi nằm ở đó. Q05 phải chứng minh `93,3` gắn **An toàn thông tin – 2026 – Mức đạt / Tỷ lệ (%)**; Q07 phải buộc `1233`/`1149` vào **TỔNG CỘNG** đúng cột 2026; Q08 không được mất `127`; Q09 phải đủ sáu chương trình nhóm A, không lẫn nhóm B; Q13 không được làm rơi chunk công thức sau rerank.

## Nguyên nhân và cách sửa

### 1. Q05/Q07/Q09 — xác minh số theo hàng, không chỉ theo tập số

- Bảng 1 phiên 940 (`ev_p006_b002`, 16×12) có header ba tầng gộp ô. Sau sửa multitier phiên 943, dữ liệu đã chọn được ô, nhưng lớp kiểm tra số cho bảng **unselectable** vẫn gộp mọi số của mọi hàng thành một tập. Vì vậy một số đúng ở hàng khác/năm khác/nhóm khác vẫn có thể “chứng minh” cho câu sai, hoặc ngược lại guard từ chối oan.
- `cells.py` nay tách **per-fact binding**: `_row_facts`, `_claim_binds`, `_table_support`, `_clause_claims`. Mỗi số trong câu phải khớp **đúng hàng chủ thể** và **đúng cột/năm/metric** của ô nguồn; năm trong câu có thể lấy từ header đã dẫn làm phạm vi cột, nhưng không được lấy số từ hàng khác. Số chỉ nằm trong hàng header hoặc hàng khác bị từ chối.
- `materialize` không còn 502 toàn bộ khi chỉ một phần câu sai: giữ các câu đã xác minh, bỏ riêng câu có số không xác minh, thêm `Requirement(status="missing")` và ghi `trace.grounding.materialization` (`dropped_statements`, `dropped_numbers`). Khi **không còn câu nào** xác minh được thì vẫn 502 `answer_table_value_not_extractive`; guard không bị nới.
- Catalog mượn header đã chứng minh từ fragment cùng `source_table_citation` (kể cả fragment dữ liệu không có link riêng), giữ các tầng header đã được chứng minh dù fragment chỉ đánh dấu một phần. Không re-index; chỉ chạy ở tầng trả lời trên canonical bundle.

### 2. Q08 — neo định danh chính xác trong fusion

- Trước sửa, chunk chứa `AM-0029`/`127` có trong lexical top-30 nhưng bị RRF ba nhánh đẩy ra khỏi `candidate_k`; reranker không bao giờ thấy nó.
- `hybrid.py` thêm `exact_anchors`/`anchor_match`: định danh có cả chữ và số (ví dụ `AM-0029`) hoặc mã bắt đầu bằng `0` là neo chính xác. `fuse` giữ tối đa **2 slot cuối** cho ứng viên khớp neo, không tăng `candidate_k`, không nhân bản hit. `search.py` phát `fusion_anchor_count`/`fusion_anchor_ids` trong trace. Quy tắc suy từ query, không phải từ điển hay ngoại lệ theo tài liệu.

### 3. Q13 — cross-encoder là thứ tự cuối, RRF chỉ chọn pool

- Trước sửa, sau rerank còn trộn thêm một lớp RRF (`RERANK_WEIGHT=2.0`, `RERANK_RRF_K=30`) nên chunk công thức ở hạng 2 của cross-encoder bị đẩy khỏi `top_k`.
- `hybrid.py` bỏ lớp RRF thứ hai và `RERANK_WEIGHT`/`RERANK_RRF_K`; `select_reranked` lấy trực tiếp thứ tự cross-encoder, khử trùng, giới hạn `top_k`. RRF vẫn chỉ dùng cho pool trước rerank. Trace đổi `rerank_fused_ids` sang danh sách đã chọn và thêm `ranking.rerank_selected`/`score_kinds.rerank_selection`.

## File sửa

- `backendV1/qnu/domains/rag/answer/cells.py` (+480/−…): xác minh số theo hàng/cột/metric, giữ câu đúng và báo phần thiếu, mượn header gia đình/multitier.
- `backendV1/qnu/domains/rag/answer/service.py` (+5): truyền `report` và gắn `trace.grounding.materialization`.
- `backendV1/qnu/domains/knowledge/index/hybrid.py` (+89/−…): neo định danh, giữ slot fusion, bỏ RRF sau rerank.
- `backendV1/qnu/domains/knowledge/index/search.py` (+12): truyền neo và trace.
- Test: `backendV1/tests/unit/test_table_row_attribution_944.py` (mới, 12 hàm), `backendV1/tests/unit/test_fact_attribution_946.py` (mới, 17 hàm), `test_hybrid_fusion_938.py` (+72), `test_unselectable_prose_941.py` (+8), `test_answers_api_648.py` (+4), `test_hybrid_655.py` (+3).
- Tài liệu: `docs/WORK_LOG.md`, `docs/nhat_ky/README.md`, `docs/memory/PROJECT_CONTEXT.md`, nhật ký này và snapshot `docs/memory/snapshots/2026-11-12_session_945.md`.

## Đo trước / sau (hai vòng, cùng snapshot)

Môi trường: `ws_39c202a81045`, collection phiên 940 `col_0daa6e0ed137`, index `idx_bfd36fae5a30` generation 1 (465 chunk, không re-index), `hybrid_rerank`, `top_k=5`, `candidate_k=30`, `rrf_k=60`, embedding bge-m3, rerank `bge-reranker-v2-m3` (`prv_8f5c1f17c932`), chat `qwen3.8-27b-q4` (`prv_902ce43408bb`), prompt `qnu.rag.answer/v28`, grounding `qnu.answer-cells/v5`.

| Câu | Trước sửa | Sau sửa (2 vòng) | Bằng chứng ô |
|---|---|---|---|
| Q05 | Phiên 940 abstain sai; phiên 943 chỉ 1/2 (vòng 2 502 do gán `93,3` cho mảnh chỉ-header) | **2/2 answered + token** | `E1:r7:k8`, ô `ev_p006_b002_c07_07` = `93,3`; chủ thể `A Công nghệ, số hóa / An toàn thông tin`; cột `2026 / Mức đạt / Tỷ lệ (%)` |
| Q07 | Phiên 940 abstain sai | **2/2** | `E1:r15:k6` = `1233` (`c15_04`, `2026 / Quy mô / Chỉ tiêu (SV)`); `E1:r15:k7` = `1149` (`c15_05`, `2026 / Ghi nhận / Số lượng (SV)`); chủ thể `TỔNG CỘNG (12 chương trình)` |
| Q08 | Chunk nhóm B rơi khỏi fusion; trước sửa fusion 0/2, `127` mất, `2027` bị materialize bỏ, coverage `partial` | **2/2** | `E10:r13:k10` = `127` (`c13_09`; header `c00_03`, `c01_07`, `c02_07`); chủ thể `B Quản trị, xã hội / AM-0029 / Kế toán số`; cột `2027 / Dự kiến / Ước tính (SV)` |
| Q09 | Phiên 940 abstain sai | **2/2** | Sáu chương trình nhóm A: Kỹ thuật phần mềm, Công nghệ thông tin ứng dụng, Khoa học dữ liệu, Quản trị dữ liệu số, An toàn thông tin, Thiết kế truyền thông số; không có tên nhóm B |
| Q13 | Chunk công thức `ich_18e57e5dec06` ở rerank hạng 2 nhưng bị selection loại | **2/2** | Chunk công thức vẫn ở rerank hạng 2 và được dẫn trong câu trả lời |

Token/thời gian (vòng 1 / vòng 2): Q05 4416/5,75 s và 4416/7,70 s; Q07 2970/5,89 s và 3053/8,29 s; Q08 9430/9,49 s và 9473/10,17 s; Q09 4122/7,61 s và 4068/6,78 s; Q13 3298/9,35 s và 3415/10,68 s.

## Kiểm tra bổ sung trên mã cuối

Sau khi hoàn thiện lớp xác minh per-fact (18:31), chạy lại một lượt trên cùng corpus phiên 940:

- Q05, Q07, Q08 đều `answered`, lần lượt 4416, 2990, 9501 token; Q05 giữ `E1:r7:k8`, Q07 giữ `E1:r15:k6`/`E1:r15:k7`, Q08 giữ `E10:r13:k10`.
- Q13 `answered` 3391 token/9,46 s, chunk công thức vẫn ở rerank hạng 2 và được dẫn.
- **Q09 trả HTTP 502 `answer_citation_invalid`** (“Citation không thuộc bằng chứng đã cấp”) — lỗi hợp đồng đầu ra của model, không phải lỗi provider/hạ tầng và không phải lỗi xác minh số. Đây là lần thử đầu tiên trên mã cuối; **không chạy lại để làm xanh**. Trên build đo hai vòng trước đó Q09 đã đạt 2/2; unit Q09 vẫn đạt. Rủi ro còn lại (đính chính 2026-11-12 theo bản ghi `answer.validation_failed`): model thỉnh thoảng **lặp lại một evidence_id hợp lệ trong cùng một statement** (`duplicate` tại `statements[0].evidence_ids`; không có `not_allowed`), đặc biệt ở câu liệt kê — không phải citation ngoài tập evidence.

## E2E ba tài liệu mới

### Fixture và luồng thật

| Loại | Tệp / SHA-256 | Nguồn / revision / OCR | Version / publish | Kết quả index |
|---|---|---|---|---|
| PDF text | `quyet_dinh_27_qd_hb_hoc_bong_2026.pdf`, `64109a0b7caf13f48e53837e90a56660180c8c1fc9bb42b1267e627668cf54d3` | `src_dae49d7db771` / `rev_e76a228331a4` / `ocr_fb81cd7a0e41` | `cver_490bf454751b` / `pdec_86ddb0b2bac9` | `idx_4a4482f00dd0` gen 2, 34 chunk |
| PDF scan | `thong_bao_08_tb_dt_xet_tuyen_bo_sung_2026.pdf`, `08a572e4d093ef139f13ea507be5e6fe09fd1f5c2f456f0115edc1949125d761` (0 ký tự text, 1 ảnh) | `src_602751c3a8b7` / `rev_99f973e19076` / `ocr_fd748d3a32ab` (MinerU) | `cver_6fd31092901e` / `pdec_f90486eb5331` | readiness `ready`, cùng generation |
| DOCX | `ke_hoach_12_kh_dt_chi_tieu_2027.docx`, `e975e03599d0907ef23882bd1db3ec376fd573e838f2e5f497e6fc834872baf8` (bảng native 3 cột) | `src_e037db588d29` / `rev_a2298f96f677` / `ocr_0fba46dbb781` | `cver_5530a838bbd5` / `pdec_b58938b2ed1f` | readiness `ready`, cùng generation |

Collection cô lập `col_a41c290efff5` trong `ws_39c202a81045`; cả ba nguồn đã qua text-review (không sửa, API trả 409 `ocr_text_unchanged` nên dùng OCR gốc version 0), compile source-first, đăng ký, submit → approve (`review_skip`) → publish, index tự động generation 2. Không đụng dữ liệu thật hay collection khác.

### Bảy câu hỏi (một lượt, không retry)

| ID | Tài liệu | Câu trả lời | Token | Thời gian | Kết quả |
|---|---|---|---|---|---|
| D1 | PDF text | Tổng kinh phí học bổng năm 2026 là `2.480.000.000` đồng, tương ứng `124` suất | 3448 | 9,32 s | PASS |
| D2 | PDF text | Hạn nộp hồ sơ là `16 giờ 30 phút ngày 25/09/2026`; hồ sơ muộn không được xem xét | 2967 | 6,42 s | PASS |
| S1 | PDF scan | Chỉ tiêu xét tuyển bổ sung đợt 2 năm 2026 là `185`; điểm chuẩn tạm thời Khoa học dữ liệu là `21,75` | 2812 | 9,31 s | PASS |
| S2 | PDF scan | Nhận hồ sơ từ `05/10/2026` đến hết `12/10/2026` | 2278 | 7,13 s | PASS |
| C1 | DOCX | Trí tuệ nhân tạo — Chỉ tiêu năm 2027: `95` | 2303 | 7,62 s | PASS |
| C2 | DOCX | Hệ thống thông tin — Chỉ tiêu năm 2027: `120` | 2344 | 6,57 s | PASS |
| R1 | PDF text | `insufficient_evidence`, `reason=model_abstained`, không có nguồn, không bịa học phí | 2900 | 6,56 s | PASS (từ chối đúng) |

Xác minh dẫn chứng: mọi `version_id` được dẫn đều là ba version đã xuất bản ở trên; `publication_decision_id` khớp; tải nội dung nguồn trả HTTP 200 và SHA-256 khớp fixture; evidence unit có mặt. DOCX có proof ô `E1:r3:k2` = `95` (Trí tuệ nhân tạo, Chỉ tiêu năm 2027) và `E1:r2:k2` = `120` (Hệ thống thông tin, Chỉ tiêu năm 2027). OCR scan có biến thể nhận dạng lành tính `MÔ PHỒNG` cho `MÔ PHỎNG`; các số `185`, `21,75` và ngày tháng đều trích đúng.

## Kiểm chứng kỹ thuật

- **Unit thuần (mã cuối):** `pytest tests/unit/test_hybrid_fusion_938.py tests/unit/test_unselectable_prose_941.py tests/unit/test_multitier_table_941.py tests/unit/test_table_row_attribution_944.py tests/unit/test_fact_attribution_946.py -q` → **66 passed** trong 1,79 giây. Riêng hai tệp mới `test_table_row_attribution_944.py` + `test_fact_attribution_946.py` là **33 ca** (29 hàm, 4 parametrized), cũng đạt.
- **Ruff check:** 11 tệp production/test đã sửa → `All checks passed!`.
- **Ruff format --check:** báo 4 tệp sẽ được định dạng lại (`hybrid.py`, `test_hybrid_655.py`, `test_fact_attribution_946.py`, `test_table_row_attribution_944.py`); **chưa áp** để không sửa tệp khi full pytest của phiên khác đang chạy. Đây là lỗi style, không phải lỗi hành vi.
- **Các nhóm trọng tâm trong phiên:** 81 ca liên quan đạt (trước đó 262 ca trọng tâm đạt) trên DB cô lập; không chạy lại để làm xanh.
- **Full Pytest cô lập: NOT RUN** — tiến trình `PID 18888` của phiên khác vẫn đang chạy trên DB `qnu_v1_test_d6c2ecc0ed1c4064`; không can thiệp. Baseline lịch sử **FAIL 4/1627** (phiên 928: 2× `test_integration_gateway_pipeline.py`, `test_legacy_source_deletion_718.py`, `test_rag_verification_policy_672.py`) giữ riêng; **NOT RUN ≠ PASS**.
- **XLSX: NOT RUN** — không có fixture/đường kiểm thử XLSX trong đợt này.

## Rủi ro / bước sau

- `verification.mode = "off"`, `status = "not_run"` trong mọi trace trả lời; việc chấm số/ô/nội dung do harness bên ngoài đối chiếu evidence unit, draft cells và byte nguồn tải về, không phải runtime verifier.
- Q09 có thể trả 502 `answer_citation_invalid` khi model phát citation không hợp lệ (lần thử trên mã cuối; **đính chính 2026-11-12:** bản ghi sự kiện cho thấy dạng lỗi là `duplicate` — lặp một ID hợp lệ, không có `not_allowed`); cần theo dõi và xử lý riêng ở lớp hợp đồng model, không hạ guard và không retry.
- Q05/Q07/Q08 đã được xác nhận lại trên mã cuối; Q09/Q13 chưa chạy lại đủ hai vòng trên mã cuối (Q13 đã đạt một lượt; Q09 một lượt 502). Không tuyên bố độ bền 2/2 cho mã cuối.
- Chưa commit/push; giữ nguyên thay đổi và tệp chưa theo dõi của các phiên trước. Không re-index, không đổi mặc định retrieval, không sửa parser/chunking.
- Nhãn câu hỏi và kết quả E2E là kiểm chứng kỹ thuật, không phải benchmark chất lượng toàn diện; full suite vẫn chưa có kết quả cuối.
