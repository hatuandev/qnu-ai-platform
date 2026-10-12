# Phiên #384 — Đề xuất chặn nhầm năm số liệu RAG/DAG

2026-10-12. Người dùng yêu cầu đề xuất tối ưu, chưa yêu cầu thực hiện sửa. Skill RAG: kiểm fact-first, grounding/citations/no-answer; chỉ đọc code và viết đề xuất. Không HTTP inference/DB write/policy/worker/reparse/publish/reset/qnu-sso trong phiên này.

## Nguyên nhân được kiểm chứng

Trace#383: câu hỏiCNTT2026 được rewritegiữnguyên; knowledge_answer gán21.5năm2025thành2026, guardchoqua với grounded_ratio0.8. Numericgrounding ởRAG gom các số từcandidate/citation/facts/query/system_context, không kiểmquan hệ entity/attribute/year/value. Cócitation thìis_refusal_answer trảFalse trước khi kiểmmissingdecision. Cấu trúc multi-header2024/2025 nằm ởMarkdown nhưng81factsactive chỉmãngành/tổhợp/phươngthức, chưa cócutoffyear. Worker09:20codev4 chưarestart#382; đây lànguyênnhân artifactchưaupgrade, không phải solecause củaLLMhallucination.

## Đề xuất kiến trúc

1. **Chuẩn hóa fact có kiểu/ngữ cảnh**: entityID/name, attribute, applicability_year khácdocument_year/issued_date, phương thức/đơn vị/loại sốliệukhi nguồn cung cấp, raw/normalizedvalue, qualifier, source/index/factsetrevision, evidencepage/table/headerpath/row/cell. Multi-header/mergedcells xửlýcấutrúc/spans; thiếu hoặc ambiguous khônggán nămvăn bản hoặcdefaultnămmới nhất. Dùng thuậttoán tổngquát, khôngdictionaryvá.
2. **Query constraints bất biến**: bóctáchentity/attribute/year/methodtừcâu hỏi; giữqua rewrite, khôngcho2026→2025. Mơhồ hỏi lại. Resolveentitycodequa dữliệupersisted khônggáncứngngành/năm.
3. **Answerability trước generation**: traSQLfactsactive snapshot bằngexactconstraints; cófactsvalidated thì deterministicrender sốliệu, LLMchỉdiễnđạt. MissingDBfact không chứngminhnguồnkhôngcódữliệu: kiểm tableevidence hợp lệ từartifact/Markdown vớiheader/year cònđầyđủ; nếuchưađủcăn cứ trảmissing/ambiguous, khôngdùngyearkhác đểlấpchỗtrống. Message“Chưa có căn cứ điểmchuẩn2026 trong khođãxuấtbản”, khôngsuyrathực tếtrườngchưacôngbố khi thiếuevidence. Historicalfacts hiểnthịriêngkhingườidùngmuốnthamkhảo, luôncónăm.
4. **Common structured contract RAG/DAG**: supported/missing/ambiguous + constraints/evidenceIDs/facts, backend quyết địnhstatus; khôngdựavàophânloạiregexcâuvăn hoặc“cócitation=làanswered”. DAGkhôngtựnângstatus/sinhcâutrảlờisốliệumới saugate.
5. **Per-claim verification**: mỗiassertion số liệuđối chiếu tuple entity/attribute/year/method/unit/value và sourceversion. Sốxuấthiệntrongtext/query khônglàbằngchứng; query chỉconstraintkhôngevidence. Cócitationchưađủ: phải hỗtrợđúngclaim. Sai/missingfailclosed, khôngcachesuccess. Vớiprose khôngcấutrúc, verifier/model quaModelOps hỗtrợ nhưngkhông soleapprovalcủasốliệunguycơcao.
6. **Performance/cache**: compositeindexPostgres trênscope+fact identity/year/method vàactiveindexrevision; exactfacts trảtemplatekhôngLLMjudgebổsung. Qdrantpayload cófact/content_year khiđượcchứngminh, payloadindex choactualfilters; khôngfilterdocumentyear2026 rồi nghĩ bảng2025 làfacts2026. Cache fingerprint thêmgroundingcontract/extractor/policyversions +scope/snapshot/constraints, đọccachecũngverify; invalidationchỉcachecủakhoaffected sauuserapprovalsửa, khôngxóatệpgốc.

## Ưu tiên triển khai nếu được duyệt

- P0: commonanswerability/yearconstraints/noanswergate/regression2026missing; keyversionkhôngreusecachesai.
- P1: structuredtableheader/year facts, sourceevidence, deterministicfacts-first, reviewambiguous; restartworker đúngthờigiancóthôngbáo, khôngxóaup lại. Buildstaging/publish từsnapshot/Markdown hiệncó, OCRlạichỉkhiartifactthiếutrongthực tếvàđượcchọn.
- P2: rewriteinvariants/citationclaimcheck/cache audit vàbatchgoldencases. BM25/reranker/modelupgrade giúpretrieval/diễnđạt nhưngkhôngthaythếsemanticyeargate.

## Nghiệm thu

2024=16.5,2025=21.5đúngcăn cứ;2026missingkhônggánsố; so sánh3nămphảiđánhdấu2026thiếu. IELTS6→9khônglấy7→10. Môn/phươngthứccùngnămkhácnhaukhôngtrộn. Nội dungthiếu/khôngrõheaderphảireview/clarify. Multi-turn/rewrite/cache/SSEgiữconstraint, cachedanswertráiquerybịchặn. Nguồnpaused/unpublishedkhôngphụcvụ. Khôngtuyênbốzero-hallucinationtoànappchỉvìmộtcasepass.

## Nguồn tham khảo primary

- [Qdrant filtering](https://qdrant.tech/documentation/search/filtering/?q=MatchText): payloadfilters/indexes hỗtrợconstraintretrieval, khôngtựđảmbảocorrectnessclaim.
- [ALCE, EMNLP2023](https://aclanthology.org/2023.emnlp-main.398/): kiểm citationquality/correctness táchbiệt; dùnghướngđánhgiákhôngxemcócitationlàđúng.

Chưa sửa code/test runtime; chưa chạy pytest/build do chỉ đề xuất. Memory/snapshot/nhật ký/WORK_LOG đồng bộ.
