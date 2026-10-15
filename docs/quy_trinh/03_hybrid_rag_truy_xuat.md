# QUY TRÌNH 03: TRUY VẤN HYBRID RAG & CHỐNG BỊA ĐẶT (HYBRID RAG & ANTI-HALLUCINATION RETRIEVAL FLOW)

Tài liệu này đặc tả cơ chế tìm kiếm hỗn hợp (Dense Vector + Sparse Lexical), thuật toán dung hợp thứ hạng Reciprocal Rank Fusion ($k=60$), tái xếp hạng Cross-Encoder và chốt chặn bảo vệ trích dẫn (Citation Guardrail).

## Chat RAG trực tiếp và bốn ưu tiên chất lượng — phiên 443

Đối với trợ lý hỏi đáp chọn `execution_mode=rag`, endpoint chat/SSE gọi trực tiếp RAG, không tạo workflow execution. Workflow vẫn dùng riêng cho tác vụ/công cụ/HITL; không đưa DAG trở lại để thực hiện truy hồi bổ sung.

1. **Kiểm chứng điều kiện theo vai trò**: audit phân biệt số/ngưỡng/giờ/đơn vị bắt buộc, số liệu hiện tại, định danh phương thức, năm dữ liệu, năm văn bản và năm sự kiện. Vai trò mặc định giữ kiểm tra số nghiêm ngặt. `current_value` chỉ dùng cho một đại lượng hiện tại được hỏi: nhận diện số hiệu/ngày tài liệu theo hình thái; phần so sánh gắn văn bản có ngày cũ hơn không trở thành số bắt buộc của đại lượng hiện tại. Không áp dụng cơ chế này cho điều kiện đầu vào, công thức, hạn chót hoặc yêu cầu so sánh. `method_identity` cho phép alias chữ-số của phương thức, không thay thế chứng cứ cho mã chính xác khi người dùng hỏi mã. Các vai trò do audit ngữ nghĩa xác định, không phải chứng minh quyền ưu tiên nguồn; vẫn cần verifier độc lập, same-source binding và source preferences cùng applicability tuple.
2. **Truy hồi lai đa biến thể và giữ cụm cấu trúc**: tối đa bốn truy vấn có câu gốc, biến thể và các trường ngữ cảnh đã phân giải. Không thêm số/mã/năm từ phản hồi thiếu căn cứ. Mỗi truy vấn gọi hybrid thật trong session đọc riêng, cùng tenant/workspace và snapshot; các xếp hạng BM25/ngữ nghĩa được hợp nhất bằng RRF và rerank qua ModelOps đã cấu hình. Session bị hủy không làm hỏng transaction đọc nguồn. Metadata unit/span được dùng để ánh xạ anchors; chỉ mục cũ thiếu metadata dùng page anchors + lexical ranking như tín hiệu, không phải chứng cứ tự xác nhận.
3. **Tìm bổ sung tối đa một lượt**: khi proposal `missing` hoặc audit thiếu coverage, truy hồi lại theo phần thiếu nhưng giữ câu hỏi, trường đích, mùa/năm và snapshot. Không truy cập web. Chỉ đề xuất/kiểm chứng lại khi context thật sự có block mới; context không đổi thì không lặp sinh đáp án. Mâu thuẫn hoặc cần hỏi lại không kích hoạt truy hồi này. Claims partial được giữ khi còn đúng identity/span và kiểm chứng lại cùng draft mới; lỗi DB/model/JSON/timeout vẫn là lỗi dịch vụ, không giả thành thiếu dữ liệu. Deadline tổng không được gia hạn.
4. **Đóng gói theo độ phủ và chống lặp**: thứ tự đóng gói dùng greedy coverage giảm dần cho các thành phần truy vấn, giữ chi phí/độ liên quan. Đây là heuristic retrieval, không phải semantic proof hay tỷ lệ đúng. Cụm mục đánh số + nhánh chữ cái và parent metadata được giữ nguyên khối, kể cả qua trang, dừng ở mục ngang cấp/heading khác trong cùng binding/index/source/hash. Với bullet là các lựa chọn độc lập, câu hỏi focused chỉ cần phần dẫn + mục được chọn; yêu cầu enumeration vẫn giữ đủ danh sách. Nhóm không vừa ngân sách bị loại và ghi log, không cắt mất nhánh. Đoạn trích nhỏ nằm hoàn toàn trong đoạn đã chọn cùng nguồn được loại lặp; không gộp chéo năm/revision hoặc mất câu điều kiện nằm trong đoạn lớn. Nhánh được chọn còn phải gắn proof của phần dẫn vào references và hiển thị phần dẫn nguyên văn để verifier không kiểm tra giá trị ngoài phạm vi quy định.

Năm trong ngày ban hành/số hiệu không tự xác lập mùa dữ liệu. Header năm cùng nguồn không ghi đè năm lịch sử ghi rõ hoặc data-year đã verified. Trích dẫn vẫn trả raw span/hash, không dùng projection embedding. AnswerDecision ghi `corrective_retrieval_attempted`, `corrective_new_block_ids`, `repair_history` và timings; lỗi JSON chỉ lộ tên contract/field không hợp lệ, không lộ prompt/key/raw response.

Sau projection, backend gắn thêm header mùa thật trong cùng binding/index/source/hash cho năm dữ liệu yêu cầu; không phụ thuộc model có tự chọn passage header hay không. Header không trở thành câu trả lời và không ghi đè scope historical/verified. Feedback tìm bổ sung cho phép năm mặc định đã được plan validate; không cho bịa giá trị trả lời mới.

Các ví dụ/ca tuyển sinh nằm trong kiểm thử, không tạo từ điển FAQ, tên model, số liệu hay alias hardcoded trong runtime. Không cần reset, reindex hoặc xuất bản lại để dùng thay đổi đọc này; worker/API cần chạy phiên bản code mới. Bộ 20 câu đối soát và kiểm tra span không thay thế TM-08 hoặc kiểm định độc lập toàn bộ 82 câu.

## Kiểm chứng đủ ý, phạm vi nhóm và tính dùng được — phiên 444

1. **Missing tự bịa không chặn completeness**: `missing_constraints` tự do mà mọi con số đã có trong claims (phép cộng/tổng mới ngoài ý định hỏi, trừ số người dùng đã nêu) chỉ là ghi chú tư vấn, không ép partial; thiếu số chưa trích hoặc thiếu không số vẫn chặn. Qualifier `retained_by` rỗng được bù khi hợp claims đã đủ proof số/method; trỏ claim lạ vẫn là gap; proof năm giữ nghiêm; ref không số/không alias-digit (như URL) không được auto-retain.
2. **Hàng đơn lẻ không chứng minh cả nhóm**: mọi claim đều `reviewed_fact` mà không claim canonical-thực-chất nào và không hàng nào trùng thực thể hỏi thì partial kèm phạm vi đã chứng minh; muốn kết luận nhóm phải trích đoạn chính sách nhóm hoặc ghi rõ phần thiếu, giữ nguyên "một số" không suy rộng.
3. **Nối câu qua trang/chunk**: khối trước dở câu (không kết bằng `.!?…:;`), khối sau cùng nguồn/cùng section/kề thứ tự mở đầu chữ thường, không heading/marker/container thì đóng gói và projection cùng nhau (tối đa 2); chữ hoa/heading/list là dừng. Mục đánh số còn nhóm cả đoạn tiếp nối không marker (dòng công thức, "Trong đó:") và dãy bullet định nghĩa sau dấu hai chấm, tối đa 8 khối.
4. **Công thức phải dùng được**: câu hỏi công thức mà claim trích glyph công thức nhưng anh em cùng nhóm cấu trúc (chú giải biến, điều kiện) chưa trích thì partial; có thì trình bày nguyên văn công thức + chú giải + chỉ Phụ lục, thiếu đầu vào thì nói rõ, không bịa số.
5. **Nơi đăng ký thiếu locator là partial**: câu hỏi vị trí mà trích dẫn có số hiệu văn bản nhưng không có token URL thì partial "chưa có đường dẫn hoặc địa chỉ cụ thể được trích dẫn"; tuyệt đối không tự tạo URL và không lấy cổng chung đắp vào thông báo riêng.

## Ngữ cảnh thời gian và cấu trúc dùng chung — phiên 432

QueryPlan tách `years` (kỳ dữ liệu), `document_years` và `event_years`. Ví dụ hỏi số liệu 2023 trong báo cáo 2026: năm dữ liệu lọc là 2023, không phải cả 2023/2026. Không ghi vai trò năm nào thì tiếp tục chính sách năm hiện tại của trợ lý; năm rõ trong câu hỏi phải được giữ. Kế hoạch tự đổi/bịa năm trả lỗi `EVIDENCE_PLAN_SCOPE_INVALID`.

Dense/FTS và BM25 chỉ lọc scope data verified theo manifest chung. Năm được nhắc, năm tiêu đề hoặc ngày ban hành không đủ để loại cứng. Fact lịch sử có scope riêng, không bị scope năm văn bản thay thế. Unknown/proposed vẫn cần verifier; không mặc nhiên được xác nhận. Retrieval lọc sau khi lấy ứng viên nên corpus lớn có thể cần tăng độ phủ hoặc bổ sung pushdown filter sau đo lường.

Evidence đọc raw span với ID/hash revision và manifest pin từ index, không lấy projection embedding làm quote. Context bổ sung các cha/header có chứng cứ trong cùng nguồn, không lấy đoạn lân cận không liên quan. Digest không khớp trả `EVIDENCE_UNIT_INVALID`; dữ liệu verified trái năm yêu cầu không được xác nhận chỉ vì verifier trả supported. Header/cell lặp mơ hồ tiếp tục yêu cầu đối soát.

Chưa chuyển chỉ mục thật sang cấu trúc mới. Dùng candidate snapshot của staging đã build để test trước khi publish; không reset nguồn hoặc tự suy ra scope verified cho tài liệu cũ. Kiểm thử kỹ thuật riêng không thay thế đối soát câu trả lời với corpus thực tế. Xem [nhật ký phiên 432](../nhat_ky/2026-10-14_phien_432_don_vi_nguon_va_ngu_canh_thoi_gian.md).

## Nhánh chứng cứ opt-in — phiên #417

Trợ lý bật `knowledge_policy.evidence_policy.enabled` dùng luồng: planner → published manifest → hybrid anchors + BM25/RRF đoạn nguyên bản và hàng facts đã duyệt → reranker ModelOps → đề xuất claims/quotes → kiểm chứng độc lập → AnswerDecision. Không tái OCR, ghi facts suy đoán, nạp lại embedding hoặc tự xuất bản. Nhánh legacy giữ nguyên cho trợ lý không bật chính sách này. Nhánh mới bỏ qua cache câu trả lời cũ; namespace policy fingerprint v4.

- Planner giữ entity/attribute/year/method/round/event; năm không ghi rõ dùng năm hiện tại theo múi giờ Việt Nam khi quản trị chọn `current_year`, nêu rõ trong câu trả lời. Câu độc lập không lấy năm từ lịch sử không liên quan. Năm của tên tệp/ngày ban hành không chứng minh năm của ô dữ liệu.
- Đọc đúng tenant/workspace, binding/index/source revision đã pin, active/ready, parity/review/hash hợp lệ. Đoạn giữ page và offset nguyên bản. Hàng bảng được nhóm theo revision/table/row/year, dùng giá trị authoritative trong `knowledge_facts`, không lấy ô raw cũ đè ô đã hiệu đính. Raw table bị loại khi chỉ mục có manifest facts. Không truy vấn entity bằng unigram hay từ điển vá câu hỏi.
- Ngân sách hiện tại: nguồn canonical tối đa 2 triệu ký tự; facts tối đa 5.000 ô; shortlist mặc định 24, context 10 khối/36.000 ký tự. Quá ngân sách báo lỗi rõ, không trả chứng cứ giả. Chỉ khối được chọn được gửi vào mô hình; đọc corpus cho ranking không đồng nghĩa đưa toàn kho vào prompt.
- Mỗi claim có quote liên tục khớp chính xác với khối định danh; mọi số phải xuất hiện trong quotes của chính claim. Tất cả references của một claim cùng source revision; so sánh nhiều nguồn dùng nhiều claims. Kiểm chứng riêng entailment, relevance, scope và coverage; Decimal chỉ xác minh số, không tự chứng minh thuộc tính/đơn vị/phương thức.
- `source_preferences` lưu quan hệ ưu tiên do con người xác nhận theo immutable source IDs và năm, chỉ áp dụng khi cùng applicability tuple. Phiên này quản trị xác nhận TB 1906 cập nhật ưu tiên flyer đầu mùa cho cùng thông tin năm 2026. Flyer vẫn giữ thông tin riêng và lịch sử. Preferred evidence phải nằm trong snapshot/context; không có bằng chứng cùng tuple thì báo mâu thuẫn/thiếu, không dùng tên file để phân xử.
- `supported/partial/missing/conflict/clarify` quyết định cả text và citations. Thiếu ngữ cảnh không đồng nghĩa Trường chưa công bố. Partial chỉ hiển thị claims đủ căn cứ và nêu phần thiếu; lỗi DB/provider/JSON/timeout giữ mã lỗi hạ tầng, không đổi thành no-answer. JSON sai được sửa định dạng tối đa một lần; deadline đối soát mặc định 90 giây.
- API direct RAG không tin `runtime_policy` do client gửi; tải policy trợ lý từ DB của cùng kho/tenant khi collection bật evidence. Reranker dùng provider/model được quản trị chọn qua ModelOps, không tải reranker về laptop.

Bổ sung cuối phiên #417: phân giải policy dựa trên collection đã lưu, kể cả khi `module_code` trống hoặc mặc định `general`; không cho né guard bằng bỏ mã phân hệ. DB lỗi, khác tenant/workspace hoặc policy trợ lý chưa bật khi kho yêu cầu evidence đều fail-closed. `persona_scope` lấy từ cấu hình quản trị, chỉ xác định trường đang tư vấn/phạm vi chủ đề, không làm chứng cứ cho số liệu; trường tổ chức kỳ thi không tự thay thế trường đích.

Khớp quote cho phép duy nhất reflow khoảng trắng và phải trả lại span nguyên bản không mơ hồ; không sửa từ/số để ép khớp. Truy hồi danh sách mở rộng các đoạn liền kề theo cú pháp đánh số/bullet và dừng khi gặp văn xuôi/heading, không dùng từ điển nghiệp vụ. Nếu toàn bộ claims bị loại vì binding, cho một lần đề xuất sửa từ cùng evidence; kiểm tra quote/same-source/số và verifier độc lập vẫn bắt buộc, deadline tổng không được gia hạn. Lý do loại và `quote_repair_attempted` được lưu trong AnswerDecision; sửa thất bại vẫn missing, không giả thành supported.

Đây là chốt chặn và contract kiểm chứng, không phải chứng nhận mọi câu trả lời đúng ngữ nghĩa. Cần đối soát chất lượng độc lập và bổ sung nguồn chuyên đề còn thiếu; không tự tắt guard để tăng tỷ lệ answered.

Sửa thêm khi chạy test #417: đóng gói body + heading cùng nguồn như cặp nguyên tử, tính cả JSON metadata trong ngân sách và ưu tiên slot cho reviewed rows thay vì cắt phần đuôi sau khi thêm headings. Tên trường/ngày ban hành dạng mixed-case label không được chọn làm season-heading chỉ vì tỷ lệ chữ hoa cao. Facts có shortlist riêng từ câu gốc, plan/entity/attribute/variants và được rerank ngữ nghĩa riêng qua chính AI server ModelOps, không chỉ append top BM25.

Ngân sách tương tác `retrieval_timeout_seconds` mặc định10s và `rerank_timeout_seconds`3s, cấu hình được trong evidence policy; không đổi timeout chung của provider/OCR/worker. Hybrid anchors dùng session read-only riêng để cancellation không phá transaction đọc canonical/facts. Hết thời gian chỉ giữ corpus rank trên nguồn đã pin và facts thật; không fake CE score, embedding hay catalog seed. Verifier vẫn bắt buộc; DB nguồn/facts lỗi vẫn lỗi dịch vụ, không nhận no-answer thay lỗi. Timeout tổng90s ghi substage planning/retrieval/proposal/verification trong log/lỗi để phân biệt nguyên nhân.

Rowidentity là chốt bổ sung: `entity_name` lấy từ rowfacts đãduyệt, khôngphải entitydoLLMđoán. Quote và claim dùng reviewed row phải giữ tênthựcthể đó (NFC/case/whitespace normalization). Không được chỉquote ô20 rồi viếtcho toàn nhóm. CommonDAGintegrity cũngkiểmtra; semantically broad/negation/condition vẫnphải qua verifier và đốisoát độc lập, rowguardkhôngbảođảm mọi suy luận đúng.

## Contract runtime — cập nhật #370

- **#382**: Reranker threshold dùng raw `relevance_score`, không dùng RRF hoặc thuộc tínhscore thiếu. Malformed response không scored-success, giữ degradation RRF khi lỗi. Citation title ưu tiên tên nguồn. Facts API chỉ trả activeindex/binding và Excellegacy active, nhậnsourcefactdocument_idnull.
- **Candidate QA #382**: endpoint Knowledge preview yêu cầu actorupdate/scopedcollection, backend dựng manifest readyindices đúngactive sourcerevision. RAG khôngcheckcandidate bằngservingpointer, dùnginternal flag cho stagingallowlist, pin cùngsnapshotdense/sparse/facts/neighbors, bỏsemanticcache, khôngswap/publish. UI dùngModelOpsmặc định, không tương đươngDAGpolicy trợ lý. Question test chưa làautomatedqualitygate; noanswer/citationrelevance/auditmodelthực chưa hoàn thiện.

- **Ngừng nguồn (#373)**: binding paused bị loại khỏi snapshot mới bởi điều kiện active; tăng collection index_epoch và binding active_epoch làm cache/snapshot cũ mất hiệu lực cho yêu cầu mới. Không xóa/deactivate Qdrant khi pause, giữ artifact cho snapshot đã pin của câu trả lời đang xử lý. Không thu hồi được câu trả lời đã gửi hay đảm bảo hủy lượt inference đang chạy. Mọi nguồn đã ngừng vẫn bị loại khi xuất bản generation mới; facts/neighbors dùng cùng snapshot active. Không coi index pointer còn lưu là bằng chứng nguồn đang phục vụ.

- API RAG search/ask/facts lấy tenant/workspace từ actor đã xác thực, không dùng phạm vi tùy ý trong body. Snapshot kiểm tra ownership kho và khóa index revisions; fact lookup trực tiếp cũng chỉ dùng revisions đã xuất bản.
- Ask gửi đúng tenant/assistant code, model/provider/fallback và conversation vào ModelOps một lần. ModelOps tự xử lý failover/quota/keys. Lỗi `ALL_PROVIDERS_UNAVAILABLE`/quota được giữ nguyên, lỗi bất ngờ bọc `LLM_GENERATION_FAILED`, nội dung model rỗng bị từ chối. Không đổi outage thành trích đoạn answered/cache. Thiếu candidates/facts vẫn là `insufficient_context`, khác lỗi hạ tầng.
- Cache v2 hash canonical request policy: prompt, provider/model/fallback, assistant revision, generation limits, reranker và runtime policy; vẫn kèm tenant/workspace/history/snapshot/epoch. Không reuse namespace v1. Fingerprint này không tự theo dõi mọi thay đổi nội bộ DB provider/defaults; cập nhật policy trợ lý/cấu hình request hoặc invalidate cache khi đổi defaults ngoài request.
- Lexical hiện là weighted ILIKE + FTS/unaccent, chưa BM25. Tên/mã nguồn được khớp thêm từ chunk_metadata của snapshot. Neighbors dùng binding/index_revision/chunk_index hoặc page adjacency cho nguồn độc lập, không inner join legacy documents trên nhánh binding. Giữ active binding và scope snapshot; context neighbors chỉ làm nền, không tự thành citation.
- Vector materialization mới lưu tên tệp, số văn bản và chunk_index vào metadata DB/Qdrant. Chỉ mục cũ không được tự ghi lại/publish; nếu metadata cũ thiếu cần build/publish có chủ đích. Không phụ thuộc object Repository.
- Nhánh tư vấn chuyên biệt đọc facts cùng scope/published revision snapshot, không lấy facts của bản bóc tách chưa xuất bản; không tự nâng insufficient_context thành answered bằng guidance.

Giữ fallback reranker sang RRF nếu reranker lỗi; không đồng nhất điều đó với fallback câu trả lời LLM. Không thay OCR/chunking/publication và chưa bổ sung BM25 trong đợt này.

---

## 1. Sơ Đồ Quy Trình Xử Lý Truy Vấn RAG

```mermaid
flowchart TD
    Q([Câu hỏi người dùng]) --> G1[1. Input Safety Guardrail]
    G1 -->|Phát hiện Prompt Injection / Jailbreak| DENY[Từ chối trả lời & ghi log vi phạm an ninh]
    G1 -->|Hợp lệ| G2[2. PII Redaction: Che mờ CCCD, SĐT, Email]
    
    G2 --> FACT_STEP{3. Tra cứu Structured Fact Layer?}
    FACT_STEP -->|Tìm thấy bản ghi trùng khớp mã ngành / học phí| FACT_FOUND[Lấy thông số thực tế từ DB bảng facts]
    FACT_STEP -->|Không có trong fact layer| HYBRID_SEARCH
    
    subgraph HYBRID_RETRIEVAL [4. Tìm Kiếm Lai Đa Tầng (Hybrid Retrieval)]
        HYBRID_SEARCH[Đồng thời kích hoạt 2 động cơ tìm kiếm]
        HYBRID_SEARCH -->|Dense Vector Search: BGE-M3 1024D| QD[(Qdrant Vector DB)]
        HYBRID_SEARCH -->|Sparse Lexical Search: FTS tiếng Việt| PG[(PostgreSQL FTS)]
        
        QD -->|Top Dense Candidates| RRF[5. Reciprocal Rank Fusion - RRF k=60]
        PG -->|Top Sparse Candidates| RRF
        
        RRF -->|Danh sách ứng viên dung hợp| RERANK[6. Cross-Encoder Reranker: BGE-Reranker-v2-m3]
        RERANK -->|Nếu Reranker offline / timeout| FALLBACK_RRF[Graceful Fallback: Giữ nguyên thứ hạng RRF]
        RERANK --> TOP_CHUNKS[Top 3-5 Chunks liên quan nhất]
        FALLBACK_RRF --> TOP_CHUNKS
    end

    TOP_CHUNKS --> CIT_GUARD{7. Kiểm định Citation Guardrail}
    CIT_GUARD -->|Điểm liên quan < ngưỡng hoặc thiếu chứng cứ| NO_ANSWER[8. No-Answer Policy: Từ chối lịch thiệp & cung cấp Hotline Tuyển sinh 0256.3846.156]
    
    CIT_GUARD -->|Hợp lệ| PROMPT_BUILD[9. Answer Format Planner: Lắp ráp Prompt thông minh]
    FACT_FOUND --> PROMPT_BUILD
    
    PROMPT_BUILD -->|Gửi Prompt| LLM_GATEWAY[10. ModelOps LLM Gateway: gpt-4o-mini / gemini-1.5-flash]
    LLM_GATEWAY --> OUT_GUARD[11. Output Safety Guardrail: Quét rò rỉ API key / Prompt nội bộ]
    OUT_GUARD --> FINOPS[12. FinOps Cost Tracker: Tính toán Token & Chi phí USD]
    FINOPS --> RES([13. Trả câu trả lời kèm Trích dẫn Nguồn & Gợi ý câu hỏi])
```

---

## 2. Chi Tiết Kỹ Thuật Từng Bước

### Bước 1 & 2: Bảo vệ An ninh & Dữ liệu Riêng tư (Guardrails)
- **Input Safety Guardrail**: Quét phát hiện tấn công Prompt Injection (`Ignore all previous instructions...`, `Reveal system prompt...`).
- **PII Data Redaction**: Tự động nhận diện và che mờ các thông tin nhạy cảm của thí sinh/sinh viên trước khi gửi sang LLM (CCCD thành `077******988`, SĐT thành `0912***678`, Email thành `sin***@qnu.edu.vn`).

### Bước 2.5: Phân Loại Ý Định Truy Vấn & Định Tuyến Ưu Tiên Số Liệu (Fact-First Query Routing)
- **Phân biệt paraphrase tổ hợp môn vs xét tuyển thẳng (phiên #183)**:
  * Câu hỏi mơ hồ `"ngành CNTT cần những môn học nào để xét tuyển"` được chuẩn hóa thành `"tổ hợp môn"` trước retrieval; `QueryClassifier` ánh xạ `môn + xét tuyển/ngành` sang `fact_attributes=["subject_combinations"]` khi không chứa marker `học sinh giỏi / tuyển thẳng / ưu tiên xét tuyển`.
  * Truy vấn HSG / tuyển thẳng giữ nguyên để không lấn át Phụ lục 1; truy vấn ngày tháng thuần túy không bị ép Fact-First.
- **Tra cứu ngược theo tên môn + token ILIKE đặc thù (phiên #184)**:
  * `QueryClassifier.SUBJECT_PATTERNS` bóc tách tên môn chuẩn (`toán/lý/hóa/sinh/văn/sử/địa/tiếng anh/tin...`) vào `QueryAnalysis.subject_names` khi có ngữ cảnh `tổ hợp` hoặc `môn + xét tuyển`; đại từ `anh` trần và truy vấn HSG bị loại trừ.
  * `select_ilike_tokens()` tách từ bằng regex `\w+` (hết dính dấu phẩy `toán,`), loại âm tiết chung (`các/ngành/xét/tuyển/hợp/môn`) để token đặc thù dẫn dắt ILIKE thay vì 3 token đầu chung chung.
- **Bộ phân loại ý định thông minh (`QueryClassifier`)**:
  * Phân tách câu hỏi thành 3 nhóm ý định chuyên biệt (`QueryIntent`):
    - `EXACT_FACT`: Tra cứu số liệu cụ thể (mã ngành `7\d{6}`, chỉ tiêu, điểm chuẩn, học phí, quy đổi IELTS/VSTEP, mã nhiệm vụ `\d+\.\d+`, đơn vị chủ trì, hạn hoàn thành).
    - `NARRATIVE`: Câu hỏi giải thích chính sách, quy chế đào tạo, thủ tục nhập học, văn bản hướng dẫn.
    - `MIXED`: Câu hỏi tổng hợp đòi hỏi cả số liệu cụ thể kèm văn cảnh diễn giải.
  * **Trích xuất thực thể miền sâu (Domain Entity Extraction)**: Tự động bóc tách các mã định danh chuẩn (`entity_codes` như `7480107`, `6.8`, `certificate_conversion`) và danh mục thuộc tính nghiệp vụ (`fact_attributes` như `expected_quota`, `cutoff_score`, `lead_unit`, `end_date`, `converted_score`).
- **Chiến lược điều phối tìm kiếm thích ứng (Intent-tailored Retrieval Strategy)**:
  * Khi `is_fact_first = True` (thuộc `EXACT_FACT` hoặc `MIXED`):
    - Hệ thống ưu tiên tra cứu trực tiếp từ `KnowledgeFact` qua `lookup_facts` với bộ lọc `entity_codes` và `fact_attributes`.
    - Kết quả số liệu được định dạng thành Markdown Table chuẩn và đưa lên vị trí trang trọng nhất (`BẢNG SỐ LIỆU ĐÃ XÁC THỰC`) trong ngữ cảnh cung cấp cho LLM.
    - Với `EXACT_FACT`, hệ thống thu gọn phạm vi Hybrid Retrieval (`top_k=4`, `rerank_top_k=3`) nhằm tránh hiện tượng văn bản thừa làm loãng hoặc xung đột với số liệu chính xác.
  * Với `NARRATIVE`, hệ thống mở rộng Hybrid Retrieval (`top_k=8`, `rerank_top_k=5`) để bao quát đầy đủ các điều khoản và quy định liên quan.

### Bước 3: Ưu Tiên Tuyệt Đối Bảng Sự Thật (Structured Fact Layer) & Ràng Buộc Vòng Đời Tài Liệu
- Tra cứu bảng `knowledge_facts` trên PostgreSQL kết hợp `outerjoin` với `knowledge_documents`.
- **Ràng buộc Vòng đời Phê duyệt (Document Lifecycle Binding)**: Chỉ trích xuất facts gắn với tài liệu ở trạng thái đã kiểm duyệt và hiệu lực (`status in ["approved", "completed", "processed", "ready"]` và `is_active = True`) hoặc các facts số liệu độc lập không gắn tệp (nhập qua bảng tính Excel/CSV). Tuyệt đối loại trừ 100% facts từ tài liệu đang chờ duyệt hoặc đã lưu trữ.

### Bước 3.5: Cơ Chế Lập Chỉ Mục Qdrant An Toàn Theo Phiên Bản (Revision-Safe Qdrant Indexing)
- **Staging Revision**: Khi tài liệu có bản sửa đổi mới (`document_revision`), các chunks mới được tính toán vector và nạp vào Qdrant với `is_retrievable = False` và `document_status = "indexing"`. Revision cũ vẫn tiếp tục phục vụ tìm kiếm bình thường mà không bị gián đoạn (Zero Downtime).
- **Parity Verification (`verify_revision_parity`)**: Trước khi công bố, hệ thống đối soát tự động số lượng points trong Qdrant có cùng `document_id` và `document_revision` với số chunks trong PostgreSQL. Nếu phát hiện lệch số lượng hoặc thiếu metadata, quá trình kích hoạt bị chặn đứng ngay lập tức (Fail-Fast).
- **Kích hoạt nguyên tử (`activate_document_revision`)**: Chỉ khi parity đạt 100%, hệ thống cập nhật đồng loạt payload sang `is_retrievable = True` và `document_status = "ready"`.
- **Dọn dẹp an toàn revision cũ (`purge_stale_revisions`)**: Sau khi revision mới đã active thành công, hệ thống xóa bỏ các points thuộc các revision cũ hơn (`document_revision < current_revision`), triệt tiêu 100% hiện tượng "vector ma" (ghost chunks).
  * Tương tự, `search_sparse_fts` và `lookup_facts` trên PostgreSQL cũng chỉ truy xuất các bản ghi thuộc tài liệu có `status.in_(["ready", "approved"])`, `is_active=True`, bảo đảm tính đồng thuận và nhất quán 100% giữa 3 nguồn dữ liệu.
- **Công thức Reciprocal Rank Fusion kết hợp Trọng số Pháp lý (Legal Priority Weighted RRF)**:
  $$RRF\_Score(d) = \left( \sum_{m \in \{Dense, Sparse\}} \frac{1}{k + rank_m(d)} \right) \times \left(1.0 + (\text{priority} - 5) \times 0.02\right) \quad (\text{với } k = 60)$$
  * Điểm `priority` (1-10) phản ánh giá trị pháp lý của 37 loại văn bản theo chuẩn ĐH Quy Nhơn (Quy chế, Quyết định có priority=10 được nhân hệ số boost $+10\%$; Thông báo/Tin tức có priority=5 giữ nguyên hệ số $1.0$).
  * Giúp các văn bản quy phạm pháp luật cốt lõi tự động bứt phá lên vị trí đầu bảng kết quả khi điểm tương quan ngữ nghĩa tương đương với các văn bản tin tức/hướng dẫn phụ trợ.
- Cân bằng tối ưu giữa khả năng hiểu ngữ nghĩa sâu sắc của Vector BGE-M3 và độ chính xác tuyệt đối của từ khóa FTS tiếng Việt.

### Bước 6: Tái xếp hạng (Cross-Encoder Reranker) kèm Fallback
- Gọi mô hình Cross-Encoder `BAAI/bge-reranker-v2-m3` để chấm điểm tương quan cặp `(Query, Chunk)`.
- **Cơ chế phòng thủ Graceful Fallback**: Nếu dịch vụ reranker bị timeout (>3 giây) hoặc ngoại tuyến, hệ thống tự động suy thoái an toàn về thứ tự ban đầu của thuật toán RRF mà không làm gián đoạn request của người dùng.

### Bước 7 & 8: Chốt chặn Trích dẫn Nghiêm Ngặt (Strict Evidence-Based Citation Guardrail) & Chính Sách Không Trả Lời
- **Bộ lọc Trích dẫn Nghiêm ngặt (Strict Citation Filtering)**:
  * **Lọc bỏ từ dừng học thuật tiếng Việt (`ACADEMIC_STOPWORDS`)**: Trước khi tính điểm giao thoa giữa câu trả lời và đoạn trích, thuật toán loại trừ toàn bộ các từ dừng phổ biến như *"sinh viên"*, *"quy nhơn"*, *"đại học"*, *"trường"*, *"theo"*, *"trong"*, *"với"*, *"tối"*... nhằm loại bỏ hoàn toàn các trường hợp match giả (false positive overlap).
  * **Xử lý an toàn `quote is None`**: Đảm bảo không bao giờ phát sinh lỗi ngoại lệ khi trích đoạn rỗng.
  * **Tuyệt đối không cấp Citation giả**: Khi không có trích dẫn nào vượt qua ngưỡng kiểm định bằng chứng, hệ thống trả về danh sách rỗng (`[]`) và chuyển trạng thái câu trả lời sang `insufficient_context` (chấm dứt hoàn toàn cơ chế fallback trả ngẫu nhiên 2 citation đầu).
- **Phản hồi từ chối chuẩn mực (No-Answer Policy)**: Khi thiếu căn cứ, phản hồi hướng dẫn lịch sự kèm hotline tư vấn tuyển sinh chính thức: `0256.3846.156` hoặc email `tuyensinh@qnu.edu.vn`.

### Bước 8b: Chốt Số Liệu Trích Dẫn Ở Runtime (phiên #185)
- `CitationGuard.verify_numeric_grounding()` trích số nhiều chữ số trong đáp án (so sánh không phân biệt `,`/`.`), đối soát với quotes + facts; số lạ → `insufficient_context` + No-Answer thay vì trả liều. Số 1 chữ số và đáp án không số được miễn (nhiễu).

### Bước 8c: Đợt B — Rank Facts, RRF Trọng Số, Prompt Tầng, Eval Online (phiên #186)
- **Rank facts theo số môn khớp (B1)**: `count_subject_matches()` đếm môn trong `attribute_value` (không quét tên thực thể, tránh `Kế Toán` khớp `toán`); `lookup_facts(..., subject_names)` over-fetch ×3 rồi xếp hạng và cắt limit.
- **RRF trọng số theo intent (B2)**: `reciprocal_rank_fusion(..., dense_weight, sparse_weight)`; EXACT_FACT (1.0/1.2) tin lexical, NARRATIVE (1.2/0.8) nghiêng ngữ nghĩa, MIXED cân bằng; log policy mỗi lượt.
- **Prompt phân tầng + ép temperature (B3)**: fact-query tách TẦNG 1 facts / TẦNG 2 chunks / TẦNG 3 history kèm quy tắc xung đột, history gắn nhãn tham khảo, `temperature = min(req, 0.2)`.
- **Eval online từ vote (B4)**: bảng `conversation_feedbacks` + `POST /conversations/feedback` + `GET /conversations/feedback/stats` (up-rate); nút 👍/👎 Chat Studio gửi vote best-effort kèm thread/câu hỏi/trả lời.

### Bước 8d: Đợt C — Parent-Child, Multi-Query, Drift Dashboard (phiên #187)
- **Parent-child mở rộng ngữ cảnh (C1)**: `expand_with_neighbors()` lấy chunks kề cùng document theo `chunk_index` (fallback `page_number`), tối đa 2 chunks top đầu; đưa vào prompt dưới nhãn `BỐI CẢNH MỞ RỘNG`, không trích dẫn, không làm evidence; lỗi DB suy thoái êm.
- **Multi-query sparse fusion (C2)**: service dựng `keyword_query` từ mã/môn/từ khóa dài; `retrieve(..., sparse_variants)` chạy thêm tối đa 2 truy vấn sparse song song (không tốn embedding), dung hợp RRF với trọng số chiết khấu 0.5 qua `extra_lists`.
- **Trend + samples + panel eval (C3)**: `GET /conversations/feedback/trend` (buckets ngày, gom bằng Python cho tương thích PG/SQLite), `GET /conversations/feedback/samples` (down mới nhất); tab `Đánh Giá Người Dùng` trên `/evaluation` với KPI up-rate, thanh trend 14 ngày và bảng down cần đối soát.

### Bước 9: Phân Vùng Bộ Nhớ Đệm Ngữ Nghĩa Đa Tầng (Multi-Tenant & Policy Partitioned Semantic Cache)
- Lớp cache ngữ nghĩa trên Redis (`SemanticCache`) sử dụng khóa phân vùng bảo vệ chặt chẽ:
  `rag:cache:{tenant_id}:{workspace_id}:{collection_id}:{preferred_model}:{policy_version}:{hash(query)}`
  với `policy_version = "v1"`.
- Việc phân tách 5 lớp (`tenant_id`, `workspace_id`, `collection_id`, `model`, `policy_version`) bảo đảm:
  1. Tuyệt đối không rò rỉ dữ liệu hoặc câu trả lời giữa các tenant và workspace.
  2. Khi người dùng đổi mô hình (`gpt-4o-mini`, `gemini-1.5-flash`, `qwen2.5-7b`), cache không trả kết quả lệch lạc do định dạng của model trước đó sinh ra.
  3. Khi chính sách retrieval thay đổi (`policy_version`), cache tự động phân tách mà không bị ô nhiễm bởi kết quả từ chính sách cũ.
- Hỗ trợ cơ chế vô hiệu hóa cache chủ động theo mẫu wildcard (`invalidate_collection`) bao quát cả mẫu khóa mới `rag:cache:*:*:{collection_id}:*` và mẫu khóa kế thừa `rag:cache:*:{collection_id}:*` ngay khi có tài liệu mới được duyệt/lập chỉ mục hoặc bị xóa.
- **Cache theo history (phiên #185)**: key thêm hậu tố `history_hash` (SHA-256 16 ký tự của 4 turns gần nhất, `nohist` khi không có history) qua `SemanticCache.hash_history()`; query ngắn <8 từ kèm history (ví dụ `có tôi muốn`) bị bỏ qua cache đọc/ghi để không trả đáp án của ngữ cảnh cũ.
- **Scoping history theo chủ đề (phiên #185)**: `scope_history_by_topic()` giữ turn mới nhất + các turn cũ có trùng mã thực thể/tên môn/từ khóa dài, tối đa 4 tin nhắn; tên môn trần chỉ tính khi tin nhắn cũ bàn về tổ hợp (chống `Kế toán` khớp nhầm `toán`).
- **Unaccent fallback (phiên #185)**: `strip_vietnamese_accents()` + `is_unaccented_query()`; query không dấu kích hoạt lượt ILIKE bổ sung dùng `func.unaccent()` (bỏ qua êm khi CSDL thiếu extension).
- **Rerank quan sát được (phiên #185)**: timeout Cloudflare 10s→3s, log `provider/latency_ms/in/out` cho cả 3 nhánh (cloudflare/custom/rrf_fallback).

### Bước 10: Định dạng thông minh (Answer Format Planner)
Tự động lập kế hoạch trình bày câu trả lời:
- Hỏi so sánh / danh sách ngành $\rightarrow$ Trả về **Bảng Markdown** (`markdown_table`).
- Hỏi thủ tục / hồ sơ $\rightarrow$ Trả về **Danh sách kiểm tra** (`checklist`).
- Hỏi lịch trình / mốc thời gian $\rightarrow$ Trả về **Dòng thời gian** (`timeline`).

### Bước 11: Tái sử dụng dùng chung cho mọi Trợ lý mới (Generic Reusable RAG)
- **Query Router theo module (`query_router.py`)**: Registry `FACT_KEYWORD_PACKS` cho admissions, regulations, library, drafting, question_bank; trợ lý mới dùng tín hiệu generic (số hiệu QĐ/NĐ/TT, số tiền triệu/tỷ, năm, bao nhiêu/danh sách/liệt kê) mà không cần sửa code. API `analyze(query, module_code="general")` tương thích ngược.
- **System Prompt dùng chung (`service.py`)**: `build_generic_system_instruction(module_code, custom_prompt)` ưu tiên prompt của trợ lý, ngược lại dùng instruction Zero-Hallucination toàn trường kèm contact theo module (admissions giữ hotline 0256.3846.156, module mới dùng contact tổng quát).
- **Phát hiện từ chối phi thiên vị**: `is_refusal_answer(answer, has_evidence)` chỉ dựa vào cụm từ từ chối + có/không có citations/facts, thay thế hoàn toàn heuristic cũ chỉ biết triệu/học phí/điểm chuẩn.
- **Mặc định an toàn**: `AskRequest.module_code` mặc định `general` (thay vì admissions) để trợ lý mới không bị nhiễm ngữ cảnh tuyển sinh.

### Bước 12: Ràng Buộc Thực Thể, Chỉ Đạo Định Dạng & Bộ Lọc Hậu Xử Lý (phiên #188)
- **Nhận diện Thực thể Trọng tâm (`target_entities`)**: `QueryClassifier.analyze()` tự động trích xuất các thực thể cụ thể (ví dụ: ngành đào tạo, mã ngành, văn bản) từ câu hỏi người dùng.
- **Ràng buộc Trích xuất theo Thực thể (Entity-Scoped Prompt Injection)**: Khi người dùng hỏi về một thực thể cụ thể (ví dụ: *Công nghệ thông tin*), hệ thống inject chỉ thị bắt buộc vào `user_content`:
  * Chỉ được phép trích xuất thông tin liên quan đến thực thể đó.
  * Tuyệt đối không sao chép hay hiển thị thông tin của các ngành/đối tượng khác có trong bảng/tài liệu.
- **Chỉ đạo Định dạng Động từ `AnswerFormatPlanner`**: `get_format_instructions(format_type, target_entity, is_combo_query)` đưa trực tiếp quy tắc trình bày vào prompt:
  * Tổ hợp môn: Bắt buộc dùng danh sách gạch đầu dòng (-) rõ ràng từng tổ hợp môn `(Môn 1, Môn 2, Môn 3)`, giải thích rõ ràng các ký hiệu số phương thức (ví dụ: 1, 2, 3, 4 là Phương thức xét tuyển 1-4).
  * Bảng số liệu: Bắt buộc dùng cú pháp bảng Markdown chuẩn chỉnh đầy đủ Header, cấm viết ký tự pipe `||` thô dính chùm.
- **Bộ lọc Hậu xử lý Làm sạch Cú pháp Bảng (`sanitize_rag_answer`)**:
  * Tự động làm sạch các cụm ký tự pipe rác `||||||` do OCR tài liệu sinh ra.
  * Chốt chặn trường hợp LLM nhả cả khối bảng nhiều ngành: tự động phân tích và chuyển đổi thành danh sách gạch đầu dòng chuẩn mực cho đúng thực thể được hỏi.
  * Giữ nguyên vẹn tính toàn vẹn của các bảng Markdown chuẩn.

### Ngữ cảnh bản ghi và đủ ý trong shared evidence path (phiên452)

Lớp đọc bổ sung recordpath từ lược đồ field lặp, giữ mục con qua marker trang và gắn rawheading vào claim cùng nguồn. Những heading chưa phân loại giữ unknown; không viết ngược canonical/unitmanifest/index hoặc tự xác nhận năm dữ liệu. BM25 dùng đường dẫn như context, packing ưu tiên subsection đúng bản ghi và các facet được hỏi trong ngân sách cấu hình hiện có.

Primary body sai bản ghi bị chặn; verifier/audit kiểm tra entity, education level, attribute và public topic coverage. Fact dùng context đúng trang hàng/header, không dùng section cuối tài liệu. Tách proposal nhiều source để bind/verify riêng, không mượn điều kiện/năm giữa source. Giá trị bôi đậm vẫn là evidence; fieldtuple không tạo yêu cầu enum ngoài câu hỏi. Nhánh lịch sử ghi rõ điểm dừng, giữ partial có nhãn và lỗi dịch vụ thật; timeout ở historical_verification không được biến thành missing.

### Tham khảo khác năm trong shared evidence path (phiên 449)

Ưu tiên trả lời và kiểm chứng theo năm được hỏi. Nếu chưa có claim hợp lệ cho năm đó, có thể tra cứu một năm dữ liệu trước gần nhất từ ứng viên liên quan trong chính snapshot đã pin, rồi kiểm chứng riêng theo năm tham khảo. Không dùng năm filename/ngày ban hành để tự xác nhận năm dữ liệu; giữ đúng thực thể, thuộc tính, trường, phương thức, đợt và sự kiện.

Phản hồi có căn cứ lịch sử luôn là `partial` / `HISTORICAL_REFERENCE_ONLY`: `requested.years` giữ năm người dùng hỏi, `historical_reference` ghi năm hỏi/năm tham khảo; citations/span/hash giữ nguồn thật. Nói rõ chưa tìm thấy căn cứ đã kiểm chứng đủ rõ cho năm hỏi và thông tin năm cũ không xác nhận áp dụng năm mới. Không kết luận Trường chưa công bố thông tin từ kết quả tìm kiếm thiếu.

Không thay thế trả lời đúng năm đã supported hoặc partial có claims, không che conflict/clarify/DB/model/timeout. Không tự fallback câu so sánh nhiều năm, publication/event-year, hoặc yêu cầu cấm tham khảo khác năm. Giữ timeout chung, provider/model/reranker và tenant/snapshot. Nhánh này chỉ thuộc evidence policy; legacy non-evidence giữ hành vi cũ.

### Bước 13: Chuẩn Hóa Góc Độ Nút Gợi Ý & Chống Entity Hijacking Đa Lượt (phiên #189)
- **Chuyển đổi góc độ Nút Gợi Ý (`convert_or_filter_suggestion_perspective`)**:
  * Rào chắn chống lộn vai trò: Nhận diện và chuyển đổi các câu hỏi tu từ bot hỏi người dùng (*"Bạn có muốn tìm hiểu về tổ hợp môn xét tuyển của ngành cụ thể nào không?"*) sang góc độ người dùng hỏi bot (*"Các ngành của trường xét tuyển những tổ hợp môn nào?"*).
  * Lọc sạch câu hỏi lịch sự mơ hồ (*"Bạn có muốn mình chia sẻ thêm điều gì không?"* $\rightarrow$ loại bỏ hoàn toàn, không hiển thị).
  * Chỉ dẫn System Prompt: Ép 100% câu gợi ý phải đặt câu hỏi từ góc độ người dùng, cấm bắt đầu bằng *"Bạn có muốn..."*, *"Bạn có quan tâm..."*.
- **Chống Entity Hijacking & Intent Drift trong Query Router & Query Rewrite**:
  * Loại trừ danh sách từ placeholder mơ hồ (*"cụ thể"*, *"cụ thể nào"*, *"nào đó"*, *"bất kỳ"*, *"gì"*, *"khác"*,...) khỏi việc trích xuất `target_entities`.
  * Cấm gán ghép thiên kiến ngành vào câu hỏi chung khi xử lý đa lượt, ngăn chặn hiện tượng kéo tên ngành cũ (như CNTT) vào làm biến dạng ý định câu hỏi hiện tại.


## Truy hồi hàng bảng có ngữ cảnh — cập nhật phiên 468

Sau reset cần xem `rag_execution_branch`: `fact_hybrid` là nhánh legacy, `evidence` là
nhánh kiểm chứng theo policy. Code không tự bật policy hoặc chuyển model. Historical
reference/semantic verifier trong evidence path không được mặc nhiên coi đang chạy ở legacy.

Fact lookup lọc đúng entity phrase/mã trước SQL LIMIT và xếp requested applicability-year
trước unknown. Năm ban hành/tên file không là năm áp dụng. Khi metric chưa được phân giải
và có row anchors, các ô cùng entity không tự được thăng lên “số liệu đã xác thực”.

Nhánh fact-hybrid bổ sung source-row anchors: tìm ô định danh từ chunk đã đánh chỉ mục,
pin collection/tenant/workspace/binding/index/source; kiểm hash/review/parity/unit manifest.
BM25 hiện hữu xếp hạng hàng kèm intro/notes cùng nguồn. Bảo vệ hai hàng đầu, giữ source-units
ghi chú nguyên văn ngoài slot cạnh tranh; cấu hình topK reranker cho alternatives không đổi.
Không có anchor giữ nguyên kết quả cũ. Không tạo điểm CE giả hoặc giả lập dữ liệu khi DB lỗi.

Trích dẫn mới lấy raw span, trang hàng/header/ghi chú có chứng cứ riêng; metadata của hàng
không sao chép sang ghi chú. Liên kết chỉ là ngữ cảnh, không tự chứng minh điều kiện cho
mọi hàng, năm hoặc mọi cấp đào tạo. Cache legacy có version thuật toán mới, không xóa cache chung.

Không cần migration/reset/reindex cho phần query này; nguồn chưa có source-unit metadata
cần nâng cấp qua lifecycle ingestion, không tạo hàng giả khi thiếu metadata. Cần BE/worker mới
trước test chat. Chưa thay output budget hoặc status refusal, chưa mặc định bật policy evidence.
Diagnostic không gọi model chỉ xác nhận retrieval, không phải accuracy. Xem
[nhật ký468](../nhat_ky/2026-10-15_phien_468_rag_giai_doan_3_truy_hoi_hang_bang.md).

## Sinh và kiểm chứng đầu ra — cập nhật phiên 469

Generation legacy bổ sung grounding instruction vào system message của lượt gọi, không
ghi đè persona cấu hình. Đối chiếu tương đương ngữ nghĩa từ chính định nghĩa/header/đoạn
dẫn, giữ đủ giá trị theo phương thức và điều kiện áp dụng; thiếu phải chỉ rõ phần thiếu,
không dùng cảnh báo chung để phủ nhận cả đáp án. Không thêm từ điển nghiệp vụ/model.

Tách gợi ý và sanitize trước khi lọc citation/nhận diện refusal. Citation không phủ nhận
refusal; nội dung rỗng/không evidence không answered hoặc cache success. Đây là boundary
check heuristic, không thay independent semantic completeness audit trong evidence policy.
Không tự bật evidence policy sau reset.

OpenAI-compatible window400 được recovery một lần khi tokenizer cùng server trả count
thực và window khớp. Giữ nguyên prompt/alias/template; chỉ giảm output cap riêng lượt gọi.
Không dùng “at least” như số đếm chính xác, không cắt nguồn, không persist request count
thành cấu hình. Không hỗ trợ/không đủ chỗ thì giữ lỗi/fallback. JSON/SSE kết thúc `length`
không được nhận là hoàn tất, kể cả đã sinh một phần nội dung. Không replay stream đã phát.

Đây không phải nới cửa sổ server hay bỏ quota, không cần migration/reindex. Cần BE/worker
nhận code mới trước test live, đối soát source/citation/đủ ý thủ công, không lấy HTTP200 hoặc
status answered làm accuracy. Xem [nhật ký469](../nhat_ky/2026-10-15_phien_469_rag_giai_doan_4_sinh_va_kiem_chung.md).

Kiểm chứng live phiên469 đã hết lỗi window và chạy primary, nhưng hai câu điểm sàn vẫn
sai/thiếu dù hàng đủ trong prompt. Generation chưa nghiệm thu; chưa triển khai row-cell
answer contract/semantic validation mới, chưa chạy20/82. Xem mục đề xuất cần duyệt trong nhật ký.

## Hợp đồng ô nguồn ở nhánh fact-hybrid — cập nhật phiên 470

Sau khi duyệt tiếp, fact-first có row anchors đủ header/source-unit provenance sẽ đi
MetricScope (đoạn dẫn định nghĩa loại số liệu) → RowSelection (ID ô/scope/notes) → RowAudit
độc lập không nhìn selection. Dùng ModelOps cấu hình hiện hữu và assistant_scope để xác định
trường ngầm định, không lấy facts từ persona. Không bật evidence policy hoặc đổi model/config.

ID server gắn đúng hàng/cột/raw value; ID ngoài nhóm metric hoặc scope nguồn khác bị chặn.
Request collection/tenant/workspace phải khớp snapshot. Năm cột rõ ràng không được đổi thành
năm ban hành; scope chưa rõ không được tự coi verified. Verdict không đạt trả insufficient,
không free-synthesis để né kiểm chứng, không cache thành công.

Render từ ô gốc thay model viết lại số, có citation raw span/hash/trang/header. Giữ ô trống/dấu
ở giữa các cột đã chọn cùng họ header, không điền số thiếu hoặc đoán nghĩa dấu. Notes giữ
đủ nhánh điều kiện và câu tiếp qua trang theo cấu trúc cùng nguồn; các paragraph chú giải
độc lập không tự thuộc điều kiện đứng trước. Hiển thị rõ từng mục chỉ áp dụng cho phạm vi
trong chính mục đó. Ghi chú vẫn bảo thủ/khá dài, chưa rút gọn tự do.

No catalog hoặc câu không fact-first vẫn dùng nhánh hiện hữu. Deterministic temporal-table
trước nhánh này không đổi; historical fallback/evidence policy không mặc nhiên được bật.
Live hai câu điểm sàn cuối470 đã đủ15/18/600/15 và20/–/–/20 cùngnotes; chưa20/82/accuracy.
Xem [nhật ký470](../nhat_ky/2026-10-15_phien_470_rag_hop_dong_o_nguon.md).

