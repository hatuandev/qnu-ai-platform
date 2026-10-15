# Đề xuất bổ sung RAG: mở rộng truy vấn có trọng số và lộ trình triển khai

Ngày: 15/10/2026. Trạng thái: đề xuất để duyệt, chưa triển khai runtime.

## 1. Mục tiêu và ranh giới

Giúp câu hỏi tự nhiên tìm được thuật ngữ đúng trong văn bản mà không làm lệch ngành, năm dữ liệu, phương thức, phủ định hoặc ý định hội thoại. Tái sử dụng kiến trúc Python/FastAPI hiện có, không chuyển .NET, không framework agent/DAG mới.

Tách ba bài toán: truy hồi đúng bằng chứng; kiểm chứng đủ/đúng phạm vi; trình bày tự nhiên không lặp. Query expansion cải thiện bài toán đầu, không tự chữa OCR, suy ra năm thiếu, chứng minh danh sách đầy đủ hoặc sửa hành vi hội thoại.

## 2. Hiện trạng đã đối chiếu

| Thành phần | Hiện có | Khoảng trống cần xử lý |
| --- | --- | --- |
| `rag/retriever.py` | Weighted tokens theo hình thái/độ dài/mã, PostgreSQL ILIKE/FTS, dense/sparse fusion và rerank | Chưa phải hợp đồng trọng số theo original/alias/feedback; không được gọi sparse SQL là BM25 chuẩn |
| `rag/evidence_bm25.py` | Unigram+bigram, BM25, body/context weighting0.15, content/revision cache | Các query tokens hợp nhất thành set, mất provenance và trọng số riêng theo nguồn mở rộng |
| `rag/evidence_search.py` | Multi-query, kiểm tra số mới, RRF original1.0/variants0.7 | Trọng số từng danh sách không giới hạn tổng phiếu của nhiều variants; corrective feedback có thể lên index0 nên không thể hiểu index0 luôn là câu gốc |
| `rag/evidence_pipeline.py` | Search variants→hybrid anchors→canonical/facts→fusion→rerank→context packing/coverage | Cần gắn kế hoạch mở rộng một lần rồi truyền xuyên suốt, không sinh thêm pipeline cạnh tranh |
| `rag/evidence_repair.py` | Feedback theo phần thiếu, giữ số và snapshot, giới hạn vòng sửa | Tái dùng để rewrite có điều kiện, không thêm vòng retry mở |
| `rag/combination_enumeration.py` | Duyệt records đầy đủ trong phạm vi hỗ trợ, same-tuple, năm ô/nguồn | Không đưa TopK/RM3 vào làm điểm cắt danh sách ngành; ranking không chứng minh completeness |
| `rag/conversation_acts.py` | Explain/reformat/filter cho enumeration | Bốn biên phiên477 còn mở; không lấy weighted retrieval thay cho việc sửa lỗi này |

Phạm vi trên dựa vào mã và tài liệu, không phải đo chất lượng hiện tại của82câu. Repo có nhánh fact_hybrid và evidence opt-in; phải kiểm tra cả hai, không chỉ sửa nhánh không được chatbot thực tế dùng.

## 3. Hướng bổ sung ưu tiên: Weighted Query Expansion

### 3.1. Một hợp đồng truy vấn dùng chung

Giữ riêng:

- `raw_question`: câu hiện tại người dùng nói.
- `resolved_question`: ý định độc lập đã phân giải từ hội thoại, không phải câu chứa đáp án.
- `protected_constraints`: institution/entity/code/data-year/method/round/negation và facets của câu hỏi đã được xác nhận; missing/unknown phải giữ nguyên trạng thái, không suy từ filename.
- `terms`: term/phrase, dạng chuẩn hóa, nguồn `original`, `planned_variant`, `approved_alias`, `feedback`, trọng số và provenance.
- `queries`: các câu tự nhiên gốc/biến thể, ID, loại và nhóm trọng số, không dùng vị trí trong mảng làm nguồn gốc.
- `snapshot/config_version`: phiên bản publication, tokenization và expansion policy cho trace/cache.

Đây là hợp đồng nội bộ, không tin client truyền verified constraints/terms/weights. Bộ điều phối hội thoại quyết định có cần search không trước khi tạo query plan; explain/reformat không mặc nhiên gọi expansion.

### 3.2. Trọng số có nguồn gốc và giới hạn tổng

Ở lexical scoring: `score(d) = sum(weight(term) * BM25(term,d))` trên bộ tokenizer thống nhất giữa query và corpus. Từ gốc và cụm gốc ưu tiên; alias đã duyệt nhẹ hơn; feedback thống kê nhẹ hơn nữa. Những trọng số1.0/0.5/0.3 trong ZIP chỉ là cấu hình thử, chưa là giá trị tối ưu.

Không chỉ giới hạn từng term: nhiều terms bổ sung vẫn có thể cộng dồn lấn át câu gốc. Cần chuẩn hóa/giới hạn tổng đóng góp của từng nhóm, deduplicate token/cụm, không cộng trọng số nhiều lần khi một term vừa xuất hiện trong câu gốc vừa trong alias/feedback. Giữ attribution tách nguồn; budget nhóm phải xác định rõ trước benchmark. Không hứa original match luôn thắng mọi document vì IDF/length/relevance còn ảnh hưởng; bảo vệ entity/year bằng validation riêng, không chỉ bằng điểm.

Ví dụ cấu hình thử cho fusion: original-query group0.65, toàn nhóm variants+feedback0.35; chia phần0.35 giữa các danh sách đang hoạt động. Không nhân0.35 lại ở từng tầng một cách vô ý. Đây là budget RRF, khác query-term weights; cần ablation riêng từng thay đổi, không nhân mù mọi hệ số. Fallback khi một retriever không có kết quả phải có quy tắc rõ và trace, không cấp phiếu mới cho tài liệu vắng mặt.

Giữ nguyên câu hỏi tự nhiên đã phân giải khi gửi dense/reranker/generation. Expanded weighted terms dành cho lexical scoring; không nhồi token rời thành câu rerank mới. Biến thể ngôn ngữ có thể làm nhánh dense riêng khi đã validate, nhưng không thay semantic authority của câu gốc.

### 3.3. Ví dụ tác dụng, không phải từ điển runtime

Với câu hỏi “điểm sàn ngành Quản lý giáo dục2026”, giữ entity và data-year nguyên vẹn. Một biến thể “ngưỡng bảo đảm chất lượng đầu vào” chỉ giúp tìm nguồn. Nó không biến điểm sàn thành điểm trúng tuyển, không chuyển sang ngành khác vì cùng chứa “giáo dục”, không tự thêm giá trị điểm kỳ vọng. Các ví dụ chỉ nằm trong tests/tài liệu, không tạo map gõ tay trong runtime.

Lần đầu tái dùng biến thể do planner hiện có tạo ra, có label/provenance và validator; không thêm một lượt LLM riêng. Không gọi chúng là “approved aliases” nếu chưa có phê duyệt. Câu không có mở rộng vẫn chạy đúng hành vi cũ trong scorer API tương thích.

## 4. Hướng bổ sung sau baseline: feedback thống kê/RM3

Chỉ thực hiện trên corpus đã được phép đọc trong đúng tenant/workspace/collection/snapshot. Statistics/cache không được trộn workspace hoặc alias version. Ưu tiên nguồn canonical/facts được kiểm chứng, không lấy prompt/history/đáp án model làm corpus.

1. Lấy các ứng viên ban đầu từ search gốc; bảo đảm đủ seed tin cậy theo tiêu chí đã đo (identity/scope/retriever agreement), không lấy BM25score thô làm xác suất.
2. Dựng relevance model từ phân bố từ trong các tài liệu seed và trọng số tài liệu; chọn feedback terms, chuẩn hóa và nội suy với query model. Cách biến retrieval scores thành trọng số phải xác định, kiểm thử và ghi phiên bản; nếu chỉ dùngTFIDFheuristic thì gọi đúng làPRFheuristic, không gắn nhãnRM3chuẩn.
3. Loại terms đã có, boilerplate và OCR-noise theo statistics/structure/stopword config hiện có. Không tạo manual vocabulary mới. Không thêm năm/mã ngành/điểm/method/entity mới vào constraints hoặc answer. Không đưa số đáp án từ feedback thành điều kiện search.
4. Chạy lại tối đa một lượt trong deadline chung, hợp nhất với kết quả gốc; giữ seed gốc trong candidate pool, không đảm bảo chúng sẽ được xác nhận chỉ vì điểm cao.
5. Không có seed tốt thì bỏ feedback với reason rõ; không dùngRM3để khuếch đại kết quả đầu sai. Lỗi mandatoryDB/model phải giữ lỗi, không ngụy trang thành thiếu nguồn. Stage optional timeout chỉ được giữ kết quả cơ sở thật còn hợp lệ và log degraded, không tự marking success/completeness.

Mặc định tắt khi mới triển khai; chạy shadow và ablation trước khi bật cho assistant được chọn. Không nâng cấp mặc định cho mọi domain khi mới tốt ở tuyển sinh.

## 5. Hướng bổ sung khác từ ZIP

### 5.1. Alias động có quản trị

Không giữ core dictionary gán cứng. Khai thác candidates từ tiêu đề/cột/định nghĩa/ngoặc viết tắt trong nguồn; đây là gợi ý tìm kiếm, không tự coi đồng nghĩa hoặc chính sách đúng. Chỉ kích hoạt alias do người quản trị duyệt, có workspace, provenance, context/year khi cần, version và khả năng thu hồi. Không trộn các kỳ ĐGNL khác cơ quan thành cùng phương thức. Dùng cấu hình DB có cấu trúc hiện có nếu đáp ứng; nếu cần bảng/migration/UI mới thì táchRFCxin duyệt, không lén mở rộng G1.

### 5.2. Ngữ cảnh tìm kiếm không làm bẩn văn bản gốc

Tái dùng retrieval units/projection và header/parent/notes links hiện có. Ngữ cảnh bổ sung/alias dùng cho search field trọng số thấp hơn body, không sửa canonical raw spans hoặc ghi nội dung model sinh thành citation. Năm ban hành khác năm ô dữ liệu. Thay lexical query-time đầu tiên không cần nạp lại vector; thay embedding projection chỉ làm sau khi được duyệt index generation mới và kiểm tra trước publish. Tài liệu OCR lỗi cần review riêng, ranking không sửa được fact sai.

### 5.3. Multi-hop và công cụ quy đổi điểm

Sau khi retrieval/hội thoại ổn: thiết kế tool read-only tra rule+mapping+percentile brackets cùng source/year/method đã duyệt, tính bằngDecimal, rounding theo văn bản, provenance đầy đủ; khôngevalOCR, không clamp/ngoại suy nếu nguồn không cho phép. Lý thuyết công thức dùngRAGformula+legend; chỉ tính khi đủ inputs. Tool không tự nhận mapping ví dụ hoặc bộ7tổ hợp trongZIP là quy định cho mọi năm/domain. Chưa triển khai calculator trong G1/G2.

## 6. Lộ trình nghiệm thu

| Giai đoạn | Công việc | Điều kiện qua cổng |
| --- | --- | --- |
| G0 — Sửa nền và đo baseline | Khắc phục4biên477; trình bày danh sách đầu tiên không đổ toàn124records; nội bộ egressguard; phân loại gold82 theo nguồnđủ/thiếu/lịch sử | Regression năm antecedent, unknownsource, modeldown, handleruncertain đạt;20ca đại diện và trace baseline có label đúng |
| G1 — Weighted expansion cơ sở | Contract provenance; reuse planner variants; termweights và group-normalizedRRF, bảo vệ constraints, telemetry/cacheversion | OldAPI/no-expansion không đổi; không nhân phiếu khi clonevariants; targeted lexical-gap cải thiện, không tăng sai năm/ngành/method/negation trên holdout |
| G2 — RM3 shadow/opt-in | Relevance model đúng tên, scopedstatistics, gate seed,1passfeedback, ablation | So sánh G0/G1/G1+RM3cùng corpus/config; chỉ bật nếu retrieval/answer metrics cải thiện có kiểm tra nguồn; latency đạt budget thống nhất |
| G3 — Alias quản trị/projection | Candidate mining+phê duyệt,version/thu hồi; chỉ đổi index khi cần và được duyệt | Alias xấu chưaduyệt không tác động; thu hồi vô hiệu cache; không crossworkspace, không thaycanonical/span |
| G4 — CalculatorRFC và tool | Schema rule/map/brackets, validation, Decimal, routing+explain | Tất cả biên thiếu/mâu thuẫn/năm/sai phương thức/mốc/rounding cótest; phép tính đối chiếu độc lập với nguồn chính thức |

G1tách termweight và fusion normalization thành hai batch đánh giá độc lập. Không áp dụng TopKđể cắt exhaustive enumeration. Không cần chờ G3để thử G1. Nếu baseline không có retrieval miss mà chỉgeneration/presentation sai, không dùng RM3như mặc định chữa lỗi.

## 7. Điểm tích hợp dự kiến, không phải danh sách phải tạo hết

- Contract nhỏ `rag/query_expansion.py` (tên dự kiến): nguồn gốc terms/variants, constraints fingerprint, validate và policyweights. Tách thêm `rag/relevance_feedback.py` chỉ khi G2được duyệt, không tạo frameworkgeneric.
- `evidence_bm25.rank_blocks`: optional weighted query representation, giữ wrapper cũ mặc định tương thích; không loại body/header/sourceprovenancechecks.
- `evidence_search.search_queries/fuse_blocks`: giữ queryID/role qua corrective feedback, tổng weight theo nhóm thay vì index; dùng chung cho evidence pipeline.
- `retriever.extract_weighted_tokens/search_sparse_fts/retrieve`: nhận plan/tokens có provenance ở nhánh SQL/hybrid; không giả vờ mọi sparse scores đều cùng thangBM25. Chuẩn hóa lexical scorer trước khi trộn bằngRRF.
- `service.py`/`evidence_pipeline.select_context`: tích hợp vào nhánh thực tế, không thêm luồng gọiLLM/thêmdeadline. Rowanchors/facts/citationvalidation và exhaustive enumeration giữ độc lập.
- `evidence_policy.py` hoặc cấu hình DB hiện có: server-trusted opt-in/tuning/version, không LLMcredentialsenv, không nhận policyclienttùyý.
- Tests mới theo hành vi, script benchmark scoped, docs; loglocal rawdocuments khôngcommit. Chưa thayFE hayDBschema.

## 8. Đánh giá không làm đẹp số liệu

Phân nhóm82câu: lexical gap; multi-year; bảng/multi-entity; enumeration; formula; thiếunguồn. Thêm paraphrases và chuỗi hội thoại, giữ tập holdout không tuningtrên nó. Không dùng syntheticfacts để chứng minh dữ liệu thật đủ; testsynthetic dành invariants, oraclefacts thật do người reviewnguồn.

Đo: Recall@k trên đơn vị chứng cứ đúng, MRR/nDCG theo relevance labels, coverage các facts bắt buộc, wrongentity/year/method, false-refusal và false-answer khi thiếunguồn, citationaccuracy và latency p50/p95. Báo rawcounts/mẫu, không gộp no-answer hợp lệ vào lỗi hoặc ép đủ82answers. So sánh cùng snapshot/provider/modelconfig; ghi failures thật, không suy ổn định từ vài ca pass.

Regression cần có: termgốc trùngalias không cộngđôi; expandedterm nhiều không lấn budget; duplicatevariants không tăng phiếu; feedback không đổiscope; narrow2026 không giữ2025; body/header biệt nhau; OCRnoise seed bị chặn; crossworkspacecache/statistics khôngrò; khôngseed→skipfeedback; model/DBdown đúnglỗi; enumerationkhôngcắtTopK; historicalreference tách nhãn.

Backendimplementation chạyRuff+targeted+fullpytest, đối chiếu exactfailIDsbaseline. Không thay baseline errors thành pass bằng no-optheo môi trường test. Probe tài liệu chỉ model nội bộ sau egressguard độc lập failclosed trước transport/redirect; không thay fallbackproduction để test. Lượt kế hoạch này chưa chạytest/model/DB hoặc đo chất lượng.

## 9. Nguồn tham khảo thuật toán

- [Pyserini RM3Reranker](https://github.com/castorini/pyserini/blob/master/pyserini/search/lucene/rerank/rm3_reranker.py): relevance model, chuẩn hóa và nội suy query. Tham khảo thuật toán, không đề nghị thêmJava/Lucene để thay stack hiện tại.
- [Anthropic Contextual Retrieval](https://www.anthropic.com/engineering/contextual-retrieval): gắn ngữ cảnh riêng cho chunk trước tìm kiếm. Kết quả họ đo không phải mức cải thiện được bảo đảm cho QNU; ở app này giữ canonical và searchprojection tách biệt.

Khuyến nghị duyệt trước G0+G1; G2/G3/G4 có cổng riêng sau đo lường. Không runtime/config/reset/migration/reindex/publish/restart/deploy/commit/push trong lượt này.
