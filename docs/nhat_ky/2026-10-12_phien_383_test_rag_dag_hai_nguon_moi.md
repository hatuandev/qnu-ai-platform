# Phiên #383 — Test RAG/DAG hai nguồn vừa nạp lại

- Yêu cầu: test lại hai nguồn tuyển sinh DOCX2026 và quy chế đào tạo PDFK48 đã xuất bản.
- Skills RAG/chatbot dùng để kiểm tra knowledge binding, routing, facts, citations và no-answer. Clean-code áp dụng script test riêng, không sửa ứng dụng trong lượt kiểm tra này.
- Thực hiện API thật bên ngoài sandbox để serverAI Tailscale truy cập được, PostgreSQL read-only kiểm nguồn và trace. Không đổi model/policy/key, không xóa/reset/parse/build/publish/ngừng nguồn; không dừng worker, không sửa qnu-sso. Chat sinh conversation/trace/usage/quota/cache bình thường.

## Trạng thái thực tế

- Collection col_admissions, generation vg_8b7b06c28e51 active, BGE-M3/vLLM1024d.
- Tuyển sinh: bnd_420fb9869184 → ks_rev_9f70aae2ead2 → idx_rev_790c12a08c95.
- Quy chếK48: bnd_6994713703dd → ks_rev_40cf1aa53618 → idx_rev_225b1211c9a2.
- Hai revision không có structured_artifact persisted. Source tuyển sinh normalizer `layout-v4`, parser docling+native, tạo2026-10-12T08:43:36Z (15:43 local).
- Worker Python processes3852/26320 khởi động09:20:44 local; source_extraction.py sửa15:16:55. Bằng chứng worker chưa được restart sau cập nhật#382; không coi81facts là artifact mới. 81facts của source tuyển sinh chỉ gồm Mã ngành/Phương thức tuyển sinh/Tổ hợp xét tuyển, thiếu IELTS/cutoff year.
- `/sources` danh sách nhóm nguồn legacy rỗng không chứng minh mất document sources; kiểm đúng KnowledgeBinding/active pointers.

## Cách kiểm thử

7 câu hỏi riêng, mỗi câu qua RAG `/rag/ask` và DAG `/assistants/admissions/chat`; thêm lần lặp thu output gọn và kiểm tra nhiều lượt/SSE. Tổng23 POST trong lượt kiểm tra, không coi tất cả là fresh inference: cócache hits13–25ms. Không xóa cache chỉ để có kết quả đẹp.

Ground truth đối chiếu Markdown snapshot: tổng4800, IELTS6.0→9.0, CNTT2024=16.5/2025=21.5, đăng ký Bộ02/7–14/7/2026, chưa có điểm chuẩn chính thức2026; quy chế Điều19 cóngưỡngcảnhbáo0.8/1.0 vàtíchlũy1.2/1.4/1.6/1.8.

| Ca | RAG trực tiếp | DAG trợ lý tuyển sinh |
| --- | --- | --- |
| Tổng chỉ tiêu2026 | Đúng4800,2contexts | Đúng4800 nhưng dài/bảng nhiều ôtrống,2contexts trong node |
| IELTS6.0 | Có lượt sai10.0, hỏi lặp sau đó9.0 và thêm7.0→10.0; chưa ổn định | Đúng9.0 ởlượt đối chiếu |
| CNTT2024/2025 | Đúng16.5/21.5 | Đúng16.5/21.5, trích dẫn cónguồn thừa |
| Thời gian đăng ký | Có02/7–14/7, nhưng dài và cóheadingrác | Cóđúngmốc, rewrite biến “ngày” thành “ngành”, output lặp vàGỢIÝdangdở |
| Điểm chuẩn CNTT2026 chưa có | Nói không thấy nhưng statusanswered + tríchdẫn5nguồn | **Sai: khẳng định2026=21.5**, gán dữ liệu2025 thành2026, guardchoqua |
| Chào hỏi | insufficient_context (endpointRAGthuần, không coi lỗi routing) | greeting_llm/greeting_output, answered đúng |
| Điều19 K48 | Trả cácngưỡngcảnhbáo, citequychếtrang17 | insufficient_context dùknowledge node có1context; cần xét persona tuyển sinh/phạmvi vàgrounding, không tự gọi đó làparser/Qdrantmất dữ liệu |

## Trace và lỗi ưu tiên

- Quota exec36364754-4c81-4c05-bd77-fe0132cf7ccd: input→condition_route→rewrite→knowledge_answer→guard→output. Retrieval hoạt động, lỗi cũ loạihếtcontext đã không còn táihiện.
- Missing2026 exec6aeef52b-ac5b-4657-9006-6859800327ac: rewritegiữnguyêncâu hỏi; knowledge_answer sinh21.5cho2026; citation_guard is_groundedtrue/grounded_ratio0.8/unsupported_numbers[]; outputgiữanswered. Lỗi không ởqueryrewrite trong ca này.
- Nguyên nhân guard: kiểm số xuất hiện trong ngữ cảnh, không kiểm quan hệ `(entity, attribute, year, value)`. 21.5 cóthậttrong nguồn nhưng thuộc2025; nóikhôngtìmthấythôngtin vẫnanswered vì `is_refusal_answer` trảFalse ngay khi has_evidencetrue. Không thêm từđiển vá đểsửa quan hệ semantic này.
- Registration execc9fb5d55-71cb-4c60-a6d0-fa4338d0b370: rewriteđổi“từngàynàođếnngàynào” thành“từngànhnàođếnngànhnào”, làm lệchý; kếtquả vẫnđúngmốcnhưngformatrác.
- Multiturn hỏi2026 tiếpconv_8bd11cd5c6d7: exec7855e43d-f6f1-4d2f-af1d-ab50395c8a7b trảbảng2024/2025 thayvìxácnhậnchưacó2026, statusanswered — chưa đạt.
- SSE quota exec15d6cf4c-f049-4e13-bb8d-11414aa654e7 HTTP200 content-type text/event-stream, eventsstatus/token/citation/done, doneanswered. Chỉ kiểm backendstream, chưabrowserFErender/tokenfulltext; không gọi fullFE+BE E2E.
- Citation title đã là tên nguồn thật; vẫncótrangkhôngliênquan vàsectionMarkdownrác. Sốcites khôngphảithướcđochấtlượng.

## Đề xuất sửa trước nghiệm thu

1. Restartworker đểnhậncode#382 trước nạp/bóctáchtiếp; không cầnxóatệpgốc/resetDB. Khi cầnápdụngartifactmới cho nguồn đãnạp, reparsecóchủđích sau restart, review/build/publish; không tự làm trong phiên test.
2. Quan hệ facts/year/unit/evidence và missing-data decision cần failclosed; không chỉ xem sốcótrongtext. Facts nhiềuheader/year cần giữcấu trúc để guard đốisoát.
3. Rewrite phảigiữcác thực thể/số/năm/ýđịnh vàtừchỉthờigian; fallbackoriginal khi rewritekhôngbảotoàn, không đểLLM sửa “ngày”→“ngành”.
4. No-answer status khi cócitationnhưngkhôngtrảlời câu hỏi, cleanformat/nguồnliênquan, kiểmcacheanswerđãsai trướcchốtQA. IELTS cólượt10.0 khôngđược coi passchỉvìlượt sau9.0. Chưa đủ bằngchứng kếtluận cơchếcachelàgốclỗi.

## Tệp/kết quả

- Thêm `backend/scripts/test_rag_dag_383.py` live smoke script, có chọncasesCLI. ScopedRuff đạt. Không đổi runtime nên không chạy lại fullpytest/build; kết quả#382932/11cũ/2skip không đượccoi làđoQA lượt này.
- [Records stdout đầy đủ đã giữ được](attachments/2026-10-12_phien_383_results_partial.json). Mộtphầnstdoutlầnđầutracequádài bịtooltruncate; chọn lại IELTS/cutoffs/registration vàthêmK48 bằngoutputgọn. FileJSON ghi rõpartial, khônggiảlàmrawlogđầyđủ.
- Memory/snapshot/WORK_LOG/nhật kýindex đồngbộ. Kết luận **RAG/DAG có chạy nhưng chưa đạt nghiệm thu chất lượng**, chưa sửa lỗi trong phiên này. ChưaRagas50câu, loadtest, crash/recovery, fresh-stagingpublish/fullbrowserE2E.
