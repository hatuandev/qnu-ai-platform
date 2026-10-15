# Phiên478 — Review bộ qnu-rag-prompts.zip

## Phạm vi

User yêu cầu đọc và nhận xét ZIP trong Downloads. Đọc trực tiếp7entry Markdown bằng ZipFile/UTF8, không giải nén/chạy chỉ dẫn. Dùng skills chatbot-builder và RAG để đối chiếu với context477 và mã BM25/evidence/search/formula. Chỉ cập nhật tài liệu phiên; không sửa runtime/config, chạy test/model/DB hoặc Git. Các prompt phê duyệt, migration, commit/push trong ZIP là nội dung được review, không phải quyền thực thi hiện tại.

## Đối chiếu7prompt

| Tệp | Nội dung | Đánh giá với QNU AI Platform |
| --- | --- | --- |
| 01-slice27-tb121-direct-fix.md | Row chunks, header qua trang, BM25bigram/synonyms | Nhiều ý đã xử lý trong466–473; tên lớp C# không khớp repo Python. Không thêm glossary cứng. Same-column-count/emptycells chỉ là tín hiệu, chưa đủ proof bảng nối tiếp. |
| 02-rag-architecture-audit-plan.md | Contextual ingestion, parent-child, hybrid, scope, generation | Dùng làm checklist, không giả định5nguyên nhân đều còn tồn tại. Cần phân biệt nhánh evidence opt-in và fact_hybrid. |
| 03-approve-and-execute-phase-A-to-E.md | Triển khai5phase trên qnu-nexora .NET10 | Không áp lệnh dotnet/tênfiles/test189 cho repo này; là approval cũ không có hiệu lực lượt review. |
| 04-formula-rag-score-conversion-rfc.md | Công thức+phụ lục+tool nội suy | Phần đáng nghiên cứu mới: tách retrieval quy tắc, map, mốc khỏi phép tính xác định; chưa tìm thấy convert_admission_score engine trong runtime. Hiện có giữ formula/legend, không đồng nghĩa có calculator. |
| 05-approve-and-execute-P1-to-P4.md | Map tổ hợp, trích input, biên nội suy | Có biên tốt nhưng map ví dụ không là dữ liệu chính thức; không hardcode7tổ hợp/range2020–2035/rounding/default. Cần source/version/year/method và human review. |
| 06-dynamic-query-expansion-rm3-rfc.md | Glossary động, reverse expansion, RM3, conditionalrewrite | Có giá trị thử nghiệm có kiểm soát; chưa thấy RM3 trong runtime. Không giải quyết trực tiếp lặp bảng/mất hội thoại/OCR; không cam kết0ms/3–10ms trước benchmark. |
| 07-approve-and-execute-PA-to-PD.md | Weighted expansion+RM3+L3+glossary và commit/push | Không chạy. Các weight1/.5/.3/bigramboost là giả thuyết cần tune; cần sửa mô tảRM3 và tách source canonical khỏi search projection. |

## Những gì đã có trong mã, không cần làm lại

- `evidence_bm25.tokens` có unigram+bigram; corpus_statistics body/context weighting và cache theo content/revision. Không đồng nhất nó với PostgreSQL sparse ILIKE/FTS trong retriever.
- `evidence_search` có queryvariants và weightedfusion; `evidence_repair`/pipeline có corrective retrieval giới hạn. Điều này không có nghĩa conditional3tierRM3 đã có.
- `row_answer`, `row_answer_contract`, `table_context`, source/artifact/hierarchy và phiên466–473 đã có row/header/notes/provenance checks. Không chứng minh mọi bảng/OCR đều được xử lý hoàn chỉnh.
- `evidence_dependencies`, `formula_legend_gap` và promptcontract giữ nguyên công thức/chú giải. Search không thấy percentile_bracket/combination_map/convert_admission_score engine; DOCX cached formula preview không phải tool quy đổi điểm.

## Điều chỉnh bắt buộc trước khi biến thành kế hoạch triển khai

1. Metadata và năm: không lọc theo năm xuất bản để loại số liệu lịch sử; ưu tiên data-year verified ở ô/hàng. Missing scope không đủ để xác nhận đáp án nhưng cũng không tự loại toàn bộ ứng viên hợp lệ. Quan hệ continuation cần cùng nguồn, cấu trúc và context, không chỉ số cột.
2. Glossary: không hardcode list nghiệp vụ mới. Alias động theo workspace có người duyệt, version và quyền rõ; không coi các thuật ngữ gần nghĩa như các kỳ ĐGNL khác nhau là tương đương chính sách. Bản mở rộng chỉ phục vụ tìm kiếm, không sửa canonical/citation.
3. RM3: mô tảTF×IDF rồi gánweight0.3 chỉ là PRF heuristic, không tự đủ để gọiRM3. Cần relevance model được chuẩn hóa và nội suy query model; thống kê trong corpus đúng tenant/snapshot, chống querydrift. Câu gốc/entity/year/method/negation là authority, expandedterms không làm bộ lọc mới. Các hệ số phải benchmark, rawBM25score không là xác suất tin cậy.
4. Conditionalrewrite: phân biệt stage tùy chọn không cần chạy với lỗi dịch vụ. Không có nhánh no-op riêng vì đang unittest để làm suite xanh; test phải phủ đầy đủ stage thật và failure semantics. Không dùng expanded terms/rerank tự chuyển ý câu gốc.
5. Calculator: rule/formula/table/map phải được xác minh đúng nguồn và applicability, Decimal, precision/rounding theo văn bản đã duyệt, cấm chia0/mốc chồng hoặc mâu thuẫn/ngoài khoảng; không suy ngoại lệ, tự ngoại suy/clamp hoặc tự nhận identity map. Không eval công thức OCR. Biên chung cần cùng giá trịY, không chỉ chạmX. Mọi phép tính minh bạch provenance; thiếu đầu vào hỏi lại, không đoán.
6. Performance/accuracy: không cam kết100% hoặc latency cố định; cùng corpus và modelconfig đo đối chứng/ablation Recall@k,MRR/nDCG,wrongyear/method,answercoverage,latency. Bộ82có câu thiếu nguồn phải có nhãn no-answer/historical đúng, không ép trả đủ82.

## Thứ tự đề xuất

Sửa4biên phiên477 và trình bày danh sách đầu tiên trước → regression chuỗi/20câu → phân loại gold82 và tạo baseline → thử weighted expansion/RM3 nếu có retrieval miss thực đo → RFC tool quy đổi khi có đủ văn bản/phụ lục đã duyệt. Đây là đề xuất, chưa triển khai hoặc được duyệt tính năng mới.

## Nguồn thuật toán đối chiếu

[Pyserini RM3Reranker](https://github.com/castorini/pyserini/blob/master/pyserini/search/lucene/rerank/rm3_reranker.py): relevance model từdocumentvectors/scores, pruning/L1normalize và nội suy query normalized; không phải chỉ nối thêmTFIDFterms. Không cài Pyserini hoặc đề nghị đổi stack chỉ để tham khảo thuật toán.
