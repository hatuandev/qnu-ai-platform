# Phiên 417 — Đợt 2: chứng cứ, thời gian và quyết định RAG/DAG

## Checkpoint cuối — lượt bị ngắt, chưa nghiệm thu

User cung cấp stack `corr_38f7df916fbe`: MissingGreenlet tại workflow service.py:537, đọc execution_record.id đã expired. Execution49d78f40-2d80-4482-993b-bc129d00c70f failed/finalize sau3inference success. Regression PostgreSQL thật mởtransaction trongnode rồi rollback tái hiện lỗi ở3status completed/failed/paused; fail đúngdòng trước sửa. Đã sửa4chỗ dùng immutableidentityID chốttrướcexecute. Sau sửa3PG+13runtime =16passed; retrycâu5HTTP200/5.173/completed (`bb75684d-5be0-449d-8118-45c17b9e7010`). Không replay/sửa trạngthái recordcũ.

FinalRuff đạt; **1.071passed/11baselinefailed/9skipped**,94,52s (`pytest417_identity_final.log`).3skipmới là PGexpiration opt-in đã test riêng.45focused/31PGcorpus đạt trướcđó; khôngfailure mới, khôngsửaFE/buildFE.

Benchmarkfrozen82 dừng sau25đểfixfinalize. Lượt26–82 trênbảnfix (`admissions_eval417_remaining57.json`) ghi26–43:18attempts/16HTTP,9supported/2partial/2missing/1clarify/2failedproviders;42ReadError/43ConnectError khiếnhelpertựdừng. Khôngcònbenchmarkhelper khi kiểmtra sauturnbịngắt; agentkhôngdừng BE/FE/worker/9router. **44–82 chưa thử;42/43 cầnretry**. Đã thử1–43qua2build +retry5; khônggộp thànhaccuracy/full82mãchốt. Cấu hình/publication/codecuối lượt26–43 chưa kiểmtrađược do mấtkếtnối, reportgiữnull. [Đối soát26–43](./2026-10-13_phien_417_doi_soat_26_43.md).

WordSHA256 khớpfixture `5bdee19ececf709c472a56459e02a36e7f1afb44ffdba9974f58e899ed66c3fe`. Câu41lượtcuốianswered. Cònfalse-noanswer/cross-reference/semanticrisk (câu26điểmchuẩn vsđiểmxéttuyển và ưu tiên vsđiểmcộng) cầnđốisoát; supportedkhônglàđúngtựđộng. ChưaRagas/productionready. Tiếpquản: kiểmtraservices, giữsource19/epoch3/modelcũ; tiếp44–82 cùngfingerprint vàretry42/43outputriêng, khôngresetDB/Redis/reembed/OCR/publish/nhétFAQđápán. Các mục “đangchạy” bên dưới là nhật ký iterationtrước checkpoint này.

## Mục tiêu và quyết định người dùng

Triển khai đợt 2 theo đề xuất phiên 415 sau đợt 1. Người dùng chọn mặc định mùa tuyển sinh năm hiện tại theo giờ Việt Nam, ghi rõ năm; xác nhận TB 1906 cập nhật ưu tiên flyer đầu mùa cho thông tin cùng ngữ cảnh. Không reset DB/Redis, OCR/re-embed, duyệt thêm nguồn, hoặc tự xuất bản assistant/workflow.

## Thay đổi và thuật toán

- Core `evidence_policy.py`: opt-in, dynamic current/fixed/clarify year, budget/deadline và source preference theo revisions/năm, không hardcoded runtime model/source answers.
- RAG `evidence_schemas/model/validation/blocks/facts/precedence/runtime/pipeline.py`: planner ràng buộc scope; hybrid anchors + corpus BM25 từng variant/RRF + reranker AI server; exact canonical span và whole reviewed rows; proposal/independent verifier; claim-own numeric/quote binding, same-source scope, approved precedence. Toàn bộ số liệu chỉ lấy nguồn đã xuất bản. Không dùng đáp án mẫu hoặc training knowledge để lấp thiếu.
- RAG schemas/service/router: policy cache fingerprint v4; public policy từ DB, không client override; nhánh opt-in trước cache/legacy table-only gate.
- Assistant schemas/chat service và DAG citation_guard/no_answer/output_chat: AnswerDecision chung, partial citations bảo toàn, không bị legacy guard/template nâng trạng thái hoặc thay đổi câu trả lời.
- Scripts setup/inspect/evaluate417: actual DB policy config có backup, corpus audit, selection diagnosis và live sequential eval. Tests evidence_claims/evidence_postgres, cập nhật fixture legacy temporal để dùng DB session mock rõ opt-out (không bypass runtime khi DB thiếu).

## Cấu hình lưu thực tế

19 published sources, epoch3/gen `vg_21324678abcf` giữ nguyên. Primary/fallback/reranker cặp DB giữ như đợt 1. Admissions evidence enabled, year=current_year/VN. Referral 1800.55.88.49 có exact proof TB1906 page1. Source preference `ks_rev_6280c8de7f46` ưu tiên `ks_rev_f122689af572` chỉ năm2026 và cùng tuple; lưu authorization note của người dùng. Backup `backend/storage/evidence417_before.json` không bị ghi đè khi thêm ưu tiên.

## Kiểm thử và quan sát

- Hồi quy ban đầu75, sau preference77 đạt. Evidence + temporal25 đạt; PostgreSQL thật + evidence12 đạt (fixture rollback), có DB outage và JSON repair failure paths.
- Lượt full backend cuối trên runtime đã chốt: **1.063 passed / 11 failed baseline / 6 skipped**, 97,86 giây (`storage/pytest417_quote_final.log`). Không có failure mới so với11baseline416. Focused evidence+temporal37 đạt; PostgreSQL thật+evidence23 đạt, fixture rollback. Các lượt full trung gian1047/12/5 →1054/11/6 →1060/11/6 không phải số final.
- Ruff toàn Backend đạt (có cảnh báo quyền thư mục pytest cũ); không sửa FE trong đợt2 nên không chạy FE build theo fast-path scope.
- Live iteration: câu5 từng đúng5173 nhưng truy hồi có lần bỏ sót khi query quá rộng; đã thêm ranking độc lập attribute và giữ preferred spans theo ngân sách. Câu41 đã lấy đúng thể hình gồm nam1,65m/45kg,nữ1,55m/40kg cùng yêu cầu dị tật. Câu42 đã lấy20 + điều kiện2môn văn hóa+2/3ƯT≥13,34 từ whole reviewed row. Một số iteration có timeout90s/ALL_PROVIDERS_UNAVAILABLE; ghi failed rõ, không coi là thiếu tài liệu.
- Các lượt `full/verified/stable` là chẩn đoán trung gian, không gộp thành accuracy. Lượt stable mất kết nối sau khi dịch vụ local bị tắt, người dùng xác nhận lỡ tắt9router và đã mở lại cả BE/FE/worker; lỗi transport còn lại không được chấm là lỗi dữ kiện. Script đã dừng khi ConnectError thay vì tiếp tục gửi toàn bộ bộ câu hỏi.
- Lượt8trọng tâm cuối (`admissions_eval417_quote_final.json`):5supported/2missing/1failed(timeout), 5/5 quyết định supported đạt digest/revision/quote/numeric contract; config/publication/code không đổi. Câu1 mãDQN và câu5 chỉ tiêu5173 đúng ở cả DAG/directRAG. Câu42 DAG đủ20+13,34, directRAGmissing; thử riêngmodel dựphòngGemini trả đúng đầyđủ cùng facts. Câu13không còn nhầm trường tổ chức kỳthi với trường đích, nhưng vẫn missing/timeout; không kết luận áp dụng cho ngành sưphạm khi chưa đủ quote. Các status trên KHÔNG là accuracy/Ragas.
- Fresh full82 trên runtime chốt đang chạy tại `backend/storage/admissions_eval417_final82.json/.log`; kết quả và chất lượng chưa nghiệm thu cho đến khi đốisoát toàn bộ.

## Bổ sung khi tiếp tục phiên

- DirectRAG tải policy theo collection kể cả module_code trống/general; kiểm tra tenant/workspace và fail503 khi DB/policy không hợp lệ, không fallback sanglegacy. Regression tái hiện3failure trước sửa, sau sửa37focused đạt.
- `persona_scope` từ quản trị được truyền planner/proposer/verifier; identity không được dùng làm evidence. Giữ trường đích khi câu hỏi nhắc một trường tổ chức thi.
- `evidence_claims.py`: một bounded quote repair khi tất cảclaims ban đầu bị loại; numeric/same-source/span và verifier vẫn bắtbuộc. Missing vẫn missing khi repair sai; không sửa số/từ bằng fuzzy matching. Audit lưu rejection reason và repair flag. Reflowwhitespace chỉ khôi phục exact canonical span không mơhồ. Syntactic listneighbor mở rộng sibling clauses không dùng domain dictionary.
- Năm mặc định cũng áp dụng câu thôngtin chung; claim text trùng bị dedup. Scripts audit/inspect/report có đầu vào riêng, báo sốlượt đúng theo routes, phânbiệt transport/HTTP/runtime errors và không gọistatuslà chấtlượng.
- ModelOps audit không phát hiện khóa đangcooldown/lease/quotaerror. Lượt cũ có upstreamGitHub connecttimeout của9router; riêng timeout90s cuối chưa xác định được substage, KHÔNG quy hết choRedis/9router hoặc resetDB.

## Root cause truy hồi phát hiện trong benchmark

Lượt full82 `final82` đã dừng chủ động sau11ca để sửa lỗi budget, KHÔNG phải benchmark hoàn tất. Regression tái hiện reviewed rows bị loại do cắt shortlist trước/đằng sau ghépheaders. Đã sửa pack nguyên tử body+same-sourceheading, tính JSON metadata; giữ ưu tiên rows. Ngày ban hành mixed-case `Số: /TB...` không còn vượt ngưỡng uppercase để bị dùng làm seasonheading.

Facts bổ sung trước đây chỉrankBM25, có thể chọn bảngkhuvực/quychế thay hàngngành. Đã thêm semantic rerank riêng qua model/provider AIserver đãlưu, mở candidates từ câu gốc/plan/entity/attribute/variants bằngBM25 corpus, không domain dictionary. Timeout câu42 trong iterationpack đã ghi rõ **retrieval**, không phải bướcsinhcâu trảlời. Evidencebranch dùngbudgetanchors10s/rerank3s cấuhìnhđược, anchorDBsession riêng tránhcancel phá transactionparent. Degradation chỉdùng canonical/facts thật, không đổi timeoutprovider toàncục, khôngmodelhardcode/localreranker/reset.

Sau batch này44focused/30PG thật đạt; fullBackend và live4lượt13/42DAG/RAG đangxác minh tại `pytest417_retrieval_final.log` và `admissions_eval417_retrieval_final.json`. Các iterationcũ không được gộp khi đánh giá accuracy. Cần ghi lại full82 cuối trênmãchốt, chưaRagas/no productionready.

## Chốt runtime cuối và kiểm thử độc lập

Lượt retrieval4: DAGcâu13/42supported, directRAGpartial; khôngtimeout ở4lượt, nhưng manualaudit phát hiện claimkhái quát ngưỡng20cho nhómgiáoviên từ một hàngcụthể. Đã thêm metadata `entity_name` từfactđãduyệt; quotevàclaim phải chứa đúngtênthựcthểrow (NFC/case/whitespace), không dùng danh sáchngànhhardcode. Numeric/same-source/verifier và commonDAGintegrity cùngkiểmtra rowidentity; một numericquote thiếuentity bịloại. Proposer/verifier có chỉdẫn không suy từ rowra toàn nhóm.

Final gate saurowguard: **Ruffđạt;1.071passed/11baselinefailed/6skipped**,98,99s (`pytest417_entity_final.log`);45focused và31PG thật đạt. SSEHTTP200, códone+AnswerDecision (lượtSSEcodequestion trảmissing, không lấytransportpassedlàm chấtlượngpassed; done khôngchứaanswer riêng vì text gửi qua delta).

Lượt82cuối trênmãchốt: `storage/admissions_eval417_frozen82.json/.log`, đangchạy; khôngsửamã/config tronglượt này. Các lượt`final82/pack/retrieval/quote` trước đó chỉchẩnđoán và cófingerprint riêng, khônggộp làmaccuracy82. Cầncậpnhật đốisoát cuối và danh sách cònthiếu; chưaRagas/productionready.

## Bài học và giới hạn

Đúng số chưa đủ: cần đúng nguồn, năm, phương thức, đợt, thuộc tính và điều kiện. Nhóm hàng authoritative tránh mất qualifier hoặc quay lại raw cell trước hiệu đính. Nguồn cập nhật phải do quản trị xác nhận, không ưu tiên chỉ từ tên file. Một source preference không xóa thông tin riêng của flyer. Supplemental151/158 chưa có trong19nguồn; cần đối soát nguồn chính thức trước bổ sung. Việc khóa JSON/quote/số không đảm bảo semantic verifier tuyệt đối đúng; phải chấm độc lập và giữ no-answer cho phần thiếu.

Quy trình03/04/07, memory snapshot và work log được đồng bộ trong phiên; kết quả final và các ca còn thiếu sẽ cập nhật sau lượt kiểm thử.
