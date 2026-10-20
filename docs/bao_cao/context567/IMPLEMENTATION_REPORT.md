# Context567 — Phạm vi sửa mã và giới hạn

## Ranh giới dữ liệu

Đây là sửa đường trả lời RAG trên nguồn published có sẵn. Không tạo revision, sửa canonical Markdown/JSON, ghi lại facts/chunks, đổi embeddings, reindex hoặc publish. Parser và Quality Gate giữ nguyên. Các module Context564–565 và thay đổi chưa commit của người dùng được giữ.

## File và hành vi

| Vùng | File chính | Hành vi |
|---|---|---|
| Ràng buộc câu hỏi | [query_constraints.py](../../../backend/app/modules/rag/query_constraints.py), [temporal_answer.py](../../../backend/app/modules/rag/temporal_answer.py), [service.py](../../../backend/app/modules/rag/service.py) | Thu nhiều đại lượng; đơn vị explicit; ý hỏi hiện tại thắng stale rewrite; ràng buộc được đối chiếu trước chọn ô |
| Định danh theo nguồn | [source_fact_resolution.py](../../../backend/app/modules/rag/source_fact_resolution.py), [entity_codes.py](../../../backend/app/modules/knowledge/entity_codes.py) | Đối chiếu tên/mã/hàng tổng bằng raw JSON và canonical rows; không coi catalog classifier là proof; scalar0 không tự thành mã |
| Nối tiếp | [conversation_resolution.py](../../../backend/app/modules/rag/conversation_resolution.py), [conversation_router.py](../../../backend/app/modules/rag/conversation_router.py), [intent_rules.py](../../../backend/app/modules/rag/intent_rules.py) | Year-only sửa trên prior user question cùng scope; không dùng assistant prose làm fact; literal reference chỉ sửa địa chỉ khi duy nhất |
| Trường bảng phụ | [row_answer.py](../../../backend/app/modules/rag/row_answer.py), [row_answer_contract.py](../../../backend/app/modules/rag/row_answer_contract.py), [source_rows.py](../../../backend/app/modules/rag/source_rows.py) | Text/date/state có thể được chọn; giữ literal measure label; identifier có underscore không bị coi như câu tự nhiên bỏ dấu |
| Danh sách đầy đủ | [source_identity_enumeration.py](../../../backend/app/modules/rag/source_identity_enumeration.py) | Hai model calls chỉ chọn closed schema IDs; server lấy giá trị từng hàng đã chứng minh; blank/duplicate/unresolved identity hoặc count/budget mismatch không được bỏ qua |
| Context văn bản | [source_labels.py](../../../backend/app/modules/rag/source_labels.py), [prose_selection.py](../../../backend/app/modules/rag/prose_selection.py), [prose_fallback.py](../../../backend/app/modules/rag/prose_fallback.py) | Gợi lại body caption/formula và literal row; locator/input kịch bản không thành fact demand; full ranked rule trước table summary; giữ whole dependencies |
| Unknown và thông điệp audit | [evidence_blocks.py](../../../backend/app/modules/rag/evidence_blocks.py), [evidence_claims.py](../../../backend/app/modules/rag/evidence_claims.py), [evidence_model.py](../../../backend/app/modules/rag/evidence_model.py), [evidence_indexed_audit.py](../../../backend/app/modules/rag/evidence_indexed_audit.py) | Truyền trạng thái cell chưa rõ để không dùng làm supplemental semantic proof; source denial/unknown có thể là câu trả lời hợp lệ; không tính thiếu biến bằng0 |
| Citation trước audit | [canonical_candidates.py](../../../backend/app/modules/rag/canonical_candidates.py) | Candidate phải khớp duy nhất binding/index/source/hash/unit và chứa body nguyên văn; không sửa OCR để cố khớp; citation dùng đúng source span |
| Audit từng mệnh đề | [response_audit.py](../../../backend/app/modules/rag/response_audit.py) | Source-owned bodies cho đoạn ngắn, exact-subquote cho đoạn dài; every answer span có verdict; scope/conditions/conflict/numeric checks giữ |

## Source-owned audit contract

Private contract mới `IndexedVisibleSpanAudit` không yêu cầu model chép lại quote hoặc lặp lại root summary có thể mâu thuẫn các verdict. Nó chỉ nhận đáp ứng câu hỏi, giữ điều kiện, conflict, missing constraints và một check cho mỗi answer span. `evidence_id` là Literal của các body đã ghim; `answer_span_id` phải đủ, không thiếu/trùng/ngoài tập.

Server tự tính tập proof IDs từ các check và dùng body nguồn nguyên văn làm quote. Không có field global mà model được phép gửi để nâng một verdict âm thành dương. Field lạ, ID sai hoặc check thiếu vẫn bị schema chặn. Verdict `entailed=false` hoặc `relevant=false` vẫn làm toàn câu thất bại; đủ span chưa thay kiểm tra completeness/scope/condition/conflict.

Một body ngắn nguyên vẹn vốn đã là quote hợp lệ trong contract cũ; thay đổi loại bỏ bước model chép lại numbering/formatting. Nếu có body dài hơn4000 ký tự thì giữ exact-subquote contract cũ; không cắt ngắn nguồn để biến thành proof. Budget context/output và retry không tăng.

Canonical binding trước bước này bảo đảm source text thực, không dùng search prefix làm bằng chứng. Citation cuối lấy lại đúng block đã audit; không dựa vào heuristic word overlap để tạo quote khác.

## Những bảo vệ vẫn bắt buộc

- Source hash, source/index revision, manifest, published snapshot và actor authorization.
- Code/name/row/column/year/metric/unit phải cùng tuple; không đổi tên gần giống hoặc lấy năm khác bù.
- Không diễn giải ký hiệu chưa định nghĩa hoặc dùng unknown thành0.
- Không dùng model selector hoặc prompt input làm quyền ghi/duyệt nguồn.
- Partial/conflicting/ambiguous numeric answers không được rửa qua prose fallback.
- Nhóm proof phụ thuộc phải nguyên vẹn và đúng source. Opt-in whole first group có thể nhiều physical blocks hơn K như cơ chế đã có; giới hạn byte vẫn cứng. Không đổi cấu hình K.

## Test doubles và tương thích

Các orchestration unit tests có DB AsyncMock không giả làm kho nguồn thật: [rag_test_proofs.py](../../../backend/tests/rag_test_proofs.py) cung cấp literal candidate/source boundary riêng cho tests kiểm format/cache/history/routing. Không đưa helper này vào app hoặc benchmark. Các source/hash/revision negative controls vẫn gọi code binding thật với nguồn fixture kiểm soát.

Wire fixture507 cập nhật shape private contract mới, vẫn kiểm nguyên text và cả hai verdict true/false. Long-quote compatibility có regression riêng. Test DB concurrency guard dùng environment test, loopback và strict nonce DB-name regex thay vì chỉ tên một context cũ.

Cache key của code lên verified-answer-v5 để không đọc lại câu đã được cache trước sửa proof. Không flush Redis hoặc đổi cache policy persisted.

## Giới hạn còn thực tế

Điểm benchmark cuối chỉ vừa đạt85%, còn9 FAIL. Không coi đây là chứng minh mọi lỗi đã hết. Ba nhóm cần tiếp tục nếu tăng mục tiêu:

1. Source scope và dependency closure: semantic rank cao có thể chọn đoạn nhóm chung trước quy định ngoại lệ cụ thể, làm budget bị chiếm dù raw source đủ. P06 là ví dụ còn thất bại; tăng context model không tự sửa liên kết này.
2. Độ đầy đủ của diễn giải: model có thể bỏ qualifier/điều kiện, từ chối quá mức hoặc thêm khẳng định sai. P03/P07/P08/P11/P15 được chấm FAIL dù có hoặc đã tìm đúng nguồn. Proof binding chỉ chứng minh nơi lấy text, không thay kiểm nghĩa.
3. Lý do từ chối: X05/X08/X09 không bịa số nhưng chưa giải thích đúng ràng buộc thiếu. Cần trình bày nguyên nhân từ typed decision một cách có căn cứ, không hardcode đáp án theo test ID.

Xem [bảng từng ca](CASE_COMPARISON.md), [kết quả benchmark](BENCHMARK_REPORT.md) và [kiểm thử](VALIDATION_REPORT.md). Không triển khai thêm thay đổi chỉ để vượt tiêu chí hoặc loại các ca khó khỏi mẫu số.
