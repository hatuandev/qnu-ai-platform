# Phiên502 — Chọn đúng đoạn và đóng gói chứng cứ phục hồi RAG

## Yêu cầu và phạm vi

Rà luồng RAG liên quan ba lỗi của câu “Trường Đại học Quy Nhơn áp dụng những
phương thức xét tuyển nào?”, sửa mã rồi thử lại trên dữ liệu đã xuất bản.
Tiếp tục sau khi user mở lại Docker/stack. Dùng skill clean-code, backend,
rag-pipeline, rag-evaluation và modelops-resilience cho phần tương ứng.

Không đổi provider/model hay cấu hình DB; không migration, sửa nguồn, reindex,
restart/deploy hoặc Git commit/push. Giữ nguyên thay đổi các phiên trước.
Probe chỉ gửi inference đến provider nội bộ được xác nhận; policy vận hành
ModelOps mở lại ở phiên501 không bị đổi thành internal-only.

## Nguyên nhân xác minh

1. Canonical nguồn đang xuất bản có đoạn liệt kê đầy đủ PT1–PT5 và xét tuyển
   thẳng, block `ks_rev_8f3c2063c14e:1893:2512`, trang1. Không thiếu dữ liệu cho
   nội dung này. BM25 thích đoạn ngắn; đoạn trả lời nằm dưới heading đúng chủ đề
   nhưng có thể bị loại trước rerank. Chỉ tăng TopK không giải quyết thứ tự đóng gói.
2. Rerank dùng câu gốc có phần tên trường lặp; packing lại đổi thứ hạng theo lợi
   ích/độ dài, khiến đoạn chi phí lấn đoạn chính. Nhánh phục hồi còn trần riêng
   6.000 ký tự và ngân sách output riêng 1.600, không theo request/policy chung.
3. Audit hiển thị dùng trần12.000 riêng; validator thoát sớm khi sai ngữ nghĩa
   làm tập ID trả về thiếu, có thể báo sai nguyên nhân là ID không hợp lệ.
   Reflow whitespace của answer_quote cũng có thể bị từ chối dù chữ/số giữ nguyên.
4. Bỏ trần6.000 làm lộ giới hạn thật của model: serving window8.192 token. Request
   proposal phải giữ ngân sách output4.000; payload nhiều nguồn/metadata có thể
   vượt cửa sổ. Không thể coi36.000 ký tự là36.000 token hoặc bảo đảm vừa model.

## Thay đổi

- `prose_selection.py`: thứ tự theo độ phủ từ/cặp từ của chủ đề trong BODY;
  thứ hạng ngang nhau giữ thứ tự reranker. Đây là hint, không phải chứng minh
  ngữ nghĩa. Dedup chỉ text trùng khít và cùng nguồn/hash/scope/heading/record.
- `prose_fallback.py`: ghép có giới hạn candidate BM25 với children của heading
  bằng helper có sẵn; chỉ nhận prose đủ điều kiện và áp lại lọc năm. Không biến
  heading, filename hay năm ký thành fact. Rerank theo topic ngữ nghĩa; không
  đổi thứ tự lần nữa bằng coverage/chi phí ưu tiên đoạn ngắn. Dùng limit/budget
  cấu hình, không min6.000/min1.600 riêng; không sửa giá trị trong DB/UI.
- Giữ list/dependency group nguyên vẹn. Chỉ sau lỗi `MODEL_CONTEXT_EXCEEDED`
  ở proposal mới thử lại MỘT lần bằng nhóm chứng cứ ưu tiên nguyên vẹn; giữ
  question/plan/output budget, không cắt câu hay list, không đổi provider.
  Nếu nhóm không nhỏ hơn/không vừa hoặc vẫn lỗi thì trả lỗi, không giả no-data.
  Claim binding, independent verifier và coverage audit vẫn bắt buộc.
- `evidence_context.py`, `evidence_passages.py`, `evidence_claims.py`,
  `evidence_indexed_audit.py`: compact opt-in cho prose. Metadata theo block,
  câu nguồn không sửa; whole_passage_id là alias cùng catalog server. Có
  whole_text khi catalog bỏ fragment dưới3 ký tự để không mất nội dung.
  Bỏ field rỗng/null, giữ false/0/unknown. Luồng khác mặc định dùng payload cũ.
- `response_audit.py`: dùng budget cấu hình; tách kiểm tra ID khỏi verdict sai,
  thêm số đếm mismatch an toàn; chỉ chuẩn hóa whitespace cho so khớp span.
  Không sửa dấu/chữ/số/phủ định và không cho verdict false vượt kiểm chứng.
- Regression mới `tests/test_prose_selection_502.py`; cập nhật assertion ngân
  sách request của `tests/test_rag_prose_recovery_491.py`, không nới grounding.
- Runner `scripts/probe_prose_502.py`: chỉ primary nội bộ đã lưu, chặn cloud,
  cho phép Qdrant cấu hình đọc-only, bypass cache riêng trong process. Inspect
  chỉ xuất ID/count/length, không chép corpus/prompt/credential vào artifact.

## Kiểm chứng đã chạy

CWD các lệnh Python/Ruff: `backend`, Python3.12 trong `.venv` hiện có.

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_prose_selection_502.py tests/test_rag_prose_recovery_491.py tests/test_rag_batch_492.py tests/test_evidence_claims.py tests/test_evidence_contracts_500.py tests/test_rag_webui_501.py -q --tb=short -p no:cacheprovider --basetemp <unique-storage-directory>
.\.venv\Scripts\ruff.exe check app/modules/rag/prose_selection.py app/modules/rag/prose_fallback.py app/modules/rag/response_audit.py app/modules/rag/evidence_claims.py app/modules/rag/evidence_context.py app/modules/rag/evidence_passages.py app/modules/rag/evidence_indexed_audit.py scripts/probe_prose_502.py tests/test_prose_selection_502.py tests/test_rag_prose_recovery_491.py
.\.venv\Scripts\python.exe -m scripts.probe_prose_502 --live --question 'Trường Đại học Quy Nhơn áp dụng những phương thức xét tuyển nào?'
.\.venv\Scripts\python.exe -m pytest -q --tb=short -p no:cacheprovider --basetemp <unique-storage-directory> --junitxml=storage/prose502-verified.xml
```

- Regression cuối: **132 PASS**, 5,51s, exit0. Ruff cuối **PASS**, exit0.
- Có thử trước khi user mở lại stack: Postgres connection refused, chưa inference.
- Trong8 probe của cùng câu ở các mốc code:6 lỗi context;1 answered nhưng harness
  chặn nhầm Qdrant nên chỉ lexical; cuối1 answered với full hybrid và cache bypass.
  Các lần dense0 không dùng để nghiệm thu full hybrid hoặc quy lỗi cho Qdrant.
- Lần cuối: dense12/lexical12/fused21/rerank21/returned5, hai tài liệu, không
  degradation. Draft chính vẫn bị audit bác; không ép accepted=true.
  Prose recovery lấy đúng đoạn PT1–PT5, chạm cửa sổ thật rồi repack nhóm nguyên vẹn;
  verifier nhận6 claim, missing/errors/rejections rỗng, status answered.
- Nội dung hiển thị: năm2026, PT1/100, PT2/200, PT3/402A, PT4/402B, PT5/405 và
  xét tuyển thẳng. **6 trích dẫn từ1 văn bản**, không phải6 tài liệu. Không còn
  câu từ chối chung ở cuối. Đối chiếu thủ công nội dung với chính đoạn canonical.
- Sidecar metadata không chép raw corpus:
  `backend/storage/prose502-acceptance.json`. Chưa chụp full snapshot fingerprint
  trong sidecar; không tuyên bố benchmark frozen hoàn chỉnh hay Recall@K.
- Full lần đầu: **1845 PASS /11 FAIL /17 SKIP**, exit1,203,37s;
  `backend/storage/prose502-full.xml`. Exact failure IDs khớp baseline501.
  Khi rà diff phát hiện corner case fragment ngắn trong compact alias, đã vá,
  thêm regression; vì mã đổi sau collection nên chạy lại full gate cuối.
- Full gate cuối: **1846 PASS /11 FAIL /17 SKIP**, exit1,194,99s;
  `backend/storage/prose502-verified.xml`. JUnit đối chiếu baseline501: exact11
  failure IDs khớp, không phát sinh failure ID mới; **tổng suite vẫn FAIL**.
- UTF-8/no-BOM/LF trên file batch, JSON sidecar hợp lệ và diff whitespace **PASS**.

11 failure IDs nền đối chiếu JUnit, không sửa trong batch:

```text
tests.test_consulting_dispatcher::test_dispatch_admissions_with_export
tests.test_consulting_dispatcher::test_dispatch_regulations_with_export
tests.test_publishing_v2_cutover_and_gc::test_gc_api_endpoint
tests.test_publishing_v2_cutover_and_gc::test_canary_policy_get_and_update_api
tests.test_publishing_v2_decommissioning_and_system_gc::test_direct_upload_blocked_when_flag_disabled
tests.test_publishing_v2_decommissioning_and_system_gc::test_direct_upload_allowed_when_flag_enabled
tests.test_publishing_v2_decommissioning_and_system_gc::test_rest_api_system_wide_gc_and_decommissioning_audit
tests.test_publishing_v2_e2e_canary::test_api_routes_canary_and_rollback
tests.test_rag_data_truth_and_lifecycle::test_reconciliation_detects_discrepancies
tests.test_trust_boundary_and_hitl::test_auth_session_cookie_actor_claims
tests.test_universal_tools::test_dispatch_admissions_with_dynamic_facts
```

## Rà thêm: giới hạn chưa xử lý

- Draft hybrid vẫn có thể sai hoặc audit trả ID/span chưa hợp lệ; thành công lần
  này là phục hồi canonical được kiểm chứng, không phải mọi model call đã ổn.
- Generator có supplemental context nhưng audit chỉ giữ candidate pinned. Không
  tự biến neighbor chưa có provenance đầy đủ thành trích dẫn để vượt gate.
- Phục hồi một nhóm sau overflow không bảo đảm câu so sánh/nhiều nhóm đều trả lời
  được; thiếu facet vẫn phải từ chối. Chưa có preflight tokenizer/window dùng
  chung đáng tin; không suy token bằng số ký tự hay bảo đảm tránh mọi HTTP400.
- Chưa thay thuật toán list_groups toàn cục hoặc trần tải canonical2 triệu ký tự.
  Mốc6.000 của split_source_blocks là chia block, khác trần context đã bỏ.
- **NOT RUN**: WebUI, Docker build, benchmark10/20/82, model ngoài và log serverAI.
  Không suy độ chính xác80% hay production-ready từ một câu hỏi đạt.
- Kiểm tra cờ reload tiến trình Windows bị Access denied; chưa xác nhận WebUI/BE
  đang chạy đã tự nạp mã cuối. Không tự nâng quyền hoặc restart để kiểm chứng điều này.

Không cần upload lại tài liệu/reset DB cho batch này. Bàn giao mã và bằng chứng,
chưa tự restart hoặc deploy.
