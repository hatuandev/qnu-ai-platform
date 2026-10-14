# Phiên #442 — Phân tích câu chưa đúng và đề xuất cải thiện RAG

Ngày: 14/10/2026, múi giờ Asia/Bangkok. Trạng thái: **phân tích và đề xuất, chưa triển khai**.

## Phạm vi

Theo yêu cầu người dùng, xác định nguyên nhân các câu còn lỗi sau #441 và đánh giá thuật toán nên bổ sung. Dùng skills qnu-rag-pipeline, qnu-chatbot-builder, qnu-clean-code-architect. Chỉ đọc artifacts, mã và DB; tái hiện một hàm kiểm chứng thuần với dữ liệu đã có. Không gọi LLM/chat, không sửa runtime, model/provider, tài liệu nguồn, trạng thái duyệt hoặc publication. Không reset/reindex.

Nguồn bằng chứng: `backend/storage/admissions_eval441_acceptance20.json`. DB hiện tại có cùng publication fingerprint `733f3faf2f247c16e3a2` với lượt test. Việc kiểm tra thêm khẳng định **cả ba câu5/13/38 đều có thông tin liên quan trong kho đã xuất bản**; không được quy cả ba thành thiếu dữ liệu hoặc dùng kết luận này cho toàn82câu.

## 1. Câu5 — Bộ kiểm chứng số từ chối nhầm

Câu hỏi: tổng chỉ tiêu2026. Claim được chấp nhận có5.173, đi kèm cùng-source header “Thông tin tuyển sinh đại học năm2026 (cập nhật)”. Audit semantic cũng xác nhận số liệu đúng, nhưng qualifier riêng “năm2026” lại gắn vào cả một câu của nguồn thuyết minh, chứa chỉ tiêu cũ4.500, mã văn bản1906/263 và hai ngày ban hành.

Trong `evidence_audit.py:144`, `needed=number_values(quote)-requested_years` yêu cầu mọi số còn lại của câu nguồn xuất hiện trong claim. Tái hiện `audit_coverage` trên dữ liệu gốc trả accepted1/errors0/missing=[năm2026]/complete=false. Claim numbers={5173}; qualifier numbers={2,5,263,2026,12,1906,4500,5173,31}. Đây là lỗi phạm vi điều kiện/numeric guard, không phải truy hồi thiếu chỉ tiêu hoặc model hết context.

**Đề xuất P0: role-aware constraint grounding.** Ràng buộc cần có trường/quan hệ được hỏi, vai trò, giá trị, đơn vị/phạm vi, source passage/span và các claim giữ nó. Đối soát số của điều kiện đó, không mọi số nền của cả đoạn. Phân biệt quantity/data-year với document identifier/issued-date/historical comparison bằng cấu trúc số, kiểu dữ liệu, ngữ cảnh cú pháp và proof nguồn; không từ điển domain gõ tay. Season header chỉ xác lập năm khi thực sự gắn với giá trị được hỏi, không áp dụng cho mọi số liệu lịch sử trong văn bản2026. Không chỉ sửa thành kiểm các số trong nhãn qualifier do LLM sinh, vì nhãn có thể bỏ mất giờ/ngưỡng quan trọng. Không tắt numeric guard.

## 2. Câu13 — Có chính sách nhóm nhưng context bỏ sót

Câu hỏi: ngành sư phạm có xétĐGNLTrườngĐHSPHàNội không. Context chọn đoạn mụcV nói chung QNU nhậnPT4 cho ngành/tổ hợp công bố. Nó không chọn block `ks_rev_aae30aac628c:3019:3522` ở mụcII, có câu trực tiếp nói một số ngành đào tạo giáo viên phù hợp được dùngPT4 với điểmĐGNLĐHSPHàNội. Model đòi thêm danh sách cá thể, repair lại trên cùng context nên vẫn partial.

Câu trả lời đúng mức khái quát phải giữ “một số ngành phù hợp/được công bố”, không biến thành mọi ngành. Nếu người dùng hỏi một ngành cụ thể thì cần chứng cứ ngành đó; không tự suy từ nhóm.

**Đề xuất P1:** truy hồi đa cách diễn đạt giữ nguyên năm/trường đích/phương thức; entity aliases chỉ từ tài liệu/config đã xác thực, không tạo bảng synonym hardcoded. Mã hiện tại gọi hybrid anchors một lần với plan.query; search_queries bổ sung chủ yếu dùng BM25 trên corpus. Cần cho các biến thể hợp lệ tham gia semantic/hybrid retrieval rồi hợp nhấtRRF và rerank bằng AI server đã cấu hình. ProbeBM25 chỉ đọc với cách diễn đạt lấy từ nguồn “đào tạo giáo viênPT4năm2026” đưa đúng block chính sách nhóm vào top4; chưa là bằng chứng cải thiện end-to-end, và không chứng minh multi-query đơn lẻ sửa được mọi câu.

## 3. Câu38 — Thiếu cụm điều kiện trong context, dễ nhầm vai trò điểm thi

Câu hỏi: điều kiện đầu vào sư phạm cho phương thức không dùng kết quảthiTHPT để xét tuyển. Kho có mục2 của **TB điểm sàn26**, block `14691:15064`, nêu đúng loại phương thức và hai nhánh liền kề a/b ở `15066:15532`, `15533:15896`. Các nhánh này có điều kiện học tập, các lựa chọn18,00/8,50 và ngoại lệGDTC16,50/6,50; không dùng những số đó ngoài scope của nhánh gốc.

Lượt test không chọn cả cụm trên. Nó chọn một đoạn thuyết minh vềĐGNLSPHN và các đoạnIELTS/THPT liên quan nhưng khác mục đích. Các biến thể truy vấn có một câu đổi “điều kiện đầu vào/xét tuyển” thành “điều kiện nhập học”, làm lệch ý định. QueryPlan đánh coverage=focused; mở rộng section/list hiện chỉ kích hoạt khi enumeration. Với TB điểm sàn, parent_id của mục2 và a/b đang null; mở rộng chỉ dựa headingMarkdown không đủ.

Proposal trảmissing và không có claim; `_answer` trả No-Answer trước verification/repair. Đây là điểm thiếu cơ chế tìm lại, không phải lỗiHTTP hay bằng chứng toàncorpus thiếu nội dung.

**Đã chứng minh:** cụm nguồn có và không nằm trong context cuối; early-exit không tìm lại. **Cần kiểm tra thêm:** model có hiểu nhầm “không dùng làm điểm xếp hạng” thành “không yêu cầu điểmthi dưới bất kỳ vai trò nào” hay không, vì artifact không lưu đầy đủ lập luận proposal. Hai vai trò phải được tách trong plan/verification, nhưng không tự kết luận nguyên nhân suy nghĩ của model.

**Đề xuất P1: structure/dependency-aware retrieval và packing.** Chọn một đoạn nhỏ rồi mở rộng đúng mục cha, phần dẫn, nhánh a/b và ngoại lệ trong cùng source revision, kể cả qua trang; dừng ở mục ngang cấp tiếp theo, không kéo cả mục ngànhLuật. Dựa heading hierarchy, numbered/lettered markers, offsets, adjacency và parent metadata; có thể xây liên kết cấu trúc trong bộ nhớ đọc, không phải đưa DAG workflow trở lại. Mở rộng theo dependency cần thiết cho câu hỏi điều kiện, không chỉ câu hỏi liệt kê. Bảo toàn AND/OR/ngoại lệ, không tự diễn giải thứ tự logic nếu nguồn còn mơ hồ.

## 4. Các bổ sung thuật toán nên làm, theo thứ tự

| Ưu tiên | Thay đổi | Mục tiêu và giới hạn |
| --- | --- | --- |
| P0 | Sửa role-aware numeric/temporal/constraint validation | Giải quyết falsepartial5, vẫn chặn sai số/năm/đơn vị/giờ/điều kiện |
| P1 | Structure-aware parent/child + dependency closure | Lấy đủ cụm nguồn của38, giữ nhánh/phạm vi và ngoại lệ; không lấy hàng xóm tùy tiện |
| P1 | Multi-query hybrid retrieval +RRF/reranker | Tìm chính sách nhóm13 qua cách diễn đạt khác; xác thực biến thể không đổi đối tượng/năm/phủ định/mục đích |
| P1 | Bounded corrective retrieval | Nếu coverage thiếu do ngữ cảnh, tìm lại tối đa một lượt theo phần thiếu rồi kiểm chứng; không regenerate nhiều lần trên cùng context |
| P2 | Coverage-aware packing | Ưu tiên đoạn chứng minh thành phần còn thiếu, không chỉ các top-k đoạn giống nhau; giữ nhóm dependency nguyên khối |
| P2 | Same-source span-containment deduplication | Nếu câu con đã nằm trong paragraph được chọn thì bỏ phần lặp; không dedup chéo năm/revision/source hoặc mất ngoại lệ |

Corrective retrieval lấy cảm hứng từ [CRAG](https://arxiv.org/abs/2401.15884), nhưng đây là bản điều chỉnh cho QNU: chỉ truy hồi kho đã duyệt/xuất bản, không tự mở rộng web hoặc dùng kiến thức huấn luyện làm chứng cứ. Không gọi đây là triển khaiCRAG nguyên bản hay [Self-RAG](https://arxiv.org/abs/2310.11511), vốn có cơ chế huấn luyện/reflection tokens riêng.

Parent-child, hybrid retrieval và reranking có thể tham khảo [bài AdvancedRAG của repo người dùng](https://github.com/rohitg00/ai-engineering-from-scratch/blob/main/phases/11-llm-engineering/07-advanced-rag/docs/en.md). QNU đã cóBM25/vector/RRF/reranker, nên phải sửa chỗ nối và kiểm chứng, không xây một engine khác chỉ để thêm tên thuật toán.

Có thể thử greedy weighted set-cover cho packing sau khi xác định được các yêu cầu và đoạn nào chứng minh chúng: chọn theo phần yêu cầu mới được phủ/cost, giữ relevance và giới hạn context. Coverage labels cần proof nguồn, không tin nhãnLLM một cách tuyệt đối. Đây là phương án đánh giá, chưa khẳng định tốt hơn cấu hình hiện tại.

Chưa ưu tiênGraphRAG/RAPTOR/fine-tuning/đổi model lớn/HyDE sinh đáp án giả/semantic cache. Các ca hiện tại là truy hồi cụm quy định và validation, không cần community graph hay thay model. MMR có thể thử khi candidate bị trùng lặp, nhưng span-containment và coverage packing phù hợp hơn với lỗi đã quan sát; MMR không được loại ngoại lệ bắt buộc để đổi lấy độ đa dạng. Cache cần key theo snapshot/policy/year/scope và chỉ dùng đáp án đã kiểm chứng, tránh lưu lỗi hoặc trộn2025/2026.

## 5. Cách nghiệm thu đề xuất

1. Tái hiện5/13/38 trước sửa; negative controls: số/ngày sai, một ngành không suy thành mọi ngành, thiếu ngoại lệ/nhánhOR, lẫnscore role, nguồn2025 cho câu2026, thực sự thiếu nguồn, model/DB/reranker lỗi.
2. Chạy lại20câu cùng publication/config; so sánh không chỉ supported mà cả điều kiện bắt buộc, tính liên quan và trích dẫn.
3. Sau đó chạy82, phân biệt câu có đủ dữ liệu, đủmột phần, chưa có nguồn và lỗi runtime. Golden answers cũng cần đối soát mùa/năm; không lấy đáp án2025 làm oracle2026.
4. Đo retrieval recall/coverage, false-refusal rate, answer correctness/faithfulness/completeness, p50/p95latency, sốlượtmodel và retrieval repair. 31/31spanhash hoặc HTTP200 không phải accuracy. Quan điểm phân biệt correctness/faithfulness phù hợp [nghiên cứu đánh giáQA](https://arxiv.org/abs/2307.16877).

Không tăngcontext/max_tokens đại trà hoặc tắt guardrail để làm đẹp pass rate. Vì mạng quốc tế chậm, không thêm một vòngLLM tự phản biện cho mọi câu; dùng metadata/span checks trước và chỉ sửa truy hồi ở ca yếu. Các câu5/13 đã tiêu tốn khoảng23giây verification nhưng vẫn thất bại trên cùngcontext.

## Tài liệu thay đổi và kiểm tra

Chỉ tạo nhật ký/snapshot442 và cập nhật README nhật ký, PROJECT_CONTEXT, WORK_LOG. Không thay luồng hiện hành; chưa cập nhật docs/quy_trinh thành quy trình mới vì các bước ở trên mới là đề xuất. Không chạyRuff/Pytest/Vite hoặc full82 vì không sửa mã ứng dụng. Kiểm tra cấu trúc/UTF-8 của tài liệu; deterministic replay5 và read-only snapshot/source probes đã thực hiện, không có LLM request mới.
