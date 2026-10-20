# Context564 — RAG thực tế

**PARTIAL / REVIEWED_FACT_E2E_BLOCKED.** Câu hỏi đoạn văn đã trả lời có trích dẫn qua backend thật; câu hỏi chỉ tiêu AM-0007 chưa đạt. Không suy từ closure unit tests sang thành công trả lời số liệu.

## Môi trường và nguồn cố định

Development/local; actor development admin đã được xác minh qua cơ chế auth hiện hành, không override quyền. Nguồn đang published: collection `col_admissions`, binding `bnd_fa71a57c9cf1`, source `ks_rev_ca1e7f16d9e0`, index `idx_rev_967891af9d5d`, generation `vg_a6e3190d11af`. Không tạo index, publish lại, thay cấu hình hoặc restart dịch vụ.

Primary thực chạy là `qwen3.5-9b` / `prov_rtx5090_vllm`. Không tăng context 32K, top-K hoặc budget. Embedding/Qdrant/reranker dùng cấu hình hiện hành. Trong batch ASGI cuối, các spies chỉ chuyển tiếp vào hàm gốc để đếm call, không thay response. Batch TCP gọi backend đang chạy tại `127.0.0.1:8001`, không instrumentation.

`evidence_policy.enabled=false` trong cấu hình trợ lý hiện tại được giữ nguyên. Câu hỏi số liệu đi qua fact/table decision rồi prose fallback; không tự bật full evidence pipeline để thay đường chạy thực tế.

## Cases cuối qua ứng dụng thật và providers thật (ASGI)

Mọi case dưới đây dùng cùng published snapshot. ASGI là kiểm chứng thành phần thật qua app; bằng chứng transport TCP được ghi riêng phía dưới. Tất cả HTTP 200, **không còn 409 trong batch cuối**. Latency là wall time của request, không phải SLA.

| ID / câu hỏi | Intent; thực thi | Bằng chứng và kết quả | ms | Đánh giá |
|---|---|---|---:|---|
| E2E-01: tài liệu mô phỏng có giá trị áp dụng thực tế không? | KNOWLEDGE; retrieve 1, sparse 1, dense 1, embed 1, Qdrant 1, rerank 2, Qwen generate 5 | Answered; `VERIFIED_PROSE_FALLBACK`, closure/projection PASS, citation hash/revision/quote hợp lệ | 11002,14 | LOCAL_INTEGRATION_PASS với upstream thật; TCP cũng PASS |
| E2E-02: chỉ tiêu **SV**, AM-0007, năm 2026? | KNOWLEDGE; fact/table + canonical prose, rerank 1, Qwen 2; dense/Qdrant không chạy | `NO_COMPATIBLE_FACT_EVIDENCE`, insufficient_context; packed 5 canonical blocks, 0 reviewed facts, closure PASS nhưng **không chứng minh fact answer** | 3557,14 | **FAIL mục tiêu Reviewed Fact E2E** |
| E2E-03: Xin chào | SOCIAL; 0 retrieval/Qdrant/model | Answered tự nhiên, không citation cần thiết | 124,75 | PASS social isolation |
| E2E-04a: Cảm ơn, cùng conversation E2E-02 | SOCIAL; 0 retrieval/model | Không xóa chủ đề | 134,71 | PASS |
| E2E-04b: Còn năm 2025? | KNOWLEDGE_FOLLOWUP; rewrite giữ AM-0007/SV và đổi đúng năm; rerank 1, Qwen 3 | insufficient_context; closure PASS, không 409; chưa có số liệu/citation | 4637,14 | Routing/memory PASS; **fact answer chưa đạt** |
| E2E-05: chỉ tiêu AM-0007 riêng năm 2098, không dùng năm khác | KNOWLEDGE; fact/prose, rerank 1, Qwen 2; dense/Qdrant không chạy | insufficient_context; closure PASS, không mượn số năm khác/citation giả | 2717,20 | PASS chống trả sai năm; revision negatives ở fixture |
| E2E-06: email riêng của trưởng chương trình AM-0007? | KNOWLEDGE; retrieve 1, sparse 1, dense 1, embed 1, Qdrant 1, rerank 2, Qwen 2 | insufficient_context; không bịa email/citation, closure PASS | 3993,01 | PASS thiếu bằng chứng |

E2E-01 chứng minh các stage đã thực thi, nhưng answer cuối đến từ canonical prose fallback sau retrieval. Không tuyên bố câu trả lời được sinh trực tiếp từ dense hit. E2E-02/04/05 không có dense calls; trường `requires_rag=true` không đủ để kết luận vector retrieval đã chạy.

K=5/36000 giữ nguyên. Fact probe chọn 6 ranked groups, từng group 5 blocks và có source row. Prose path có ngoại lệ `allow_first_whole_group` từ trước; E2E-05 giữ nguyên nhóm 7 physical blocks, diagnostic `whole_group_exceeds_block_k=true`, character budget vẫn cứng. Không thêm ngoại lệ mới; số physical blocks có thể khác body K do heading.

## Xác nhận qua TCP backend đang chạy

Một conversation mới, 5 requests qua API thật; `/health/live` 200. Usage audit xác nhận **8 Qwen3.5-9b success calls**, không fallback trong batch TCP. Không thể gán số call từng stage từ transport TCP riêng; bảng ASGI có instrumentation cung cấp bằng chứng stage tương ứng.

| ID | Case | HTTP / status | Citation | ms | Đánh giá |
|---|---|---|---|---:|---|
| TCP-03 | Xin chào | 200 / answered | 0 | 176,98 | LIVE_E2E_PASS cho social |
| TCP-01 | Câu hỏi giá trị áp dụng như E2E-01 | 200 / answered | **1**, kiểm lại exact binding/index/source/hash/quote trên published blocks đạt | 10976,28 | **LIVE_E2E_PASS cho canonical text** |
| TCP-02 | AM-0007/SV/2026 | 200 / insufficient_context | 0 | 2419,55 | **FAIL fact answer** |
| TCP-04a | Cảm ơn | 200 / answered | 0 | 131,39 | PASS |
| TCP-04b | Còn năm 2025? | 200 / insufficient_context | 0 | 2276,91 | Context retained; numeric E2E chưa đạt |

Không browser automation trong Context564; không gọi TCP checks là UI E2E. Citation PASS yêu cầu citation tồn tại; không lấy `all([])` làm PASS.

## Blocker độc lập còn lại

Read-only probe cùng câu hỏi cho `entity_codes=[]`, `target_entities=[]`, attribute `expected_quota`. Fact lookup thực trả **39 facts**, trong đó canonical row tương ứng có 9 facts; không phải kho rỗng hay không đủ context model. `temporal_answer` không gắn được mã AM-0007 với thực thể vì analysis chưa nhận mã alphanumeric và câu hỏi không chứa tên thực thể đầy đủ; decision là `NO_COMPATIBLE_FACT_EVIDENCE`.

Ngoài ra, projection facts ở dòng đó gán cùng `expected_quota` cho cả cột chỉ tiêu SV và cột số lượng/ghi nhận SV. Đây là rủi ro metric binding cần kiểm riêng; không phải lỗi đọc mất canonical row, và chưa chứng minh là nguyên nhân trực tiếp của mọi refusal. Canonical literal và gold nguồn vẫn phân biệt các cột/năm. Gold giữ private, không sao chép corpus vào Git.

Không sửa Intent Router/query classifier/semantic annotation hoặc dữ liệu published để ép ca này PASS. Bước tiếp theo cần phạm vi riêng cho source-backed entity code resolution và metric-role matching, sau đó chạy lại đúng E2E-02/04 với cùng source/revision và đối chiếu giá trị literal.

## Lượt trung gian và cleanup

Lượt đầu có ca wrong-year 409 do list member bị thêm mà thiếu footnote; đây là lỗi tích hợp packing thứ hai đã sửa, có red tests và batch cuối xác minh lại. Một thử nghiệm diễn đạt cột khác ở giữa batch gặp `provider_request_failed` rồi fallback Luna theo policy sẵn có bị invalid audit contract; lượt đó FAIL, không phải bằng chứng context overflow và không thay cấu hình để né lỗi. Các receipts lịch sử vẫn giữ.

Private evidence: `backend/storage/context564/live-verified/`, `tcp-results.json`, `tcp-usage.json`, `final-audit.json`; cleanup receipts xác nhận 11 threads/8 gap records thuộc ca kiểm thử đã xóa, usage audit giữ lại. Hash của toàn bộ collection/binding/revision/index và cấu hình kiểm trước/sau khớp. Runtime Storage test bị policy chặn xóa; không bypass.

