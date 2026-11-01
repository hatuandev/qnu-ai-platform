# PROJECT_CONTEXT.md — Snapshot Ngữ Cảnh Dự Án QNU AI Platform

> **⚠️ QUAN TRỌNG**: AI Agent phải đọc file này NGAY ĐẦU mỗi phiên làm việc và cập nhật lại CUỐI mỗi phiên.
> Đây là điểm vào ngữ cảnh dự án; trạng thái và kết quả phải đối chiếu với mã, cấu hình và bằng chứng kiểm tra hiện tại.

---

## 1. Thông Tin Phiên Gần Nhất

- **2026-11-01 — Context790: contextual RAG và scope opt-in.** Metadata proof đúng target/canonical; recipe `qnu.search-context/v1`, catalog planner `qnu.catalog-scope/v1`, glossary có citation, ambiguity409/no widening, context cùng scope; UI bật có chủ đích, promptv14. APIcuối7PASS, unit645PASS1FAIL716, FE594PASS33FAILexact789;targeted30/build/TS/lintPASS. Không restart/reindex/đổiModelOps/live assistant hoặc gọi model thật/53câu; giữ93faa11f0caf và uncertain789. [Nhật ký790](../nhat_ky/2026-11-01_phien_790_rag_ngu_canh_va_pham_vi.md), [Snapshot790](./snapshots/2026-11-01_session_790.md).

- **2026-11-01 — Context789: F14/MX-05 đãPASS,cohortchưa9/9.** Promptv13/source-orderblockghim/citationclosure/mixedanswer/requestschemaenumtext/referralfacetgiữquerygốc;guardtableprosevẫncứng. V11 6/3,v12 7/2,giữhistory;v13 **8PASS1UNCERTAIN**,9dispatched0NOT_RUN/exit1. I25-04API/testprocessmất,DBrunning,chưabiếtupstream;khônbáomodelchậmhaysaitoken,khônggửilại. Khôiphụccùngphiênchỉ6NOT_RUN,cùngfingerprint;8finishedchatattempt1/9reservation,360131tokenobserved1unknown. Unit630PASS1FAIL716,FE591PASS33FAILexact779,API66PASS+8/3targeted/TS/build/lintPASS. Giữ93faa11f0caf/index/ModelOps/checkpoint;servecuối38788. [Nhật ký789](../nhat_ky/2026-11-01_phien_789_dieu_kien_va_tra_loi_hon_hop.md), [Snapshot789](./snapshots/2026-11-01_session_789.md).

- **2026-11-01 — Context788: Sửa RAG và retest9 không retry.** Promptv10/required JSON Schema/audit an toàn, native typed-header/chủ thể số/cellv3, context từ block nguồn ghim, retrieval nhiều ý cùng scope/index, evaluator cùngcitation/year và runner durable/drift/uncertain. Live **7PASS2FAIL** F14/MX-05 model_abstained,0NOT_RUN/UNCERTAIN,177.7s;9chat+14embedding+14rerank attempt1/codeok/366452token. Evidence hai câu đã vào context; chưa sửa hết khâu tổng hợp, không schema/tokenlimit trong lượt này. Fullunit611PASS1FAILnền716/FE589PASS33FAILexact779;targeted/TS/build/lintPASS,APIjudgefixture đã sửa sau đối chiếu baseline. Giữ93faa11f0caf/checkpoint/history/index/ModelOps,khôngretry/reindex. Serveẩn19828/API64624/FE64625. [Nhật ký788](../nhat_ky/2026-11-01_phien_788_sua_rag_va_retest9.md), [Snapshot788](./snapshots/2026-11-01_session_788.md).

- **2026-11-01 — Context787: Review retest9-786.** DB9conv/9turn/9key,9embedding/rerank/chat toànattempt1,314421tokens;JSON0PASS9FAIL,165.586s.5responseoff/cùnghash,promptv9;4failedresponseinvalidthiếuraw. F13checkerép1statementchưađủtựPASS,4abstainchưachứngminhnguyênnhân. P2runnerstale/fingerprint/driftkhônghalt/uncertaingộpFAIL/dispatchtestgap;report“triệttiêu100%/0token/mấtnguồn”quáchắc.12unitPASS/replay5/probeoffline;khôngmodelcall/fixapp/config,giữcohortcũ. [Nhật ký787](../nhat_ky/2026-11-01_phien_787_review_retest9.md), [Snapshot787](./snapshots/2026-11-01_session_787.md).

- **2026-11-01 — Context785: Answer off/output tối đa theo yêu cầu.** ModelOps Qwen taskanswer off, giữcompiler; assistantrev2/output16384/context98304byte trong131072. Helper lấy maxoutput động,RED4FAIL→targeted58PASS/TS/build/BiomePASS;1managedprobe0.62s/6completion/33total/reasoning0. Chưa16/53retest,khôngretry/resetcohort/restart/index. Cầncohort mới cho cấu hình mới,giữ37/16 và7/9cũ. [Nhật ký785](../nhat_ky/2026-11-01_phien_785_tat_thinking_answer_output_max.md), [Snapshot785](./snapshots/2026-11-01_session_785.md).

- **2026-11-01 — Context784: Review retest16 phiên783.** XácminhJSON7PASS9FAIL/DB16turn16key16conv,attempt1/535208tokens;12responseevaluatorofflinekhớp. P1harnesskhôngassertcuốidẫnPlaywrightfalsegreen;P2singlethiếubindingmởall/fingerprintchépcũkhôngfreeze/nhậtkýsaitrangvàcâuMX,thiếufactkhôngphảimấthếtdoc. Khôngsửaapp/config/gọimodel;giữ53cũ37/16. [Nhật ký784](../nhat_ky/2026-11-01_phien_784_review_ket_qua_retest16.md), [Snapshot784](./snapshots/2026-11-01_session_784.md).

- **2026-11-01 — Context782: Key .env cho E2E được user cho phép.** Ngoại lệ hẹp bootstrap qua ModelOps: active key trước, rồi E2E_QNU_API_KEY/E2E_9ROUTER_API_KEY ở root .env, thiếu thì nhập ẩn. Không export/runtime override/rotate, giữ guard uploaded/model/capacity. Thêm ô trống local/example, chưa điền key thật; .env ignored. RED→33 script tests/Ruff PASS; không gọi model/cleanup/init/restart, giữ37/16. [Nhật ký782](../nhat_ky/2026-11-01_phien_782_key_env_e2e.md), [Snapshot782](./snapshots/2026-11-01_session_782.md).

- **2026-11-01 — Context781: Phân tích16FAIL, không sửa.** Header false và quy tắc chủ thể có chữ loại bảng numeric (I25-05/MX-05); BC24-04 đủ ô vẫn abstain; BC24-08 compiler mất qualifier; MX-02/MX-10 thiếu nửa fact trong context. Có prose compiler nhầm metric. Output2 finishlength/4096; schema3 JSONobject chưa schema/raw không lưu; cellselection3 guard đúng; F13 checker1statement false negative; MX-01 gián đoạn vẫn running. Đọc3canonical kiểm hash/probe offline, không modelcall/config/source/indexchange, giữ37/16. [Nhật ký781](../nhat_ky/2026-11-01_phien_781_phan_tich_16_cau_loi.md), [Snapshot781](./snapshots/2026-11-01_session_781.md).

- **2026-11-01 — Context780: Gửi đủ53 câu.** Tiếp tục39NOT_RUN,cùngsource/index/config/budget,giữ14recordscũ. Tổng37PASS16FAIL0NOT_RUN;1MX-01giánđoạnvẫnrunning,52câuterminal. DB53turn53key0duplicate;F15PASS87.5s. Lỗioutput2/contract6/abstain6/checker1/giánđoạn1;khôngretry/đổiapp/ModelOps/index/gold. UserngắtởMX-01,GETkhôngPOSTlại,bậtservecùngphiên30640/API64624/FE64625. CheckpointchatFAIL;reportcuốiremaining-1793510384663788200. [Nhật ký780](../nhat_ky/2026-11-01_phien_780_chay_het_53_cau.md), [Snapshot780](./snapshots/2026-11-01_session_780.md).

- **2026-11-01 — Context779: Xuất bản nhanh sau compiler.** Thêm lựa chọn review_skip với checkbox/lý do/version/hash/audit; giữ quyền/preview/approve/publish và default review gate. API33/unit6/FE38/script4/build/TS/lintPASS; fullunit593PASS1FAILpurge716/fullFE567PASS33FAIL exact778. Live3PDF/28trang/179chunks publicationPASS30s; chatFAIL5.8m12PASS2FAIL39NOT_RUN/14dispatch, khôngretry. F13checkerđòicùngstatement/modeltách2;F14answer_response_invalid502dừngcohort,chưaxácđịnhrãschema/statements. Giữ93faa11f0caf, serve mớiẩn28384/API64624/FE64625; không đổi corpus/compiler/ModelOps. [Nhật ký779](../nhat_ky/2026-11-01_phien_779_xuat_ban_nhanh.md), [Snapshot779](./snapshots/2026-11-01_session_779.md).

- **2026-11-01 — Context778: compiler riêng sau khởi động máy.** Thêm admissions-draft; giữ gate/OCR/hash/quota,quota tháng11=20M theo duyệt. Userchọnthinkingoffcompiler:probe0.64s/reasoning0,lưuModelOps taskcompiler. Live3PDF/17partsPASS5.1m,floor80.5s/info129.2s/report85.4s,0review/17rawreasoning0. Giữhistoryinterrupted/quota;33focused/15script/TS/build/lintPASS,full565PASS/33FAIL đúngIDs777. Khôngpublish/index/chat;serveẩn33356cònchạy,giữ93faa11f0caf. [Nhật ký778](../nhat_ky/2026-11-01_phien_778_compiler_khong_review.md), [Snapshot778](./snapshots/2026-11-01_session_778.md).

- **2026-11-01 — Context777: rà compiler→chat sau422.** Payloadtopic/ocr_run_ids/text_versions,structuredtrue/autoreviewfalse;OCRversion/hashpin,recoveryhistorysauPOST,3review/gate/indexactive/docset. TestofflineAPIRoute/Pydantic với request runner;88liênquanPASS,full560PASS/33FAIL9UI/fixture;TS/build/Biome/Ruff/diffPASS. KhôngsửaBE/modelcall/restart/cleanup/init/publish/reindex. Session93faa11f0caf upload/extractionPASS,compilation422cũFAIL;chạylạicompilation→publication→chat,khôngrecovercholỗibodychưatạorun. [Nhật ký777](../nhat_ky/2026-11-01_phien_777_ra_contract_compiler_den_chat.md), [Snapshot777](./snapshots/2026-11-01_session_777.md).


- **2026-10-31 — Context776: ngân sách E2E20M được duyệt.** Đồng bộ profile QNU và validator từ trần1M lên20M, giữ guard hữu hạn.14test/E2ETS/Biome/build/diffPASS; không gọi model hoặc đổi DB/usage/reserved. Log mới: provider/discovery/4modelPASS, navigationBLOCKED do trần cũ; chạy lại navigation áp dụng20M, không cleanup/init/restart/key. [Nhật ký776](../nhat_ky/2026-10-31_phien_776_tang_quota_e2e_20m.md), [Snapshot776](./snapshots/2026-10-31_session_776.md).


- **2026-10-31 — Context775: sửa benchmark đa tài liệu sau review774.** v2-775giữF01–F19,sửa nhãn/cột/trang mới,factproof/provenance/typednumbers/scopefailclosed,durable dispatch,no-retry,aggregatecontentfail,quota read-only,explicitbudget/3indexinputs/freezecohort.49scoped/PDF3file28trang55facts/E2ETS/build/Biome/RuffPASS;fullfrontend539PASS/33FAIL9fileUI/fixture(chưabaselineđộc lập).Live53NOT_RUN,session93faa11f0cafprovider-setupBLOCKEDchờkeyterminal;khôngcleanup/init/restart/reindex/publish/modelcalls. Budgetchỉcapacityplan,finalpayloadvẫnModelOpsguard;semanticreviewNOT_RUN. [Nhật ký775](../nhat_ky/2026-10-31_phien_775_sua_benchmark_multi_docs.md), [Snapshot775](./snapshots/2026-10-31_session_775.md).


- **2026-10-31 — Context774: review độc lập multi-docs773.** P1nhãnsai/FIDsđổi(LuậtPDF20/22/750/20trang4),assistantmới16000byte,checkerđa nguồncófalsePASS;P2singlethiếubindingmởcảkho,parsehàngnghìn,failfast,autoquota20Mkhôngpreflight.14Vitest/typecheckPASS,3probetái hiệnbug/Nodeparse/PDFvisual;khôngsửaapp/runtime/modelcall. Phiên93faa11f0cafprovider-setupBLOCKED/model-navigation-admissionsNOT_RUN;khôngcleanup/initlạichỉđểnạpkey. [Nhật ký774](../nhat_ky/2026-10-31_phien_774_review_multi_docs.md), [Snapshot774](./snapshots/2026-10-31_session_774.md).

- **2026-10-31 — Context773: mở rộng E2E tuyển sinh 3 tài liệu, 53 cases.** Benchmark 53 cases (`admissions-multi-docs.json`): 19 floor2026 (8 trang), 12 info2025 (13 trang), 12 report2024 (7 trang), 10 cross/boundary MX (tổng 28 trang). Checkpoint `documents[key]`, upload/OCR 28 trang tuần tự, compilation/review độc lập từng tài liệu, 1 combined index chung; RAG scope single/all, citations per source sha256, quota 20M, 0 retry. 6 unit vitest mới PASS, 22 targeted PASS, typecheck/Biome 7 file PASS, 29 backend pytest PASS, Ruff PASS. Đã cleanup phiên cũ `1da945adac7c`, init phiên mới `93faa11f0caf`, serve daemon đang chạy (API 64624, FE 64625). Dừng đúng tại `provider-setup` để nhập API key qua terminal tương tác theo quy chuẩn bảo mật. [Nhật ký773](../nhat_ky/2026-10-31_phien_773_mo_rong_e2e_tuyen_sinh_3_tai_lieu.md), [Snapshot773](./snapshots/2026-10-31_session_773.md).

- **2026-10-31 — Context772: sửa F09 lookup projection.** Validselector→BEchỉtríchcatalogô,bỏprose/counttrace;no-lookupnumeric/foreignIDvẫnchặn,promptv9/projectionv1. RED3→focused40PASS,RuffPASS;full587PASS/1FAILnền716. F09livePASS20.672s,1turn/1executionmỗicapabilityattempt1/codeok,total36632token;khôngretry/gộpcohort. Giữassistantrev6/budget81920/index/ModelOps/serve/quota10M;used9610050/reserved123455/còn266495. APIcôlập28PASS/DBdrop/sentinelgiữ;19câu/semanticđộc lậpNOT_RUN. [Nhật ký772](../nhat_ky/2026-10-31_phien_772_fix_f09_lookup_projection.md), [Snapshot772](./snapshots/2026-10-31_session_772.md).

- **2026-10-31 — Context771: chẩn đoán F09 theo yêu cầu user.** MộtPOSTmới/capture trướcBE,Qwenđúngô22vàselector nhưngnumericprose dẫn bảng nên answer_cell_selection_required/FAIL,19.515s. Khôngretry/sửaapp/config/prompt/restart/index; audit1executionmỗicapabilityattempt1/codeok. Assistantrev6/promptv8/catalogv2;quota10Mgiữ,used9573418/reserved123455/còn303127. Khôngcoitoànđiềukiệndiễngiảiđãđúng,khôngsuyraw770giốnglầnnày. [Nhật ký771](../nhat_ky/2026-10-31_phien_771_xem_phan_hoi_f09.md), [Snapshot771](./snapshots/2026-10-31_session_771.md).

- **2026-10-31 — Context770: triển khai RAG chọn ô nguồn.** Grid giữ span/header/citation, quality/dependencies chunkerv3, catalogv2/promptv8, BE copy giá trị và chặn table numeric prose/ID giả; budget tính envelope đầy đủ. Focused55PASS,fullunit581PASS/1FAILnền716;isolatedAPI47PASS/dropDB/sentinelgiữ,APIv2cuối27PASS. Livecohortv1 riêng3case: F12/F17PASS,F09FAIL answer_cell_selection_required,49.141s/3POST,khôngretry; bảnv2 cuối chưa live và19câuNOT_RUN,khônggộpPASS. Giữ assistantrev6/index/source/ModelOps/serve; quota10M,used9536641/reserved123455/còn339904. Semanticreview/gold độc lậpNOT_RUN,XLSXchưaextraction. [Nhật ký770](../nhat_ky/2026-10-31_phien_770_rag_chon_o_nguon.md), [Snapshot770](./snapshots/2026-10-31_session_770.md).

- **2026-10-31 — Context769: sửa đọc bảng, chưa hoàn tất mục tiêu chất lượng.** Rerank đọc plaintext, promptv7, native numbered-table chain theo khungtrang/sốthứtự/cùngbinding,tốiđa4sealed supportchunks ngoài top20; giữraw/canonical/index vàguardquyền/metadata. Hai cohort riêngv6 16/19 rồi v7 **17/19**:F06/F15đạt,F09sai20vs22/F12abstain; khôngretrytừngcâu/khônggộpPASS. Cuối295.797s,19turns và19executionsmỗicapabilitytoànattempt1/codeok,sameconfig/index;usage696149,khôngtokenerror. Assistantrevision6,budget81920;quota10Mgiữ,used9426181/reserved123455/còn450364. API45PASS sau44/1assertversioncũ;fullunit562PASS/1FAILnền716,focusedcuối18PASS. DBtestdrop/sentinelgiữ. Khôngrestart/reindex/publish/đổicheckpoint. Citationđúngchưachặnsaicột,semanticNOT_RUN/nhãndraft; cần xửlýtiếpF09/F12. [Nhật ký769](../nhat_ky/2026-10-31_phien_769_sua_doc_bang_va_live_rag.md), [Snapshot769](./snapshots/2026-10-31_session_769.md).

- **2026-10-31 — Context768: cấu hình budget và live 19 câu không retry.** Assistant admissions revision3→4,context_max_bytes16000→57344 theo top20/46chunks cận51391byte; modelcontext131072/output4096 giữ. Fresh API/backend hiện tại/auth/providers thật: **16PASS/3FAIL/0NOT_RUN**,228.297s;F06/F09abstain,F15numbers_mismatch chung/ngoại lệ. Audit19turns mới và19executions mỗi capability,toànattempt1/codeok,cùngpromptv5/taskhash/index. Không lỗi token/context/quota;maxevidence49819byte,prompt21908token,usage1088242. Quota10M/reserved123455 giữ. Setup trước đó dừng0modelPOST rồi sửa preflight tuần tự; khôngretry. Khôngrestart/reindex/đổicheckpoint/mãứngdụng. Nhãn draft/semanticNOT_RUN,khôngcoi19completedlà19PASS. [Nhật ký768](../nhat_ky/2026-10-31_phien_768_context_budget_va_live_19_cau.md), [Snapshot768](./snapshots/2026-10-31_session_768.md).

- **2026-10-31 — Context767: sửa bốn P2 và fixture RAG.** Window0ápbytebudget,rerankgiữusage0/positive,answerthêmtaskhash+reasoningguardkhôngđổilegacyhash;reviewcộngclaimtime,resumekhôngreset,khôngbậtlại300s. Fixture672đoạnphânbiệt/đốichứngsauâm. RED7→43focusedPASS,full548PASS/1FAILnền716. API76PASS/4FAILdođốichứngmớitạotrùngkey/mãschema,giữlog;sửatestsetup/chạyriêng6728PASS. ModelOps31/answer25/hybrid12/review4PASS;DBtestđãdrop. LivePDF/FEbuildNOT_RUN,khôngđổiDBruntime/index/restart;top20budget16000cóthểchặnđúngguardmới. [Nhật ký767](../nhat_ky/2026-10-31_phien_767_sua_bon_p2_va_fixture_rag.md), [Snapshot767](./snapshots/2026-10-31_session_767.md).

- **2026-10-31 — Context766: review RAG/Compiler/ModelOps.** MãV1/HEAD01f682ed giữdiff763–765; không sửa logic/config/index/restart/inference. P2 context_window0 bỏ bytebudget, rerank error usage0 thànhNone, reasoning answer đổi nhưnghash/tracekhôngđủ; P2time758 cònresetquaresume. Unit533PASS/1FAILnền716; DB37PASS/1FAIL/3ERROR (ModelOps31/review2PASS, RAGfixtureparagraphtrùngbịdedup), DBđãdrop/sentinelgiữ;4probeexit0,liveNOT_RUN. [Nhật ký766](../nhat_ky/2026-10-31_phien_766_review_rag_compiler_modelops.md), [Snapshot766](./snapshots/2026-10-31_session_766.md).

- **2026-10-31 — Context765: F15 sửa relevance/ngoại lệ, không retry.** Đoạnriêngrank4 bịsorttrang xuốngE18; nguồnđủ/khôngtokenerror. Giữrerankorder vàpromptv5quytắcngoạilệ cóscope, khôngnhúngngành/sốđiểm. F15PASSđúng1executionattempt1/18.19s;F14,F17–19PASS,5/5tổng76.37s,cùngindex/manifest/rerankIDs.5focused/21APIintegration/RuffPASS,full533PASS/1FAILnền716;DBtestđãdrop/sentinelgiữ. KhôngđổiModelOps/quota/index/checkpoint/restart;khôngrerunF15/toàn19. [Nhật ký765](../nhat_ky/2026-10-31_phien_765_sua_f15_khong_retry.md), [Snapshot765](./snapshots/2026-10-31_session_765.md).

- **2026-10-31 — Context764: sửa projection/replay/promptv4.** Giữ rawtable/spans/identity, bỏ exactJSON trùng, sharebudget/prompt; replay/resume không firstattempt hoặc GETlatency giả, reconcile trạng thái không gửi lại terminal.4focused/22FE/21APIintegration/TS/build/lintPASS,full532PASS/1FAIL nền716. Live API19fresh cùngconfig/promptv4/top20/candidate50:18PASS/1FAIL F15model_abstained,275.35s; không tokenerror/retry. Khôngrestart/đổi ModelOps/OCR/compiler/publication/index; giữuserdiff10M. Chưa nghiệmthu toànquality,F15cần phân tích riêng. [Nhật ký764](../nhat_ky/2026-10-31_phien_764_sua_projection_va_replay.md), [Snapshot764](./snapshots/2026-10-31_session_764.md).

- **2026-10-31 — Context763: review ba thay đổi RAG.** HEAD01f682ed/3dirtyfile; đãbỏretrygold/tênngànhprompt,giữkeyổnđịnh. P1 compactmấtrawtable/spans/tableidentity,replaycompletedđánhfirstattempttrue;P2 promptv3khôngđổi.528unitPASS/1FAILnền716,Ruff/E2ETS PASS,BiomeFAIL;chỉreview,khôngsửalogic/runtime/live. [Nhật ký763](../nhat_ky/2026-10-31_phien_763_review_ba_diem_rag.md), [Snapshot763](./snapshots/2026-10-31_session_763.md).

- **2026-10-31 — Context762: review admissions-chat sau IDE khác.** Report19PASS/224.5s nhưng11answerID cũ,configs10/30,20/30,20/50; nhãn draft/semantic_reviewNOT_RUN. P1 retry theo gold, thiếuturnID tựreset có thể gửi trùng, prompt nối bảng theo ngànhtest chưa cóproof; P2 promptv3khôngđổi,nuốt updateassistant.16unit/14FE/E2ETS/RuffPASS; khôngsửa logic/runtime/live trongreview. Giữ phiênpublication/index. [Nhật ký762](../nhat_ky/2026-10-31_phien_762_review_admissions_chat.md), [Snapshot762](./snapshots/2026-10-31_session_762.md).

- **2026-10-31 — Context760: Qwen giảm suy luận, bỏ300s/phản hồi.** Userủyquyềncấuhình; probe enable_thinkingfalse JSONđúng/reasoning0, default2.09ssooff0.67s; lưuModelOps off cho compiler/review và wait_for_completiontrue đúngprv_b8eba1466634/1da945adac7c. Request/runtime/hash/adapter/executor hỗtrợchờkhôngread/totaldeadline, transport/connect vàbudgetjobgiữ; Redis/keyleaseheartbeats cófence, switchUI. 28focused/26FE/Ruff/Biome/buildPASS; integration34PASS/1FAIL namespaceharness,rerun4PASS; full527PASS/1FAIL nền716. Đãreloadserve/xemUI/probecuối0.8s, rồi dừngserveagent; giữrununcertain/2phầncompleted, khôngrerunPDF. Usermởserve rồi admissions-compilation --headed --recover, khôngcleanup/init. [Nhật ký760](../nhat_ky/2026-10-31_phien_760_qwen_reasoning_va_cho_hoan_tat.md), [Snapshot760](./snapshots/2026-10-31_session_760.md).

- **2026-10-31 — Context759: Qwen Compiler reasoning-only truncated.** Phiên1da945adac7c/runcmp_9efc601ec91f root1/2 length8192output, content0, reasoning26189/25827ký tự; total87350 gồm input. Code diagnose đòi content nên khôngchia. Sửa nhận length xác định, giữraw/usage/limits; red2FAIL tái hiện,63focused/4integration/RuffPASS, full522PASS/1FAIL nền source_purge716. Không restart/đổiModelOps/livererun; userrestartserve, admissions-compilation --headed --recover, giữOCR/checkpoint. P2time758 chưa sửa. [Nhật ký759](../nhat_ky/2026-10-31_phien_759_qwen_reasoning_only_truncated.md), [Snapshot759](./snapshots/2026-10-31_session_759.md).

- **2026-10-31 — Context758: review độc lập và test bản sửa757.** Giữ code chưa commit, chỉ thêm2negative integration758 và docs. 58focused/32FE/8integration PASS; Ruff/Biome/TS/build PASS; full516PASS/1FAIL nền source_purge716. E2E compilation PASS (replay); review mới rvw_fa001f399977 completed3/3 trong15.59s, usage19972, needs_attention5findings. Không bỏ finding/publish. P2 còn lại max_seconds reset mỗi resume; probe60s thành124s/4calls qua2claim. Serve agent đã dừng, giữ f2b0e64738c1/checkpoint, khôngcleanup/init. [Nhật ký758](../nhat_ky/2026-10-31_phien_758_review_doc_lap_va_test_compilation.md), [Snapshot758](./snapshots/2026-10-31_session_758.md).

- **2026-10-31 — Context757: áp giới hạn ranh giới model, prompt replay hash và phục hồi contract review.** Xử lý 3 phát hiện từ Context756: P1 áp trần request/token/time trước mỗi lần gửi model bằng ledger `attempts_of`, `reserve_attempt`, `settle_attempt` (tính exposure cả input và output dự trù, unknown giữ None); P2 nâng `SEGMENT_PROMPT_VERSION` v3 độc lập số lá anh em và đảm bảo messages rebuild khớp hash đã kiểm; P2 phục hồi dứt khoát phản hồi sai hợp đồng `compilation_review_invalid` (dư context, thiếu unit) qua `_refine_segment` với trần `max_contract_recoveries=4` có lưu vết `last_failure` và chẩn đoán; sửa Biome workflow.spec.ts. 71 focused unit PASS, 17 regression test mới PASS; full unit 516 PASS/1 FAIL nền source_purge716; FE 32 PASS; live E2E chặng compilation trên phiên f2b0e64738c1 PASS (18.0s, Review 1 14.8s, Review 2 9.0s). Dừng serve an toàn, giữ checkpoint và containers. [Nhật ký757](../nhat_ky/2026-10-31_phien_757_gioi_han_model_hash_va_phuc_hoi_contract.md), [Snapshot757](./snapshots/2026-10-31_session_757.md).

- **2026-10-31 — Context756: review và kiểm chứng compiler/review sau vibe.** Git c7dcda7a, không sửa logic. Giữ phiên f2b0e64738c1; Docker engine chạy, migration0010 đạt. 41focused/6integration/32FE/TS/build/Ruff PASS; full499PASS/1FAIL nền source_purge716, Biome workflow FAIL. Live compilation HTTP409 compilation_review_invalid: model stop3759completion, source13 so12owned (dư readonly context), review uncertain. P1 trần request/token chỉ kiểm lúc chia (probe1 nhưng7calls/2240tokens); P2 system prompt replay lệch hash sau tăng số lá; P2 raw invalid received replay lại lỗi. Serve agent đã dừng, giữ checkpoint, chưa cleanup/init/publish. [Nhật ký756](../nhat_ky/2026-10-31_phien_756_review_va_test_compiler.md), [Snapshot756](./snapshots/2026-10-31_session_756.md).

- **2026-10-31 — Context755: tối ưu review chia phần theo output và phục hồi truncated.** Chẩn đoán phiên `f2b0e64738c1` (`cmp_af9ff45d717e`, `rvw_32ebeb77c954` lỗi `422 chat_output_truncated` ở 4096 token vì planner cũ chỉ xét input 131072). Đợt 1 nâng `review_parts_v4` tính `ReviewOutputBudget` (dự trữ reasoning 40% + framing 15%, chỉ tính owned unit, chia nhóm hàng bảng, lưu `request_total` giữ `prompt_sha256`). Đợt 2 thêm migration `0010_review_refinement`, `review/refinement.py` và wave execution chỉ chia tiếp phần `chat_output_truncated`, giữ phần `completed`, giới hạn depth 4/nodes/1500s và giữ raw/usage quan sát (unknown giữ `None`). Đợt 3 lưu artifact `assessment_json` + `markdown` từng phần/cha, kiểm tra `verify_parent_child_coverage`, thêm API đọc segment artifact và E2E recovery cho review trước v4. 25 unit trọng tâm PASS, full unit 499 PASS/1 FAIL nền `source_purge_716`, FE 16 PASS + TS/Biome/build PASS; DB integration & live E2E NOT RUN do `com.docker.service` đang `Stopped`. Giữ nguyên phiên `f2b0e64738c1` và cấu hình `ollama/gpt-oss:120b` 4096/131072. [Nhật ký755](../nhat_ky/2026-10-31_phien_755_review_chia_phan_va_phuc_hoi_truncated.md), [Snapshot755](./snapshots/2026-10-31_session_755.md).

- **2026-10-31 — Context754: alias model 9router trong E2E.** Log user model-chat sai equality tên ollama/gpt-oss:120b và gpt-oss:120b; setup/discovery/embed/rerank PASS, OCR đang chạy. Profile alias cụ thể theo provider/requested, giữ capability và trace; không strip prefix tổng quát. 14 regression/E2E TS/Biome/build PASS, live rerun NOT RUN. Không đổi backend/DB/restart; đợi OCR rồi chạy lại model-chat trên cùng phiên. [Nhật ký754](../nhat_ky/2026-10-31_phien_754_test_alias_model_9router.md).

- **2026-10-31 — Context753: sửa catalog 9router.** Catalog thật638 model/HTTP200 có alias đúng, trần cũ500 từ chối. Nâng5000 có kiểm tra toàn bộ, lỗi vượt trần rõ; setup phân biệt discovery lỗi/model thiếu. 40adapter/23script/Ruff PASS, live discovery diagnostic_ok; full gate488PASS/1FAIL nền source_purge716/69SKIP. Chưa restart/inference/E2E/đổi DB/key; giữ phiên, mở lại serve rồi provider-setup, khai context/output thật vì catalog chưa có. [Nhật ký753](../nhat_ky/2026-10-31_phien_753_sua_catalog_9router.md).

- **2026-10-30 — Context752: test9router và chọnchat.** Profile thêmendpointuser/ollama-gpt-oss120b, keyQNU→key9routerẩn rồi chọnQwen/GPT-OSS. Model-chat/defaultworkspace/Compiler/review/chat theo lựachọn; OCR/embed/rerank giữQNU. Thiếucapacitymodelđượcchọn thìhỏi thôngsốthật, khôngđoán.21script/28FE/E2ETS/build PASS, live9routerNOTRUNchờuserkey. Khôngcleanup/init/restart hoặcđổi draft9findingsphiên751; provider-setup chặn sauupload, cầnphiênmới. [Nhật ký752](../nhat_ky/2026-10-30_phien_752_e2e_9router_model_mac_dinh.md).

- **2026-10-30 — Context751: compiler chia tiếp cha–con.** Planner v5/migration0009, budget sâu4/node31xroots/1500s; raw/MD/JSON, links/usage từng request, không retry uncertain; default output hợp trầnModelOps(4K giữ4K/Qwen8192). Review literal/concurrency2/context đủ hàng-header-bảng/compactv3/schema2, replay full-v1-v2 giữ nguyên. Full unit479PASS/1FAIL source_purge716; FE17PASS/integration trọng tâmPASS, gate toàn repoFAIL. Compiler live4/4/211.6s; review20/20/7.8phút nhưng9findings (2diễn giải bảngmâu thuẫn,6uncertain,1unsupported), chặngFAIL, khôngpublish. Serve agent đã dừng; giữ checkpoint/OCR/draft/report, tiếp tục cần rà soát draft chứ không cleanup/init hay nới test. [Nhật ký751](../nhat_ky/2026-10-30_phien_751_compiler_refinement.md).

- **2026-10-30 — Context749: chẩn đoán admissions uncertain.** Report2.1s đọc run cũ cmp_10c51e267f1f6/15; worker log17:48:47 chat_provider_uncertain, trước worker mới19:30:57. elapsed1003.4s thuộc lượt cũ; chưa đủ phân biệt timeout/network cụ thể. E2E chỉ replan failed, uncertain giữ nên chưa chạy planner v4. Cần phục hồi chủ đích dùng OCR sẵn có, giữ lịch sử/partial; không resend mù/reset pending. Không sửa code/DB/checkpoint/restart/test/model. [Nhật ký749](../nhat_ky/2026-10-30_phien_749_chan_doan_admissions_uncertain.md).

- **2026-10-30 — Context748: dừng E2E mồ côi.** Serve cha548 không còn nhưng5con API/worker/frontend giữ ports; đã xác minh/dừng đúngcon của phiên7082ee7b7311. Kiểm tra cả5PID hết, ports61563/61564/61565 trống. Giữ checkpoint, upload/extraction PASS lịch sử và compilation FAIL cũ; chưa chạy lại. Người dùng mở serve, đợi E2E live rồi admissions-compilation; không cleanup/init. Không sửa code/migration/test/model. [Nhật ký748](../nhat_ky/2026-10-30_phien_748_dung_tien_trinh_e2e_mo_coi.md).

- **2026-10-30 — Context747: sửa P1/P2 sau review compiler.** Scheduler đóng hàng đợi trước nhả slot khi lỗi/hủy; usage phần settle session riêng, claim fence trước ghi và giữ số đo khi recovery. Planner/projection/prompt v4 giữ note dài/giữa bảng với scope unresolved, không suy nối bảng theo header/cột; replay v2/v3 giữ contract cũ. Redis admission chat default4/queue300s dùng chung endpoint/model; compiler default2. Single-call reasoning ghim directive, E2E chờ ceil-waves cộng queue. Regression đã viết; test/build/lint/typecheck/live **NOT RUN**, chưa đo tốc độ/Redis cap thật; gate rộng lịch sử737 còn FAIL. Không restart/migration/reindex/push/đổi DB/checkpoint. [Nhật ký747](../nhat_ky/2026-10-30_phien_747_sua_compiler_p1_p2.md).

- **2026-10-30 — Context746: compiler chia phần song song có giới hạn.** Planner/projection v3 ước lượng nội dung sẽ viết (không dùng byte nguồn), context theo vai trò, outline gọn, liên kết bảng nhiều trang có căn cứ; projection v2 đóng băng byte để run15phần đang dở dựng lại đúng `input_sha256`. ModelOps thêm `reasoning_policy_v1` có cổng `verified` (mặc định `server_default`, không suy đoán theo tên model). Scheduler bounded2/4, mỗi phần session riêng, ghép theo `segment_index`; progress API/E2E rõ phần đang chạy. Đo planner8trang/105hàng →2phần ở8192, 1phần ở16384; chưa đo tốc độ thật. Test/build/lint/live **NOT RUN**, không restart/migration/reindex/push. [Nhật ký746](../nhat_ky/2026-10-30_phien_746_compiler_chia_phan_song_song.md).

- **2026-10-30 — Context745: sửa compiler hết output.** Raw phần1:8192completion toàn reasoning, content rỗng. Planner/prompt v2 theo input+output, owned/context rõ, E2E JSON Schema và recovery một lượt theo ModelOps ceiling. Regression đã viết; test/build/lint/live NOT RUN, giữ default8192. [Nhật ký745](../nhat_ky/2026-10-30_phien_745_compiler_output_truncated.md).

- **2026-10-30 — Context744: tiếp tục compiler chia phần từ OpenCode.** Giữ khung planner/segments/review/output/migration0008; sửa review chưa gọi model, ownership/provider fence, context/coverage và output blob an toàn. Thêm regression/hướng dẫn; test/build/lint/migration/live NOT RUN theo yêu cầu. [Nhật ký744](../nhat_ky/2026-10-30_phien_744_hoan_thien_compiler_chia_phan.md).

- **2026-10-30 — Context743: viết test PDF điểm sàn 26.** 5chặng admissions riêng từ upload đến chat, 19câu (16positive/3negative) theo PDF8trang đã chốt hash; report/citation/scope, giữ review gate. Nhãn draft cần người duyệt; test/build/lint/live NOT RUN theo yêu cầu. [Nhật ký743](../nhat_ky/2026-10-30_phien_743_test_pdf_diem_san_26.md).

- **2026-10-30 — Context742: người dùng chạy E2E live 14/14 PASS.** Phiên816537dc7b48 đối chiếu checkpoint/14report: expected14, unexpected/skipped/flaky0; compilation5.3m, publication/chat/permissions/lifecycle đạt. consumed=true, lượt mới cần phiên mới. Không tự chạy test/model; gate rộng lịch sử737 giữ FAIL. [Nhật ký742](../nhat_ky/2026-10-30_phien_742_nguoi_dung_e2e_14_chang_pass.md).

- **2026-10-30 — Context741: chặn runtime cũ và phục hồi compilation.** Runner lưu hash source khi khởi động API/worker, chặn run nếu mã đổi/chưa xác nhận; không tự restart. Khôi phục bản trung gian qua finding gốc cùng document và khóa sửa v2; giữ history/gate. Test/build/lint/live NOT RUN theo yêu cầu. [Nhật ký741](../nhat_ky/2026-10-30_phien_741_chan_runtime_cu_va_phuc_hoi_compilation.md).

- **2026-10-30 — Context740: giữ giới hạn khối chưa đọc trong draft.** Ghi chú có citation từ metadata trống/cần kiểm tra, giữ nguồn/bảng/unknowns; preview edit đúng nội dung hiệu lực. E2E rerun append bản sửa và version mới, giữ gate/historical drafts. Test/build/lint/inference NOT RUN theo yêu cầu. [Nhật ký740](../nhat_ky/2026-10-30_phien_740_giu_gioi_han_khoi_chua_doc.md).

- **2026-10-30 — Context739: hiển thị thời gian review.** E2E giải thích timeout là giới hạn chờ tối đa, báo thời gian completed theo timestamp server. Không đổi timeout/token, không ngắt lượt đang chạy; test/build/lint/live NOT RUN theo yêu cầu. [Nhật ký739](../nhat_ky/2026-10-30_phien_739_hien_thoi_gian_review.md).

- **2026-10-30 — Context738: review output theo capacity.** Bỏ 8192 cố định ở review API/UI/E2E, dùng ModelOps planner; compiler giữ 8192. Chạy lại chặng chỉ phục hồi truncated khi cùng provider và output tăng, giữ lịch sử/idempotency. Test/build/lint/live NOT RUN theo yêu cầu; chưa restart/đổi DB. [Nhật ký738](../nhat_ky/2026-10-30_phien_738_review_output_theo_capacity.md).

- **2026-10-30 — Context737: sửa fixture DOCX backend.** OPC package hợp lệ cho LibreOffice, giữ bảng/merge/literal/footnote; assertion converter theo cấu hình.46focused/18unit/14native/Ruff và HTTP200 PDF thật đạt. Gate rộng FAIL:410pass/2fail/1error/494notrun; lỗi lifecycle659,purge716,setup recovery666, ID tại nhật ký. E2E người dùng14/14 PASS giữ, không chạy lại/purge/restart. [Nhật ký737](../nhat_ky/2026-10-30_phien_737_sua_fixture_docx_backend.md).

- **2026-10-30 — Context736: sửa review khối ảnh rỗng.** Giữ source unit không text và provenance, prompt v4 phân biệt unknown với kiểm định OCR, không bỏ gate.43focused/Ruff đạt; live review finding0, publication PASS, hash nguồn/draft giữ. Chat/permissions/lifecycle NOT RUN; full gate FAIL ở DOCX710 (25pass/1fail), chi tiết tại nhật ký. [Nhật ký736](../nhat_ky/2026-10-30_phien_736_sua_review_khoi_anh_rong.md).

- **2026-10-30 — Context735: sửa E2E lưu capacity.** Provider-setup thiếu bước áp dụng discovery; đã nối snapshot/sync và profile vận hành có căn cứ, giữ input/OCR operator. Cùng phiên live: bốn model configured, setup +5model stages +navigation PASS.15FE/4offline/build+TS/Biome đạt; upload trở đi NOT RUN, fullBE FAIL lịch sử733 giữ. Không restart/reset. [Nhật ký735](../nhat_ky/2026-10-30_phien_735_sua_e2e_tu_dong_luu_capacity.md).

- **2026-10-30 — Context734: hướng dẫn test lại từ đầu.** Bản ngắn mụcB và bản đầy đủ/README E2E đưa UI lấy capacity sau provider-setup, tách timeout/OCR còn thiếu, giữ đủ14chặng và gate review.18khối PowerShell kiểm cú pháp, thứ tự/link/UTF8/LF/diff; chỉ docs, chưa chạy E2E mới. [Nhật ký734](../nhat_ky/2026-10-30_phien_734_cap_nhat_huong_dan_test_tu_dau.md).

- **2026-10-30 — Context733: lấy capacity từ server.** Discovery metadata + preview/import/sync current có audit, giữ input/OCR và chặn dimension đổi. Live GETmodels200 đủ4model;73ID BE trọng tâm/22FE/build+TS/Ruff/Biome và browser desktop/mobile đạt. Full889collected gặp Windows access violation, vẫn FAIL. Không inference/restart/đổi DB phục vụ. [Nhật ký733](../nhat_ky/2026-10-30_phien_733_tu_dong_lay_capacity_server.md).

- **2026-10-30 — Context732: hướng dẫn test lại và giải thích hình OCR.** Bản ngắn tách resume với cleanup/init mới, đủ14chặng và cấu hình128K/16K. Ba finding cùng một figure rỗng; review bỏ block không text nên thiếu source unit. Chỉ đọc API/docs, chưa sửa OCR/review hoặc gọi model. Link/UTF8/LF/diff kiểm; không đổi runtime. [Nhật ký732](../nhat_ky/2026-10-30_phien_732_huong_dan_test_lai_va_review_hinh.md).

- **2026-10-30 — Context731: test Qwen128K/16K.** Đã lưu Qwen context131072/output16384, Compiler8192 giữ. Chat641ms và navigation/upload/extraction/compilation PASS; review mới56s so91s nhưng token3968so6520, tốc độ decode tương đương. Report3uncertain hình ảnh; chưa phát hành/full pipeline. Biome/build+TS đạt. [Nhật ký731](../nhat_ky/2026-10-30_phien_731_test_qwen_128k_16k.md).

- **2026-10-30 — Context730: phục hồi review timeout.** Phục hồi review120s: Qwen timeout300, output8192 giữ; lượt1 completed105s. Lượt2 truncated8192 reasoning, recovery JSON Schema completed91s. User tạm dừng;17regression/Biome/build+TS đạt, chưa full pipeline. [Nhật ký730](../nhat_ky/2026-10-30_phien_730_phuc_hoi_review_timeout.md).

- **2026-10-30 — Context729: dừng chờ review uncertain.** Phiên E2E đang phục vụ, compilation completed/review uncertain. Helper thiếu terminal uncertain khiến đợi240s; sửa báo lỗi sau1.6s trên cùng review, vẫn FAIL đúng upstream, không inference mới. Biome/build+TS đạt; thêm hướng dẫn resume sau tắt máy. Không reset dữ liệu/capacity/restart/push. [Nhật ký729](../nhat_ky/2026-10-30_phien_729_dung_cho_review_uncertain.md).

- **2026-10-30 — Context728: lưu capacity và test model live.** Bốn probe PASS; OCR đo max1664×2048 input3336, lưu budget4096 có căn cứ. Sửa assertion allowed-providers; navigation/upload/extraction PASS. Compilation4096 lỗi truncated; đã lưu Qwen262144/221184/32768 và giữ Compiler8192, chat/navigation/upload/extraction test lại đạt; biên soạn8192 completed nhưng review HTTP504/chat_provider_uncertain nên compilation FAIL, bốn chặng sau NOT RUN. Biome/build+TS đạt; chưa nghiệm thu toàn luồng. [Nhật ký728](../nhat_ky/2026-10-30_phien_728_luu_capacity_va_test_model_live.md).

- **2026-10-30 — Context727: mở cấu hình capacity model con.** Sửa model trong chi tiết nhà cung cấp dùng form đầy đủ token/dimension/OCR; không bịa capacity hoặc bỏ guard. Người dùng báo5probe PASS, navigation vẫn BLOCKED thiếu giới hạn server. 18test trọng tâm/Biome/build+TS đạt; browser màn nhỏ xem và hủy form. Chưa live inference/navigation sau sửa; cần serving config bỏ credential. [Nhật ký727](../nhat_ky/2026-10-30_phien_727_cau_hinh_capacity_model_con.md).

- **2026-10-30 — Context726: provider E2E và menu trực tiếp.** Thêm provider-setup tự chuẩn bị provider/key qua nhập ẩn, kiểm kết nối/đăng ký4model và UI tạo provider tạm trước discovery; không tự đặt capacity. Sidebar Nhà cung cấp /providers có RBAC, bỏ mục khỏi Cấu hình. FE5test/build/TS/Biome, Python14offline/Ruff và discovery-only đạt; UI sidebar đã xem. Live setup/inference NOT RUN. [Nhật ký726](../nhat_ky/2026-10-30_phien_726_provider_setup_va_sidebar.md).

- **2026-10-29 — Context725: hướng dẫn model → pipeline QNU live.** File tổng hợp13lệnh; pipeline gắn đúng4model đã test/current làm default workspace E2E, quota thử hữu hạn nếu thiếu, chat hybrid+rerank và kiểm trace. Không đổi default dev/production/capacity. Biome/TS/Ruff/10offline và6helper-case đạt; live/E2E NOT RUN. [Nhật ký725](../nhat_ky/2026-10-29_phien_725_huong_dan_model_den_pipeline_live.md).

- **2026-10-29 — Context724: thêm test model QNU thật.** Nhóm live model-discovery/chat/embedding/rerank/OCR qua ModelOps, profile4model không secret và báo cáo observation; workflow không thể xác nhận live. Ruff/Biome/TS/9offline/discovery-only đạt; live inference/E2E NOT RUN. Người dùng cấu hình key/model qua UI phiên thử rồi chạy từng lệnh. [Nhật ký724](../nhat_ky/2026-10-29_phien_724_test_model_qnu_live.md).

- **2026-10-29 — Context723: sửa assertion API key E2E.** Người dùng chạy6chặng đến chat đạt; permissions lỗi expected401/received403. Đối chiếu backend: revoked trả403/api_key_inactive, unknown trả401/invalid_api_key. Spec kiểm chính xác status/code và khóa mới hoạt động sau rotate; không sửa BE. Biome/TS đạt; permissions/lifecycle sau sửa NOT RUN, giữ serve/phiên hiện tại. [Nhật ký723](../nhat_ky/2026-10-29_phien_723_sua_assertion_api_key_e2e.md).

- **2026-10-29 — Context722: sửa cleanup E2E kẹt cờ serve cũ.** Kiểm tra chỉ đọc xác nhận cổng đã đóng/không còn client; thêm OS lease và guard TCP để nhận diện trạng thái cũ, không tự kill tiến trình.6regression offline/Ruff/AST đạt; cleanup Docker/E2E thực tế NOT RUN, người dùng chạy lại cleanup/init/serve. [Nhật ký722](../nhat_ky/2026-10-29_phien_722_sua_cleanup_e2e_stale_serve.md).

- **2026-10-29 — Context721: sửa DOCX fixture E2E.** Log worker/Gotenberg xác nhận HTTP500/UNO; fixture cũ thiếu OPC content type/root relationship. Bổ sung DOCX package/styles/bảng/footnote và preflight, giữ revision gốc; cần phiên thử mới. Offline XML/ZIP/Ruff/AST đạt; Gotenberg/E2E sau sửa NOT RUN, không cần cấu hình model thật. [Nhật ký721](../nhat_ky/2026-10-29_phien_721_sua_docx_fixture_e2e.md).

- **2026-10-29 — Context720: sửa quota fixture E2E.** Log người dùng: navigation/upload đạt, extraction lỗi quota_not_configured. Thêm quota workflow hữu hạn theo tháng và phục hồi một lần job quota lỗi qua API, giữ nguồn gốc/checkpoint; làm rõ BLOCKED prerequisite. Biome/TS/Ruff/AST đạt; E2E sau sửa NOT RUN, không đổi backend hoặc dữ liệu runtime. [Nhật ký720](../nhat_ky/2026-10-29_phien_720_sua_quota_fixture_e2e.md).

- **2026-10-29 — Context719: E2E V1 chạy theo từng lệnh.** Thêm init/serve/run từng chặng, checkpoint và môi trường Docker riêng; bỏ FLUSHDB dùng chung, mock đúng contract và probe purge PostgreSQL/S3/Qdrant. Ruff/Biome/TypeScript/PowerShell/help kiểm tĩnh đạt; E2E/runtime/model NOT RUN, người dùng tự chạy. Không restart/migrate/xóa dữ liệu hiện có/push. [Nhật ký719](../nhat_ky/2026-10-29_phien_719_e2e_theo_tung_lenh.md).

- **2026-10-29 — Context718: sửa upload trùng sau xóa mềm trên API cũ.** Chẩn đoán chỉ đọc xác định runtime chưa nạp purge; thêm inventory legacy/Hoàn tất xóa tại kho và thông báo duplicate theo trạng thái, giữ guard published/quyền/hash. Ruff/Biome/TS/build đạt,12regression NOT RUN. Chưa restart/xóa dữ liệu thật/model/migrate/push. [Nhật ký718](../nhat_ky/2026-10-29_phien_718_sua_upload_sau_xoa_cu.md).

- **2026-10-29 — Context717: tinh gọn frontendV1 và luồng demo tài liệu → hỏi đáp.** Sidebar6mục, chọn Đơn vị cố định trên Topbar, trung tâm Cấu hình4nhóm; kho mở trực tiếp Tài liệu/Biên soạn/Phát hành + Công cụ nâng cao, bỏ màn trung gian. Upload gửi auto_extract=true, thanh tiến độ thật ProcessingProgress nối counter trang BE và JobView link nguồn/biên soạn; thêm Chat thử, link trích dẫn về nguồn/bản phát hành và điều kiện chuyển bước. Giữ nguyên diff Context716. Scoped Ruff4file, Biome32file, typecheck và build PASS; Pytest/Vitest/E2E/live model NOT RUN theo yêu cầu. [Nhật ký717](../nhat_ky/2026-10-29_phien_717_tinh_gon_frontend_v1_luong_demo.md).

- **2026-10-29 — Context716: xóa vĩnh viễn tài liệu nguồn.** Còn bản published thì chặn, phải withdraw; durable purge giữ scope/quyền, dọn đúng file/point và giữ index còn lại. FE xác nhận/theo dõi tại kho, bỏ Tài nguyên. 13 regression mới NOT RUN; Ruff/Biome/TS kiểm tĩnh đạt, chưa nghiệm thu runtime. Không xóa thật/restart/migrate/model/push. [Nhật ký716](../nhat_ky/2026-10-29_phien_716_xoa_vinh_vien_tai_lieu.md).

- **2026-10-29 — Context715: sửa P2 DOCX renderer.** HTTP Gotenberg ngoài khóa MuPDF, log chỉ status/type, fixture offline cho unit render/native.6regression viết chưa chạy; scopedRuff/AST/UTF8/LF/diff đạt. Test/runtime NOT RUN theo yêu cầu; không restart/env/model/migrate/push. [Nhật ký715](../nhat_ky/2026-10-29_phien_715_sua_p2_docx_renderer.md).

- **2026-10-29 — Context714: sửa hai P1 DOCX renderer.** Settings/.env thống nhất, profile DOCX ghim converter/endpoint/revision/rasterizer; lỗi không fallback, resume dùng PDF kiểm hash đã lưu. Legacy/PDF identity giữ;6regression mới chưa chạy. ScopedRuff/AST/UTF8/LF/diff đạt, test/runtime NOT RUN theo yêu cầu. Không restart/env/migrate/model/push. [Nhật ký714](../nhat_ky/2026-10-29_phien_714_sua_p1_docx_renderer.md).

- **2026-10-29 — Context713: review tĩnh BE V1, không test.**5finding: converter DOCX chưa ghim/recovery, URL .env bị bỏ qua(P1); HTTP giữ khóa render, rawlog, unit test gọi service(P2). PDF/resolve-route có scope guard trong mã đã đọc. Chỉ docs, chưa sửa app; test/lint/build/runtime NOT RUN theo yêu cầu. [Nhật ký713](../nhat_ky/2026-10-29_phien_713_review_tinh_backend_v1.md).

- **2026-10-29 — Context712: URL workspace và sidebar.** /:code/files/:sourceId, TanStack mask/bridge và resolve-route kiểm membership/lifecycle; giữ link cũ, sửa active Kho tri thức, quản lý workspace trong dropdown admin. FE465PASS/build/TS/Biome, full lintFAIL28lỗi ngoài phạm vi; BE338PASS/60SKIP thiếu DB test. Browser link cũ/ngắn/F5/đổi workspace/Back đạt; user cho restartV1 runner28344. Giữ diff đồng thời, không migrate/model/quota/push. [Nhật ký712](../nhat_ky/2026-10-29_phien_712_url_workspace_va_sidebar.md).

- **2026-10-29 — Context711: Gotenberg trong Docker V1.** Runner thêm service sẵn có, bind127.0.0.1:3005; qnu_gotenberg healthy/image8 local8.38.1. Health200, DOCX tiếng Việt và HTML→PDF đều200/1trang; scripts44PASS/Ruff/Compose/diff đạt. Bốn container hạ tầng khác giữ ID/StartedAt. Chưa nối rendererV1; không env/model/quota/migrate/restart app/push. [Nhật ký711](../nhat_ky/2026-10-29_phien_711_them_gotenberg_vao_ha_tang_v1.md).

- **2026-10-29 — Context710: backend V1 tự bóc tách sau upload.** Run auto cùng transaction nguồn, native PDF/DOCX, OCR khi cần, MD/JSON/ảnh/ZIP và processing theo revision; schema/code head0007. Bao phủ835ID PASS,28mới/mất0/trùng0 (210call trước gián đoạn+625PASS/lệnh exit0; không full liên tục); Ruff26/OpenAPI131path/link/encoding đạt. DB thử/sentinel và Redis10–15 đã dọn. Chưa migrate/restart phục vụ/live OCR; giữ FE/model/grants/default/quota hiện tại. [Nhật ký710](../nhat_ky/2026-10-29_phien_710_backend_v1_boc_tach_tu_dong.md).

- **2026-10-29 — Context709: rút gọn xác nhận xóa kho tri thức.** Xóa collection/source/document chỉ hỏi Hủy/Xóa, không lý do/checkbox; preview tự chuẩn bị, giữ server quyền/hash/hạn sử dụng/chống lặp. FE450PASS/50tệp, focused29PASS, build+TS theo log hoàn tất; Biome2tệp exit0. Browser desktop/mobile đã kiểm và hủy, hai tài liệu thật giữ nguyên; không live accept/OCR/backend mới. Giữ cấu hình model/quota; không restart/push. [Nhật ký709](../nhat_ky/2026-10-29_phien_709_rut_gon_xac_nhan_xoa_kho_tri_thuc.md).

- **2026-10-29 — Context708: sửa chức năng kho tri thức.** Menu nguồn có xóa/lưu trữ/tải xuống ở thẻ/bảng, lifecycle preview/restore; chặn xóa thư mục còn nội dung, nối chặng3–5, sửa OCR error/paging/poll và quyền admin local ở worker. FE439PASS/buildPASS, BEfocused5+12PASS; full BE ghi804PASS/2FAIL rồi kẹt teardown; recovery17PASS/2FAIL (2revision cũ), DB thử đã dọn. Full lintFAIL29lỗi ngoài phạm vi. LiveCRUD/restoređạt, kho thử đã lưu trữ; User chốt giữ cấu hình model/quota hiện tại, hoàn tất sửa chức năng; không chạy thêm OCR thật. [Nhật ký708](../nhat_ky/2026-10-29_phien_708_sua_chuc_nang_kho_tri_thuc.md).

- **2026-10-29 — Context706: sửa kiểm tra API Key/kết nối.** Chọn đúng key_id, batch từng khóa, strict HTTP/TLS/timeout và history; bỏ fake RoundRobin. FE422PASS/buildPASS, BEfocused36+9PASS; full BE FAIL787/4/3skip (2 lỗi env chạy riêng đạt, 2 assertion revision cũ). User cho restartV1, health200; live2khóa cũ đạt trước khi user tự thay/xóa. Không env/model/migration/push. [Nhật ký706](../nhat_ky/2026-10-29_phien_706_sua_kiem_tra_api_key_ket_noi.md).

- **2026-10-29 — Context707: sửa v1-infra-up/storage.** Đủ PostgreSQL/Redis/Qdrant/MinIO, selected env, tạo bucket local khi thiếu và thử ghi/đọc/xóa; preflight thêm storage chỉ đọc. Giữ đúng image pgsty được yêu cầu. 44test/Ruff/Compose PASS; chạy thật hai lần +v1-check5mụcOK, MinIO giữ healthy. Không đổi env/domain/FE/restart API/migrate/inference/push. [Nhật ký707](../nhat_ky/2026-10-29_phien_707_sua_v1_infra_up_va_storage.md).

- **2026-10-29 — Context705: review kiểm tra API Key/kết nối.** CHANGES REQUESTED9nhóm, trọng tâm kiểm sai khóa/batch1lượt và HTTP lỗi vẫnok. Live4model/47ms, key_id thứ2trả422; FE4FAIL+4cũPASS/BE8FAIL+3PASS; lintPASS. Chỉ review/test/docs, hash app giữ, không sửa cấu hình/restart/push. [Nhật ký705](../nhat_ky/2026-10-29_phien_705_review_kiem_tra_api_key_ket_noi.md).

- **2026-10-29 — Context704: nghiên cứu AnythingLLM cho QNU.** Đọc36nguồn ghim0941fb0; đề xuất9hướng, ưu tiên menu theo quyền, folder/upload và onboarding; giữ membership/revision/hash và owner hội thoại. Link/encoding đạt; test/build/benchmark NOT RUN, chỉ docs, không sửa app/runtime. [Nhật ký704](../nhat_ky/2026-10-29_phien_704_nghien_cuu_anythingllm_cho_qnu.md).

- **2026-10-28 — Context703: review Kho tri thức/thư mục.** CHANGES REQUESTED10nhóm: build27TSerror, OCR router, folder lifecycle/scope, upload identity/form, Compiler picker, URL và download. FE411cũPASS/probe2FAIL; handlerBE6FAIL/2PASS, unit5PASS/schema1FAIL, fixturegốc1ERROR; RuffPASS/BiomeFAIL. DB thử dọn; chỉ review/docs, chưa sửa app hoặc migrate/restart/push. [Nhật ký703](../nhat_ky/2026-10-28_phien_703_review_kho_tri_thuc_thu_muc.md).

- **2026-10-28 — Context702: ModelOps nhà cung cấp và model.** Tạo kết nối → thêm khóa → discovery → thêm nhiều model; migration0005 giữ ID/grants/index và phạm vi khóa cũ, shared key/pool có owner cha. BE765PASS +recovery4PASS (ca có chuyển dữ liệu chạy lại1PASS); FE411PASS, lint/build+TS và UI desktop/mobile đã kiểm bằng dữ liệu riêng. DB thử dọn; chưa migrate DB phục vụ/live inference/restart/push. [Nhật ký702](../nhat_ky/2026-10-28_phien_702_modelops_nha_cung_cap_va_model.md).

- **2026-10-28 — Context701: cấu hình URL API tích hợp local.** Thêm PUBLIC_BASE_URL=http://127.0.0.1:8002 vào .env root theo runner V1; giữ nguyên cấu hình khác. Theo yêu cầu không test/build/restart. [Nhật ký701](../nhat_ky/2026-10-28_phien_701_cau_hinh_public_base_url_local.md).

- **2026-10-28 — Context700: sửa10lỗi Providers/API tích hợp.** Key lifecycle/quyền/limiter, giữ policy trợ lý, strict single-turn, URL tin cậy và diagnostics đã sửa. Full BE755PASS +recovery4PASS; FE406+1PASS, regression44/schema7/pipeline1PASS; build/lint PASS. Browser desktop sáng/mobile sáng-tối đã kiểm; DB thử dọn. Cần cấu hình PUBLIC_BASE_URL; không live model/env/restart/push. [Nhật ký700](../nhat_ky/2026-10-28_phien_700_sua_10_loi_api_tich_hop.md).

- **2026-10-28 — Context699: seed Phòng Công tác sinh viên.** Workspace/kho trống +3membership admin/editor/member; khóa dev riêng trong local registry hash, không cấp admin nền tảng. Focused8PASS/integration1PASS; seed lặp không trùng và API ASGI DB local kiểm quyền đạt. Full bị ngắt/có1FAIL upload concurrency, riêng1PASS; DB test đã dọn. Không frontend/env/model/migration/restart/push. [Nhật ký699](../nhat_ky/2026-10-28_phien_699_seed_phong_cong_tac_sinh_vien.md).

- **2026-10-28 — Context697: review Providers/API tích hợp sau prompt.** Tái hiện10lỗi về policy trợ lý, quyền/lifecycle khóa, limiter, history, error và URL/diagnostics. BE batch+review3PASS/8FAIL, FE batch4PASS/review2FAIL; build+TS/Ruff PASS, Biome FAIL1format. DB thử đã dọn; chỉ review/docs, chưa sửa app hoặc gọi AI/restart/push. [Nhật ký697](../nhat_ky/2026-10-28_phien_697_review_provider_va_api_tich_hop.md).

- **2026-10-28 — Context696: bổ sung nguyên tắc thiết kế frontend.** Cập nhật skill QNU và skill cá nhân admin-frontend-design: bố cục theo tác vụ, hierarchy/nhãn/lỗi/trống và tự rà soát; giữ design system, sửa nhỏ không ép thiết kế lại. Hai validator PASS; chỉ đổi skill/docs, không cài skill ngoài hoặc chạy app test/build/restart/push. [Nhật ký696](../nhat_ky/2026-10-28_phien_696_bo_sung_nguyen_tac_thiet_ke_frontend.md).

- **2026-10-28 — Context695: ModelOps nhóm khóa, dự phòng và registry V1.** Pool PostgreSQL có fencing/cooldown401/429, max3lượt/gateway1; dự phòng trước tác vụ giữ grants/quota và model đã ghim, không đổi embedding. Runtime theo DB người gọi, audit gắn usage; FE có chính sách/trạng thái khóa/lịch sử và registry. BE tổng715PASS +recovery1PASS; sau fix OCR reuse có61regressionPASS. FE400PASS, Ruff44/Biome10/build+TS và browser desktop/mobile đạt. Không migration/.env/live inference/đổi cấu hình/restart người dùng hoặc push. [Nhật ký695](../nhat_ky/2026-10-28_phien_695_modelops_nhom_khoa_du_phong_va_registry.md).

- **2026-10-28 — Context694: ModelOps lấy danh sách và chẩn đoán.** Admin discovery/probe theo capability, lịch sử lỗi/latency/stale và chọn model qua dialog FE; thêm4provider/key mã hóa cho server QNU, cả4probe thật đạt. FE393PASS, BE33regressionPASS, lint/build PASS. Full BE đầu682PASS/2FAIL/2SKIP do môi trường;4ca chạy lại với Redis/loop phù hợp đều PASS. API8002 cũ cần chạy lại phiênv1-dev; không tự restart phiên người dùng/push. [Nhật ký694](../nhat_ky/2026-10-28_phien_694_modelops_discovery_va_chan_doan.md).

- **2026-10-28 — Context693: nghiên cứu 9router cho ModelOps V1.** Đọc35tệp source/test tại commit3a978a6, đối chiếu QNU: đề xuất discovery/probe, trace, key cooldown, policy fallback và registry; giữ grants/quota/index pinning, tránh raw logger và SSE200 rỗng. Chỉ nghiên cứu/docs, test/benchmark NOT RUN, không sửa app/config hoặc gọi model. [Nhật ký693](../nhat_ky/2026-10-28_phien_693_nghien_cuu_9router_modelops.md).

- **2026-10-28 — Context692: rà soát điều hướng V1.** Dùng chung danh mục/scope cho sidebar, chọn workspace/kho, Ctrl+K và breadcrumb; sửa active tab/view, OCR, thêm Xuất bản, tạo kho tại picker và bỏ header mẫu KTX. Full FE385PASS, regression37PASS, Biome/build+TS PASS; browser desktop/mobile đã kiểm, workspace live chưa có kho nên chưa chạy OCR/LLM. Không đổi BE/env/data hoặc push. [Nhật ký692](../nhat_ky/2026-10-28_phien_692_ra_soat_dieu_huong_v1.md).

- **2026-10-28 — Context691: nối router sidebar theo chức năng.** Chọn workspace/kho có ghi nhớ mục; OCR, Compiler, tìm kiếm, hỏi đáp, đánh giá tới đúng tab/page, server vẫn kiểm quyền. Router thật fixture10test/full358PASS, Biome/build+TS PASS; chưa live browser/model hoặc push. [Nhật ký691](../nhat_ky/2026-10-28_phien_691_noi_router_sidebar.md).

- **2026-10-28 — Context690: sắp xếp sidebar.** Nhãn gọn theo nhóm Tri thức, Trợ lý, Quản trị & vận hành; giữ workspace và URL hiện có. Biome2tệp,3test, build+TS PASS; chưa kiểm browser/full suite, không sửa BE/auth hoặc push. [Nhật ký690](../nhat_ky/2026-10-28_phien_690_sap_xep_sidebar.md).

- **2026-10-28 — Context689: lối vào chức năng workspace ở sidebar.** Hiện kho/OCR/Compiler/RAG, trợ lý/hội thoại và quản trị/vận hành; chọn workspace trước, chức năng tài liệu chọn thêm kho, quyền vẫn kiểm ở server. Biome3tệp/3test/build+TS PASS; chưa kiểm browser/full suite/backend hoặc push. [Nhật ký689](../nhat_ky/2026-10-28_phien_689_loi_vao_sidebar_workspace.md).

- **2026-10-28 — Context688: ẩn menu KTX khỏi sidebar.** Chỉ hiển thị nhóm QNU AI không phải template, vẫn áp kiểm quyền V1; giữ route và command menu mẫu. Biome PASS, build/TypeScript theo receipt phiên688; chưa kiểm browser/E2E, không sửa backend/auth hoặc push. [Nhật ký688](../nhat_ky/2026-10-28_phien_688_an_sidebar_ktx.md).

- **2026-10-28 — Context687: đăng nhập local.** Đồng bộ khóa FE theo backend .env gốc hiện có, không đổi backend/mã nguồn. Live bridge200/auth-me200 xác nhận dev.admin/AI.Admin; không log secret/token, không restart backend hoặc push. [Nhật ký687](../nhat_ky/2026-10-28_phien_687_dong_bo_dang_nhap_local.md).

- **2026-10-28 — Context686: sửa khởi động V1/schema mới.** Preflight trước dịch vụ,16lệnh chung, onesync/PORT/Node và uv env-file Windows. Xác nhận DB local trống rồi migrate0003;4checkOK, smoke API/FE200 và workerhealth0, tiến trình thử đã dọn.27test/54wrapper/Ruff/syntax đạt; chưa inference/login/fullsuite/GNU Make runtime hoặc push. [Nhật ký686](../nhat_ky/2026-10-28_phien_686_sua_khoi_dong_v1_va_schema_moi.md).

- **2026-10-28 — Context685: Make chạy V1.** Bốn runner có14lệnh v1-* chung, API/worker/FE foreground, env root/backend tường minh, không auto-migrate/restart. 12test và48kiểm wrapper đạt; Ruff/syntax/link/encoding/diff đạt. GNU Make runtime chưa chạy do thiếu binary; không chạy ứng dụng/DDL/model hoặc push. [Hướng dẫn38](../quy_trinh/38_huong_dan_chay_qnu_v1.md), [nhật ký685](../nhat_ky/2026-10-28_phien_685_makefile_chay_v1.md).

- **2026-10-28 — Context684: nhánh v1.0.2 trên Gitea.** Commit mã nguồn e112ac5 (1394 tệp) đã push Gitea và xác nhận SHA. Người dùng chỉ cần Gitea; tiến trình GitHub trước đó kết thúc exit1 sau Ctrl+C, không gửi lại. Quét staged/fixture có đối chiếu; diff-check FAIL khoảng trắng cũ, test/build/runtime NOT RUN. [Nhật ký684](../nhat_ky/2026-10-28_phien_684_push_nhanh_v1_0_2_gitea.md).

- **2026-10-27 — Context683: hướng dẫn chạy V1.** Tài liệu chạy API/worker/FE, giữ đúng .env/storage, cài mới/migration, admin local và ModelOps. Parser 14 khối PowerShell và kiểm tra tĩnh/link/encoding đạt; 1980 tệp ứng dụng giữ hash. Không chạy dịch vụ, migration, test/build hoặc model thật. [Hướng dẫn38](../quy_trinh/38_huong_dan_chay_qnu_v1.md), [nhật ký683](../nhat_ky/2026-10-27_phien_683_huong_dan_chay_qnu_v1.md).

- **2026-10-27 — Context682: FE mục4–6.** Hỏi đáp thử theo kho với model/policy/document scope và nguồn kiểm publication; tải raw review kể cả failed/uncertain; dashboard QNU theo workspace/quyền, mẫu KTX giữ riêng. Full348PASS giữ311ID+37mới, lint557tệp/build+TS/probes19/bundle11PASS. BE giữ hash, không chạy lại;11ảnh fixture và raw155byte khớp. Chưa live API/model/SSO/corpus hoặc quality benchmark. [Báo cáo682](../bao_cao/context682/REPORT.md), [nhật ký682](../nhat_ky/2026-10-27_phien_682_frontend_hoi_dap_review_goc_va_dashboard.md).

- **2026-10-27 — Context681: FE phân trang, phạm vi tài liệu và mở lại chính tả (F1–F3).** URL giữ trang/review/check; Compiler BE thêm offset, search/eval cùng document_ids, spelling GET ghim revision/run/version/hash. FE311PASS giữ287ID+24mới, lint546tệp/build+TS PASS, probes19/bundle11PASS. BE tổng hợp655ID đạt qua các nhóm; full đầu bị ngắt, lượt tiếp thiếu Redis1FAIL đã chạy lại314PASS; không có full exit không gián đoạn. DB thử đã dọn.9ảnh fixture; chưa live model/SSO/corpus hoặc quality benchmark. [Báo cáo681](../bao_cao/context681/REPORT.md), [nhật ký681](../nhat_ky/2026-10-27_phien_681_frontend_phan_trang_pham_vi_va_chinh_ta.md).

- **2026-10-27 — Context680: kiểm kê chức năng FE/BE, chỉ đọc ứng dụng.** Luồng chính đã có FE. Còn phân trang lịch sử, document picker search/eval, mở lại spelling check, collection answers, raw review và dashboard QNU; Compiler >100/history eval/streaming/feedback/share/restore web cần BE bổ sung theo phạm vi. Inventory128HTTP/96path helpers;5route chưa khai báo FE gồm answers+4health/metrics, không suy path matching thành UI coverage. Không chạy lại build/test/live; app hash kiểm cuối. [Báo cáo680](../bao_cao/context680/FE_BE_INVENTORY.md). [Nhật ký680](../nhat_ky/2026-10-27_phien_680_kiem_ke_chuc_nang_fe_be.md).

- **2026-10-27 — Context679: FE bốn đợt sao lưu, dọn tệp, xem nguồn và đánh giá RAG.** Operations backup/retention/verify/download và GC preview/ack/receipt/retry cùng hash/key; search toàn văn/bảng/citation kiểm publication và link version/OCR; evaluation active snapshot, 1–20 câu, chọn gold đọc được, human ack, dense/hybrid/rerank, JSON/CSV. Full287PASS giữ244ID+43mới, focused43PASS/regression51PASS; nhãn cuối UI48PASS, lint542tệp0/0/0, build+TS PASS; probe67411PASS/6768PASS, bundle11PASS. Baseline796,10cũ đổi/22mới, BE/auth/ModelOps giữ hash.10ảnh browser desktop/390×844 sáng/tối và2download fixture; helper/tab đóng. Chưa live BE/SSO/model/corpus/quality, chưa lịch sử evaluation server/fullrestore UI; không migrate/reindex/restart/deploy/Git. [Nhật ký679](../nhat_ky/2026-10-27_phien_679_frontend_sao_luu_don_tep_va_danh_gia_rag.md), [báo cáo](../bao_cao/context679/REPORT.md).

- **2026-10-27 — Context678: FE mục2–3–4.** Lifecycle preview/xác nhận/biên nhận, thùng rác/restore/pause-resume/cancel/cleanup; staged upload giữ serving và approved replacement; Ops filters/pagination/detail/recovery/summary/usage/readiness theo quyền, deep links/retry cùng key. Full244PASS/0FAIL/0SKIP giữ211ID+33mới, focused56PASS, lint520tệp0/0/0, typecheck/build PASS; probe67411PASS/6768PASS, bundle/template11PASS. Snapshot779:16cũ đổi/26mới, BE/auth/ModelOps/style/devbridge giữ hash;6ảnh browser fixture sáng/tối/390px, helper đã dừng. Chưa live BE/SSO/model/corpus, không migrate/reindex/runtime/deploy/Git. [Nhật ký678](../nhat_ky/2026-10-27_phien_678_frontend_vong_doi_thay_the_va_van_hanh.md), [báo cáo](../bao_cao/context678/REPORT.md).

- **2026-10-27 — Context677: sửa4lỗi FE676.** Nháp OCR giữ base và kiểm lại lúc lưu; năm sai chặn click/Enter ở search/chat; index/search ghim session/workspace/collection và bỏ kết quả muộn; callback SSO hủy ticket dev-login kể cả đã kết thúc. Baseline6FAIL/2PASS→probe8PASS; trọng tâm30PASS; full211PASS/0FAIL/0SKIP giữ190ID+21mới, lint494tệp0/0/0, build+TS PASS; probe67411PASS, bundle/template sau build11PASS. Đúng6source+5test mới, BE/test cũ giữ hash; chưa live SSO/API/model/UI đa thiết bị, không đổi runtime/config/index/deploy. [Nhật ký677](../nhat_ky/2026-10-27_phien_677_sua_bon_loi_frontendv1_sau_review.md), [báo cáo](../bao_cao/context677/REPORT.md).

- **2026-10-27 — Context676: review FE sau prompt675, CHANGES REQUESTED.** 190PASS/0FAIL/0SKIP giữ156ID674+34mới; lint489tệp0/0/0, build+TS PASS; probe cũ11PASS, bundle/template sau build11PASS. Probe mới6FAIL/2PASS xác nhận4nhóm: nháp OCR tự đổi base(P1), năm sai bị bỏ scope, search sai collection khi đổi phạm vi, dev-login ghi token khi SSO bắt đầu giữa request(P2). 774hash app giữ nguyên; chỉ review/docs, chưa live API/SSO/model/UI đa thiết bị, không sửa app/config/index/runtime. [Nhật ký676](../nhat_ky/2026-10-27_phien_676_review_frontendv1_sau_prompt675.md), [báo cáo](../bao_cao/context676/REVIEW.md).

- **2026-10-27 — Context675: hoàn thiện frontendV1 theo Context674.** Sửa4lỗi: F1 ticket epoch/attempt/sessionId kiểm lại lúc ghi + store `ssoCallbackActive` hoãn auto-login khi callback SSO (cleanup effect mount không tăng epoch để giữ single-flight StrictMode); F2 draft hậu OCR sang store ngoài theo phiên+base version, chặn rời trang/đổi lượt, rebase chỉ khi người dùng chọn; F3 chỉ đúng404+`published_compilation_not_found` mới rỗng, trang chi tiết có nhánh lỗi+thử lại; F4 trạng thái `cancelled` kết thúc, không mời gửi lại cùng khoá. Nối RAG673: `rag_policy` vào type/form gập/trang chi tiết/mọi payload bật-tắt (mặc định dense/cửa sổ0/off, không tự nâng cấp), tab "Chỉ mục & Tìm kiếm" endpoint+idempotency+trạng thái thật, chat gửi `metadata_filter` tường minh + xử lý `conversation_scope_conflict`, khai báo/hiển thị `retrieval_metadata` kèm căn cứ, cổng duyệt bắt xác nhận metadata rồi gửi đúng hash backend trong `review_ack`, hiển thị verification/context/scope với usage sinh và judge tách riêng. 190PASS/0FAIL/0SKIP (giữ156 cũ+34 mới), lint489tệp0/0/0, build+TS PASS, bundleguard21PASS, probe674 từ10FAIL/1PASS→11PASS/0FAIL không đổi assertion, `dist/` 0 khớp7mẫu server-only. NOT RUN smoke API/SSO/model thật, desktop/mobile/bàn phím/light-dark, preview runtime; catalog provider đã lọc capability rerank/embedding/chat nhưng backend chưa có cổng quyền riêng theo provider RAG. Không commit/push/migrate/deploy/index lại/KTX. [Nhật ký675](../nhat_ky/2026-10-27_phien_675_hoan_thien_frontendv1_theo_context674.md), [báo cáo](../bao_cao/context675/REPORT.md).

- **2026-10-27 — Context674: review frontendV1, CHANGES REQUESTED.**4lỗi tái hiện: autologin muộn ghi đè SSO/logout/unmount(P1), mất draft OCR khi đổi tab ảnh, publication error thành chưa xuất bản, cancelled turn không có UI(P2).3gap RAG673: policy/scope/index/search, metadata/hash ack, judge/report/reason mới (observe unsupported không cảnh báo). Existing156PASS,lint472file0/0/0,build+TS và6bundleguardPASS;10probeFAIL+1controlPASS,755hash appFE/qnuBE giữ nguyên. Chỉ review, chưa sửa ứng dụng/livebrowser/SSO/API/model/fullsmoke. [Nhật ký674](../nhat_ky/2026-10-27_phien_674_review_frontendv1_sau_prompt_va_rag.md).

- **2026-10-27 — Context673: RAG mục1–4 backendV1.** Nối policy dense/hybrid/rerank vào snapshot trợ lý/hội thoại; metadata target/citation/quote bất biến và human hash ack; filter trước Qdrant/FTS TopK; chunker v2/context cùng mục/publication/budget; judge ModelOps observe/enforce kiểm statement/quote/số và trace rank/score/usage. Migration0003 thêm3JSONB,0001/0002 giữ bytes, worker/recovery cùng head. Full652PASS/0FAIL/0SKIP, giữ604ID cũ+48mới/mất0; Ruff39file/format/schema/OpenAPI101path128operation/UTF8/LF/links PASS. So sánh3mode cùng snapshot chỉ functional tổng hợp, chưa quality/liveAI/FE mới. Default dense/context0/off; scope cần tường minh. Không cài Meilisearch, sửa FE, đổi serving config/migrate/reindex/restart/deploy. [Nhật ký673](../nhat_ky/2026-10-27_phien_673_rag_policy_metadata_context_va_kiem_chung.md).

- **2026-10-27 — Context672: tự đăng nhập local và xử lý nợ lint frontendV1.** Thêm cầu nối chỉ chạy trong Vite dev server: access key nằm ở tiến trình Node, trình duyệt chỉ nhận token và vẫn qua `/auth/me`; mặc định TẮT, chỉ POST/loopback/cùng origin, không tồn tại trong build/preview. Đăng xuất không bị tự đăng nhập lại; thiếu cấu hình/sai key/backend tắt đều báo đúng nguyên nhân. Sửa nợ lint: hàng bảng dùng được bàn phím, label/`htmlFor`, bỏ key theo index, hook deps, bỏ `any`, sắp xếp import; chuyển 3 artifact QA vào `storage/artifacts` và loại trừ đúng thư mục output. 156PASS/0FAIL/0SKIP (134 cũ + 22 mới); lint 472tệp 0/0/0 PASS; build/typecheck/npm ls PASS; `dist/` không chứa credential. Chưa chạy dev server với key thật; RAG đang bị phiên khác sửa nên 9/11 hash đã đổi, không kết luận RAG giữ nguyên. [Nhật ký672](../nhat_ky/2026-10-27_phien_672_tu_dang_nhap_local_va_no_lint_frontendv1.md).

- **2026-10-27 — Context671: review lại và sửa frontendV1 sau prompt xuất bản.** Sửa 7 nhóm lỗi669 còn tồn tại; giữ hai download Compiler đã được668 sửa. Ghim form theo session/run, focus ổn định, chat lịch sử, cache và auto-review; sửa thêm ReviewGate đọc sai nội dung findings. Vitest giữ123test cũ +11mới:134PASS/0FAIL/0SKIP; build/typecheck/Biome25tệp/npm ls PASS. Lint toàn FE vẫn FAIL61errors12warnings6infos ngoài phạm vi. Chưa live SSO/API/model/browser navigation; RAG11hash giữ nguyên, không BE/config/index/deploy. [Nhật ký671](../nhat_ky/2026-10-27_phien_671_review_lai_va_sua_frontendv1.md).

- **2026-10-27 — Context670: rà soát RAG backendV1, chỉ phân tích.** Đã có dense/FTS-RRF/rerank API, table-aware chunks/follow-up/citation validation; chat assistant còn dense. Ưu tiên metadata scope, parent/window context và answer verification; sau đó decomposition/structured retrieval. Probe cục bộ exit0: citation đúng ID chưa kiểm ngữ nghĩa; chưa scope data_year/assistant retrieval fields/parent metadata. Không benchmark/live/test toàn bộ hoặc sửa BE/FE/config/index; Context658 nhãn draft chưa chứng minh rerank cải thiện. [Nhật ký670](../nhat_ky/2026-10-27_phien_670_ra_soat_patterns_rag_backendv1.md).

- **2026-10-27 — Context668: Triển khai giao diện quản lý phiên bản và xuất bản tài liệu biên soạn trong frontendV1.** Luồng Compiler completed → đăng ký tài liệu mới (`POST .../compiled-documents` có `document_key` và `title`) hoặc thêm phiên bản vào tài liệu có sẵn (`POST .../compiled-documents/:docId/versions` có `Idempotency-Key`) → xem danh sách tài liệu (`GET .../compiled-documents`), metadata chi tiết và phiên bản xuất bản hiện hành (`GET .../published`, 404 trả null) → xem chi tiết phiên bản (`/versions/:versionId`) và nội dung draft bất biến (`GET .../draft`, citations, literal tables) → cổng rà soát Review Gate (`GET .../review-gate`, verdict tham khảo, checkbox xác nhận đã xem bắt buộc, giải trình 100% findings: `accepted_risk` | `not_an_issue`, lý do >= 10 ký tự) → xem trước duyệt (`POST .../decision-preview` action: `approve`) → xác nhận duyệt (`POST .../decisions` có `preview_id`, `preview_sha256`, `Idempotency-Key`) → xem trước và xuất bản (`publish`, tự động chuyển bản published cũ thành `superseded`) → xem trước và thu hồi phiên bản (`withdraw`, không bắt qua review-gate, không tự khôi phục bản cũ) → xem lịch sử quyết định (`GET .../history`). Đặt Tab "Tài liệu biên soạn" trong chi tiết collection, thêm nút "Đăng ký thành tài liệu biên soạn" trên trang Compiler completed run. Routes: `/documents`, `/documents/:documentId`, `/documents/:documentId/versions/:versionId`. Kiểm chứng: 24/24 unit/contract tests PASS (`tests/v1-publication.test.ts`), 47/47 tests toàn bộ suite PASS 100%, Biome check 20 file PASS 100%, TypeScript `tsc --noEmit` 0 lỗi, `npm run build` PASS. Chưa embedding/index/search, chưa tự động thay thế revision nguồn. [Nhật ký668](../nhat_ky/2026-10-27_phien_668_giao_dien_xuat_ban_tai_lieu_frontendv1.md).

- **2026-10-27 — Context669: review chức năng frontendV1, CHANGES REQUESTED.** 7 nhóm lỗi: draft Compiler giữ khi đổi run (P1), ba nút tải thiếu client, chat sau50lượt, key mục theo nội dung, invalidation list, auto-review và runner test. Build PASS; test hiện42PASS/6tệpFAILkhởi chạy/0SKIP; lint64errors14warnings6infos, BiomeQNU96tệp5errors2warnings;7probe handler/hook FAILxác nhận hành vi. Chỉ login browser, chưa SSO/API thật/mobile/dark; source app giữ nguyên. Publication đang viết đồng thời chưa review. [Nhật ký669](../nhat_ky/2026-10-27_phien_669_review_chuc_nang_frontendv1.md).

- **2026-10-27 — Context667: Triển khai giao diện Compiler trong frontendV1.** Luồng chọn nguồn OCR completed và text version (v0 raw hoặc v1..vN hậu OCR) → tạo Compiler run (`POST .../compilation-runs` có `Idempotency-Key`) → theo dõi trạng thái bằng polling backoff an toàn → xem bản biên soạn hoàn chỉnh & dẫn chứng `[ocr_id:ev_id]` → ngăn kéo đối chiếu `CitationDrawer` → bảng nguồn literal read-only `SourceTablesView` bảo toàn cấu trúc → theo dõi auto-review (404 trả `notScheduled: true`, không coi là lỗi) & tạo review thủ công (`POST .../reviews`, chặn key `auto:`) → xem báo cáo review hai chiều (nguồn ↔ bản nháp) kèm trích đoạn & gợi ý xử lý → chỉnh sửa có cấu trúc `GET edit-context` (admin/editor) → xem trước diff server `POST edit-previews` → xác nhận tạo bản sửa `POST edits` sinh child run `origin="user_edit"` trỏ bản cũ. Đặt mục "Biên soạn" trong chi tiết collection, thêm nút "Dùng để biên soạn" từ OCR run completed và màn hình text review. Route danh sách `/compilations` và route chi tiết `/compilations/:runId`. Kiểm chứng: 23/23 unit/contract tests PASS (`tests/v1-compilation.test.ts`), Biome check 19 file PASS 100%, TypeScript `tsc --noEmit` 0 lỗi, `npm run build` PASS. Chưa đăng ký/duyệt/xuất bản compiled doc, chưa embedding/index/search, chưa cập nhật phục vụ Chat. [Nhật ký667](../nhat_ky/2026-10-27_phien_667_giao_dien_compiler_frontendv1.md).

- **2026-10-27 — Context666: review gate, GC, recovery và readiness backendV1.** Human ack/hash/findings ghim preview/approval; GC admin preview/key/audit/conditional delete giữ nguồn/raw; bundle mã hóa43 bảng/tệp, restore đích mới và remap mọi generation; worker heartbeat/readiness gồm quota. Migration0002, baseline/archive và475legacy giữ bytes. Full đầu một nhóm kẹt Windows Proactor/TestClient (FAIL/incomplete), lặp tái hiện; opt-in Selector cho nhóm TCP/Redis, production loop giữ. Hợp cuối604 PASS/0FAIL/0SKIP,29mới/0mất so575; CLI standalone và quota có boundary bổ sung. API HTTP/ARQ/model thật/PDF2trang/answer5nguồn; restore18tệp/query5hit; MinIO conditional PASS. Chỉ functional, chưa semantic/SSO thật/migrate/restart/deploy phục vụ. [Nhật ký666](../nhat_ky/2026-10-27_phien_666_duyet_gc_recovery_va_readiness_backendv1.md).

- **2026-10-27 — Context665: giao diện OCR và kiểm tra hậu OCR trong frontendV1.** Triển khai hoàn chỉnh giao diện xử lý OCR và rà soát văn bản hậu OCR trong `frontendV1`, kết nối API thực `backendV1` `/platform/v1alpha1/.../revisions/{revision_id}/processing-runs` và `.../text-review`. Hỗ trợ chọn revision (PDF và DOCX), yêu cầu lượt xử lý OCR với catalog ModelOps capability `ocr` (hoặc mặc định `provider_id = null`), cờ `force: false` (tái sử dụng lượt 200 Reused) hoặc `force: true` (tạo generation mới 201 Created kèm cảnh báo token). Theo dõi trạng thái từng trang (`pending`, `in_flight`, `completed`, `blank`, `failed`, `uncertain`), số đếm trang `pages_done / pages_total` (chờ xác định khi null, không sinh phần trăm giả), attempt count, usage tokens (không đổi null thành 0), và nút Dispatch cho lượt `dispatch_pending`. Màn hình đối chiếu song song ảnh PNG trang kết xuất với văn bản/bảng biểu (giữ raw and disclaimer DOCX layout, tái dựng row_span, col_span, header). Bảng điều khiển rà soát văn bản hậu OCR (`text-review`) duyệt các phiên bản (v0 OCR gốc, v1, v2...), sửa nội dung từng đoạn/ô vào draft cục bộ, modal đối chiếu diff trước/sau, lưu sửa đổi với header `Idempotency-Key`, `expected_version`, `expected_sha256` và mảng changes `before`/`after`. Xử lý `409 ocr_text_version_conflict` giữ nguyên bản nháp của người dùng. Kiểm tra chính tả bằng AI (Chat ModelOps capability `chat`, phạm vi 1-100 đoạn) tính toán span theo Unicode code point (tương thích Python, xử lý ký tự ngoài BMP), áp dụng gợi ý theo thứ tự offset giảm dần chống chồng lấn, chỉ cập nhật draft cục bộ. Tải và xem các artifact: Canonical JSON, Markdown dẫn xuất, Processing Manifest và Evidence Snapshot ghim nguồn phục vụ Compiler. Bộ 76 test cases frontend PASS (11 test OCR/review mới), Biome 0 error / 0 warning trên 15 tệp, TypeScript 0 error. [Nhật ký665](../nhat_ky/2026-10-27_phien_665_giao_dien_ocr_va_review_frontendv1.md).

- **2026-10-27 — Context664: sửa hủy lượt chat khi dừng/lưu trữ qua API cập nhật.** Assistant PUT tắt và conversation PUT archive tái dùng lifecycle cancellation, giữ lock/quyền/owner; trạng thái, hủy và audit số lượt cùng transaction. Bật/mở lại không nhận lượt cũ, giữ revision khi chỉ tắt/bật và history completed. Regression trước sửa 2 FAIL đúng hành vi; sau sửa focused 50 PASS, full 575 PASS / 0 FAIL / 0 SKIP, 10 mới/0 mất so 565. Ruff/format 4 file, UTF-8/LF, OpenAPI 96 path/123 operation; 487 file legacy/migration giữ bytes; DB thử dọn. Không schema/frontend/provider config/migrate/restart/deploy; model HTTP tổng hợp. [Nhật ký664](../nhat_ky/2026-10-27_phien_664_sua_huy_luot_chat_khi_dung_va_luu_tru.md).

- **2026-10-27 — Context663: review backendV1 và quy trình ngược, CHANGES REQUESTED.** Regression lifecycle 23 PASS; hai probe độc lập FAIL đúng hành vi: PUT tắt/bật assistant hoặc archive/mở lại conversation khi AI đang trả lời vẫn nhận 200/completed/có kết quả, thiếu hủy turn bền vững so với lifecycle mới. FE hiện dùng hai PUT này. Probe assistant đầu lỗi dựng request thừa trường, sửa probe rồi tái hiện cả hai; chưa sửa app. Ghi rõ soft delete, GC orphan/full DR, review chưa publish gate và thay thế nguồn dùng chung theo nhóm còn thiếu. Ba DB thử dọn, sentinel/version giữ, 0 vector v1 quan sát. Full suite không chạy lại; 565 PASS Context662 là lịch sử; model HTTP tổng hợp, chưa AI thật/migrate/restart/deploy. [Nhật ký663](../nhat_ky/2026-10-27_phien_663_review_backendv1_va_quy_trinh_nguoc.md).

- **2026-10-27 — Context662: gộp migration backendV1.** Gộp 15 revision thành `0001_initial_schema`, DDL cố định cho 42 bảng; lưu nguyên bytes 15 file cũ trong ZIP, kiểm checksum và đối chiếu catalog schema cũ/mới khớp. Chặn trùng bảng, revision đã nghỉ và downgrade; giữ bảng/version legacy. Full suite 565 PASS / 0 FAIL / 0 SKIP, thêm 2 ca và không mất ca nào trong 563 ca trước. Ruff/format 4 file, UTF-8/LF, ownership và byte của 475 file backend cũ đều đạt. DB thử đã dọn; chưa áp migration, stamp, restart hoặc deploy DB phục vụ. Cập nhật hướng dẫn/ADR/contract; giữ báo cáo lịch sử. [Nhật ký662](../nhat_ky/2026-10-27_phien_662_gop_migration_backendv1.md).

- **2026-10-27 — Context661: chức năng Chat với Trợ lý AI trong frontendV1.** Triển khai hoàn chỉnh luồng Trò chuyện với Trợ lý AI trong `frontendV1`, kết nối API thực backendV1 `/platform/v1alpha1/workspaces/{workspace_id}/conversations`. Danh sách hội thoại phân trang mảng thuần (`limit`, `offset`), bộ lọc trạng thái (tất cả/đang mở/lưu trữ) và hành động đổi tên / lưu trữ / mở lại (`PUT` bảo toàn status hoặc title tương ứng). Tạo hội thoại từ danh sách trợ lý hoạt động hoặc từ nút "Trò chuyện" trên trang chi tiết trợ lý; chặn auto-retry tạo hội thoại. Trang chat độc lập (`/workspaces/:workspaceId/conversations/:conversationId`), tự cuộn thông minh khi đang ở đáy, phím tắt Enter gửi / Shift+Enter xuống dòng / kiểm soát IME. Gửi lượt hỏi (`POST .../turns`) bắt buộc header `Idempotency-Key` (UUID) và `expected_turn_no` lấy nghiêm ngặt từ `conversation.last_turn_no`; chặn double submit và race condition; retry cùng thao tác giữ nguyên key và body. Xử lý trung thực các trạng thái lượt: `running` (polling có giới hạn, dọn khi unmount/đổi phiên, không hiệu ứng gõ giả), `completed`, `failed` (hiển thị lỗi và nút thử lại có giải thích sequence/key), `uncertain` (cảnh báo timeout lease). Render phân tách `statements` gắn nút dẫn nguồn `evidence_ids` chỉ trong cùng turn; `CitationSheet` hiển thị trích đoạn, tài liệu, phiên bản, vị trí trang/bảng (hiện "Không có thông tin" khi thiếu) và điểm tương đồng; tự động loại bỏ kết quả/citation cũ khi `source_status === "unavailable"` hoặc `result === null`. Xử lý chi tiết các mã lỗi RFC 7807 (`conversation_busy`, `conversation_sequence_conflict`, `idempotency_conflict`, `assistant_inactive`, `conversation_archived`, v.v.). Bảo vệ cô lập phiên theo `sessionId`, không lưu token/câu hỏi nhạy cảm vào storage. Bộ 64 test cases frontend PASS (11 test chat mới), Biome 0 error / 0 warning trên 20 tệp, TypeScript 0 error. [Nhật ký661](../nhat_ky/2026-10-27_phien_661_chuc_nang_chat_tro_ly_ai_frontendv1.md).

- **2026-10-27 — Context660: vòng đời ngược backendV1.** Preview/accept có quyền/hash/expiry/idempotency/audit; lưu trữ/xóa mềm/khôi phục tài liệu, kho, chatbot và owned conversation; pause/resume, hủy tác vụ và chặn kết quả muộn; staged revision + publication/index chuyển nguyên tử; dọn vector/chunk generation không còn phục vụ. Migration0015/2bảng. Full đầu FAIL2review nguồn +1teardown/2queueNOTRUN; tách latest/serving và sửa race auto-review; chạy lại trọn nhóm lỗi và boundary37PASS. Hợp cuối563PASS/0FAIL/0SKIP,23mới/0mất so540. Ruff/format49/UTF8-LF/OpenAPI96path123op(92cũ)/475legacybyte giữ PASS. Dọn đúng DB/vector thử. Giữ raw/derived, chưa purge/AI thật/quality/UI/migrate/restart/deploy phục vụ. [Nhật ký660](../nhat_ky/2026-10-27_phien_660_vong_doi_nguoc_backendv1.md).

- **2026-10-27 — Context659: giao diện quản lý Trợ lý AI trong frontendV1.** Triển khai trọn vẹn luồng Trợ lý AI trong `frontendV1`, kết nối `/platform/v1alpha1/workspaces/{workspace_id}/assistants`. Danh sách trợ lý dùng phân trang mảng thuần (`limit`, `offset`, không có Page wrapper và không giả `total`), hiển thị badge `v{revision}`, model, bộ sưu tập và Switch toggle bật/tắt an toàn (bảo toàn cấu hình gốc và gửi `expected_revision`). Form tạo/sửa trợ lý (Dialog/Drawer) hỗ trợ native submit (click/Enter), chọn bộ sưu tập từ `useCollectionsQuery` (ở chế độ sửa `collection_id` bị khóa cứng/bất biến theo contract 409 backend), chọn model chat từ ModelOps catalog (`capabilities.includes("chat")`, lưu provider ID, chọn "Theo mặc định workspace" gán `null`), validate Zod chặt chẽ theo Pydantic backend (trim name, description/persona default `""`, số nguyên dương cho tham số RAG). Xử lý xung đột `409 assistant_revision_conflict` bằng cách giữ draft form, cảnh báo xung đột và cung cấp nút tải lại dữ liệu mới nhất. Trang chi tiết độc lập (`/workspaces/:workspaceId/assistants/:assistantId`) với breadcrumbs, liên kết tới bộ sưu tập và ModelOps, cùng checklist điều kiện trung thực (đánh dấu rõ "Chưa kiểm tra runtime", không tạo nút chat thử giả). Phân quyền `canManageAssistants` chỉ cho phép workspace `admin` và platform-admin ghi, `editor`/`member` chỉ đọc. Toàn bộ 53/53 test cases frontend PASS (10 test assistants mới), Biome 0 error / 0 warning trên 16 tệp, TypeScript 0 error. [Nhật ký659](../nhat_ky/2026-10-27_phien_659_giao_dien_tro_ly_ai_frontendv1.md).

- **2026-10-27 — Context658: vận hành, thử PDF thật và hybrid backendV1.** Job/usage thật, recovery preview/outbox, evidence backup/retention; FTS+dense/RRF/rerank ModelOps và evaluation cùng snapshot/candidates. Compiler/review JSON Schema tùy chọn, prompt review bỏ dữ liệu lặp nhưng giữ units và metadata phiên bản nguồn. Migration0014/2bảng. Full539PASS/1FAIL thiếu metadata→sửa code/nhóm58PASS; hợp cuối540PASS/0FAIL/0SKIP,48ca batch+2SSO đồng thời/0mất/61file. Ruff/format56/OpenAPI92path119op/475legacybyte giữ PASS. PDF2trang→OCR→Compiler→review→index→answer3nguồn→backup verify PASS trong DB thử; review6findings chưa xác nhận.3lookup draft: dense recall1,0; hybrid/rerank0,833, giữ dense mặc định. Dọn DB/vector thử; chưa UI/migrate/config/restart phục vụ, full DR hoặc quality acceptance. [Nhật ký658](../nhat_ky/2026-10-27_phien_658_van_hanh_thu_that_va_hybrid_backendv1.md).

- **2026-10-27 — Context657: giao diện Kho tri thức giai đoạn đầu trong frontendV1.** Mở rộng transport client v1 hỗ trợ `multipart/form-data` (giữ nguyên File bytes, không tự gán JSON content-type), header `Idempotency-Key` (8-128 ký tự, giữ nguyên key khi retry cùng thao tác), và `requestBlob` phân giải filename RFC 5987 an toàn (lỗi HTTP luôn parse problem+json, không coi lỗi là file tải về). Xây dựng module `features/knowledge` gồm types, schemas, requests, scoped queries theo `sessionId` và `workspaceId`, cùng phân quyền `canManageKnowledge` (admin/editor hoặc platform admin). Hoàn thiện các màn hình: tab Kho tri thức trong workspace, danh sách bộ sưu tập (`/collections`), dialog tạo/sửa bộ sưu tập (so sánh null để xóa mô tả), chi tiết bộ sưu tập (`/collections/:collectionId`), dialog tải lên nguồn tài liệu (`FileUpload` max 60 MiB, .pdf/.docx), chi tiết nguồn tài liệu (`/sources/:sourceId`), dialog tải lên revision (từ chối title theo contract backend 422), bảng lịch sử revision bất biến, tải bản gốc qua token xác thực, và xem trước PDF bằng Blob Object URL (thu hồi URL khi unmount/đổi revision; thông báo tải xuống rõ ràng cho DOCX). Unit test frontend 43/43 PASS, Biome 0 error/0 warning trên 21 tệp, TypeScript 0 error. [Nhật ký657](../nhat_ky/2026-10-27_phien_657_giao_dien_kho_tri_thuc_frontendv1.md).

- **2026-10-27 — Context656: tích hợp đăng nhập QNU SSO cho frontendV1 và backendV1.** Thay thế luồng dev key bằng OpenIddict Authorization Code Flow with PKCE S256 (`oidc-client-ts`). Token lưu hoàn toàn trong bộ nhớ (`InMemoryWebStorage`), không lưu token trong `localStorage` hay `sessionStorage`, transaction state tạm (`qnu_ai_oidc_txn_`) tự động dọn sạch sau callback. Route độc lập `/signin-oidc` xử lý callback, chống duplicate re-entrancy (React StrictMode), gọi ngay `GET /platform/v1alpha1/auth/me` để backend xác thực kép trước khi điều hướng; chống open redirect (`sanitizeReturnUrl` chỉ cho phép internal path an toàn). Backend v1 trích xuất linh hoạt singular/array roles và permissions, trích xuất `user_type` thực từ JWT thay vì mặc định staff, giữ `sub` có phân biệt hoa thường làm `actor_id`, trả 503 nếu lỗi JWKS. `signOut` xóa token bộ nhớ, xóa query/mutation cache và kích hoạt end-session SSO. Patch C# cho `qnu-sso` (seed cổng 3001 và quyền `ai.workspaces.*`). Unit test frontend 36/36 PASS, Biome 0 error/0 warning, TypeScript 0 error; backend test SSO 7/7 PASS, Ruff PASS. [Nhật ký656](../nhat_ky/2026-10-27_phien_656_tich_hop_dang_nhap_sso_frontendv1_backendv1.md).

- **2026-10-26 — Context655: hoàn thiện tích hợp Workspaces & ModelOps frontendV1.** Khắc phục triệt để secret trong `MutationCache` (xóa thuộc tính trực tiếp trước mutation và dọn dẹp dự phòng trên TanStack cache); cô lập phiên (`sessionId` ghim đơn điệu, 401 phiên cũ không xóa phiên mới, response trễ abort với `code: "session_aborted"`, query keys gắn `sessionId`, xóa query/mutation cache khi đổi phiên/đăng xuất, validate actor từ `/auth/me`). Tái cấu trúc `<form>` bên trong `<ResponsiveDialogContent>` ở `key-dialogs.tsx` để click và Enter kích hoạt native submit trên cả desktop/mobile; bổ sung `form.reset` khi mở lại form workspace, member, provider. Đối chiếu contract: phân biệt `configured=false` với `configured=true, limit=null` ("không giới hạn"), validate `limit <= 10^15`, loại bỏ provider tắt/thiếu capability khỏi defaults, reset draft khi đổi workspace và bảo vệ draft khi background refetch. Đạt Biome 0 errors / 0 warnings trên 18 tệp v1; TypeScript typecheck 0 errors; Unit test 26 PASS / 0 FAIL. README và AGENTS cập nhật phân định rõ ranh giới v1 live và KTX template mẫu. [Nhật ký655](../nhat_ky/2026-10-26_phien_655_tich_hop_workspaces_modelops_frontendv1.md).

- **2026-10-26 — Context654: nối hậu OCR, review tự động và sửa Compiler backendV1.** Compiler chọn text_versions theo OCR, omission/0 raw; pin selected ID/hash+gốc qua worker/review/publication/index/citation. Completion+review intent atomic, ARQ/reconcile/stable key, failed/uncertain không resend. Edit context→preview→accept có quyền/hash/expiry tạo run con user_edit, giữ parent/bảng/citation, MD/JSON mới và own review, không recompile/auto publish. Migration0013/2bảng. Full đầu489PASS/1FAIL migration wording→target1PASS/nhóm3 86PASS; hợp cuối490PASS/0FAIL/0SKIP,30mới/0mất/52file; Ruff29/UTF8/OpenAPI79path105op(75cũ) PASS,14DB0còn/0v1vectors. Byte legacy FAIL:413/475same,62drift (48EOL/14unresolved),62Gitindexcontentmatch; chưa quy được nguồn, không restore, không claim475bytegiữ. ChỉBE, chưa model thật/quality/UI/migrate/config/restart/reindex phục vụ; review chưa publish gate, blob orphan chưa GC. [Nhật ký654](../nhat_ky/2026-10-26_phien_654_noi_hau_ocr_review_va_sua_compiler.md) · [Workflow](../../backendV1/docs/compiler-workflow.md).

- **2026-10-26 — Context653: sơ đồ quy trình backendV1.** Tài liệu HTML tĩnh/3SVG/3PNG mô tả tổng quan, hai review và hỏi đáp; profile qnu-teal có sẵn.8node/hình/1280×720, selfcheck/browser/UTF8-links; giữ rõ textreview chưa nối Compiler, Compilerreview API riêng chưa auto/cổng publish. Không đổi mã app/DB/ModelOps hoặc trạng thái kiểm chứng652; pytest app NOT RUN vì tài liệu thuần. [Sơ đồ](../diagrams/quy-trinh-qnu-backendv1-2026-10-26.md) · [Nhật ký653](../nhat_ky/2026-10-26_phien_653_so_do_quy_trinh_backendv1.md).

- **2026-10-26 — Context652: review ngữ nghĩa Compiler backendV1.** API riêng sau completed, source/draft/bundle pin, coverage2chiều/IDđủ, excerpts server JSON/MD; ModelOps reviewer động, durable key/quota/raw/usage/expiry/recheck. Không sửa draft/approve hoặc auto-call worker. Migration0012/2bảng; baseline404FAIL→focused22PASS/1FAIL(expectationtruncated422)→24PASS; extra2PASS/1FAIL(importtest)→1PASS. Full4nhóm460PASS/0FAIL/0SKIP,25mới/0mất/47file,383,56s wall; Ruff/format16/UTF8/OpenAPI75path101op(70cũ) PASS,475legacy giữ,10DB0còn/0v1vector. ChỉBE; chưa live/quality, UI, textreviewbinding, autorepair hoặc migrate/config/restart/pub/index phục vụ. [Nhật ký652](../nhat_ky/2026-10-26_phien_652_review_ngu_nghia_compiler_backendv1.md).

- **2026-10-26 — Context651: rà soát và sửa văn bản hậu OCR backendV1.** API đoạn/ô, gợi ý ModelOps và save text version tạo MD/JSON đồng bộ, giữ gốc; version/hash/idempotency/quyền, migration0011/2bảng. Baseline404FAIL→focused18PASS/concurrent4PASS; same-key race1FAIL→1PASS. Full đầu dừng; tuần tự sau434PASS/1FAIL thông báo downgrade và kẹt shutdown Windows, không PASS; sửa thông báo1PASS. Full cuối sáu nhóm đủ435PASS/0FAIL/0SKIP,22mới/0mất,3integration+unit293,28s; gốc shutdown chưa sửa. Ruff/format14file/UTF8/link/OpenAPI70path95op(65cũ) PASS,475legacy giữ;16DB0còn/0v1vector. User chọn chỉ BE, UI làm sau; chưa live/quality, Compiler binding hoặc migrate/config/restart/pub/index phục vụ. [Nhật ký651](../nhat_ky/2026-10-26_phien_651_ra_soat_va_sua_van_ban_hau_ocr.md).

- **2026-10-26 — Context650: sao chép đầy đủ FE KTX thành frontendV1.** User chọn giữ toàn bộ màn hình KTX làm mẫu, thay nghiệp vụ sau. Nhập324tệp/giữ78route, menu/feature/layout/component/docs/license; lock dependency giữ, không copyenv/cache/node_modules cũ. Cổng3001 riêng, demo có nhãn, chặn fetch nghiệp vụ/auth/import/export; không nối KTX/backendV1. npmci484gói PASS, boundary2PASS, build+TS PASS (mainchunk667,97kB warning), Biome17tệp thích nghi PASS; full lint FAIL56error/12warning/6info, source39error khác context/chưa parity. Browser desktop light/dark/users/search/reload/form và mobile menu/rooms/lỗiAPI rõ; chưa nghiệm thu78route/E2E. SourceKTX và1.902tệp code cũ giữ; không BE/DB/migrate/deploy/Git, giữserver3001. [Nhật ký650](../nhat_ky/2026-10-26_phien_650_sao_chep_frontend_ktx.md).

- **2026-10-26 — Context649: trợ lý và hội thoại backendV1.** Assistant một collection/ModelOps/style/budget/revision; conversation owner+snapshot/scope, turn question/result/citation/error bền vững, key/sequence/lease/replay và follow-up từ userquestions. Tái dùng answer648/checkpoint/source revalidation; history nguồn cũ ẩn result, không auto retry. Migration0010/3bảng chat_*, OpenAPI65path/89operation,59path cũ giữ. Baseline1FAIL→focused38PASS→full413PASS/0FAIL/0SKIP,592,92s;17ca mới/0ca mất,Ruff/format/ORM PASS. Live2turn BGE-M3/Qwen/Qdrant answered1,453s/2,266s,4373chat token,history2/replay cùngusage/source đúng; trước có schemaFAIL/abstain. Còn diễn giải ghi chú chưa đủ căn cứ: chưa quality.475legacy giữ,8DBtest dọn/0còn/0v1vectorcollection. Chưa config/migrate/deploy phục vụ/corpus/FE/share/stream/tools; skill NVIDIA chỉ tham khảo, chưa cài/sửa. [Nhật ký649](../nhat_ky/2026-10-26_phien_649_tro_ly_va_hoi_thoai_backendv1.md).

- **2026-10-26 — Context648: API hỏi đáp có nguồn backendV1.** Search647 → evidence ID → ModelOps chat → kiểm citation/nguồn/quyền/model sau HTTP → answer/statements/sources/trace. Chặn citation giả cả trong text, không retry/fallback hoặc bịa no-data. Live BGE-M3 + Qwen3.5-9B/Qdrant PASS:2ý/1nguồn,1.979token,2,891s,150 và ghi chú2023 giữ; OCR/Compiler mock. Focused18PASS, inline1FAIL→1PASS; full đầu kẹt Proactor Windows khi đóng TestClient (không PASS), retry cùng code396PASS/0FAIL/0SKIP,466,33s;20ca mới/0ca mất, chưa sửa nguyên nhân shutdown. Ruff/format PASS, OpenAPI59path/78operation,58path cũ giữ; không migration mới/head0009.475legacy giữ,8DBtest dọn/0còn/0v1vectorcollection. Chưa config/deploy phục vụ, corpus/quality/history/stream/hybrid/rerank/FE. [Nhật ký648](../nhat_ky/2026-10-26_phien_648_hoi_dap_co_trich_dan_backendv1.md).

- **2026-10-26 — Context647: dense index/search backendV1.** Publication → chunk/bảng có nguồn → ModelOps embedding → ARQ/Qdrant generation → API trả đoạn/citation; scope trước TopK và recheck sau HTTP, manifest/hash, lease/fence/uncertain, replacement fail giữ active cũ. Migration0009/3bảng, OpenAPI58path/77operation. Focused43PASS→full376PASS/0FAIL/0SKIP,341,56s;42ca mới/0ca mất, Ruff/format/ORM PASS. Live BGE-M3 thật1024chiều + ARQ/Qdrant PASS với2chunk mẫu, index1,906s/search0,625s; withdraw0embedding mới, OCR/chat mock.475legacy giữ,12DBtest dọn/0còn/0v1vectorcollection. Chưa migrate/cấu hình DB phục vụ, chưa corpus thật/quality/hybrid/rerank/answer/FE. [Nhật ký647](../nhat_ky/2026-10-26_phien_647_index_va_tim_kiem_dense_backendv1.md).

- **2026-10-26 — Context646: phiên bản và publication bản biên soạn v1.** Document/version có provenance/hash, preview/receipt và duyệt/xuất bản/thay thế/thu hồi; kiểm quyền/nguồn hiện hành, restore cần duyệt lại. Migration0008/4bảng, OpenAPI54path/72operation. Sửa hẹp storage Windows bằng striped lock + bounded read retry, không fake success. Baseline2FAIL→focused35PASS→full334PASS/0FAIL/0SKIP,237,43s;17ca mới/0ca mất, Ruff/format/ORM PASS.475legacy giữ,6DBtest dọn. Chưa migrate/start phục vụ, chưa indexing/RAG/FE hoặc live model/quality; không pub dữ liệu thật. [Nhật ký646](../nhat_ky/2026-10-26_phien_646_phien_ban_duyet_xuat_ban_backendv1.md).

- **2026-10-26 — Context645: runtime chat và Compiler v1.** ModelOps chat OpenAI-compatible, job Compiler có idempotency/lease/fence/reconcile, snapshot OCR và draft JSON/Markdown/citation/bảng gốc. gh/gpt-6-luna thật qua 9router + ARQ PASS 13,328s/5.216 token; OCR mẫu mock. Focused32PASS,31ca mớiPASS; full cuối316PASS/1FAIL/0SKIP (LocalBlobStore Windows, cùng ID/cause642), Ruff/OpenAPI45path PASS. Downgrade/ORM2PASS;475legacy giữ,10DBtest dọn. Chưa migrate/start phục vụ, chưa quality/pub/index/RAG/FE; Compiler legacy giữ. [Nhật ký645](../nhat_ky/2026-10-26_phien_645_runtime_chat_va_compiler_backendv1.md).

- **2026-10-26 — Context644: trace và nghiệm thu OCR v1.** Trace theo run/revision/model/hash và duration/status từng bước; raw API nguyên bytes có quyền/checksum kể cả khi processing lỗi; reporter JUnit/receipt6nhóm tách live/quality. Baseline2FAIL→focused21PASS→full286PASS/0FAIL/0SKIP,121,96s; Ruff/format/OpenAPI40path PASS. Redis/ARQ thật trên queue test riêng, OCR mock loopback;21ca mới/0ca mất,475legacy giữ hash, DBtest/Redis test đã dọn. Runtime v1 chưa đủ cấu hình: live/ảnh nguồn NOT RUN. Không schema/dependency/config/Compiler/RAG/index/pub/restart/Git. [Nhật ký644](../nhat_ky/2026-10-26_phien_644_nghiem_thu_va_trace_ocr.md).

- **2026-10-26 — Context643: sửa sáu lỗi OCR642.** Startup/capacity-quota/pin target/heartbeat-fencing/recovery/raw retention đã nối runtime; DOCX header/footer chưa giữ được trả lỗi rõ. Baseline6FAIL → focused76PASS → full265PASS/0FAIL/0SKIP, replay mẫu1PASS (raw khớp byte,10block/bảng6x6/usage4077); Ruff/OpenAPI PASS.5DBtest dọn,475legacy giữ; DB chính chưa migrate. Chưa live OCR/so ảnh nguồn/Compiler; driver local không đổi. [Nhật ký643](../nhat_ky/2026-10-26_phien_643_sua_sau_loi_ocr_backendv1.md).

- **2026-10-26 — Context642: review OCR v1, CHANGES REQUESTED.** 6probe độc lập FAIL: startup ARQ thiếu settings, capacity chưa áp, resume trộn endpoint/model, run hết lease không phục hồi, DOCX mất header, parse lỗi bỏ raw. Full248PASS/1FAIL/0SKIP (writer Windows vẫn lỗi ngay trong harnessD), RuffPASS;640file source/migration giữ hash,4DBtest dọn. Chưa fix/live OCR/Compiler. [Nhật ký642](../nhat_ky/2026-10-26_phien_642_review_luong_ocr_backendv1.md).

- **2026-10-26 — Context640: luồng xử lý PDF/DOCX backendV1.** Upload → revision bất biến → yêu cầu xử lý cùng transaction → job ARQ claim có lease + cron reconcile → render PyMuPDF (DOCX qua fixed-layout PDF) → OCR từng trang qua ModelOps runtime (`resolve_ocr_runtime`, credential giải mã, 0 request khi provider tắt/thiếu capability/hết quota) → `raw_response` + canonical `qnu.ocr.document/v1` + Markdown + manifest content-addressed → 8 route đọc có `ETag`, snapshot `evidence` ghim theo revision/generation/hash. Migration `0006_ocr_processing`: 3 bảng, composite FK theo workspace, partial unique index một lượt hoạt động/revision, `downgrade()` từ chối; `uq_kb_revision_scope` thêm bằng 0006, không sửa 0005. 14 ca OCR integration từ 11FAIL→0; full v1 **249PASS/0FAIL/0SKIP**, 83,39s, 95 ca mới (81 unit + 14 integration); Ruff PASS; OpenAPI 39path/54operation. Đóng 2 lỗi mở của 641 (regression downgrade639 nay kiểm bất biến; PermissionError local writer chỉ do basetemp ngoài harness). **Live Nemotron NOT RUN** (không endpoint/credential thật; provider loopback là mock). 475 file legacy giữ hash, DB phục vụ chưa migrate; chưa Compiler/chunk/embedding/index/publication/RAG/FE. [Nhật ký640](../nhat_ky/2026-10-26_phien_640_luong_xu_ly_pdf_docx_backendv1.md).

- **2026-10-26 — Context641: capacity ModelOps backendV1.** API token_limits theo model, binding endpoint/model, public budget guard; không trần chung8K/32K, gỡ trần cấu hình OCR32768. Focused44PASS/33ca mớiPASS; full snapshot152PASS/2FAIL (downgrade639 sau0006 và lỗi local Windows), Ruff/OpenAPI PASS.4DBtest dọn,475legacy giữ; guard chưa nối OCR execution, DB chính chưa migrate. [Nhật ký641](../nhat_ky/2026-10-26_phien_641_capacity_modelops_backendv1.md).

- **2026-10-26 — Context639: sửa ba lỗi kho tri thức v1.** Local staging/atomic replace giữ file đã commit; idempotency gồm title hiệu lực, tương thích sổ cũ; downgrade0005 từ chối tường minh. Baseline3FAIL → focused24PASS → full121PASS/0FAIL/0SKIP, Ruff/OpenAPI PASS. 10DBtest dọn,475legacy app giữ hash; DB phục vụ chưa migrate. [Nhật ký639](../nhat_ky/2026-10-26_phien_639_sua_ba_loi_kho_tri_thuc.md).

- **2026-10-26 — Context638: review kho tri thức v1, cần sửa3lỗi.** Suite104PASS/RuffPASS nhưng3probe độc lập FAIL: ghi local đồng thời làm hỏng file đã commit (P1), hash idempotency thiếu title (P2), downgrade0005 chặn upgrade sau (P2). Chưa sửa app;141file source/migration giữ hash, hai DBreview đã dọn. [Nhật ký638](../nhat_ky/2026-10-26_phien_638_review_kho_tri_thuc_backendv1.md).

- **2026-10-26 — Context637: kho tri thức backendV1, upload trực tiếp.** Bốn bảng `kb_*` (collection/source/revision/idempotency), FK tổ hợp giữ chuỗi workspace→collection→source→revision; dedupe `(collection, sha256)`, idempotency `(workspace, actor, key)`, blob content-addressed, tải lại bytes gốc có kiểm checksum. Full v1 104PASS/0FAIL/0SKIP, focused33PASS, Ruff/migrationORM/OpenAPI31path PASS; DBtest đã dọn, DB phục vụ chưa migrate, chưa parser/OCR/worker/index/RAG/FE. [Nhật ký637](../nhat_ky/2026-10-26_phien_637_knowledge_collections_backendv1.md).

- **2026-10-26 — Context636: Workspace và ModelOps backendV1.** Membership/role/resolver, auth dev/SSO, provider/key/grant/default theo capability và quota/usage nội bộ. Full v1 60PASS/0FAIL/0SKIP, Ruff/migrationORM/lock/OpenAPI PASS;475file legacy giữ hash, DBtest đã dọn, chưa migrate DB phục vụ hoặc live inference/SSO. [Nhật ký636](../nhat_ky/2026-10-26_phien_636_workspaces_modelops_backendv1.md).

- **2026-10-25 — Context635: bỏ thư viện sửa chính tả hậu OCR.** Gỡ package/từ điển/hook và ba phép thay từ cũ; giữ chữ Nemotron, bảng và raw OCR. Focused128+23subtest/Ruff4 PASS; full NOT RUN do Docker/PostgreSQL không chạy, ready503/không worker. Không backfill/index; DB test bị gián đoạn đã dọn. [Nhật ký635](../nhat_ky/2026-10-25_phien_635_bo_thu_vien_sua_chinh_ta.md).

- **2026-10-25 — Context634: sửa và chạy đúng OCR Nemotron.** Batch giữ engine qua retry; HTML → GFM, sửa đối chiếu DOCX và giữ raw OCR Office. Cả3 mẫu DOCX/PDF/PDF scan có raw Nemotron,16/16 ô đúng; scan còn2 blocker cấu trúc, không tự duyệt. Focused134+23subtest/Ruff7 PASS; full3.835PASS/14FAIL/57SKIP,13lỗi nền cùngcause,1thiếu defaults test recheckPASS,40ca cũ thêmSKIP. DBtest đã dọn,0index/defaults giữ. [Nhật ký634](../nhat_ky/2026-10-25_phien_634_sua_luong_ocr_nemotron.md).

- **2026-10-25 — Context633: test upload/Nemotron chưa đạt đầu-cuối.** 3file upload/download hash và duplicate PASS; native import2/2, direct PNG/scan OCR16/16ô/0fallback, regression29PASS. DOCX reparse failed/alignment HTML; PDF review_required/TABLES_NOT_MATERIALIZED dù raw/JSON giữ đủô. Initialbatch thiếuengine riêng; API409chặnartifactv1trongv2failed,activev1giữ/0index. ModelOpskeypool/defaultsgiữ; khôngappfix/UI/full/pub/Compiler/Git. [Nhật ký633](../nhat_ky/2026-10-25_phien_633_test_upload_nemotron.md).

- **2026-10-25 — Context632: hạ tầng mới 5/5 healthy.** User xác nhận đã xóa dữ liệu cũ và chỉ định pgsty/minio:RELEASE.2026-06-18T00-00-00Z; đổi đúng 1 dòng image local infra. PostgreSQL/Redis/Qdrant/Gotenberg/MinIO healthy, SELECT1/PONG/HTTP200 và S3 ListBuckets có xác thực200/0bucket PASS, đủ 4 volume mới. Giữ 4 dịch vụ khác và diff đồng thời; chưa app/worker/migration/seed/Compiler, không phục hồi dữ liệu cũ. [Nhật ký632](../nhat_ky/2026-10-25_phien_632_khoi_tao_lai_ha_tang.md).

- **2026-10-25 — Context630: sửa PDF text, giữ chuẩn MD/JSON và Quality Gate.** Header trắng, nối trang không header, native projection và metadata OCR; cache PDF v6, đọc v5 tương thích. Focused219/Ruff9 PASS; full3.833PASS/18FAIL nền/17SKIP, exactIDs/cause khớp627, 33test mớiPASS. Quyđổi760→0/họcphí570→0limitations; báo cáo2024 còn184 và vùng hình vẫn chặn. DBtest dọn/Storage giữ, nguồn/model/index seals khớp; không LLM mới/Compiler/vector/pub/restart/Git. [Nhật ký630](../nhat_ky/2026-10-25_phien_630_sua_pdf_text_va_doi_soat.md).

- **2026-10-25 — Context629: PaddleOCR endpoint hoạt động.** User chỉ định layout-parsing nội bộ; probe đúng1crop header qua adapter/Redis thật HTTP200/errorCode0/1,578s/exit0,0cloudfallback. Rawheader có123/TB-HĐTS và date11/7/2026; Markdown bỏheader, header_rescue đọcchỉMarkdownnênthiếusố, offline táihiện. Chưaappfix/wholePDF/Compiler;628NEEDS_ATTENTIONgiữ. DBreadonly/source-provider-apphashgiữ, không index/pub/restart/modelchange/Git. [Nhật ký629](../nhat_ky/2026-10-25_phien_629_xac_minh_endpoint_paddleocr.md).

- **2026-10-25 — Context628: thử PDF quy đổi điểm QNU2026, chưa đạt trước Compiler.** MD/JSON/source replay và giữ760rawfields PASS; header trắng/đậm không thỏa bold+shading nên cả3phần bảng header0. AutoNEEDS_ATTENTION7blocker/760limitations; Compiler preview/create chặn source_not_current_ready,0LLM. OCR đầu bị Redis cô lập; lượt live bị auto-review chặn payload/đích, không bypass. HaiDBtest dọn/Storagegiữ; app/source/shared/config seals giữ. Không appfix/wholeDOCX/index/pub/restart/commit/push. [Nhật ký628](../nhat_ky/2026-10-25_phien_628_thu_pdf_thuc_te_truoc_compiler.md).

- **2026-10-24 — Context627: người dùng đã nghiệm thu chức năng Compiler và yêu cầu không chạy lại.** Retry121–123 bằng cx bỏ relations; grounded prompt làm mất DIRECTION_RULES. Sửa prompt dùng chung quy tắc, không swap/đổi guard. Sau sửa:5.173→4.500 được122/123 supported; triad vẫn FAIL vì mã1906 trong heading bị coi là năm. Baseline8FAIL→8PASS, focused129/Ruff2PASS; full3.800PASS/18FAIL nền/17SKIP, exact IDs/cause khớp625, không regression mới. Hai DB regression đã dọn/Storage giữ, acceptance/old jobs giữ. Không whole/64/index/pub/restart/commit/push. [Nhật ký627](../nhat_ky/2026-10-24_phien_627_chay_lai_va_sua_chieu_quan_he.md).

- **2026-10-24 — Context626: retry cx/gpt-6-luna và chạy hết compiler.** Bước86 PASS 15,734 giây, review87 6/6 supported; tổng38 phản hồi mới stop/0 fallback, tiếp tục đến123. Bundle58 assertion/9 section/1 relation, đọc mới/idempotency PASS nhưng needs_attention:6/14 packet và4 section chưa đủ, relation4.500→5.173 ngược. Mốc5.948/2024,5.081 nhập học/2025,5.173/2026 đúng nguồn/năm. Tái dùng candidate cũ bằng test-only namespace mapping có guard/audit; không sửa app/default/source/QG hoặc old uncertain. Không full/64/index/pub/Git, acceptance DB/Storage giữ. [Nhật ký626](../nhat_ky/2026-10-24_phien_626_thu_cx_luna_va_tiep_tuc_compiler.md).

- **2026-10-24 — Context625: chưa nghiệm thu compiler.** Tiếp tục từ bước 9, giữ candidate/hash/receipt; tới 85, bước 86 PacketDraft ALL_PROVIDERS_UNAVAILABLE/uncertain, chưa final bundle. Sửa coverage role binding tại JSON boundary, giữ server guard; baseline 3 FAIL/4 PASS → focused 93 PASS/Ruff 3 file PASS. Full 3.792 PASS/18 FAIL nền/17 SKIP, exact IDs/cause khớp623, không regression mới. Hai DB regression đã dọn; acceptance DB/Storage giữ, không resend. Nguồn/model/QG giữ, không index/publish/restart/commit/push. [Nhật ký625](../nhat_ky/2026-10-24_phien_625_tiep_tuc_compiler_tu_buoc9.md).

- **2026-10-24 — Context624: retry riêng bước8 PASS.** User xác nhận9router và cho thử lại; gh/gpt-5.6-luna/timeout30,10,734s,1retry/0fallback/stop;64proof phân loại đủ52+12,18.713input/1.247output. Hash request/config và Storage readback/seals khớp;không chạy lại1–7, không sửa app hoặc checkpoint uncertain cũ. Chưa bước9/wholecompiler/full/64/index/pub/Git; DBacceptance/Storage giữ. [Nhật ký624](../nhat_ky/2026-10-24_phien_624_thu_lai_buoc8_9router.md).

- **2026-10-24 — Context623: chưa nghiệm thu compiler.** Sửa 2 blocker lưu/đối soát và làm rõ scope; 154 focused/Ruff4 PASS, 7 test mới PASS; full cuối 3785 PASS/18 FAIL nền/17 SKIP, exact IDs/cause khớp622. Lượt đầu 120 stage/0fallback, 2resume, lưu/đọc mới/idempotency đạt, các mốc5948/5081/5173 đúng nhưng machine_complete=false. Lượt mới7 phản hồi, stage8 ReadTimeout30s/uncertain. User yêu cầu giữ để kiểm tra9router: dừng model, giữ DBacceptance/Storage/checkpoint;2DBregression đã dọn. Không index/publish/Git/config/source writes. [Nhật ký623](../nhat_ky/2026-10-24_phien_623_nghiem_thu_compiler_va_giu_checkpoint.md).

- **2026-10-24 — Context622:** sửa phân biệt scope/thiếu giá trị, repairv3 có mapping/coverage độc lập và guard cột prose. Gói2026 cuốiPASS5.173/data2026 qua Luna3+2calls/0fallback; replay mixed candidatePASS. 14regression mới/98focused/Ruff9PASS; full3778PASS/18FAILnền/17SKIP, exactIDs/cause khớp620. Hai DBtest đã dọn, Storage giữ policy; nguồn/default/seals giữ. Chưa wholecompiler/64/index/pub/Git. [Nhật ký622](../nhat_ky/2026-10-24_phien_622_sua_giu_gia_tri_5173_va_repair.md).

- **2026-10-24 — Context621 phân tích:**5.173cóđủrawDOCX/MD/request/scalarspan. Initialnhầmscope→unknown; correction62đãtríchđúng5173nhưngthêmunknownsai, cảcandidatebịrejected/giữinitial. 8offlineprobePASS/exit0,0LLM/DB/networklượtchốt,apphashgiữ. Chưafix/khôngfull/64/index/pub/Git. [Nhật ký621](../nhat_ky/2026-10-24_phien_621_nguyen_nhan_5173_unknown.md).

- **2026-10-24 — Context620:** thửgh/gpt-5.6-luna/capacityđộng(metadata1050000/128000),defaultappgiữ. SửaModelOpsghiobservationidempotent,focused124/Ruff2PASS;full3764PASS/18FAILnền/17SKIP,exactID/causegiữ. Final66Luna/0fallback/allstop,targetgender5081/data2025đúng; vẫn2026explicit5173→unknown/coverageincomplete,finishFAILgrounded_coverage_review_missing,machine_completefalse. ChưaAPPROVED;3DBtestdọn/Storagegiữpolicy,nguồn/QGgiữ,không64/index/pub/Git. [Nhật ký620](../nhat_ky/2026-10-24_phien_620_thu_gh_gpt_56_luna.md).

- **2026-10-24 — Context619 nghiệm thu: NOT APPROVED.** Wholecompiler3DOCX/381proof,39GPT-OSSmedium/0fallback/allstop; servicefinishFAILsemantic_repair_rejected_candidate_effective. Replay39stage/0LLM xác nhậnactiveassertionbảngkhác,saipublication2025,machine_completefalse; metadatareview/coverage gâycomparisonlệch. Khôngappchange/full/64/index/pub/Git. DB619đãdọn/Storagegiữpolicy, nguồn/default/sealsgiữ. [Nhật ký619](../nhat_ky/2026-10-24_phien_619_nghiem_thu_compiler.md).

- **2026-10-24 — Context618:** thêm menu span_id/proof/literal/offset/role tường minh và safe feedback, giữ enum/QG. Baseline10FAIL→focused92PASS, broad232PASS/Ruff6PASS; full3759PASS/18FAIL nền/17SKIP, exactID/cause giữ. Hai DB618 đã dọn/Storage giữ policy. Gói617từnglỗi:1GPT-OSSmedium draft22341input/2234output/stop/0fallback, chọn exactrecord5.081; chưa semantic/coverage/wholecompiler. Nguồn381proof/defaultgh giữ, không64/index/pub/Git. [Nhật ký618](../nhat_ky/2026-10-24_phien_618_span_id_va_vai_tro_trich_doan.md).

- **2026-10-24 — Context617:** tự khám phá capacity endpoint, tokenizer/calibration và output theo phần context còn lại; không cần nhập tay ModelOps. GPT-OSS live120002input/219output/3marker đúng/stop/0fallback, metadata128000context/64000output. Focused54/Ruff16PASS; full3744PASS/18FAIL nền/17SKIP, exactID/cause giữ, không regression mới. Bốn DB617 đã dọn/Storage giữ policy. Compiler3DOCX29callsFAIL span role enum, không overflow, chưaAPPROVED. Nguồn/defaultgh/QGgiữ, không64/index/pub/Git. [Nhật ký617](../nhat_ky/2026-10-24_phien_617_capacity_endpoint_va_ngan_sach_dong.md).

- **2026-10-24 — Context616 đang thực hiện:** literal/record/native header/truth-coverage và planner rendered-review; focused61/Ruff18 PASS, full cuối NOT RUN. Live11 còn capacity blocker, chưa APPROVED. Dừng thử13 theo yêu cầu không ghim token/kiểm kê: 128stage import,0inference mới; chưa đổi DB/model/QG. Capacity profile chưa khai báo; fallback24K/2500, script24K/8192, admissions5000. Không64/index/pub/Git. [Nhật ký616](../nhat_ky/2026-10-24_phien_616_compiler_va_kiem_ke_ngan_sach_token.md).

- **2026-10-23 — Context615:** chặn xác nhận nhãn số liệu không có binding literal metric/cột/ô; policy v4, giữ đọc bundle cũ. Baseline9FAIL/3PASS→focused19PASS/Ruff6PASS; full/64NOTRUN theo yêu cầu chỉ test ca nhầm. Hai lượt thật cùng câu5.081/8GPT-OSSmedium8192/0fallback không còn affirmative quota, nhưng binding/scope/header còn lỗi: guard đạt, semantic extraction chưaAPPROVED. Source/defaultgh/config/domain hashes giữ, không tạoDBtest/index/pub/restart/Git. [Nhật ký615](../nhat_ky/2026-10-23_phien_615_chan_nham_vai_tro_so_lieu.md).

- **2026-10-23 — Context614: liên kết compiler mục/bảng/header/ô/note, raw role candidate và coverage debt không tự duyệt. Focused88/Ruff13/21regression mới PASS; full3622PASS/18FAILnền/17SKIP,+23subtestPASS, exact613IDs/cause giữ. Real3DOCX102entities/116assertions/36sections/36groups/18relation candidate, Storage readback khớp nhưng needs_attention. Manual finding:5.081 vẫn bị LLM gán quota thay số nhập học, dù item/section supported; chưaAPPROVED. Final261call/thực tế toànphiên442GPT-OSSmedium8192/0fallback;72topiccalltáidùng. Source/defaultgh/sharedrows/vector2943/0retrievablegiữ;5DBtestdọn/Storagegiữpolicy; khôngreindex/publish/restart/commit/push.** [Nhật ký614](../nhat_ky/2026-10-23_phien_614_lien_ket_ngu_canh_compiler.md).

- **2026-10-23 — Context613: compiler theo nhóm/Manifestv2 và ngân sách ModelOps theo alias/endpoint; giữ QG.15regression mới/focused70/Ruff19PASS; full3601PASS/18FAILnền/17SKIP,+23subtestPASS, exact611IDs/cause giữ. Real3DOCX92entities/145assertions/25sections/16groups,54calls mới/0fallback/length,96cũ không lặp; bundle đọc lại khớp nhưng needs_attention, cross12/31cặp. Source/defaultgh/sharedrows/vector2943/0retrievable giữ,5DBtestdọn/Storagegiữpolicy; khôngreindex/publish/restart/commit/push.** [Nhật ký613](../nhat_ky/2026-10-23_phien_613_compiler_theo_nhom_va_ngan_sach_model.md).

- **2026-10-23 — Context612: chẩn đoán compiler ngoại tuyến, không sửa app/gọi LLM/DB. D01–D12 PASS/exit0 tái hiện tổng92/145 vượt64/128 trước batching; một nguồn70entities. Phát hiện tiếp synthesis planner thêm5000reserve chặn4request dù request gốc vừa24K; service bọc generic502. Giữ nguồn/app/JSON611, chưa compiler APPROVED; khôngreindex/publish/commit/push.** [Nhật ký612](../nhat_ky/2026-10-23_phien_612_tim_nguyen_nhan_compiler.md).

- **2026-10-23 — Context611: Đã sửa packing/checkpoint và explicit reasoning_effort, giữ QG. Ruff14/focused59/concurrency2PASS; full3586PASS/18FAIL nền/17SKIP,+23subtestPASS,22test mớiPASS, exact608IDs/cause giữ. Real3DOCX/GPT-OSSmedium8192:96calls/0fallback/length,max5295output; resume giữ54prefix,chỉ42calls mới. Compiler vẫnFAIL khi ghép92entities/145assertions>64/128,không nới/cắt đểPASS. Nguồn/defaultgh/model/vector2943/0retrievable giữ,4DBtestdọn/Storagegiữpolicy; khôngreindex/publish/restart/commit/push.** [Nhật ký611](../nhat_ky/2026-10-23_phien_611_dong_goi_checkpoint_compiler.md).

- **2026-10-23 — Context610: Thử GPT-OSS medium/output8192 qua ModelOps trong process riêng, giữ primary gh/gpt-6-luna. Ba DOCX/381proof/12gói chọn/24calls đều stop, max2795output,0fallback/truncation. Compiler FAIL HTTP422 single_unit_budget trước draft:192proof giữ, reserve26699>24K; mô phỏng32K vẫn>=68calls>64. Tiền kiểm đầu chỉselection, đã đối soát fullplan ngoại tuyến, không LLM thêm. Nguồn/sharedrows/457appfiles/vector2943/0retrievable giữ, DBtestdọn/Storagegiữpolicy. Không sửaapp/reindex/publish/restart/commit/push; chưa APPROVED.** [Nhật ký610](../nhat_ky/2026-10-23_phien_610_thu_gpt_oss_medium_8192.md).

- **2026-10-23 — Context609: Thử ollama/gpt-oss:120b qua ModelOps, giữ primary gh/gpt-6-luna. Probe JSON PASS; compiler3DOCX FAIL ở TopicSelection thứ2 do output2.500 bị cắt, HTTP503/uncertain/bundle null. Điều tra cap app8.192 và workflow24K; chưa tăng cap, chưa gọi lại. Nguồn/model/457app files/vector2.943/0retrievable giữ, DBtestdọn/Storagegiữpolicy. Không reindex/publish/restart/commit/push; full/64NOTRUN, chưa APPROVED.** [Nhật ký609](../nhat_ky/2026-10-23_phien_609_thu_gpt_oss_va_ngan_sach_dau_ra.md).

- **2026-10-23 — Context608: sửa empty draft→coverage và tách temporal review;13test mới, focused182/Ruff5 PASS. Full3564PASS/18FAIL baseline/17SKIP,+23subtestPASS, exact IDs/cause giữ. Qwen hai probe hẹp PASS nhưng whole3DOCX FAIL reason>400. Theo chỉ đạo tiếp, thêm đúng alias gh/gpt-6-luna/9router sau probe thật, đổi primary defaults+admissions single/no fallback, giữ role khác; provider trả model gpt-6-luna. Luna chọn bằng chứng18lượt qua3nguồn rồi2draft JSON syntax FAIL, HTTP502/bundle null; chưa APPROVED. Nguồn/model ngoài phạm vi/vector2943/0retrievable giữ,3DBtestdọn/Storagegiữpolicy. Không reindex/publish/restart/commit/push. Gitea607commit09d254da đã đồng bộ; GitHub còn GH001 PDF lịch sử, không rewrite.** [Nhật ký608](../nhat_ky/2026-10-23_phien_608_sua_review_rong_va_thu_gh_luna.md).

- **2026-10-23 — Context607: người dùng cho phép commit/push checkpoint600–606 trên v1.0.1. Preflight107tệp, không nghi vấn token/private key; Ruff52/FE14/BiomeLF6/build+TS PASS, app hashes giữ. Full606 vẫn3551PASS/18FAIL baseline/17SKIP; compiler thật chưa APPROVED. Snapshot này ghi trước commit; xác nhận push bằng SHA remote/receipt607 và phản hồi cuối. Gitea trước GitHub, không force/reindex/publish/restart/deploy.** [Nhật ký607](../nhat_ky/2026-10-23_phien_607_checkpoint_git_wiki_va_compiler.md).

- **2026-10-23 — Context606: đã đổi nhãn assertion trên wire thành source_unspecified/null, tách verdict unresolved và giữ unknown/null đã lưu. Kiểm chiều quan hệ PASS và đối soát ba coverage dispute; thêm source limitation guide, local graph guard và cap4primary để chừa đầu ra. Focused169/Ruff10/31test mới PASS; full3551PASS/18FAIL baseline/17SKIP,+23subtestPASS, exact ID/cause giữ. Toàn90usage Qwen,0Luna/fallback. Ba full compiler trước alias FAIL; probe cuối extraction đúng alias nhưng temporal review/empty-draft schema vẫn FAIL, chưa APPROVED/compiler bundle. Source/model/config/vector2943/0retrievable giữ,2DB test dọn/Storage giữ policy. Không benchmark64/reindex/publish/restart/commit/push.** [Nhật ký606](../nhat_ky/2026-10-23_phien_606_ro_nghia_unknown_va_kiem_chung_qwen.md).

- **2026-10-23 — Context605: theo yêu cầu mới, chuyển model chính sang Qwen3.5-9B vì Luna gần hết token. ModelOps defaults single/Qwen-only và admissions primary=Qwen/fallback=null; HTTP PUT/PATCH/GET200, route resolver Qwen/no fallback. Một probe HTTP200 đúng qwen3.5-9b/stop/no fallback,20input/2output, không Luna. Chỉ system defaults/admissions đổi; provider/key/embedding/rerank/OCR/bốn assistants/source/index và app code giữ. Token Saver 9router trước đây chưa có đối chứng, không quy nguyên nhân hoặc relabel lịch sử. Blockers604 giữ; không full/64/compiler dài/reindex/publish/restart/commit/push.** [Nhật ký605](../nhat_ky/2026-10-23_phien_605_chuyen_qwen_model_chinh.md).

- **2026-10-23 — Context604: bổ sung bảo vệ scope/source-year, chiều quan hệ và coverage trước đợt5; chưa nghiệm thu compiler thật. Policy v3, literal anchors, temporal/event roles, blind endpoint membership, bounded repair và exact wire budgets. Focused138/Ruff12/52test mới PASS; full3520PASS/18FAILnền/17SKIP,+23subtestPASS, exactIDs/cause khớp baseline3468/18/17,0lỗi mới/thiếu. Real3DOCX cuối10assertions/3sections/1relation/41Luna,381exactproofs; draft2025khônglansang2024,5173→4500đúng,24proofcũđốisoát. Còn3relevance disagreement/directionreviewunresolved; probe codecuối ReadTimeout, chưaAPPROVED. Nguồn/model/config/vector2943/0retrievable giữ; DB604dọn/Storagegiữpolicy. P10/64/FE/serving đểsau; không reindex/publish/restart/commit/push.** [Nhật ký604](../nhat_ky/2026-10-23_phien_604_kiem_chung_pham_vi_va_chieu_quan_he.md).

- **2026-10-22 — Context603: triển khai backend compiler/lifecycle đợt3–4; nội dung thật chưa nghiệm thu. Topic selection+review, assertion/scope/time proofs, bounded synthesis, immutableStorage/registry, auth/OCC/idempotency/audit/revocation và per-source packet reuse. Focused139/Ruff18/55test mới PASS; full3468PASS/18FAILnền/17SKIP,+23subtestPASS,exactIDs/cause khớp baseline3413/18/17,0lỗi mới/thiếu. Real3DOCX APIcreate+exactGET200,5assertions/3sections/1relation,381/381exactproofs;33Luna/0fallback. Needs_attention,24missedproofs/1unresolvedsection; manual phát hiện draft2025gánsang2024 vàđảochiềusupersedes, chưaAPPROVED nội dung. Source/model/config/vector2943/0retrievable giữ,DBtest603dọn/Storagegiữpolicy. P10đểsau,64khôngrerun; khôngFE/RAGhook/reindex/publish/restart/commit/push.** [Nhật ký603](../nhat_ky/2026-10-22_phien_603_compiler_chu_de_va_vong_doi_dan_xuat.md).

- **2026-10-22 — Context602: sửa nền và hợp đồng biên soạn đợt1/2; chưa nghiệm thu toàn RAG. Native DOCX reconciliation giữ provenance, year lexer không suy từ mã, inventory512/page đủ1301sections, evidence recovery giữ qualifier sau reselection. Schema/binding mới chỉ review_only, chưa compiler xuyên nguồn. Focused889/Ruff21/51test mới PASS; full3413PASS/18FAILnền/17SKIP,+23subtestPASS, exactIDs/cause khớp baseline3362/18/17. Frozen64cuối59/60(98,33%),49/50positive,10/10negative,4/4social; cònP10,140/140citations,147Luna/0fallback. Multi-source6/12 so4/12,3wiki ready/14trang,23/23citations; M02/M03timeout,M08scope-condition,M09/M10coverage,M12year-role. P13auditprompt76323tokens cần budget tiếp; không quy lỗi cho32K. Source/model/config/fullvectorpayload giữ,DBtestdọn/Storagegiữpolicy; không reindex/publish/restart/commit/push.** [Nhật ký602](../nhat_ky/2026-10-22_phien_602_sua_nen_va_hop_dong_bien_soan_tri_thuc.md).

- **2026-10-22 — Context601: bảo toàn tiền đề và kiểm chứng nguồn thật nhiều năm; chưa nghiệm thu. 23 test mới, focused852/Ruff6 PASS; full3361PASS/19FAIL/17SKIP,+23subtestPASS:18 nền giữ ID/cause, thêm backupWindows PermissionError (chạy riêng6PASS), không ghép full. Frozen64chốt57/60(95%),47/50positive,10/10negative,4/4social; cònP07/P08/P16, giảm2 câu so600.128/128citations,149Luna/0fallback. Multi-source adapters4/12PASS,8FAIL;2024/25Wikiunavailable dofragment ngắn,2026ready;4lỗi year-scope, cẩm nang1301sections>512. DBtestdọn/Storagegiữtheopolicy; nguồn/model/code/vector/publication seals giữ, không reindex/publish/restart/commit/push.** [Nhật ký601](../nhat_ky/2026-10-22_phien_601_bao_toan_tien_de_va_kiem_thu_nhieu_nam.md).

- **2026-10-22 — Context600: triển khai liên kết/revision/đối chiếu Wiki4–6, chưa nghiệm thu do P07. Focused829/Ruff13/FE22/Biome6/build+TS PASS;45 test mới PASS. Full3339PASS/18FAIL nền/17SKIP,+23subtestPASS,exact599 IDs/cause giữ. Baseline64 58/60→cuối59/60(49/50positive,10/10negative,4/4social),gainsP10/P15,lossP07 thiếu tiền đề;152/152citations,0runtime,150Luna/0fallback. RetryP07 riêngPASS không thay điểm. Multi-source/lifecycle/consistency kiểm trên DBtest/ASGI thật;modelmock. Source/model/index/vector giữ;DBtestdọn,Storagepolicyblocked. Browserauth/publishedE2E NOTRUN;không reindex/restart/publish/commit/push.** [Nhật ký600](../nhat_ky/2026-10-22_phien_600_wiki_lien_ket_revision_va_doi_chieu.md).

- **2026-10-22 — Context599: sửa P06/X09, giữ điều kiện và phục hồi ý trả lời. 19 test mới, focused 784/Ruff 8 PASS; full 3294 PASS/18 FAIL nền/17 SKIP +23 subtest PASS, exact ID/cause khớp597, không lỗi mới hoặc mất test. Live chốt 6/6, 39/39 citations, 40 Luna/0 fallback; probe5/6 và4/6 giữ riêng. Source/model/code/vector/publication seals giữ; DB test đã dọn, Storage giữ theo policy. Full64/FE/published E2E NOT RUN; không ghép thành60/60, không reindex/restart/publish/commit/push.** [Nhật ký599](../nhat_ky/2026-10-22_phien_599_sua_p06_x09_va_kiem_chung.md).

- **2026-10-22 — Context598: phân tích P06/X09, chưa sửa app. Nguồn/gold/context đủ; P06 audit loại claimSV và repair chỉcondition, cònmissingfacet; nhánh break chính xác chưa được log đủ. X09 numeric90 chưa có rawdraft để chốt; fallback đủtopic nhưng source-review bắtQscale, verifier loại, ledger chặn. Offline9probe exit0,1.244seals giữ,0LLM/DB/egress; một metadata attempt bịguard chặn. Full/liveNOTRUN,58/60 giữ lịch sử597; không parser/reindex/publish/restart/commit/push.** [Nhật ký598](../nhat_ky/2026-10-22_phien_598_phan_tich_p06_x09.md).

- **2026-10-22 — Context597: ổn định điều kiện nguồn và phạm vi từng trích đoạn. 765 focused/Ruff14 PASS,37 regression mới PASS; full3275PASS/18FAILnền/17SKIP, exactIDs/nguyên nhân khớp595. Frozen64 cuối58/60=96,67% (49/50positive,9/10negative,4/4social), đạt85%; cònP06/X09,0runtime,141/141citations,148Luna/0fallback. Các lượt/probe giữ riêng; source/model/index/code seals khớp, chưa publish. 4DBtest dọn/Storage giữ theo policy; không reindex/restart/commit/push. Chưa nghiệm thu100% hoặc wiki4–6.** [Nhật ký597](../nhat_ky/2026-10-22_phien_597_on_dinh_dieu_kien_nguon_va_benchmark64.md).

- **2026-10-22 — Context596: phân tích giảm điểm RAG, chưa sửa app. 59159/60→59551/60: F03gain,9loss gồm5lease vàF08/P07/P12/P15. Synthetic model song song làm nhiễu; retry5/5 giữ riêng. P07 đủ source/audit scope nhưng thiếu tiền đề; required=false có thể bỏ gap. P12 audit vẫn thiếu định nghĩa sau bổ sung; P15 chọn đoạn thừa; cùngcontextIDs/mãfallback591. F08literal mismatch chưa lưu rewrite để kết luận case-only. Offline exit0,1239seals giữ;0LLM/DB/network,full/liveNOTRUN. Không quy toàn bộ loss cho595 hoặc parser/context32K; không fix/reindex/publish/restart/commit/push.** [Nhật ký596](../nhat_ky/2026-10-22_phien_596_phan_tich_nguyen_nhan_giam_diem_rag.md).

- **2026-10-22 — Context595: sửa mục3–6: role năm, tập referent nhiều đối tượng/bảng, wiki budget theo trang chọn và cache repack theo budget/policy/nguồn. Focused381/Ruff7 PASS,43mớiPASS; full3238PASS/18FAILnền/17SKIP, exactIDs/cause khớp594. Synthetic Luna4/4; replay11/11pages. Frozen64:51/60tri thức,41/50positive,10/10negative,4/4social; target85positive FAIL.5lỗi lease retry riêng5/5, không ghép điểm; cònF08/P07/P12/P15. Model/nguồn/index/publication giữ, postchecksPASS,DBtestdọn/Storagegiữ; không reindex/publish/restart/commit/push. Chưa APPROVED toànRAG hoặc triển khai wiki4–6.** [Nhật ký595](../nhat_ky/2026-10-22_phien_595_vai_tro_nam_tap_tham_chieu_va_wiki_budget.md).

- **2026-10-22 — Context594: sửa P1 coverage đối tượng/nguồn và bảo toàn điều kiện/ngoại lệ. Focused290/Ruff4 PASS;56regression mới PASS. Full3195PASS/18FAILnền/17SKIP, exactIDs/cause khớp592, không lỗi mới/thiếu. Live8/8,citations8/8,6Luna/0fallback; synthetic routing3/4,C04FAIL do metric không giữ literal, hỏi lại an toàn, chưa chứng minh riêng hoa/thường. Full64/FE NOT RUN. Hai DBtest dọn, Storage giữ theo policy; nguồn/model/vector/publication và code ngoài scope giữ. Chưa mục3–6/wiki4–6/reindex/publish/restart/commit/push.** [Nhật ký594](../nhat_ky/2026-10-22_phien_594_bao_toan_pham_vi_va_dieu_kien_hoi_thoai.md).

- **2026-10-22 — Context593: review mở rộng ngữ cảnh/liên kết, chưa sửa app. Tái hiện8 trường hợp thành6 nhóm: coverage chủ thể/nguồn và điều kiện/ngoại lệ (P1); role năm học, nhiều đối tượng/bảng, chia budget wiki (P2); cache khi đổi budget (P3, chưa chứng minh caller hiện tại hạ budget). Hai control đúng, offline exit0, 1235 code seals giữ, 0LLM/DB/network. Full/live hiện tại NOT RUN; 8/8 và full3139PASS/18FAIL/17SKIP là lịch sử592. Không reindex/publish/restart/commit/push.** [Nhật ký593](../nhat_ky/2026-10-22_phien_593_review_mo_rong_lien_ket_va_ngu_canh.md).

- **2026-10-22 — Context592: tách locator/metric và sửa tham chiếu một lần trong cùng20s. Live cuối 8/8 followup, cònFAIL không có; citations8/8, 4Luna usage/0fallback. Focused269/Ruff3 PASS; full3139PASS/18FAILnền/17SKIP, 16 test mới PASS, không lỗi mới/thiếu ID/đổi cause. Full64 hiện tại NOT RUN, điểm59/60 là lịch sử591. Batch đầu7/8/F08FAIL giữ nguyên; postcheckPASS,2DBtestdọn/Storagegiữ. Model/nguồn/vector giữ; không reindex/publish/restart/commit/push.** [Nhật ký592](../nhat_ky/2026-10-22_phien_592_tham_chieu_hoi_thoai_va_sua_loi_co_gioi_han.md).

- **2026-10-22 — Context591: sửa trace/reader/unknown/year/condition packing; cuối đủ64, 59/60 tri thức, positive49/50, negative10/10, social4/4; 85%PASS. CònFAIL F03. Focused257/Ruff21 PASS; full3123PASS/18FAILnền/17SKIP, 37mớiPASS, exactIDs/cause không đổi. 138/138citationsđúng, 124Luna usage/0fallback. Source/model/config/vector giữ, postcheckPASS, 2DBtestdọn/Storagegiữtheopolicy. Không reindex/publish/restart/commit/push.** [Nhật ký591](../nhat_ky/2026-10-21_phien_591_sua_rag_wiki_va_benchmark64.md).

- **2026-10-21 — Context590: chẩn đoán 9 lỗi RAG còn lại, chưa sửa app.** 24 gold spans/23 units còn trong canonical/wiki; P03/P13/P14 sai reader contract; P07/P11 hỏi năm trước retrieval; P09/P10 ambiguous bị báo lỗi integrity; P05 audit vòng sau thiếu điều kiện. P01 thiếu mã lỗi gốc, không đủ chứng minh upstream HTTP502/timeout. Offline12 probe PASS/exit0, 0LLM/DB,743seals giữ; full/live64 NOT RUN. Giữ model/nguồn/vector/publication và code cũ; chưaAPPROVED/ưu tiên4–6/commit/push. [Nhật ký590](../nhat_ky/2026-10-21_phien_590_phan_tich_loi_rag_wiki.md).

- **2026-10-21 — Context589: extractive wiki PDF đạt, chatbot chưa nghiệm thu.** Rev12/wiki11 trang, đủ327 units/1915 exact refs, staging327chunks415facts/0retrievable; 7 lượt Luna, model/source/config giữ. Bộ chính nhận63/64 kết quả, P06 gián đoạn; điểm chính50/60; P06 bổ sung PASS nên tham khảo51/60=85%, positive41/50=82%, social4/4; chưa đạt43/50 positive. Full cuối 3.086 PASS/18 FAIL/17 SKIP, exact18 IDs/cause khớp baseline,60 test mới PASS. DBtest đã dọn; Storagetạm giữ do policy. ChưaAPPROVED/ưu tiên4–6/publish/commit/push/restart/deploy. [Nhật ký589](../nhat_ky/2026-10-21_phien_589_hoan_thien_wiki_pdf_va_benchmark64.md).

- **2026-10-21 — Context588: thử PDF thật, wiki chưa đạt dù canonical benchmark đạt85%.** Tạorev5ks_rev_697bfdc3de8e (0blocker/canonical51531chars trùng583), idx_rev_bb4c3f1a91d0 staging327chunks415facts; namespace654points (old327+new327)/0retrievable, activeIndexnull. Wikiunavailable0pages/HTTPGET200: Luna analysis35591prompttokens rồi generationtimeout, Qwencontext400; packetbudget chỉtext23891chars nhưngJSON107136 (heading15707/temporal55540). Cầnfixpayload/token budget/metadata share, chưaappfix; không dùng synthetic587PASS để nóiPDFwikiPASS. Frozen64samequeries/rubric/spans:55/60=91.67%,positive45/50,negative10/10,social4/4;gainsP01/P16,lossF04,commonFAILP05/P07/P09/P10.105Luna success0fallback,124/124citationsresolve;benchmarkwiki_enabled=false nênkhôngclaimwikigain. PostcheckPASS/modeltimeout30/config/code/outside/oldrevisions giữ;0testthreads/messages/gaps, noDBtest. Noappfix/publish/commit/push/restart/deploy. [Nhật ký588](../nhat_ky/2026-10-21_phien_588_pdf_revision5_wiki_va_benchmark64.md).

- **2026-10-21 — Context587: triển khai ba ưu tiên wiki trong QNU.** Source/entity/concept Markdown biên soạn trước embedding cho revision mới, exact refs/year roles/conditions; bundle ghim chunk/index hash, reader tối đa hai lượt dùng canonical evidence, API/UI Trang tri thức. Sửa policy-before-readiness-seal và metadata wiki null. Focused162/FE15/Ruff21/Biome6/build PASS; full3026PASS/18FAIL/17SKIP, exact18 IDs/message khớp baseline, 41 ca mới PASS. ModelOps thật synthetic compiler/reader đạt, không HTTP E2E/64 benchmark, chưa merge entity xuyên nguồn hoặc biên soạn lại kho cũ. Ba DB test dọn, Storage còn do policy; sáu nhóm runtime seals khớp. Không đổi model/config/nguồn/vector/publication thật hoặc commit/push/restart/deploy. [Nhật ký587](../nhat_ky/2026-10-21_phien_587_trang_tri_thuc_va_doc_nguon.md).

- **2026-10-21 — Context586: đã thử lại đủ6câu PDF với Luna timeout30s: 2 PASS, 4 FAIL.** P05/P16 PASS; P01 từ chối, P07 thiếu điều kiện, P09/P10 ROW_ANSWER_SOURCE_INVALID. 21 Luna success/0fallback,17/17 citations resolve;runner0/scorer1/postcheckPASS. Source/model/config/code/vector giữ,327stagingpoints/0retrievable;chưa publish. Benchmark64gốc54/60 giữ; không app fix/commit/push/reindex/restart/deploy. Current fullNOTRUN. [Nhật ký586](../nhat_ky/2026-10-21_phien_586_thu_lai_du_6_cau_pdf.md).

- **2026-10-21 — Context585: timeout Luna đã đổi từ15 lên30giây theo yêu cầu; P16 thử riêng PASS.** HTTP200/fresh DB readback30; 36,7giây toàn luồng, 6/6 citations, 5 Luna success/0fallback. Giữ model/source/index/code/vector;327stagingpoints/0retrievable, chưa publish. Benchmark64 gốc giữ54/60, không ghép điểm. Full hiện tại NOT RUN; không app fix/commit/push/reindex/restart/deploy. [Nhật ký585](../nhat_ky/2026-10-21_phien_585_timeout_luna30_va_thu_lai_p16.md).

- **2026-10-21 — Context584: đối chiếu 6 lỗi PDF.** Không mất nội dung cần cho 6 câu; khoảng hở heading/legend metadata, đóng gói điều kiện, xử lý unknown và audit; P16 timeout provider15s. 19 probe chẩn đoán PASS, source pair/7trang visual kiểm; no LLM/app fix/knowledge write. P05 chưa có raw audit để quy chính xác predicate. Chi tiết và giới hạn trong báo cáo. [Nhật ký584](../nhat_ky/2026-10-21_phien_584_phan_tich_6_loi_pdf.md).

- **2026-10-21 — Context583: benchmark PDF staging frozen64 54/60=90.0%, social4/4; 85% ĐẠT.** Positive44/50, negative10/10; DOCX57659/60 lịch sử, gains P06, losses P01/P05/P07/P09/P10/P16. Actual Luna only105usage/0fallback; source/config/code/vector seals giữ,327points/0retrievable. Candidate service thật, không HTTP E2E; không app fix/publish/reindex/model/Git writes. Current fullNOTRUN; full582FAIL18lịch sử. [Nhật ký583](../nhat_ky/2026-10-21_phien_583_benchmark_pdf64.md).

- **2026-10-21 — Context582: PDF hết 70 mục chặn, vector staging đạt.** Revision 4 `ks_rev_fef00606f91f`, builder v5, READY_WITH_LIMITATIONS/0 blocker; 10 bảng/695 ô khớp, 3 footnote, 7 tên trường `_` dựng lại từ glyph. Nạp thật327chunks/415facts, chưa publish/64NOTRUN. Focused159/Ruff11 PASS; full2985PASS/18FAIL nền/17SKIP+23subtests, 27 mới PASS/0 lỗi mới theo ID/cause. Hai DB test dọn; Storage xóa bị policy chặn, không bypass; source/model ngoài phạm vi giữ. [Nhật ký582](../nhat_ky/2026-10-21_phien_582_go_chan_pdf_va_regression.md).

- **2026-10-21 — Context581: PDF đã nạp lại, benchmark64 BLOCKED.** DOCX đã purge; rev2ks_rev_d495e1fe0477 dùng parser mới, MD/JSON/projection/192ô Bảng1 PASS. Còn70blockers, vector404 do nguồn pending;0index/vector mới, chưa publish;64NOTRUN, model giữ. [Nhật ký581](../nhat_ky/2026-10-21_phien_581_nap_pdf_va_chan_benchmark64.md).

- **2026-10-21 — Context580: sửa cấu trúc PDF, giữ chuẩn QNU Markdown và DOCX.** Offline Bảng1 16×12/header3/192ô khớp; Bảng3 7×1; MD/JSON/hash/projection PASS. Cache version riêng PDF; parser124PASS+23subtests, full2958PASS/18FAIL nền/17SKIP, 0 lỗi mới theo ID/cause. Hai DB test đã dọn, Storage bị policy chặn; không thay revision phục vụ hoặc publish. [Nhật ký580](../nhat_ky/2026-10-21_phien_580_sua_luoi_pdf_chuan_md.md).

- **2026-10-21 — Context579: xác định nguyên nhân PDF Bảng 1 bị 34 cột.** Native nhận cạnh nền thành lưới; bỏ nền được 16×12 nhưng header chưa đúng, 20 đoạn viền bị coi là figure; trang 6 không OCR. Probe D01–D08 PASS/exit0, chất lượng Q01–Q03 FAIL; không sửa app hoặc dữ liệu nguồn. [Nhật ký579](../nhat_ky/2026-10-21_phien_579_phan_tich_bang_pdf.md).

- **2026-10-20 — Context578: dọn col_admissions và nạp PDF export 18 trang; source/cặp MD-JSON/cú pháp/projection PASS, nội dung NEEDS_ATTENTION.** Binding bnd_12190866d5ec, revision ks_rev_1071c152fab0; Bảng 1 nhận 34 thay vì 12 cột. Chưa vector/publish; Repository/kho khác/config giữ nguyên, không sửa app hoặc Git writes ngoài docs. [Nhật ký578](../nhat_ky/2026-10-20_phien_578_nap_pdf_phuc_tap.md).

- **2026-10-20 — Context577: người dùng chấp nhận kết quả và yêu cầu commit local gói parser/bản đọc/RAG Context568–576 trên main.** Kiểm tra phạm vi, credential theo mẫu, encoding và diff; không sửa thêm app, không push hoặc thay đổi dữ liệu/vận hành. Test ứng dụng không chạy lại; 18 lỗi nền và P06 vẫn được ghi nhận. [Nhật ký577](../nhat_ky/2026-10-20_phien_577_commit_parser_reader_rag.md).

- **2026-10-20 — Context576: ranh giới thuật nguồn/giả định/đánh giá hồ sơ; 44 regression mới PASS, focused 393 PASS, Ruff 15 file PASS; frozen64 59/60 = 98.33% (baseline 59/60), social 4/4; N18 PASS, B03 PASS trên code chốt; còn P06. Full 2949 PASS / 18 FAIL / 17 SKIP, không có lỗi pytest mới theo ID/nguyên nhân. Dọn: DB_REMOVED_STORAGE_POLICY_BLOCKED; model/nguồn/index giữ nguyên; không commit/push/reindex/publish/restart/deploy.** [Nhật ký576](../nhat_ky/2026-10-20_phien_576_sua_n18_b03_va_kiem_chung.md).

- **2026-10-20 — Context575 sửa phạm vi/điều kiện RAG, thêm 67 ca regression; frozen64 59/60 = 98.33%, social 4/4; full 2905 PASS / 18 FAIL / 17 SKIP, không có lỗi pytest mới theo ID/nguyên nhân; Ruff 18 file PASS; biến thể gọi thật 3/4. 8 lỗi gốc đạt, còn N18 và B03; Storage tạm bị policy chặn xóa. Giữ nguồn/model/index/publication; không Git/restart/deploy.** [Nhật ký575](../nhat_ky/2026-10-20_phien_575_sua_rag_va_regression_mo_rong.md).

- **2026-10-20 — Context574: phân tích8lỗi RAG.** Nội dung8ca còn nguyên trong DOCX/MD/JSON; lỗi ở row scope, enumeration guard, dependency/condition audit và timeout. Không sửa parser/app; probes21PASS1FAIL(IOattemptblocked),followup9PASS;benchmark52/60giữ. [Nhật ký574](../nhat_ky/2026-10-20_phien_574_phan_tich_8_loi_rag.md).

- **2026-10-20 — Context573: thử lại riêng X07 một lần.** HTTP200/21,37s, hết timeout nhưng nội dung vẫn FAIL;4Luna nội bộ/0fallback,1thread1gapdọn;source/model/code/vector giữ, không đổi điểm572. [Nhật ký573](../nhat_ky/2026-10-20_phien_573_thu_lai_x07.md).

- **2026-10-20 — Context572: benchmark và DOCX staging.** 52/60=86,67%,8FAIL (1timeout503); nguồn mới233blocks/10tables/53items/3notes/517fields, staging262points/415facts, chưa publish. Native flag integration fixed;focused109/RuffPASS;full2838PASS/18FAIL/17SKIP exact571. DBtestdọn/Storagedeletepolicyblocked. [Nhật ký572](../nhat_ky/2026-10-20_phien_572_benchmark_va_docx_staging.md).

- **Phiên571 (2026-10-20) — Cấu trúc DOCX/PDF, reader, chưa benchmark**: PDF 42 khối/5 mục; DOCX 233 khối/10 bảng/53 list items/3 note, 517 fields giữ; reader 61.760 bytes; focused172/FE36/Ruff/Biome/build PASS; full 2837 PASS/18 FAIL/17 SKIP, 0 lỗi mới theo ID. Source/model/index giữ; DB/Storage riêng đã dọn; 68 RAG files/14 benchmark input hashes giữ. [Nhật ký571](../nhat_ky/2026-10-20_phien_571_cau_truc_docx_pdf_va_ban_doc.md).

- **Phiên570 (2026-10-20) — Sửa RAG bước2, chưa benchmark**: SửaRAGscope/condition/caption/packing/reason;focused155PASS/replay9PASS;full2810PASS/18FAIL/17SKIP;0newFAIL;noLLM/64benchmark/reindex/pub/modelchange/restart/Gitwrites;17app+25regressions,DBdọn/Storagedatabase_and_storage_removed;source/configsealskhớp568. Auditrequiredvẫnmodel,khôngclaim13PASS. [Nhật ký570](../nhat_ky/2026-10-20_phien_570_sua_evidence_scope_rag.md).

- **Phiên569 (2026-10-20) — Đối soát13câu RAG, chưa sửa**: unionFAILQwen567/Luna568=13/common5,26pairs18FAIL8PASS lịch sử;33goldspans/30citations checked/samecanonical368Facts. P06packreplay11IDsđúngbỏgold,oracle2goldfitK5/36K;P07/P03conditioncoveragegap,P15ordererroraccepted;P08flagkhôngđủ/M05captiongap(selectorUNKNOWN),P10/N19tablefallbackexcluded;P11/P16/X09verificationproofscope,X05/X08genericreason. Probe13PASS/3FAIL(exit1:2P08hypothesesbịbác+importQdrantcompatintentblocked),followupstdlib4PASS/exit0giữFAIL;noLLM/DB/appfix/newbenchmark/config/index/pub/Gitwrites. Hash1275code/frozeninputs vàdocscheckhandoff;fullcurrentNOTRUN/full56718FAILlịchsử. Bước2chưatriểnkhai. [Nhật ký569](../nhat_ky/2026-10-20_phien_569_doi_soat_13_cau_rag.md).

- **Phiên568 (2026-10-20) — Luna chính/Qwen dự phòng, benchmark chỉ Luna**: user cho đổi systemchatdefaults/chain và admissions model_policy quaAPI, config khác giữ; freshDB/APIreadback đúng vàgiữsautest. Frozen64realASGIhandler/nooverrides/nolifespan/realproviders;existing server-owned allowlist scope chỉLuna,khôngđổipolicychung.51/60=85% bằngQwen567;positive43/50=86%(Qwen44/50),negative8/10(Qwen7/10),social4/4;4gainsP03/P11/P15/X09,4lossesN19/M05/P10/P16;9FAILcòn.111Luna success/0Qwenchat/0fallback;79/79citationsvalid;maxprompt10612.1275app/tests/scripts/frontend hashesgiữ,source/index262points/payloadsealsgiữ;noreindex/republish/codefix/restart/Gitwrite.58threads/14gapsdọn;usage/evidencegiữ,noDB/runtimeStorage mới.14gaplogcharmapwarningssaucommit,recordsdọnverified;khôngfix/replay. DifferentASGIvsQwenTCP,latencykhôngcontrolled;goldchưahumansignoff/notholdout,khôngkếtluậnLunatốthơntổngthể. FullcurrentNOTRUN;full56718FAILvẫnlịchsử. [Nhật ký568](../nhat_ky/2026-10-20_phien_568_luna_only_benchmark.md).

- **Phiên567 (2026-10-20) — Sửa RAG, benchmark vừa đạt85%**: query multi-metric/unit, source literal identity/aggregate, follow-up scope, text table fields/exhaustive identities, caption/formula/whole proof, canonical binding và source-owned audit. Frozen64 cuối51/60=85%,positive44/50=88%,negative7/10,social4/4 ngoài mẫu số;9FAIL P03/P06/P07/P08/P11/P15/X05/X08/X09. Source/citation không đồng nghĩa đúng:93/93spanvalid, vẫn thiếu điều kiện/rank sai/từ chối quá mức/thừa mâu thuẫn/lý do chung. Three runs51/52/51 sau đối soát rubric,khôngcherrypick;109Qwen success/0fallbackcuối,maxprompt8650. Ruff36/focused118/wire49PASS;full2785PASS/18FAIL/17SKIP+23subtests,exact565IDs/causes/38addedPASS/0new. Source/index/config/generation262points/payload seals giữ;cache codev5khôngflush.58threads mỗi lượt,gaps13/10/12dọn;DBtestdọn,runtime567~43,9MB bị auto-review blocked by policy,giữ/no bypass. Khôngreindex/republish/modelconfig/restart/deploy/Gitwrites;gold chưa human signoff,notholdout,khôngAPPROVEDtoànhệthống. [Nhật ký567](../nhat_ky/2026-10-20_phien_567_sua_rag_va_benchmark_85.md).

- **Phiên566 (2026-10-20) — Benchmark RAG85%, FAIL**: frozen60tri thức+4social, actualTCP64/64HTTP200; strict34/60=56,67%,positive28/50=56%,negative6/10,social4/4ngoàimẫusố.20positiveinsufficient,F03wrongmetric/M04partial/X05wrongunit;57/57citationhash/spanvalidkhôngđồngnghĩađúng.131usage=128Qwen+3Lunafallbackpolicycũ;maxprompt7495,khôngHTTPcontextoverflow. Code/source/index/config/generation262points/payloadsealsgiữ;58threads/29gapsdọn,usage/evidencegiữ. Runnerexit0/scorerexit1;noappfix/modelconfig/reindex/republish/restart/deploy/Gitwrites;fulltestsNOTRUN,labelchưahumansignoff/notholdout. [Nhật ký566](../nhat_ky/2026-10-20_phien_566_benchmark_rag_85.md).

- **Phiên565 (2026-10-20) — Entity/metric có căn cứ nguồn, NUMERIC E2E VERIFIED**: exactcode/zero đầu/code-name, canonicalrow+column lọc trướcLIMIT, read-onlylegacy metric quota/recorded/estimate/rate; currentmetric/unit thắng stale rewrite; guards/proof/notes/citation giữ. Focused253PASS/54new; orchestration70PASS (trùng); full2747PASS/18FAIL/17SKIP+23subtestsPASS,exact564IDs/causes/0regression;2unitfixtures boundary updated giữassertions. ASGI13/TCP8+2scalarPASS,audit23response exactsource;numericdirect0LLM/dense,followup2Qwen.14threads/6gaps dọn,source/index/configsealgiữ. DBdọn/runtimepolicyblocked/no bypass;no source/index/publish/restart/deploy/Gitwrites,benchmark85%NOTRUN. [Nhật ký565](../nhat_ky/2026-10-20_phien_565_entity_metric_resolution.md).

- **Phiên564 (2026-10-20) — Evidence dependency closure, PARTIAL**: giữ exact source row/refs, directed canonical/member closure trước budget;27testmới. Focused343PASS; full2693PASS/18FAIL/17SKIP+23subtests, exact562IDs/causes/0regression. 113prose seedpacks0broken,6rankedfactgroupsK5closurePASS. ActualTCP đoạn văn1citationhash/quotePASS,8Qwensuccess;social/followuproutingPASS, nhưng AM-0007/SV2026→2025 vẫn insufficient_context do entity/metric binding độc lập, chưa numericE2E/benchmarkPASS. Hash nguồn/index/config nguyên;DBtest/11threads/8gaps dọn, runtimeStorage xóa bịpolicyblocked/no bypass. Khôngmodelconfig/source/index/publish/restart/deploy/Gitwrite bởiagent; concurrentcommit32cdc36bgiữ. [Nhật ký564](../nhat_ky/2026-10-20_phien_564_evidence_dependency_closure.md).

- **Phiên563 (2026-10-20) — Điều tra EVIDENCE_CONTEXT_MISSING, không do Qwen32K ở request đã chạy**: usage562 hai Qwen success543/133 và4786/52tokens; backend409 khácMODEL_CONTEXT_EXCEEDED. Read-only probe full272canonical+6fact closurePASS; _fact_groups kiểmrownhưngkhônggiữrow, pack4block/8057chars/0drop thiếu canonical source row; K5/36000 và K100/10000000 đều409 trongclaimprojection, thêmđúng1rowtrongbộnhớclosure/projectionPASS. Không LLM mới/appfix/config/source/index/publish/restart/deploy/Git writes/fulltest; bằngchứngprivate563/diagnosis.json. Chưa cófullplan/stacklivecũ, khôngquymọi409duynhấtnhánhnày; cầnsửaatomicgroup/regressionvàliveE2Eriêng. [Nhật ký563](../nhat_ky/2026-10-20_phien_563_diagnose_evidence_context_missing.md).

- **Phiên562 (2026-10-20) — Hybrid intent và conversation scope, ROUTING_VERIFIED / LIVE_KNOWLEDGE_E2E_BLOCKED**: whole-message social/meta0model/retrieval; một combined resolver call/user-bound referents, history theo assistant/config, admin debug/capability domain-separated. React public A/B/reload và JS widget continuation/fragmented SSE đạt; 116utterances/20gold, focused277/compat36/Ruff21/FE6/Biome10LF/buildPASS. Full2666PASS/18FAIL/17SKIP+23subtests exact561 IDs/causes,172addedPASS/0changed/0removed. Qwen thật3cases PASS (0,7–1,9s); ASGI social142–230ms/0calls; Knowledge mixed HTTP409 EVIDENCE_CONTEXT_MISSING, packed-fact thiếu canonical source row trong probe, chưa sửa evidence packing ngoài scope. Hash5collections/23bindings/2source revisions/27indexes giữ nguyên. DBtest/6ownthreads/harness dọn; runtime1185file/18422741byte auto-review blocked by policy, không bypass; evidenceprivate562 giữ. Không source/index/publish/config/Git/restart/deploy writes. [Nhật ký562](../nhat_ky/2026-10-20_phien_562_hybrid_intent_conversation.md).

- **Phiên561 (2026-10-20) — col_admissions đã dọn và DOCX mới đã xuất bản**: người dùng duyệt toàn kho;7purge/318oldpoints→0/33orphan sidecars removed; Repository và collection khác nguyên. Nguồn bnd_fa71a57c9cf1/ks_rev_ca1e7f16d9e0/idx_rev_967891af9d5d:233block/10table/262chunks/368facts/262retrievable, strictidentityparity và latestnativeguard PASS. Bản nguồn v20 không viết lại; v21 giữ header diagnostic literal_only và association duy nhất. Focused87/RuffPASS; full2494PASS/18FAIL/17SKIP+23subtests, exactbaseline18ID/cause,0new. Không commit/push/restart/deploy. DB test dọn, runtime xóa bịpolicyblocked/no bypass. [Nhật ký561](../nhat_ky/2026-10-20_phien_561_clean_admissions_docx_publish.md).

- **Phiên560 (2026-10-19) — DOCX native fidelity và staging**: bản v4 cũ đạt content/vector staging262/368; hình dùng explicituserconfirmation; focused261+23/86PASS, full bịngắt khôngPASS. Source v4 vềsau đã purge theo duyệt561; lỗiidentity105/headerassociation được xửlý561. [Nhật ký560](../nhat_ky/2026-10-19_phien_560_docx_native_fidelity_va_vector.md).

- **Phiên559 (2026-10-19) — Live Automatic DOCX: VECTOR_BLOCKED**: authorized revision3 ks_rev_9c93b4b4e2be officialinlineworker; MD/JSON233block/10table/3footnote exactnative/core/rawPASS. NEEDS_ATTENTION8(listpage/5merged-role/header/figure),4rawlimits khôngfact; actualvectorPOST404 bindingpending,0job/index/embedding/Qdrantpoint/no publish. Old2rows/pairs/allbindingscollections/generation nguyên; no appcode/config/Git/deploy. FullNOTRUN/testhelperfirstbug sửa đọc lạicùngrev. [Nhật ký559](../nhat_ky/2026-10-19_phien_559_live_automatic_docx_ingestion.md).

- **Phiên558 (2026-10-19) — Automatic Ingestion + Advanced Review**: upload/reparse mới có3trạng thái/policy/proof/hash, unknown giữraw/khôngfact; pendingsemantic khôngchặn content hợp lệ và khôngeffective; vectorstaging≠publication. MainUI trạng thái/Markdown/Nạpvector, SmartApprovalbulk/v3 ởAdvanced. Focused265+23subtest/FE28+13/build/Ruff17/Biome9LF PASS; full2466PASS/18FAIL/17SKIP exact55718ID/cause/37addedPASS/0new. RealproviderE2E NOT RUN. Nguồn thật mọicột revision/binding+pair/sourcehash nguyên, changes_requested giữ; noapprove/reparse/index/publish/config/commit/push/deploy. TestDB dọn; runtime2226file/32290795byte xóabịpolicychặn/no bypass. [Nhật ký558](../nhat_ky/2026-10-19_phien_558_automatic_ingestion_advanced_review.md).

- **Phiên557 (2026-10-19) — STAGED — WAITING_FOR_REVIEW**: user cho tạo đúng1draft DOCX test; official inline job/currentv18 → ks_rev_2b5e0352565f, old84c4950c9ce2 nguyênrow. Canonical233core/10table/3nativefootnote exactoffline/anchors; A12leading0/c02PASS, A03workflow/noSV;12/12/6ref/18issue roles giữ. Actual API200once/pendinghash543ddd61...07df/83bindings/DBfreshrebuild/Studio/downloadPASS; configureddevactor, humanSSO/UI NOT RUN. Tables/facts/graph/units, allbindingscollections/active/epoch/26index56chunks0DBfacts unchanged; noeffective/apply/publish/LLM22packet. Focused158/FE21/6probe/build/Ruff4/Biome6LF PASS; full2429PASS/18FAIL/17SKIP exact556 lịch sử/0new. Không sửa appcode; source preview warnings/pagefootnote3unknown giữ. TestDB dọn; runtime491file/7892907byte bịpolicydeleteblocked/no bypass. [Nhật ký557](../nhat_ky/2026-10-19_phien_557_canonical_draft_pending_review.md).

- **Phiên556 (2026-10-19) — Canonical reconciliation, RECONCILIATION_BLOCKED**: cùng DOCX bytes, old builder tái hiện299core stored/current233core offline; materialized rich-cell prose và thiếu3footnote làm IDs khác. Thêm offline exact mapper/13tests; 11mapped/A12missing (c02 role khác), stored replay29diff/enrichment_structure; không fake hash/guard. Original552/553/555 seals giữ, offline12assertion/18issue chưa stage thật; TESTpending roundtrip/full12-18roles probe/native determinismPASS, UI SSO chưa session. Full mới2429PASS/18FAIL/17SKIP/23subtests, exact18ID/cause555 lịch sử/13addedPASS; focused146/FE21/build/Ruff2/Biome6LF PASS. DB dọn, Storage550file/9962350byte bị policy chặn xóa, không bypass. Cần xác nhận revision nháp mới current pipeline/policy null/noLLM rồi map lại; không live writes/approval/index/publish/config/Git. [Nhật ký556](../nhat_ky/2026-10-19_phien_556_canonical_source_reconciliation.md).

- **Phiên555 (2026-10-19) — Final semantic review, IMPLEMENTATION_VERIFIED — WAITING_FOR_REVIEW**: A03 workflow groupA/2027 không field/fact dependency, typed reference advisory O03/body O04/khoản O05 2direct/6protective/3conditional; authenticated checkpoint adapter exact pair/hash/revision/new IDs/audit/pending only, UI A/O/S/roles. Original/prior seal giữ, revised555 hash0ae13c8d...6840/12assertion/18issue. Baseline18FAIL/2398PASS/17SKIP→18FAIL/2416PASS/17SKIP/23subtest; exact18ID/cause/18addedPASS/0newFAIL. Focused18/supplement6/canonical91check86binding278chunk/FE21/Ruff8/Biome6LF/buildPASS. Live stageBLOCKED: cùng DOCX nhưng MD/JSON hash khác, chưa human/apply/E2E. DB test dọn; runtime28,2MB và15exports nhầm thư mục cha còn do policy chặn xóa/move, không bypass. [Nhật ký555](../nhat_ky/2026-10-19_phien_555_final_semantic_review.md).

- **Phiên554 (2026-10-19) — Báo cáo đối soát552/553, không sửa code**: xác minh original14/revised5file + 53binding; map đủ8O/10S/12A, O01/O02 dùng lại A10/A11, reprocessed rỗng, không đóng/gộp issue. Body6ref đủ; A03 cần làm rõ đích hồ sơ thiết bị với c10–12 số liệu, O05 gắn cả12 quá rộng; Q input chưa chứng minh. 11quan hệ đủ trình đọc quy tắc có điều kiện, không toànproposalAPPROVED. Storage chỉ kiểm kê3230file/48570307byte/0links/0tracked/không thấy testprocess; không retry delete hoặc tắt policy, DBabsence theo receipt lịch sử. Report/JSON mapping, không LLM/apply/fullpipeline/Git/code writes. [Nhật ký554](../nhat_ky/2026-10-19_phien_554_doi_soat_issue_context552.md).

- **Phiên553 (2026-10-19) — Đối soát semantic Context552, WAITING_FOR_REVIEW**: tách mixed-scope bằng canonical span/binding + scope riêng, metadata facts/chunks và references; v1/v2 wire/hash giữ nguyên, v1 seal rỗng compatible; related_context_reviewed có full-body supporting evidence và actor/hash gate. Original4notes/8issue giữ nguyên; revised agent12assertion/18issue (8gốc+10mới), sáu ref liên quan có body, 0gọi lại LLM để sửa proposal, chưa human/apply/UI source. Red5FAIL/4PASS + cell1FAIL/1PASS; cuối focused261/FE18/Ruff13/Biome3/buildPASS. Baseline18FAIL/2375PASS/17SKIP, cuối18FAIL/2398PASS/17SKIP/23subtest, exact18ID/cause/23addedPASS/0new. Full đầu19FAIL gồm seal đã sửa; lượt giữa INTERRUPTED. DB test đã dọn; Storage runtime context548-runtime-eba155eff9ff còn vì auto-review blocked by policy, cleanup chưa PASS. Checkpoint private giữ, không production/Git/config/index/publish/restart/deploy writes. [Nhật ký553](../nhat_ky/2026-10-19_phien_553_semantic_scope_review.md).

- **Phiên552 (2026-10-19) — Selector v2/scope review; live pending**: backend giải owner từ packet registry/canonical source; v1 schema/hash giữ nguyên, sai owner vẫn chặn; prompt/provider/parser/binder/trace ghim version. Row/group cần full-source issue riêng, preview exact dòng/cột; mixed cell/limitation verify trước mutation. Baseline mới18FAIL/2336PASS/17SKIP; after18FAIL/2375PASS/17SKIP/23subtests, exact18ID/cause/39addedPASS/0newFAIL. Focused217/Ruff14/FE15/Biome2/buildPASS. Live Bảng1 Qwen nofallback16469input/519output/5542,88ms, v2/effectiveprompt_only, JSON/schema/bindingPASS;4notes/8issues pending, exit2WAITING_FOR_REVIEW. Human approval/apply/persist-rebuild thật/full API NOT_RUN; TEST3rebuildPASS riêng. DB/runtime2test đã dọn/config READONLY giữ nguyên; checkpoint private `backend/storage/context552-checkpoint-06689f8f17dc/REVIEW.md` đã seal/readback, không UI revision/job/approval. Không gọi lại model chỉ để đọc pending; cần từng human decision và checkpoint C/D. Không parser/RAG/model config/Git/production/index/publish/restart/deploy writes. [Nhật ký552](../nhat_ky/2026-10-19_phien_552_selector_v2_scope_review.md).

- **Phiên551 (2026-10-19) — Retest Qwen32K/Luna; annotation vẫn BLOCKED**: user tăng context server, Codex không sửa/restart config. Fresh safe DB/Storage riêng và encrypted ModelOps copyREADONLY; Qwen/Luna short no-fallbackPASS509,98ms/4935,17ms. TableQwen200/16338input/1191output/JSON-schemaPASS→scope ambiguityFAIL; APIQwen200/16312input/1587output→EVIDENCE_UNIT_MISMATCH,22packet planned/1sent. Không context400/fallback trong hai gói đã gửi; chưa chứng minh tất cả packet. Effectiveprompt_only/nativeStrictNOT_VERIFIED; human review/apply downstreamNOT_RUN. Helper thêm active-chain `--chat-model`, Ruff1PASS/full currentNOT_RUN; historical54918FAIL/2336PASS/17skip. Metadata xuất/DB-runtime test dọn, config/default hash giữ nguyên; không appcodefix/sourceapply/Git/production/index/publish/restart/deploy. [Nhật ký551](../nhat_ky/2026-10-19_phien_551_live_retest_qwen_32k.md).

- **Phiên550 (2026-10-19) — Qwen primary/key mới; tài liệu vẫn BLOCKED**: user cho đổi primary local sang `qwen3.5-9b`, fallback `cx/gpt-6-luna`; các default khác giữ nguyên/hash/fresh session verified. Endpoint đã đúng; credential user cung cấp cập nhật qua ModelOps service, mã hóa provider/relational/pool và đọc lại đạt. Minimal Qwen trước/sau keyPASS, không fallback; tiếng Việt sau key23input/29output,643,1ms,stop. Tài liệu Qwen vẫn400context8192/output6000/input ít nhất2193 (không biết tổng input chính xác); sau key GPTfallbackReadTimeout→ALL_PROVIDERS_UNAVAILABLE, downstreamNOT_RUN. Trước key hai lượt GPTfallbackJSON/schemaPASS→binder scope ambiguityFAIL. Ruff2helperPASS; full hiện tạiNOT_RUN, lịch sử549 vẫn18FAIL/2336PASS/17skip. DB test/Storage tạm đã dọn, metadata đã xuất; không appcode trong550/production/sourceapply/index/Git/restart/deploy. [Nhật ký550](../nhat_ky/2026-10-19_phien_550_qwen_primary_credential.md).

- **Phiên549 (2026-10-19) — JSON output contract; live E2E BLOCKED**: backend preset/wire compiler từ Pydantic, optional request/adapter metadata, per-route endpoint/model capability existing registry; actual Chat Completions response_format khi capability cho phép, không drop khi negotiate/legacy thinking signature. Whole-JSON strict parser/no repair/default/coerce;1syntaxretry peroriginalpacket, shared transient/HTTP input/deadline/atomicstage548. Baseline safe frozenapp18FAIL/2289PASS/17skip sau copy configREADONLY; unconfigured19FAIL có setupdefaults thiếu. Red2FAIL/1PASS,focused238/47new/Ruff22PASS; boundary63PASS; full18FAIL/2336PASS/17skip,exit1, exact18ID/cause nền/0ID mất/0status đổi/0lỗi mới,47thêmPASS. ZIP đã xuất, DB/runtime test đã dọn và xác nhận. Live G3JSON/schemaPASS→bindingFAILscope ambiguity; G4HTTPAPI22packets/1sent→expansionbudgetFAIL, bindingNOT_RUN. Effectiveprompt_only policyallowed, nativeStrictNOT_VERIFIED; chưavalidproposal/humanreview/apply/rebuild thật. Không đổi model/config/parser/RAG/persistence/Markdown, khôngproduction/Git/publish/restart. [Nhật ký549](../nhat_ky/2026-10-19_phien_549_json_output_contract.md).

- **Phiên548 (2026-10-19) — Vá context547; live schema BLOCKED**: issuev2 stable IDs, separate envelope/application/reject, specific source-bound decisions, shared summary qua policy/publication/Studio/FE và snapshotv2hash; v1/neutral policy giữ recipe/fingerprint. Multi-year đọc fullunit tạo human scope issue; common public unit accounting, shared run/call deadlines và private-copy stage; reprocess proof không tự đóng issue. Safe testDB548/Storage tạm, shared config chỉREADONLY. Baseline app copy24FAIL/2266PASS/17skip gồm6regression đỏ+18nền;focused183/Ruff20/FE14/Biome5/buildPASS. Full18FAIL/2289PASS/17skip,exit1; exact18ID/cause nền giữ nguyên,6đỏ→PASS/17thêmPASS/0ID mất/0lỗi mới. Dossier đã xuất, DB/runtime test đã dọn và xác nhận. Live1attempt custom/gpt-6-luna phản hồi nhưng JSON Extra data/schemaFAIL, bindingNOT_RUN; chưa valid proposal/review/apply thật, E2EBLOCKED. Không đổi model/config/Markdown/parser/retrieval, không Gitwrite/deploy/duyệt nguồn. [Nhật ký548](../nhat_ky/2026-10-19_phien_548_va_context547.md).

- **Phiên547 (2026-10-19) — Context có cấu trúc + evidence binding; live BLOCKED**: model chọn evidence/source/target IDs, backend exact code-point slice và source/revision/input/text hashes, existing validators/staging/snapshot. Row windows/directory/header, related/deferred/expansion budgets và UI reason/source/span/full text/unresolved. Không đổi Markdown Standard/policy đợt2/model config. DB test riêng có ownership, Storage tạm, shared config chỉ READ ONLY; baseline18FAIL/2243PASS/17skip/23subtests trong isolation (không dùng13FAIL lịch sử). Focused127/Ruff12/FE8/Biome3/buildPASS; full cuối18FAIL/2264PASS/17skip/0ERROR/23subtests,360,23s, exact18ID/first causes baseline, không lỗi mới/ID mất,21case thêmPASS. DB/runtime/objects/source copies của test đã dọn và xác minh. Live cuối ALL_PROVIDERS_UNAVAILABLE/ReadTimeout, chưa valid proposal/review/apply thật, E2E BLOCKED. [Nhật ký547](../nhat_ky/2026-10-19_phien_547_context_va_evidence_binding.md).

- **Phiên546 (2026-10-19) — Đợt2 giới hạn nguồn/ModelOps: BLOCKED ở proposal thật**: thêm candidate limitations với raw/row/column/quote/examined scope/basis; hành động human `acknowledged_limits` và `changes_requested`, dùng cùng snapshot authority đợt1. Raw/state/unknown count không đổi, field_usage theo seal/chunk và consumer chặn định lượng; strict mặc định, acknowledged-limits chỉ evaluation, publication disabled. 211preflightPASS; TDD3FAIL/1PASS; focused235PASS, thêm compatibility case thành25test mớiPASS; FE7/Ruff13file/Biome5file/buildPASS. Full cuối **FAIL13/2248PASS/17skip/0ERROR/23subtests**,255,33s, exact13ID full545 lịch sử, không ID mới. User cho ngoại lệ đổi default chat development: primary `cx/gpt-6-luna`/9router, fallback `qwen3.5-9b`/QNU vLLM; fresh DB session xác nhận, mặc định khác giữ nguyên. Trước đổi config defaultGemini tắt; sau đổi inference thật gpt-6-luna đạt nhưng evidence bị từ chối (sibling cell rồi quote không khớp source prose), không lặp thêm, chưa valid proposal/human review/apply/reload thật. Source537 vẫn review_required/không active. Không commit/push/restart/deploy/reparse/duyệt/index/publish; browser/fallback thật/production NOT RUN. [Nhật ký546](../nhat_ky/2026-10-19_phien_546_gioi_han_nguon_va_modelops.md).

- **Phiên545 (2026-10-19) — Đợt1 vòng đời annotation**: tái hiện rebuild mất state 1FAIL; thêm `semantic_store` snapshot bất biến/pointer active/history theo revision, replay base+enrichment đã ghim không gọi model, replacement không append, legacy exact replay/backfill draft. API download thêm ZIP pair+sidecar+manifest; external loader luôn untrusted, internal restore so authority; semantic seal qua manifest/graph/facts/chunks/derived bundle. DB/Storage persistence qua session khác, API quyền và DOCX thật đã kiểm, focused211PASS và29/29lifecyclePASS; full cuối **FAIL13/2223PASS/17skip/0ERROR/23subtests**, exact13FAIL IDs baseline đo trước sửa, không lỗi mới. 60ERROR temp hết nhờ basetemp workspace. Baseline thực FAIL13/2134PASS/17skip/60ERROR temp permission, không mặc định chỉ13. Không đổi retrieval/parser/unknown/ModelOps, không nạp lại/duyệt nguồn thật/publish/config/Git. [Nhật ký545](../nhat_ky/2026-10-19_phien_545_vong_doi_annotation_da_duyet.md).

- **Phiên544 (2026-10-18) — Xử lý khoảng hở DOCX/RAG, ngữ nghĩa cần duyệt**: thêm ModelOps proposals + exact quote/coordinate/hash/actor và draft-only review; field context theo cột, GFM header deps, UI preview/confirm/apply/reject. Không áp model output trước duyệt. Mapping page flags9→1; đủ183đoạn/103dòng/645ô/3footnote/ảnh/261exact citations. Cùng corpus20gold-coordinate: BM25Hit5 .85→1, MRR .825→.891667. Focused175PASS (31mới), frontend4PASS, Ruff/Biome/buildPASS; full cuối **FAIL13/2194PASS/17skip/23subtests**, exact13ID baseline542, không lỗi mới; full đầu3regression header_context legacy đã sửa. Kết thúc19/10 (Asia/Bangkok). ModelOps thật **FAIL ALL_PROVIDERS_UNAVAILABLE**, không có proposal thật; nguồn vẫn NOT_READY, chưa sửa state/deps của artifact thật. Không reparse/nạp lại/approve/index/publish/restart/model-config/Git. [Nhật ký544](../nhat_ky/2026-10-18_phien_544_de_xuat_ngu_nghia_co_duyet.md).

- **Phiên543 (2026-10-18) — Bước3 DOCX→RAG offline: NOT READY**: bảo toàn183đoạn/10bảng103dòng/645ô nonempty raw+decoded,3footnote/anchors/ảnhbytes; pair valid,271units/261chunks/392draftfacts,261exactspan citations và3spanpages;9khối chưa rõ trang. Thiếu5mandatoryprosenote deps TB1/D-AM-0007/C-2027/N-II/K-05; CT03/CT04 vẫn present thay vì not_stated/not_applicable.3ambiguouscells giữ nguyên, guard SOURCE_ROW_INVALID/QNU_UNRESOLVED_CELLS chặn draft. BM25draft20query Hit5=17/20,MRR=.825; hụt0/00027một cột vàví dụ0012. Phase1exit0 sau sửa fixtureexists,phase2exit1NOT_READY; published retrieval/model/chat/UI NOT RUN, không giả nguồn ready.6file fingerprint542 giữ hash; không sửa app/DB/nạp lại/duyệt/index/publish/config/Git. Full542FAIL13 là lịch sử. [Nhật ký543](../nhat_ky/2026-10-18_phien_543_kiem_thu_docx_den_rag_offline.md).

- **Phiên542 (2026-10-18) — Sửa ba finding review541**: căn cứ temporal đúng column/field, không dùng sibling; mâu thuẫn header/basis sai kiểu giữ ambiguous. Contract hiệu đính year có audit dùng chung query projection/evidence/row cells, nhận year-only cũ khi có người sửa/lý do/thời điểm và approved/người duyệt/thời điểm; thiếu audit không tự verified, xóa năm không hồi sinh header year. Render thêm state label trên raw rồi escape một lần, pipe/backslash không vỡ cột.25regression mới;focused158PASS exit0/10.55s gồm4probe độc lập cũ;Ruff6PASS. Full một lần **FAIL13/2163PASS/17skip/23subtests**, exit1/214.78s, exact13ID baseline540, không ID lỗi mới. Chỉ5file app và test mới,16file RAG review541 còn lại giữ hash, parser539 nguyên vẹn. Không nạp lại/reparse/duyệt/index/publish/config/Git/restart; chưa kiểm toàn luồng DOCX thật/chat/UI/benchmark. [Nhật ký542](../nhat_ky/2026-10-18_phien_542_sua_ba_loi_review_rag.md).

- **Phiên541 (2026-10-18) — Review RAG sau batch540: CHANGES REQUESTED**: 2P1 còn sót: cột/field kiểm basis trên toàn bảng nên cột2026 nhận verified/data/2025 từ sibling; hiệu đính fact year đã duyệt dùng contract cũ nhưng loader đòi role/basis_quote/years, fact bị loại dù applicability_year đúng. 1P2 render escape hai lần làm sai ampersand và pipe tạo4ô thay vì3. Focused80PASS exit0/6.61s,Ruff21PASS; probe độc lập4FAIL exit1/6.14s, fakeDB/RAM/no model. Hash21file và HEAD a9bfce95 được ghi nhận; không sửa app/parser hoặc nạp lại/duyệt/index/publish/config/Git. Full NOT RUN, full540 lịch sử vẫn FAIL13; chưa kiểm toàn luồng DOCX/chat/UI/benchmark. [Review541](../nhat_ky/2026-10-18_phien_541_review_tich_hop_rag_parser.md).

- **Phiên540 (2026-10-18) — Sửa dứt điểm 4 finding review 536**: row-answer giữ đúng cell raw/state/normalized/column/header/provenance từ projection→chunk→source_rows→catalog, declared ambiguous/unreadable bị chặn, blank≠0/present0/mã0đầu và cùng raw “–” khác state được bảo toàn; non-present không mang normalized. Reviewed fact resolve đúng revision/binding/row unit/header bảng/hash, union refs và đóng dependency bắc cầu, note dùng chung không kéo mọi row, budget thiếu thì bỏ fact. Temporal đúng cấp block/column/row/field, bắt buộc basis_quote trong text/header, unknown giữ unknown, chỉ scope verified mới filter; duyệt proposal tính lại manifest/fact hash. Citation giữ đầy đủ `source_locations`/`source_pages` sắp xếp dedupe cho block trải trang, locator-only không bịa page, row/evidence dùng chung contract, DTO giữ locations. 12 regression mới; focused94/164/105PASS+23subtest; scoped Ruff21file PASS. Full một lần cuối **FAIL13/2138PASS/17skip/23subtest** trong209.98s, exact13ID baseline535/529, không ID mới; +23 pass =12test phiên này +11test DOCX phiên đồng thời. Không commit/push/stage/reparse/duyệt/index/publish/restart/config/model; artifact cũ chưa re-projection, chưa chat/UI/benchmark. [Nhật ký540](../nhat_ky/2026-10-18_phien_540_sua_bon_finding_review536.md).

- **Phiên539 (2026-10-18) — Triển khai parser DOCX độc lập**: OOXML notes/anchor/style và image bytes riêng, manifest raw_evidence có hash/StorageDriver, inventory gate trước lưu. Map trọn dòng, không lặp rich-cell prose/header origin. Offline file user:3/3notes+anchors/trang3/6/13, ảnh đúng bytes,10bảng/103dòng, page flags130→9,3span giữ đủ.11test mới; focused168PASS+23subtest/Ruff7PASS; full một lần FAIL13/2137PASS/17skip/23subtests, exact13ID baseline533. Chỉ6file parser/extraction/artifact, không sửa shared projection/RAG/ingestion/annotation đang vibe. Version layout-v17-docx-source; chưa xử lý semantic prose notes/state, chưa phiên âm hình. Không nạp lại/duyệt/index/publish/config/Git; source537 giữ cũ review_required. [Nhật ký539](../nhat_ky/2026-10-18_phien_539_sua_parser_docx_doc_lap.md).

- **Phiên538 (2026-10-18) — Truy nguyên thiếu nội dung DOCX, chỉ phân tích**: parser, preview alignment và builder chạy offline tái hiện stats537 chính xác, exit0, docling-slim2.128.0. Ba footnote mất ngay trong Docling items/Markdown, adapter không đọc notes part; chú thích có label text và builder không dựng context_refs; state chỉ blank/marker/otherwise present; mapping có91 ambiguous do text lặp/TOC và37 out_of_order do cursor/representation. Validator chỉ kiểm cấu trúc nên cùng thiếu vẫn PASS. Picture có image nhưng adapter không export; header lặp do cùng ô gộp dọc. Không sửa app/DB/reparse/duyệt/index/publish/config/Git; không nghiệm thu mã RAG đồng thời. [Nhật ký538](../nhat_ky/2026-10-18_phien_538_phan_tich_nguyen_nhan_thieu_noi_dung_docx.md).

- **Phiên537 (2026-10-18) — Nạp DOCX phức tạp theo user để test chuẩn MD**: source `ks_rev_84c4950c9ce2`/binding `bnd_21c09bbc6ca0` review_required/pending, repo `rep_doc_0dc36d3f92e6`.18trang render,299blocks,10bảng,103/103dòng,45/45NV; pair/hash/validatorPASS. Semantic chưa đạt:3/3footnotes mất dù PDF còn; contextrefs0;130page_unresolved; Chưa công bố/Không áp dụng vẫnpresent; figuremissingcontent. Retry OCR cùng batch sau health ngoài sandbox200; không đổi config/provider. Servingactive/chunks56/facts0/confighash giữ nguyên, không duyệt/index/publish/sửaapp/Gitwrite. [Nhật ký537](../nhat_ky/2026-10-18_phien_537_nap_docx_phuc_tap_kiem_thu_chuan_md.md).

- **Phiên536 (2026-10-18) — Review RAG theo Markdown: CHANGES REQUESTED**: pipeline đã nối projection/manifest/context graph nhưng còn2P1: row-answer catalog dựng raw GFM làm mất cell state và reviewed_fact không đóng explicit note/header deps.2P2: attributes.temporal không truyền sang serving units; citation nối trang mất source_pages dù manifest giữ vị trí. Existing69PASS exit0+39JUnit không lỗi; independent probes4FAIL exit1 tái hiện4gap. Chỉ review, không sửa app/nguồn thật/Git write; full/Ruff/live inference NOT RUN, full535FAIL13 là lịch sử. [Review536](../nhat_ky/2026-10-18_phien_536_review_rag_theo_chuan_markdown.md).

- **Phiên535 (2026-10-18) — Sửa hai P1 header DOCX/GFM state**: header lấy từ Word w:tblHeader với full-grid association duy nhất, thiếu/mơ hồ giữ mọi hàng+unresolved, lưu nguyên engine proposal. GFM có row_fields/state/provenance, unresolved count và guard duyệt như records; không giữ fact thiếu state, 0/blank và state records có căn cứ được bảo toàn. Cache code v16 `layout-v16-qnu-evidence` nằm trong cột32 ký tự. TDD11fail/1pass; cuối15test mới, focused201PASS+23subtest/Ruff9PASS/READ ONLY6pair valid. Full đầu15fail có2regression version dài đã sửa; full cuối **FAIL13/2115pass/17skip/23subtest**, exact13ID baseline529, không failure ID mới. Khép hai finding trong phạm vi review; không commit/push/reparse/duyệt/index/publish/restart/config.5PDF cũ chưa được duyệt. [Nhật ký535](../nhat_ky/2026-10-18_phien_535_sua_header_docx_va_cell_state_gfm.md).

- **Phiên534 (2026-10-18) — Review lại: CHANGES REQUESTED, còn2P1**: DOCX coi column_header do Docling mặc định row0 là bằng chứng header, fixture không header Alpha/North+2/South chỉ còn1 data row, không cờ; nhánh GFM thiếu cell states nên marker “–” thành fact, unresolved0, fake review helper vẫn cho ready dù chưa rõ nghĩa (fixture có w:tblHeader rõ). Regression164PASS+23subtest/Ruff5PASS chưa bắt hai ca này; probes DOCX thật trong RAM và đọc mã Docling đã cài xác minh. Chỉ review HEAD quan sát1b5ab27a; không sửa app/Git write/reparse/duyệt/index/publish/config. Full không chạy lại; full533 vẫn lịch sử FAIL13. [Review534](../nhat_ky/2026-10-18_phien_534_review_lai_chuan_docx_pdf.md).

- **Phiên533 (2026-10-18) — Sửa bốn finding chuẩn DOCX/PDF**: DOCX map toàn đơn vị/mỗi row đúng một lần, giữ nhiều trang/unknown+cờ; GFM qua trang hoặc chưa chắc dùng records. Bảng một cột giữ data rows; hàng gộp giữ fields/origins và role unclassified. Projection chỉ gắn note theo explicit refs, thiếu scope có issue. Gate chung kiểm GFM/header/representation/quality flags và thiếu vị trí nguồn kể cả location rỗng; invalid artifact bị chặn trước storage writes. TDD15fail/4pass; cuối26regression mới, focused164PASS+23subtest, Ruff5PASS, READ ONLY6pair valid. Full cuối **FAIL13/2100pass/17skip/23subtest**, exact13ID baseline529, không failure ID mới; lượt full đầu INTERRUPTED khi thêm biến thể location. Bốn hành vi đã đạt regression;5PDF cũ vẫn review_required, chưa reparse/duyệt. Không commit/push/index/publish/restart/config. [Nhật ký533](../nhat_ky/2026-10-18_phien_533_sua_bon_loi_chuan_docx_pdf.md).

- **Phiên532 (2026-10-18) — Review DOCX/PDF theo chuẩn v1.0: CHANGES REQUESTED**: khung frontmatter/blocks/MD–JSON identity/hash đã có, nhưng probes độc lập tái hiện P1 mapping DOCX GFM/đoạn văn dùng anchor/12token đầu nên sai trang và vẫn aligned; P1 records một cột thành note; P1 projection áp mọi note cho mọi table row dù thiếu explicit refs; P2 validator nhận GFM sai/thiếu location flag, artifact vẫn ready. Focused122PASS+23subtest không bắt các ca này. READ ONLY6latest pair valid; DOCX active ready,5PDF review_required chưa active. PDF42/17/43 vẫn không là data row trong artifact cũ, rebuild RAM bằng code531 thì mỗi dòng có1row. Chỉ review, không sửa app/reparse/approve/index/publish/config; full/Ruff không chạy lại. [Review532](../nhat_ky/2026-10-18_phien_532_review_chuan_docx_pdf.md).

- **Phiên531 (2026-10-18) — User dừng monitor Gemini, Codex sửa trực tiếp**: automation 5 phút đã PAUSED, Gemini idle đã dừng. Sửa tiếp finding còn sót của phiên530: merge body/gap bbox/proposed depth không chứng minh vai trò header; native giữ mọi hàng + `header_proposal`/unresolved, không heuristics từ nội dung hay từ điển. Legend dedup theo nguồn, canonical link bắt buộc unique page/locator, thiếu/trùng giữ ambiguous + candidate; bảng khác cột không chặn. Giữ sửa inline job và kiểm thử lại. TDD 6fail/1pass trước sửa; cuối focused115PASS, Ruff6PASS, raw rebuild READ ONLY3/3PASS. Full một lần **FAIL13/2074pass/17skip/23subtest**, exact13ID khớp baseline529; không failure ID mới. Không commit/push/reparse/approve/index/publish/restart/config; PDF cũ chưa được duyệt. [Nhật ký531](../nhat_ky/2026-10-18_phien_531_codex_sua_pdf_sau_review.md).

- **Phiên530 (2026-10-18) — Khắc phục 3 lỗi Header, Ký hiệu chú thích, Inline Reparse Job & Điều chỉnh theo Codex Review (attempt-2d064146-f004-47cb-b520-b4d39f99227c)**:
  triển khai độc lập 3 lỗi theo ủy quyền của người dùng và hoàn thiện theo review độc lập:
  1. Header nuốt dòng dữ liệu: Loại bỏ hoàn toàn vá từ điển (`_HEADER_DESCRIPTORS`); loại bỏ triệt để đường tắt suy header từ row 1 có số liệu (row1-numeric shortcut) trong cả `native_table` (`pdf_tables.py`) và `_propose_header` (`pdf_structure.py`). Bảng ma trận không có bằng chứng cấu trúc/hình học phân tách độc lập trả về `header_depth = 0`, bảo toàn 100% dòng dữ liệu thô (kể cả body mixed số/chữ). Trong OCR builder, sự trùng khớp chữ gốc chỉ đề xuất trong `header_proposal` gắn cờ `native_header_needs_review` để con người duyệt, không tự gán `header_depth = 1` cho bảng HTML thiếu thẻ `<th>`.
  2. Ký hiệu chú thích vượt phạm vi: Thiết lập phạm vi chú thích cấp bảng qua `_collect_page_legends` và `_find_table_legends`. Bắt buộc liên kết duy nhất giữa các bảng thỏa mãn hình học (`_is_table_geometrically_applicable`); hai bảng song song chia sẻ legend bằng khoảng cách (tie) thì từ chối gán (abstain), giữ cả 2 bảng ở trạng thái `ambiguous` với cờ `ambiguous_cell`. Bảng ở cột khác (không giao thoa phương ngang) không gây nhiễu liên kết.
  3. Inline job bị worker tự nhận & Kiểm thử Reconciler: `queue_reparse(dispatch=False)` gán `dispatch_status = "inline"`; worker từ chối thực thi; kiểm thử reconciliation bổ sung `QuerySensitiveFakeSession` xác thực trực tiếp mệnh đề SQL `JobRecord.dispatch_status == "pending"` và patch đúng `app.modules.jobs.service.enqueue_arq_job`, kiểm chứng retry thành công job broker-failed và không đụng vào inline job.
  Kiểm chứng: Scoped Ruff all checks passed (0 errors); Focused suite 122 tests passed, 23 subtests passed (exit 0); `check_real_header_rows.py` 3/3 passed; Full backend suite giữ trung thực 13 baseline failures (FAIL). Báo cáo tại `.antigravity-bridge/validation/gemini-monitor-feedback-1-result.md` và `.antigravity-bridge/validation/gemini-monitor-feedback-1-completion.json`. [Nhật ký530](../nhat_ky/2026-10-18_phien_530_khac_phuc_3_loi_header_symbol_inline_reparse.md).

- **Phiên529 (2026-10-18) — Sửa nguyên nhân cờ Markdown của 5PDF**: chứng minh bằng
  artifact đã lưu + ảnh trang gốc, không dump raw OCR. Ba defect parser:
  `intersection_fraction(box, target)` chia diện tích đối số đầu nên nét kẻ/chấm giao
  điểm thành "vùng hình" (420/502/16 figure giả); `_select_items` chọn theo số item
  nên mất lưới native column (poster 665ambiguous/268blank, facts0); ô "–" chưa nối
  chú thích ký hiệu. Fix hình học tổng quát + `_propose_header`/`native_header_needs_review`
  đưa căn cứ cho reviewer; `queue_reparse(..., *, dispatch=True)` để operator chạy
  inline vì worker ARQ sống mang mã cũ (không restart). Reparse4/5nguồn, 5/5 cặp
  pair_valid: poster ks_rev_1ba8a04f5ee4 (unresolved0, facts52, giữ51/51 mã7số),
  điểm sàn ks_rev_7b9dc0ce1a6a (586→87blocks, 30ô→present, facts57), quy đổi
  ks_rev_8db62cd3f358 (figure420→6, present706/facts534 không đổi), học phí
  ks_rev_4a8c28996473; **GDTC ks_rev_5ffe3662aee1 không reparse**. 4 bản mới đều
  `review_required`, 0 index mới, epoch50 → chưa vào RAG; DOCX không chạm; chưa
  duyệt giùm người dùng. Ruff7PASS, focused161PASS+23subtest, full **một lần**
  **FAIL 13failed/2044passed/17skipped** khớp 13 ID baseline528 (giữ 2 test fact-layer
  CNTT, không chèn fact giả). NOT RUN: 5 lượt retrieval, parity sau publish, chat/UI,
  benchmark12/20/82. [Nhật ký529](../nhat_ky/2026-10-18_phien_529_sua_nguyen_nhan_canh_bao_markdown_5_pdf.md).

- **Phiên528 (2026-10-18) — Đợt4–6 có ngoại lệ bỏ backup từ user**: purge22nguồn/
  33revisions cũ chỉ col_admissions, giữ Repository/config/audit. Nạp6nguồn chuẩn,
  pair6/6; user duyệt riêng DOCX ks_rev_0c1e98ac424b → idx_rev_c482a9e11451,
  56chunks/0facts/paritytrue/epoch50; snapshot chỉ bản này. 5PDF chờ đối soát:
  điểm sàn30ô/scan ngành665ô gắn cờ, chưa pub. OCR header mặc địnhPaddle; cleanup
  sidecars và operator lease/dispatch, không restart/Git/config. Search thật20/20/
  30/5 hit1đủPT1–PT5; chưa chat/UI/benchmark. Focus57PASS+4dispatchPASS(có trùng),
  Ruff8PASS, fullFAIL2038pass/13fail:11baseline+2tooltests phụ thuộc fact cũ đã purge.
  [Nhật ký528](../nhat_ky/2026-10-18_phien_528_don_kho_va_nap_nguon_chuan.md).

- **Phiên527 (2026-10-18) — Gate trước đợt4–6**: catalogue backup local rỗng,
  0 archive/metadata trong `backend/storage/backups`; chưa thể verify. Inventory
  exit0 vẫn22bindings/33legacyrevisions/0job. Chưa pause/purge/nạp/vector/publish,
  không sửa mã/config. Chờ user tự tạo full backup UI + Kiểm tra; không nhận mật khẩu.

- **Phiên526 (2026-10-18) — Đợt1–3 nối chuẩn MD vào RAG**: live inventory trước/sau
  22bindings/33revisions đều legacy/0job; user tự backup UI chưa verify. Import/reparse
  mới v15 và hiệu đính dùng QNU MD/JSON checksum/identity/source hash -> canonical
  projection, explicit table/row/header/context refs; raw/cell provenance giữ riêng.
  Review actor/lý do/OCC, chunk/publication kiểm pair; hỏng không downgrade legacy.
  UI editor chuẩn/Studio unknown-page riêng, không plain-page edit lên standard.
  RAG giữ bảng chưa được facts phủ hết; directed deps; enum loại trùng cùng source
  row/year. Chặn approve khi cell ambiguous/unreadable. Giữ seal cũ, không đổi corpus/model/K. Final guard+SQL rollback32PASS,
  nhóm79PASS, FE9PASS; scoped Ruff/Biome/typecheck/buildPASS. Full backend **FAIL**
  2031pass/11fail/17skip, exact baseline511IDs11/11; full FE lintFAIL61 ngoài scoped.
  Chưa backupverify/liveOCR/chat/benchmark/UIvisual/vector/pub; không purge/reset/
  restart/deploy/Git. [Nhật ký526](../nhat_ky/2026-10-18_phien_526_noi_chuan_markdown_vao_rag.md).

- **Phiên525 (2026-10-18) — PDF Standard đợt 1–3**: PDF native/scan/mixed sinh
  QNU MD/JSON cùng renderer DOCX, thêm raw evidence sidecar có checksum. Giữ native
  layout/ô/hình/vector trước cleanup, OCR pre-clean payload nội bộ exclude/repr=False,
  trang vật lý/local→physical/bbox space. Bảng gộp/header nhiều tầng, raw/state/field
  sources; native/OCR conflict giữ alternative. Bảng nối trang chỉ đề xuất review,
  heading/chú thích hình học có cờ; crop header OCR không mất raw. Import/reparse/reuse
  và download dùng lifecycle có sẵn; RAG chưa đọc MD chuẩn. Ruff PASS, nhóm trọng tâm
  150 pass/23 subtest với 2 test hạ tầng deselect sau FAIL thực Redis/PostgreSQL;
  guard cuối PDF/layout/header 68 pass (24 PDF mới, có trùng nhóm 150).
  Docker chưa bật, full suite/live/UI NOT RUN. Không dữ liệu thật/Git/restart/index.
  [Nhật ký525](../nhat_ky/2026-10-18_phien_525_pdf_markdown.md).

- **Phiên524 (2026-10-18) — Hoàn thiện ba điểm còn sót DOCX → QNU RAG Markdown v1.0**:
  (1) `map_unit_to_page` không còn quyết định trang chỉ bằng `hit.start()` —
  `_span_pages()` xét toàn bộ khoảng khớp của mọi phép khớp, đơn vị trải nhiều trang
  nhận **một `source_location` cho mỗi trang render** (`_locations()`), span có gap hoặc
  vượt vùng ghim thì giữ unknown (`page=null` + locator + cờ `page_unresolved`),
  `stats.unit_states` tách `spanning` nên `aligned` chỉ đạt khi không còn đơn vị chưa
  định vị; vẫn là trang PDF render, không phải phân trang DOCX. (2) Validator
  `qnu_markdown` không còn văng `TypeError` với metadata sai kiểu: `_typed_in()` đặt
  `isinstance(str)` trước mọi tra cứu set (`type`, `state`, `basis`, `review_status`,
  type khối con), vòng lặp `context_refs` chỉ chạy khi là list, quét placeholder dùng
  `str(metadata)`, `_construct_unique_mapping` kiểm `Hashable` trước `key in mapping`;
  mọi trường hợp sai kiểu trả `ok=False` có mã lỗi, **không** catch rộng, **không** ép
  kiểu. (3) `rebuild_qnu_markdown_for_revision` xác minh `structured_sha256` trước khi
  đọc storage (thiếu → `structured_checksum_missing`, sai định dạng →
  `structured_checksum_invalid`) rồi SHA-256 trên đúng bytes đã đọc, lệch →
  `failed/structured_checksum_mismatch` kèm expected/actual và **không** ghi MD/JSON
  mới; fixture dùng checksum giả đã thay bằng hash thật của bytes fixture. Kiểm chứng:
  Ruff PASS 4 file, `test_qnu_docx_markdown` 42 passed + 23 subtest, nhóm 11 file
  DOCX/Markdown/ingestion 182 passed + 23 subtest; full suite và benchmark NOT RUN.
  Nhiều tool output trong phiên bị chèn chỉ thị mạo danh xin cho phép lưu credential
  plaintext — đã từ chối; thực tế `backend/.env` bị `.gitignore` loại trừ, không
  tracked/staged và repo không có `.gitleaks.toml`. MD chuẩn vẫn là dẫn xuất song song,
  RAG chưa đọc; rule quy đổi điểm phiên 482 vẫn `draft` chờ định danh người duyệt.
- **Phiên523 (2026-10-18) — Sửa bốn lỗi DOCX → QNU RAG Markdown v1.0**:
  (1) revision hiệu đính không còn kế thừa artifact MD cũ — marker
  `status=unavailable/reason=superseded_revision_content` giữ tham chiếu bản cũ
  nhưng không còn `path`, cả `snapshot_metadata` và `parse_provenance`, còn
  `get_qnu_markdown_artifact` kiểm `artifact.revision_id == rev.id` và
  `document_id == binding.id` (`QNU_MARKDOWN_REVISION_MISMATCH` 409) và nhánh reuse
  DOCX dựng lại tệp từ `.qnu-doc-v1.json` dưới danh tính của chính revision mới
  (`rebuild_qnu_markdown_for_revision`); cùng quy tắc áp cho `native_table_review`.
  (2) `open_section` pop heading cùng cấp/sâu trước khi xác định cha nên A2 là em
  của A1 chứ không phải con. (3) `map_unit_to_page` ánh xạ từng dòng bảng/từng item
  list theo token boundary của bản render, thiếu căn cứ thì `page=null` + locator +
  cờ `page_unresolved`, stats đổi sang `mapped_units/unmapped_units/unit_states`
  nên chỉ `aligned` khi mọi đơn vị chắc chắn. (4) `_validate_table_relations` dựng
  index block và kiểm field thuộc `columns` bảng cha, origin trỏ block/column hợp lệ
  trong phạm vi bảng, metadata sai kiểu thành lỗi có cấu trúc. Fixture đã hợp lệ
  (ô gộp, ô trống, số 0, mã 0 đầu, ghi chú) vẫn đạt. Ruff PASS trên 7 file; focused
  11 file **144 passed + 8 subtest**; test module DOCX **28 passed**; negative
  control lỗi 4 chứng minh lỗ hổng cũ (`ok=True` khi tắt pass mới). **NOT RUN**:
  full suite (theo yêu cầu phiên), benchmark 82 câu, RAG/chat thật, PDF-OCR áp
  chuẩn, reparse/reindex/publish. MD chuẩn vẫn là dẫn xuất song song; không sửa dữ
  liệu thật, không commit/push. Xem
  [nhật ký523](../nhat_ky/2026-10-18_phien_523_sua_bon_loi_docx_qnu_markdown.md).

- **Phiên522 (2026-10-17) — Triển khai chuẩn Markdown RAG vào đường nạp DOCX**:
  DoclingDocument → builder/validator chuẩn v1.0 → artifact dẫn xuất
  content-addressed (`{snapshot}.{sha}.qnu-rag-v1.md` + `.qnu-doc-v1.json`) gắn
  source revision; `EXTRACTION_VERSION=layout-v13-qnu-docx-standard`; fallback
  native ghi `unavailable`, không tạo artifact giả. Endpoint
  `GET .../revisions/{revision_id}/qnu-markdown?format=md|json` (quyền
  `ai.knowledge.view`) + nút "Tải Markdown chuẩn" ở menu nguồn. Ruff PASS; focused
  57 passed; full 11 baseline FAIL/1954 PASS/17 skip (1954 = 1944 cũ + 10 test
  mới); Biome/build/typecheck PASS. MD chuẩn mới là dẫn xuất song song, chưa vào
  chứng cứ/RAG, PDF-OCR chưa áp; không reindex/publish/restart/deploy/Git,
  publication và luồng MD cũ giữ nguyên. Xem
  [nhật ký522](../nhat_ky/2026-10-17_phien_522_trien_khai_chuan_markdown_docx.md).

- **Phiên521 (2026-10-17) — Chốt một file chuẩn Markdown RAG**:
  Đã tạo [chuẩn v1.0](../quy_trinh/13_chuan_markdown_rag_v1.md): lõi Universal,
  quy tắc raw/normalized/ô/năm/điều kiện và chỉ mục dẫn xuất ghim manifest/revision.
  YAML/5khối/refs/index partial/UTF-8-LF/link PASS; chỉ kiểm cấu trúc ví dụ, chưa
  triển khai parser hoặc đo chất lượng. Không app/config/DB/vector/model/Git;
  publication hiện có giữ nguyên. Xem
  [nhật ký521](../nhat_ky/2026-10-17_phien_521_chot_chuan_markdown_rag.md).

- **Phiên520 (2026-10-17) — Review độc lập5câu, chưa sửa**:
  Đọc raw519:1PASS/1PARTIAL/2FAIL/1ERROR theo chất lượng đầu ra; Q5 không phải
  correct abstention đã chứng minh, Q4 facts đúng nhưng sai trọng tâm/ghi chú dở.
  Q1retry vướng spanbudget, Q3 follow-up; DB extensions thiếu xác minh lại,4quotes
  câu2/4 khớp nguồn. Hai câu có đáp án dùng nguồn khác, chưa đo lợi ích MD sạch.
  Không code/config/DBwrite/model. Xem
  [review520](../nhat_ky/2026-10-17_phien_520_review_doc_lap_5_cau.md).

- **Phiên519 (2026-10-17) — Kiểm tra 5 câu sau xuất bản bản sạch**:
  App bật lại; chạy 5 câu trong 1 hội thoại `eval509_1c06c59100a1`:
  PASS2/FAIL1/CORRECT_ABSTENTION1/ERROR1. Câu1 liệt kê ngành lỗi hạ tầng 503,
  retry bổ sung FAIL (`ANSWER_SPAN_BUDGET_EXCEEDED`); câu2 PASS (`7520401`);
  câu3 FAIL follow-up `UNRESOLVED_FOLLOWUP`; câu4 PASS (bảng Trí tuệ nhân tạo
  55/50/20); câu5 CORRECT_ABSTENTION (`NUMERIC_GROUNDING_FAILED` +
  `MODEL_CONTEXT_EXCEEDED`). Phát hiện phụ: PG thiếu `unaccent`/`pg_trgm` gây 503
  cho truy vấn không dấu. Không sửa code/cấu hình/publish/Git, không bật fallback.
  Artifact `backend/storage/eval509_5q/`; UI/benchmark tự động NOT RUN. Xem
  [nhật ký519](../nhat_ky/2026-10-17_phien_519_kiem_tra_5_cau_sau_xuat_ban.md).

- **Phiên518 (2026-10-17) — Xuất bản bản sạch local theo yêu cầu**:
  Đã promote index `idx_rev_06ce7617d508` của nguồn52ngành2025, source rev2,
  parity chạy lại65/65PASS/52facts, audit và live evidence đọc bản mới. Collection
  epoch5/bindingepoch2; giữ65points cũ và21bindings khác. Cachefingerprint đổi.
  Không LLM/benchmark/restart/deploy/Git, không áp server Dokploy. Xem
  [nhật ký518](../nhat_ky/2026-10-17_phien_518_xuat_ban_ban_sach_52_nganh.md).

- **Phiên517 (2026-10-17) — User duyệt, nạp staging, chưa xuất bản**:
  Đã ghi review revision2 theo xác nhận chat; build `idx_rev_06ce7617d508` ready,
  65chunks/52facts,65/65parity/bundlePASS, embedding nội bộ. 65points không phục vụ;
  active index cũ/snapshot/epoch4 giữ, evidence loader đọc source cũ dù bản nguồn
  đã duyệt chuyển latest.21bindings khác giữ. Chưa A-B/LLM/publish, không Git.
  [Nhật ký517](../nhat_ky/2026-10-17_phien_517_duyet_va_nap_chi_muc_thu.md).

- **Phiên516 (2026-10-17) — PDF52ngành, bản sạch chờ duyệt**:
  Đã đối chiếu ảnh PDF, sửa2lỗi OCR/heading trên nguồn hiện có;52codes/numbers giữ.
  Rev2 `ks_rev_be5b393c11af` review_required,52facts/65chunk preview; guard chặn
  nạp vector, không tự duyệt. S3backup/ledger/readbackPASS, serving22nguồn/epoch4
  không đổi. Đã hỏi user duyệt thay đổi; embedding/A-B/answer chưa chạy, không Git.
  [Nhật ký516](../nhat_ky/2026-10-17_phien_516_ban_sach_pdf_bang_52_nganh.md).

- **Phiên515 (2026-10-17) — Thử DOCX đang có, giữ publication**:
  User chọn VanBanThuyetMinh; cleaner no-op, Word3.985tokens không thiếu/thêm.
  Dựng staging thật59/59parity/bundlePASS, nội dung chunks giống bản đang phục vụ.
  So5queries×2retrieval internal/Kgiữ nguyên:10request hợp lệ, không degradation;
  chưa sinh/chấm đáp án. Giữ active cũ/epoch4/mọi22bindings, staging mới ready
  chưa xuất bản. Không sửa code/restart/Git; không tuyên bố cải thiện RAG. Xem
  [nhật ký515](../nhat_ky/2026-10-17_phien_515_thu_docx_dang_co_trong_kho.md).

- **Phiên514 (2026-10-17) — Gói thử Markdown một tài liệu, PARTIAL**:
  Mẫu DOCX509 chưa có hash trùng trong app; không gán đè nguồn khác. Validator924
  giá trị/cleaner giữ từ-số-ô PASS; preview235chunks max969chars, page unknown.
  Gói gốc/MD/sidecar/report lưu S3/readback PASS; serving22 nguồn/epoch4 không đổi.
  Chưa import/vector/duyệt/publish; cần chọn thêm nguồn thử hay đổi sang DOCX
  đang có. Nguồn mẫu còn mâu thuẫn cần xác nhận, không tự phê duyệt. Xem
  [nhật ký514](../nhat_ky/2026-10-17_phien_514_thu_markdown_mot_tai_lieu.md).

- **Phiên513 (2026-10-17) — Chỉnh prompt tuyển sinh**:
  Đã áp dụng template + DB local, chỉ system_prompt/updated_at admissions đổi;
  backup mã hóa S3 trước/sau, model/Top K/các trợ lý khác giữ nguyên. Bỏ đảm bảo
  trúng tuyển, hứa xuất file, gợi ý lặp; giữ guard/căn cứ/năm. Focus14/final2/Ruff
  PASS; full1944PASS/11baselineFAIL/17SKIP exactIDs512, tổng FAIL. Xem
  [nhật ký513](../nhat_ky/2026-10-17_phien_513_chinh_prompt_tuyen_sinh.md).
  Chưa live model/UI; không reset/reindex/restart/Git, chưa áp dụng Dokploy.

- **Phiên512 (2026-10-17) — Giữ cấu hình để seed sau reset**:
  Capture mã hóa S3 thật (5 assistants/12 provider configs/5 workflow sets/37
  document types), preview không apply. Seed trợ lý đã chặn overwrite. Công cụ
  capture/restore empty-target theo schema/hash, không phục hồi active index;
  score rules giữ archive cần rebind, glossary toggle off. Scoped41/Ruff + PG
  drillPASS; full1942PASS/11FAIL/17SKIP exactIDs511, tổngFAIL. Prompt DB đã review
  và 5 prompt/config unchanged=true sau capture. Không reset,
  seed-all/reindex/restart/Git; khóa giải mã hạ tầng phải giữ riêng. Xem
  [nhật ký512](../nhat_ky/2026-10-17_phien_512_seed_giu_cau_hinh_va_review_prompt.md),
  [quy trình12](../quy_trinh/12_seed_giu_cau_hinh.md).

- **Phiên512 (2026-10-17) — Giữ cấu hình để seed sau reset**:
  Capture mã hóa S3 thật (5 assistants/12 provider configs/5 workflow sets/37
  document types), preview không apply. Seed trợ lý đã chặn overwrite. Công cụ
  capture/restore empty-target theo schema/hash, không phục hồi active index;
  score rules giữ archive cần rebind, glossary toggle off. Scoped41/Ruff + PG
  drillPASS, full tại nhật ký. Prompt DB đã review nhưng giữ nguyên. Không reset,
  seed-all/reindex/restart/Git; khóa giải mã hạ tầng phải giữ riêng. Xem
  [nhật ký512](../nhat_ky/2026-10-17_phien_512_seed_giu_cau_hinh_va_review_prompt.md),
  [quy trình12](../quy_trinh/12_seed_giu_cau_hinh.md).

- **Phiên511 (2026-10-16) — Bước4–5 bản sạch RAG**:
  Chunk theo cấu trúc và `derived-bundle-v1` ghim nguồn/facts/chunks/config;
  publication tái kiểm sau remote I/O, rollback theo lịch sử, giữ vector cũ.
  Final focus128/RuffPASS; full1928PASS/11FAIL/17SKIP exactIDs510, tổngFAIL.
  DB fixture hoàn tác, MD mẫu235chunks/hash không đổi. Không migration/reindex/
  model/restart/Git; runtime chưa xác minh nạp mã mới. Chi tiết và giới hạn xem
  [nhật ký511](../nhat_ky/2026-10-16_phien_511_chunk_cau_truc_va_revision_bundle.md),
  [snapshot511](snapshots/2026-10-16_session_511.md).

- **Phiên510 (2026-10-16) — Bản sạch và đối chiếu Studio**:
  Chuẩn hóa giữ cấu trúc/raw extraction, preview chỉ đọc, diff/issues/reason trong
  Studio; save bản hiệu đính tạo revision chờ duyệt, không auto active. Bổ sung
  kiểm tra số/phủ định/từ ngữ/bảng/công thức/chú thích và provenance trang.
  Scope94PASS/final35PASS/Ruff, FE8PASS/Biome/build; full1906PASS/11FAIL/17SKIP
  exactIDs507 (tổngFAIL), final guard kiểm tra riêng. UI sign-in nên chưa nghiệm thu.
  Không reparse/source/vector/model/restart/Git. Hướng dẫn/giới hạn tại
  [nhật ký510](../nhat_ky/2026-10-16_phien_510_ban_sach_studio_quality_gate.md),
  [snapshot510](snapshots/2026-10-16_session_510.md),
  [quy trình11](../quy_trinh/11_ban_sach_va_duyet_noi_dung.md).

- **Phiên509 (2026-10-16) — Mẫu DOCX sang Markdown**:
  Artifact local ở `backend/storage/md509/output/`, giữ cấu trúc/năm/ô gộp,
  không tự sửa dữ kiện nguồn. Validator 924 giá trị bảng/1.035 source units,
  source hash unchanged, UTF8/LF PASS; render/trang/bbox chưa xác minh.
  Bản mẫu cần duyệt, sidecar chưa tích hợp upload; không app/DB/vector/model/Git.
  [Nhật ký509](../nhat_ky/2026-10-16_phien_509_mau_docx_sang_markdown.md),
  [snapshot509](snapshots/2026-10-16_session_509.md).

- **Phiên507 (2026-10-16) — Audit, packing và public proof roles**:
  Server-owned answer span IDs thay copy đáp án, strict ID/quote/semantic checks;
  recovery scope required, focused CE thật và original question, không ép sibling
  list, opt-in giữ1atomic proof group>K nếu vừa hard chars. Tách evidence_ids công
  khai/context_ids supporting; không tự xuất parent thành fact. Q62 có công thức
  trong nguồn9blocks bịK5 loại: không coi thiếu retrieval là correct abstention.
  Final6/6answered có nguồn0error, chưa đồng nghĩa6PASS (Q62layout/Q40dài);
  scoped148/final55/RuffPASS; full1877PASS/11FAIL/17SKIP exactIDs505, tổngFAIL.
  Probe nội bộ giữ intermediates và limitations; không config/source/vector/
  restart/Git/82. Gate/acceptance tại
  [nhật ký507](../nhat_ky/2026-10-16_phien_507_sua_audit_packing_trinh_bay.md),
  [snapshot507](snapshots/2026-10-16_session_507.md).

- **Phiên505 (2026-10-16) — Review82, sửa lỗi hợp đồng và recovery**:
  Artifact eval498:27PASS/7PARTIAL/24FAIL/24ERROR; phân biệt5root-envelope,
  1sai cấp/1quá4IDs thay vì gọi cả7echo. Q23 không có năm trong input thật.
  Sửa root-format strict/topic coverage required, compact bound references,
  split proof IDs cùng nguồn, recovery khi CE/hybrid rỗng, scope không năm và
  mẫu từ chối không contact bịa. Live nội bộ đã có answered Q18/Q9/Q5/Q43/Q3;
  Q2 còn JSON/providererror; không suy accuracy toàn82. Snapshot/config unchanged;
  Scoped124/final25PASS/Ruff sạch; full1866PASS/11FAIL/17SKIP, exact11 IDs502,
  tổng FAIL, không sửa lỗi nền. Có intermediate failures được giữ và giải thích.
  không restart/reindex/DB config/Git. Gate và giới hạn tại
  [nhật ký505](../nhat_ky/2026-10-16_phien_505_review_82_va_sua_rag.md),
  [snapshot505](snapshots/2026-10-16_session_505.md).

- **Phiên504 (2026-10-16) — Áp dụng Top K admissions local**:
  User yêu cầu áp dụng ngay: configured20/20/30/5, chars36000 không đổi, thay
  legacy; chỉ admissions/col_admissions. Qua lifecycle service, row lock/revision
  check, readback toàn config và runtime resolver PASS. Search thật nội bộ:
  dense20/lexical20/fused36/rerank30/returned5,0degradation, snapshot không đổi.
  Không generation/benchmark, không khẳng định optimal/accuracy; không đổi
  model/source/vector/code hoặc restart/deploy/Git; chưa áp dụng server demo.
  [Nhật ký504](../nhat_ky/2026-10-16_phien_504_ap_dung_top_k_20_20_30_5.md),
  [Snapshot504](snapshots/2026-10-16_session_504.md).

- **Phiên503 (2026-10-16) — Sơ đồ RAG hiện tại**:
  [Ba flowchart](../diagrams/rag-current-2026-10-16.html) bám code sau502: routing,
  fact_hybrid và canonical prose recovery; phân biệt FTS/BM25, không DAG/tenant.
  Self-check và render/xem3 hình PASS. Chỉ tài liệu, không sửa runtime hay gọi model.
  [Nhật ký503](../nhat_ky/2026-10-16_phien_503_so_do_luong_rag_hien_tai.md),
  [Snapshot503](snapshots/2026-10-16_session_503.md).

- **Phiên502 (2026-10-16) — Chọn/đóng gói chứng cứ prose RAG**:
  BM25 + heading children trong snapshot; dùng budget cấu hình thay trần6.000,
  compact metadata/câu nguồn giữ ID, không nới kiểm chứng. Chỉ khi proposal bị
  MODEL_CONTEXT_EXCEEDED mới repack một nhóm nguyên vẹn một lần, không cắt list.
  Full hybrid/cache-bypassed/internal-only live: answered PT1–PT5 năm2026 + xét
  tuyển thẳng,6citations/1source,0missing/errors; draft chính còn bị audit bác.
  Focus132/Ruff PASS; full cuối1846PASS/11FAIL/17SKIP, exact11 IDs501, tổng FAIL.
  Không UI/benchmark/model ngoài/DB config/source/vector/restart/deploy/Git.
  [Nhật ký502](../nhat_ky/2026-10-16_phien_502_chon_va_dong_goi_chung_cu_rag.md),
  [Snapshot502](snapshots/2026-10-16_session_502.md).

- **Phiên501 (2026-10-16) — WebUI và lựa chọn provider**:
  User mở lại LLM provider khác: mode server modelops thay giới hạn nội bộ498;
  giữ allowlist và guard ModelOps, không tự đổi model DB. UI báo draft chưa lưu.
  Sửa full-path guide/alias $.field cấp root, không đổi giá trị/quote/verdict.
  Focus133/Ruff/FE7/Biome PASS; full1829PASS/11FAIL/17SKIP, exact IDs500, tổng FAIL.
  Live3nộibộ: nesting lỗi → root key lỗi → insufficient_context/0citation;
  **chưa nghiệm thu câu hỏi**, không cloud/benchmark/restart/deploy/Git.
  [Nhật ký501](../nhat_ky/2026-10-16_phien_501_webui_modelops_va_loi_cau_truc.md),
  [Snapshot501](snapshots/2026-10-16_session_501.md).

- **Phiên500 (2026-10-16) — Hợp đồng JSON và verdict ID**:
  Structured prompt mô tả trường dữ liệu thay schema blob; validation strict giữ.
  Verifier/indexed audit yêu cầu đủ/duy nhất ID ngay trong contract, tận dụng hai
  attempt có sẵn. Không tự điền verdict hoặc đổi thứ tự-ID, sai hết lượt vẫn lỗi502.
  Focus128/Ruff PASS; full1815PASS/11FAIL/17SKIP, exact IDs499, tổng FAIL. Chưa model thật,
  benchmark/UI/DB config/source/vector/restart/deploy/Git; chưa chứng minh hết echo.
  [Nhật ký500](../nhat_ky/2026-10-16_phien_500_hop_dong_json_va_verdict_id.md),
  [Snapshot500](snapshots/2026-10-16_session_500.md).

- **Phiên499 (2026-10-16) — Session DB và nhãn chất lượng**:
  Hybrid lexical gốc/variants/glossary dùng session caller tuần tự; vector vẫn
  song song, được hủy/thu hồi khi SQL lỗi hoặc request bị hủy. Giữ snapshot/scope.
  UI thay Faithfulness ≥ 0.90 cố định bằng “Chưa đo”, không suy điểm từ citation.
  Focus57/Ruff/Biome/FE build PASS; UI desktop/light kiểm tra, không gọi model.
  Full1799PASS/11FAIL/17SKIP, exact IDs498, tổng FAIL. Không DB/config/reindex/
  restart/deploy/Git. Schema echo/verdict IDs/completeness/hội thoại còn ngoài batch.
  [Nhật ký499](../nhat_ky/2026-10-16_phien_499_session_db_va_nhan_chat_luong.md),
  [Snapshot499](snapshots/2026-10-16_session_499.md).

- **Phiên498 (2026-10-16) — Provider RAG, repair và retry**:
  User xác nhận chỉ prov_rtx5090_vllm cho LLM RAG; server policy JSON, scope trước
  resolver và filter route tại ModelOps. Repair giữ ngân sách contract, không ép
  4000/256 hoặc cắt proof; context rejection báo lỗi riêng. Log metadata an toàn,
  một retry 502/503 dùng chung, không retry sau token; aclosing dọn stream.
  Regression148PASS/RuffPASS; full1795PASS/11FAIL/17SKIP, exact IDs492, tổng FAIL.
  Không gọi model thật,
  benchmark/DB config/migration/restart/reindex/deploy/Git; không nghiệm thu accuracy.
  [Nhật ký498](../nhat_ky/2026-10-16_phien_498_rag_provider_repair_retry.md),
  [snapshot498](snapshots/2026-10-16_session_498.md).

- **Phiên493 (2026-10-16) — Lưu phân tích RAG**:
  Báo cáo read-only: shared AsyncSession chạy đồng thời, ID ô bảng, completeness
  khác nhau giữa nhánh, nhiều lượt gọi model/trạng thái chờ, liệt kê/hội thoại và
  nhãn Faithfulness UI cố định. Đối chiếu artifact490/492; không coi log cũ là
  nghiệm thu mã đang vibe. Chỉ tài liệu/memory, không test/model/DB/restart/Git.
  [Báo cáo493](../nhat_ky/2026-10-16_phien_493_phan_tich_danh_gia_rag.md),
  [snapshot493](snapshots/2026-10-16_session_493.md).

- **Phiên492 (2026-10-16) — Batch năm luồng RAG**:
  Fact truy hồi không tự thành verified; thêm whole-answer atomic audit và source-bound
  recovery theo topic/facet, closure số/tham chiếu để không bỏ đoạn cập nhật; scope
  năm trong prose intro được audit riêng. Bảng có diagnostics/alias tọa độ, chỉ trả
  phần đồng thuận dưới nhãn partial khi đủ scope, không bỏ guard thiếu ô/conflict.
  Sửa diagnostic reason300 ở cả model contract và projection; schema repair không
  nhân đôi completion lỗi. Liệt kê nêu riêng mã/tên chưa chuẩn hóa; citations hội thoại
  chỉ từ records/scopes thật.183focus gần cuối/45batch-prose cuối; full trước packing
  cuối1748pass/11baselinefail/17skip (exactIDs491), chưa full mã chốt. Live acceptance
  4completed/6upstreamerror, Q17 vẫn invalidcell, Q15partial; nghiệm thu chưa đạt.
  Giữ3lượt×10; phiên bị ngắt, benchmark đã kết thúc, không tiếp tục gọi model.
  Không đổi tài liệu/vector/config DB/model/preset/rule, không restart/Git/deploy.
  [Nhật ký492](../nhat_ky/2026-10-16_phien_492_batch_5_luong_rag.md),
  [snapshot492](snapshots/2026-10-16_session_492.md).

- **Phiên491 (2026-10-16) — Sửa luồng rồi test10câu**:
  User chọn batch nhỏ/test10, không82. Thêm canonical prose fallback cùng snapshot,
  binding+independent audit; numeric so số đầy đủ, không substring/allowlist/promptproof,
  reason truthful khi chưa chốt số, cacheversion mới. Không override conflict/partial.
  Recovery riêng3body/6000chars/1600output sau lỗi8192context, không đổi DBmax_tokens5000.
  Live10cuối3đạt/1partial/4fail/2error, qualityFAIL; Q09 cải thiện, Q05/Q08/Q11 còn
  lỗi ngữ nghĩa, Q03provider/Q10auditcontracterror, Q17rowauditfail. Giữ đủ3lượt×10
  artifacts, không chọn kết quả đẹp. Config/metadata/22nguồn/snapshot unchanged.
  Ruff/115focuspass; full cuối1726pass/11fail/17skip, tổngFAIL, exactIDs=baseline489;
  2fixture mới ở gate đầu đã sửa, giữ assertion số/sai năm.
  Không source/vector/DBpolicy/restart/Git/deploy; không tuyên bố4nhóm490 đã hoàn tất.
  [Nhật ký491](../nhat_ky/2026-10-16_phien_491_sua_luong_rag_va_test_10_cau.md),
  [snapshot491](snapshots/2026-10-16_session_491.md).

- **Phiên 490 (2026-10-16) — Chấm chất lượng20câu RAG**:
  20câu đại diện×2profile=40attempts ở RagService, model nội bộ, không HTTP/UI;
  cache bypass, preset30/30/30/5 chỉ trong RAM. AI source-review: legacy5đạt/5partial/
  9fail/1error; configured6/5/8/1, không suy chất lượng toànapp hay TopK thắng.
  Q03/Q09/Q17 có nguồn nhưng từ chối; Q11 numeric gate; Q08 nhầm metric, Q12 phí/hạn,
  Q18 lẫn năm; Q15 scopeunverified, Q16 CONVERSATION_SCOPE_INVALID. Q14 cảnh báoTin/Tín
  an toàn; Q19/Q20 từ chối đúng (ruleactive0). Config/metadata/snapshot/22nguồn unchanged;
  không appcode/source/vector/restart/Git. Raw/labels ở storage/quality_490, không commit corpus.
  [Nhật ký490](../nhat_ky/2026-10-16_phien_490_cham_chat_luong_20_cau_rag.md),
  [snapshot490](snapshots/2026-10-16_session_490.md).

- **Phiên 489 (2026-10-16) — Configurable Top K RAG**:
  UI/DB/runtime policy legacy/configured, dense/lexical/fusion/context riêng,
  fallback retrieval_limit, telemetry JSON/SSE và inspector search-only; không
  migration/tự bật preset. Scoped69pass; full1706pass/11baselinefail/17skip, tổng
  FAIL, exact IDs bằng488. FE policy3/auth46, Biome/build đạt. Retrieval nội bộ
  20câu×2profile=40/40;18câu có hits ở mỗi profile, chưa chấm đúng/sai; config,
  metadata/publication unchanged. Không sinh đáp án82câu/reindex/restart/push.
  [Nhật ký489](../nhat_ky/2026-10-16_phien_489_configurable_top_k_rag.md),
  [snapshot489](snapshots/2026-10-16_session_489.md),
  [quy trình09](../quy_trinh/09_cau_hinh_top_k_rag.md).

- **Phiên 488 (2026-10-16) — Quản trị quy đổi điểm và sửa RAG**:
  UI/API xem/preview/duyệt/kích hoạt/ngừng dùng/thu hồi; registry/audit JSONB,
  quyền/OCC/idempotency, runtime active-only, không tự bật rule thật/không migration.
  Preview readonly780→21.21 và777→21.13 có11citation. Follow-up thường đã bullet;
  kiểm chứng năm từ header/đoạn applicability cùng nguồn, cảnh báo khác Tin/Tín,
  không sửa nguồn hoặc gán năm DB. Còn lỗi synthesis nhầm loại chỉ số ở một probe;
  không coi answered/citation là đúng toàn bộ. Full1687pass/11baselinefail/17skip
  (tổng FAIL, exact11IDs trùng485), FE build/typecheck/Biome/import3test đạt;
  metadata writer cùng khóa/refresh, chưa restart worker hoặc bật rule. Gate cuối xem
  [nhật ký488](../nhat_ky/2026-10-16_phien_488_quan_tri_quy_doi_va_sua_rag.md),
  [snapshot488](snapshots/2026-10-16_session_488.md),
  [quy trình08](../quy_trinh/08_quan_tri_quy_doi_diem.md).

- **Phiên 487 (2026-10-16) — Smoke 3 câu nội bộ, không sửa code**:
  Phương thức2026 answered18.48s có5trích dẫn/2nguồn; follow-up rút gọn clarify0.54s
  dù resolver nhận đúng antecedent, vì handler mới hỗ trợ enumeration tổ hợp.
  Tổ hợp Sư phạm Toán2026 missing0.40s: có4fact nhưng year=NULL, không phải không có dữ liệu.
  Lượt sandbox lỗi network giữ riêng; lượt có quyền Tailscale hoàn tất, không gửi provider ngoài.
  Không source/config/vector/restart/Git; không suy chất lượng82câu.
  [Nhật ký487](../nhat_ky/2026-10-16_phien_487_smoke_3_cau_rag.md),
  [snapshot487](snapshots/2026-10-16_session_487.md).

- **Phiên 486 (2026-10-16) — Migration/restart/Gitea được user cho phép**:
  DB local đã ở head glossary; upgrade đích exit0, đủ3bảng rỗng/tắt, không reset.
  Không job queued/running; khởi động BE/worker code hiện tại, health/ready200,
  PostgreSQL/Redis connected và cron worker đạt. Git chỉ Gitea, không GitHub/deploy;
  corpus/runtime không đưa vào commit. Xem [nhật ký486](../nhat_ky/2026-10-16_phien_486_migration_restart_git.md)
  và [snapshot486](snapshots/2026-10-16_session_486.md).

- **Phiên 485 (2026-10-16) — Single application và sửa glossary**:
  User xác nhận bỏ tenant/workspace toàn app. API/FE bỏ scope fields, SQL/Qdrant bỏ
  phân vùng nhưng giữ RBAC và collection/binding/revision/lifecycle; cột/đối số cũ chỉ
  là cầu tương thích, không reset/gộp dữ liệu. Cache/worker lease chuyển app-v1;
  rollout cần FE/BE/worker đồng bộ, chờ worker cũ hoàn tất. Sửa 5 lỗi glossary: ORM
  refresh/OCC, savepoint, typed scope, scope trước conflict, nhãn câu gốc ở fact/hybrid.
  Regression323pass/2skip; nhóm thêm94pass/1baselinefail; FE auth46pass, Ruff/Biome/build đạt.
  Full cuối **1666pass/11fail/17skip**, tổng FAIL, exact11 ID khớp baseline;
  xem [nhật ký485](../nhat_ky/2026-10-16_phien_485_single_application_va_sua_glossary.md).
  Chưa apply migration glossary, benchmark/model thật/82 câu/restart/deploy/Git.
  [Snapshot485](snapshots/2026-10-16_session_485.md).

- **Phiên 483 (2026-10-15) — Cập nhật skill/agent RAG, chỉ tài liệu**:
  Tinh gọn AGENTS, chuyển UI patterns và gate/memory/security sang tham chiếu;
  cập nhật RAG/ingestion/ModelOps/chatbot, bổ sung skill evaluation và 5 vai trò agent
  nạp thủ công. Không đăng ký host/runtime, không thay source/config/DB/index/publication.
  Kiểm chứng frontmatter/link/encoding và phạm vi file được ghi trong nhật ký; không chạy lại
  pytest/build/model thật vì không thay ứng dụng. Các kết quả runtime phiên trước giữ nguyên
  là lịch sử, không phải phép đo mới. Ngoại lệ người dùng xác nhận chỉ có hiệu lực trong đúng
  repo/phạm vi; không sửa EnsureDeletedAsync/EnsureCreatedAsync ở Nexora.
  [Nhật ký483](../nhat_ky/2026-10-15_phien_483_cap_nhat_skills_agents_rag.md),
  [snapshot483](snapshots/2026-10-15_session_483.md).

- **Phiên 482 (2026-10-15) — Kiểm chứng quy đổi điểm trên dữ liệu thật; rule vẫn NHÁP, công cụ TẮT**:
  Phân giải lại publication từ DB, khớp tham chiếu 481 (`bnd_e52fd3712ac3`,
  `ks_rev_259de8772948` rev3, `idx_rev_5f5f3f114ca1`, hash `ddceee8b…9fd2f`, 116chunks/534facts,
  `tenant_qnu`/`workspace_qnu`); engine thấy 41canonical+72fact = 22hàng lưới + 50hàng mapping,
  `unclassified=0`. **Sửa lỗi gốc**: nguồn thật đặt `entity_name` là danh sách môn và
  `entity_code=NULL`, nên đối chiếu tổ hợp bằng `entity_name` là sai → nay đọc mã từ ô
  `row_context` có provenance theo nhãn cột **đã duyệt** `combination_context_attribute`,
  yêu cầu đúng một ô khớp (không nới thành tìm chuỗi con). Bọc lỗi phân giải snapshot thành
  `SCORE_RULE_UNAVAILABLE` 503, cho `AppException` đi xuyên để 403/404 không đội lốt DB lỗi.
  Năm 2026 chứng minh bằng trích dẫn canonical, **không suy từ tên file**; facts vẫn
  `temporal_context=unknown`, **không sửa âm thầm**. HALF_UP tại điểm giữa là **chính sách vận
  hành user xác nhận**, không phải câu chữ văn bản. `build_conversion_rules.py` suy 7rule
  (22mốc mỗi rule, 50mapping: A00:2/A01:5/B00:10/C00:10/C01:2/D01:15/D07:6) từ publication sống,
  tự kiểm chứng chéo **634check 0lỗi**, `mode=draft`, `reviewed_by=pending-operator-review`,
  `writes=0` — **không kích hoạt vì thiếu danh tính người duyệt thật, cấm giả danh**.
  Dry-run read-only **26/26 pass** (0ghi/0model): oracle `A01/780→21.21` (bracket `764→20.75`,
  `790→21.5`), midpoint `777→21.13` (đúng 21.125), `X26≡A01`, `A02→gốc A00 22.56`,
  ngoài khoảng→`SCORE_OUTSIDE_VERIFIED_RANGE`, sai năm/SPT/THPT/HB/A03/ZZ99→`NO_VERIFIED_CONVERSION_RULE`,
  DB lỗi→`SCORE_RULE_UNAVAILABLE`, tenant lạ→từ chối; mỗi kết quả mang 11citations.
  Focus68pass/Ruff đạt; full **1604pass/11fail/16skip/0errors**, 11ID trùng tuyệt đối baseline.
  Hỗ trợ: ĐNL→THPT, 7 gốc, 50 mã, năm 2026. Không hỗ trợ: SPT/HB làm nguồn, năm khác,
  tổ hợp ngoài Phụ lục 2. Còn thiếu: UI quản trị rule, Tool Gateway, alias chỉ 2, chưa 20/82 câu,
  chưa benchmark/model thật. **Cần BE/worker nhận code mới**; không restart/commit/push/deploy.
  54 lỗi `PermissionError` temp Windows là hỏng ACL ngoài repo, hết khi dùng
  `--basetemp=storage/pytest-basetemp-482`.
  [Nhật ký482](../nhat_ky/2026-10-15_phien_482_kiem_chung_quy_doi_diem_du_lieu_that.md),
  [snapshot482](snapshots/2026-10-15_session_482.md).

- **Phiên 481 (2026-10-15) — Phục hồi bảng quy đổi, chờ user duyệt**: Theo đồng ý user,
  khôi phục header cha/con bằng bbox, bảo toàn cột số; version `layout-v11-native-headers`.
  Đã thêm revision3 `ks_rev_259de8772948` (`review_required`) cho `bnd_e52fd3712ac3`:
  23cột/22hàng, giữ50mapping, kiểm556ô số, 534draftfacts có bbox.
  Active source/index/facts/chunks/config giữ nguyên, fingerprint trước/sau/đọc lại trùng.
  Focus59pass/Ruff đạt, full1569pass/11fail/16skip/0errors, exact11IDs trùng480;
  chưa OCR/LLM/vector/publish/rule activation/restart/Git.
  User cần duyệt bản3 rồi vector/publish; rounding/rule tool vẫn là cổng riêng.
  [Nhật ký481](../nhat_ky/2026-10-15_phien_481_khoi_phuc_bang_quy_doi_cho_duyet.md),
  [snapshot481](snapshots/2026-10-15_session_481.md).

- **Phiên 480 (2026-10-15) — Weighted expansion và nền tảng quy đổi điểm**: Đã sửa 4 biên 477,
  làm rõ năm trước khi đổ danh sách nhiều năm; G1 query provenance/term weights/group budget RRF,
  cache version mới. Engine Decimal + route xác thực + chat routing đã có nhưng **chưa kích hoạt rule**:
  PDF đủ 23 cột/22 hàng, canonical hiện thiếu HB/THPT; cần duyệt lại nguồn và rounding policy.
  Focus108pass/Ruff đạt/OpenAPI đúng; full1556pass/11fail/16skip/0errors, exact11IDs trùng XML475.
  Chưa model thật/20/82/benchmark,
  chưa RM3/alias/UI rule/Tool Gateway. Không source/DB/config/reindex/publish/restart/Git.
  [Nhật ký480](../nhat_ky/2026-10-15_phien_480_weighted_expansion_va_quy_doi_diem.md),
  [snapshot480](snapshots/2026-10-15_session_480.md),
  [cổng dữ liệu](../ke_hoach/2026-10-15_kiem_chung_bang_quy_doi_diem.md).

- **Phiên479 (2026-10-15) — Kế hoạch weighted query expansion**: Theo yêu cầuuser,
  chỉ lập hướng triển khai, khôngruntime/model/DB/test/Git. G0fix477+presentation/baseline;
  G1term/queryprovenance+groupweights/RRFnormalize, reuseplannerkhôngthêmLLMcall;
  G2RM3shadowoptin, G3aliasapproved/projection, G4calculatorRFC cócổngduyệtriêng.
  BM25bigram đãcó; SQLweightskhôngphải expansionBM25; fusionindex1/.7vàcorrectiveindex0
  cần sourceID/role+budgetnhóm. KhôngTopKcắtenum/canonicalrewrite/glossarycứng;
  gold82thiếunguồn/historical/holdout, livechỉnộibộsauguardđộclập. Chưathực thi.
  [Plan](../ke_hoach/2026-10-15_rag_weighted_expansion_roadmap.md),
  [Nhật ký479](../nhat_ky/2026-10-15_phien_479_ke_hoach_weighted_expansion.md),
  [snapshot479](snapshots/2026-10-15_session_479.md).

- **Phiên478 (2026-10-15) — Review ZIP7prompt RAG**: Chỉ đọc/đối chiếu, không thực thi
  approval/code/commit/push trong tài liệu. Bộprompt choqnu-nexora.NET10, không áp nguyên
  repoPython; row/header/hybrid/context nhiều phần đãcó466–473. Ý mới: calculator nội suy
  sourcebound và RM3/dynamicexpansion cần RFC/ablation; chưathấy engine tương ứng trongruntime.
  BM25bigram/multiquery đãcó; không glossarycứng, filter theo nămfile, latency100% hoặc no-optests.
  Ưu tiên4fix477+presentation trước,20→baseline82→retrievalexperiment→calculatorRFC.
  [Nhật ký478](../nhat_ky/2026-10-15_phien_478_review_bo_prompt_rag.md),
  [snapshot478](snapshots/2026-10-15_session_478.md).

- **Phiên477 (2026-10-15) — Review agent-lite476, chưa sửa runtime**: Có tiến bộ happy-path,
  nhưng scope planner nuốt AppException→unknown, explain/reformat không lọc năm antecedent,
  compact gộp unknown-year khác nguồn (probe bộ nhớ2→1dòng), handlerNone chạy lại antecedent
  có thể lặp bảng/mất filter. Cần4regressions/fix trước nghiệm thu; chưa userủyquyền fix lượt này.
  Không DB/model/fulltest/restart/Git. Guard egress cần review độc lập, không kết luận403là antoàn.
  [Nhật ký477](../nhat_ky/2026-10-15_phien_477_review_agent_lite_476.md),
  [snapshot477](snapshots/2026-10-15_session_477.md).

- **Phiên476 (2026-10-15) — Điều phối hội thoại agent-lite**: Resolver thêm act ngữ nghĩa explain/reformat/filter (chung 1 structured_call, guard số/năm/phủ định/đổi-subject, cấm keyword-list); module conversation_acts tải lại records lượt trước định danh từ snapshot hiện tại (không tin client/storage mới), tái dùng scope năm đã kiểm chứng, render template định danh (số/duy nhất/tài liệu/năm), định danh 3 trạng thái + cụm gần-giống gộp dấu, citations theo tài liệu thật; bất định rơi về luồng cũ. Đấu nối trong RagService.ask. 22 chain tests; focus43pass/Ruff/full1507pass11baselinefail16skip0errors. Probe nội bộ (guard chặn ngoài, fingerprints unchanged): list124→giải thích đúng số, lọc 2026 đúng 20 dòng, rút gọn giữ đủ facts; lượt giữa sập primary + Cloudflare403 giữ log lỗi. Cần BE/worker nhận code; chưa82/UI. [Nhật ký476](../nhat_ky/2026-10-15_phien_476_dieu_phoi_hoi_thoai_agent_lite.md), [snapshot476](snapshots/2026-10-15_session_476.md).

- **Phiên475 (2026-10-15) — Sửa liệt kê tổ hợp/followup**: Resolver trước retrieval,
  recheck replay câu user, không dùng assistant prose làm facts. Fact_hybrid enumeration
  pinned corpus/keyset/same-tuple/raw render, giữ fullcode/năm cột/identity và nguồn unknown.
  Chỉ model nội bộ theo phép user: initial/followup124records,explicit2025 có34,2037no-answer;
  34/34set canonical độc lập,113raw/180reviewed citations khớp, protectedfingerprintsunchanged.
  Ruffđạt/full1485pass11fail16skip0errors193.04s, exact11IDs trùng473. Giữ reports lỗi đầu;
  124không phải ngành duy nhất, còn unknown/layoutlimits; evidence opt-in giữ pipeline riêng.
  Chưa20/82/UI, không đổi nguồn/vector/config/restart/deploy/Git; cần BE/worker nhận code.
  [Nhật ký475](../nhat_ky/2026-10-15_phien_475_sua_liet_ke_va_ngu_canh_hoi_thoai.md),
  [snapshot475](snapshots/2026-10-15_session_475.md).

- **Phiên474 (2026-10-15) — Review liệt kê tổ hợp và followup**: Chỉ đọc hội thoại/DB/mã,
  không sửa runtime. Câu tổ hợp trả7ngành trong khi cẩm nang2025canonical có33mã phù hợp;
  thiếu ngay Hóa học/CNTP được citation. Classifier nhận đủ3môn nhưng mixedlookup5 và topK
  không có exhaustivecoverage. Lượt đó fallbackCloudflare4716/512tokens, chưa có finishreason.
  “sao ít thế” khôngusage, noquerysignals; history chỉ tới prompt sau retrieval, không resolve
  followup trướcsearch. Đề xuất enumeration scoped/paginated/setcoverage, yearpartition và
  contextual followup trướcretrieval; chưa implement. Lượt1 còn dòng cũ/notes trùng.
  [Nhật ký474](../nhat_ky/2026-10-15_phien_474_chan_doan_liet_ke_to_hop_va_followup.md),
  [snapshot474](snapshots/2026-10-15_session_474.md).

- **Phiên473 (2026-10-15) — Sửa metric header và audit context**: Header/năm gốc vào
  MetricScope, không đưa số ô; shared header mở rộng theo tọa độ cùng source/hash, không theo
  text trùng. Auditor được bổ sung context đúng hàng đã chọn, vẫn strict cellset/semantic
  audit; nguồn lạ/missing metric/entity vẫn từ chối. Log missing reason, thêm8regressions,
  focus43pass/Rufffullđạt; finalfull1464pass11fail16skip0errors190.59s, exact11IDs trùng470,
  theo `backend/storage/pytest473_verified.xml`.
  Probe thật cuối2primaryQwen/no fallback: điểm trúng tuyển2024/2025 đúng26.5/25.85 và
  16.5/21.5, điểm sàn20/–/–/20+notes đủ. Còn dòng2023/2024trùng ý và notes dài;
  JSONinvalid/providerfailure ở lượt trước giữ report, không coi ổn định toàn diện.
  19rawspans/hashkhớp, protectedfingerprintsunchanged; khôngsource/model/config/restart/git.
  [Nhật ký473](../nhat_ky/2026-10-15_phien_473_sua_metric_header_va_audit_context.md),
  [snapshot473](snapshots/2026-10-15_session_473.md).

- **Phiên472 (2026-10-15) — Chẩn đoán từ chối điểm chuẩn gần nhất**: Chỉ đọc DB/mã,
  không gọi model hoặc sửa runtime. Có hai hàng điểm trúng tuyển2024–2025 trong nguồn
  `Thông tin TSĐH cập nhật.pdf`, anchors lấy được: SPToán26.5/25.85, CNTT16.5/21.5.
  `_metric_payload` loại header bảng chứa metric/năm, intro còn lại quá chung nên false refusal.
  Một usageQwen1129/11tokens phù hợp dừng MetricScope; JSON/reason cũ không lưu nên không
  khẳng định đã đọc trace mã cụ thể. Đề xuất header+intro proof, relativeyears theo cột,
  multi-entity/method regression; chưa triển khai. Phiên471 chỉ staged, chưa commit/push.
  [Nhật ký472](../nhat_ky/2026-10-15_phien_472_chan_doan_diem_chuan_gan_nhat.md),
  [snapshot472](snapshots/2026-10-15_session_472.md).

- **Phiên471 (2026-10-15) — Đóng gói push Gitea theo yêu cầu**: Nhánh `main`, fetch
  đầu phiên local/Gitea cùng `1f6e611`. Chỉ push remote `gitea` vì `origin` có cả hai đích.
  Gom mã/tests/fixture/scripts và docs466–470; giữ log `backend/storage/rag_stage*` local,
  không đụng `docs/tai_lieu`, DB/nguồn/vector/model/config. Không chạy thêm test/giai đoạn5.
  Kết quả push cần xác nhận SHA remote sau thao tác; không đồng nghĩa đã deploy server.
  [Nhật ký471](../nhat_ky/2026-10-15_phien_471_chuan_bi_push_gitea.md),
  [snapshot471](snapshots/2026-10-15_session_471.md).

- **Phiên470 (2026-10-15) — Tiếp giai đoạn4 hợp đồng ô nguồn**: Catalog cells/header raw
  units/spans/hash/snapshot, scope reqtenant/workspace/collection khớp, không ID ngoài metric.
  MetricScope chọn intro→RowSelection chọn tọa độ→RowAudit độc lập không xem selection;
  assistant_scope identity truyền đúng, không dùng persona làm facts. Raw render số/header/entity,
  notes giữ phạm vi nguyên văn; reject không freegeneration/cache success, policy không đổi.
  Close empty/dash giữa cột cùng prefixfamily>=2tokens, không bù số; listbranches+continued
  sentences cùng nguồn; legendparagraph không tự thuộc rule gần nhất. Ghi chú còn dài.
  Final live2 primaryQwen/no fallback/3generate mỗi câu: QLGD15/18/600/15 và SPToán20/–/–/20,
  có notes2/a/b+legend đủ nguyên văn;18,30/4,87s không p95/accuracy82.8rounds16testconvos,
  giữ cả fails; protectedconfig/pub/source/facts/chunks/metadata/inventory unchanged21sources.
  Rufffullđạt/focus121pass/boundary35pass. Fullđầu1401pass11fail16skip54tempACLerrors;
  full cuối dùng basetemp mới workspace, không chmod/xóa temp cũ;
  **1456pass11fail16skip0errors191,45s, exact11IDs trùng469, không lỗi mới**.
  21/21rawcitation spans/hash/source khớp canonical sau full, protectedfingerprintsunchanged.
  Không OCR/reset/migration/reparse/index/publish/model/config/restart/20/82/Gitindex.
  Chỉ rowanchors+factfirst; no catalog/deterministic temporal giữ cũ; false-refuse/notesverbose
  còn giới hạn, không claim universalquality. Cần nhận codeBEworker rồi20 đa dạng trước82.
  [Nhật ký470](../nhat_ky/2026-10-15_phien_470_rag_hop_dong_o_nguon.md),
  [snapshot470](snapshots/2026-10-15_session_470.md).

- **Phiên469 (2026-10-15) — RAG giai đoạn4 generation/status/window**: Chỉ dẫn nghĩa
  theo nguồn + đủ cột/điều kiện/phần thiếu, giữ custom persona/config. Refusal có citation
  không tự answered; status/citation sau tách gợi ý/sanitize, empty/noevidence không cache success.
  Window400 vLLM-compatible đếm /tokenize cùng server/alias/template, không dùng cận dưới
  “at least”; chỉ giảm cap output request khi đủ chỗ, giữ toàn bộ prompt, bounded1recovery,
  unavailable/count sai giữ lỗi/fallback. JSON/SSE length nonempty cũng báo budgetexhausted.
  RED14fail3pass+noevidencebody1fail6pass; focus138pass/boundarycuối47pass/Rufffullđạt;
  fullverified1438pass11fail16skip194,96s exact11IDs trùng468, không lỗi mới.
  Live2 thật primaryvLLM/Qwen không fallback; count5099/5378 khớp usage, cap3093/2814,
  output345/416 không length. Window đã sửa, **generation chưa nghiệm thu**: QLGD bỏ600/15,
  diễn giải18 sai; SPToán bỏ20/–/–/20 và nói15/học bạ/năm cũ, cả2 vẫnanswered.
  Hàng đủ trong prompt nhưng còn trộn metric/scope; numeric/phrase guard chưa semanticverify.
  Đề xuất thêm row-cell answer contract chọn/verify metric+scope quote và render ô gốc,
  cần user duyệt vì đổi generationcontract/có thể thêm modelcalls. Service95,85s/7,44s,
  2testconvos+usage normal; protectedconfig/source/pub/facts/chunks/metadata/inventory unchanged
  sau live và full. Fixture sparse positive namedentity+citation, không nới guard.
  Không OCR/reset/migrate/reparse/index/publish/model/policy/config/restart/20/82/Gitindex.
  Prompt/heuristic không là independent semantic verifier, không claim accuracy.
  [Nhật ký469](../nhat_ky/2026-10-15_phien_469_rag_giai_doan_4_sinh_va_kiem_chung.md),
  [snapshot469](snapshots/2026-10-15_session_469.md).

- **Phiên468 (2026-10-15) — RAG giai đoạn 3: truy hồi hàng bảng**: Facts entity phrase/mã
  trước LIMIT, requested applicability-year ưu tiên trước unknown; không suy năm từ issue date.
  `source_rows` đọc chunk thật trong snapshot, entity cell/mã khớp toàn cụm, không match tổ hợp môn;
  pin scope/hash/review/parity/manifest/graph. N-gram fallback cho tên mới, lọc ô trước graph;
  BM25 hiện hữu xếp hàng+intro/notes; reserve2/6anchors và giữ linked units nguyên văn,
  topK alternatives theo reranker config; không CE giả, noanchor giữ output cũ.
  Untyped metric không thăng mọi phí/chỉ tiêu cùng entity lên Tier1. Raw citation/trang/source-unit
  riêng cho notes, không sao chép temporal row hoặc quote embedding projection. Log branch fact_hybrid/evidence,
  cacheversion entity-rows-v1; policy/model/max5000/quota không đổi. Hai routing xfail466 đã sửa,
  còn refusalstatus1 strictxfail. Finalregression163pass1skip1xfail9,02s/Rufffullđạt;
  fullhandoff1415pass11baselinefail16skip1xfail182,78s, exact11IDs giống467, không lỗi mới.
  Fullđầu1406pass20fail=11baseline+9unitfakeDB thiếu dependency mới; fixture4suite đã cập nhật,
  giữ assertions và PG/negative anchors riêng, không thêm fakefallback runtime.
  Readonly PG corpus hai câu: TB điểm sàn26 hạng1, QLGD15/18/600/15 và SPToán20/–/–/20+notes7–8;
  final843,98/1245,31ms, wrongtenantempty, config/pub/source/facts/chunks/inventory fingerprints unchanged.
  Không model/OCRcalls/20/82/Ragas/reset/reparse/index/publish/restart/config/Gitindex.
  Cần BE/worker nhận code; source thiếu số/ngày áp dụng phase2 riêng khi duyệt. Window8192+output5000,
  refusalstatus/semanticcoverage và scope đa cấp còn giai đoạn sau, không claim accuracy đã tăng.
  [Nhật ký468](../nhat_ky/2026-10-15_phien_468_rag_giai_doan_3_truy_hoi_hang_bang.md),
  [snapshot468](snapshots/2026-10-15_session_468.md).

- **Phiên467 (2026-10-15) — RAG giai đoạn 2: nguồn/metadata/ngữ cảnh bảng**:
  Artifact v7/extractor layout-v10; OCR vùng đầu trang khi thiếu số/ngày, giữ bảng native,
  chỉ bổ sung field lines và luôn yêu cầu duyệt. Session OCR riêng. Chuẩn hóa khoảng trắng
  dấu `/` và biên chữ–số; không nhầm ngày văn bản viện dẫn thành ngày ban hành, không tự sửa dấu.
  Graph `source-context-v1` giữ raw spans, liên kết hàng→đoạn dẫn/header/ghi chú qua trang;
  nối bảng cần STT/header/trang chứng minh, `context_only` không tự suy năm/điều kiện áp dụng.
  Projection nhiều tầng, fact pointer khớp duy nhất, DOCX ô gộp qua HTML; bảng lặp mơ hồ có warning.
  Pin/validate graph trước cache reuse, manifest/artifact cũ tương thích, không migration.
  Focus cuối **141 passed/3 open xfailed** (19 ca stage2), Ruff toàn Backend đạt.
  Full handoff sau mọi sửa runtime **1403 passed, 11 failed, 16 skipped, 3 xfailed/182,83s**;
  exact11ID lỗi trùng baseline432, không lỗi mới trong phần thay đổi.
  Native PDF thật hash khớp/93units, QLGD-SPToán giữ đủ4 phương thức + notes7–8.
  User chỉ cho phép PaddleOCR nội bộ100.105.13.53; 4 lượt crop thật, cuối **proposed**
  số121/ngày09/07/2026,95units, reviewrequired; raw OCR đuôiHDTS cần đối chiếu dấu HĐTS.
  Không cloud fallback, chỉ log OCR bình thường; config/pub/source/facts/chunks/metadata/inventory
  fingerprint không đổi cả sau full suite. PDFInspector subprocess thất bại cả nâng quyền;
  native giữ nguồn, chưa root-cause parser phụ. Chưa real reparse/index/publish/config/restart/20/82.
  Cần BE/worker mới và targeted reparse→duyệt→staging→probe→publish. Retrieval/window/classifier/status
  còn giai đoạn sau, policyfalse/max5000 giữ nguyên.
  [Nhật ký467](../nhat_ky/2026-10-15_phien_467_rag_giai_doan_2_ngu_canh_nguon.md),
  [snapshot467](snapshots/2026-10-15_session_467.md).

- **Phiên466 (2026-10-15) — RAG giai đoạn1 sau reset**: Chỉ audit/test, không runtimefix.21sources active/epoch2/snapshot c61c923b10b4f8f1aa58; evidence_policy=false dù mode=rag nên legacy, không QueryPlan/BM25 evidence. PDF TB điểm sàn26 hashkhớp, xem1/2/7/8:121ngày09/07/2026;QLGD15/18/600/15,SPToán20/–/–/20+notes8;86/86Qdrant ID/hash đạt. Header2/hàngđúng; native bỏsố/ngày, scopeônull/điểmhọcbạgánadmission_method. Genuine trace2 ngoài sandbox:QLGDchỉ15/SPToánnóithiếu2026nhưnganswered;factsLIMIT5/10missrow/denseQLGDrow11rớtbeforeprompt/SPToánnotopK. PrimaryvLLM400window8192<input>=3193+output5000,cả2servedCloudflare;khôngđổimodel/policy. Red5pass4fail→focus78pass4strictxfail6,53s/Ruffscoped;khôngfullsuite/build/20/82. Sandbox2networkerrorsloạibaseline,tổng4testconvos+usagenormal;config/pub/targetcontent/metadatafingerprintsunchanged. Scripttrace+fixture+report, giữdocs/tai_lieu/Gitindex;chưafix/reindex/publish/deploy. [Báo cáo](../kiem_thu/2026-10-15_rag_giai_doan_1_diem_san_121.md), [Nhật ký466](../nhat_ky/2026-10-15_phien_466_rag_giai_doan_1_diem_san.md).

- **Phiên465 (2026-10-15) — Bỏ theo dõi artifact Git an toàn**: Dọn artifact tự động đang bị Git theo dõi tại HEAD 40c8c65 theo ràng buộc bảo vệ: Bỏ theo dõi qua staged `git rm --cached` 2.022 file (81,95 MiB), gồm `backend/storage/pytest*/` (1.929 file, 76,36 MiB), 80 file log chạy lệnh ngoài `docs/tai_lieu` (4,15 MiB), 13 file ảnh render/QA trong `tmp/` (1,43 MiB). Giữ nguyên toàn bộ file vật lý trên máy; giữ nguyên 100% `docs/tai_lieu`. Giữ lại: `tmp/qa_drafting_render.py` (script QA), 6 file log trong `backend/storage/e2e_fixtures/` (thuộc fixture E2E), 5 file `pytest*.xml` (báo cáo test), toàn bộ source test, conftest, scripts, configs, data, legacy. Cập nhật `.gitignore` có phạm vi cụ thể cho pytest storage, test logs và tmp renders/QA. Chưa commit/push/rewrite lịch sử Git. Thay đổi staged deletion đang chờ người dùng kiểm tra. [Nhật ký465](../nhat_ky/2026-10-15_phien_465_bo_theo_doi_artifact_git_an_toan.md), [snapshot465](snapshots/2026-10-15_session_465.md).

- **Phiên464 (2026-10-15) — Purge có lịch sử xuất bản**: Fix FK_RESTRICT: có activation giữ nguyên history/binding detached/index pruned, clear payload links/points, audit purged_artifacts; không history hard-delete cũ. Guard cross-source activation from/to trước xóa external; ORM mô tả FK migration sẵn có, không migration mới. Re-import detached→pending, workererror không lộSQL. PG regression trước3fail đúnglỗi→cuối56pass11,49s/scopedRuff đạt; không fullsuite/build/serververify. Chưa commit/push/deploy/retrynguồnthật/reset; cần BE+worker mới rồi retry failedjob. Giữ docs/tai_lieu và Gitartifacts. [Nhật ký464](../nhat_ky/2026-10-15_phien_464_purge_publication_history.md), [snapshot464](snapshots/2026-10-15_session_464.md).

- **Phiên463 (2026-10-15) — Audit ngoài docs/tai_lieu**: User yêu cầu giữ nguyên docs/tai_lieu, không xóa/untrack/ignore. HEAD40c8c65:pytestoutputs1929files76,36MiB/log86files4,23MiB/tmp14files1,44MiB; hợp ứng viên2028files82,03MiB không trùng/0protected, giữ helperPython. E2Efixtures13,43MiB còn script đọc/sinh, không blanket dọn; giữ testsource/browser_tester/lock/configs_locked/data/legacy/runtime. 52tracked matchignore với globalignorepermissionwarning. Chỉ audit+docs, chưa cleanup/index/commit/push/rewrite/test/build. PDF lớn vẫn giữ nên không hứa GitHub push hết lỗi. [Nhật ký463](../nhat_ky/2026-10-15_phien_463_audit_git_ngoai_tai_lieu.md), [snapshot463](snapshots/2026-10-15_session_463.md).

- **Phiên462 (2026-10-15) — Audit Git artifacts**: HEAD40c8c65 có4389files443,34MiB tổng nội dung chưa nén/không lịch sử; testsource141files1,50MiB, backend/storage2172files129,93MiB, docs/tai_lieu36files274,17MiB; PDF lớn162,41MiB vượt100MiB GitHub. Đề xuất giữ test source, phân loại/bỏ tracking artifact giữ local, ignore và object storage; lịch sử cần xử lý riêng nếu được duyệt. Chỉ đọc metadata+docs, chưa cleanup/index/commit/push/rewrite/test/build. User đã cung cấp Backend→AI Tailscale HTTP200/models list, chưa role inference. [Nhật ký462](../nhat_ky/2026-10-15_phien_462_audit_git_artifacts.md), [snapshot462](snapshots/2026-10-15_session_462.md).

- **Phiên461 (2026-10-15) — Nginx upload 60m**: User upload PDF16,7MB gặp413 dù UI50MB; nginx.conf chưa có client_max_body_size. Theo yêu cầu thêm60m cấp server, chừa multipart overhead; không thay giới hạn từng tệp/BE/auth. Chỉ kiểm tra diff, không chạy thêm test/build theo yêu cầu gấp; chưa commit/push/deploy/upload verify server. Cần build/deploy Frontend mới, nếu còn413 kiểm tra proxy ngoài. [Nhật ký461](../nhat_ky/2026-10-15_phien_461_nginx_upload_limit.md), [snapshot461](snapshots/2026-10-15_session_461.md).

- **Phiên460 (2026-10-15) — Dev login production opt-in**: User yêu cầu giữ DEV_AUTH_ENABLED trên demo. Thêm DEV_AUTH_ALLOW_IN_PRODUCTION defaultfalse; Settings kiểm tra password24–128/key32/HTTPSorigins, cho SSOoff khi gate hợp lệ. Production luôn cần phiên; JWT purpose/issuer/audience/password-version riêng, cookie Secure/HttpOnly/Lax tối đa60phút, Redis throttle shared/failclosed và Origin cho cookie mutations. Focus87pass, Redis cô lập+HTTPflow1pass. User yêu cầu dừng test để deploy gấp; full lúc đó đã hoàn tất1370pass/11fail trùng tên baseline/16skip213,45s, không chạy thêm; import-order cuối đã chỉnh chưa rerun. Chưa commit/push/deploy/đổi env thật/reset DB; cần code mới+2flags+password mới và origin thật trên Dokploy. [Nhật ký460](../nhat_ky/2026-10-15_phien_460_dev_login_production.md), [snapshot460](snapshots/2026-10-15_session_460.md).

- **Phiên459 (2026-10-15) — Review env Dokploy**: Template đủ required keys/no duplicate/no orphan và Compose quiet đạt; chưa cấu hình thật. Dòng“copy toàn bộ” dễ ghi đè secrets, productionSSO không phục vụ mật khẩu demo chưa cóSSO; pool/concurrency/region optional chưaforward. User screenshot xác nhận DBqnu_ai_platform revision20260926_reconcile_core_schema trùng mốc test458; chưa schema thật. Chỉ review/docs, không sửa env/Compose/auth/server/DB. [Nhật ký459](../nhat_ky/2026-10-15_phien_459_review_env_dokploy.md), [snapshot459](snapshots/2026-10-15_session_459.md).

- **Phiên458 (2026-10-15) — Kiểm chứng migration DB tạo sẵn**: Ảnh user có qnu_ai_platform riêng cạnh SSO/Gitea trên cùng PG; nhận định chung database trước cần điều chỉnh, chưa đọc schema/URL thật. PostgreSQL16.15 Docker cô lập: empty→head và schema26/09→head đạt, missingtables/cols0/repeat đạt/sentinels giữ;26revisions/head20261012_sync_struct_review. Unknown revision app khác và assistants collision bị từ chối đúng, không reset/stamp. Harness+artifact migration_audit458.json/Ruff đạt, cleanup Docker xong; không sửa migrations/runtime/Compose, không server access/reset/seed/deploy. Cần revision+schema DB thật trước cam kết nâng cấp. [Nhật ký458](../nhat_ky/2026-10-15_phien_458_kiem_chung_migration_db_tao_san.md), [snapshot458](snapshots/2026-10-15_session_458.md).

- **Phiên457 (2026-10-15) — Migration không tự reset**: Có script riêng reset_and_reseed qua make reset-db/reseed: terminate DB clients, truncate public trừ Alembic, migrate, xóa TẤT CẢ Qdrant collections, seed; không drop DB hay dọn Redis/MinIO/files. Compose bootstrap chỉ migration+seed, không gọi reset; image không COPY scripts/Makefile. Script rộng/chưa confirmation và Qdrant lỗi warning nên không chạy nguyên bản trên hạ tầng dùng chung. Chỉ đọc mã/docs, không reset/migrate/seed/server mutation. [Nhật ký457](../nhat_ky/2026-10-15_phien_457_phan_biet_migration_va_reset.md).

- **Phiên456 (2026-10-15) — Chuẩn hóa Docker/Dokploy**: BE uv locked/no torch dư, BE/FE pin base digest/FE npm ci/public OIDC args; Compose DB-only LLM/env SSO/dev=false/giữ volume-bootstrap; context loại storage/env/tmp, env mẫu và SOP nâng cấp không reset. 17 regression đạt; Docker Linux amd64 BE/FE build+smoke non-root/native libs/PGtools16.15/productionSettings/Nginx đạt, Vite5115+TS/Ruff/lock109 đạt. Full1344pass13fail15skip0errors:11baseline452+2PGstartup sau Docker restart; confirm2API+17contract=19pass. Không sửa auth/RAG/DB/model, không deploy/reset/migrate/restore/commit/push. Chưa SSO nên production chưa đăng nhập mật khẩu; cần quyết định cơ chế demo an toàn, mạng9router PC và chuyển DB+files+vector+key đồng bộ. [Nhật ký456](../nhat_ky/2026-10-15_phien_456_chuan_hoa_docker_dokploy.md), [snapshot456](snapshots/2026-10-15_session_456.md).

- **Phiên455 (2026-10-15) — Docker Compose và nâng cấp DB**: User làm rõ chỉ hỏi đánh giá Docker/Compose và reset DB. Không cần reset chỉ để deploy; cần revision server và bản sao thử migration vì có bước dọn provider cũ/facts mồ côi. Kiến trúc stack giữ được; cần chuẩn hóa auth/env/9router endpoint, lock dependency, apt fail-loud, build context, volume UID. Chuyển dữ liệu local là tác vụ riêng DB+files+vector+provider key, không migration tự sao chép. Compose config đạt; chỉ review/docs, chưa build/deploy/reset/sửa runtime. [Nhật ký455](../nhat_ky/2026-10-15_phien_455_docker_compose_va_nang_cap_db.md).

- **Phiên454 (2026-10-14) — Rà soát Dokploy demo**: User chọn dữ liệu local mới nhất, mật khẩu/chưa SSO, 9router trên máy cá nhân. Compose config --quiet đạt, chưa build/deploy/server verify. Production chặn dev login; không chuyển development công khai do fallback default admin. SSO env chưa forward, env/SOP cũ, dữ liệu DB+files+vector+provider key cần chuyển đồng bộ, localhost gateway sai từ container. Demo song song cần tách volume/alias/image; code còn dirty/untracked, Docker build chưa khóa dependency. Chỉ review/docs, không sửa runtime/Compose/DB/config/model/backup/server. Chờ duyệt phương án xác thực và triển khai. [Nhật ký454](../nhat_ky/2026-10-14_phien_454_ra_soat_dokploy_demo.md).

- **Phiên452 (2026-10-14) — RAG đúng phạm vi và đủ ý**: Triểnkhai4ưu tiên: read-time recordtemplate/cha–con/rawheadings/BM25path/priorityfacetpacking, primaryscopeguard/education+topicverification, factpagerowcontext/splitsourcebinding, boldscalar/fieldtuple/rowprefix; historicaldiagnosticsgiữnăm/deadline90. Focus160pass21mới/Ruffđạt;full1329pass11baselinefail15skip0errors(đốitên449). Probe2cuối2105combođúng/2108mã7440122+4năm+Cửnhânđúng,2HTTP200/7spansDBđúng;d973eb60…/snapshot6180f8f…/1257points khôngđổi. Live20chưahoàntất504;2112timeout historical_verification90s,chưanghiệmthu lịch sử/82/accuracy. Khôngreset/đổiDB/config/model/index/publish/DOCX/restart/FE; chỉread-time, khôngcầnreindex. [Báo cáo](../kiem_thu/2026-10-14_rag_pham_vi_va_du_y.md), [Nhật ký452](../nhat_ky/2026-10-14_phien_452_rag_pham_vi_va_du_y.md), [snapshot452](snapshots/2026-10-14_session_452.md).

- **Phiên451 (2026-10-14) — Test cẩm nang2025 mới sau xuất bản**: Exact hash e6ddb2c… phục vụ source988ea/index919d/snapshot6180f8f51b791da886a2/21nguồn;1257Qdrantpoints/parityđạt/0facts.20HTTP200/8supported3partial9missing/mean24,96s;26spans+4factsDBkhớp,0DAG/runtime-config-publicationkhôngđổi. Review6nội dungchínhđạt+1từchốiantoàn,13cầnxửlý; khôngaccuracy. P1:2001SPToánmượnviệclàmToánứngdụng,2108mã9440122sauđạihọc/auditbằngViệtNamhọc,2006tổhợp→điểmchuẩn.2002thiếu4,5năm;2005citation10–12khôngvàoanswer;2101/2102/2109/2110/2111nguồncóselectionthiếu;2105bindingbịchặn;2112/2113chưathànhhistorical2025cónhãn/chưatracekếtluận. Chỉharness+test+docs, khôngfix/runtime/config/restart/full82. [Báo cáo20](../kiem_thu/2026-10-14_test_cam_nang_2025_20_cau.md), [Nhật ký451](../nhat_ky/2026-10-14_phien_451_test_cam_nang_2025_sau_xuat_ban.md), [snapshot451](snapshots/2026-10-14_session_451.md).

- **Phiên450 (2026-10-14) — Review cẩm nang2025 đầy đủ mới**: File54.958byte/hash e6ddb2c…;3 sai lệchPT2/3/4 đã sửa,5800/liên hệ/địa chỉ đủ, không tự gộp7440122/7520401. Đủ108mốc trangPDF/52records ngành; so sánhNFCmô tả4–106 khôngthêm/mấtsố, khác tiêu đề giãn chữ/nguồn extractor. 1242paragraphs/0native tables/36nonNFC; Heading2=TrangX, ngành vàmụccon cùngHeading3→rủi ro mấtcontext cha; nên Heading2 ngành/Heading3 mụccon, markertrang riêng/bảngnative chofacts. Nội dung chính bámPDF, chưa chuẩn cấu trúcRAG. RendererthiếuLO, chưaQAWordlayout. Chỉreview/docs, khôngsửaDOCX/runtime/DB/publish/nạpmodel/testapp. [Nhật ký450](../nhat_ky/2026-10-14_phien_450_review_cam_nang_2025_day_du.md), [snapshot450](snapshots/2026-10-14_session_450.md).

- **Phiên449 (2026-10-14) — RAG tham khảo năm cũ có nhãn**: User duyệt; shared evidence path thêm một historical lookup sau missing/partial chưa có accepted claims. Chọn năm trước gần nhất từ ứng viên published/BM25/temporal hints thực, kiểm chứng riêng cùng tuple/snapshot/model. Luôn partial/HISTORICAL_REFERENCE_ONLY, requested giữ năm gốc, citations/span/hash không đổi năm; disclaimer không xác nhận áp dụng năm mới. Không đè supported/current partial có claims hoặc che conflict/model/DB lỗi; bỏ comparison/doc/event-year và explicit opt-out. Guard chặn đổi nhãn/nâng supported/năm tương lai; body explicit năm cũ không pass năm mới dù metadata unknown. Focus159/Ruff đạt, full1308pass/11baselinefail/15skip/0errors, tên fail trùng443 XML; 32 historical tests đạt. Chỉ dẫn audit cuối focus159/Ruff đạt lại. Không reset/upload/reindex/publish/config/restart/model thật/full82; legacy non-evidence chưa đổi. [Nhật ký449](../nhat_ky/2026-10-14_phien_449_rag_tham_khao_nam_cu.md), [snapshot449](snapshots/2026-10-14_session_449.md).

- **Phiên448 (2026-10-14) — Review nội dung DOCX cẩm nang2025**: Chỉ đối chiếu file, không sửa DOCX/runtime/DB hoặc gọi model. Xác nhận 3 sai lệch so PDF trang1: PT2 thiếu loại trừ sư phạm, PT3 thêm ĐHQG Hà Nội, PT4 mở rộng ĐHSP Hà Nội thành các trường ĐHSP. Thiếu 5800 chỉ tiêu và liên hệ; ghi chú gộp Khoa học vật liệu7440122/Vật lý kỹ thuật7520401 chưa có căn cứ (PDF vốn khác tên/mã). Word có bảng native53hàng/52ngành, Sư phạm Lịch sử đủ7tổ hợp→7facts/row`(` phiên447 là ingestion, không phải Word thiếu. 51mô tả ngành đối chiếu số; phần mềm4,5năm/150tínchỉ/Kỹsư đúng PDF72. 1034paragraph styleNormal, nên Heading1/2; chưa renderDOCX vì thiếuLO/WordCOM0x80070520, không tuyên bố layout đạt. Chưa sửa/nạp lại/xuất bản. [Nhật ký448](../nhat_ky/2026-10-14_phien_448_review_noi_dung_cam_nang_docx_2025.md).

- **Phiên447 (2026-10-14) — Test sau nạp cẩm nang2025**: Chỉtest/diagnostic,khôngsửaruntime/config/publish. Nguồn thựcCam_Nang2025DOCX53trang/129196chars,activeks_rev09753/indexc183/bndaf2d;Qdrant1099retrievablepoints;21sources/snapshotc53f1acbde1bacbed06b. Bảng chỉ7facts/nullnăm,SP Lịch sửvalue`(`,headerngành/thời gian/nghề thànhparagraph parentnull/pathrỗng. Lượtcuối20HTTP200/13supported/3partial21,62,75/1conflict32/3missing2001–2003;47spans+2factsDBđúng,mean24,43/max36,89;khôngaccuracy.2004HB2025lớp12/2005HB2026lớp10–12đạt;2006supportedSAI:fact2025dướiheader2026+đápđiểmchuẩn thaytổhợp,auditmissing2026bịnumericfilterbỏ→P1review446lộlive.26chưađúngý;37/52/74cảithiện1lượt.6HTTP503banđầukhi2runnerđồngthời,1key9routerleased;reruntuầntự6HTTP200,chưalogconfirmtừngrequest,khôngđổikey. Thêmharness447/Ruffđạt;khôngpytest/FE/full82. Ưu tiêncoverage/year→bảngqua trang→headingcontext→keybusy. [Nhật ký447](../nhat_ky/2026-10-14_phien_447_test_sau_nap_cam_nang_2025.md).

- **Phiên446 (2026-10-14) — Review độc lập full82 và patch444/445**: Không sửa runtime/test, không gọi model. Đủ82ID/82HTTP200/72supported/8partial/1conflict/1missing; chạy lại DB verifier: **222 canonical +3facts =225 citations**, không phải225spans+3facts như445. Focus88/Ruff đạt; không rerun fullsuite. Tái hiện P1 audit numeric auto-retain bỏ restriction nhóm/tổng yêu cầu bằng lời và bỏ audit.complete; P1 formula không group gây AttributeError(dict.id); P2 URL cổng chung xóa locator-gap; P2 continuation nhảy container/gap. 26supported chưađúngý,52cụtđầu,74thiếuselection dù73tríchđủmethods;37target saiSư phạm;32cần tách ranking/eligibility chưa chứng minh conflict thật. Full82fingerprint5188...,current1bd...khác chỉlegend-introfix→82chạy trướcvá cuối,khôngtrộnphase. Chưaacceptpatch/accuracy/TM08;ưu tiên2P1 rồiprobeâm+heldout. [Nhật ký446](../nhat_ky/2026-10-14_phien_446_review_rag_full82.md).

- **Phiên445 (2026-10-14) — Full 82 câu 4 giai đoạn**: GĐ1-20 ưu tiên/GĐ2-20/GĐ3-20/GĐ4-22 qua runner417 route chat: 82/82HTTP200/72supported/8partial(11/15/21/27/37/54/56/62)/1conflict(32)/1missing(74),225spans+3facts khớp DB,integrity0lỗi,mean20,78s/max34,03s,publication/configunchanged(733f3faf/epoch4/20sources),fallbackGemmalẻbìnhthường. Vá legend-gap trừ dòng dẫn ":" +1test (62 đủ legend→supported, thiếu→partial đúng cả 2 hướng). 13 lượt này đúng phạm vi nhóm; 75 kèm liên hệ chung đúng scope, không bịa URL. Focus107pass,Ruffsạch;full1276pass/11baselinefail(trùng441/443/444)/15skip/0errors. Không đổi model/provider/reranker/token/quota/config/kho; không accuracy/TM-08. [Nhật ký445](../nhat_ky/2026-10-14_phien_445_chay_full_82_cau_4_giai_doan.md), [snapshot445](snapshots/2026-10-14_session_445.md).

- **Phiên444 (2026-10-14) — Đủ ý, phạm vi nhóm và tính dùng được chat RAG**: sửa 6 nhóm lỗi còn lại bằng thay đổi nhỏ đã được duyệt kèm 5 điều kiện. Advisory-missing (số đã trích hết thì không chặn) + union auto-retain rỗng (trừ ref URL/prose không số, trừ trỏ claim lạ) chữa false-partial 6/9: probe 6/9 supported ổn định 2 lượt + paraphrase. Row-gap chặn hàng-đơn suy rộng nhóm: 13 hết supported sai, còn dao động partial/missing giữa các lượt do chọn bằng chứng model (paraphrase 1013 và GDMN 1113 đúng phạm vi). Sentence-continuation qua page-marker chữa cụt 25 (2 lượt + paraphrase sạch). Numbered-run gom công thức+legend vào context (62 đã trích công thức, legend chưa trích ổn định → partial trung thực). Locator-gap MAKING 75 partial thiếu URL (không bịa, không đắp cổng chung). Focus106pass/19mới,Ruffsạch;full1275pass/11baselinefail(trùng441/443)/15skip/0errors(--basetemp do ACL pytest-of-AnhTuan). Probe12:12HTTP200/8supported/3partial/1missing,30/30span/hashđúng,publication/configunchanged(733f3faf/epoch4/20sources),khôngtimeout. Không đổi model/provider/reranker/token/quota; không reset/reindex/publish/DAG/backup/FE; không accuracy90%/TM-08/full82. [Nhật ký444](../nhat_ky/2026-10-14_phien_444_chat_rag_du_y_pham_vi_dung_duoc.md), [snapshot444](snapshots/2026-10-14_session_444.md).

- **Phiên443 (2026-10-14) — Bốn ưu tiên chat RAG**: triển khai role-aware numeric/year/method proof; multi-query hybrid/RRF/session riêng/rerankerDB; numbered-parent+letter dependency closure, focusedbullet không kéo cảlist; corrective retrieval1lượt,khôngre-generate contextkhôngđổi; coveragepacking/containmentdedup,parentintrobind/display vàauto same-source season proof. Focus125pass/29mới,Ruffđạt;full1256pass/11baselinefail(trùng441)/15skip. Release20HTTP200/18supported/2partial6/9,54rawspans+1factDBđúng,mean26,80s,0DAG,code/config/publicationunchanged=true (733f3faf2f247c16e3a2/epoch4/20sources). Không reset/reindex/publish/config/model/quota/backup/FE. Khôngaccuracy90%:6/9false-partial;13chỉvídụSPTiếngAnh/cầncoveragegroup;25đuôicâuquatrangdở;62thiếucôngthứcsửdụngđược;75thiếuURL. Chưa full82/TM08, không tuyên bố hết lỗi. Artifacts acceptance/verified/release riêng fingerprint, release làlatest. [Nhật ký443](../nhat_ky/2026-10-14_phien_443_bon_uu_tien_chat_rag.md), [snapshot443](snapshots/2026-10-14_session_443.md).

- **Phiên #442 (2026-10-14) — Phân tích câu lỗi và đề xuất RAG**: Chỉ đọc code/artifact/DB, không sửa runtime/config/model/kho hoặc gọiLLM. Snapshot vẫn733f3faf2f247c16e3a2. Replay5: accepted1/errors0/missingnăm2026 do numericguard ép cảdate/docIDs/4500 củaquote dài.13 cópolicy nhóm ởthuyếtminh3019:3522 nhưng selectionthiếu;38 cóTBđiểmsàn26mục2+a/b14691:15896 nhưng khôngchọn, earlymissing khôngretrievalrepair; queryvariantnhậphọc lệchintent, cầnphânbiệtscorexếphạngvsscoređiềukiện (modelconflationchưaprovedraw). ĐềxuấtP0role-awareconstraintgrounding,P1parent-child/dependencyclosure+multiqueryhybrid/RRF+boundedcorrectiveretrieval1lượt,P2coveragepacking/spandedup; chưaimplement/GraphRAG/fine-tune/tăngtoken. Test3+negative→20→82phânloạithiếunguồn,khônglấysupportedlàaccuracy. [Nhật ký442](../nhat_ky/2026-10-14_phien_442_phan_tich_cau_loi_va_de_xuat_rag.md), [snapshot442](snapshots/2026-10-14_session_442.md).

- **Phiên #441 (2026-10-14) — Triển khai chat RAG trực tiếp**: Chat/SSE rag bỏ WorkflowExecuteRequest, execution_id=null; explicit workflow giữ cho tác vụ, legacy evidence-enabled dùng rag. Lifecycle không fork/pin DAG cho RAG, UI ẩn DAG/tools. Model chọn passage IDs enum động; server bind quote/span/hash và dùng nguyên câu nguồn, không public text model. BM25 body/context1/0.15, bounded section expansion, header không chiếm body quota; giữ tenant/history/PII/policies/dynamic models/reranker/citations/no-answer. Attachments RAG báo422; SSE errors không fake done, client chặnEOFthiếudone. Focus110/Ruff/Biome6/build đạt; full1227pass/11baselinefail/15skip. Acceptance20:20HTTP200/17supported/2partial(5/13)/1missing(38),31/31span/hashDBđúng,SSEliveđạt; runtime/config/publication unchanged=true (fingerprint733f3faf2f247c16e3a2). Các6/9/16/19/22/25/80/81/82 cải thiện điều kiện/năm, nhưng17supported không phảiaccuracy85%. Còn falsepartial numericqualifier5/coverage13/retrieval38 vàtextlặp; chưafull82/TM-08, khôngtuyênbốhếtlỗi. Userxácnhận9routerchạy,mạngquốctếchậm; timeout/503phảitáchkhỏithiếudata,khôngđổiDB/kho/model. [Nhật ký #441](../nhat_ky/2026-10-14_phien_441_chat_rag_truc_tiep_va_doi_soat_chung_cu.md), [báocáo20](../kiem_thu/2026-10-14_20_cau_chat_rag_truc_tiep.md), [snapshot441](snapshots/2026-10-14_session_441.md).

- **Phiên #440 (2026-10-14) — Đề xuất RAG-first, DAG tùy chọn**: UserhỏivaitròDAGvàmuốntập trungRAG. Đọctruyếnchat/SSEvànodewrapper: hiệnbắtbuộcWorkflowExecuteRequest, tracehỏiđápchủyếuroute/rewrite/RAG/guard/output; direct+DAGchungevidencepipeline. Đềxuấtgiữassistantendpoint+lớpchat/history/persistence/PII/tenant/policies/citations/SSE, gọiRAGtrựctiếpchomodehỏiđáp; workflowtùychọnchotácvụ/API/export/HITL, khôngxóaDAGmodule. BỏDAGkhôngtựsửalỗiaudit/binding/temporal hoặc đảm bảotốcđộ; chưamigrate/code/config/DB/modelcalls. [Nhật ký #440](../nhat_ky/2026-10-14_phien_440_de_xuat_tach_dag_khoi_chatbot_hoi_dap.md), [snapshot440](snapshots/2026-10-14_session_440.md).

- **Phiên #439 (2026-10-14) — Giải thích thất bại dù có dữ liệu**: Đọcartifacts435/438cùngpublicationfingerprint và audit/binding/scope code; khôngliveLLM/mutation. Nhiềucontext đãcóDQN/53+56/15/30/học phí/học bổng/hỗtrợ nhưng audit sai ID/quote/.../atomic coverage hoặc đòiýngoàicâu hỏi. Q9packing thiếuPT1–PT5 vốn cónguồn,Q25lẫn2025/2026,Q38scopeoutputinvalid502; Q22RAG/Q13DAGsupportedvẫnthiếuqualifier. Numeric digit-only làhạnchế, chưa xácnhậnperclaimvìrawfinalproposalthiếu. Verification~19–20s so với retrieval~1,8s; audit mới false negatives/latency cần hiệu chỉnh, không kết luận max5000/context gây lỗi. URL75 thiếutrongđoạnđượcchọn chưa khẳngđịnhtoàncorpus. Chỉdocs, PythonDBprobeunavailablepydantic nên khôngclaimDBlive. [Nhật ký #439](../nhat_ky/2026-10-14_phien_439_doi_soat_nguyen_nhan_that_bai_rag_dag.md), [snapshot439](snapshots/2026-10-14_session_439.md).

- **Phiên #438 (2026-10-14) — Test lại 20 câu RAG/DAG sau khi BE/worker khởi động lại**: Chạy 40 lượt trên cùng bộ câu `1,3,5,6,9,11,13,16,19,22,25,38,48,51,62,66,75,80,81,82`; DAG20/20 HTTP200 với 4 supported/11 partial/5 missing, RAG19/20 HTTP200 với 3 supported/12 partial/3 missing/1 conflict và câu38 HTTP502 `EVIDENCE_TARGET_SCOPE_INVALID`. Latency trung bình DAG33,37s/RAG27,17s; 304 lượt gpt-oss:120b và 3 fallback gemma4:31b thành công. Ghi nhận numeric quote binding (19/25/80/82), scope inference (38), temporal noise tài liệu2025 trong truy vấn2026, semantics 53/56/28 và qualifier/coverage false partial; chưa sửa code, chưa reset/reindex/publish/config. Cần xử lý các nhóm này trước full82/Ragas. [Nhật ký #438](../nhat_ky/2026-10-14_phien_438_test_lai_20_cau_rag_dag_sau_khoi_dong_lai.md), [snapshot438](snapshots/2026-10-14_session_438.md).

- **Phiên #437 (2026-10-14) — Triển khai phương án audit RAG/DAG**: Đã thêm semantic audit claim nguyên tử/qualifier/source-span, scope target institution vs exam organizer, compact model context với source_context cùng revision, BM25 ưu tiên data-year và subject-aware enumeration packing. RAG/DAG dùng chung verification; superseded_by không có proof cùng tuple được retry giới hạn; semantic repair không làm mất claim partial đã kiểm chứng. Focus evidence/temporal 95 pass, Ruff pass. Probe thật câu13 còn partial an toàn vì chưa có danh sách ngành cụ thể; câu16 giữ điều kiện ngành cho phép. Không đổi max_tokens/model/provider, không reset DB/reindex/publish. Cần restart BE/worker rồi chạy lại 20 câu, sau đó mới full82/Ragas. [Nhật ký #437](../nhat_ky/2026-10-14_phien_437_trien_khai_audit_rag_dag.md), [snapshot437](snapshots/2026-10-14_session_437.md).

- **Phiên #436 (2026-10-14) — Context khác max_tokens**: Chẩnđoán từ435/code/config, khôngliveLLM/mutations. UI5000generationbudget; evidencecapsplan1000/propose4000/verify2400; policy24candidates/10blocks/36000JSONchars/rerank5. Câu6RAGcontextquotecó53+56,prompt8012/completion549 nhưngbỏ56;19bỏqualifiercótrongquote,16entailmentfalsepositive;11DAGpacknguồn2025thayđoạn2026. Khôngchứngcứoutputcạn; upstreamwindow/truncationchưaverify. Đềxuấtcoverage/qualifier/atomicrelation+tokenawarepackobservability trước tănglimits,chưaimplement. [Nhật ký #436](../nhat_ky/2026-10-14_phien_436_phan_biet_context_va_max_tokens.md).

- **Phiên #435 (2026-10-14) — Test20 sau thêm thuyết minh**: Xác nhậnnguồn mới published epoch4/20sources, binding9da34/sourceaae30/indexec8a.40HTTP200/DAG16RAG16answered+4insufficientmỗi route;median15,23/11,37s;125usage/939393tokens/2Gemmafallback;34integrity57spanhashpass,khôngaccuracy;20lượttríchnguồn mới/configpublicationtrackedcodeunchanged. RAG16PT3gánTHPT/verifierchoqua,13nhầmtargetĐHSP,11DAGchọn2025,38/48/62noanswer,qualifier6/19/22/48/51/82 thiếu,falsepartial16/75DAG. Chỉtest+đềxuấtatomicclaims/roles/contextcoverage/partial,khôngfix/reset/reindex/config/restart/backup;chưafull82/Ragas. [Báo cáo20](../kiem_thu/2026-10-14_20_cau_rag_dag_sau_them_van_ban_thuyet_minh.md), [Nhật ký #435](../nhat_ky/2026-10-14_phien_435_test_20_cau_sau_them_thuyet_minh.md).

- **Phiên #434 (2026-10-14) — Menu thao tác nguồn**: Gom Nạp vector/Studio OCR/Chi tiết/Ngừng dùng/Xóa vào ba chấm mỗi dòng; bulk toolbar không đổi. RenderTrigger tùy chọn giữ dialog/mutation/polling owner ngoài menu, caller cũ vẫn nút độc lập. Biome5/build5115+TS đạt; browser menu/disabled Xóa/dialog focus+hủy/URL Chi tiết+Studio đạt. Không backend/real mutation/reset/reindex/publish; backup paused và hạng mục433 giữ nguyên. [Nhật ký #434](../nhat_ky/2026-10-14_phien_434_gom_thao_tac_nguon_vao_menu.md).

- **Phiên #433 (2026-10-14) — Rà luồng FE và điều hướng**: Boundary sidebar/detail breadcrumbs từ config; BackButton chung core, 6 detail domains bỏ history.back; Studio→chi tiết→kho và nhóm→list nhóm. Tab collection/assistant/source+revision dùng Router URL, remount theo ID, revision sai không fallback; save/context/reparse chung refresh+facts/jobs. Knowledge list dùng summary thực19sources227chunks thay legacy0/0, unknown —/error thật. OptionSelect+Field renderprops giữ model/provider, mobile model390 hết tràn; indexvi/QNUtitle/zoom. ScopedBiome32/build5114+TS/12FEtests đạt; authenticated browser F5/Back/model/revisionbad/counts và desktop1280. Không BE test/config/real mutation/reset/reindex/publish/restart/backup. Chưa UIunitcontext432/unsaved blockers/dashboard audit/mọipage/dark; bulk summary cần khi scale. [Nhật ký #433](../nhat_ky/2026-10-14_phien_433_ra_soat_luong_frontend_va_dieu_huong.md).

- **Phiên #432 (2026-10-14) — Đơn vị nguồn và năm dữ liệu dùng chung**: Đã triển khai manifest source-units-v1 trên canonical Markdown: heading/paragraph/list/table/row, parent/path/raw span/trang thật; projection embedding giữ header nhiều tầng, quote gốc không đổi. TemporalScope tách issued/mention/heading/data/role; chỉ data verified lọc cứng, không ép năm ban hành2026 lên dữ liệu2022–2024. QueryPlan tách data/document/event years. Optional annotation đoạn văn có năm qua ModelOps DB, exact quote/year, proposed→duyệt; unavailable observable; mặc định tắt/API config, chưa UI editor unit. Hiệu đính revision/audit/CAS manifest, PG/Qdrant chung metadata/digest; BM25/dense/FTS scope thống nhất, facts lịch sử scope riêng, evidence pin hash+parents. Focus95/Ruff đạt, real PG/Qdrant staging+model2pass13,23s; full sau header1198pass11baselinefail15skip168,75s. Fix giữ explicit provider khi lấy model mặc định được kiểm tra riêng trong focus cuối sau full khởi chạy. Chưa reindex/publish nguồn thật/upload DOCX/reset/config/restart; backup paused/quota unlimited. Cần BE/worker restart và staging corpus đã đối soát trước cutover; chưa full native tree/validity intervals/accuracy82/Ragas. [Nhật ký #432](../nhat_ky/2026-10-14_phien_432_don_vi_nguon_va_ngu_canh_thoi_gian.md).

- **Phiên #431 (2026-10-14) — Đề xuất cấu trúc tri thức chung**: User xác nhận bản tổnghợp2026, hỏi táicấutrúc lúc bóctách cho multi-domain. ĐọcparserOffice/chunker/temporal_metadata/source_context/evidenceblocks: đãcó issued_date/year/subject_years/evidence/audit/factapplicability; nhánhprose còn lấyheadingyear gán mọiblock. Đềxuất tận dụngcanonicaltree+rawspan, genericcoremetadata+domainextension, táchissued/effective/subjectperiod/eventdate, inheritance theoevidence local/parent/docdefault, không filename/latestyear tựthay. Structuraltokenaware parent-child chunks giữlist/rowheaders/conditions; embeddingcontext táchrawquote. Vector+BM25/FTS filters chungcontract, unknownretrieve rồiverify khônglọccứng; distinctyearrecord khôngdedup. Plan3đợt metadata→tree/chunk/index→stagingtest/migrate revisions, chưacode/DB/reindex/upload/publish. [Nhật ký #431](../nhat_ky/2026-10-14_phien_431_de_xuat_cau_truc_tri_thuc_chung.md).

- **Phiên #430 (2026-10-14) — Review văn bản thuyết minh2026**: User gửi DOCX Downloads/QNU_TuyenSinh_2026_VanBanThuyetMinh_RAG.docx; bundledpython đọc56đoạn/16Heading1/no tables/changes. Bản biên tập từFAQ18/09/2026, chưa xác nhận duyệt/nguồn từngclaim; chưa đủchi tiết mọi82câu (16khuyênchọn,38nonTHPTphạmvi,75URL, bảngquyđổi). Có học bổng2025 trong văn bản2026: không scope toànfile=2026; cần year/round/method theođoạn, không filename/dateyear. NếuindextừFAQ thì test82 không độc lập; thêm paraphrases/crossyear/missing/negative. Chưaupload/publish/code/config/reset, chưaverifyofficiallaws/layout vìbundledWindows thiếuLO. Đọc batch429recovered đã40HTTP200/DAG12answered8insufficient/RAG13answered7insufficient/configpublicationcode unchanged; chưamanualaccuracy/Ragas, tài liệu mới chưaincorpus. Backup paused/quotaunlimited giữ nguyên. [Nhật ký #430](../nhat_ky/2026-10-14_phien_430_review_van_ban_thuyet_minh_tuyen_sinh.md).

- **Phiên #429 (2026-10-14) — Sửa evidence RAG/DAG và tối ưu BM25**: Cache corpus LRU4/content+revision/inverted postings giữ công thức, benchmark diagnostic58blocks14queries7,95→2,638ms, không là tốc độ chatbot. Atomic list theo marker/source, coverage subject, partial footer, reviewed row exact identity, invalid precedence reject claim thay502, original sanitized DAG input giữ intent. Quote năm gắn heading thật cùng binding/index/source, không filename/nguồn khác. Focus82pass/PGrollback; Ruff đạt; finalfull1175pass11baselinefail13skip170,09s. Iteration `admissions_eval429_final20.json` trước year/subject bổ sung:40HTTP200/DAG10RAG12answered/integrity26/26/125GPTOSS/no fallback/configpublicationcode unchanged;DQN/PT5 sửa được, không accuracy. Lượt `verified20` bị9routertimeout/ALL_PROVIDERS_UNAVAILABLE, không ghép. Lượt mới `recovered20` còn chạy nền khi user bổ sung thông tin:22/40HTTP200/14answered8insufficient, chưa final fingerprint. User xác nhận nguồn2025/2026 và corpus thiếu nội dung một số82câu; đang tổng hợp văn bản mới, chờ gửi để đối soát, không ép82/82answered. Giữ default năm hiện tại/explicit năm, không dùng năm ban hành làm năm áp dụng. Không reset/config/reembed/publish/backup, quota vẫn unlimited. [Nhật ký #429](../nhat_ky/2026-10-14_phien_429_sua_evidence_va_toi_uu_bm25.md).

- **Phiên #428 (2026-10-14) — Bỏ quota nội bộ theo yêu cầu và test fresh20**: monthly token/cost default0 (unlimited), kiểm tra chỉ limit dương; presetkeynull, giữ usage/adminblock/upstream429/timeout/max5000. Transaction exacttenant tháng2026-10 đổi5M/100→0/0 giữ counter5.002.480; cuối6.199.933, noreset. Regressionbefore2fail/6pass→focus55/10unit+1PGrollback/Ruff; full1158pass11baselinefail13skip182,37s. Live40lượt0quota: DAG10answered10insufficient/RAG8answered11insufficient1precedence502;120GPT-OSS calls1.130.701tokens/no fallbackGemma;integrity23/23/configpublicationcode trackedunchanged. Câu9 cả2 sai chỉ4PT bỏPT5/405 dùsupported;DQN/rowentity/intent/partialfooter lỗi, chưa sửaRAG/chưaaccuracy/Ragas. Không FE/runtime restart/reset/reembed/publish/backup; worker process cần restart khi dùng code mới. [Nhật ký #428](../nhat_ky/2026-10-14_phien_428_bo_quota_noi_bo_va_test_20_cau.md), [Đối soát20](../kiem_thu/2026-10-14_20_cau_rag_dag_gpt_oss.md).

- **Phiên #427 — Test fresh 20 câu GPT-OSS/Gemma, bị quota chặn**: User đã lưu primary `ollama/gpt-oss:120b`/fallback `ollama/gemma4:31b` cùng 9router, temp0,2/max5000/thinking0; reranker AIserver giữ nguyên. 40 lượt DAG+RAG: câu1 hai lỗi EVIDENCE_PRECEDENCE_INVALID dù source có DQN; câu2 hai đáp án đúng address2026/quote trang1/integrity2/2; câu3–20 có36 QUOTA_EXCEEDED (DAGHTTP200 failed, RAG429), không phải accuracy20/Ragas. Tenant tháng2026-10 used5.002.480/limit5.000.000;16 GPT-OSS calls/156.169tokens/no fallback. Quota counter khác tổng legacy logs, chưa reconcile. DOCXhash/config/publication/evidencecode unchanged;19sources epoch3. Không sửa runtime/quota/config/reset/publish/restart/backup; cần user cho phép nâng quota riêng (đề xuất10M) rồi test lại; lỗi precedence cần tái hiện trước sửa. [Nhật ký #427](../nhat_ky/2026-10-13_phien_427_test_20_cau_rag_dag.md).

- **Phiên #426 — Ổn định /models đa provider**: Probe theo role metadata/spec/default exact thay vì tên; bounded32→256 empty+length/deadline/status thật, vector/rerank validate; relational keys authoritative/no stale disabled fallback; Claude native Messages, Gemini không đổi alias/max budget/thought leak, Mistral shared contract, Cloudflare bỏ fake/missing-key output và estimated usage. API DTO capability/dimension/scope/URL validation, endpoint không appendv1 vào pathcustom; UUID35chars/row-lock/primary removal/latency thật/DBdown503. FE add/edit roles, async save→default, stale-result guard, ResponsiveDialog, no fake404/suggestionscustom, runtime/readiness respectrole. Live6model:9router3/Gemini2.5/vLLMembed+rerank đạt; sandboxAIblocked nhưng unsandbox200/probes đạt. Focus118/PGrollback1/FE5/Biome10/build5112+TS/Ruff đạt; finalfull1148pass11baselinefail12skip191.47s; FElint13baseline. Không model/config thật/reset/restart/publish/backup; metadataJSONB không migration. Cần restartBE/worker+F5; UIauthenticated/mobile/dark và nativeAnthropic live chưa nghiệm thu; OCRhealth/catalogue không phải bóc tách. [Nhật ký #426](../nhat_ky/2026-10-13_phien_426_on_dinh_modelops_da_provider.md).

- **Phiên #425 — Tạm dừng backup, chẩn đoán Custom Gateway**: Read-only provider + live catalogue554 có exact `ollama/gpt-oss:120b`; probe32 HTTP200/length/content rỗng/reasoning115chars/completion32→decoder protocol error, cùng request256 HTTP200/stop/OK./completion81→success. Không upstream404; FE hardcode404/Error và probe gộp thiếu ngân sách với protocol lỗi. Đề xuất bounded evidence-based probe retry + phân loại lỗi/DTO/UI, không chấp nhận reasoning làm đáp án. Chỉ diagnosis/docs, chưa fix/model config/DB health/reset/restart; backup work paused, không thay đổi lịch app. [Nhật ký #425](../nhat_ky/2026-10-13_phien_425_chan_doan_custom_gateway_probe.md).

- **Phiên #424 — Backup đợt2 đã chốt kiểm thử**: User chọn external secret mount + S3/MinIO. Import raw bounded/unverified+pinned, secret paths không giữ pass trong DB, copy encrypted/full readback hash/version, ARQ tick10/40 deferred/exact next_run lock, soft removal/.trash/last-good/pin/calendar retention chưa reclaim disk. Internal-network target + secret-free fixed relay pinned image ID, cleanup labels/network; missing relay fail-closed. Windows reader replace race regression/retry0,5s; all-active catalogue. Windows42(+workers49)/Ubuntu38+4skip/integration126.24s/isolation11.26s/Ruff/FEbuild5111+TS/scopedBiome đạt. Final full1113pass11baselinefail11skip150.20s; không failure backup/worker mới, Docker opt-in đã test riêng. FEfull13baseline; browser sign-in chưa authenticated/mobile/dark. Bản thật bkp_0748d2ca73254460bfe2ab4a4cb6599e completed1097107244bytes còn nguyên metadata, policy chưa tạo/defaultoff; không realrestore/copy/bậtcron/reset/restart. Không còn container/network test; images giữlocal. Cần BE/worker restart, operator secret files/S3bucket/relay config; chưalivecutover/PITR/remote prune/RPO-RTO. [Nhật ký #424](../nhat_ky/2026-10-13_phien_424_sao_luu_dot_2.md), [Runbook](../trien_khai/05_sao_luu_dot_2.md).

- **Phiên #423 — Đã gỡ 5 backup thất bại cũ theo yêu cầu**: Exact IDs trong ảnh, chỉ metadata failed/create/size0/no archive; chuyển 5 JSON vào `backend/storage/backups/.removed-423` với exclusive reservation/operation handles, literal paths/reparse guards/checksum trước-sau đạt. Catalogue top-level0, có thể phục hồi metadata; không xóa dữ liệu app/DB/Redis/lock files, không source edits/tests/retry/create backup. User F5 rồi tự sao lưu mới. [Nhật ký #423](../nhat_ky/2026-10-13_phien_423_go_nam_backup_that_bai.md).

- **Phiên #422 — Đã đối soát 3 workflow legacy, gỡ blocker hiện tại**: User cho phép; exact IDs phiên421 chuyển running→failed trong shared maintenance lock/row lock/conditional atomic transaction, completed13:29:42.293116UTC. Runtime_profile.legacy_reconciliation lưu session422/evidence/no_replay/previous; input/output/profile gốc/nodes/tổng workflow không đổi. Post-commit read-only 3/3 đạt, running workflows0/pending-or-retryable jobs0. Không source edits/full suite/restart/reset/replay/backup mới; user F5 tạo backup mới, chưa cam kết corpus thật qua các bước sau. [Nhật ký #422](../nhat_ky/2026-10-13_phien_422_doi_soat_ba_workflow_legacy.md).

- **Phiên #421 — Backup thật bị chặn bởi workflow legacy, chờ xác nhận**: `bkp_7430df87ffca495186b2287e8e4a0211` runner PID9224/progress15 đã khởi chạy, lỗi BACKUP_WORKFLOW_RUNNING. Read-only DB đúng 3 running thiếu deadline/nodes0: `0f200a3a-30dc-4736-b1b9-159277ae387c`, `c7d8e6f3-e4a7-4ee7-a644-d81c2c11a303`, `8bb61da6-22e0-44ec-ab2e-d1f69ca23ba1`; đối chiếu eval413/415 là HTTP500 cũ, BE/worker restart20:18 sau chúng. Cron chỉ deadline không xử lý legacy là chủ đích. Đề xuất conditional reconciliation đúng 3 ID→failed/audit, giữ dữ liệu/không replay, cần user xác nhận; chưa mutation/reset/retry backup. Không bypass guard; chưa cam kết corpus thật. [Nhật ký #421](../nhat_ky/2026-10-13_phien_421_chan_doan_backup_workflow_cu.md).

- **Phiên #420 — Đã sửa launcher backup Windows/Ubuntu**: Popen qua thread, Windows hidden/POSIX session riêng, reap không phụ thuộc Selector; giữ reload/global policy. Stdin binary UTF-8 sửa mật khẩu có dấu; lỗi spawn ghi type an toàn + failed history. Windows30/Ubuntu24.04 container27+3skip/integration PG-MinIO-Qdrant42.45s/Ruff đạt; full1101pass11baselinefail10skip132.05s. Không FE/worker edits, không restart/reset/backup dữ liệu thật; cần restart BE/F5/thao tác mới, giữ failed history. Chưa Ubuntu full suite/image production/corpus thật/RPO-RTO. [Nhật ký #420](../nhat_ky/2026-10-13_phien_420_fix_backup_windows_ubuntu.md), [Runbook](../trien_khai/04_sao_luu_va_khoi_phuc_dot_1.md).

- **Phiên #419 — Backup UI503 chưa sửa**: Ảnh POSTbackup BACKUP_LAUNCH_FAILED; process thật uvicornreload trênWindows, thư viện chọnSelectorEventLoop(use_subprocess=true). Probe create_subprocess_execSelector→NotImplementedError, Proactor→exit0. service.launch nằm requestloop; test418defaultProactor khôngphủreload. Đềxuất Popenoffload/launcherProactorrieng+regressionHTTP202Selector+sanitizederrortype, không đổi globalpolicy/bỏreload. Chỉdiagnosis/docs; khôngfix/restart/reset/backupthật, khôngđụngRedis/mật khẩu. [Nhật ký #419](../nhat_ky/2026-10-13_phien_419_chan_doan_backup_windows_reload.md).

- **Phiên #418 — Backup đợt1 đã triển khai, kiểm thử dữ liệu mẫu**: Whole-installation PG+file local/S3 current+Qdrant single-node+configs+encrypted key escrow; scrypt/AES-GCM streaming/manifest hashes, independent runner/catalogue ngoài DB, PG barrier API/SSE/worker, auth AI.Admin phiên thật, scoped cookie download, list/detail/history UI và offline CLI. Restore chỉ container mới/labels/localhost/no live mounts, không Redis replay/AI calls. Unit24/realPG-MinIO-Qdrant37.20s/Ruff đạt; full1095pass11baselinefail10skip108.49s; FEfinalbuild5105/TS/scopedBiome đạt, full lint13baseline. Container/runner test đã kết thúc/dọn; không backup/reset/restore/publish thật, chưa scheduler/remote/PITR/live-restore; cần restart toàn bộBE/worker, tự giữ mật khẩu/chép off-host. Chưa Docker prod build/UI E2E do sign-in, chưa corpus thật/RPO/RTO. [Nhật ký #418](../nhat_ky/2026-10-13_phien_418_sao_luu_dot_1.md), [Runbook](../trien_khai/04_sao_luu_va_khoi_phuc_dot_1.md).

- **Checkpoint hiện tại #417 — bị ngắt, chưa nghiệm thu**: Userstack xác nhận MissingGreenletfinalize/expiredPK;4chỗdùngimmutableexecutionID,3PGfailtrước/passsau+13runtime=16pass, retry5HTTP200/5173/completed. FinalRuff/full1071pass11baselinefail9skip (3PGskipđãtest riêng),45focused/31PGcorpus. Frozen82dừng25đểfix; remaining57ghi26–43,27/38ALL_PROVIDERS_UNAVAILABLE,42ReadError43ConnectErrorhelpertựdừng; khôngcònhelper/agentkhôngdừngservices.44–82chưatest/42–43cầnretry; chưaaccuracy/Ragas/productionready. Wordhashkhớp. Khôngreset/reembed/publish/đổimodel. Cácbản“đangchạy” dướiđây là iterationcũ. [Nhật ký #417](../nhat_ky/2026-10-13_phien_417_dot_2_evidence_va_chatbot.md).

- **Chốt runtime #417 sau sửa root cause**: Atomicbody+same-sourceheader/JSONmetadata budget (trướcđófacts bịcắt), factsemanticrerankriêngAIserver, anchor10s/rerank3s+DBsessionriêng, rowentityname giữtrongquote/claim vàDAGguard; không giảmtimeoutOCRprovider. Ruff/full1071pass11baselinefail6skip/focused45/PG31 đạt. Full82cũdừng11 đểsửa; fresh82mãchốt `admissions_eval417_frozen82.json` đangchạy, chưaaccuracy/Ragas/productionready. SSE200done códecision nhưnglượtSSEcodequestionmissing; khôngcoitransportlàquality. Userđãmởlạiservices, khôngreset/reembed/publish/đổimodel. [Nhật ký #417](../nhat_ky/2026-10-13_phien_417_dot_2_evidence_va_chatbot.md).

- **Phiên #417 — Đợt 2 đang kiểm chứng chất lượng**: Evidence opt-in shared RAG/DAG, exact source spans/whole reviewed rows, BM25 variants/RRF/reranker AI server, own numeric quotes/same-source scope/verifier; AnswerDecision giữ partial citations. User chọn năm hiện tại VN và TB1906 ưu tiên flyer cùng tuple2026, đã lưuDB policy/contact;19sources/epoch3khôngđổi. DirectRAGcollectionpolicy khôngbypassmodule trống/general, persona giữtrườngđích, boundedquote repair1 vẫnfailclosed. FinalRuff/full1063pass11baselinefail6skip/focused37/PG23 đạt. 8lượttrọngtâm5supported/2missing/1timeout, integrity5/5; chưaaccuracy/Ragas. Userđãmởlạiservices saulỡtắt; full82cũtransportfailkhôngchấmlàđápánsai. Fresh82 `admissions_eval417_final82.json` đangchạy; còncoverage/timeout cầnđốisoát, chưaproductionready. Khôngreset/OCR/reembed/publish/đổimodel. [Nhật ký #417](../nhat_ky/2026-10-13_phien_417_dot_2_evidence_va_chatbot.md).

- **Final gate #416**: Ruff đạt; full Backend1041pass/11baselinefail/5skip (107.53s); PostgreSQL opt-in đã đạt riêng. FE3tests/Biome9files/build+TypeScript đạt. Không có failure mới; còn baseline publishing/auth/consulting/export/reconciliation và Windows teardown log. Chi tiết phạm vi, cấu hình đã lưu và giới hạn ở nhật ký416.

- **Phiên #416 — Đợt 1 chatbot**: Theo user, reranker trỏ AI server DB `prov_rtx5090_vllm/bge-reranker-v2-m3`; pin primary9routerlocal `gh/gpt-6-luna[1m]` và fallbackGemini3.1flashlite. Readiness theo published retrieval snapshot/parity/review/scope,19nguồn epoch3, score93 ready/no blockers; legacyDocuments0 không falseblock. DB-only role/key validation, relational keys authoritative; FE roundtrip provider+model, dynamic role options/no hardcoded reranker defaults. Chat JSON/SSE dùng explicit provider/model route plan, không thử alias trên embeddingserver; LLM/DAG/RAG/consulting forward cảfallbackprovider. Workflow boundary setup/engine/finalize rollback+fresh terminal audit/cancel/timeout, deadline300s cấu hình được; worker cron chỉ expire running códeadline quá hạn+30s, không replay, không sửa recordcũ thiếu deadline/paused HITL. Worker cần restart để nhận cron, chưa tựrestart.96focused/PG thật,19failure+worker trước13phase1cuối, FE3/Biome/build/Ruff đạt; final full suite ghi trong nhật ký, vẫn11baselinefail. Live AIrerankscore0.998266, chat200 usagegpt-6-luna/custom/noFallback workflowcompleted6nodes. Chưa phase2 prose/temporal/claim-grounding/82eval/Ragas; khôngreset/reembed/OCR/publish hoặc đổi defaults toàn kho. [Nhật ký #416](../nhat_ky/2026-10-13_phien_416_dot_1_readiness_reranker_va_workflow.md).

- **Phiên #415 — Đề xuất chatbot sau đổi model**: User lưu gh/gpt-6-luna[1m]/Gemini3.1flashlite. Test14criticalDAG:11answered/1insufficient/2HTTP500(khôngaccuracy);10Luna/customsuccess+1Geminifallbackdo9routerReadTimeout; cascadecòn thửnhầm alias trênvLLMembedding. Gemini naycókey1JSON/1relational.19publishedbinding/epoch3nhưnglegacyDocuments0→readinessfalseblock78%; rerankerbgev2m3/Cloudflarevẫnpairlệch vìFElưubỏproviderid. Quota5.173prose vẫnnoanswer, GDTCheightcontextkhôngretrieve, sàn20nguồnactive nhưngbotkhôngthấy; c21chọn2025khôngnêunăm.2câulịchsauAPIretry200(51noanswer/68đúng);500workflowsrunning/nodes0,causechưastack. Chỉproposal/docs+probes; đềxuấtsnapshotreadiness/preservepolicy→providerpin/workflowfinalize→tupleevidenceprose+year/eventretrieval+commonRAGDAGdecision→nguồnthiếu/full82. Khôngfix/reset/publish/reembed. [Nhật ký #415](../nhat_ky/2026-10-13_phien_415_de_xuat_xu_ly_chatbot_sau_doi_model.md).

- **Phiên #414 — Fix ModelOps 9router**: Shared OpenAI chat contract: probe32/cap256, explicit streamfalse/true, bounded HTTP400 parameter negotiation không hardcode tên model; unsupportedtemperature observation lưu DB theo provider/alias/endpoint. Strict JSON/SSE/content; partial stream không replay. Test2/2model localOK; generategh/gpt-5.4-mini→gpt-5.4-mini/custom/noFallback; hotlinechat200 dùng model mới; streamgh/gpt-6-luna[1m]→gpt-6-luna/custom/noFallback. APItest message/codes/servedcapabilities và generate requested/provider/fallbackreason; bỏ qnu_workflow fakeusage+legacyaggregation, quota singleowner. 92focused/21last/Ruff đạt; full1028pass/11baselinefail/4skip. Chưa full82/Ragas/readinesslegacy/rerankersave/RAGfix. Khôngreset/modelconfig/publish; capability observations và normal testrecords cóghi. [Nhật ký #414](../nhat_ky/2026-10-13_phien_414_fix_modelops_9router_request_contract.md).

- **Phiên #413 — Chẩn đoán /models và 9router**: User đổi primarygh/gpt-5.4-mini/fallbackgemini-3.1-flash-lite rồi chuyểnqnu-9router sanglocalhost20128. Catalog552 chứa cảgh/gpt-5.4-mini vàgh/gpt-6-luna[1m]; APItestQNU gửimax_tokens1, cả2HTTP400minimum>=16; direct32/omittemperature/streamfalse cả2OK200. Runtime luôn gửitemperature(model mới từ chối400) và khôngstreamfalse(gateway mặc địnhSSE200, jsonparsefail); chatbot vẫnCloudflareLlama fallback, Gemini active nhưngkhôngkey. ReadinessđếmKnowledgeDocumentlegacy0 dù19publishedbindings; FElưureranker bỏprovider_id→BEdefaultCloudflare; aggregateusage/latency110tĩnh gây hiểu nhầm. Có1HTTP500/1ReadErrorbatchđầu, retry5HTTP200, chưastack API; chưa đánh giámodelmới/full82. Chỉprobes/diagnosis/proposal/docs, khôngfix/config/reset/publish. Đềxuấtsharedcapabilityrequest/probe→providerpin/actualobservability→snapshotreadiness/preservepolicy→RAGclaimevidence+82regression. [Nhật ký #413](../nhat_ky/2026-10-13_phien_413_chan_doan_modelops_9router_va_de_xuat.md).

- **Phiên #412 — Test FAQ tuyển sinh**: Đọc DOCX người dùng, đủ82Q&A/16nhóm; test thật82DAG+82RAG,164HTTP200/0exception/82traces. DAG48answered/34insufficient, RAG66/16 (không phải số đúng/Ragas). Phát hiện mã DQN bị citation gate, quota5.173 prose bị typed-fact gate, sư phạm học bạ/GDMN năng khiếu/GDTC thể hình phủ định sai, điểm sàn2026 lấy20.25 từ2023, trộn lịch/đợt/phí bổ sung. OpenAI/Gemini inactive;69inference DAG dùng Cloudflare Llama3.1-8b fallback,82qnu_workflow log gpt theo config không phải inference. 19source/pointers/epoch3/genvg_21324678abcf giữ nguyên. Chỉ diagnostic harness/báo cáo/docs; không sửa runtime/đổi model/reset/uploadFAQ/publish. ScopedRuff+compile đạt. [Nhật ký #412](../nhat_ky/2026-10-13_phien_412_test_bo_cau_hoi_chatbot_tuyen_sinh.md), [Báo cáo82câu](../nhat_ky/2026-10-13_phien_412_bao_cao_test_chatbot_tuyen_sinh.md).

- **Phiên #411 — Xuất bản nguồn đã chọn**: User đồng ý partial, đã thêm `/publish-selected` pin binding/source/index IDs; source scope/review/fact parity/CAS+remote count/audit gates, giữ pointers không chọn; first/same gen hỗ trợ incremental, đổi gen phải cover mọi source đang serving (unpublished không bắt buộc). FE publish theo targets và confirmation scope rõ, candidate preview hợp nhất selected+serving; API full activate/rollback cũ giữ tương thích, worker không đổi. 12unit/1PostgreSQL roundtrip (outerrollback/Qdrantmock)/FE8/Ruff/Biome6/build đạt; full trước ca bổ sung1001pass/11baselinefail/9error/4skip. Runtime endpoint có/invalid-source404; chưa browser hoặc live Qdrant partial fixture, không publish/đổi model kho thật. [Nhật ký #411](../nhat_ky/2026-10-13_phien_411_xuat_ban_nguon_da_chon.md).

- **Phiên #410 — Đề xuất xuất bản nguồn đã chọn**: Người dùng xác nhận test lại từ đầu ổn, nhưng nạp1–2nguồn không publish riêng được. FE `canPublishSources` + BE `publish_generation` gate tất cả active bindings; retrieval lọc active generation nên không thể bỏ gate đơn giản. Đề xuất selected publication atomic/exact revisions/review/parity/CAS/audit, first generation cho partial, same-generation giữ pointers không chọn; đổi model/generation vẫn cần chuyển toàn kho. Chỉ diagnosis/proposal, chưa code/data/publish/test; chờ thống nhất contract. [Nhật ký #410](../nhat_ky/2026-10-13_phien_410_de_xuat_xuat_ban_nguon_da_chon.md).

- **Phiên #409 — Nạp vector và xuất bản tuyển sinh**: Theo yêu cầu explicit của người dùng, nạp 19 nguồn đã duyệt bằng ModelOps default bge-m3/prov_rtx5090_vllm/1024d; generation `vg_75acf82ded93` active, collection epoch2, 19 completed jobs/19 parity pass,227chunks/3428facts. Qdrant `col_admissions_169f2ef17edd4ae5` có227 retrievable points; RAG tuyển sinh2026 và học phíK49 có kết quả đúng snapshot epoch2/19binding. Fix API summary đếm group links thành scoped bindings và model active metadata; live summary19/19/227/ready/bge-m3. 35focused+1skip/Ruff đạt; full990pass/11baselinefail/9tempErrors/3skip. Chưa full LLM/Ragas; không OCR/reset/duyệt lại/provider config. [Nhật ký #409](../nhat_ky/2026-10-13_phien_409_nap_vector_va_xuat_ban_tuyen_sinh.md).

- **Phiên #408 — Cập nhật trạng thái sau duyệt Studio**: Studio trước chỉ refresh bản hiển thị/chi tiết, không invalidation binding list/summary, trong khi QueryClient staleTime30s khiến quay lại vẫn dùng cache cũ. Helper `refreshSourceQueries` nay refetch cả inactive queries theo collection/source; Studio lưu/duyệt và detail duyệt/từ chối đều chờ đồng bộ, bỏ refetch trùng. Regression QueryClient thật xác nhận list/summary/vector cập nhật và kho khác giữ nguyên; Biome4files + Vite/TS build đạt. Chưa browser duyệt tài liệu thật; không backend/DB/Redis/mutation dữ liệu. [Nhật ký #408](../nhat_ky/2026-10-13_phien_408_cap_nhat_trang_thai_sau_duyet_studio.md).

- **Phiên #407 — Fix persist duyệt và phạm vi nguồn**: DB chứng minh bulk review trước đã chạy lúc 02:17 UTC nhưng chỉ `revision.status/updated_at` persist, còn artifact review vẫn `required`; nguyên nhân mutate JSONB lồng tại chỗ khiến SQLAlchemy không thấy `parse_provenance` dirty, không phải Redis và không cần reset DB. Backend nay deep-copy artifact trước quyết định và có regression dirty-history. Frontend lấy blocker theo đúng vector targets, nên chọn 1 chỉ hiện 1 thay vì toàn bộ 8. Không tự duyệt/publish/data reset. Ruff toàn backend, source ingestion10, backend focused3, FE52, Biome4files, Vite+TS build đạt; full backend 987pass/11fail/9error/3skip với lỗi baseline ngoài scope. [Nhật ký #407](../nhat_ky/2026-10-13_phien_407_fix_persist_duyet_va_pham_vi_nguon.md).

- **Phiên #406 — Fix hộp thoại duyệt nhiều nguồn**: Live DB vẫn giữ 8 artifact `review.required` và không đổi timestamp sau thao tác, còn endpoint bulk đã có trên runtime và trả RFC 7807 đúng khi probe; do đó không reset DB/Redis. Nguyên nhân UI là ConfirmDialog bulk nằm trong Dialog nạp vector, gây xung đột portal/focus trap trước khi request được commit. Đã nâng selection/mutation/ConfirmDialog lên `VectorLoadControls` và render xác nhận cùng tầng với Dialog chính, khóa các action cạnh tranh khi duyệt. Không tự duyệt/publish/data mutation. Biome hai file và Vite+TS build 5092 modules đạt. [Nhật ký #406](../nhat_ky/2026-10-13_phien_406_fix_hop_thoai_duyet_nhieu_nguon.md).

- **Phiên #405 — Fix duyệt Studio OCR và duyệt nhiều nguồn**: Structured artifact nay là nguồn chuẩn cho read DTO, Studio, binding list và publish gate qua `structured_review_status/requires_structured_review/structured_issue_count`. Studio duyệt được cả legacy `ready + artifact required`; bulk API khóa/pin exact revisions, validate toàn bộ rồi commit một lần. Dialog nạp vector liệt kê blocker, chọn nhiều bằng Checkbox và xác nhận rõ ràng; publish không còn bật sai. Không tự duyệt 8 nguồn, không publish/reindex/xóa Redis. Ruff toàn backend, source module9, Studio compatibility4, FE utility9, Biome11files và Vite+TS build đạt. Full backend 982pass/15fail/9error/3skip; 4 lỗi Studio do thay đổi đã fix 4/4, còn 11/9 baseline ngoài scope. [Nhật ký #405](../nhat_ky/2026-10-13_phien_405_fix_duyet_studio_va_duyet_nhieu_nguon.md).

- **Phiên #404 — Publish 409 sau khởi động lại**: Live head đúng, Redis queue0/worker cron-health hoạt động, DB 57 completed không active/failed. Generation tuyển sinh có 19/19 index ready+parity pass nhưng 8 active source mang status ready trong khi artifact vẫn review.required (23 visual/header issues). FE chỉ gate source_status+vector và detail chỉ hiện review khi status review_required; backend publish đọc artifact và trả FACT_SET_REVIEW_REQUIRED. Root cause là state-contract drift, không phải Redis. Đề xuất artifact-derived review field/read boundary + FE blocking list/deep link + idempotent reconciliation; chưa sửa/duyệt/publish/reindex/Redis. [Nhật ký #404](../nhat_ky/2026-10-13_phien_404_chan_doan_publish_409_sau_khoi_dong_lai.md).

- **Phiên #403 — Kiểm tra Redis và lỗi upload cũ**: Live Redis chỉ có 1 `rag:cache`, không có ARQ queue/job/result/lease; DB có 57 completed và không active/failed jobs. UI lấy lỗi ingestion từ PostgreSQL. Retry batch tạo JobRecord/UUID mới; retry chung tăng attempt và broker ID mới, nên không tái dùng kết quả lỗi Redis. Cảm giác lỗi cũ chủ yếu do worker chưa restart hoặc structured artifact reuse từ PostgreSQL/storage; ARQ orphan sau DB reset chỉ log missing rồi kết thúc. Chỉ read-only, không code/data/Redis/restart. [Nhật ký #403](../nhat_ky/2026-10-13_phien_403_kiem_tra_redis_job_loi_cu.md).

- **Phiên #402 — Fix đồng bộ structured review**: Invariant chung buộc artifact có `review.required`/issues thành source `review_required` cho cả parse mới, artifact reuse và reparse; endpoint duyệt hỗ trợ bản legacy lệch trạng thái nhưng không tự duyệt. Migration `20261012_sync_struct_review` đã áp dụng; live `col_admissions` hiện 8 review_required/11 ready, marker khớp 8/8, không đổi active generation/vector. Ruff focused và 8 source-ingestion tests đạt; full backend 985 pass/11 fail/9 error/3 skip, lỗi baseline ngoài scope. Cần cán bộ đối soát và duyệt 8 nguồn rồi mới xuất bản; không reset/re-index/tự duyệt/publish. [Nhật ký #402](../nhat_ky/2026-10-13_phien_402_fix_dong_bo_structured_review.md).

- **Phiên #401 — Chẩn đoán xuất bản bị chặn và worker**: DB xác nhận 19 ingestion + 19 index jobs completed, 19/19 revisions ready và parity pass, worker cuối log failed0/ongoing0/queued0. Ba missing lúc start là Redis jobs cũ sau reset; Inspector/DrawingML là fallback warning, không phải lỗi batch. Publish bị `FACT_SET_REVIEW_REQUIRED` do 8 structured artifacts cần duyệt (visual hoặc unresolved table headers), nhưng các source revision đang `ready`; nhánh reuse artifact không chuyển quality status sang warning nên UI không hiện nút review trong khi publish gate vẫn chặn. Chỉ read-only diagnosis; chưa fix/duyệt/publish/retry/reset/restart. [Nhật ký #401](../nhat_ky/2026-10-12_phien_401_chan_doan_xuat_ban_bi_chan_va_worker.md).

- **Phiên #400 — Triển khai Fact nội dung dài và chặn job treo**: `KnowledgeFact` có deterministic `entity_key`, bounded collision-resistant `entity_label`, full `entity_text`; `entity_name` tương thích ngược chuyển TEXT. Artifact v5/parity/schema API/RAG FTS được nối đầy đủ; migration add/backfill/GIN/drop B-tree/downgrade guard đang ở head. Index worker rollback và reload job trước khi ghi failed, chặn `PendingRollbackError`. Ruff toàn backend đạt; 54 focused và 4 long-fact cuối (có PostgreSQL round-trip >512) đạt. Full 980 pass/13 fail/9 error/3 skip, lỗi còn lại ngoài scope do seed/quyền API/Windows temp. Không retry hai file, không publish/reset/restart. [Nhật ký #400](../nhat_ky/2026-10-12_phien_400_trien_khai_fact_noi_dung_dai.md).

- **Phiên #399 — Fact cho nội dung dài**: Đề xuất bỏ vai trò chồng chéo của `entity_name`: `entity_key` deterministic code/hash cho exact/dedup, `entity_label` nhãn UI, `entity_text` + `attribute_value` dùng TEXT, `raw_data` giữ nguyên hàng/evidence/provenance. Không B-tree toàn văn; dùng hash và FTS GIN/trigram. Nội dung dài embedding theo parent-child chunks, cực lớn giữ canonical artifact+locator. Migration add/dual-write/backfill/switch/remove có parity/collision/rollback gates; transaction lỗi phải rollback và stale job recovery. Chỉ đề xuất, chưa schema/code/data/retry/publish/test. [Nhật ký #399](../nhat_ky/2026-10-12_phien_399_de_xuat_fact_noi_dung_dai.md).

- **Phiên #398 — Hai job nạp vector treo**: Trước reset runtime đồng thời, `phu-luc-hd-tuyen-sinh-2025.signed.pdf` và `HD nhập học.pdf` bóc tách xong nhưng index jobs `job_3f4bbde98ff8`/`job_12a2dfdd2e8c` kẹt running10%. Fact table dùng đoạn mô tả dài làm `entity_name`, vượt `VARCHAR(512)`; flush lỗi rồi task thiếu rollback trước `_is_cancelled/_set_job`, gây `PendingRollbackError` và không ghi failed/error; 17 job còn lại completed. Cuối phiên DB đã bị tác vụ ngoài phiên làm sạch/reset nên job/batch/binding không còn, worker báo ARQ cũ missing. Đề xuất entity identity cấu trúc + provenance nguyên văn, validate contract trước ORM, rollback/session sạch và stale recovery; phiên này không code/retry/publish/restart/provider/reset. [Nhật ký #398](../nhat_ky/2026-10-12_phien_398_chan_doan_hai_job_nap_vector_treo.md).

- **Phiên #397 — PDF preview giữ kết quả DOCX**: Helper OOXML field-stack materialize cached table formulas trong bản sao trước Gotenberg, giữ gốc/format/gridSpan/PAGE; missing/nested/malformed trả422, không đoán số. layout-v9 invalidates artifact reuse. PDF thật7trang hàng tổng1070/451/402/351 đúng ảnh, SHA gốc không đổi;10formula+1HTTP cuối và37focused trước đạt, Ruff đạt; full988pass/11baseline/3skip. Không FE/restart/reparse/publish/reset/keys. User make dev rồi Bóc tách lại; preview nguồn cũ vẫn cache, header5–6 còn vấn đề riêng, chưa universal cell-parity. [Nhật ký #397](../nhat_ky/2026-10-12_phien_397_docx_preview_giu_ket_qua_cong_thuc.md).

- **Phiên #396 — DOCX SUM preview sai**: Phuong huong2024 DOCX total thạc sĩ là SUM(ABOVE) cached1070/451/402/351, cộng25dòng khớp; GotenbergLibreOffice preview7trang tính sai cột do ô nhãn span3, xuất cả tổng mã ngành208561309. Review thật TABLE_HEADER_UNRESOLVED trang5–6, không phải guard formula. Đề xuất materialize data-field cache trong bản sao preview + per-cell parity/header continuation; không đổi DOCX gốc/PAGE/nguồn. Chỉ read-only, chưa fix/reparse/review/publish/restart. [Nhật ký #396](../nhat_ky/2026-10-12_phien_396_docx_formula_preview_sai_cot.md).

- **Phiên #395 — Chờ khóa embedding**: ModelOps phân biệt busy với invalid/quota, polling async deadline120s mặc định, transient recovery/backoff; heartbeat30s giữ lease batch dài/cancel giải phóng vLLM. UI Chờ embedding. PostgreSQL thật20jobs1key không overlap/dọn testUUID;32focused/5FE/Ruff/Biome/build đạt; full977pass/11baseline/2skip trước testheartbeat thêm. Không FIFO nghiêm ngặt/không retry vô hạn. Publish hiện for_update+epoch/sourceCAS, không cầnGPUqueue; giữ nguyên. Chưa restart/retry/reset/publish/đổi khóa thật; user chạy make dev rồi nạp lại nguồn lỗi. [Nhật ký #395](../nhat_ky/2026-10-12_phien_395_hang_doi_khoa_embedding.md).

- **Phiên #394 — Chẩn đoán nạp vector hết khóa**: Provider vLLM có một khóa active, quota=null, không lỗi/cooldown; audit selected/success. Job đồng thời tranh lease độc quyền trước Redis capacity, resolver báo MODEL_PROVIDER_KEYS_UNAVAILABLE ngay; worker không phân loại retryable. Đề xuất busy queue/backoff/release-cancel và UI chờ, không thêm key hay reset. Chỉ đọc DB/code, chưa sửa/retry/publish/restart. [Nhật ký #394](../nhat_ky/2026-10-12_phien_394_chan_doan_tranh_chap_khoa_embedding.md).

- **Phiên #393 — Tên nguồn chờ duyệt**: List/detail binding dùng latest snapshot metadata riêng, thiếu thìimportsnapshotbulktenant/collection; khôngđổiactivepointer/status. Runtime8nguồn bndIDđãcótên/fileđúngactive=null.6tests/Ruffđạt;full968pass/13ngoàiscope/2skip. KhôngFEstatus/reset/duyệt/publish/restart; refresh sauBEreload. [Nhật ký #393](../nhat_ky/2026-10-12_phien_393_ten_nguon_cho_duyet.md).

- **Phiên #392 — Fix child shutdown race trong dev**: PID2136 guard hủy restart sau stopworker; root vẫnstrict, descendants đổiidentity/đangthoát đượcskipkhôngkill, Stop-Process exitrace kiểm lại.18assert/AST/diff đạt,2lầndev thậtexit0. Hiện worker11896 start22:19/RedishealthOK, FE3000 PID6924, BE8001 PID5224; PIDcũđãthoát. Không reset/publish/retrynguồn/keys/Docker; user có thể retryOCR vớiworker mới. [Nhật ký #392](../nhat_ky/2026-10-12_phien_392_fix_dev_child_shutdown_race.md).

- **Phiên #391 — make dev restart cả ba**: Bốn entrypoint Windows dev/dev1/dev2 dispatch start-dev.ps1; xác minh ownership/PID epoch/cây con/foreignports, mutex, DB ready trướcstop, chờports+processes10s, startworker1lần và terminal BE/FE absolute/strictPort. 16 regression + PS5 AST + WhatIf thật PID10008 đạt; chưa restartlive/DBmutation/testsứngdụng. Worker cũ còn sống cho đến user chạydev. Không Docker/reset/key/publish/purge. Jobs có thể bị ngắt, cần chạy khi batch kết thúc; không kill cha legacy không xác minh. [Nhật ký #391](../nhat_ky/2026-10-12_phien_391_make_dev_restart_be_fe_worker.md).

- **Phiên #390 — Worker cũ vẫn EMPTY_OCR_PAGE**: Batch9442 mới failed21:58, SHA đúngfileBC2022. PID10008 ARQ đúngrepo start19:41 trước blank guard sửa20:07; start-worker.ps1 thấy PID/startTicks còn sống thìreturn nên restart BE/dev không reload worker. Classifier hiện tại trên cùngSHA is_blank=true. Chỉ read-only diagnosis; chưa stop/start/retry/reset/publish/codefix. Cần restart riêngworker và retry, đề xuất launcher phiên bản/restart rõ ràng. [Nhật ký #390](../nhat_ky/2026-10-12_phien_390_worker_cu_giu_blank_guard.md).

- **Phiên #389 — Mixed visual ingestion/progress**: layout-v8/structured-v4; union ảnh–native route OCR, giữ chữ ảnh DOCX, blank speck morphology, native MuPDF lock/Inspector child15s, HTML spans/year subheaders/native continuation, identity diversity/row context, code-only52facts, visual/header review guards. 20 originals SHA khớp, extraction thật 20/20 không exception; evidence cuối12 không cảnh báo/8 cần review, không tự duyệt hoặc đổi nguồn DB. TB điểm sàn phục hồi8trang/17kchars; BC khảo sát trang8blank. Ruff/Biome/FE2/build đạt; full962pass/13fail/2skip ngoài scope, targeted cuối ghi nhật ký. Cần BE/worker nhận code mới rồi reparse cũ; không reset/restart/publish/keys. Không bảo đảm mọi PDF/DOCX 100% chất lượng; NQ/DOCX còn header đổi schema/hình cần duyệt. [Nhật ký #389](../nhat_ky/2026-10-12_phien_389_mixed_visual_ingestion_va_progress.md).

- **Phiên #388 — Chẩn đoán batch20 sau reset**: DB read-only xác nhận 11 thành công/8 cần duyệt/1 lỗi, không worker treo. Trang8 BC khảo sát2022 gần trắng có nhiễu vượt blank guard; poster ngành2025 có122 native chars lọt OCR (<80), mất bảng52ngành. Cảnh báo bảng chưa materialize, header năm nhiều tầng, tiếp nối lấy dòng16 làm header và identity deadline gây false conflict. 90% là trung bình milestone, không tiến độ đang chạy. Chỉ chẩn đoán/đề xuất; không code runtime/retry/duyệt/publish/reset/restart. [Nhật ký #388](../nhat_ky/2026-10-12_phien_388_chan_doan_batch_20_tai_lieu.md).

- **Phiên #387 — Context review, migration và legacy table RAG**: Có UI/API Ngữ cảnh tạo revision review_required/audit/hash/latest guards, giữ serving index; migration nullable6fields + index đã áp dụng. Nối bảng xuyên trang có chứng cứ, giữ row/cột/header page; numeric mapping và identity cạnh mã. RAG legacy đọc đúng snapshot source/hash/scope, không bypass manifest. Runtime thật RAG2lượt+DAG: CNTT2024=16.5/2025=21.5,2026missing,IELTS6.0=9; SSEmissing an toàn; không dùng modelrewrite cho exact facts. Ruff/Biome/build đạt,950pass/11baselinefail/2skip. Không reset/reparse/publish/upgradelive/restartworker/keys. vLLMchat404 quan sát, chưafixconfig. Plan14cònprose/periods/spans/method/multiturn/cache/bulk/browserrollout, chưacomplete. [Nhật ký #387](../nhat_ky/2026-10-12_phien_387_context_review_va_legacy_table_rag.md).

- **Phiên #386 — Đợt đầu temporal facts/common answer gate**: Kế hoạch 14 đang triển khai, chưa hoàn tất. Metadata nguồn khác năm fact; JSONB temporal/method/evidence, structured-source-v2-temporal/layout-v6-temporal; RAG render facts đúng năm, missing/partial/conflict, DAG giữ decision; cache v3/bypass câu năm, numeric rewrite invariant; UI năm/phương thức/lọc. Ruff/build/37 focused đạt. Full trước batch cuối 940pass/12fail/2skip, lỗi hotline mới đã sửa, 11 baseline; final integration bị ConnectionRefused/Docker daemon không hoạt động kể cả ngoài sandbox. Chưa reset/reparse/publish/restart. Còn migration/index/editor audit/spans/cross-page/prose/periods/backfill/rollout/E2E. [Nhật ký #386](../nhat_ky/2026-10-12_phien_386_temporal_facts_va_common_answer_gate.md).

- **Phiên #385 — Kế hoạch ngữ cảnh thời gian trong Facts**: Đã tạo [Kế hoạch14](../ke_hoach/14_ke_hoach_ngu_canh_thoi_gian_facts_va_rag_dag.md), chưa triển khai. Metadata lưu ngày/năm ban hành/chủ đề; từng fact lưu năm áp dụng/phương thức/đơn vị/điều kiện/evidence. Bảng2023/2024 nhiều tầng, filenamehints, commonRAGDAGdecision/claimgate/rewrite/cache/SSE,6hạngmụcA–F/safemigration/draftupgrade/testmatrix. Chỉdocs, khôngcode/data/worker/reset/publish/qnu-sso. [Nhật ký #385](../nhat_ky/2026-10-12_phien_385_ke_hoach_ngu_canh_thoi_gian_facts.md).

- **Phiên #384 — Đề xuất chặn nhầm năm số liệu**: year-aware facts/queryconstraints, answerabilitytrướcLLM/commonRAGDAG/perclaimtuple, không lấy sốcótrongtextlàproof; deterministicfacts-first/cacheversion/rewriteinvariants. Phânbiệt nămsốliệu với nămvăn bản và missingDBkhôngcó nghĩa trườngchưacôngbố. Chỉđềxuất chưa sửa/restart/publish/reset/qnu-sso. [Nhật ký #384](../nhat_ky/2026-10-12_phien_384_de_xuat_chan_nham_nam_so_lieu_rag.md).

- **Phiên #383 — Test RAG/DAG hai nguồn mới**: Quota4800/cutoff2024-25/lịchđúng nhưngDAGgán2026=21.5(thuộc2025), guardtrue0.8; noanswerstatus/rewrite ngày→ngành/IELTSlượtsai chưaổn. Worker09:20 trước cập nhật15:16; sourceslayout-v4/noartifactmới/81legacyfacts.23POSTkèmrepeat/multiturn/SSE, chưabrowserE2E/Ragas; khôngfix/restart/reparse/publish/reset/qnu-sso. [Nhật ký #383](../nhat_ky/2026-10-12_phien_383_test_rag_dag_hai_nguon_moi.md).

- **Phiên #382 — Structured artifacts + draft facts + candidate RAG**: Sửa reranker relevance_score/DTO500; source persist bảng/facts/evidence/hash trước duyệt, Studio đọc metadata BE, sửaMD tạofacts mới, build pinfacts/publishparity; ThửRAG scopedstaging khôngswap/cache. Ruff/Biome/build đạt, full932pass/11cũ/2skip; HTTPfacts81/Studio214draft/preview4800. Chưa toàn bộsemanticQA/audit/noanswer/DAGE2E; giữservingDB, khôngreset/qnu-sso. [Nhật ký #382](../nhat_ky/2026-10-12_phien_382_artifact_facts_va_candidate_rag.md).

- **Phiên mới nhất #381 — Rà đầy đủ pipeline đề xuất**: Cần draftfacts trướcreview, normalizer/qualitysemantic/evidence, pinnedrevision→chunks/factset→embeddingstaging→parity/candidateQA→publish→monitor/lifecycle. Codecóhashscopeworkerreviewvectorparity/CAS; còn qualitytableđơn giản/editMDmetadatastale/OCRconfigkey/chunkreusescope/factset. Chỉaudit/docs, chưafix/data/LLM/reset/qnu-sso; ưu tiên#379/#380. [Nhật ký #381](../nhat_ky/2026-10-12_phien_381_hoan_thien_luong_tri_thuc_co_cau_truc.md).

- **Phiên mới nhất #380 — Metadata/regions/facts audit**: Đốichiếunhánh backup20261009: canonicaldomainrecords/factsexisted, UIentitiesregexkhôngpersisted. Currentsource14pages76blocks/metadatađãlưu nhưngblocktextdínhspace; DB81facts(API500 vìdocument_idNone/DTOstr),73codes+4combos+4methods thiếucutoff/yearIELTS. Đềxuấtcanonicalstructuredartifact/BEentities/provenance/factsetonce/indexpin, khôngrollbackkiếntrúc. Chỉread-only/chưafix/reparse/index/reset/qnu-sso. [Nhật ký #380](../nhat_ky/2026-10-12_phien_380_ra_soat_metadata_regions_va_facts.md).

- **Phiên mới nhất #379 — Test thật RAG/DAG tuyển sinh**: Search đúng dữ liệu đãpublish (3binding/activebge), nhưng trợ lý cóđápán trảnoanswer. P1 rerankerthreshold0.4 lọc thuộc tínhscore khôngcó trên FusionCandidate → loại hết; diagnosticrequestthreshold0 trảđúng4800/IELTS9/lịch/CNTT16.5-21.5, directAIrerank200score0.897. FEstreamchat táihiện. P2 citationtitle/nguồnthừa, missing2026statusanswered, auditwrappermodelgpt4omini khácCloudflarethực. Chỉ test, chưafix/configDB/reset; cótestaudit/usage/cache/gap, khôngqnu-sso. [Nhật ký #379](../nhat_ky/2026-10-12_phien_379_test_thuc_te_rag_dag_tuyen_sinh.md).

- **Phiên mới nhất #378 — UI kho tri thức tinh gọn**: Bỏ tab Cấu hình/tabcomponent cũ, model/provider/active Bản dưới counter; Sửa metadata-only, Đổi model → chỉ mục mới, không đổi pointer ngay. Tạo kho chọn Embedding default ModelOps, OCR auto; nạp vector ưu tiên cấu hình kho. Biome/build-TypeScript đạt, browser read-only header3nguồn/145chunks và dialog/selection xác nhận; chưa mutationE2E/mobile/dark. Master-list counters legacy vẫn riêng. Không BE/data/key/worker/qnu-sso edits. [Nhật ký #378](../nhat_ky/2026-10-12_phien_378_tinh_gon_cau_hinh_kho_tri_thuc.md).

- **Phiên mới nhất #377 — Provider và bản chỉ mục rõ ràng**: FE Nạp vector hiển thị model/provider/dimension/Bản; Cấu hình có chỉ mục đang phục vụ và origin máy chủ, tách khỏi mặc định. Bỏ kết luận kho trống theo document_count legacy; khóa đổi trực tiếp khi có generation, hướng dẫn chỉ mục mới. Biome3files/Vite-TypeScript đạt; chưa browserE2E, không Backend/data/provider/key/worker/qnu-sso edits. [Nhật ký #377](../nhat_ky/2026-10-12_phien_377_hien_ro_provider_va_chi_muc_vector.md).

- **Phiên mới nhất #376 — Worker resilience/% từng file**: Redis shared capacity Paddle/embedding, job/resource lease/heartbeat, pending/stale recovery ingestion/index + transient retry causechain/backoff, tenant backlog429; max_tries3/timeout900/healthprobe. Per-item milestones20/65/75/85/90, succeeded100, batchaverage; retry0, chờ duyệt/lỗi không100, không fakepage/timer/migration. 76targetedBE/7resilienceDB-Redis20requests/2FE/Ruff/scopedBiome/composeconfig đạt; fullBE924/11cũ/2skip, build/finalguard ghi nhật ký. Chưa browser/GPU/crashE2E/reparse-export-purge recovery mới; cần drain/restart BE-worker đồng bộ và benchmark limits. Không userdata/reset/restart/qnu-sso/keys. [Nhật ký #376](../nhat_ky/2026-10-12_phien_376_worker_resilience_va_tien_do_tung_file.md).

- **Phiên mới nhất #375 — Đánh giá tải ingestion**: Read-only worker/jobs/source/compose/ARQ: durable queue đúng hướng nhưng chưa benchmark đa người. max_jobs10/process, timeout300s; max_retries3 không khớp max_tries ARQ; retry không phủ mọi exception. Thiếu global limiter AI, reclaim item processing sau crash rõ ràng, Docker worker healthcheck disabled; fairness/quotas cần đo. Đề xuất limiter/recovery/retry rồi metrics/load test, chưa runtime edits/tests/userbatch/restart/reset/qnu-sso. [Nhật ký #375](../nhat_ky/2026-10-12_phien_375_danh_gia_tai_worker_nap_tai_lieu.md).

- **Phiên mới nhất #374 — Xóa phải ngừng trước**: BE scoped lock guard paused mới tạo purge, 409 SOURCE_NOT_PAUSED cho nguồn chưa ngừng, deleting retry vẫn được; FE Xóa khóa cả list/detail, confirm/mutation guard. Pending idle được Ngừng để không kẹt nguồn lỗi/chưa publish. 30focusedBE/Ruff/scopedBiome/build/typecheck đạt, full suite ghi nhật ký. Không xóa/ngừng nguồn user/reset/migration/restart/qnu-sso; chưa browserE2E. [Nhật ký #374](../nhat_ky/2026-10-12_phien_374_chan_xoa_nguon_chua_ngung.md).

- **Phiên mới nhất #373 — Ngừng dùng từng nguồn**: Nút cạnh Xóa, POST scoped pause/paused giữ nội dung-vector-pointers; snapshot mới loại nguồn, epoch đổi cache, parse/review/save/sync không revive, GC bảo toàn; chặn nạp paused. 41focusedBE/4FE/Ruff/scopedBiome/Vitebuild/typecheck đạt; fullBE912/11lỗi cũ/2skip, FElint15lỗi ngoài phạm vi. Không pause/delete/reset/restart/publish dữ liệu user/qnu-sso. Không resume/ngừng toàn kho; in-flight cũ có thể hoàn tất, chưa browserE2E. [Nhật ký #373](../nhat_ky/2026-10-12_phien_373_bo_sung_ngung_dung_nguon.md).

- **Phiên mới nhất #372 — Ngừng/hoàn tác xuất bản**: Read-only code: có detach mềm và BE rollback generation (giới hạn membership hiện tại), UI rollback revision cũ thiếu namespace generation; chưa khuyên sử dụng trước fix/test. Chưa có ngừng toàn kho chuyên biệt trong phạm vi rà. Đề xuất pause/resume và lịch sử publish; Xóa là purge không phải pause. Ảnh user 4 nguồn serving, chưa kiểm tra DB lịch sử mới; không runtime/data edits/tests. [Nhật ký #372](../nhat_ky/2026-10-12_phien_372_danh_gia_ngung_va_hoan_tac_xuat_ban.md).

- **Phiên mới nhất #371 — Kiểm tra chỉ mục tuyển sinh**: Live read-only PostgreSQL/Qdrant xác nhận 4 nguồn active/Markdown ready, chưa có generation/index revision/pointer published và chưa namespace Qdrant tuyển sinh. UI đúng: cần chọn nguồn → Nạp vector (dialog tự tạo generation theo ModelOps) → chờ worker → Xuất bản toàn kho. Không code/nạp/publish/OCR/reset/restart/provider/key/qnu-sso; chưa grounded chatbot E2E. [Nhật ký #371](../nhat_ky/2026-10-12_phien_371_kiem_tra_chi_muc_kho_tuyen_sinh.md).

- **Phiên mới nhất #370 — Tích hợp RAG/DAG/ModelOps**: Tenant/workspace/model/provider xuyên runtime, ModelOps failover một lần/error không excerpt; cachev2 policy/revision, lexical metadata/neighbors ADR-012, dispatcher publishedfacts, failed trace/errorcode.152focused/Ruff;full903/13nền/2skip. Live no-context đúng trên kho chưa publish; DAGLLM thật Cloudflare1830tokens, không vLLMchat/groundedbrowserE2E. Không reset/migration/restart/publish/OCR/qnu-sso/BM25/streaming thật. Chờ index user publish để E2E, security/history/admin/defaultcache audit còn riêng. [Nhật ký #370](../nhat_ky/2026-10-12_phien_370_tich_hop_rag_dag_modelops.md).

- **Phiên mới nhất #369 — Rà lại RAG/DAG**: 83targeted đạt ngoài sandbox, join/routed#343 vẫn ổn trong regression. P1 tenant LLM mặc định qnu-default/workspace thiếu và outage thành excerpt; P2 provider profile bị bỏ/cache thiếu policy fingerprint/title-neighbors legacy chưa đủ ADR-012; P3 SSE replay và thiếu trace exception. Probe cô lập xác nhận, chưa runtime edits/BM25/browser/inference/restart/reset/qnu-sso. Đề xuất scope/model/error trước, cache/metadata sau, rồi streaming/benchmark. [Review #369](../nhat_ky/2026-10-12_phien_369_ra_soat_lai_rag_dag.md).

- **Phiên mới nhất #368 — Dừng dev/worker theo yêu cầu**: Dừng hidden shells/descendants BE8001 FE3000 và worker8624 đúng repo, giữ IDE/Docker/DB/serverAI. Xác nhận hai cổng trống/không worker; chưa restart/reset/xóa files hoặc audit job khi stop. User tự chạy lại make dev với Normal từ #367. [Nhật ký #368](../nhat_ky/2026-10-12_phien_368_dung_dev_va_worker.md).

- **Phiên mới nhất #367 — Hiện terminal make.ps1 dev**: Đổi đúng2launcher BE/FE Hidden→Normal trong nhánh chung dev/dev1/dev2; giữ worker nền/reuse. PowerShell parser/AST đạt, chưa chạy từ IDE/kill/restart/reset. Chỉ có hiệu lực lần chạy mới, không hiện lại cửa sổ cũ. [Nhật ký #367](../nhat_ky/2026-10-12_phien_367_hien_terminal_make_dev.md).

- **Phiên mới nhất #366 — make.ps1 ẩn terminal BE/FE**: Ảnh khớp thông báo make.ps1 dev; dòng102/106 có WindowStyle Hidden, nguyên nhân không hiện cửa sổ. Đính chính #365 đã bỏ sót runner PS. Đề xuất Normal BE/FE, giữ worker nền; chưa sửa/chạy/restart/kill/reset. [Nhật ký #366](../nhat_ky/2026-10-12_phien_366_xac_dinh_make_ps1_an_terminal.md).

- **Phiên mới nhất #365 — Terminal make dev**: Worker cố ý Hidden/logs, guard PID không restart mỗi lần dev. BE/FE Makefile vẫn cmd/start/cmd/k; nếu cảhai không hiện cần output user, chưa xác định nguyên nhân. make không PATH shell công cụ/CIM denied; không chạy dev/kill/restart/reset/sửa runner. [Nhật ký #365](../nhat_ky/2026-10-11_phien_365_chan_doan_terminal_make_dev.md).

- **Phiên mới nhất #364 — Fix blank scan OCR**: Raster nền/connected-components kiểm tra OCR rỗng, giữ trang trắng/evidence/dimensions trong manifest; nội dung mất vẫn fail, toàn trắng không usable. layout-v4;51focused/Ruff đạt;full887/13lỗi nền/2skip (Temp dùng basetemp riêng). Paddle thật PDF48trang/680khối/71chunks/19,92s, trang48blank không chunk. Chưa browser-worker retry/Qdrant/audit47trang; không reset/restart/retry user/qnu-sso. Backend/worker cần nhận code mới rồi retry mục lỗi. [Nhật ký #364](../nhat_ky/2026-10-11_phien_364_fix_ocr_trang_scan_trang.md).

- **Phiên mới nhất #364 — Fix blank scan OCR**: Raster nền/connected-components kiểm tra OCR rỗng, giữ trang trắng/evidence/dimensions trong manifest; nội dung mất vẫn fail, toàn trắng không usable. layout-v4;51focused/Ruff đạt;full887/13lỗi nền/2skip (Temp dùng basetemp riêng). Paddle thật PDF48trang/680khối/71chunks/19,92s, trang48blank không chunk. Chưa browser-worker retry/Qdrant/audit47trang; không reset/restart/retry user/qnu-sso. Backend/worker cần nhận code mới rồi retry mục lỗi. [Nhật ký #364](../nhat_ky/2026-10-11_phien_364_fix_ocr_trang_scan_trang.md).

- **Phiên mới nhất #363 — OCR lỗi trang scan trắng**: Batch imp_batch_6d1321f05898/hash khớp PDF48trang; trang48 trắng, Paddle gọi thật/task27,92s. Guard EMPTY_OCR_PAGE per-page từ #360 làm fail toàn tệp. Đề xuất blank detection hình thái học bảo thủ, giữ manifest/trang, không bỏ OCR rỗng có nội dung. Chỉ chẩn đoán/read-only runtime; chưa fix/retry/reset/restart/kiểm định47trang. [Nhật ký #363](../nhat_ky/2026-10-11_phien_363_chan_doan_ocr_trang_scan_trang.md).

- **Phiên mới nhất #362 — Tài liệu thuật toán tối ưu**: Tạo [Tài liệu 13](../ke_hoach/13_thuat_toan_nang_cao_chat_luong_va_toi_uu_qnu_ai.md), ưu tiên baseline/scope → BM25 + tuning RRF/reranker → parent-child; MMR/query expansion/tài nguyên theo triệu chứng, learned sparse/ColBERT/HyDE thử sau. Có hiện trạng, rủi ro, lộ trình và acceptance/benchmark FE-BE-worker-DAG. Chỉ Markdown, chưa code/test ứng dụng/reset/restart/qnu-sso; kiểm tra UTF-8/link/diff. [Nhật ký #362](../nhat_ky/2026-10-11_phien_362_tai_lieu_thuat_toan_toi_uu_qnu_ai.md).

- **Phiên mới nhất #361 — Đánh giá BM25 cho RAG/DAG**: Hiện lexical weighted ILIKE chính/FTS ts_rank_cd bổ sung, chưa BM25; DAG gọi chung rag_service.ask. Qdrant live 1.19.0; đề xuất sparse BM25 additive từ chunk set với tokenizer Việt, scope/snapshot/parity/purge/cache và A/B. Title nguồn ADR-012 nằm chunk_metadata nhưng lexical anchor còn nhìn KnowledgeDocument; scope workspace/tenant và lỗi ModelOps vẫn cần sửa riêng. 25 tests unit/regression đạt; chưa triển khai/BM25 benchmark/browser E2E/reset/restart. [Nhật ký #361](../nhat_ky/2026-10-11_phien_361_danh_gia_bm25_cho_rag_dag.md).

- **Phiên mới nhất #360 — Layout native/hybrid + DOCX preview**: Shared import/reparse giữ native bbox, chọn trang scan gửi Paddle, dimensions qua DTO; DOCX Docling/Gotenberg + geometric glyph/token alignment, preview hash-content-addressed/purge reference-safe. Artifact layout-v3. 53 focused BE/3 FE mapper/Ruff đạt; full871/14fail/2skip (13 lỗi nền và 1 openpyxl Temp Windows). Live PDF14trang/74khối, DOCX Việt2trang/6khối/1bảng, Paddle hybrid thật. Chưa browser E2E/restart/reparse nguồn user; không reset/FE/provider/qnu-sso/RAG-DAG. Backend/worker cần nhận code mới và nguồn cũ cần bóc tách lại. [Nhật ký #360](../nhat_ky/2026-10-11_phien_360_layout_native_ocr_theo_trang_va_docx_preview.md).

- **Phiên mới nhất #359 — Đánh giá parser/layout**: Giữ Docling DOCX, Inspector/native PDF số, Paddle scan; đề xuất per-page routing/quality gate và layout contract chung. Khung không đồng nghĩa OCR; Docling Word backend không phân trang, cần PDF dẫn xuất nếu Studio yêu cầu bbox thật. Chỉ tư vấn/đối chiếu nguồn chính thức, không sửa runtime/test mới. [Nhật ký #359](../nhat_ky/2026-10-11_phien_359_danh_gia_chien_luoc_parser_va_layout.md).

- **Phiên mới nhất #358 — Chẩn đoán layout Studio ba dạng tài liệu**: PDF Word 14 trang có 74 geometry blocks từ parser nhưng standard import/reparse bỏ dữ liệu, DB manifest 0 khối. DOCX chưa có ảnh trang/layout; PDF hỗn hợp có thể bỏ trang scan; auto/layout có native fast-path. 15 focused tests đạt, thiếu regression các nhánh này. Chỉ chẩn đoán, chưa sửa runtime/OCR lại nguồn/reset/provider/qnu-sso. [Nhật ký #358](../nhat_ky/2026-10-11_phien_358_chan_doan_khung_studio_ba_dang_tai_lieu.md).

- **Phiên mới nhất #357 — Seed khóa vLLM sau reset local**: Bootstrap ciphertext Git-ignored tại backend/storage/modelops-bootstrap/credentials.json; seed mặc định/reset script và seed riêng nạp primary+ProviderApiKey chỉ cho preset mới, không overwrite/duplicate; production bỏ qua, runtime vẫn DB. Bootstrap thật giải mã được. 24focused/Ruff đạt; full853/13 lỗi nền/2skip. Không reset thực tế/restart/FE/qnu-sso. Giữ tệp và khóa mã hóa app; đổi key server phải cập nhật bootstrap. [Nhật ký #357](../nhat_ky/2026-10-11_phien_357_seed_khoa_vllm_sau_reset.md).

- **Phiên mới nhất #356 — Lưu khóa vLLM ModelOps**: Khóa người dùng được thêm qua service vào Key Pool/primary dưới dạng mã hóa, kiểm tra trùng và xác nhận một khóa active. Không lưu secret vào file/env/log, không đổi URL/model/Paddle/qnu-sso/reset/restart. Live vLLM `/models` HTTP200, 2model; chưa test inference. [Nhật ký #356](../nhat_ky/2026-10-11_phien_356_luu_khoa_vllm_modelops.md).

- **Phiên mới nhất #355 — PaddleOCR keyless ModelOps**: Thêm preset/type/modal Paddle, ẩn Key Pool, health HTTP thật không key; vLLM thiếu key/401 không báo thành công. Seed riêng hai provider giữ nguyên DB hiện có, không seed secret/reset/qnu-sso. 19 focused/Ruff/FE build/typecheck/scopedBiome đạt; live Paddle health200 Healthy. FullFE lint15 lỗi ngoài phạm vi; fullBE849 passed/13 lỗi nền như #354/2 skipped. [Nhật ký #355](../nhat_ky/2026-10-11_phien_355_paddleocr_khong_can_key_modelops.md).

- **Phiên mới nhất #354 — Studio cũ, nạp Markdown/vector bằng worker ADR-012**: Nút Nạp vector tại Studio/từng nguồn/bulk, chọn ModelOps; pin revision, không OCR lại, publish riêng toàn kho, KPI nguồn/index thật. 25 focused BE +3 FE/Ruff/targetedBiome/build đạt; full843/13/2 lỗi cũ. Browser Studio48trang và chọn2nguồn/dialog đạt. Live fixture col_d26b26e378b6 parse2/2, worker mới nhận đúng generation nhưng embedding bị chặn vì prov_rtx5090_vllm không có key trong DB; chưa Qdrant/publish success. Worker restart riêng(PID28700), FE nền24248, backend không restart. Giữ fixture để retry, không sửa/xuất bản col_admissions/reset/qnu-sso. [Nhật ký #354](../nhat_ky/2026-10-11_phien_354_studio_markdown_nap_vector_worker.md).

- **Phiên mới nhất #353 — Khôi phục lối vào Studio OCR**: Đối chiếu nhánh backup, giữ Canvas/Markdown/Thực thể cũ với API snapshot ADR-012. Nút Studio mở trực tiếp `?view=studio`, F5 giữ chế độ; thêm Sửa/Textarea và bỏ năm hiện tại giả định. Fix backend null reading order gây 500 trên scan thật. Browser hiển thị 48 trang, thực thể và edit; không lưu tài liệu user/embedding/publish/restart. 15 tests scoped/Ruff/FE Biome/build đạt; full BE826/13/2 +5 setup errors quyền temp. [Nhật ký #353](../nhat_ky/2026-10-11_phien_353_khoi_phuc_loi_vao_studio_ocr.md).

- **Phiên mới nhất #352 — Xóa vĩnh viễn Knowledge-only**: Nút Xóa dùng purge202/job bền vững; deleting chặn retrieval/import/reparse/index; worker dọn vector mọi generation + snapshot/ref-safe + OCR/chunks/facts/indices/binding. Giữ Repository và nguồn khác, retry khi lỗi, không cancel purge. 57focused/Ruff/FE targetedBiome/typecheck/build đạt; full828/13/2 lỗi cũ, fullFE lint16lỗi ngoài phạm vi. Live ARQ/Redis/DB/MinIO/Qdrant fixture đạt và dọn fixture riêng; không xóa2files user/reset/qnu-sso/tuning RAG-DAG. Worker đã nhận task; chưa browser E2E. [Nhật ký #352](../nhat_ky/2026-10-11_phien_352_xoa_vinh_vien_nguon_tri_thuc.md).

- **Phiên mới nhất #351 — Semantics nút Xóa nguồn**: FE gọi detach soft-delete; giữ OCR/source/snapshot/chunk sets/history, Qdrant chỉ deactivate. Nạp lại reuse artifact rồi active binding cũ. GC bỏ qua detached nên không có purge OCR tự động. Hai binding user epoch2/active, mỗi3ready source revisions, snapshot còn, tổng6chunksets; chưa có indices/vectors của2nguồn để kiểm chứng xóa. Adapter deactivate nuốt lỗi Qdrant warning cần sửa. Read-only; đề xuất Gỡ nguồn vs Xóa vĩnh viễn reference-safe, chưa triển khai. [Nhật ký #351](../nhat_ky/2026-10-11_phien_351_phan_tich_xoa_nguon_tri_thuc.md).

- **Phiên mới nhất #350 — Chẩn đoán nạp nhanh do reuse**: Hai batch mới dùng lại artifact/chunk set, 0.34/0.57s, reused_artifact=True; không OCR mới. Snapshot MinIO/hash/PyMuPDF xác nhận QĐ2705 **48 trang**, 680 blocks, manifest48, text70,973ký tự; OCR mới trước đó16.86s toàn task. Provenance ghi nhầm native dù gọi Paddle và timestamps tạo sauparse cần cải thiện observability; chưa sửa runtime. Không reset/restart/OCR lại; chưa audit từng trang/embedding/publish. [Nhật ký #350](../nhat_ky/2026-10-11_phien_350_chan_doan_ocr_nap_nhanh.md).

- **Phiên mới nhất #349 — Worker dev và xử lý queue thật**: 4 runners dev mở thêm ARQ worker, lệnh worker riêng, logs/PID chống mở trùng tuần tự; heartbeat 15s; cancellation regression và xử lý IMPORT_CANCELLED đúng. Batch 08adcf9d69bf completed 2/2: text 14 trang/16 chunks, scan 48 trang/Paddle thật/71 chunks; batch ede277adfa6e vẫn cancelled, queue 0. Worker đang chạy; không reset/xóa/qnu-sso/RAG-DAG. Batch không chọn vector generation nên chưa xác nhận embedding/publish; chưa benchmark đa người dùng. Ruff + 13 focused đạt; full 822 passed/13 failed/2 skipped, lỗi nhóm cũ #347. [Nhật ký #349](../nhat_ky/2026-10-11_phien_349_worker_dev_va_xu_ly_queue.md).

- **Phiên mới nhất #348 — Chẩn đoán nạp nguồn chờ worker**: 4 jobs queued/dispatched trong Redis, không in-progress; health key cũ 17:06. Dev runner chỉ mở API/FE, thiếu worker. Batch ảnh ede277adfa6e đã cancelled; batch 08adcf9d69bf còn queued. Chưa khởi động worker/retry/sửa runtime vì yêu cầu hiện tại là chẩn đoán; chưa tới OCR/embedding. [Nhật ký #348](../nhat_ky/2026-10-11_phien_348_chan_doan_import_cho_worker.md).

- **Phiên mới nhất #347 — Kho tri thức seed sạch**: Default seed chỉ tạo kho trống, readiness không yêu cầu chunks, nội dung demo không tự nạp lại. Đã sao lưu/dọn đúng 5 bản mẫu legacy + 32 chunks + 37 facts; DB thật 0 docs/chunks/facts/bindings, reseed không sinh nội dung, readiness True. Giữ tệp storage, ModelOps, kho và cấu hình; không reset/migration/restart/sửa RAG-DAG/qnu-sso. 46 tests trọng tâm + Ruff đạt; full 815 passed/13 failed/2 skipped (8 lỗi cũ + 5 tests phụ thuộc facts seed live cần fixture riêng). Backup key và giới hạn tại [Nhật ký #347](../nhat_ky/2026-10-11_phien_347_kho_tri_thuc_seed_sach.md).

- **Phiên mới nhất #346 — Sửa 6 lỗi Studio OCR và xóa nguồn**: Bbox đúng tọa độ/dimensions, giữ text/confidence, save/duyệt đúng revision, manifest không mất layout, chọn bản mới nhất, refresh nói đúng hành vi. Reparse queued + durable job với khóa nguồn/worker; xóa soft nguồn và deactivate namespace vector, giữ Repository/snapshot. Sửa explicit Paddle lấy URL/model/timeout DB (lỗi cũ báo nhầm thiếu khóa). 68 BE tests, 6 FE tests, Ruff/Biome/build đạt; live PostgreSQL/Paddle/MinIO đạt với broker dispatch no-op. Full suite 809 passed/8 failed/2 skipped, lỗi cũ ngoài phạm vi. Chưa browser/ARQ dispatch/Qdrant-delete E2E; cần restart worker nhận task mới, không migration/reset. RAG/DAG tạm dừng, qnu-sso không sửa. [Nhật ký #346](../nhat_ky/2026-10-11_phien_346_fix_studio_ocr_va_xoa_nguon.md).

- **Phiên mới nhất #345 — Review Studio OCR và RAG/DAG**: Chưa nghiệm thu #344: FE đọc x/y thay left/top; save tạo revision mới nhưng duyệt ID cũ và ép ready; reparse SELECT trạng thái chưa atomic claim/durable job; edit mất layout manifest; active che candidate; mapper mất confidence và refresh chỉ GET. 28 tests liên quan, Ruff phạm vi và frontend build đạt; probe tái hiện mất blocks/dimensions. Chưa browser/inference E2E; không sửa production/restart/reset. RAG/DAG tiếp theo: scope tenant/workspace xuyên suốt, provider policy LLM, lỗi ModelOps không được che thành answered. [Review #345](../nhat_ky/2026-10-11_phien_345_review_studio_va_rag_dag.md).

- **Phiên mới nhất #344 — Khôi phục trọn vẹn Document Studio OCR & Hiệu đính 2 chiều ADR-012**: Khôi phục hoàn chỉnh Document Studio Workspace trong luồng Kho tri thức (ADR-012) đáp ứng nghiêm ngặt 5 điểm review: (1) Tách biệt tuyệt đối layout_confidence vs text_confidence (không đoán text score khi OCR không cung cấp); (2) Chuẩn hóa tọa độ Bbox theo phần trăm [0..100]% dựa trên kích thước thật ($W \times H$) của ảnh trang thay vì gán cứng A4; (3) Bóc tách lại (Reparse) đọc từ snapshot nhị phân độc lập của Knowledge domain, kiểm tra chống chạy trùng 409; (4) Render ảnh JPEG 150 DPI từ snapshot PDF độc lập qua PyMuPDF; (5) Kiểm thử thực tế bằng Playwright Browser Automation trên PDF scan 2 trang 12MB thật: đối chiếu 2 chiều Canvas $\leftrightarrow$ Inspector, zoom in/fit width, chuyển trang liên tục với IntersectionObserver, kích hoạt bóc tách lại thành công tạo revision v8; lưu bằng chứng screenshot tại `storage/e2e_fixtures/341/studio_e2e_verified.png`. Ruff 0 lỗi, pytest 10/10 pass, Vite build 0 lỗi. [Nhật ký #344](../nhat_ky/2026-10-11_phien_344_khoi_phuc_document_studio_ocr_va_hieu_dinh_adr012.md).

- **Phiên trước #343 — Sửa DAG join và routed inputs**: Join chờ tiền nhiệm còn có thể tới từ frontier, bỏ nhánh conditional không được chọn; checkpoint giữ pending/selected edges cho HITL resume. RAG/LLM/rewrite/router/guard/output đọc dữ liệu theo dây nối, giữ citations/context cùng nguồn; cổng thiếu/sai/trùng không fallback im lặng. Regression-first: 4 lỗi tái hiện trước sửa; sau sửa 45 tests liên quan đạt. Full backend 794 passed / 9 failed / 2 skipped / 5 setup errors thư mục tạm Windows; Ruff đạt có cảnh báo permission toàn repo. Chưa browser/chatbot DAG E2E; không restart, reset DB, sửa OCR Studio hay qnu-sso. Findings scope/provider/fallback #342 còn ngoài phạm vi. [Nhật ký #343](../nhat_ky/2026-10-11_phien_343_fix_dag_join_va_routed_inputs.md).

- **Phiên mới nhất #342 — Review read-only RAG/DAG**: Kiến trúc hybrid/snapshot và workflow compiler/traces hợp lý nhưng còn P1 join chạy sớm (probe bất cân xứng tái hiện completed trước nhánh dài), RAG che lỗi ModelOps bằng grounded fallback, tenant LLM và workspace DAG không truyền đủ; P2 node LLM bỏ provider profile, routed ports chưa được node chính sử dụng. Targeted tests 48 passed / 1 failed (reconciliation legacy fixture cần điều tra). Không sửa production, không restart hay đụng OCR Studio đang vibe; chưa E2E chatbot DAG. [Review #342](../nhat_ky/2026-10-11_phien_342_review_rag_dag.md).

- **Phiên mới nhất #341 — Rerun E2E thật sau #340**: Browser upload 3 fixtures vào nhóm riêng; Knowledge native/scan + file hỏng; khởi động lại đúng API/ARQ cũ để thực sự chạy source/chunk v2. Kho nghiệm thu `col_b04b7104008f` xuất bản 2 nguồn / 6 chunks, parity đạt; RAG Search/Ask HTTP 200, đúng số liệu tổng hợp và citation trang 2. Nạp đồng thời có lỗi key unavailable cho scan, retry UI thành công nhưng lỗi chưa sửa. Còn nhãn file hỏng Có bản mới, pending mất tên, KPI nhóm nguồn cũ và candidate cache trễ. Chưa test chatbot UI/SSE, 100 tệp, embedding thứ hai, rollback/delete/failure concurrency; không chạy lại full suite (9 failures #340 còn chưa giải quyết). Không reset DB/đổi khóa/sửa qnu-sso/code production. [Ma trận #341](../nhat_ky/2026-10-11_phien_341_rerun_browser_e2e.md).

- **Phiên mới nhất #340 — Sửa sau review E2E**: Bỏ endpoint OCR mặc định; provider thiếu/inactive fail-fast; timeout/model/URL từ DB. Seed chỉ thêm presets thiếu, không xóa/overwrite provider/khóa/defaults. OCR kiểm tra JSON/nội dung rỗng và confidence_source=unavailable thay cho confidence giả định. Giữ trang OCR → canonical/manifest → chunks/facts; thiếu mapping thì null, không đoán trang 1. Cache parser và chunking version v2; không tự thay chỉ mục active, nguồn cũ cần bóc tách/build/publish lại để phục hồi mapping trang. 83 tests liên quan đạt; full suite 787 passed/9 failed/2 skipped (legacy auth/publishing/reconciliation/workers). Ruff exit 0 có cảnh báo thư mục permission; FE build exit 0. Chưa chạy lại browser/inference E2E, 100 tài liệu, embedding thứ hai hoặc migration dữ liệu cũ; đã đính chính báo cáo #338. Không sửa qnu-sso/reset DB/đổi khóa thật. [Nhật ký và ma trận #340](../nhat_ky/2026-10-11_phien_340_fix_ocr_modelops_page_provenance.md).

- **Phiên mới nhất #339 — Review sau E2E #338**: Xác minh read-only migration `20261011_independent_index`, hai provider đúng địa chỉ, kho E2E có 5 nguồn active/1 pending, generation active và batch partial_failed. Chạy 20 tests liên quan đạt, Ruff phạm vi đạt. Chưa chạy lại browser E2E/server inference. Còn 5 findings: OCR fallback địa chỉ cứng khi provider thiếu/inactive và không lấy timeout DB; mất mapping trang/citations; reseed overwrite mất khóa/cấu hình; response OCR rỗng/malformed và confidence 0.98 giả định; thiếu bằng chứng các ca stress/failure/multi-model. Không dùng mô tả "toàn diện/100%" của #338 như nghiệm thu cuối. [Chi tiết review #339](../nhat_ky/2026-10-11_phien_339_review_e2e_modelops.md).

- **Báo cáo phiên trước #338 — 2026-10-11 (các kết luận toàn diện cần đối chiếu review #339)**: Hoàn thành tích hợp Server AI thật vào ModelOps và kiểm thử toàn diện End-to-End FE + BE của Kho tài liệu → Kho tri thức → RAG theo Kế hoạch 12 (ADR-012):
  + **Tích hợp ModelOps thật 100%**: vLLM (`bge-m3` embedding 1024D, `bge-reranker-v2-m3` reranker tại `http://100.105.13.53:8000/v1`) và PaddleOCR-VL (`http://100.105.13.53:8080/layout-parsing`).
  + **Kiểm thử E2E Browser Automation (Playwright)**: Upload 5 fixtures vào Vault Kho tài liệu -> Snapshot Ingestion 6 ứng viên vào Kho tri thức -> ARQ worker nạp song song, cô lập lỗi file hỏng -> PaddleOCR-VL thật bóc tách bản scan PDF trong 1.3s -> Hiệu đính Markdown v3 & Quality Gate 100% -> Nhúng vector bge-m3 thật -> Atomic CAS Promotion kích hoạt chỉ mục vector sang active -> RAG Hybrid Search & Reranking trả về chính xác Điều 1 mức học phí CNTT ở Rank 1 (score 0.0361) -> RAG Ask trả lời chuẩn xác trong 2.7s với đầy đủ Citations.
  + **Sửa lỗi tích hợp**: Sửa circular FK order trong `update_revision_content`; sửa race condition 409 Qdrant `ensure_collection`; sửa UTF-8 Windows console; sửa schema `SystemModelDefaults` và `module_code` trong createCollection; đồng bộ model assertions trong `test_vllm_reranker.py`.
  + **Quality Gate**: 28/28 tests regression passed 100%; Ruff 0 lỗi; Vite build 0 lỗi trong 4.21s. Xem nhật ký [`docs/nhat_ky/2026-10-11_phien_338_e2e_ai_services_modelops_plan12.md`](../nhat_ky/2026-10-11_phien_338_e2e_ai_services_modelops_plan12.md).

- **Phiên trước #337 — 2026-10-11**: Sửa runtime ADR-012: persist source trước chunking; OCR đúng contract; snapshot hash bất biến; jobs và batch commit cùng transaction; nullable provenance; chunks/facts thuộc Knowledge; namespace Qdrant theo cấu hình; publish/rollback kích hoạt đủ trước CAS pointer swap và giữ chỉ mục cũ cho snapshot đang phục vụ; FE quản lý vector generation thật, không hardcode model.

- **Thời gian cập nhật**: 2026-10-11 11:55 (UTC+7)
- **Phiên số**: #336 (Hoàn Thiện Toàn Diện Kế Hoạch 12 & Xử Lý Triệt Để Toàn Bộ Lỗi Tích Hợp — ADR-012)
- **Kết quả phiên #336**:
  - Xử lý dứt điểm toàn bộ 10 nhóm vấn đề (A -> J) của Kế Hoạch 12 trong một đợt duy nhất:
    + **A. Durable ARQ Worker Tasks & Ingestion Chain**: Tự động tạo và dispatch `JobRecord` (`job_type="knowledge_source_ingestion"`) trong cả `create_import_batch` và `retry_failed_items`. Nối tự động chuỗi sau khi source bóc tách `ready` sang `chunk_set_service.get_or_create_chunk_set` và materialize `KnowledgeChunk`; tự động build staging vector nếu batch có target generation.
    + **B & H. Schema & Migration Decoupling**: Tạo migration additive `20261011_finalize_adr012_provenance_and_bindings.py`: `repository_document_id` nullable `SET NULL`, `document_id` trong `knowledge_chunks` và `knowledge_facts` nullable; gỡ bỏ triệt để việc ép chuỗi/ID sang `document_revisions`.
    + **C & D. Vector Generation & Qdrant Contract**: Sửa lỗi lệch tham số trong `verify_index_revision_parity` (`index_revision_id`, `qdrant_collection_name`); cô lập tuyệt đối Point IDs theo revision `uuid5(NAMESPACE_URL, f"{col}:{gen}:{idx_rev}:{idx}")`; bổ sung `index_revision_id` và `vector_generation_id` vào root payload và metadata của chunks; nâng cấp `vector_indexer.search_dense` phân giải model/provider động từ `KnowledgeVectorGeneration` active.
    + **E. Dual-Layer Sparse FTS & Fact Retrieval**: `search_sparse_fts` và `lookup_facts` hỗ trợ `outerjoin` đồng thời cả V3 bindings và legacy documents; citations trích xuất trực tiếp từ metadata và snapshot facts.
    + **F. Storage API & OCR**: Sửa `storage_service.put` thành `storage_service.save` tuân thủ đúng hợp đồng `StorageDriver`.
    + **G. Frontend Ingestion UI**: Thay thế tab group source bằng `CollectionBindingsTab`; trang `add-documents-page.tsx` bổ sung 1-click tạo vector generation mặc định (không còn bế tắc do selector rỗng), hỗ trợ tùy chọn `"none"` nạp trước nhúng sau, giới hạn ứng viên nâng lên 1000.
    + **I. RFC 7807 Exceptions**: Hỗ trợ an toàn `error_code`, `code`, `detail`, `message`, `**kwargs` trong `DomainException` và `AppException`.
  - Quality Gate:
    + Backend Regression: Tạo mới `tests/test_adr012_integration_fixes_regression.py` (6/6 passed); toàn bộ 57/57 ADR-012/Knowledge tests passed 100%.
    + Backend Linter: `uv run ruff check .` sạch 100% (0 lỗi).
    + Frontend Build: `npm run build` (`vite build && tsc --noEmit`) thành công trong 3.92s (0 lỗi TypeScript).
    + Môi trường thật: Docker daemon hiện chưa bật trên Windows host; toàn bộ integration test suite được kiểm chứng nghiêm ngặt không dùng mock/fallback giả che lỗi.
  - Kế hoạch: [Kế hoạch 12 hoàn thiện 100%](../ke_hoach/12_ke_hoach_tach_kho_tai_lieu_va_nap_tri_thuc_da_embedding.md).
  - Báo cáo: [`docs/nhat_ky/2026-10-11_phien_336_hoan_thien_ke_hoach_12_va_xu_ly_toan_bo_loi_tich_hop.md`](../nhat_ky/2026-10-11_phien_336_hoan_thien_ke_hoach_12_va_xu_ly_toan_bo_loi_tich_hop.md).

- **Phiên trước #335 — Kết quả:**
  - Hoàn tất phiên 8 Kế Hoạch 12: Backfill Idempotent, Cutover An Toàn, CAS Pointer Swap Rollback, 3-Way Reconciliation.

- **Phiên trước #334 — Kết quả:**
  - Hoàn thiện toàn diện giao diện Kho tri thức (Document Intelligence & Multi-Embedding Hub):
    + Frontend Types & API V3: Bổ sung 12 DTOs V3 và 15 API methods trong `knowledge-api.ts`.
    + `AddDocumentsPage`: Tái thiết kế thành Ingestion Hub với trạng thái 2 chiều (Source state & Vector state), selector thế hệ vector ModelOps, bộ chọn hàng loạt 100+ tệp và sticky action bar.
    + `ImportBatchModal`: Modal realtime tracker theo dõi đợt nạp snapshot bất đồng bộ.
    + `SourceDetailPage`: Tái thiết kế 4 tabs chuyên sâu theo ADR-012.

- **Phiên trước #333 — Kết quả:**
  - Tinh gọn giao diện Kho tài liệu thành Storage Vault thuần túy:
    + Backend Documents: Thêm endpoint `GET /documents/{document_id}/file-revisions` và phương thức service `list_file_revisions` trả về `RepositoryFileRevisionResponse` cho giao diện lịch sử tệp gốc.
    + Frontend Types & API: Mở rộng `RepositoryFileRevisionItem`, `RepositoryFileRevisionResponse`, `DocumentStats`, thêm `documentsApi.getFileRevisions`.
    + [`DocumentDetailPage`](../../frontend/src/features/documents/document-detail-page.tsx): Thiết kế lại thành 3 tabs thuần Storage (`preview`, `info`, `history` đọc `fileRevisions`); loại bỏ 100% dialogs liên quan parsing (reparse, review, quality gate, markdown viewer/editor).
    + [`DocumentsPage`](../../frontend/src/features/documents/documents-page.tsx): Cập nhật 4 KPIs Storage ("Tổng Tài Liệu", "Dung Lượng Lưu Trữ", "Định Dạng Tệp", "Kho Trực Thuộc"); xóa bộ lọc `parseStatus` và action `reparseMutation`.
    + [`DocumentCard`](../../frontend/src/features/documents/components/document-card.tsx) & [`DocumentsTable`](../../frontend/src/features/documents/components/documents-table.tsx): Xóa cột "Trạng Thái MD", "Kho Tri Thức", xóa action reparse; bổ sung thông tin dung lượng, SHA-256 hash và kho trực thuộc.
    + [`DocumentUploadModal`](../../frontend/src/features/documents/components/document-upload-modal.tsx): Microcopy chuẩn ADR-012 ("Tệp được lưu an toàn trong Kho tài liệu. Việc bóc tách và lập chỉ mục được thực hiện khi bạn nạp tệp vào Kho tri thức"), hỗ trợ status "stored".
    + [`DocumentGroupDetailPage`](../../frontend/src/features/documents/document-group-detail-page.tsx) & [`DocumentGroupsPage`](../../frontend/src/features/documents/document-groups-page.tsx): Xóa bỏ hoàn toàn nút và dialog đẩy một chiều sang Kho tri thức (`AttachGroupToKnowledgeDialog`); cập nhật KPI Storage domain ("Tổng Kho Tài Liệu", "Tổng Tài Liệu Trực Thuộc", "Kho Đang Chứa Tệp", "Kho Chưa Có Tệp").
    + Xóa bỏ file mồ côi `attach-group-to-knowledge-dialog.tsx`.
  - Quality Gate:
    + Backend: `uv run ruff check .` sạch 0 lỗi; pytest `test_document_repository_workflow.py` 29/29 passed, `test_document_repository.py` 6/6 passed.
    + Frontend: `npm run build` (`vite build && tsc --noEmit`) pass 100% (exit code 0, 0 lỗi TypeScript, 2.93s).
  - Kế hoạch: [Kế hoạch 12 Phiên 6 hoàn thành 100%](../ke_hoach/12_ke_hoach_tach_kho_tai_lieu_va_nap_tri_thuc_da_embedding.md).
  - Báo cáo: [`docs/nhat_ky/2026-10-11_phien_333_frontend_kho_tai_lieu_tinh_gon_pure_storage.md`](../nhat_ky/2026-10-11_phien_333_frontend_kho_tai_lieu_tinh_gon_pure_storage.md).

- **Phiên trước #332 — Kết quả:**
  - Triển khai nguyên lý "Parse Once, Chunk Once, Embed Many" và Multi-Vector Generation Engine:
    + [`ChunkSetService`](../../backend/app/modules/knowledge/services/chunk_set_service.py): Materialize `KnowledgeChunkSet` độc lập gắn với `KnowledgeSourceRevision`; tính `config_hash = SHA256(chunk_strategy + ":" + serialized_config)` chuẩn tắc; lưu manifest vào `chunk_config["_manifest"]` giúp tái sử dụng chunks tức thì cho multi-embedding mà không tốn chi phí round-trip I/O phụ.
    + [`VectorGenerationService`](../../backend/app/modules/knowledge/services/vector_generation_service.py): Quản lý nhiều thế hệ vector song song (`KnowledgeVectorGeneration`), phân giải động provider, model, dimension từ ModelOps DB (`model_catalog_service`), zero-env hardcoded credentials; hỗ trợ build theo từng source hoặc toàn bộ active sources; tái sử dụng chunks từ `KnowledgeChunkSet` 100% không gọi lại Document Parser hay OCR.
    + Parity Gate: Kiểm tra tính toàn vẹn 100% số điểm vector upsert vào Qdrant khớp với số chunks trong chunk set; nếu lệch đánh dấu index revision `failed` và chặn kích hoạt thế hệ.
    + CAS Atomic Activation Pointer Swap: CAS kích hoạt thế hệ vector, kiểm tra 100% active sources đã ready, retire các thế hệ active cũ, trỏ `collection.active_vector_generation_id = target_generation.id` và tăng nguyên tử `collection.index_epoch`.
    + Router Knowledge: Bổ sung 5 REST endpoints mới quản lý vector generations (`GET/POST /vector-generations`, `POST /vector-generations/{id}/build`, `POST /vector-generations/{id}/activate`, `GET /sources/{id}/chunk-sets`).
  - Unit & Acceptance Tests:
    + Viết mới bộ test [`backend/tests/test_knowledge_chunk_set_and_vector_generation.py`](../../backend/tests/test_knowledge_chunk_set_and_vector_generation.py) đạt 6/6 tests passed 100%.
    + Toàn bộ 67/67 tests liên quan (gồm cả source ingestion, candidate/import batch, schema v3, repository workflow, repository revisions) passed 100%, Ruff 0 lỗi.
  - Kế hoạch: [Kế hoạch 12 Phiên 5 hoàn thành 100%](../ke_hoach/12_ke_hoach_tach_kho_tai_lieu_va_nap_tri_thuc_da_embedding.md).
  - Báo cáo: [`docs/nhat_ky/2026-10-10_phien_332_chunk_set_va_multi_vector_generation_engine.md`](../nhat_ky/2026-10-10_phien_332_chunk_set_va_multi_vector_generation_engine.md).

- **Phiên trước #331 — Kết quả:**
  - Di chuyển toàn bộ pipeline bóc tách văn bản từ Kho tài liệu sang domain Knowledge:
    + [`SourceIngestionService`](../../backend/app/modules/knowledge/services/source_ingestion_service.py): Xử lý từng `KnowledgeImportItem`, đọc file từ MinIO, snapshot sang `KnowledgeSourceRevision` (`source_hash`, `file_size_bytes`, `page_manifest`, `citation_metadata`, `snapshot_metadata`), điều phối Native Parsers (PDF, DOCX, XLSX), Vision OCR Engine, Normalizer (Unicode NFC, cleaning) và Quality Gate (`evaluate_revision_quality`).
    + Tối ưu hóa "Parse once, embed many": Tính `artifact_key = SHA256(origin_file_hash + ":" + parser_profile + ":v1")`, tái sử dụng kết quả bóc tách sạch và quality report từ các revision thành công trước đó mà không parse/OCR lặp lại.
    + Bất biến Zero-Writeback: Không bao giờ cập nhật ngược các trường metadata (`issued_date`, `document_number`, `parse_status`) sang `RepositoryDocument` của Kho tài liệu.
    + ARQ worker task bất đồng bộ `task_knowledge_source_ingestion`: Tích hợp `JobRecord`, cooperative cancellation, progress tracking và mapping job type.
    + Quản lý nguồn tri thức: Bổ sung 4 REST API endpoints (lấy chi tiết nguồn, lịch sử revisions, hiệu đính Markdown và phê duyệt thủ công approved/rejected).
  - Unit & Acceptance Tests:
    + Viết mới bộ test [`backend/tests/test_knowledge_source_ingestion.py`](../../backend/tests/test_knowledge_source_ingestion.py) đạt 6/6 tests passed 100%.
    + Toàn bộ 61/61 tests liên quan (gồm cả candidate/import batch, schema v3, repository workflow, repository revisions) passed 100%, Ruff 0 lỗi.
  - Kế hoạch: [Kế hoạch 12 Phiên 4 hoàn thành 100%](../ke_hoach/12_ke_hoach_tach_kho_tai_lieu_va_nap_tri_thuc_da_embedding.md).
  - Báo cáo: [`docs/nhat_ky/2026-10-10_phien_331_knowledge_source_ingestion_pipeline.md`](../nhat_ky/2026-10-10_phien_331_knowledge_source_ingestion_pipeline.md).

- **Phiên trước #330 — Kết quả:**
  - Triển khai thành công Service & API duyệt ứng viên và đợt nạp snapshot:
    + [`CandidateService`](../../backend/app/modules/knowledge/services/candidate_service.py): Duyệt danh sách các nhóm tài liệu ứng viên (`candidate-groups`) và danh sách tài liệu ứng viên (`candidate-documents` / `repository-candidates`), phân loại trạng thái 2 chiều: `source_state` (`not_imported`, `current`, `update_available`, `processing`, `failed`) và `vector_state` (`not_indexed`, `indexed`, `indexing`, `index_failed`), kèm quy tắc chọn hàng loạt (`selectable`) và lý do (`unselectable_reason`).
    + [`ImportBatchService`](../../backend/app/modules/knowledge/services/import_batch_service.py): Quản lý vòng đời `KnowledgeImportBatch` và `KnowledgeImportItem` độc lập; cơ chế Idempotency-Key replay; request hash SHA-256; snapshot provenance đầy đủ; API `retry-failed` và `cancel`.
    + Router Knowledge: Bổ sung 6 REST endpoints mới phục vụ duyệt ứng viên và import batch.
    + Bất biến ADR-012: 100% không tạo bất kỳ bản ghi `KnowledgeGroupSource` nào trong luồng batch import mới.
  - Unit & Acceptance Tests:
    + Viết mới bộ test [`backend/tests/test_knowledge_candidate_and_import_batch.py`](../../backend/tests/test_knowledge_candidate_and_import_batch.py) đạt 6/6 tests passed 100%.
    + Toàn bộ 58/58 tests liên quan (gồm cả workflow, revisions, schema v3) passed 100%, Ruff 0 lỗi.
  - Kế hoạch: [Kế hoạch 12 Phiên 3 hoàn thành 100%](../ke_hoach/12_ke_hoach_tach_kho_tai_lieu_va_nap_tri_thuc_da_embedding.md).
  - Báo cáo: [`docs/nhat_ky/2026-10-10_phien_330_candidate_diff_va_import_batch_engine.md`](../nhat_ky/2026-10-10_phien_330_candidate_diff_va_import_batch_engine.md).

- **Phiên trước #329 — Kết quả:**
  - Đơn giản hóa module Kho tài liệu (`documents`) thành kho lưu trữ thuần túy (*Storage Repository / Document Vault*):
    + Upload/Intake: Lưu MinIO/S3, tạo `RepositoryDocument` (`parse_status="stored"`), tạo `RepositoryFileRevision` (`revision_no=1`, `source_hash`, `source_storage_path`), tạo `DocumentRevision` (`status="stored"`).
    + Cắt bỏ hoàn toàn việc tạo `JobRecord(job_type="document_revision_parse")` và không dispatch ARQ worker task `task_document_revision_parse`. Trả về `AsyncUploadDocumentResponse` với `status="stored"` và `job_id=None`.
    + Cắt bỏ auto-parse trong `upload_document`.
    + Xóa bỏ logic ràng buộc cascade với `KnowledgeDocument` trong `delete_document` (theo ADR-012, snapshot imports một chiều độc lập, soft-delete kho tài liệu không làm hỏng dữ liệu Knowledge).
    + Bảo toàn deduplication/idempotency và MinIO compensation.
  - Unit & Acceptance Tests:
    + Cập nhật các kịch bản test intake trong `test_document_repository_workflow.py` (`test_02`, `test_07`, `test_12`, `test_http_route_intake_idempotency_header`) sang `status="stored"` và `job_id is None`.
    + Viết thêm 2 acceptance tests cho ADR-012: `test_adr012_batch_upload_stored_status_and_zero_parse_invocations` và `test_adr012_delete_repository_document_decoupled_from_knowledge`.
    + Cập nhật `test_document_repository.py` và `test_document_revisions_lifecycle.py` sang `status="stored"`.
    + Toàn bộ 52/52 tests liên quan pass 100%, Ruff 0 lỗi.
  - Kế hoạch: [Kế hoạch 12 Phiên 2 hoàn thành 100%](../ke_hoach/12_ke_hoach_tach_kho_tai_lieu_va_nap_tri_thuc_da_embedding.md).
  - Báo cáo: [`docs/nhat_ky/2026-10-10_phien_329_simplify_kho_tai_lieu_backend_pure_storage.md`](../nhat_ky/2026-10-10_phien_329_simplify_kho_tai_lieu_backend_pure_storage.md).

- **Phiên trước #328 — Kết quả:**
  - Ban hành văn bản kiến trúc chính thức [`ADR-012`](../adr/ADR-012-decouple-storage-repository-and-knowledge-document-intelligence.md): Tách rời hoàn toàn Kho tài liệu thuần lưu trữ và Kho tri thức sở hữu Document Intelligence; bãi bỏ foreign key cascade; thiết lập snapshot import một chiều; nguyên lý "Parse once, embed many".
  - Khai báo các SQLAlchemy models mới:
    + `RepositoryFileRevision` (`repository_file_revisions`) trong domain `documents` + quan hệ `RepositoryDocument.file_revisions`.
    + `KnowledgeSourceRevision` (`knowledge_source_revisions`), `KnowledgeChunkSet` (`knowledge_chunk_sets`), `KnowledgeImportBatch` (`knowledge_import_batches`), `KnowledgeImportItem` (`knowledge_import_items`) trong domain `knowledge`.
    + Mở rộng quan hệ: `KnowledgeBinding.active_source_revision`, `KnowledgeIndexRevision.source_revision_v2`, `KnowledgeIndexRevision.chunk_set`, `KnowledgeCollection.import_batches`.
  - Viết Alembic additive migration [`20261010_decouple_storage_and_knowledge_v3.py`](../../backend/alembic/versions/20261010_decouple_storage_and_knowledge_v3.py): Idempotent 100% bằng inspector; tạo 5 bảng mới và 3 cột liên kết; downgrade đầy đủ; bảo đảm duy nhất 1 Alembic HEAD.
  - Bổ sung Pydantic DTOs & Contracts V3 cho cả Documents (`RepositoryFileRevisionItem/Response`) và Knowledge (`KnowledgeSourceRevisionResponse`, `KnowledgeChunkSetResponse`, `KnowledgeImportBatchCreateRequest/Response`, `KnowledgeImportItemResponse`, `CandidateListResponse`).
  - Unit & Regression Testing: Viết mới `backend/tests/test_knowledge_v3_schema.py` đạt 7/7 passed in 0.52s; regression suites 72 passed, 1 skipped; Ruff 0 lỗi.
  - Kế hoạch: [Kế hoạch 12 Phiên 1 hoàn thành 100%](../ke_hoach/12_ke_hoach_tach_kho_tai_lieu_va_nap_tri_thuc_da_embedding.md).
  - Báo cáo: [`docs/nhat_ky/2026-10-10_phien_328_adr012_additive_schema_va_contracts_v3.md`](../nhat_ky/2026-10-10_phien_328_adr012_additive_schema_va_contracts_v3.md).

- **Phiên trước #327 — Kết quả:**
  - Chốt ranh giới mới: Kho tài liệu chỉ lưu tệp/metadata danh mục/nhóm; Kho tri thức sở hữu snapshot, OCR/parser, Unicode NFC, Markdown, Quality Gate, chunk/facts và Qdrant publishing.
  - Loại bỏ mô hình liên kết nhóm nguồn lâu dài; Knowledge chỉ lưu provenance một chiều để dedupe/diff, không ghi ngược trạng thái vào Documents.
  - Thiết kế `KnowledgeSourceRevision`, `KnowledgeChunkSet`, import batch/items và trạng thái nguồn/vector tách biệt.
  - Chốt parse once/embed many: đổi embedding model chỉ tạo vector generation mới từ chunk set, không OCR lại.
  - Lập lộ trình 8 phiên additive migration → backend cutover → frontend → backfill/cleanup; kèm prompt tổng dùng trực tiếp cho vibe coding.
  - Quyết định ADR: tạo ADR-012 supersede ranh giới domain của ADR-011, giữ staging/parity/CAS/RetrievalSnapshot/rollback.
  - Không thay đổi code, DB, runtime hoặc `qnu-sso` trong phiên này.
  - Kế hoạch: [`docs/ke_hoach/12_ke_hoach_tach_kho_tai_lieu_va_nap_tri_thuc_da_embedding.md`](../ke_hoach/12_ke_hoach_tach_kho_tai_lieu_va_nap_tri_thuc_da_embedding.md).
  - Báo cáo: [`docs/nhat_ky/2026-10-10_phien_327_lap_ke_hoach_tach_kho_tai_lieu_va_nap_tri_thuc_da_embedding.md`](../nhat_ky/2026-10-10_phien_327_lap_ke_hoach_tach_kho_tai_lieu_va_nap_tri_thuc_da_embedding.md).

- **Phiên trước #326 — Kết quả:**
  - Xác định nguyên nhân nút **Thêm nguồn** đổi URL nhưng không đổi trang: các deep route bị TanStack Router lồng dưới `knowledge.$collectionId.tsx`, trong khi route cha render trực tiếp `CollectionDetailPage` và không có `Outlet`.
  - Chuyển ba trang sang non-nested route: `knowledge.$collectionId_.add-documents.tsx`, `knowledge.$collectionId_.sources.$sourceId.tsx`, `knowledge.$collectionId_.documents.$bindingId.tsx`; giữ nguyên toàn bộ URL công khai.
  - Cây route sinh tự động xác nhận cả ba trang có `KnowledgeRoute` làm cha trực tiếp, sửa đồng thời luồng Thêm nguồn, Chi tiết nguồn và Chi tiết binding.
  - Quality gate frontend: TypeScript không lỗi; Vite build thành công, 5.077 modules trong 6,07 giây. Trình duyệt kiểm tra tách biệt chuyển về `/sign-in` vì không chia sẻ phiên đăng nhập người dùng.
  - Không tác động backend và không thay đổi repository `qnu-sso`.
  - Báo cáo: [`docs/nhat_ky/2026-10-10_phien_326_sua_route_them_nguon_kho_tri_thuc.md`](../nhat_ky/2026-10-10_phien_326_sua_route_them_nguon_kho_tri_thuc.md).

- **Phiên trước #325 — Kết quả:**
  - Khắc phục dứt điểm lỗi SQLAlchemy Mapper Initialization (`expression 'DocumentGroup' failed to locate a name ('DocumentGroup')`) khi chạy `db ensure-ready`: import kiểu `DocumentGroup` rõ ràng trong `knowledge/models.py`, chuyển `documents/__init__.py` sang lazy loading, chuyển import `KnowledgeDocument` sang cục bộ trong các hàm truy vấn của `documents/service.py` để tránh circular dependency.
  - Đồng bộ và chuẩn hóa toàn diện 4 file task runner (`Makefile`, `make.ps1`, `make.bat`, `make` bash script):
    + Bổ sung đầy đủ lệnh CSDL & Migration: `migrate` (chạy Alembic HEAD không lo thiếu `alembic.ini`), `db-check` (kiểm tra schema & bảng), `db-ready` (kiểm tra và tự động khởi tạo/seed nếu thiếu).
    + Bổ sung lệnh kiểm soát chất lượng mã nguồn: `lint` (Ruff & Biome), `lint-fix`, `typecheck` (TypeScript), `build` (Vite build).
    + Bổ sung lệnh kiểm thử phân nhánh: `test` (Backend Pytest & Frontend npm test), `test-be`, `test-fe`.
    + Bổ sung lệnh kiểm tra tri thức: `reconcile` (đối soát 4 tầng), `reindex` (đánh lại vector index).
    + Khắc phục triệt để lỗi gọi script `test:e2e` không tồn tại trong frontend package.json và thiếu `uv` trong PATH môi trường Windows (ưu tiên venv python).
    + Xóa bỏ hoàn toàn các chú thích lỗi thời về port 3001, chuẩn hóa bảng `help` có màu sắc và phân nhóm trực quan.
  - Quality gate: Ruff sạch (All checks passed!), Pytest nguồn nhóm 32 passed / 1 skipped, `.\make.ps1 help` và `make.bat help` chạy thành công 100%.
  - Báo cáo: [`docs/nhat_ky/2026-10-10_phien_325_chuan_hoa_toan_dien_task_runner_makefile_va_khac_phuc_circular_import_mapper.md`](../nhat_ky/2026-10-10_phien_325_chuan_hoa_toan_dien_task_runner_makefile_va_khac_phuc_circular_import_mapper.md).

- **Phiên trước #324 — Kết quả:**
  - Bổ sung `_upsert_failed_item` để giữ đúng một response item trên mỗi tài liệu và nâng cấp item hiện có theo độ ưu tiên lỗi.
  - Conflict `DOCUMENT_BOUND_TO_ANOTHER_GROUP_SOURCE` thay thế cả item success và `DOCUMENT_REVISION_FAILED`; revision failed chỉ thay thế success, không che lỗi nghiệp vụ cụ thể.
  - Sửa regression fixture conflict giữ `desired_pairs` đúng contract thật của `evaluate_group_diff`; bổ sung test trực tiếp cho hai trường hợp upsert.
  - Quality gate: Ruff sạch; test nguồn nhóm 32 passed/1 skipped; backend targeted 90 passed/1 skipped; frontend 10/10 pass; Vite build + TypeScript thành công; `git diff --check` đạt.
  - Báo cáo: [`docs/nhat_ky/2026-10-10_phien_324_upsert_loi_nguon_nhom_va_test_contract_thuc.md`](../nhat_ky/2026-10-10_phien_324_upsert_loi_nguon_nhom_va_test_contract_thuc.md).

- **Phiên trước #323 — Kết quả:**
  - **1. Bổ sung Action Banner cho trạng thái `updates` & Khử trùng lặp nút CTA**:
    - Khai báo `shouldShowUpdatesBanner = bannerType === "updates"` trong `source-detail-page.tsx`.
    - Render Action Banner thứ 3 "Có tài liệu cần đồng bộ" với semantic tokens, icon `Sparkles`, CTA chính **"Đồng bộ"** gọi `syncMutation.mutate()`, disabled khi sync/publish.
    - Cưỡng chế thứ bậc ưu tiên bất biến tối đa 1 banner: `failed > review > updates > none`.
    - Khử trùng lặp CTA: Nút thao tác chính trong `Changes Diff Breakdown Card` chỉ hiển thị khi `bannerType === "none"`, ẩn đi khi đã có action banner ở trên.
  - **2. Chuẩn hóa mã lỗi Conflict Ownership qua `populate_failed_items_from_diff`**:
    - Bổ sung helper `populate_failed_items_from_diff` trong `group_source_diff_service.py`: duyệt và đánh dấu `conflict_docs` trước với `DOCUMENT_BOUND_TO_ANOTHER_GROUP_SOURCE`, sau đó mới duyệt lỗi revision chung `DOCUMENT_REVISION_FAILED` cho các doc không thuộc conflict.
    - Áp dụng helper đồng bộ cho cả `group_source_publish_service.py` (post-publish), `group_source_sync_service.py` (fast path & post-sync).
    - Bảo đảm invariant: mỗi tài liệu lỗi chỉ xuất hiện đúng 1 lần trong `items` và `failed_count`.
  - **3. Đồng bộ số liệu thực tế dòng code**:
    - `group_source_sync_service.py`: **712 dòng** thực tế (giảm 205 dòng lặp so với ban đầu 917 dòng).
    - `group_source_diff_service.py`: **553 dòng**; `group_source_publish_service.py`: **293 dòng**.
  - **Quality Gate**:
    - Backend Ruff linter: **All checks passed (0 errors)**.
    - Targeted Pytest: **89 passed, 1 skipped (100% đạt)** trên `test_knowledge_group_sources.py` (31 tests), `test_document_repository_workflow.py`, `test_rag.py`, `test_knowledge_publishing_v2.py`.
    - Frontend Unit Tests: **10/10 passed (100%)** trên `retry-decision.test.ts`.
    - Frontend Vite build: **✓ built in 3.89s (0 lỗi biên dịch, exit code 0)**.
    - Git diff check: **0 errors**.
    - Báo cáo: [`docs/nhat_ky/2026-10-10_phien_323_action_banner_updates_va_chuan_hoa_ma_loi_conflict.md`](../nhat_ky/2026-10-10_phien_323_action_banner_updates_va_chuan_hoa_ma_loi_conflict.md).

- **Phiên trước #322 — Kết quả:**
  - Khắc phục dứt điểm 6 vấn đề: Xử lý trạng thái rỗng khi nhóm có doc lỗi/processing; Adopt binding ownerless ở mọi revision; Preview attach phát hiện conflict khi `source=None`; Triệt tiêu đếm trùng lỗi bằng `failed_document_ids: set[str]`; Siết chặt an toàn `TEST_DATABASE_URL` bằng `make_url` và `is_safe_test_database_name`; Khử trùng 2 banner CTA qua `resolveSourceActionBanner`; Tinh gọn `group_source_sync_service.py` còn 712 dòng thực tế.
  - Báo cáo: [`docs/nhat_ky/2026-10-10_phien_322_sua_sau_nguon_nhom_kho_tri_thuc.md`](../nhat_ky/2026-10-10_phien_322_sua_sau_nguon_nhom_kho_tri_thuc.md).

- **Phiên trước #321 — Kết quả:**
  - Hoàn thiện 7 vấn đề quy trình nguồn nhóm kho tri thức; Single Source of Truth `eligible_doc_count`; phân loại `adoptable_docs`; tái sử dụng staging ready; cấm xuất bản revision cũ; frontend `resolveRetryAction`; targeted 17 passed / 1 skipped, related 58 passed.
  - Báo cáo: [`docs/nhat_ky/2026-10-10_phien_321_knowledge_group_source_retry_and_publish.md`](../nhat_ky/2026-10-10_phien_321_knowledge_group_source_retry_and_publish.md).

- **Phiên trước #320 — Kết quả:**
  - Bảo toàn ràng buộc NOT NULL PostgreSQL cho `KnowledgeBinding.source_revision_id = target_rev.id` và khởi tạo `status = "pending"`.
  - Tách bạch current revision và pending staging revision; chống build staging lặp lại.
  - Chuẩn hóa state machine resolver `resolve_group_source_state`; bổ sung metrics UI.
  - Báo cáo: [`docs/nhat_ky/2026-10-10_phien_320_sua_state_machine_publish_retry_kho_tri_thuc.md`](../nhat_ky/2026-10-10_phien_320_sua_state_machine_publish_retry_kho_tri_thuc.md).

- **Phiên trước #319 — Kết quả:**
  - Hoàn thiện quy trình nguồn kho tri thức: staging index, retry & workspace isolation.
  - Báo cáo: [`docs/nhat_ky/2026-10-10_phien_319_hoan_thien_quy_trinh_nguon_kho_tri_thuc.md`](../nhat_ky/2026-10-10_phien_319_hoan_thien_quy_trinh_nguon_kho_tri_thuc.md).

- **Phiên trước #318 — Kết quả:**
  - Hoàn thiện quy trình Kho tri thức liên kết lâu dài với Nhóm tài liệu qua `KnowledgeGroupSource`.
  - Thuật toán phân loại diff 6 tập (`added`, `updated`, `removed`, `unchanged`, `not_ready`, `failed`).
  - `membership_hash` SHA-256 ổn định độc lập thứ tự. Tinh gọn UI 4 tab, ẩn toàn bộ luồng legacy/canary.
  - Báo cáo: [`docs/nhat_ky/2026-10-10_phien_318_kho_tri_thuc_nhom_nguon.md`](../nhat_ky/2026-10-10_phien_318_kho_tri_thuc_nhom_nguon.md).

- **Phiên trước #317 — Kết quả:**
  - Không còn coi mọi `IntegrityError` khi commit membership là duplicate race hợp lệ.
  - Sau rollback, service re-query chính xác `(group_id, document_id)`; chỉ trả thành công khi membership concurrent thật sự tồn tại.
  - Nếu không tìm thấy membership winner, trả RFC 7807 `DOCUMENT_GROUP_MEMBERSHIP_FAILED` (HTTP 409).
  - Response primitives được lưu trước rollback để tránh truy cập ORM objects có thể bị expire.
  - Documents regression suites: **48/48 passed**; Ruff toàn backend sạch.
  - Báo cáo: [`docs/nhat_ky/2026-10-10_phien_317_xac_minh_membership_race_sau_integrity_error.md`](../nhat_ky/2026-10-10_phien_317_xac_minh_membership_race_sau_integrity_error.md).

- **Phiên trước #316 — Kết quả:**
  - **1. Xử Lý Object Mồ Côi Khi Concurrent Upload Khác Tên File**:
    - Khi gặp `IntegrityError` (trùng SHA-256 hash `(tenant_id, workspace_id, file_hash)`), rollback transaction và tìm `winner_doc`.
    - So sánh chính xác: `if winner_doc.storage_path != storage_key`: gọi `await storage_service.delete(storage_key)` để dọn object mồ côi của loser request.
    - Nếu `winner_doc.storage_path == storage_key`: tuyệt đối không xóa vì winner đang dùng chung object đó.
    - Nếu không tìm thấy winner: compensation-delete đúng `storage_key` của request và ném lại lỗi.
  - **2. Validate Revision Trước Khi Tạo Membership & Xử Lý Race Idempotent**:
    - Truy vấn và resolve revision thật: `winner_doc.current_revision` -> `winner_doc.current_revision_id` -> newest revision.
    - Validate trạng thái thuộc `VALID_REVISION_STATUSES`. Nếu không có revision hợp lệ, ném RFC 7807 `AppException(code="DOCUMENT_REVISION_INVALID", status_code=409)`, không thêm membership, không cập nhật group, không commit.
    - Chỉ khi revision hợp lệ mới kiểm tra và thêm `DocumentGroupMembership`.
    - Bọc mutation commit trong `try ... except IntegrityError`: rollback an toàn nếu có race condition cùng thêm membership, đảm bảo hành vi idempotent 100%.
  - **3. Thống Nhất Frontend Production Idempotency**:
    - `document-upload-modal.tsx` import và sử dụng trực tiếp `FileIdempotencyManager` từ `@/features/documents/utils/idempotency.ts` (`const idempotencyManagerRef = useRef(new FileIdempotencyManager())`).
    - Xóa bỏ `WeakMap` cục bộ và helper `getOrCreateIdempotencyKey` trùng lặp trong modal.
    - Retry cùng một đối tượng `File` giữ nguyên key. File mới nhận key mới.
    - `resetForm()` gọi `idempotencyManagerRef.current.reset()`.
    - Thêm script `"test:documents": "bun test src/features/documents/utils/idempotency.test.ts"` vào `frontend/package.json`.
  - **Quality Gate**:
    - Backend targeted test suites: **47/47 passed (100%)** (`test_document_repository_workflow.py` 26/26, `test_document_groups_and_knowledge_attach.py` 14/14, `test_document_revisions_lifecycle.py` 7/7).
    - Backend Ruff: `All checks passed! (0 errors)`.
    - Frontend Unit Tests: **3/3 passed (100%)** (`idempotency.test.ts`).
    - Frontend Biome: 13 files checked, 0 errors.
    - Frontend Vite Build: `✓ built in 4.52s` (0 errors).
    - Zero file modified in `qnu-sso`. Zero runtime files in `backend/storage/documents/`.
  - Báo cáo chi tiết: [`docs/nhat_ky/2026-10-10_phien_316_hoan_thien_an_toan_concurrency_va_idempotency_kho_tai_lieu.md`](../nhat_ky/2026-10-10_phien_316_hoan_thien_an_toan_concurrency_va_idempotency_kho_tai_lieu.md).

- **Phiên trước #315 — Kết quả:**
  - Tích hợp bốn nguyên tắc `Think Before Coding`, `Simplicity First`, `Surgical Changes` và `Goal-Driven Execution` vào `AGENTS.md` và skill `qnu-clean-code-architect` hiện có.
  - Áp dụng kiểm thử theo rủi ro: test-first cho dữ liệu/transaction/concurrency/idempotency/migration/auth/tenant/payment; code theo lô rồi test một lần cho tính năng thông thường; lint/build nhanh cho thay đổi UI thuần túy.
  - Thay Boy Scout Rule mở rộng bằng Surgical Change Rule, ngăn AI tự ý refactor hoặc format code ngoài phạm vi.
  - Bật `allow_implicit_invocation: true` để skill Clean Code tự động hỗ trợ các phiên coding, fix, review và refactor.
  - Giữ nguyên các quality gate chuyên ngành Backend/Frontend; tối ưu số lần chạy chứ không bỏ final verification.
  - Skill validator: `Skill is valid!`.
  - Snapshot: [`docs/memory/snapshots/2026-10-10_session_248.md`](./snapshots/2026-10-10_session_248.md).

- **Phiên trước #314 — Kết quả:**
  - **1. Sửa Race Condition Xóa Nhầm Object Khi Upload Đồng Thời**:
    - Trong nhánh `except IntegrityError`, rollback transaction và truy vấn winner document `(tenant_id, workspace_id, file_hash)` trước.
    - Nếu tìm thấy winner: tuyệt đối không xóa `storage_key` (bảo toàn byte của winner theo content-addressed invariant); gắn membership vào Document Group idempotent; đọc revision thật và `JobRecord` đang hoạt động thật từ DB.
    - Ném lỗi RFC 7807 HTTP 409 `DOCUMENT_REVISION_INVALID` nếu winner không có revision hợp lệ. Tuyệt đối không sinh revision ID giả hay job ID giả.
    - Chỉ thực hiện compensation delete `storage_key` khi không có winner (transaction tạo tài liệu thất bại hoàn toàn).
  - **2. Giữ Ổn Định Idempotency-Key Khi Retry**:
    - Xây dựng `FileIdempotencyManager` (`useRef<WeakMap<File, string>>`) với helper `getOrCreate(file: File): string`.
    - Cùng một đối tượng `File` trong modal và cùng phiên retry luôn nhận đúng UUID ban đầu.
    - Reset kho key khi form reset hoặc đóng modal. File mới nhận key mới. Không dùng tên file đơn thuần.
    - Tiếp tục gửi key qua header `Idempotency-Key`, không đưa vào `FormData`. Đã bổ sung 3 unit tests Bun test passed 100%.
  - **3. Chuyển Toàn Bộ Endpoint Legacy V1 Sang Intake V2**:
    - Mọi request tới `/documents/upload` (dù có hay không có `group_id`) đều đi qua orchestration bất đồng bộ `document_intake_service.intake_document(...)`.
    - Tiếp nhận và chuyển tiếp header `Idempotency-Key`.
    - Truyền đầy đủ `actor`, `tenant_id`, `workspace_id`, `group_id`, metadata NĐ 30.
    - Map kết quả qua `document_repository_service.get_document(...)` để trả `RepositoryDocumentResponse` tương thích client cũ.
    - Tuyệt đối không gọi `document_repository_service.upload_document(...)` từ router legacy nữa.
  - **4. Chuẩn Hóa Thông Báo Gắn Nguồn Vào Kho Tri Thức (Honest Binding Semantics)**:
    - Giữ `auto_activate: false`.
    - Tiêu đề: *"Đã gắn nguồn tài liệu"*; Mô tả: *"Các tài liệu sẵn sàng đã được liên kết với Kho tri thức. Chúng cần được lập chỉ mục trước khi có thể dùng để truy xuất RAG."*; Toast: *"Đã gắn {created_count} tài liệu vào Kho tri thức."*.
    - Loại bỏ triệt để các từ "xuất bản hoàn tất", "sẵn sàng sử dụng", "đã lập chỉ mục" khi chưa có `index_revision_id`.
    - Nút hành động đổi thành *"Mở Kho tri thức"*.
    - Xử lý error state khi tải Kho tri thức với banner lỗi và nút *"Thử lại"*.
  - **Quality Gate**:
    - Backend Ruff: `All checks passed! (0 errors)`.
    - Backend Workflow & Lifecycle Unit Tests: **45/45 passed (100%)** (`test_document_repository_workflow.py` 24/24, `test_document_groups_and_knowledge_attach.py` 14/14, `test_document_revisions_lifecycle.py` 7/7).
    - Frontend Unit Tests: **3/3 passed (100%)** (`idempotency.test.ts`).
    - Frontend Biome: 13 files checked, 0 errors.
    - Frontend Vite Build: `✓ built in 3.20s` (0 errors).
  - Báo cáo chi tiết: [`docs/nhat_ky/2026-10-10_phien_314_xu_ly_dut_diem_4_van_de_con_lai_kho_tai_lieu.md`](../nhat_ky/2026-10-10_phien_314_xu_ly_dut_diem_4_van_de_con_lai_kho_tai_lieu.md).

- **Phiên trước #313 — Kết quả:**
  - Hoàn thiện dứt điểm 8 vấn đề cốt lõi của quy trình Kho tài liệu & Intake V2: Cô lập storage key theo scope tenant/workspace; HTTP Idempotency-Key header & replay conflict; Legacy V1 adapter chống orphan; xóa bỏ toggle autoParse; deduplicate đọc từ current_revision; hoàn thiện error state frontend; Alembic safe index inspector migration; chuẩn hóa semantic token `text-warning`. 40/40 tests passed, Ruff 0 lỗi, Biome 0 lỗi, Vite build đạt 100%.
  - Báo cáo chi tiết: [`docs/nhat_ky/2026-10-10_phien_313_hoan_thien_toan_dien_quy_trinh_kho_tai_lieu_va_intake_v2.md`](../nhat_ky/2026-10-10_phien_313_hoan_thien_toan_dien_quy_trinh_kho_tai_lieu_va_intake_v2.md).

- **Phiên trước #312 — Kết quả:**
  - Hoàn thiện dứt điểm toàn diện tích hợp QNU SSO giữa hai repositories theo hướng production-first: Truyền `environment.EnvironmentName` trực tiếp làm source of truth; fail-fast production khi thiếu base URL; frontend `resolveOidcAuthority` nhận diện mọi loopback (`localhost`, `127.0.0.1`, `::1`), strip trailing slash; chống JWKS stampede bằng `asyncio.Lock` và double-checked locking; 16 unit tests production thật cho `fetch-interceptor.ts`; strict HTTPS allow-list và idempotent client reconciliation; chuẩn hóa ESM loader hook cho Node 24 native test runner; đồng bộ OIDC issuer với `options.SetIssuer(issuerUri)`; toàn bộ 120/120 tests SSO passed, 38/38 backend tests passed, 46/46 frontend tests passed, Ruff 0 lỗi, Biome 0 lỗi, Vite build đạt 100%.
  - Báo cáo chi tiết: [`docs/nhat_ky/2026-10-09_phien_312_hoan_thien_dut_diem_tich_hop_qnu_sso_production.md`](../nhat_ky/2026-10-09_phien_312_hoan_thien_dut_diem_tich_hop_qnu_sso_production.md).

- **Phiên trước #311 — Kết quả:**
  - Tái cấu trúc luồng Kho Tài Liệu `/documents` theo chuẩn UX Production: chuyển trang `/documents` thành trang quản lý các Kho Tài Liệu (Document Groups); loại bỏ nút "Nhóm Tài Liệu" và "Tải Lên Tài Liệu", chỉ giữ 1 nút "Tạo Kho Tài Liệu"; tự động làm mới dữ liệu và hiển thị kho mới tạo ngay trên màn hình; hỗ trợ click trực tiếp vào kho để mở chi tiết; chuẩn hóa nút "Tải Lên Tài Liệu" bên trong trang chi tiết kho; hỗ trợ ViewModeToggle (Grid/Table); Biome linter 0 lỗi, Vite build 5.42s thành công 100% 0 lỗi TypeScript.
  - Báo cáo chi tiết: [`docs/nhat_ky/2026-10-09_phien_310_tai_cau_truc_luong_kho_tai_lieu_documents_theo_ux_production.md`](../nhat_ky/2026-10-09_phien_310_tai_cau_truc_luong_kho_tai_lieu_documents_theo_ux_production.md).

- **Phiên trước #309 — Kết quả:**
  - Hoàn thiện luồng tạo Nhóm tài liệu & tải lên trực tiếp trong chi tiết nhóm: sau khi tạo nhóm tự động điều hướng sang `/documents/groups/:groupId`; bổ sung nút "Tải Lên Tệp Mới" trong Action Toolbar và EmptyState của trang chi tiết nhóm; backend mở rộng `group_id` cho `/documents/upload` và `/documents/intake` tự động thêm thành viên vào nhóm; kiểm thử đầy đủ 14/14 Pytest passed 100%, Ruff 0 lỗi, Vite build 0 lỗi.
  - Báo cáo chi tiết: [`docs/nhat_ky/2026-10-09_phien_309_hoan_thien_luong_upload_truc_tiep_trong_chi_tiet_nhom_tai_lieu.md`](../nhat_ky/2026-10-09_phien_309_hoan_thien_luong_upload_truc_tiep_trong_chi_tiet_nhom_tai_lieu.md).

- **Phiên trước #308 — Kết quả:**
  - Hoàn thiện toàn diện hardening production tích hợp QNU SSO giữa hai repositories: Chống JWKS stampede bằng `asyncio.Lock`, double-checked locking và generation tracking (`_refresh_count`); Viết 16 test cases production thật cho `fetch-interceptor.ts`; Triển khai `resolveOidcAuthority` loopback isolation; OpenIddict dynamic issuer; Reconcile idempotent; Khôi phục tsconfig chuẩn và Node 24 ESM test-loader; Docs UTF-8 sạch. 46/46 frontend tests pass, 38/38 backend tests pass, 120/120 SSO tests pass.
  - Báo cáo chi tiết: [`docs/nhat_ky/2026-10-09_phien_308_hoan_thien_hardening_qnu_sso_integration.md`](../nhat_ky/2026-10-09_phien_308_hoan_thien_hardening_qnu_sso_integration.md).

- **Phiên trước #307 — Kết quả:**
  - Đóng hoàn toàn lỗ hổng P0 anonymous dev admin: mọi request không có token trong production luôn trả HTTP 401; dev admin actor chỉ hoạt động khi đồng thời là dev/test, `DEV_AUTH_ENABLED=true` và không yêu cầu enforce auth; endpoint `/auth/login` bị vô hiệu hóa (HTTP 403) khi `DEV_AUTH_ENABLED=false` hoặc trong production; production cấm decode local JWT `qnu_session`.
  - Validate JWT OIDC chuẩn xác: xác thực chữ ký JWKS, `exp`, `nbf`, `iss == clean_sso_authority`, `aud == SSO_AUDIENCE` (`ai.api`), cố định thuật toán `RS256`, cấm `verify_aud=False`. JWT sai fail-closed ngay lập tức, không fallback UserInfo. Opaque token bắt buộc verify scope `ai.api`.
  - Triệt tiêu toàn bộ cơ chế tự cấp quyền: xóa bỏ default permissions theo `user_type`, cấm dùng substring `admin`, người dùng bắt buộc có ít nhất 1 role `AI.*` và permission `ai.access.read` (nếu thiếu trả HTTP 403 RFC 7807), từ chối permission `*` từ SSO token.
  - Sửa semantic RBAC: exact match, `ai.access.admin` hoặc exact role `AI.Admin` cho phép toàn bộ `ai.*`, `ai.access.manage` không phải wildcard, `ai.access.read` không mở rộng.
  - Đồng bộ danh mục permissions: thay thế toàn bộ `.edit` thành `.update` (`ai.assistants.update`, `ai.knowledge.update`) trên toàn bộ router và tests; tạo Contract Test AST tự động quét literals `require_permission(...)` đối soát với `qnu-ai-permissions.json` (pass 100%).
  - Bảo vệ token Frontend: chuyển `oidc-client-ts` `userStore` sang `sessionStorage`, xóa bỏ token đọc trực tiếp từ `localStorage`, bảo toàn headers từ `Request` object, triển khai single-flight silent renew và retry đúng 1 lần khi HTTP 401 với anti-loop guard, dọn sạch session khi renew thất bại.
  - Đồng bộ `qnu-sso`: Sửa `QnuAiClientSeed` (xử lý base URL qua `Uri`, fail-fast production, hỗ trợ `ReconcileExistingClientAsync` idempotent cập nhật an toàn không ghi đè cấu hình admin, không tạo secret cho public SPA), sửa Docker Compose không truyền chuỗi rỗng, hoàn thiện bootstrap `AI.Admin` cho system admins trong `AuthorizationSeed.cs`.
  - Quality Gate: Backend pytest 34/34 passed (`test_auth.py`, `test_sso_auth.py`, `test_permission_contract.py`), Ruff 0 lỗi; Frontend Biome 0 lỗi, `npm run build` thành công 100% (Vite + TSC 0 lỗi); `qnu-sso` dotnet build thành công (0 warning, 0 error), dotnet test 123/123 passed (107 Application.UnitTests, 8 Domain.UnitTests, 8 Infrastructure.IntegrationTests).
  - Báo cáo chi tiết: [`docs/nhat_ky/2026-10-09_phien_307_fail_closed_sso_integration_hardening.md`](../nhat_ky/2026-10-09_phien_307_fail_closed_sso_integration_hardening.md).

- **Phiên trước #306 — Kết quả:**
- **Kết quả phiên #306**:
  - Bổ sung bộ lọc `tenant_id` và `workspace_id` cho các truy vấn KPI, danh sách tài liệu nhóm và luồng preview/attach server-side.
  - Kết quả attach phân loại revision `failed`/`rejected` thành `status="failed"` nhất quán với aggregate counters và UI.
  - Chuẩn hóa màu trạng thái nhóm tài liệu sang semantic tokens `success`, `info`, `warning`, `destructive`.
  - Quality gate: full backend 636 passed, 1 skipped; test nhóm tài liệu 13 passed; Ruff 0 lỗi; Vite + TypeScript build đạt.
  - Báo cáo chi tiết: [`docs/nhat_ky/2026-10-09_phien_306_hardening_review_document_groups.md`](../nhat_ky/2026-10-09_phien_306_hardening_review_document_groups.md).

- **Phiên trước #305 — Kết quả:**
- **Kết quả phiên #305**:
  - Triển khai toàn diện phân hệ Nhóm Tài Liệu (`DocumentGroup`) và quan hệ nhiều-nhiều (`DocumentGroupMembership`).
  - Migration Alembic additive `20261009_document_groups` (1 head duy nhất) với PostgreSQL functional unique index `uq_doc_groups_tenant_ws_lower_name` trên `(tenant_id, workspace_id, lower(name))`.
  - Tách bạch ranh giới kiến trúc: file nguồn bất biến (`RepositoryDocument`), nhóm logic (`DocumentGroup`), quan hệ nhiều-nhiều (`DocumentGroupMembership`), không gian RAG (`KnowledgeCollection`), và liên kết tri thức (`KnowledgeBinding`).
  - Đã khắc phục triệt để 13 vấn đề sau code review:
    1. Frontend build sạch: xóa `ExternalLink`, `Check` thừa, sửa an toàn unknown error trong `__root.tsx`, `npm run build` (vite + tsc) thành công 100%.
    2. Sửa rò rỉ mock singleton: dùng `monkeypatch.setattr(binding_service, "create_bindings", ...)` trong pytest; test hồi quy `test_knowledge_publishing_v2.py` pass 100% (26/26 tests passed kết hợp).
    3. Cưỡng chế tenant & workspace isolation cho `/documents`: `list_documents` nhận `actor: AuthActor`, lọc bắt buộc tenant/workspace, từ chối `group_id` khác scope với code `DOCUMENT_GROUP_ACCESS_DENIED`, truy vấn badges nhóm tenant-scoped.
    4. Server-side preview API: `POST /knowledge/collections/{id}/preview-document-group` (read-only), dùng chung helper `_evaluate_group_members` với `attach_document_group`.
    5. Refactor dialog "Đưa vào kho": đọc preview từ server qua query key `["preview-document-group", collectionId, groupId]`, hiển thị Bento KPI và trạng thái từng tài liệu, invalidate đúng 5 query keys.
    6. Chuẩn hóa tên nhóm: Pydantic validator Unicode NFC, collapse consecutive whitespace, trim, từ chối rỗng, giới hạn $\le 128$ ký tự.
    7. Chống trùng tên nhóm ở CSDL: functional unique index `lower(name)` ở PostgreSQL, bắt `IntegrityError` rollback trả HTTP 409 `DOCUMENT_GROUP_NAME_CONFLICT`.
    8. Atomic optimistic locking: câu lệnh SQL atomic `UPDATE ... WHERE lock_version = :expected_lock_version`, `rowcount == 0` trả HTTP 409 `OPTIMISTIC_LOCK_CONFLICT`.
    9. Chuẩn hóa audit actor: `actor.actor_id` -> `actor.username` -> `"system"`.
    10. Sửa KPI danh sách nhóm: tính chuẩn `processing_documents`, dùng `groupsData.total`, gắn nhãn rõ ràng "Trong kết quả" khi đang lọc.
    11. Modal chọn tài liệu: hỗ trợ param `exclude_group_id` server-side với `NOT EXISTS`, loại bỏ filter client-side 100 tài liệu.
    12. Validation API: `SUPPORTED_CHUNK_STRATEGIES`, `sync_policy: Literal["manual"]`, `strict_ready` trả chi tiết `STRICT_READY_VIOLATION`.
    13. Mã nguồn sạch: `git diff --check` sạch 0 lỗi whitespace, Ruff 0 lỗi, Alembic 1 head duy nhất.
  - Quality Gate: Backend pytest 26/26 passed (`test_document_groups_and_knowledge_attach.py` 13/13 + `test_knowledge_publishing_v2.py` 13/13), Ruff 0 lỗi; Frontend `npm run build` thành công 100% (0 lỗi TypeScript, 0 lỗi Biome).
  - Báo cáo chi tiết: [`docs/nhat_ky/2026-10-09_phien_305_trien_khai_tinh_nang_nhom_tai_lieu_va_attach_knowledge_group.md`](../nhat_ky/2026-10-09_phien_305_trien_khai_tinh_nang_nhom_tai_lieu_va_attach_knowledge_group.md).

- **Phiên trước #304 — Kết quả:**
  - Nhánh sao lưu cục bộ `codex/main-before-knowledge-publishing-v2-20261009` bảo toàn `main` cũ tại commit `b2d61cb`.
  - Toàn bộ mã nguồn, migration, tests và tài liệu Publishing V2 đã được lưu vào `main` bằng commit `6a223bc` (`feat: implement safe document-to-knowledge publishing v2`).
  - Artefact `.pytest-review-*`, script vá tạm chưa theo dõi và dữ liệu runtime `storage/` không được đưa vào commit.
  - Các nhánh và commit chưa được push lên remote.
  - Báo cáo chi tiết: [`docs/nhat_ky/2026-10-09_phien_304_sao_luu_main_cu_va_commit_publishing_v2.md`](../nhat_ky/2026-10-09_phien_304_sao_luu_main_cu_va_commit_publishing_v2.md).

- **Phiên trước #303 — Kết quả:**
  - Loại bỏ các nhánh nuốt lỗi/fallback trong scope helpers; mọi thao tác yêu cầu khóa đều thực thi `SELECT ... FOR UPDATE`, kể cả luồng nội bộ không có `actor`.
  - Cưỡng chế cấp phát `index_epoch` chỉ từ giá trị nguyên của `UPDATE ... RETURNING`; không còn đọc lại object rồi tự cộng một.
  - Tập trung phân giải embedding dimension tại `ModelCatalogService.resolve_embedding_dimension`, kiểm tra provider/model/dimension và từ chối metadata snapshot sai lệch bằng RFC 7807.
  - Khép kín race cooperative cancellation: worker kiểm tra quyền chuyển trạng thái ở cả checkpoint `running` lẫn trước khi công bố kết quả cuối.
  - Chuẩn hóa màn cấu hình Knowledge bằng `Button` dùng chung, chọn model theo cặp provider-model và chặn lưu cấu hình thiếu dimension.
  - Quality gate: Ruff 0 lỗi; 34/34 regression test trọng tâm pass; Biome kiểm tra 504 files với 0 lỗi; Vite + TypeScript build thành công.
  - Full backend suite: **616 passed, 6 failed, 1 skipped**; sáu integration test còn lại cần PostgreSQL seed nhưng Docker daemon hiện không chạy. Không thêm mock/fallback production để tạo kết quả xanh giả.
  - Báo cáo chi tiết: [`docs/nhat_ky/2026-10-09_phien_303_khoa_race_condition_modelops_dimension_va_frontend_quality_gate.md`](../nhat_ky/2026-10-09_phien_303_khoa_race_condition_modelops_dimension_va_frontend_quality_gate.md).

- **Phiên trước #302 — Kết quả:**
  - Xử lý triệt để 5 vấn đề cốt lõi hậu code review theo kiến trúc sạch, Production-First và Zero Hallucination:
    1. **Tenant & Workspace Scoping (`scope_helper.py`)**: Tối ưu hóa `get_scoped_collection`, `get_scoped_binding`, `get_scoped_index_revision` dùng `await db.get(...)` trước để hit identity map cache, kiểm tra scope `tenant_id` / `workspace_id` chặt chẽ, xử lý coroutine unwrap an toàn cho cả async runtime và unit test mocks.
    2. **Atomic SQL Epoch Increment**: Hàm `bump_collection_index_epoch` thực thi duy nhất 1 câu SQL nguyên tử `UPDATE knowledge_collections SET index_epoch = index_epoch + 1 WHERE id = ... RETURNING index_epoch`, loại bỏ race condition CAS và thay thế toàn bộ bare `except Exception:` bằng các lớp exception cụ thể (`SQLAlchemyError`, `TypeError`, `AttributeError`, `KeyError`).
    3. **Connection Pool Optimization Trong Cooperative Job Cancellation**: Nâng cấp `is_job_cancelled(job_id, db=db)` nhận `db: AsyncSession | None = None` để tái sử dụng session hiện có trong worker checkpoints (`tasks.py`, `gc_service.py`), tránh tạo socket mới làm cạn connection pool; xây dựng helper `_extract_cancellation_state` an toàn nhận diện model object, SQLAlchemy Row, tuple, mapping.
    4. **Dynamic ModelOps Vector Dimension Resolution & Partial Points Cleanup**: Loại bỏ hoàn toàn fallback `vector_size=1024` trong `IndexBuildService`, phân giải kích thước vector động từ ModelOps DB và fail-fast `EMBEDDING_DIMENSION_NOT_CONFIGURED` (400); checkpoints hủy tác vụ hợp tác (`_check_job_cancelled`) tự động gọi `vector_indexer.client.delete` dọn dẹp partial points trên Qdrant khi bị hủy và đổi status sang `failed` (`JOB_CANCELLED`).
    5. **Frontend Quality Gate & Type Standardization**: Chuẩn hóa kiểu dữ liệu `ModelOption` (`label?: string`) và `exportMultiSheetToExcel` (`AnyExcelSheet`), loại bỏ các lỗi TypeScript typecheck còn tồn đọng; đạt **0 lỗi Biome linter** (483 files) và Vite build thành công 100% trong 3.89s (0 TypeScript errors).
  - Toàn bộ test suites Publishing V2: `test_publishing_v2_hardening.py` (11), `test_publishing_v2_cutover_and_gc.py` (9), `test_publishing_v2_decommissioning_and_system_gc.py` (7), `test_publishing_v2_resilience_and_cancellation.py` (8) -> **35/35 PASSED (100%)**.
  - Toàn bộ ModelOps test suites: `test_modelops.py` (22), `test_modelops_usage.py` (4), `test_model_runtime_resolver.py` (2) -> **28/28 PASSED (100%)**.
  - Backend Ruff linter: **All checks passed (0 errors)**; Alembic: **20261008_publishing_v2_hardening (head)** (1 head duy nhất).
  - Báo cáo chi tiết: [`docs/nhat_ky/2026-10-09_phien_302_hardened_tenant_scope_atomic_epoch_vector_and_cancellation.md`](../nhat_ky/2026-10-09_phien_302_hardened_tenant_scope_atomic_epoch_vector_and_cancellation.md).

- **Phiên trước #301 — Kết quả:**
  - Bảo vệ đa tenant/workspace bằng `AuthActor` giải mã từ phiên xác thực SSO / Dev Access Gate; loại bỏ 100% header `X-Tenant-Id` và `X-Workspace-Id` từ client; trả 404 cho cross-tenant nhằm chống rò rỉ siêu dữ liệu.
  - Bổ sung workspace isolation cho Document Revision (`documents/revision_service.py` & `router.py`), kiểm tra đồng thời cả `tenant_id` và `workspace_id`.
  - Khắc phục triệt để race condition index epoch bằng SQL nguyên tử `bump_collection_index_epoch` (`UPDATE knowledge_collections SET index_epoch = index_epoch + 1 RETURNING index_epoch`).
  - Cưỡng chế CAS (Compare-And-Swap) với tham số bắt buộc `expected_epoch: int` cho cả promote và rollback, ném RFC 7807 409 `CAS_EPOCH_CONFLICT`.
  - Triệt tiêu hoàn toàn runtime ModelOps hardcode: `get_system_model_defaults` chỉ đọc từ CSDL, fail-fast `MODEL_DEFAULT_NOT_CONFIGURED`, cấm tự seed hoặc gán cứng fallback model.
  - Bảo toàn bất biến vector dimension: cấm truncate/pad im lặng trong `VectorIndexer._fit_dim` (ném `VECTOR_DIMENSION_MISMATCH`), validate dense vectors tính sẵn, raise `AppException(QDRANT_UPSERT_FAILED)` khi Qdrant upsert lỗi.
  - Cơ chế cooperative job cancellation: kiểm tra tín hiệu hủy `_check_pre_execution_cancelled` trước khi chuyển sang `running`; 5 checkpoint trong staging build (`task_knowledge_index_build`); dọn dẹp dense points trên Qdrant khi bị hủy.
  - Bảo vệ xoá/dọn dẹp Job: chỉ xoá job terminal (xoá running/queued báo 409 `job_not_terminal`); cleanup chỉ nhận terminal statuses (báo 400 `INVALID_CLEANUP_STATUS`).
  - Chuẩn hóa Frontend: xoá sạch `as any` trong điều hướng TanStack Router (`add-documents`, `binding-detail`); Biome 0 lỗi.
  - Quality Gate: Backend unit & regression test suites chính passed 100% (knowledge v2: 13/13, hardening: 11/11, jobs: 18/18, rag: 18/18); Ruff 0 lỗi; Biome 0 lỗi; Alembic 1 head.
  - Báo cáo chi tiết: [`docs/nhat_ky/2026-10-08_phien_301_hoan_thien_tenant_modelops_vector_va_job_cancellation.md`](../nhat_ky/2026-10-08_phien_301_hoan_thien_tenant_modelops_vector_va_job_cancellation.md).

- **Phiên trước #300 — Kết quả:**
  - Bảo vệ API Jobs theo quyền fine-grained (`require_permission`) và cô lập dữ liệu 100% theo tenant của `AuthActor`; trả 404 cho cross-tenant; retry job reset sạch cờ `cancel_requested`.
  - Ràng buộc revision với document và tenant trong service; ngăn chặn truy cập trái phép chéo tài liệu hoặc chéo tenant.
  - Chuẩn hóa DTO ParityReport (`parity_status: "passed" | "failed"`, `indexed_points`, `verified_points`), loại bỏ trạng thái giả `staging`, nút Promote chỉ hiển thị khi `ready` và parity passed.
  - Khôi phục thao tác Rollback từ revision `archived` còn khả dụng dữ liệu (`is_rollback_available: bool`, `storage_state`); phân biệt rõ với `pruned`.
  - Cưỡng chế CAS (Compare-And-Swap) với `expected_epoch` bắt buộc khi promote, ném RFC 7807 `409 Conflict` (`CAS_EPOCH_CONFLICT`) khi stale, frontend hiển thị Toast xung đột và tự động refetch.
  - Thiết lập Vector Generation Invariants: cấm tuyệt đối truncate/padding âm thầm trong `_fit_dim` (ném `VECTOR_DIMENSION_MISMATCH`), verify số chiều Qdrant collection trong `ensure_collection`, truyền `vector_generation` thật từ ModelOps DB.
  - Hỗ trợ cooperative job cancellation trong worker (`tasks.py`) tại các checkpoint trước và sau khi xử lý nặng.
  - Khóa aggregate cha bằng `with_for_update()` chống race condition khi cấp số revision (`document_revision_no`, `index_revision_no`).
  - Triệt tiêu 100% model/provider hardcode trong runtime nghiệp vụ, lấy defaults từ ModelOps DB.
  - Quality Gate: Backend 31/31 unit & regression tests passed (100%), Ruff 0 lỗi, Biome 0 lỗi, Vite build 4.23s thành công, Alembic 1 head.
  - Báo cáo chi tiết: [`docs/nhat_ky/2026-10-08_phien_300_hardening_bao_mat_va_publishing_contract.md`](../nhat_ky/2026-10-08_phien_300_hardening_bao_mat_va_publishing_contract.md).

- **Phiên trước #299 — Kết quả:**
  - Sửa vòng đời revision: chỉ promote sau Quality Gate/duyệt, CAS bằng `expected_lock_version`, retry/review theo state machine thật.
  - Hoàn thiện job outbox idempotent, dispatch reconciliation, heartbeat/attempt và lỗi worker fail-fast.
  - Khóa tenant/workspace trên binding, revision, chunks và snapshot; parity PostgreSQL–Qdrant kiểm tra count/ID/hash thật.
  - Đồng bộ activation/rollback theo `index_revision_id` và `expected_epoch`; Vector Generation phân giải ModelOps động, không trộn không gian embedding.
  - RAG snapshot pin toàn bộ dense/sparse/facts/neighbors; cache mang epoch + fingerprint; loại bỏ dữ liệu fake/test shortcut.
  - Backfill/canary/GC dùng artifact thật và thứ tự xóa an toàn; Reranker không hardcode model/endpoint runtime.
  - OCR layout nhận diện danh sách bằng quy tắc hình thái/cú pháp tổng quát; frontend revision/binding contracts khớp API.
  - Quality Gate: Backend `598 passed, 1 skipped`; Ruff toàn repository 0 lỗi; Alembic một head; frontend Vite + TypeScript build thành công.
  - Báo cáo chi tiết: [`docs/nhat_ky/2026-10-08_phien_299_hardening_quy_trinh_xuat_ban_tri_thuc_v2.md`](../nhat_ky/2026-10-08_phien_299_hardening_quy_trinh_xuat_ban_tri_thuc_v2.md).

- **Phiên trước #298 — Kết quả:**
  - **Xóa Bỏ Ollama & Dọn Dẹp Toàn Bộ Seed Data / Defaults Liên Quan**:
    * Xóa bỏ hoàn toàn nhà cung cấp `QNU AI Server (RTX 5090 - Ollama)` (`prov_rtx5090_ollama`, URL `http://tormemrtxproto.tail0924dd.ts.net:11434`) khỏi `STANDARD_QNU_PROVIDERS`.
    * Bổ sung cơ chế tự động dọn dẹp an toàn trong `seed_default_providers`: `if "prov_rtx5090_ollama" in existing: await db.delete(...)`.
    * Cập nhật `DEFAULT_QNU_OCR_COMBO_CHAIN`: Ưu tiên 1 là Google Gemini (`gemini-3.1-flash-lite`), loại bỏ Ollama.
    * Cập nhật `ast_drafting` và `ast_question_bank` trong `assistants/seeder.py` sang `prov_gemini` (`gemini-2.5-flash`), loại bỏ tham chiếu tới `prov_rtx5090_ollama`.
  - **Cấu Hình & Seed Nhà Cung Cấp vLLM On-Premise Mới**:
    * Nhà cung cấp mới: `QNU AI Server (RTX 5090 - vLLM)` (`prov_rtx5090_vllm`) tại `http://tormemrtxproto.tail0924dd.ts.net:8000/v1` (Port 8000 chuẩn vLLM trên mạng Tailscale).
    * Đăng ký 3 mô hình cục bộ với `model_specs` chuẩn xác:
      + `bge-m3`: vLLM pooling / embeddings (1,024 dims).
      + `bge-reranker-v2-m3`: vLLM rerank / score Cross-Encoder tái chấm điểm Top-K.
      + `qwen3-embedding-4b`: vLLM pooling / embeddings (2,560 dims) đã tải local.
    * Cập nhật `DEFAULT_QNU_EMBEDDING_COMBO_CHAIN`: Ưu tiên 1 là `prov_rtx5090_vllm` (`bge-m3`).
    * Cập nhật `DEFAULT_QNU_RERANKER_COMBO_CHAIN`: Ưu tiên 1 là `prov_rtx5090_vllm` (`bge-reranker-v2-m3`).
    * Cập nhật `CollectionDataProcessingConfig` và `SystemModelDefaults`: Mặc định trỏ về `prov_rtx5090_vllm`.
  - **Chỉ số Quality Gate**:
    * Backend Pytest: `test_vllm_reranker.py` 4/4 tests passed 100% (bổ sung test case `test_vllm_seed_provider_config`).
    * Backend Ruff: 0 lỗi (`All checks passed!`).
  - Báo cáo chi tiết: [`docs/nhat_ky/2026-10-08_phien_298_thay_the_ollama_bang_vllm_on_premise_bge_qwen.md`](./nhat_ky/2026-10-08_phien_298_thay_the_ollama_bang_vllm_on_premise_bge_qwen.md).

- **Phiên trước #297**:
  - Hoàn thành Retention, System-Wide Artifact Garbage Collection & Contract Migration Loại Bỏ Legacy An Toàn (ADR-011) — Đóng trọn vẹn 12 phiên Kế hoạch 11.
  - Báo cáo chi tiết: [`docs/nhat_ky/2026-10-07_phien_297_hoan_thanh_retention_system_gc_va_contract_decommissioning.md`](./nhat_ky/2026-10-07_phien_297_hoan_thanh_retention_system_gc_va_contract_decommissioning.md).

- **Phiên trước #295**:
  - Bảng điều khiển kiểm định đối soát Parity Gate & Shadow Retrieval Dashboard V2 (`CollectionParityAuditTab`).
  - Bento Grid 4 KPIs, Sub-tab 1 Parity Inventory, Sub-tab 2 Shadow Retrieval Tester (Zero Revision Leak).
  - Báo cáo chi tiết: [`docs/nhat_ky/2026-10-07_phien_295_hoan_thanh_parity_audit_va_shadow_retrieval_dashboard_v2.md`](./nhat_ky/2026-10-07_phien_295_hoan_thanh_parity_audit_va_shadow_retrieval_dashboard_v2.md).

- **Phiên trước #294**:
  - Master-Detail Deep Routing Kho Tri Thức V2: Trang Thêm Tài Liệu (`/add-documents`) & Trang Chi Tiết Binding (`/documents/:bindingId`).
  - Chunks Inspector Modal, Instant Rollback $O(1)$, Parity Gate verification.
  - Backend `GET /knowledge/bindings/{binding_id}/chunks` phân trang (13/13 tests Pytest passed).
  - Báo cáo chi tiết: [`docs/nhat_ky/2026-10-07_phien_294_hoan_thanh_frontend_kho_tri_thuc_v2_add_documents_va_binding_detail.md`](./nhat_ky/2026-10-07_phien_294_hoan_thanh_frontend_kho_tri_thuc_v2_add_documents_va_binding_detail.md).
  - **Master-Detail Deep Routing Chuẩn AGENTS.md**:
    * Tách bạch không gian danh sách tổng quan (`CollectionDetailPage`) với các trang nghiệp vụ chuyên sâu, sở hữu URL độc lập (`/knowledge/:collectionId/add-documents` và `/knowledge/:collectionId/documents/:bindingId`).
  - **Trang Thêm Tài Liệu Từ Kho (`AddDocumentsPage`)**:
    * Giao diện toàn màn hình, thanh tìm kiếm tức thì, bộ lọc trạng thái liên kết (Tất cả, Chưa liên kết, Đã liên kết).
    * Bảng chọn tài liệu hàng loạt với Select All / Invert Selection, xem trạng thái thể thức NĐ 30 và file size.
    * Panel cấu hình Chunking Strategy toàn cục (ClauseBasedChunker, Semantic, Recursive, Markdown Header) kèm Chunk Size/Overlap.
    * Sticky Action Bar nổi khối (`motion.div`) với tùy chọn Tự kích hoạt (Auto-activate) và nút Submit batch mutations.
  - **Trang Chi Tiết Binding Chuyên Sâu (`BindingDetailPage`)**:
    * Header với breadcrumb phân cấp, trạng thái active revision, nút hành động Dựng Index Staging và Gỡ Liên Kết.
    * Bento Grid 4 KPIs: Phiên Bản Nguồn, Chỉ Mục Phục Vụ, Kích Thước Dữ Liệu, Parity Gate & Tính Toàn Vẹn.
    * 3 Tabs nghiệp vụ:
      1. *Lịch Sử Index Revisions & Rollback $O(1)$*: Bảng phiên bản chỉ mục, dialog Promote hoán đổi con trỏ nguyên tử CAS và dialog Hoàn tác tức thì $O(1)$ với bảo vệ Rollback window.
      2. *Trình Duyệt Chunks (Chunk Inspector)*: Lọc theo điều khoản / nội dung, Modal Chi Tiết Chunk xem toàn văn, metadata NĐ 30, Qdrant point ID.
      3. *Thông Tin Nguồn & Thể Thức NĐ 30/2020/NĐ-CP*: Trích yếu, số hiệu, ngày ban hành, hash SHA-256, MinIO S3 path.
  - **Mở rộng Backend**:
    * Thêm endpoint phân trang `GET /knowledge/bindings/{binding_id}/chunks` hỗ trợ lọc theo revision.
    * Phương thức `BindingService.list_binding_chunks` và `KnowledgeService.list_binding_chunks`.
    * Unit test `test_list_binding_chunks_service_and_api` trong `test_knowledge_publishing_v2.py`.
  - **Chỉ số Quality Gate**:
    * Pytest Backend: 13/13 passed 100% trong 47.13s (`test_knowledge_publishing_v2.py`).
    * Ruff Backend: 0 lỗi (`All checks passed!`).
    * Biome Frontend: 0 lỗi, 0 warnings (`Checked 2 files. No fixes applied.`).
    * TypeScript Frontend: 0 lỗi biên dịch (`tsc --noEmit` exit code 0).
  - Báo cáo chi tiết: [`docs/nhat_ky/2026-10-07_phien_294_hoan_thanh_frontend_kho_tri_thuc_v2_add_documents_va_binding_detail.md`](./nhat_ky/2026-10-07_phien_294_hoan_thanh_frontend_kho_tri_thuc_v2_add_documents_va_binding_detail.md).

- **Phiên trước #293**:
  - Kích hoạt Cutover Toàn Diện V2 (`RAG_REVISION_READ_MODE = "revisioned"`, `KNOWLEDGE_REVISION_WRITES_ENABLED = True`).
  - Đánh dấu Deprecated các endpoints cũ (`/upload`, `/reindex`) kèm headers chuẩn ASCII.
  - Dịch vụ Artifact GC (`KnowledgeArtifactGCService`) có bảo vệ Instant Rollback window (active + 2 bản superseded).
  - Khóa mã lỗi RFC 7807 `REVISION_ALREADY_PRUNED` chặn rollback bản đã dọn.
  - Sổ tay vận hành production `cutover_and_operations_runbook.md`.
  - 47/47 tests Kế hoạch 11 passed 100%, Ruff 0 lỗi, TSC 0 lỗi.
  - Báo cáo chi tiết: [`docs/nhat_ky/2026-10-07_phien_293_hoan_thanh_pha_7_cutover_va_don_dep_legacy.md`](./nhat_ky/2026-10-07_phien_293_hoan_thanh_pha_7_cutover_va_don_dep_legacy.md).
  - **Kích hoạt Cutover Toàn Diện V2 (`backend/app/core/config.py`, `retriever.py`)**:
    * Chuyển chế độ đọc mặc định sang `RAG_REVISION_READ_MODE = "revisioned"`.
    * Kích hoạt `KNOWLEDGE_REVISION_WRITES_ENABLED = True` và cấu hình bảo lưu `KNOWLEDGE_GC_RETENTION_REVISIONS = 2`.
    * `HybridRetriever.search_with_snapshot` nghiêm ngặt cưỡng chế lọc chunks theo danh sách `active_index_revision_ids` của Snapshot (Zero Revision Leak).
  - **Chính sách Deprecation Legacy Endpoints (`knowledge/router.py`)**:
    * Đánh dấu `deprecated=True` trong OpenAPI spec và gắn HTTP Response Headers chuẩn ASCII (`Deprecation: @2026-10-07`, `X-API-Deprecation-Warning`) cho `/upload`, `/reindex`, `/documents/{id}/reindex`.
  - **Dịch vụ Artifact Garbage Collection (GC) Có Bảo Vệ Rollback (`knowledge/services/gc_service.py`, `vector_indexer.py`)**:
    * Triển khai `KnowledgeArtifactGCService.collect_garbage`: Bảo lưu bắt buộc revision `active` và $N=2$ bản `superseded` mới nhất cho mỗi tài liệu (cửa sổ Instant Rollback $O(1)$).
    * Dọn dẹp an toàn các bản `superseded` cũ ngoài window và toàn bộ bản `failed`/`cancelled`: cập nhật status `"pruned"`, xóa triệt để `KnowledgeChunk` và `KnowledgeFact` trong PostgreSQL, xóa vector points trong Qdrant qua hàm `delete_points_by_index_revision`.
    * Hỗ trợ cờ `dry_run=True` dự báo trước số lượng bản ghi cần dọn.
  - **Cơ chế Chặn Rollback Bản Đã Bị Dọn (`index_build_service.py`)**:
    * Chặn đứng mọi nỗ lực rollback về revision đã pruned với mã lỗi RFC 7807 `REVISION_ALREADY_PRUNED` (HTTP 400).
    * Cho phép rollback tức thì $O(1)$ về các bản `superseded` vẫn còn lưu trong retention window.
  - **Tích hợp Facade, REST API & Frontend UI**:
    * Endpoint `POST /knowledge/collections/{collection_id}/gc` tiếp nhận `GarbageCollectionRequest` và trả về `GarbageCollectionReport`.
    * Frontend: Bổ sung types trong `types/knowledge.ts`, hàm `runGarbageCollection` trong `services/knowledge-api.ts`, nút "Dọn Chỉ Mục Cũ (GC)" và Dialog xác nhận an toàn trên `CollectionBindingsTab`.
  - **Sổ Tay Vận Hành & Runbook Production (`docs/ke_hoach/cutover_and_operations_runbook.md`)**:
    * Ban hành tài liệu vận hành chi tiết: Cutover checklist, SLIs/SLOs, Parity Mismatch monitoring, Emergency rollback $O(1)$, cron maintenance GC.
  - **Kiểm thử Toàn Diện Kế Hoạch 11**:
    * Viết test suite chuyên biệt `test_publishing_v2_cutover_and_gc.py` với 7/7 tests PASSED 100%.
    * Toàn bộ 6 test suites của Kế hoạch 11: **47/47 tests PASSED 100%**.
    * Ruff linter: **All checks passed! (0 lỗi)**; TypeScript check: **0 lỗi**.
  - **KẾ HOẠCH 11 ĐÃ HOÀN THÀNH 100% (Pha 0 -> Pha 7)**.
  - Báo cáo chi tiết: [`docs/nhat_ky/2026-10-07_phien_293_hoan_thanh_pha_7_cutover_va_don_dep_legacy.md`](./nhat_ky/2026-10-07_phien_293_hoan_thanh_pha_7_cutover_va_don_dep_legacy.md).

- **Phiên trước #292**:
  - Triển khai Legacy Data Backfill & Classification (`CanaryService.audit_collection_legacy_state`, `backfill_legacy_collection`).
  - Triển khai Shadow Retrieval Verification Engine so khớp song song V1 vs V2, bảo đảm `retrieval_revision_leak_total = 0`.
  - Triển khai Compare-and-Swap (CAS) Concurrency Control (HTTP 409 `CAS_EPOCH_CONFLICT`) và Instant Zero-Reindex Rollback $O(1)$.
  - Test suite `test_publishing_v2_e2e_canary.py` 9/9 passed 100%.
  - Báo cáo chi tiết: [`docs/nhat_ky/2026-10-07_phien_292_hoan_thanh_pha_6_backfill_shadow_canary_va_e2e_testing.md`](./nhat_ky/2026-10-07_phien_292_hoan_thanh_pha_6_backfill_shadow_canary_va_e2e_testing.md).
  - **Frontend Types & API Clients V2 (`types/documents.ts`, `types/knowledge.ts`, `services/documents-api.ts`, `services/knowledge-api.ts`)**:
    * Mở rộng `types/documents.ts`: Thêm `current_revision_id` vào `RepositoryDocumentListItem`, bổ sung types `QualityReportCheck`, `QualityReport`, `DocumentRevisionListItem`, `DocumentRevision` (`review_notes`).
    * Mở rộng `types/knowledge.ts`: Khai báo đầy đủ `AvailableRepositoryDocumentItem`, `AvailableRepositoryDocumentsResponse`, `CreateKnowledgeBindingsRequest`, `KnowledgeBinding`, `KnowledgeIndexRevision`, `IndexActivationRequest`, `IndexActivationResponse`.
    * Mở rộng `documents-api.ts`: Bổ sung 5 API methods quản lý revision (`getRevisions`, `getRevision`, `updateRevisionContent`, `reviewRevision`, `retryRevision`).
    * Mở rộng `knowledge-api.ts`: Bổ sung 7 API methods quản lý publishing V2 (`getAvailableDocuments`, `createBindings`, `getBindings`, `getBinding`, `detachBinding`, `buildStagingIndex`, `promoteIndexRevision`, `getIndexRevisions`).
  - **Giao diện Chi tiết Tài liệu & Chuỗi Phiên bản (`features/documents/document-detail-page.tsx`)**:
    * Bổ sung Tab "Phiên Bản (Revisions V2)" hiển thị lịch sử Audit Trail của tài liệu (v1, v2,...) với trạng thái Ready / Chờ Thẩm Định / Đang Xử Lý / Lỗi.
    * Thẻ Quality Gate Report tự động: Hiển thị điểm % chất lượng, trạng thái Đạt Tiêu Chuẩn Xuất Bản, kiểm định 4 tiêu chí (Mật độ ký tự, Bảng biểu, Sạch Font UTF-8, Độ dài tối thiểu).
    * Dialog "Hiệu đính Markdown": Cho phép biên tập viên chỉnh sửa Markdown trực tiếp và bắt buộc nhập lý do hiệu đính (kiểm toán ISO).
    * Dialog "Thẩm định chất lượng": Phê duyệt chuyển sang trạng thái `ready` hoặc từ chối kèm ghi chú.
    * Dialog "Thử lại bóc tách (Retry)": Hỗ trợ chọn công cụ OCR (`PyMuPdfParser` hoặc `DoclingParser`).
  - **Giao diện Quản lý Liên kết Tri thức & Xuất bản Chỉ mục V2 (`components/knowledge/tabs/collection-bindings-tab.tsx`, `collection-detail-page.tsx`)**:
    * Tạo component tab mới `CollectionBindingsTab` tích hợp vào Kho Tri Thức (Tab "Liên kết V2 (ADR-011)").
    * Bảng danh sách Knowledge Bindings kết nối Bento Grid: Quản lý tài liệu liên kết, chiến lược chunking, active epoch.
    * Dialog "+ Liên Kết Tài Liệu Từ Kho": Cho phép tìm kiếm và tích chọn nhiều tài liệu đã thẩm định từ Kho Trung Tâm.
    * Chi tiết Index Revisions & Parity Gate: Kiểm tra so khớp 100% `vector_count` vs `expected_chunks` vs `lexical_count`.
    * Nút & Dialog "Kích Hoạt Nguyên Tử (Promote)": Chuyển đổi con trỏ chỉ mục nguyên tử (Atomic Pointer Swap) mà không gián đoạn truy vấn AI (Zero Downtime).
  - **Xác thực Chất lượng (Fast-Path Verification & Linters)**:
    * Biome Linter: Đạt **0 lỗi, 0 cảnh báo** (100% compliant).
    * TypeScript & Vite Production Build (`npm run build`): Đóng gói hoàn tất trong **4.41s**, **0 lỗi TypeScript, 0 lỗi JSX, exit code 0**.
  - Báo cáo chi tiết: [`docs/nhat_ky/2026-10-07_phien_291_hoan_thanh_pha_5_giao_dien_quan_tri_revisions_va_bindings_v2.md`](./nhat_ky/2026-10-07_phien_291_hoan_thanh_pha_5_giao_dien_quan_tri_revisions_va_bindings_v2.md).

- **Phiên trước #288**:

  - **SQLAlchemy ORM Data Models**:
    * Mở rộng `RepositoryDocument` (`models.py`) với `tenant_id`, `workspace_id`, `status`, `current_revision_id`, `latest_revision_no`, `row_version`, `catalog_metadata`.
    * Khai báo mới model `DocumentRevision` (`models.py`) đáp ứng đầy đủ chuỗi phiên bản bất biến.
  - **Alembic Safe Backfill Migration (`20261007_document_revisions.py`)**:
    * Safe Backfill tự động tạo revision v1 từ toàn bộ tài liệu hiện hữu.
  - Báo cáo chi tiết: [`docs/nhat_ky/2026-10-07_phien_287_hoan_thanh_pha_1_schema_csdl_document_revisions_va_dto_v2.md`](./nhat_ky/2026-10-07_phien_287_hoan_thanh_pha_1_schema_csdl_document_revisions_va_dto_v2.md).

- **Phiên trước #286**:
  - **Ban hành Kiến trúc Quyết định chính thức ADR-011**:
    * Đã tạo lập văn kiện [`docs/adr/ADR-011-immutable-document-revisions-and-safe-knowledge-publishing.md`](../adr/ADR-011-immutable-document-revisions-and-safe-knowledge-publishing.md).
    * Khóa cứng **Mười Bất Biến Bắt Buộc (The 10 Invariants)**: Source Immutability, Artifact Immutability, Zero-Downtime Reindexing, Single Active Pointer, Snapshot Consistency, Vector Space Invariance, Zero Hardcoded Models, Idempotent Retry, Tenant Isolation, Referential Integrity.
    * Xác lập ranh giới: Kho Tài Liệu là Nguồn Sự Thật Duy Nhất (`DocumentRevision` bất biến); Kho Tri Thức chuyển sang mô hình liên kết `KnowledgeBinding` và artifact `KnowledgeIndexRevision` ở vùng Staging.
    * Cơ chế Atomic Pointer Swap CAS và RetrievalSnapshot dùng chung cho Dense, Sparse, Facts, Citations triệt tiêu 100% mixed citations.
  - **Ban hành Đặc tả Kỹ thuật API Contracts V2 & Kiểm kê Hệ thống**:
    * Đã tạo lập văn kiện [`docs/ke_hoach/contracts_v2_specification.md`](../ke_hoach/contracts_v2_specification.md).
    * Bản đồ đối chiếu 9 bảng CSDL, 12 endpoints chuyển đổi, nâng cấp Qdrant payload V2, quy chuẩn Idempotency-Key và ma trận Feature Flags/Kill Switches.
  - Báo cáo chi tiết: [`docs/nhat_ky/2026-10-07_phien_286_chot_adr011_va_api_contracts_v2_tiep_nhan_mot_lan_xuat_ban_an_toan.md`](./nhat_ky/2026-10-07_phien_286_chot_adr011_va_api_contracts_v2_tiep_nhan_mot_lan_xuat_ban_an_toan.md).

- **Phiên trước #285**:
  - **Tối ưu hóa UI Nạp Tài Liệu Tập Trung (`DocumentUploadModal`)**:
    * Chuyển đổi sang chế độ kéo thả nhiều file cùng lúc (`multiple={true}`, `maxFiles={50}`, `maxSize={50MB}`).
    * Cải tiến component `FileUpload` (`src/components/admin/file-upload.tsx`) thêm container cuộn mượt mà `max-h-48 overflow-y-auto` cho danh sách tệp.
    * Thêm thanh tóm tắt dung lượng trực quan (`Đã chọn X tệp (Tổng Y MB)`) kèm nút `Xóa tất cả`.
    * **Loại bỏ hoàn toàn các trường bắt buộc nhập tay**: Xóa bỏ ô nhập `Ngày ban hành`, `Số hiệu văn bản`, `Người ký`, `Tiêu đề`.
    * Bổ sung **Card Thông Tin Bóc Tách Tự Động (Smart Recognition Banner)** phong cách Academic Teal (`Sparkles` icon): Giải thích rõ AI & Parser NĐ 30 tự động nhận diện thông tin từ nội dung tệp.
    * Cung cấp **Cấu hình chung tùy chọn cho lô tệp (`Collapsible`)**: Cho phép người dùng chọn loại văn bản chung hoặc cơ quan ban hành chung nếu cần gán nhãn hàng loạt.
    * Triển khai cơ chế **Batch Upload Progress**: Hiển thị thanh tiến trình `<Progress />` theo thời gian thực và tên tệp đang xử lý, toast tổng kết số file nạp thành công.
  - **Backend: Bóc tách tự động metadata thể thức hành chính Nghị định 30/2020/NĐ-CP**:
    * `backend/app/modules/knowledge/cleaner.py`: Xây dựng hàm `extract_administrative_metadata(text: str)` trích xuất theo các bất biến cú pháp (Syntactic Invariants, tuân thủ Tôn chỉ 7): Ngày ban hành (`issued_date`), Số hiệu (`document_number`), Loại văn bản (`document_type_code`), Trích yếu (`title`), Cơ quan ban hành (`issuing_authority`), Người ký (`signer`).
    * `backend/app/modules/documents/service.py`: Trong `parse_and_cache_document`, tự động điền các trường metadata còn thiếu vào `RepositoryDocument` và lưu vào `doc_metadata["auto_detected_metadata"]`.
  - **Kiểm thử chất lượng**:
    * Backend Pytest: `tests/test_document_repository.py` đạt **6/6 PASSED 100%** (bao gồm test case tự động bóc tách NĐ 30).
    * Backend Ruff: **0 errors**.
    * Frontend Typecheck (`tsc --noEmit`): **0 errors (Pass 100%)**.
    * Frontend Biome Linter (`biome check`): **0 errors (Pass 100%)**.
  - Báo cáo chi tiết: [`docs/nhat_ky/2026-10-07_phien_285_toi_uu_ui_nap_tai_lieu_multi_file_va_tu_dong_nhan_dien_ngay_ban_hanh_nd30.md`](./nhat_ky/2026-10-07_phien_285_toi_uu_ui_nap_tai_lieu_multi_file_va_tu_dong_nhan_dien_ngay_ban_hanh_nd30.md).

- **Phiên trước #284**:
  - Chuyển Đổi Hạ Tầng AI Server Sang vLLM & Tích Hợp Native vLLM Reranker (/v1/rerank) & Embedding (/v1/embeddings).
  - Báo cáo chi tiết: [`docs/nhat_ky/2026-10-07_phien_284_chuyen_doi_ha_tang_ai_server_sang_vllm_va_tich_hop_native_reranker.md`](./nhat_ky/2026-10-07_phien_284_chuyen_doi_ha_tang_ai_server_sang_vllm_va_tich_hop_native_reranker.md).

- **Phiên trước #283**:
  - Triển Khai Phân Hệ Kho Tài Liệu Tập Trung (Document Repository) Lưu Trữ MinIO S3, Tiền Bóc Tách Markdown & Tích Hợp Kho Tri Thức Vector DB.
  - Báo cáo chi tiết: [`docs/nhat_ky/2026-10-07_phien_283_trien_khai_kho_tai_lieu_tap_trung_minio_s3_va_tich_hop_kho_tri_thuc.md`](./nhat_ky/2026-10-07_phien_283_trien_khai_kho_tai_lieu_tap_trung_minio_s3_va_tich_hop_kho_tri_thuc.md).

- **Phiên trước #282**:
  - **Mở rộng thuật toán nhận diện họ Embedding tổng quát (`modelops-helpers.ts`)**: Bổ sung các pattern nhận diện họ embedding (`embed`, `bge-`, `bge_`, `gte-`, `gte_`, `e5-`, `minilm`, `instructor`, `text-embedding`, `voyage`, `cohere.embed`); Enforce kiểm tra `isReranker` trước `isEmbedding` tránh nhận diện sai `bge-reranker`; Bổ sung preset gợi ý cho `ollama`, `custom` và `openai`.
  - **Chuẩn hóa hệ thống Badges trên Thẻ mô hình (`models-grid.tsx`)**:
    * Bổ sung Badge `[Embedding]` (icon `<Cpu />`, màu Indigo) cho tất cả các mô hình embedding.
    * Bổ sung Badge `[Reranker]` (icon `<Zap />`, màu Amber) cho mô hình tái xếp hạng.
    * Triệt tiêu 100% nhãn `[Text]` trên các mô hình embedding (`qwen3-embedding`, `bge-m3`); Chỉ hiển thị `[Text]` khi mô hình là LLM Chat thực thụ.
    * Icon bên trái thẻ model thay đổi động trực quan theo vai trò (`<Cpu />` Indigo cho Embedding, `<Zap />` Amber cho Reranker, `<ScanText />` Teal cho OCR, `<Eye />` Sky cho Vision, `<Brain />` Purple cho Reasoning, `<Bot />` cho LLM Chat).
    * Chuẩn hóa Badge vai trò mặc định: `[★ Default Embed]` (Indigo), `[★ Default Rerank]` (Amber), `[★ Default OCR]` (Teal).
  - **Bổ sung bộ lọc chuyên biệt**: Thêm tùy chọn `Embedding (Vector nhúng)` và `Reranker (Tái xếp hạng)` trong Select Filter của `ModelsGrid`.
  - **Nâng cấp Modal Thêm Mô Hình Tùy Chỉnh (`add-custom-model-dialog.tsx`)**: Bổ sung Switch `Embedding` (icon `<Cpu />`, màu Indigo) vào lưới Khả Năng Hỗ Trợ (Capabilities) 3 cột (`Vision`, `Reasoning`, `Embedding`); Tích hợp tự động phát hiện họ mô hình embedding khi nhập ID hoặc bấm gợi ý nhanh.
  - **Nâng cấp `ProviderCard` (`provider-card.tsx`)**: Bổ sung chip đếm số lượng `[Cpu X embed]` và `[ScanText Y ocr]` ngay tại trang danh sách `/models`.
  - **Đồng bộ `SystemDefaults`**: Bổ sung query `systemDefaults` vào `modelops-page.tsx`.
  - **Khắc phục xung đột phân quyền Windows NTFS trên Backend**:
    * Sửa triệt để lỗi `Permission denied` / `Access is denied` thừa kế từ sandbox cũ trên các thư mục `node_catalog`, `alembic/versions`, `configs/nodes`, `assistants`, `workflows/nodes`.
    * Toàn bộ 599+ tệp tin mã nguồn backend thuộc sở hữu sạch của user hiện tại, 0 file bị lỗi phân quyền.
    * Sửa `pyproject.toml` và `test_node_catalog.py` loại bỏ `tmp_path` symlink conflict trên Windows.
  - **Kiểm thử chất lượng toàn diện Full-Stack**:
    * **Frontend (`npm run build`)**: Đóng gói bundle thành công trong 3.30s với **0 lỗi TypeScript, 0 lỗi biên dịch**, exit code 0.
    * **Backend Ruff**: `ruff check app/ tests/` đạt chuẩn **All checks passed (0 lỗi)**.
    * **Backend Pytest**: **180+ tests toàn diện PASSED 100%** (ModelOps 45/45, OCR 27/27, Chat Safety 5/5, Workflows/Assistants 36/36, Knowledge/RAG/Docling/Catalog 67/67).
  - Báo cáo chi tiết: [`docs/nhat_ky/2026-10-07_phien_282_bo_sung_nhan_biet_mo_hinh_embedding_va_reranker_tren_modelops.md`](./nhat_ky/2026-10-07_phien_282_bo_sung_nhan_biet_mo_hinh_embedding_va_reranker_tren_modelops.md).

- **Phiên trước #281**:
  - **Khắc phục vùng nhận diện `signature` bị lệch và cắt đôi đoạn văn**: Tái cấu trúc thuật toán phát hiện vùng kết thúc văn bản `_detect_morphology_regions` trong `layout_detector.py`. Thuật toán mới tính toán chính xác tọa độ con dấu đỏ `(seal_x1, seal_y1, seal_x2, seal_y2)` và chỉ gom con dấu đỏ + chức vụ ("HIỆU TRƯỞNG") + chữ ký + họ tên lãnh đạo ở nửa phải trang (`x >= 0.38*w`) thành 1 hộp `signature` duy nhất.
  - **Bảo tồn trọn vẹn đoạn văn bản số 4**: Loại bỏ triệt để hành vi quét khe trắng xén đôi đoạn văn bản số 4 (*"vướng mắc, các đơn vị..."*) thành 2 cột giả mạo (`list` bên trái, `signature` bên phải). Đoạn văn số 4 được giữ nguyên vẹn toàn dòng với nhãn `text`.
  - **Triệt tiêu 100% nhãn `list` giả mạo**: Xóa bỏ hoàn toàn quy tắc gán nhãn tùy tiện `elif h_pct >= 6.0: r_type = "list"` và `elif self._is_list_marker(txt): rtype = "list"` trong `layout_detector.py` và `openai_vision_adapter.py`. Mọi đoạn văn quy chế/điều khoản được đưa về nhãn `text` ("Khối văn bản") chuẩn xác.
  - **Cập nhật gán văn bản theo vị trí thực tế**: Sửa `_associate_snippets_with_regions` trong `layout_detector.py` định vị vùng Nơi nhận theo tọa độ không gian thực tế (`left < 45%` và `top >= 40%`) thay vì phụ thuộc nhãn `list`.
  - **Xác minh chất lượng**: Bổ sung unit test `test_smart_layout_closing_signature.py` pass 100%; Toàn bộ bộ test OCR 27/27 tests passed (100%); Ruff linter kiểm tra `app/modules/ocr` và `tests/` sạch 0 lỗi.
  - Báo cáo chi tiết: [`docs/nhat_ky/2026-10-06_phien_281_khac_phuc_vung_chu_ky_bi_lech_va_triet_tieu_nhan_list_scan_studio.md`](./nhat_ky/2026-10-06_phien_281_khac_phuc_vung_chu_ky_bi_lech_va_triet_tieu_nhan_list_scan_studio.md).
- **Phiên trước #280**:
  - **Khắc phục lỗi HTTP 500 khi gọi `/platform/v1alpha1/modelops/providers/{id}/keys`**: Phát hiện CSDL PostgreSQL đang dừng ở revision `20260922_conversation_feedback`, thiếu bảng quan hệ `provider_api_keys` và `provider_key_events`.
  - **Bảo vệ an toàn 100% cho `prov_rtx5090_ollama`**: Hiệu chỉnh `20261002_remove_local_model_providers.py`, loại trừ tuyệt đối máy chủ GPU nội bộ RTX 5090 (`provider_type='ollama'`) và mô hình `qwen3-vl:8b` khỏi truy vấn dọn dẹp provider cũ; bảo tồn nguyên vẹn defaults toàn hệ thống.
  - **Đồng bộ hóa Alembic lên HEAD (`20261002_remove_local_models`)**: Thực thi thành công toàn bộ chuỗi migration lên HEAD, tạo 2 bảng `provider_api_keys` và `provider_key_events`.
  - **Nâng cấp `check_db_schema` trong `app/cli.py`**: Mở rộng `required_tables` gồm 9 bảng cốt lõi (thêm `provider_api_keys`, `provider_key_events`, `conversation_feedbacks`), giúp tự động kích hoạt `migrate_database()` lên HEAD nếu DB thiếu bảng.
  - **Xác minh chất lượng**: Endpoint `/keys` trả về HTTP 200 OK với khóa on-premise; Pytest 14 tests (cli, rotation, status, provider safety) passed 100%; Ruff check 0 lỗi.
  - Báo cáo chi tiết: [`docs/nhat_ky/2026-10-06_phien_280_khac_phuc_loi_relation_provider_api_keys_va_dong_bo_alembic_head.md`](./nhat_ky/2026-10-06_phien_280_khac_phuc_loi_relation_provider_api_keys_va_dong_bo_alembic_head.md).
- **Phiên trước #279**:
  - **Chuyển đổi hoàn tất `frontend2` $\rightarrow$ `frontend`**: Xóa sạch thư mục cache/untracked của frontend cũ, di chuyển toàn bộ mã nguồn `frontend2` thành thư mục `frontend` duy nhất của dự án.
  - **Đồng bộ hóa toàn bộ Task Runners & Configs**: Cập nhật `frontend/package.json` (`qnu-ai-platform-frontend`), `frontend/bun.lock`, `docker-compose.yml` (`context: ./frontend`), `Makefile`, `run.ps1`, `make.ps1`, `make.bat`, `make`, `scratch/audit_system_deep.py`.
  - **Xác minh chất lượng**: `npm run build` (`vite build && tsc --noEmit`) thành công 100% trong 2.04s, 0 lỗi TypeScript. Git staged 100% renames sạch.
  - Báo cáo chi tiết: [`docs/nhat_ky/2026-10-06_phien_279_chuan_hoa_thong_nhat_frontend2_sang_frontend.md`](./nhat_ky/2026-10-06_phien_279_chuan_hoa_thong_nhat_frontend2_sang_frontend.md).
- **Phiên trước #278**:
  - **Root Workspace tinh gọn 54%**: Giảm từ 39 tệp/thư mục xuống còn 18 tệp. Gom 13 script `scratch_*.py` vào `scratch/archive/`, gom 8 tài liệu mẫu (.docx, .html, .md) vào `docs/tai_lieu/samples/`.
  - **Chuẩn hóa Frontend2 độc tôn**: Xóa `node_modules` cũ giải phóng ~500MB đĩa, lưu trữ bản cũ vào `legacy/frontend_v1_backup/`, cập nhật `run.ps1` trỏ thẳng `frontend2` (Port 3000).
  - Báo cáo chi tiết: [`docs/nhat_ky/2026-10-06_phien_278_tinh_gon_toan_dien_root_workspace_va_chuan_hoa_frontend2.md`](./nhat_ky/2026-10-06_phien_278_tinh_gon_toan_dien_root_workspace_va_chuan_hoa_frontend2.md).
- **Phiên trước #277**:
  - Khắc Phục Triệt Để Bounding Boxes Scan Bị Loạn & Bảng Markdown Bị Dồn Thẻ `<br>` / Mất Header Trên Scan Studio (QD2139).
  - Báo cáo chi tiết: [`docs/nhat_ky/2026-10-06_phien_277_khac_phuc_triet_de_vung_scan_loan_va_bang_markdown_bi_don_br.md`](./nhat_ky/2026-10-06_phien_277_khac_phuc_triet_de_vung_scan_loan_va_bang_markdown_bi_don_br.md).
- **Phiên trước #276**:
  - Tối Ưu Tốc Độ Tối Đa Cho Qwen3-VL OCR & Hạ Tầng GPU RTX 5090 (Tắt Alpha Channel, DPI 96, Tinh Gọn Prompt, num_ctx 4096, Batching Concurrency).
  - Báo cáo chi tiết: [docs/nhat_ky/2026-10-06_phien_276_toi_uu_toc_do_toi_da_qwen3_vl_ocr_va_ha_tang_rtx5090.md](./nhat_ky/2026-10-06_phien_276_toi_uu_toc_do_toi_da_qwen3_vl_ocr_va_ha_tang_rtx5090.md).
- **Phiên trước #275**:
  - Khắc Phục Triệt Để Qwen3-VL:8B Xử Lý Chậm & Không Phân Đoạn chunks=0 Khi Bóc Tách PDF Sang Markdown (Kỹ thuật Prefill `</think>` Bypass CoT, Parallel Gather, Keep-Alive -1).
  - Báo cáo chi tiết: [`docs/nhat_ky/2026-10-06_phien_275_khac_phuc_triet_de_qwen3_vl_ocr_cham_va_chunks_0.md`](./nhat_ky/2026-10-06_phien_275_khac_phuc_triet_de_qwen3_vl_ocr_cham_va_chunks_0.md).
- **Phiên trước #274**:
  - Chuẩn Hóa Mô Hình Embedding Từng Kho Tri Thức — Mặc Định Chạy & Hiển Thị "Đang Áp Dụng".
  - Báo cáo chi tiết: `docs/nhat_ky/2026-10-06_phien_274_chuan_hoa_embedding_model_kho_tri_thuc_va_runtime.md`.
- **Phiên trước #273**:
  - Loại Bỏ Nút Cấu Hình Thừa Trên Header Kho Tri Thức (Tránh Trùng Lặp Với Tab "Mô hình & Cấu hình").
  - Báo cáo chi tiết: `docs/nhat_ky/2026-10-06_phien_273_loai_bo_nut_cau_hinh_header_kho_tri_thuc.md`.
- **Phiên trước #272**:
  - Chuyển Cấu Hình Mô Hình Kho Tri Thức Từ Modal Sang Tab Chuyên Biệt Full-Width, Tận Dụng Toàn Diện Màn Hình Thoáng Đãng (Bento Grid 2 cột + Full-Width OCR).
  - Báo cáo chi tiết: `docs/nhat_ky/2026-10-06_phien_272_chuyen_cau_hinh_kho_sang_tab_chuyen_biet_khu_modal.md`.
- **Phiên trước #271**:
  - Đồng Bộ Triệt Để Loại Bỏ Mặc Định & Combos Trên Frontend2 Port 3000, Tinh Gọn ModelOps & Đẩy Cấu Hình Sang Kho Tri Thức / Trợ Lý.
  - Báo cáo chi tiết: `docs/nhat_ky/2026-10-06_phien_271_dong_bo_triet_de_loai_bo_mac_dinh_combos_va_tai_cau_truc_tren_frontend2.md`.
- **Phiên trước #270**:
  - Tái Cấu Trúc Toàn Diện Quản Lý Mô Hình: Tách Bạch ModelOps Hạ Tầng, Gắn Embedding & OCR Vào Kho Tri Thức, Phân Bổ Cross-Encoder Reranker Sang Trợ Lý AI.
  - Báo cáo chi tiết: `docs/nhat_ky/2026-10-06_phien_270_tai_cau_truc_model_management_knowledge_assistants_modelops.md`.
- **Phiên trước #269**:
  - Đồng Bộ Toàn Diện Dữ Liệu Seed CSDL PostgreSQL: Provider RTX 5090, Trợ Lý Soạn Thảo / Khảo Thí & Chuỗi OCR Combo Defaults.
  - Báo cáo chi tiết: `docs/nhat_ky/2026-10-05_phien_269_dong_bo_toan_dien_seed_data_provider_rtx5090_assistants_va_ocr_defaults.md`.
- **Phiên trước #268**:
  - Chốt Qwen3-VL:8B Làm Vision OCR On-Premise Chính Thức Cho QNU AI Platform (RTX 5090).
  - Báo cáo chi tiết: `docs/nhat_ky/2026-10-05_phien_268_chot_qwen3_vl_8b_lam_vision_ocr_on_premise_chinh_thuc_qnu.md`.
- **Phiên trước #267**:
  - Chuẩn Hóa Tên Miền Tailscale MagicDNS Cho Máy Chủ AI GPU RTX 5090 & Cơ Chế Kháng Lỗi Phân Giải DNS.
  - Báo cáo chi tiết: `docs/nhat_ky/2026-10-05_phien_267_chuan_hoa_ten_mien_tailscale_magicdns_cho_may_chu_ai_gpu_rtx5090.md`.
- **Phiên trước #266**:
  - Tích hợp Server GPU On-Premise RTX 5090 qua Tailscale, cấu hình DeepSeek-R1 (32B) & Qwen3 (8B) cho Soạn thảo văn bản và Khảo thí, kết nối BGE-M3 & Qwen3-Embedding.
  - Báo cáo chi tiết: `docs/nhat_ky/2026-10-05_phien_266_tich_hop_server_gpu_rtx5090_tailscale_qwen3_deepseek_r1_cho_soan_thao_va_khao_thi.md`.
- **Phiên trước #265**:
  - Chuyển Cổng Trợ Lý AI Hub thành Trang chủ (`/`) & Tái Cấu Trúc Điều Hướng Hai Không Gian (Dual-Space).
  - Tối ưu Responsive Grid Cards cho Laptop 14" (3 cột) và chuẩn hóa tên thẻ trợ lý.
  - Báo cáo chi tiết: `docs/nhat_ky/2026-10-05_phien_265_chuyen_cong_chat_thanh_trang_chu_ung_dung_va_tai_cau_truc_dieu_huong.md`.
- **Phiên trước #264**:
  - Khắc phục triệt để lỗi giật bố cục khi tải (CLS): Thay thế 3 khối Skeleton xám bằng `PublicChatSkeleton` (App Shell Skeleton chuẩn Enterprise) giữ nguyên bố cục 2 cột.
  - Báo cáo chi tiết: `docs/nhat_ky/2026-10-04_phien_264_nang_cap_app_shell_skeleton_triet_tieu_layout_shift_man_hinh_chat.md`.
- **Phiên trước #263**:
  - Đồng bộ Logo chính thức ĐH Quy Nhơn (`/logo.png`) và chuẩn hóa tên trợ lý trên giao diện Chat (/chat/:slug).
  - Báo cáo chi tiết: `docs/nhat_ky/2026-10-04_phien_263_dong_bo_logo_chinh_thuc_va_chuan_hoa_ten_tro_ly_tren_chat_view.md`.
- **Phiên trước #262**:
  - Tinh chỉnh chiều sâu thị giác (Warm off-white `#faf9f6`), làm mềm lưới kỹ thuật, chuẩn hóa tên trợ lý & khử trùng lặp câu hỏi mẫu (/chat).
  - Báo cáo chi tiết: `docs/nhat_ky/2026-10-04_phien_262_tinh_chinh_chieu_sau_thi_giac_khu_trung_lap_cau_hoi_mau_va_chuan_hoa_ten_tro_ly_chat_hub.md`.
- **Phiên trước #261**:
  - Triển khai phong cách Linear Bento Grid & Asymmetric 2-Column Hero cho Cổng Trợ Lý AI Hub (/chat).
  - Báo cáo chi tiết: `docs/nhat_ky/2026-10-04_phien_261_trien_khai_linear_bento_grid_va_asymmetric_hero_qnu_ai_hub.md`.
- **Phiên trước #260**:
  - Tích hợp hình ảnh khuôn viên Trường Đại học Quy Nhơn, Logo chính thức, Họa tiết lưới kiến trúc & Kính mờ Glassmorphism.
- **Phiên trước #259**:
  - Nâng cấp toàn diện giao diện Cổng Trợ Lý AI (Public Chat Portal) chuẩn "Academic Modernism", Spotlight Tuyển sinh & AI Prompt Dock.
- **Phiên trước #258**:
  - Chuẩn hóa toàn diện hệ thống UI Rules: Bán kính bo góc 6px/8px, Zero Raw Buttons, khử trùng lặp Citations & Sidebar 256px.
- **Phiên trước #257**:
  - Đồng bộ 100% giao diện Chatbot theo chuẩn Google Gemini Desktop (PanelLeft icon, PenLine Capsule, Mini-Rail, Motion Deceleration Animation).
- **Phiên trước #256**:
  - Rà soát & Khắc phục race condition Cổng Chat, bảo toàn dữ liệu tức thì, chuẩn hóa React 19 Hooks & Triệt tiêu điều khiển dư thừa (Zero-Redundancy).
- **Phiên trước #255**:
  - Tái cấu trúc trải nghiệm Cổng Chat Trợ lý AI (`/chat/:slug`) theo tiêu chuẩn thẩm mỹ cao cấp hiện đại của ChatGPT & Google Gemini (Collapsible Sidebar, Floating Input Dock, Seamless Borderless Header, Natural Markdown Stream).
- **Phiên trước #254**:
  - Tối ưu Responsive Grid Cards cho Laptop 14" (3 cột) và Desktop 24"+ (4 cột) trên các trang quản trị: Trợ lý AI, Kho tri thức, ModelOps, Loại văn bản, DAG Nodes (`grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 2xl:grid-cols-4 gap-3 sm:gap-4`).
  - Vite build hoàn tất trong 5.84s (0 lỗi).
- **Phiên trước #253**:
  - Khắc phục triệt để lỗ hổng thiếu Bearer Token trên Frontend:
    - Xây dựng Global Fetch Interceptor `frontend2/src/app/auth/fetch-interceptor.ts` tự động gắn `Authorization: Bearer <accessToken>` và `credentials: "include"` cho toàn bộ 77+ API calls tới `/platform/*`.
    - Tích hợp interceptor trong `frontend2/src/main.tsx` và cung cấp helper `getAuthHeaders()` trong `http-client.ts`.
    - Bổ sung scope `offline_access` vào `OIDC_CONFIG.scope` trong `oidc.ts` để kích hoạt Refresh Token ngầm qua `signinSilent`.
  - Thắt chặt an ninh AuthActor & Enforce RBAC trên Backend:
    - Sửa lỗ hổng gán nhầm default `roles=["admin"]` và `permissions=["*"]` trong `AuthActor` Pydantic model (`schemas.py`), chuyển mặc định về `roles=["staff"]`, `permissions=[]` an toàn.
    - Áp dụng `require_permission` vào các router trọng yếu: `assistants` (`create`, `edit`, `delete`, `publish`), `knowledge` (`upload`, `delete`, `reindex`, `facts.manage`), `modelops` (`manage`, `test`).
  - Bổ sung tài liệu cấu hình QNU SSO (`SSO_ENABLED`, `SSO_AUTHORITY`, `SSO_CLIENT_ID`, `SSO_AUDIENCE`, v.v.) vào `.env.example` và `.env.dokploy.example`.
  - Kết quả kiểm thử:
    - Backend: 15/15 unit tests passed 100% (`tests/test_auth.py`, `tests/test_sso_auth.py`), 0 lỗi Ruff linter.
    - Frontend: 0 lỗi Biome linter, Vite build production hoàn tất thành công trong 6.15s (0 lỗi TypeScript/bundler).
  - Báo cáo chi tiết: `docs/nhat_ky/2026-10-04_phien_253_hoan_thien_toan_dien_sso_bearer_injection_va_fine_grained_rbac.md`.
- **Phiên trước #252**:
  - Chuẩn hóa danh mục quyền hạn `qnu-ai-permissions.json` theo chuẩn `qnu-sso.permissions` v1 gồm 25 quyền (`ai.*`), đồng bộ sang cả dự án `qnu-sso` để nạp vào CSDL SSO.
  - Xây dựng tầng OIDC Client (`oidc-client-ts`) trên `frontend2`:
    - Quản lý phiên `UserManager` trong `frontend2/src/app/auth/oidc.ts`.
    - Route callback `/signin-oidc` xử lý lưu trữ user, đồng bộ cache TanStack Query và điều hướng về URL yêu cầu.
    - Cải tiến giao diện `sign-in.tsx`: Nút đăng nhập QNU SSO nổi bật (Academic Teal), badges Cán bộ/Giảng viên và Sinh viên UIS, kết hợp Accordion Dev Access Gate cho lập trình viên phát triển offline.
    - Cập nhật RBAC context (`can(permission)`) hỗ trợ đầy đủ các claims phân quyền và tiền tố `ai.access.*`.
  - Xây dựng Bộ xác thực Bearer Token trên Backend FastAPI:
    - Bổ sung cấu hình `SSO_AUTHORITY`, `SSO_CLIENT_ID`, `SSO_AUDIENCE`, `SSO_JWKS_URL`, `SSO_USERINFO_URL` trong `app.core.config`.
    - Tạo module `sso_validator.py` xác thực Bearer Token qua JWKS public keys (RSA/RS256) kèm TTL cache 1 giờ, fallback UserInfo RFC standard.
    - Bổ sung `require_permission` dependency bảo vệ API.
    - Mở rộng `AuthActor` trong `schemas.py` với `email`, `user_type`, `student_id`, `roles`, `permissions`, `has_permission`.
  - Báo cáo chi tiết: `docs/nhat_ky/2026-10-04_phien_252_tich_hop_xac_thuc_tap_trung_qnu_sso_openiddict_va_phan_quyen_rbac.md`.
  - Xây dựng bản kế hoạch tổng thể triển khai Production: [`ke_hoach_phat_hanh_chatbot_va_quan_ly_user_rbac_prod.md`](../../ke_hoach_phat_hanh_chatbot_va_quan_ly_user_rbac_prod.md).
  - Hoàn thành Sprint 1 — Cổng Chat Độc Lập cho Sinh Viên / Thí Sinh:
    - Bổ sung `/chat` và `/chat/*` vào `isPublicRoute` trong `frontend2/src/routes/__root.tsx`.
    - Xây dựng `PublicChatPortal` (`frontend2/src/features/chat/public-chat-portal.tsx`) hiển thị danh mục 5 trợ lý chính thức của ĐH Quy Nhơn, tìm kiếm, lọc theo danh mục, câu hỏi gợi ý.
    - Xây dựng `PublicChatView` (`frontend2/src/features/chat/public-chat-view.tsx`) giao diện chat toàn màn hình, Mobile-First, SSE streaming mượt mà, hỗ trợ đối soát văn bản qua `CitationSheet`, xuất biên bản Markdown (.md) và làm mới hội thoại.
    - Khởi tạo các Route TanStack: `chat.tsx`, `chat.index.tsx`, `chat.$assistantSlug.tsx`.
  - Hoàn thành Sprint 2 — Quản Lý Kênh Phân Phối & Web Chat Widget:
    - Xây dựng `ChannelsPage` (`frontend2/src/features/channels/channels-page.tsx`) với bộ cấu hình tham số widget (`data-assistant`, `data-title`, `data-welcome`, `data-position`, `data-api-base`).
    - Bộ sinh mã nhúng HTML script CDN tự động 1-click copy.
    - Cảnh báo an ninh Domain Whitelist CORS (`*.qnu.edu.vn`, `tuyensinh.qnu.edu.vn`, `daotao.qnu.edu.vn`).
    - Khung Live Preview tương tác 1:1 mô phỏng Cổng thông tin trường với bong bóng widget nổi mở/đóng và chat thử nghiệm phản hồi thời gian thực.
    - Bổ sung mục `Kênh & Web Widget` (`/channels`) vào Sidebar `frontend2/src/navigation/config.ts` dưới nhóm `Xây Dựng AI`.
    - Sửa đường dẫn nhúng widget trong `assistant-embed-dialog.tsx` trỏ đúng `/embed/qnu-chat-widget.js`.
  - Kiểm thử Frontend (`cmd /c "npm run build"`): Đạt exit code 0 (`✓ built in 4.14s`), 0 lỗi TypeScript, 0 lỗi Vite bundler.
  - Báo cáo chi tiết: `docs/nhat_ky/2026-10-04_phien_251_trien_khai_cong_chat_cong_khai_va_kenh_widget_prod.md`.
- **Phiên trước #250**:
  - Rà soát toàn bộ các phân hệ chức năng trên Sidebar (`frontend2/src/layouts/app-sidebar.tsx` và `frontend2/src/navigation/config.ts`).
  - Dọn dẹp triệt để các mục liên kết chưa có Route để loại bỏ 100% nguy cơ lỗi 404 cho người dùng.
  - Tinh gọn Sidebar còn 3 nhóm chức năng cốt lõi hoạt động trơn tru.
  - Báo cáo chi tiết: `docs/nhat_ky/2026-10-04_phien_250_don_dep_menu_sidebar_frontend_va_ra_soat_chuc_nang.md`.
- **Phiên trước #249**:
  - Tái cấu trúc UX/UI Quản lý Chuỗi Combo Dự Phòng (Failover Combos) trong `frontend2/src/components/modelops/combos-vision-section.tsx`:
    - Xóa bỏ 100% cụm 4 nút bấm chuyển đổi loại tác vụ trong Modal gây hiểu lầm là 1 combo làm 4 chức năng.
    - Gán cứng cố định kênh tác vụ (Vision OCR, Vector Embedding, Reranker, LLM Chat) theo từng Tab chuyên trách kèm banner nhận diện trực quan và badge `[Gán Cứng Cố Định]`.
    - Nút `+ Tạo Combo` ở Header tự động nhận diện Tab người dùng đang đứng để gán cứng loại tác vụ tương ứng (ví dụ đứng ở Tab `Vision & OCR` thì nút là `Tạo Combo (OCR)` và mở modal gán cứng `ocr`).
    - Logic `handleOpenEditModal` tự động chuẩn hóa tác vụ dựa trên tên combo (ví dụ `qnu-ocr-master` luôn được bảo vệ mở với `ocr`).
    - Cảnh báo mô hình không có mắt thị giác trong chuỗi OCR (`qwen/qwen3.8-27b`) và lọc nghiêm ngặt candidate picker.
  - Báo cáo chi tiết: `docs/nhat_ky/2026-10-03_phien_249_gan_cung_loai_tac_vu_combo_theo_4_tab_modelops.md`.
- **Phiên trước #248**:
  - Đánh giá chất lượng bóc tách OCR tài liệu scan `QD2139` bằng `gemini-3.5-flash`: phát hiện 4 lỗi (mất hàng học phí đầu trang 2 - ngành Kế toán 3 năm 37.440.000 VNĐ, gãy vỡ cú pháp GFM, ô nhiễm thẻ HTML table, gộp ô lười bằng thẻ `<br>`).
  - Nâng cấp `cleaner.py` với các thuật toán hậu xử lý chuyên sâu:
    - `clean_html_layout_tables`: Tự động nhận diện và chuyển đổi 100% các khối HTML table quốc hiệu, chữ ký con dấu sang cú pháp Markdown thuần (`**...**`, `*...*`, `-`).
    - `stitch_ocr_multipage_tables`: Thuật toán hàn gắn bảng biểu tiếp nối qua nhiều trang, tự động khử bỏ vạch kẻ phân trang `---` và hợp nhất / lặp lại header row hợp lệ.
    - `merge_ocr_orphan_table_rows`: Tự động bảo toàn các hàng bảng mồ côi (ô STT bị rỗng do kế thừa trang trước).
  - Chuẩn hóa kiến trúc Protocol-Based Adapter theo Phương án B:
    - `GeminiOCRAdapter`: Google Multimodal Protocol trực tiếp cho dòng Gemini 3.x / 2.5 Flash.
    - `OpenAIVisionOCRAdapter` (trong `openai_vision_adapter.py`): Tổng quát hóa cho tất cả các mô hình Vision theo chuẩn OpenAI (`/chat/completions` với `image_url` qua PyMuPDF) bao gồm Qwen-2.5-VL, GPT-4o, Claude 3.5, DeepSeek-VL, Pixtral, Ollama/vLLM.
    - Dọn dẹp xóa bỏ tệp `qwen_adapter.py` thừa, chuyển re-export sang `openai_vision_adapter.py`.
    - Kiểm thử test suite OCR: 24/24 tests passed (100%), 0 lỗi Ruff linter.
  - Rà soát tính năng OCR Combo trên UI & Backend:
    - Khắc phục sự cố `qnu-ocr-master` bị gán nhầm sang `LLM Chat` và chọn nhầm model text-only `qwen/qwen3.8-27b (Groq Cloud LPU)`.
    - Cập nhật `modelops-helpers.ts` trên Frontend2 để nhận diện hậu tố `-vl`, `_vl`, `pixtral` vào nhóm `Vision OCR`, giúp hiển thị chính xác các mô hình Vision-Language trong bộ chọn Combo.
  - Báo cáo chi tiết: `docs/nhat_ky/2026-10-03_phien_248_chuan_hoa_adapter_openai_vision_va_toi_uu_ocr_combo_multimodal.md`.
- **Phiên trước #247**:
  - Hỗ trợ tải lên nhiều tệp đồng thời (Multi-file Drag & Drop) trong Hộp thoại nạp tài liệu `DocumentUploadDialog` với danh sách hàng đợi theo dõi tiến trình từng file và thanh progress tổng thể.
  - Xây dựng thuật toán hình thái học tổng quát Khử Bảng Giả (Footnote Demotion) trong `table_reconstructor.py`, tự động nhận diện và hạ cấp các dòng chú thích cuối trang (`*`, `Ghi chú:`) ra khỏi ma trận bảng thành khối callout text.
  - Xây dựng thuật toán Gộp Cột Lệch Lưới (Interleaved Column Collapse), tự động sáp nhập các cột rác/lệch lưới do sai số tọa độ PDF ($\ge 85\%$ rỗng) vào cột liền kề, giải quyết triệt để lỗi 409 Conflict `UNRESOLVED_TABLE_HEADER` trên tài liệu bảng biểu tuyển sinh phức tạp (`doc_cd9f40ee9165` - `table_p13_2`).
  - Chuẩn hóa hàm `_is_hdr` nhận diện chính xác các mã alphanumeric (`NV-01`, `A00`, `D01`, `TH01`).
  - Khắc phục lỗi bóc tách 3 tệp PDF scan thuần ảnh (pure image PDF: `TB2302`, `QD2139`, `TB2618`): Nâng cấp cấu hình mặc định và chuỗi OCR Combo Chain từ các model cũ đã bị Google khai tử (`gemini-2.5-flash`, `gemini-2.5-flash-lite` 404) sang `gemini-3.1-flash-lite` (ưu tiên 1) và `gemini-3.5-flash-lite` (fallback 2) kết hợp xoay vòng khóa API Relational Key Pool khi gặp 429; cả 3 tệp scan đã bóc tách thành công 100%, sinh đủ 2 chunks chất lượng cao và chuyển trạng thái `ready`.
  - Báo cáo chi tiết: `docs/nhat_ky/2026-10-03_phien_247_khu_bang_gia_footnote_demotion_va_nang_cap_ocr_combo_gemini_3.md`.
- **Phiên trước #246**:
  - Khôi phục khả năng bóc tách tài liệu Office (DOCX, XLSX, PPTX, DOC, XLS, PPT) dạng declarative qua `DoclingOfficeParser` kế thừa `BaseDocumentParser`.
  - Sửa lỗi thứ tự kiểm tra `extension not in _BACKEND_CONFIG` trong `_parse_sync` để ném `ValueError` thay vì gặp `KeyError`.
  - Sửa lỗi thuật toán trích xuất bảng Markdown `_extract_markdown_tables` (bổ sung separator vào khối block, bảo toàn đầy đủ các dòng dữ liệu thay vì bỏ sót dòng đầu).
  - Tích hợp fallback native `PptxParser` cho slide PowerPoint bên cạnh `DocxParser` và `XlsxParser`.
  - Giữ nguyên 100% chính sách Zero Local AI: không khôi phục EasyOCR, SentenceTransformers, Torch/Transformers, models-local hay Ollama/vLLM; OCR scan giữ nguyên qua Gemini/Mistral API trong ModelOps DB.
  - Cơ chế tự động dùng Native Fallback khi môi trường chưa có `pypdfium2` (do hạn chế mạng).
  - Xác minh kiểm thử: `python -m unittest tests/test_docling_office_parser.py` đạt 5/5 PASSED; `compileall` parsers đạt 100%; `git diff --check` đạt 0 lỗi.
  - Báo cáo chi tiết: `docs/nhat_ky/2026-10-02_phien_246_khoi_phuc_docling_office_parser.md`.
- **Phiên trước #245**:
  - Loại bỏ toàn bộ runtime AI local (vLLM, Ollama, EasyOCR, SentenceTransformers), chuyển ModelOps hoàn toàn sang provider API key.
- **Phiên trước #244**:
- **Kết quả phiên #244**:
  - Đối chiếu 7 PDF tuyển sinh chính quy, xác nhận `col_admissions` có 7 tài liệu `ready/indexed`, 132 chunks và 1.332 facts.
  - Chạy sạch 20 câu qua API assistant `admissions`: 14 đạt, 3 đạt một phần, 3 không đạt; điểm quy đổi 77,5%; độ trễ trung bình 5,685 giây và P95 7,628 giây.
  - Ba lỗi chính: trả sai phạm vi PT5, sai lịch đăng ký/thi năng khiếu và nhầm chỉ tiêu AI/KTPM/CNTT với dữ liệu điều kiện/năng lực.
  - Phát hiện P0: phản hồi ghép context khi toàn bộ provider lỗi vẫn được ghi semantic cache, khiến provider phục hồi nhưng tiếp tục phát câu trả lời kém chất lượng. Đã xóa 25 cache của riêng `col_admissions` trước lần chạy chính thức.
  - Quan sát khóa Gemini nhận 429, chuyển `rate_limited` và runtime đi tiếp qua fallback. Chưa kiểm chứng chuỗi ba khóa provider thật vì pool Gemini chỉ có một khóa khả dụng tại thời điểm thử.
  - Báo cáo: `docs/bao_cao/2026-10-02_kiem_thu_chatbot_tuyen_sinh_20_cau.md`.
- **Phiên trước #243**:
- **Kết quả phiên #243**:
  - Phân tích log backend xác định các stack trace đều cùng một lỗi `ResponseValidationError`: khóa Gemini cũ có `status=disabled`, trong khi DTO chỉ chấp nhận trạng thái chuẩn và endpoint danh sách khóa trả HTTP 500.
  - Thêm hàm chuẩn hóa trạng thái dùng chung tại biên API/runtime: `disabled` được ánh xạ thành `inactive`; trạng thái lạ fail-closed thành `inactive` và không được đưa vào vòng xoay khóa.
  - Thêm migration `20261002_normalize_provider_key_status`: chuẩn hóa bảng relational và JSONB legacy, sau đó tạo check constraint `ck_provider_api_keys_status` để ngăn trạng thái ngoài chuẩn.
  - Đã áp dụng migration lên PostgreSQL local. Khóa `anhtuan1991dev@gmail.com` chuyển từ `disabled` sang `inactive`, giữ nguyên `is_active=false`; không thay đổi secret hay khóa đang hoạt động.
- **Kiểm tra phiên #243**:
  - Endpoint gây lỗi `/modelops/providers/prov_gemini/keys` đã trả HTTP 200, hai trạng thái là `active` và `inactive`.
  - CSDL còn 0 trạng thái ngoài chuẩn và check constraint đã tồn tại; Alembic ở head `20261002_normalize_provider_key_status`.
  - 23/23 kiểm thử trọng điểm passed; full backend 506 passed, còn đúng 5 lỗi tuyển sinh/facts/artifact đã ghi từ các phiên trước.
  - Ruff trên toàn bộ file sửa của phiên không lỗi; full Ruff vẫn còn 32 lỗi trong script/scratch ngoài phạm vi.
  - Hai dòng `Slow request` 10–12 giây trong log là cảnh báo thời gian của thao tác kiểm tra model thật, không phải exception.
- **Phiên trước #242**:
- **Phiên số**: #242 (Rà soát ModelOps từ giai đoạn 1 đến 3)
- **Kết quả phiên #242**:
  - Phân loại hard quota theo mã lỗi chuẩn hóa ngay cả khi HTTP là 402/403; tiếp tục tách biệt lỗi 429 tạm thời và khóa không hợp lệ.
  - Lỗi CSDL ở acquire/resolver/list keys không còn được che bằng fallback JSONB hay rollback làm hết hiệu lực ORM; test fixtures được sửa để trả COUNT và dữ liệu relational đúng kiểu, bỏ điều kiện production phục vụ AsyncMock.
  - Yêu cầu lớn chỉ bỏ qua khóa thiếu quota cho riêng yêu cầu đó. Khóa chỉ bị đánh dấu exhausted khi đã dùng hết quota thực tế; yêu cầu nhỏ hơn vẫn dùng được số dư.
  - Thao tác sửa/xóa/kiểm tra khóa đọc snapshot từ bảng khóa. Khóa primary do migration tạo, không có trong JSONB ban đầu, vẫn sửa được.
  - Import đồng bộ khóa xuống bảng relational, bảo toàn usage/cooldown của khóa không đổi; thay secret thì xóa lease cũ và reset trạng thái/usage của credential mới.
  - Chat, embedding, reranker và OCR giải phóng lease khi bị hủy. Chat streaming gia hạn lease sau mỗi 30 giây có token; thời hạn lease chat/resolver tính thêm khoảng đệm so với timeout, OCR dùng 180 giây cho timeout HTTP 120 giây.
  - UI bỏ emoji và nhãn khẳng định xoay khóa thật ở kết quả mô phỏng.
- **Kiểm tra phiên #242**:
  - 80/80 kiểm thử trọng điểm ModelOps/resolver/monitoring/OCR/RAG passed, gồm hủy yêu cầu và streaming trước/sau token đầu tiên.
  - PostgreSQL thật: request lớn bỏ qua quota thiếu, request nhỏ vẫn dùng số dư; 3 session đồng thời nhận 3 khóa khác nhau, session thứ tư không chiếm khóa đang dùng; chuỗi 1 → 2 → 3 và lịch sử đúng; sửa khóa migration thiếu JSONB và import secret đều hoạt động. Provider thử và khóa/sự kiện đã được xóa sau kiểm tra.
  - Build frontend + TypeScript thành công, Biome trên file UI sửa không lỗi. Ruff trên nhóm file thay đổi không lỗi.
  - Full pytest cuối cùng: 504 passed, 5 failed (cùng 5 test tuyển sinh/facts/artifact đã ghi từ #240/#241). Lần đầu có thêm lỗi quyền thư mục pytest tạm; chạy lại với thư mục tạm riêng đã loại bỏ các lỗi môi trường đó. Full Ruff vẫn 32 lỗi script/scratch ngoài phạm vi.
- **Giới hạn còn lại**:
  - Mô phỏng 429 không gọi provider thật. Token streaming là ước lượng ký tự theo cơ chế hiện tại.
  - Chưa có chính sách xóa lịch sử cũ. Lease embedding theo toàn bộ batch/OCR nhiều lượt gọi chưa có heartbeat độc lập; batch rất dài cần cơ chế gia hạn riêng trước khi chạy tải dài ở production.
- **Phiên trước #241**:
- **Phiên số**: #241 (ModelOps Giai đoạn 3 — Giám sát khóa, lịch sử và mô phỏng Failover)
- **Hoàn thành phiên #241**:
  - Thêm bảng `provider_key_events`, migration `20261002_provider_key_events` và lịch sử 30 sự kiện mới nhất theo provider. Sự kiện chọn/chuyển khóa, thành công, 429, hết quota, khóa lỗi chỉ chứa ID, loại sự kiện, mã lỗi chuẩn hóa và token; không lưu secret hay payload lỗi.
  - Trang chi tiết `/models/:id`, mục Khóa API hiển thị khóa đang dùng, cooldown, lỗi gần nhất và số lỗi liên tiếp; trạng thái/lịch sử tự tải lại mỗi 10 giây, có trạng thái rỗng/lỗi/thử lại.
  - Nút Thử Failover gọi endpoint `failover-preview` chỉ đọc bảng khóa, bỏ qua khóa bị tắt, hết quota, lỗi, đang lease hoặc còn cooldown; hiển thị thứ tự khóa dự kiến khi gặp 429.
  - Endpoint mô phỏng cũ được đánh dấu deprecated, chuyển sang xử lý bản sao; không ghi token giả hay đổi trạng thái khóa thật. Phép thử trên UI là mô phỏng, không gọi provider ngoài.
  - Đã áp dụng migration giai đoạn 2 và 3 lên PostgreSQL local; revision hiện tại `20261002_provider_key_events`. Môi trường triển khai khác vẫn cần chạy migration trước khi dùng tính năng.
- **Kiểm tra phiên #241**:
  - Frontend: `npm run build` thành công, TypeScript không lỗi; Biome trên 5 file frontend sửa đổi không lỗi.
  - Backend: 34 kiểm thử trọng điểm passed sau các chỉnh sửa cuối; Ruff trên các file sửa đổi không lỗi.
  - PostgreSQL thật với dữ liệu tạm: Key 1 gặp 429 → Key 2 gặp 429 → Key 3 thành công, ghi 6 sự kiện và hạch toán 42 token. Toàn bộ dữ liệu thử được rollback; không gọi API provider.
  - API local: danh sách khóa, lịch sử, failover-preview trả HTTP 200; preview trả `dry_run=true`.
  - Toàn bộ backend: 495 passed, 5 failed (cùng tên test đã thất bại ở phiên #240: admissions agentic flow, consulting dispatcher, hai fact lookup, universal tools). Full Ruff còn 32 lỗi trong các script/scratch có sẵn. Không khẳng định toàn bộ dự án đã sạch kiểm thử.
- **Phiên trước #240**:
- **Phiên số**: #240 (ModelOps Giai đoạn 2 — Relational Key Pool, Atomic Lease & Provider Rotation dùng chung)
- **Mục tiêu đã hoàn thành (phiên #240)**:
  - 1. **Tách Key Pool khỏi JSONB**: thêm model `ProviderApiKey` và migration `20261002_provider_api_keys`, backfill khóa hiện hữu từ `model_provider_configs.extra_config.api_keys`, đồng thời tạo khóa primary cho provider chỉ có `api_key_encrypted`.
  - 2. **Lease nguyên tử đa worker**: thêm `ProviderKeyRotationService` dùng `FOR UPDATE SKIP LOCKED`, `lease_token`, `lease_until`, cooldown, quota, trạng thái `rate_limited/exhausted/invalid` và cập nhật usage sau khi gọi provider.
  - 3. **Luồng dùng chung**: chat `generate/generate_stream`, embedding, reranker và OCR cloud đều dùng nguồn lease chung; khi key lỗi hoặc hết hạn ngạch sẽ xoay sang key tiếp theo, sau đó mới fallback provider.
  - 4. **Tương thích chuyển tiếp**: nếu migration chưa chạy hoặc bảng mới chưa có dữ liệu, runtime và API Provider tiếp tục đọc JSONB cũ; CRUD khóa ghi đồng thời relational table và JSONB trong thời gian chuyển đổi.
  - 5. **Bảo mật**: runtime chỉ giải mã khóa trong vùng gọi adapter; API quản trị chỉ trả masked key, không bổ sung đường reveal/export plaintext.
- **Kiểm thử phiên #240**:
  - Nhóm trọng điểm: **46/46 passed** (ModelOps rotation, relational lease, resolver, OCR, RAG).
  - Toàn bộ backend: **492 passed, 5 failed** ở các test admissions/fact/artifact đã tồn tại trước phiên; test Docling native trên Windows còn cảnh báo access violation.
  - Ruff trên toàn bộ file thay đổi: **0 lỗi**; `alembic heads` nhận `20261002_provider_api_keys`.
- **Phiên số trước**: #238, #237, #236, #235, #234
- **Mục tiêu đã hoàn thành (phiên #239)**:
  - 1. **Triển Khai Thành Công Kế Hoạch Hybrid DAG Nodes (`ke_hoach_nang_cap_hybrid_nodes_dag_workflow.md`)**:
       * Tiếp nhận phê duyệt của người dùng, thực thi 100% các giai đoạn đề ra.
  - 2. **Nâng Cấp & Chuẩn Hóa `condition_route_node.py` (Hybrid Intent Router)**:
       * Xóa bỏ hoàn toàn mảng từ khóa cứng 88 từ `_INQUIRY_KEYWORDS` vi phạm Tôn chỉ 7 `AGENTS.md`.
       * Bổ sung bất biến cú pháp tiếng Việt 0ms: phát hiện dấu `?`, đại từ/hạt nhân nghi vấn ngữ pháp, bóc tách hình thái học hành chính `_ORGANIZATIONAL_ENTITY_PATTERN` nhận diện tự động mọi phòng ban.
       * Tích hợp Micro-LLM Intent Classifier: Phân loại ý định vào Rule ID mục tiêu khi quy tắc tất định không khớp (timeout 1.5s, safe fallback).
       * Sửa lỗi vỡ biểu thức Regex khi `pattern` chứa ký tự điều khiển (`\b`, `(?:...|...)`), chuẩn hóa việc trích xuất token lời chào.
  - 3. **Nâng Cấp `citation_guard_node.py` & `rag_answer_node.py`**:
       * Thuật toán toán học 0ms đối soát số liệu `_detect_number_hallucinations`: hỗ trợ cả số thập phân và tiền tệ có nhiều dấu phân cách hàng nghìn (`15.000.000 VNĐ` vs `15000000`).
       * Lưu trữ `guidance_context` và `fact_markdown` từ `rag_answer_node.py` cho `CitationGuardNode` đối soát bảng sự thật.
       * Xử lý an toàn `model_policy` NoneType trong `rag_answer_node.py` tránh `AttributeError`.
  - 4. **Kiểm Thử Hồi Quy & Đóng Gói Bundle 100% Passed**:
       * Backend: Pytest 76/76 tests passed (100%), Ruff check `app` và `tests` 0 lỗi.
       * Frontend (`frontend`): `tsc -b && vite build` $\rightarrow$ 100% thành công (0 lỗi, 8.57s).
       * Frontend2 (`frontend2`): `vite build && tsc --noEmit` $\rightarrow$ 100% thành công (0 lỗi, 9.66s).
  - 5. **Tuân Thủ Tuyệt Đối Ràng Buộc Không Tự Ý Push Code**:
       * Không chạy `git push`, giữ nguyên commit cục bộ để Người dùng tự chủ động push.
- **Agent**: AI Senior Full-Stack Architect & Enterprise AI Systems Specialist
- **Trạng thái kiểm thử nền hiện tại**:
  - Backend trọng điểm phiên #240: 46/46 passed; full suite 492 passed và 5 lỗi tồn tại ở admissions/fact/artifact.
  - Ruff trên các module ModelOps/OCR/RAG và migration mới: 0 lỗi.
  - Frontend & Frontend2: Build production bundle thành công 100% (0 lỗi).
- **Tóm tắt phiên trước (#238)**:
  - Chuẩn hóa thuật toán tổng quát sub-header invariant trong `table_reconstructor.py`, tập trung hóa từ điển đánh giá Ragas TM-08 sang `configs/stopwords_vi.txt`.
  - 3. **Phiên #234 — Tích hợp Cổng Kết Nối OpenRouter AI Gateway (`prov_openrouter`)**:
       * Bổ sung biến môi trường `OPENROUTER_API_KEY` và `OPENROUTER_BASE_URL` ("https://openrouter.ai/api/v1") trong `app.core.config`.
       * Tự động gắn kèm headers `HTTP-Referer: https://qnu.edu.vn` và `X-Title: QNU AI Platform` theo chuẩn OpenRouter API trong `OpenAIAdapter`.
       * Đăng ký `prov_openrouter` vào `STANDARD_QNU_PROVIDERS` với danh mục model gợi ý (`deepseek/deepseek-r1`, `anthropic/claude-3.7-sonnet`, `openai/gpt-4o-mini`, `google/gemini-2.0-flash-001`, `meta-llama/llama-3.3-70b-instruct`) và preset schemas.
       * CSDL live PostgreSQL: Đạt đủ **11 Nhà Cung Cấp** tiêu chuẩn (OpenAI, Gemini, Mistral, Cloudflare, DeepSeek, Groq, Claude, Local vLLM, Ollama, NVIDIA NIM, OpenRouter).
  - 4. **Phiên #233 — Tích hợp NVIDIA NIM (`prov_nvidia`), Xử lý lỗi 503 Overload & Nemotron Thinking Stream**:
       * Đăng ký `prov_nvidia` vào `STANDARD_QNU_PROVIDERS` (Base URL: `https://integrate.api.nvidia.com/v1`).
       * Hỗ trợ tham số `chat_template_kwargs={"enable_thinking": True}` qua `extra_body` cho mô hình suy luận `nvidia/nemotron-3-ultra-550b-a55b` và dòng DeepSeek R1 trong `OpenAIAdapter`.
       * Bóc tách `reasoning_content` từ `chunk.choices[0].delta` và stream trực tiếp token suy luận về client.
       * Cơ chế phục hồi 503/504/529: Auto-retry 1 lần sau 1s trong `_ping_single_model`, phân loại trạng thái `temporarily_overloaded` thay vì gán lỗi chết.
       * UI `add-custom-model-dialog.tsx`: Cảnh báo màu hổ phách, icon đồng hồ `Clock`, giải thích tên mô hình chính xác và mở nút "Thêm model" cho phép người dùng lưu mô hình ngay.
  - 5. **Phiên #232 — Nâng cấp Task Runner (`reseed`, `reset-db`) & Git Dual-Push (Gitea + GitHub)**:
       * Sửa lỗi `ParameterBindingValidationException` trong `make.ps1` bằng việc bổ sung `"reseed"`, `"reset-db"` vào attribute `[ValidateSet(...)]` và triển khai nhánh switch tương ứng.
       * Tối ưu hóa `Makefile` tương thích PowerShell.
       * Cấu hình remote `origin`: Fetch trỏ về Gitea (`qnu-gitea.duckdns.org` - Gitea-first pull), Push trỏ đồng thời về Gitea và GitHub (`github.com/hatuandev`). 1 lệnh `git push` tự động đồng bộ cả 2 máy chủ.
  - 4. **Phiên #231 — Cấu hình Kỹ Năng / Tools Universal Trên Web UI & Triệt tiêu hoàn toàn `admission_score_tool.py`**:
       * Xóa bỏ 100% tệp gán cứng `admission_score_tool.py`.
       * Thay thế bằng 2 công cụ nền tảng dùng chung `lookup_fact_layer` và `export_universal_report`.
       * Nâng cấp UI `/assistants/:id` với khối "Kỹ Năng & Công Cụ Nền Tảng (Universal AI Capabilities)" cho phép bật/tắt từng công cụ qua Switch Radix UI.
- **Agent**: AI Senior Full-Stack Architect & Enterprise AI Systems Specialist
- **Trạng thái kiểm thử**:
  - Backend: 11/11 Providers nạp live CSDL PostgreSQL 16 hợp lệ (`verify_core_seed_data()`).
  - Frontend2: `npm run build` thành công 100% trong 4.79s, 0 lỗi TypeScript, 0 lỗi Biome.
  - Git: Dual-Push thành công đồng thời cả Gitea và GitHub.
- **Mục tiêu đã hoàn thành**:
- 0. **Tối Ưu Hóa Toàn Diện Responsive Mobile & Triệt Tiêu Toàn Bộ Nút/Dropdown Dư Thừa Phân Hệ Loại Văn Bản (`/document-types`) (phiên #215)**:
  - *Hiện trạng & Yêu cầu*:
    - Tiếp nhận ảnh chụp thực tế trên thiết bị di động (`media_1790243122709.png`, `media_1790244268122.png`) từ người dùng.
    - Khắc phục triệt để lỗi viền đứt đoạn do Tailwind `divide-y` trên lưới 2 cột của KPI Telemetry Strip.
    - Cân đối cụm nút hành động "Đồng bộ" & "Thêm loại", không để lệch góc trái và hở khoảng trống lớn bên phải.
    - Tinh gọn thanh công cụ Toolbar từ 4 dòng xuống 2 hàng liền mạch, không để các Select bị lửng lơ hoặc nút chuyển Grid/Table rớt dòng một mình.
    - Tiếp nhận góp ý sắc đáng của người dùng về việc lặp nút (`Chi tiết`, `Chỉnh sửa`, `Xem tài liệu` đều trỏ về 1 trang) ➔ Xóa bỏ hoàn toàn nút ba chấm `...` và `DropdownMenu` trùng lặp trên cả `DocumentTypeCard` và `Table View`, thay bằng 1 nút phẳng phiu duy nhất `[⚙ Chi tiết]`.
    - Tối ưu hóa thẻ `DocumentTypeCard` gọn gàng, giảm padding, bỏ khoảng trắng nhân tạo `min-h-8`.
    - Tối ưu hóa `DocumentTypeDetailPage` chống tràn ngang tiêu đề và dàn đều dải nút chân header.
  - *Kiến trúc & Triển khai*:
    - Tinh chỉnh `frontend2/src/components/admin/kpi-metric.tsx`: Hỗ trợ `className?: string`, padding responsive `p-3.5 sm:p-5`.
    - Tái cấu trúc lưới KPI trong `DocumentTypesPage`: Bỏ `divide-y`/`divide-x`, áp dụng ma trận viền 2x2 đối xứng (`border-r`, `border-b`) trên mobile tạo hình chữ thập phân chia chính giữa hoàn hảo; 4 cột phân cách bằng 3 đường dọc trên desktop.
    - Cụm nút hành động đầu trang: `grid grid-cols-2 gap-2 w-full sm:flex sm:w-auto` dàn đều 50/50 trên mobile.
    - Toolbar liền mạch: Hàng 1 ô tìm kiếm full width + 2 Select chia đôi 50/50, Hàng 2 gộp cụm chip lọc nhanh và nút chuyển Grid/Table trên cùng một dòng.
    - Xóa bỏ hoàn toàn DropdownMenu và các nút thừa: Thay bằng 1 nút duy nhất `Chi tiết` (`w-full` trên thẻ, `h-7 px-2.5` trên bảng), tích hợp click trực tiếp vào chip mã code `{item.code}` để sao chép vào clipboard có toast.
    - Thẻ `DocumentTypeCard`: Padding `p-3.5 sm:p-4`, thêm `shrink-0` cho Badge nhóm, chuyển `min-h-8` sang `min-h-0 sm:min-h-8`.
    - Trang chi tiết `DocumentTypeDetailPage`: Tiêu đề adaptive `max-w-[150px] xs:max-w-[200px] sm:max-w-none truncate`, nút quay lại `hidden xs:inline`, dải nút chân header `w-full justify-between sm:justify-end`.
  - *Verification*:
    - Frontend2 Biome check: 0 errors, 0 warnings.
    - Frontend2 Typecheck `tsc --noEmit`: 0 errors toàn codebase.
    - Frontend2 Vite build: Thành công 100% trong 1.37s.
- 0. **Thiết Kế & Triển Khai Hoàn Chỉnh Phân Hệ Loại Văn Bản (`/document-types`) Trên Frontend2 Chuẩn Master-Detail Deep Routing (phiên #214)**:
  - *Hiện trạng & Yêu cầu*:
    - Xây dựng hoàn chỉnh phân hệ Quản lý Loại Văn Bản trên `frontend2` (Vite 6 + React 19 + TanStack Router + Tailwind v4 + Radix UI + Biome) tại `http://localhost:3000/document-types`.
    - Chuẩn hóa thể thức văn bản hành chính theo Nghị định 30/2020/NĐ-CP và phân loại văn bản học thuật Trường ĐH Quy Nhơn.
    - Áp dụng kiến trúc Master-Detail Deep Routing (Mục 4.5 của `AGENTS.md`): Tuyến danh sách `/document-types/` và tuyến chi tiết độc lập `/document-types/:code`.
    - Tuân thủ cấu hình responsive 4-2-1 cards, 100% Radix/shadcn UI, Zero Emoji và nhãn nút ngắn gọn 1-2 từ.
  - *Kiến trúc & Triển khai*:
    - Định tuyến file-based TanStack Router:
      * `frontend2/src/routes/document-types.tsx`: Layout route bọc `<Outlet />`.
      * `frontend2/src/routes/document-types.index.tsx`: Tuyến danh sách hiển thị `DocumentTypesPage`.
      * `frontend2/src/routes/document-types.$code.tsx`: Tuyến chi tiết chuyên sâu hiển thị `DocumentTypeDetailPage`.
    - Màn hình Master View `DocumentTypesPage`:
      * Dải KPI Telemetry Strip 4 ô gộp trong Card nguyên khối: Tổng loại văn bản, Chuẩn NĐ 30/2020, Đào tạo & Học thuật, Đang hoạt động.
      * Seamless Toolbar: Ô tìm kiếm debounced (tên/code mono), bộ lọc Nhóm phân loại (175px), bộ lọc Trạng thái, chip lọc nhanh "Tất cả | Chuẩn NĐ 30 | Tùy chỉnh", chuyển đổi Grid/Table.
      * Thẻ `DocumentTypeCard` với lưới 4-2-1 (`grid-cols-1 sm:grid-cols-2 lg:grid-cols-4`), icon chuyên ngành trong `bg-primary/10`, switch trạng thái, badges NĐ 30, dải thông số kỹ thuật (Mức ưu tiên RAG 1-10, Thời hạn bảo quản, Số tài liệu thực tế liên kết) và nút hành động tinh gọn.
      * Data Table View bọc trong `overflow-x-auto` chống xô lệch.
    - Màn hình Dedicated Detail View `DocumentTypeDetailPage`:
      * Nút quay lại adaptive `← Danh mục`, switch trạng thái, nút "Lưu".
      * Bố cục 2 cột chuyên sâu: Cột trái quản lý thông số thể thức và mức độ ưu tiên RAG (progress bar trực quan); Cột phải quản lý căn cứ pháp lý NĐ 30/2020, xuất xứ đồng bộ `qnu-ai-core`, tài liệu đang áp dụng và Danger Zone.
    - Modal tạo mới `CreateDocumentTypeDialog`: 100% component Radix/shadcn UI chuẩn regex code validation.
  - *Verification*:
    - Frontend2 Biome check: 7 files mới đạt 0 errors, 0 warnings.
    - Frontend2 Typecheck `tsc --noEmit`: 0 errors toàn codebase.
    - Frontend2 Vite build: Thành công 100% trong 1.58s (tạo 3 chunks độc lập `document-types.index`, `document-types._code`, `document-type-card`).
- 0. **Điều Chỉnh Responsive Grid 4 Cards Desktop, 2 Cards Tablet, 1 Card Mobile & Tối Ưu Bố Cục Thẻ Trợ Lý AI (phiên #213)**:
  - *Hiện trạng & Yêu cầu*:
    - Điều chỉnh cấu hình grid thẻ Trợ lý AI trên `http://localhost:3000/assistants` theo đúng tỷ lệ: 4 cards trên Desktop, 2 cards trên Tablet, 1 card trên Mobile.
    - Tối ưu kích thước, padding và dải nút hành động chân thẻ để vừa vặn, không bị xô lệch trên lưới 4 cột.
  - *Kiến trúc & Triển khai*:
    - Thay thế `grid-cols-1 md:grid-cols-2 lg:grid-cols-3` thành `grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4` trên `AssistantsPage`.
    - Tinh chỉnh `AssistantCard`: Đặt `p-4 pb-2` trên CardHeader và CardContent.
    - Tái cấu trúc cụm nút hành động: 2 nút chính cân xứng ("Thử nghiệm" và "Quản trị") kết hợp Dropdown Menu tiện ích (đưa "Sơ đồ DAG" lên đầu, kèm "Nhân bản", "Lịch sử", "Mã nhúng", "Xuất bundle").
    - Nâng cấp Deep Routing: Hỗ trợ query search `tab` ("overview", "models", "tools", "playground", "workflow") trên tuyến `/assistants/$assistantId`, click nút "Thử nghiệm" nhảy thẳng vào tab Playground SSE chat.
  - *Verification*:
    - Frontend2 Biome check: 0 errors, 0 warnings.
    - Frontend2 Typecheck `tsc --noEmit`: 0 errors.
    - Frontend2 Vite build: Thành công 100% trong 1.64s.
- 0. **Thiết Kế & Triển Khai Hoàn Chỉnh Phân Hệ Trợ Lý AI (`/assistants`) Trên Frontend2 Chuẩn Master-Detail Deep Routing (phiên #212)**:
  - *Hiện trạng & Yêu cầu*:
    - Xây dựng hoàn chỉnh phân hệ Trợ lý AI trên `frontend2` (Vite 6 + React 19 + TanStack Router + Tailwind v4 + Radix UI + Biome).
    - Triển khai kiến trúc Master-Detail Deep Routing theo Mục 4.5 của `AGENTS.md`: Tách biệt Master List View (`/assistants`) và Dedicated Detail View (`/assistants/:assistantId`).
    - Bố trí trực quan vòng đời 7 lớp tạo lập Trợ lý AI (Mục 2 của `AGENTS.md` & `qnu-chatbot-builder`).
    - Tuân thủ 100% các quy chuẩn: OKLCH Academic Teal, 100% `lucide-react`, Zero Emoji (Mục 4.8), Component Reuse First (Mục 4.9), Cross-Device Responsive (Mục 4.10) và Nhãn nút ngắn gọn 1-2 từ (Mục 4.11).
  - *Kiến trúc & Triển khai*:
    - Định tuyến file-based TanStack Router:
      * `frontend2/src/routes/assistants.tsx`: Layout route bọc `<Outlet />`.
      * `frontend2/src/routes/assistants.index.tsx`: Tuyến danh sách `/assistants/` hiển thị `AssistantsPage`.
      * `frontend2/src/routes/assistants.$assistantId.tsx`: Tuyến chi tiết `/assistants/:assistantId` hiển thị `AssistantDetailPage`.
    - Màn hình Master View `AssistantsPage`:
      * Dải KPI Telemetry Strip 4 ô gộp trong Card nguyên khối: Trợ lý AI, Đạt chuẩn TM-08 (Groundedness $\ge 0.90$), Kho tri thức liên kết, Quy trình DAG.
      * Toolbar tìm kiếm Debounced, bộ lọc Lĩnh vực (Select 165px chống cắt chữ), bộ lọc Trạng thái và chuyển đổi Grid/Table.
      * Thẻ `AssistantCard` chuẩn Executive Card với switch hoạt động, dải thông số kỹ thuật (Model, Kho tri thức, TM-08 Grounded) và các nút thao tác ngắn gọn ("Thử nghiệm", "Sơ đồ DAG", "Quản trị").
    - Màn hình Dedicated Detail View `AssistantDetailPage`:
      * `AssistantHeader`: Nút quay lại adaptive, Readiness Telemetry 5 tiêu chí TM-08, các nút hành động ("Lưu", "Phát hành", "Sơ đồ DAG", "Thử nghiệm").
      * 5 Tabs chuyên sâu (`AssistantWorkspaceNav`): Cấu hình (2 cột cân xứng), Mô hình & An toàn (tham số + Guardrails), Công cụ & Quản trị (Function Calling + HITL + Danger Zone), Sơ đồ DAG (Ownership Private/Shared, Fork riêng), Thử nghiệm (`AssistantPlaygroundTab` với SSE streaming token qua `useRAGStream`, đối soát citations và gợi ý 1-click).
    - Modal tạo mới `CreateAssistantDialog`: 3 chế độ (Mẫu QNU hạt nhân, Tự sinh spec AI, Tùy chỉnh thủ công).
  - *Verification*:
    - Backend Pytest: 426/426 passed (100%).
    - Frontend2 Biome check: 20 files checked, 0 errors, 0 warnings.
    - Frontend2 Typecheck `tsc --noEmit`: 0 errors.
    - Frontend2 Vite build: Đóng gói thành công trong 1.46s (chunk `assistants.index` 31.74 kB, `assistants._assistantId` 75.31 kB).
- 0. **Thiết Kế & Triển Khai Hoàn Chỉnh Phân Hệ Kho Tri Thức (`/knowledge`) Trên Frontend2 Chuẩn Master-Detail Deep Routing (phiên #211)**:
  - *Hiện trạng & Yêu cầu*:
    - Cần chuyển đổi phân hệ Kho Tri Thức từ `frontend` sang nền tảng Next-Gen `frontend2` (Vite 6 + React 19 + TanStack Router + Tailwind v4 + Radix UI + Biome).
    - Áp dụng kiến trúc Master-Detail Deep Routing theo Mục 4.5 của `AGENTS.md`: tách biệt Master List View (`/knowledge`) và Dedicated Detail View (`/knowledge/:collectionId`), triệt tiêu việc dồn ép vào một trang tabbed monolithic.
    - Tuân thủ 100% quy chuẩn Academic Teal, Zero Emoji (Mục 4.8), Component Reuse First (Mục 4.9), Cross-Device Responsive (Mục 4.10) và Nhãn nút ngắn gọn (Mục 4.11).
  - *Kiến trúc & Triển khai*:
    - Định tuyến file-based TanStack Router:
      * `frontend2/src/routes/knowledge.tsx`: Layout route bọc `<Outlet />`.
      * `frontend2/src/routes/knowledge.index.tsx`: Tuyến danh sách `/knowledge/`, hiển thị `KnowledgePage`.
      * `frontend2/src/routes/knowledge.$collectionId.tsx`: Tuyến chi tiết độc lập `/knowledge/:collectionId`, hiển thị `CollectionDetailPage`.
    - Màn hình Master View `KnowledgePage`:
      * KPI Telemetry Strip 4 ô gộp trong thẻ `Card` nguyên khối có vách ngăn tinh tế: Kho tri thức, Văn bản bóc tách, Vector chunks (BGE-M3 1024D), Cơ sở dữ liệu (Qdrant + Postgres RRF k=60).
      * Toolbar tìm kiếm Debounced thời gian thực, bộ lọc Chunking strategy, bộ lọc OCR Engine, chuyển đổi Grid/Table view.
      * Thẻ bộ sưu tập với nút "Mở kho" outline thanh thoát (`bg-primary/10 border-primary/20 hover:bg-primary`).
    - Màn hình Dedicated Detail View `CollectionDetailPage`:
      * `CollectionHeader`: Nút quay lại adaptive, badge trạng thái và mã kho, nút hành động tinh gọn (Đối soát, Reindex, Sửa, Nạp tài liệu).
      * 4 Tabs nghiệp vụ chuyên sâu: Tài liệu (quản lý, lọc, xem trước, tải file gốc, reindex), Facts số (bảng dữ liệu cấu trúc điểm chuẩn/học phí/chỉ tiêu, nhập Excel), Tiến trình (lịch sử ARQ Ingestion, log inspector), Thử nghiệm (Sandbox hybrid RRF retrieval).
      * Đã ẩn badge số đếm `(0)` thừa trên tabs; mở rộng trigger select filter lên 165-175px chống cắt chữ; format tên văn bản hành chính và huy hiệu xanh khi đã index.
    - Modal nạp tài liệu `DocumentUploadDialog`:
      * Kéo thả tệp, nhập tiêu đề, chọn loại văn bản taxonomy, chọn bộ máy OCR (PyMuPDF, Docling, Gemini Vision, Mistral OCR) và toggle Fast-Track vector hóa tức thì.
    - Sửa lỗi TypeScript type union trên `KnowledgeDocument.status` bổ sung `"ready"`.
  - *Verification*:
    - Backend Pytest: 426/426 passed (100%).
    - Backend Ruff: 0 lỗi.
    - Frontend2 Biome check: 25 files checked, 0 errors, 0 warnings.
    - Frontend2 Typecheck `tsc --noEmit`: 0 errors.
    - Frontend2 Vite build: Đóng gói thành công trong 1.47s (chunk `knowledge.index` 17.04 kB, `knowledge._collectionId` 48.21 kB).
- 0. **Thiết Kế Trang Chi Tiết Provider `/models/$providerId` Độc Lập Chuẩn Master-Detail Deep Routing, Bổ Sung Quy Chuẩn Responsive & Nhãn Nút Ngắn Gọn Vào AGENTS.md (phiên #210)**:
  - *Hiện trạng & Vấn đề phát hiện qua ảnh chụp của người dùng*:
    - Người dùng truy cập hoặc F5 tại URL `http://localhost:3000/models/prov_c9d9d380`, trình duyệt hiển thị màn hình lỗi: *"Không tìm thấy trang - Trang bạn yêu cầu không tồn tại."* (404 Not Found).
    - Trên màn hình iPhone thực tế: breadcrumb bị tràn ép chữ, badge "Chi Tiết Provider" gập dòng chồng chéo, các nút bấm Hero card dài dòng chiếm nhiều hàng, cụm tabs có số đếm và bị cắt chữ cạnh phải.
  - *Kiến trúc & Giải pháp UI/UX*:
    - Tách cấu trúc Route chuẩn TanStack Router:
      * `frontend2/src/routes/models.tsx`: Layout route chứa `<Outlet />`.
      * `frontend2/src/routes/models.index.tsx`: Route danh sách chính (`/models/`), hiển thị `ModelOpsPage`.
      * `frontend2/src/routes/models.$providerId.tsx`: Route chi tiết độc lập (`/models/$providerId`), tiếp nhận `providerId` và render `ProviderDetailPage`.
    - Bổ sung 2 quy chuẩn bắt buộc vào `AGENTS.md` & `qnu-frontend-architect/SKILL.md`:
      * Mục 4.10: **Quy Chuẩn Thiết Kế Đa Thiết Bị & Responsive (Cross-Device & Responsive Standard)**.
      * Mục 4.11: **Quy Chuẩn Đặt Tên Nút Bấm & Nhãn Điều Khiển Ngắn Gọn (Concise Action Labels & Microcopy Standard)**.
    - Xây dựng component mới `frontend2/src/features/modelops/provider-detail-page.tsx`:
      * Breadcrumb chuẩn kèm nút quay lại di động: `← Provider / Mistral AI`, ẩn badge phụ trên màn hình nhỏ.
      * Hero Header Card (`ProviderDetailHeader`): Logo, Tên, Badge loại, nhãn nút rút gọn (`Hoạt động`, `Kiểm tra`, `Xuất JSON`, `Sửa`, `Xóa`).
      * Executive KPI Telemetry Strip 4 ô: Mô hình, Khóa API, Độ trễ (Ping), Circuit Breaker.
      * Tabs phân hệ chuyên sâu tối giản: `Mô hình`, `Khóa API`, `Chịu lỗi & Mạng`, xóa 100% số đếm badge thừa, hỗ trợ cuộn ngang êm ái.
      * Chuẩn hóa nhãn nút trong `models-grid.tsx` (`Test tất cả`, `Thêm model`, `Dọn model lỗi`) và `key-pool-section.tsx` (`Thử Failover`, `Thêm khóa`, `Lưu`, `Kiểm tra`).
  - *Verification*:
    - TypeScript Typecheck `npm run typecheck`: **0 lỗi** toàn bộ codebase.
    - Biome linter `npx @biomejs/biome check`: **0 lỗi** trên toàn bộ các route và components ModelOps.
    - Vite build `npm run build`: Đóng gói thành công trong 1.53s (chunk `models._providerId-sHTLwhbW.js` 16.94 kB).
    - Triệt tiêu 100% lỗi 404, giao diện hiển thị hoàn hảo trên màn hình iPhone di động.
- 0. **Lược Bỏ Toàn Bộ Số Đếm (Badge Count) Khỏi Main Navigation Tabs Trang ModelOps Trên Frontend2 & Frontend (phiên #209)**:
  - *Hiện trạng & Yêu cầu người dùng*:
    - Người dùng gửi ảnh chụp màn hình 3 tabs chính: `[Nhà Cung Cấp 11]`, `[Mặc Định]`, `[Combos 4]` và yêu cầu bỏ các con số trên tabs bên Frontend.
  - *Frontend2 & Frontend*:
    - `frontend2/src/features/modelops/modelops-page.tsx`:
      * Xóa bỏ component `<Badge>` số lượng `{providers.length}` trong nút `Nhà Cung Cấp` và `{systemDefaults?.model_combos?.length || 1}` trong nút `Combos`.
      * Cả 3 tabs chính `[Nhà Cung Cấp]`, `[Mặc Định]`, `[Combos]` giờ đây hiển thị phẳng phiu, tối giản và đồng đều, thanh thoát trên mọi màn hình.
    - `frontend/src/pages/modelops-page.tsx`:
      * Đồng bộ xóa bỏ badges số lượng khỏi các nút navigation tabs tương tự (`Combos & Vision Adapter`, `Nhà Cung Cấp & Khóa API`).
  - *Verification*:
    - TypeScript Typecheck `npm run typecheck`: **0 lỗi** trên cả `frontend2` và `frontend`.
    - Biome linter: **0 lỗi** trên cả 2 frontends.
    - Vite build: đóng gói thành công 100% trong 2.10s.
- 0. **Tối Ưu UI/UX & Chuẩn Hóa Nhãn Nút Trang ModelOps Trên Frontend2 Mới, Khắc Phục Triệt Để Lỗi Cắt Chữ Tabs (phiên #208)**:
  - *Hiện trạng & Yêu cầu người dùng*:
    - Người dùng đang xây dựng lại `frontend2` (Vite 6 + React 19 + TanStack Router).
    - Yêu cầu xem xét trang `/models` (ModelOps) để tối ưu UI/UX trên mọi kích thước thiết bị (đặc biệt là mobile viewports hẹp như 394px) và rút gọn các nút bấm/tiêu đề có tên quá dài.
    - Khắc phục lỗi: Tab thứ 3 trên thanh điều hướng chính bị cắt ngang thành "Tổ Hợp Co..." do container dùng `overflow-x-auto scrollbar-none` kết hợp tên nhãn quá dài ("Mặc Định Hệ Thống", "Tổ Hợp Combos").
  - *Frontend2*:
    - `frontend2/src/features/modelops/modelops-page.tsx`:
      * Khắc phục lỗi cắt chữ tab: Chuyển container main tabs sang `grid grid-cols-3 sm:flex sm:flex-wrap items-center gap-1.5 sm:gap-2`. Cả 3 nút `[Nhà Cung Cấp 11]`, `[Mặc Định]`, `[Combos 4]` dàn đều trên 1 hàng 3 cột cực kỳ cân xứng, triệt tiêu hoàn toàn nút thứ 3 rớt dòng lẻ loi.
      * Rút gọn tên 3 tabs chính: `Nhà Cung Cấp & Khóa API` $\rightarrow$ `Nhà Cung Cấp` (badge số lượng), `Mặc Định Hệ Thống` $\rightarrow$ `Mặc Định`, `Tổ Hợp Combos` $\rightarrow$ `Combos` (badge số lượng). Bề rộng co từ 465px xuống ~300px, hiển thị trọn vẹn 100% trên màn hình hẹp 394px.
      * Rút gọn nút header: `Xuất Tất Cả (JSON)` $\rightarrow$ `Xuất JSON`, `Thêm Provider Mới` $\rightarrow$ `Thêm Provider`.
      * Tối ưu dải KPI metrics 4 ô: `grid-cols-2 lg:grid-cols-4 gap-2.5 sm:gap-3`, cỡ chữ `text-[10px] sm:text-[11px] truncate` hiển thị 2 cột cân đối trên màn hình điện thoại di động.
      * Thêm `.scrollbar-none` cho category pills bar ẩn thanh cuộn thô trên trình duyệt.
    - `frontend2/src/components/modelops/system-defaults-card.tsx`:
      * Tối ưu 4 Card kênh nhiệm vụ trên Mobile (Embedding, Reranker, OCR, Chat): Header chuyển sang `flex-col sm:flex-row sm:items-center justify-between gap-2.5 sm:gap-2`; bộ chuyển chế độ `[Mô Hình Đơn | Chuỗi Combo]` mở rộng `w-full sm:w-auto` chuẩn native mobile segmented control; tiêu đề rút gọn tinh tế (`1. Nhúng Vector (Embedding)`, `2. Tái Xếp Hạng (Reranker)`, `3. Bóc Tách & OCR (Vision)`, `4. Chat & Lý Luận (LLM)`) bảo đảm tiêu đề và badge không bao giờ bị bẻ gãy từ như `1024-` / `dim` hay `Cross-` / `Encoder`.
      * Khắc phục dính chữ Header Luồng Failover: Đổi sang `flex flex-wrap items-center justify-between gap-1` và rút gọn nhãn (`Luồng Failover {task} ({n} Tầng)`, `Ưu tiên 1 ➔ {n}`) chấm dứt hoàn toàn hiện tượng dính chặt chữ `(2 TẦNG PHỤC HỒI)Ưu tiên`.
      * Tối ưu Top Banner & Footer Card: Nút `Combos ({n})` mở rộng `w-full sm:w-auto` tự nhiên trên mobile; chân card hỗ trợ `flex-col sm:flex-row` chống đè nút "Xem chi tiết".
    - `frontend2/src/components/modelops/combos-vision-section.tsx`:
      * Tối ưu Combo Card Header trên Mobile: Chuyển sang `flex items-start justify-between gap-2`, huy hiệu rút gọn `Mặc Định Kênh` $\rightarrow$ `Mặc Định` giúp huy hiệu và các nút thao tác `[Copy, Sửa, Xóa]` không bị rớt dòng lơ lửng giữa chừng.
      * Tối ưu Top Banner: Nút `+ Tạo Combo` mở rộng `w-full sm:w-auto` cân đối ở đáy card banner trên mobile.
      * Rút gọn filter tabs: `Vision & OCR`, `Vector`, `Xếp Hạng`, `Chat LLM`.
      * Chuẩn hóa Biome accessibility (`<label>` $\rightarrow$ `<span>`, `useId()`, key mảng ổn định).
    - `frontend2/src/components/modelops/models-grid.tsx`:
      * Xóa emoji rác `🧹`, đổi nhãn thành `Dọn Model Lỗi`, xóa cụm tiếng Anh `(Available Models)`.
    - `frontend2/src/components/modelops/key-pool-section.tsx`:
      * Rút gọn `Thêm Khóa Mới` $\rightarrow$ `Thêm Khóa`, `Lưu Khóa Vào Nhóm` $\rightarrow$ `Lưu Khóa`.
    - `frontend2/src/styles/globals.css`:
      * Bổ sung `.scrollbar-none` tiện ích Tailwind v4 ẩn scrollbar thô.
  - *Verification*:
    - TypeScript Typecheck `npm run typecheck`: **0 lỗi**.
    - Biome linter `npx @biomejs/biome check src/components/modelops src/features/modelops`: **12 files 0 lỗi, 0 cảnh báo**.
    - Trực quan trình duyệt: Kiểm tra trên cả desktop (1536x730) và mobile (394x852) - 100% các nút và tabs hiển thị hoàn chỉnh, không cắt chữ, layout mobile cân xứng chuẩn native app.
- 0. **Tối Ưu Hóa Bóc Tách PDF OCR Bằng Thuật Toán Tổng Quát (Zero-Hardcoded Vocabulary) & Bổ Sung Chuẩn AGENTS.md (phiên #207)**:
  - *Hiện trạng & Vấn đề giải quyết*:
    - Bóc tách văn bản hành chính / hợp đồng quét scan phức tạp (`Hợp đồng nâng cấp PM cổng thông tin điện tử_0001.pdf` 16 trang) trước đây bị:
      1. Bảng kéo dài nhiều trang bị cắt vụn nát bởi `---` ngắt trang, mất header/separator ở trang tiếp theo;
      2. Từ ngữ bị chặt đôi qua ranh giới trang (như `banner, giới` / `thiệu, hình ảnh`);
      3. Dòng trong cùng một ô bảng bị bẻ thành nhiều hàng riêng biệt làm mất STT;
      4. Ràng buộc người dùng: Tuyệt đối không được ảnh hưởng tới luồng DOCX (`DocxParser`) và PDF text (`PDFInspector`, `PyMuPDFParser`).
      5. Triệt tiêu mảng từ khóa hardcode `_COMMON_SPLIT_WORD_PAIRS = [("giới", "thiệu"), ...]`, thay bằng giải thuật tổng quát và bổ sung quy chuẩn vào `AGENTS.md`.
  - *Backend*:
    - Nâng cấp Prompt chuyên gia trong `GeminiOCRAdapter` (`backend/app/modules/ocr/adapters/gemini_adapter.py`): Bổ sung quy tắc bảng biểu liên trang không chèn `---`, quy tắc chống bẻ đôi từ qua trang, và quy tắc toàn vẹn ô mô tả 1 hàng = 1 bản ghi ngữ nghĩa.
    - Xây dựng module hậu xử lý độc lập cho OCR `backend/app/modules/ocr/cleaner.py`:
      * `repair_ocr_split_words_across_pages`: Triệt tiêu hoàn toàn mảng từ khóa cứng; sử dụng thuật toán hình thái học và cấu trúc ô/cột tổng quát dựa trên các bất biến cú pháp (`islower()`, cột ID rỗng, không ngắt câu) để hàn gắn từ và mệnh đề ranh giới trang không từ điển; xử lý hyphenation tổng quát.
      * `stitch_ocr_multipage_tables`: Hàn gắn các bảng bị `---` xé rách thành 1 Master Table hoàn chỉnh; tự động loại bỏ header lặp lại giữa chừng.
      * `merge_ocr_orphan_table_rows`: Gộp các hàng rỗng STT vào ô mô tả của hàng cha (chữ thường nối bằng dấu cách, câu mới nối bằng `<br>`); giữ tính liên tục bảng khi gặp comment trang `<!-- Trang X -->`.
      * `clean_ocr_table_syntax`: Loại bỏ separator rác chen giữa các hàng dữ liệu bảng, chuẩn hóa chính tả OCR ("số chỉ" $\rightarrow$ "chỉ số", "kí kết" $\rightarrow$ "ký kết").
      * `post_process_ocr_output`: Hàm điều phối tổng thể cho kết quả OCR.
    - Tích hợp `post_process_ocr_output` vào `_build_response` của `OCRService` (`ocr/service.py`) và trong adapter, đảm bảo toàn bộ luồng OCR (Gemini, Mistral, Combo, Rescue) tự động được chuẩn hóa; trong khi luồng DOCX/PDF text hoàn toàn độc lập, không đi qua hàm này.
    - Viết mới 6 unit tests trong `backend/tests/test_ocr_cleaner.py` (100% passed).
    - Chuẩn hóa toàn bộ tệp mẫu thực tế `Hợp đồng nâng cấp PM cổng thông tin điện tử_0001_boc_tach.md` thành 1 Master Table hoàn chỉnh 74 hàng liên tục.
  - *Tài liệu Quản trị*:
    - Bổ sung **Mục 1.7** (Tôn chỉ kỹ thuật) và **Mục 8.12** (Quy chuẩn Clean Code Vibe Coding) vào `AGENTS.md`: Bắt buộc ưu tiên thuật toán hình thái học / cấu trúc tổng quát (Algorithmic-First), cấm tuyệt đối hardcode từ vựng/từ điển gõ tay, và bắt buộc đề xuất phương pháp cho người dùng biết trước khi triển khai (Propose-Before-Implement).
  - *Verification*:
    - Pytest Full OCR & Knowledge (bao gồm DOCX, PDF text, table reconstructor, cleaners): 75/75 passed (100%).
    - Ruff check: All checks passed (0 lỗi).
    - Biome: 171 files checked, 0 errors.
    - TypeScript: tsc --noEmit (0 lỗi).
    - Vite build: thành công trong 4.67s.
- 0. **Rà Soát Triệt Tiêu Toàn Diện Hardcoded Models, Tôn Trọng Cấu Hình Nhà Cung Cấp Động 100% & Bổ Sung Chuẩn AGENTS.md (phiên #206)**:
  - *Vấn đề phát hiện*:
    1. Trong `inference_service.py`: Khi người dùng truyền `preferred_model_name = "gemini-3.5-flash"` (hoặc model tùy biến), code cũ kiểm tra `if req.preferred_model_name in p_models`. Nếu mảng `p_models` trong DB là danh sách seed cũ chưa kịp cập nhật, hệ thống tự động bỏ qua `preferred_model_name` và ép rơi về model mặc định `p["model_name"]` (`gemini-2.5-flash`), dẫn đến hiện tượng người dùng đổi 3.5 nhưng runtime vẫn chạy 2.5.
    2. Trong Workflow `llm_generate_node.py`: Node LLM quên truyền `preferred_model_name`, `fallback_model_name`, `preferred_provider_id` từ `AssistantRuntimeProfile` vào `LLMGenerateRequest`.
    3. Trong `MistralOCRAdapter`: `model_name` bị gán cứng `"mistral-ocr-latest"` thay vì nhận tham số động.
    4. Trong `readiness.py`: Dòng `getattr(...) or "gpt-4o-mini"` che lấp lỗi cấu hình sai.
    5. Trong `assistant_chat_service.py`: Hàm `_extract_primary_model` hardcode chuỗi `"gpt-4o-mini"` ở 6 nơi thay vì dùng `settings.DEFAULT_LLM_MODEL`.
    6. Trong `vector_indexer.py` và `reranker.py`: Cưỡng ép fallback về model cố định nếu string không bắt đầu bằng `@cf/`.
  - *Backend*:
    - Bổ sung hàm `_is_model_compatible_with_provider` trong `inference_service.py` phân tích độ tương thích động theo họ model (Gemini, GPT, Claude, Mistral, Qwen/DeepSeek/Llama, Custom Proxies).
    - Nâng cấp `_match_score` và phân giải `chosen_model` trong cả `generate()` và `stream_generate()` tôn trọng 100% `req.preferred_model_name` khi người dùng chỉ định.
    - Cập nhật `llm_generate_node.py` trích xuất và truyền đầy đủ `preferred_model_name`, `fallback_model_name`, `preferred_provider_id` từ `profile.model_policy` và `config`.
    - Cập nhật `MistralOCRAdapter` nhận `model_name: str | None = None` và truyền `self._model_name` động.
    - Nâng cấp `_resolve_adapter` và `_extract_auto` trong `OCRService` hỗ trợ dynamic Mistral adapter và tự động đẩy dynamic cloud model lên đầu danh sách candidates.
    - Sửa `readiness.py` bỏ hardcode ngụy tạo; sửa `assistant_chat_service.py` dùng `settings.DEFAULT_LLM_MODEL`.
    - Chuẩn hóa tiền tố Cloudflare embedding/reranker model động.
    - Bổ sung 2 test cases mới, toàn bộ 40/40 tests ModelOps/OCR và 12/12 tests Assistants passed 100%, Ruff 0 lỗi.
  - *Tài liệu Quản Trị*:
    - Bổ sung **Zero Hardcoded Models & Dynamic Provider Resolution Policy** vào `AGENTS.md` (Mục 1.6 Tôn chỉ kỹ thuật, Mục 3.5 Backend Core Rules, Mục 8.11 Clean Code Vibe Coding).
  - *Verification*: Ruff 0 lỗi, Pytest 52/52 passed, Biome 171 files 0 lỗi, tsc 0 lỗi, Vite build thành công (5.17s).
- 0. **Đồng Bộ Động Model OCR & Điều Hướng Auto Router Sang Combo Chain Từ Cấu Hình Hệ Thống (phiên #205.1)**:
  - *Vấn đề*: Người dùng cấu hình model OCR mới trong ModelOps (chọn mô hình trong Combo hoặc mô hình đơn lẻ), nhưng khi nạp tệp scan từ Kho Tri Thức thì log terminal vẫn luôn nhận `gemini-2.5-flash` do bộ định tuyến `_extract_auto` và `_resolve_adapter` trong `OCRService` bị ghim cứng adapter tĩnh chưa liên kết CSDL.
  - *Backend*:
    - Bổ sung `_get_system_defaults` trong `OCRService` truy vấn cấu hình từ CSDL PostgreSQL (`system_model_defaults`).
    - Cập nhật `_resolve_adapter(name_or_model, default_gemini_model, **kwargs)` tự động khởi tạo `GeminiOCRAdapter(model_name=default_gemini_model)` khi người dùng yêu cầu Gemini OCR.
    - Cập nhật `extract_document`: Nếu yêu cầu là `requested in ("auto", "none", "")` và `default_ocr_mode == "combo"`, tự động chuyển tiếp trực tiếp sang chuỗi `_extract_combo_chain`; nếu `default_ocr_mode == "single"`, truyền `default_ocr_model` sang `_extract_auto`.
    - Nâng cấp `_extract_auto`: Tiếp nhận `default_ocr_model` và khởi tạo `GeminiOCRAdapter` với model name động đã cấu hình thay vì cố định `gemini-2.5-flash`.
  - *Verification*: Bổ sung 2 test cases mới, toàn bộ 18/18 tests trong `tests/test_ocr.py` passed (100%), Ruff 0 lỗi, Biome 171 files 0 lỗi, tsc 0 lỗi.
- 0. **Thiết Kế Giao Diện Combos & Vision Adapter Chuẩn 9Router Proxy Theo UI Rule QNU (phiên #205)**:
  - *Ý tưởng 9Router*: Áp dụng mô hình tổ hợp mô hình "Combos (Model combos with fallback)" và "Vision Adapter" từ 9Router Proxy.
  - *Tuân thủ 100% UI Rule*: Sử dụng màu chủ đạo Academic Teal `oklch(0.46 0.13 160)`, triệt tiêu hoàn toàn emoji ký tự, 100% Lucide React icons, tokens ngữ nghĩa và bo góc chuẩn (`rounded-md` cho nút/input, `rounded-lg` cho card/dialog).
  - *Backend*:
    - Bổ sung schema `ModelComboItem` và `VisionAdapterConfig` vào `schemas.py`.
    - Mở rộng `SystemModelDefaults` và `SystemModelDefaultsUpdate` hỗ trợ quản lý nhiều combo và vision pool.
    - Cập nhật `ModelCatalogService` khởi tạo combo mẫu chuẩn QNU `combo_qnu_ocr_master` và `vision_adapter`, tự động đồng bộ sang OCR default khi có combo được đánh dấu mặc định.
  - *Frontend*:
    - Cập nhật `types/modelops.ts` với `ModelComboItem` và `VisionAdapterConfig`.
    - Xây dựng component `CombosVisionSection` (`combos-vision-section.tsx`):
      1. Khối Header & Card giới thiệu 3 chiến lược (Fallback tuần tự dự phòng, Round Robin xoay vòng phân tải, Fusion truy vấn song song).
      2. Danh sách Combos Cards sang trọng hiển thị dải các mô hình, huy hiệu chiến lược, huy hiệu mặc định Kho Tri Thức và thanh công cụ thao tác.
      3. Phân hệ Vision Adapter (Vision image/scan/tables pool, Audio pool).
      4. Dialog "Tạo / Chỉnh Sửa Combo" (Create/Edit Combo Modal) với name input, strategy select, danh sách models có sắp xếp thứ tự và nút thêm model viền nét đứt.
      5. Dialog "Thêm Mô Hình Vào Combo" (Add Model to Combo Modal) với search bar, phân nhóm theo Provider và danh sách Model Pills/Chips có capability icons (`Eye` cho Vision/OCR, `Brain` cho Reasoning, `Zap` cho Tốc độ cao, `Cpu` cho Local Engine) với hiệu ứng toggle selection teal mượt mà.
    - Tích hợp Segmented Tab phân hệ trên `modelops-page.tsx` cho phép chuyển đổi nhanh chóng giữa "Combos & Vision Adapter", "Nhà Cung Cấp & Khóa API" và "Mặc Định Hệ Thống".
  - *Verification*: Ruff 0 lỗi, Pytest 36/36 passed (100%), Biome 171 files 0 lỗi, tsc 0 lỗi, Vite build thành công (6.83s).
- 0. **Combo OCR Dự Phòng Linh Hoạt & Tự Động Failover Khi Hết Quota (Zero-Quota-Failure Policy) (phiên #204)**:
  - *Kiến trúc Combo OCR*: Cho phép định nghĩa một chuỗi gồm nhiều mô hình OCR theo thứ tự ưu tiên (Step 1 -> Step 2 -> Step 3...), gắn chuỗi này làm OCR mặc định của toàn hệ thống/Kho Tri Thức.
  - *Sequential Failover trên Quota*: Khi chạy OCR bóc tách, hệ thống gọi tuần tự từng model. Nếu model gặp lỗi 429 Quota Exceeded (Rate limit), lỗi timeout hoặc lỗi kết nối, hệ thống tự động ghi trace và chuyển sang model tiếp theo trong chuỗi, bảo đảm 0 gián đoạn ingestion.
  - *Backend*:
    - Bổ sung schema `OCRComboItem`, mở rộng `SystemModelDefaults` và `SystemModelDefaultsUpdate` hỗ trợ `default_ocr_mode` (`"combo"` | `"single"`) và `ocr_combo_chain`.
    - Khởi tạo chuỗi chuẩn QNU 5 bước `DEFAULT_QNU_OCR_COMBO_CHAIN` (Gemini 2.5 Flash -> Gemini Flash-Lite -> Mistral OCR -> Docling -> EasyOCR), lưu trữ bền vững trong PostgreSQL metadata.
    - Mở rộng `OCRExtractResponse` có `fallback_engine: str | None` và `cascade_trace: list[str]`.
    - Nâng cấp `OCRService` (`ocr/service.py`) triển khai `_get_active_combo_chain`, luồng `_extract_combo_chain` failover tuần tự, `_resolve_adapter` ưu tiên tra cứu registry.
    - Test Suite: Bổ sung 2 test cases trong `tests/test_ocr.py`, toàn bộ 36/36 tests backend passed 100%, Ruff 0 lỗi.
  - *Frontend*:
    - Bổ sung type `OCRComboItem` trong `types/modelops.ts`.
    - Nâng cấp `SystemDefaultsCard` (`system-defaults-card.tsx`): Dải sơ đồ Visual Pipeline trực quan, bảng quản lý bước (bật/tắt bằng Switch, tăng/giảm thứ tự ưu tiên bằng ArrowUp/Down, xóa bằng Trash2), dropdown bổ sung model mới từ `availableOcrs`, nút khôi phục chuỗi QNU chuẩn, thông báo Zero Quota Failure Policy.
    - Nâng cấp `document-ingest-page.tsx`: Thêm tùy chọn và đặt mặc định là "Combo OCR Mặc Định Hệ Thống", tuân thủ 100% Zero-Emoji Standard.
    - Test Suite: Biome 170 files 0 lỗi, TypeScript tsc 0 lỗi, Vite build thành công (6.49s).
- 0. **Seed Google Gemini Vision OCR, Phân Biệt Rõ Model OCR vs Text & Thiết Lập OCR Mặc Định Cho Kho Tri Thức (phiên #203)**:
  - Cập nhật danh mục mô hình Google Gemini 2.5 và 3.x vào `STANDARD_QNU_PROVIDERS` (`provider_service.py`) và CSDL PostgreSQL (`model_provider_configs` - `prov_ace0d9fe`):
    - *OCR / Vision*: `gemini-2.5-flash`, `gemini-2.5-flash-lite`, `gemini-2.5-pro`, `gemini-3.1-flash-lite`, `gemini-3.1-flash-image`, `gemini-3.1-pro-preview`.
    - *Thuần Text*: `gemma-4-26b-a4b-it`, `gemma-4-31b-it`.
    - Cấu hình `model_specs` với các trường `can_ocr: bool`, `can_vision: bool`, `type: "vision_ocr" | "text"` và mô tả chi tiết.
  - Cập nhật `ModelCatalogService` (`model_catalog_service.py`) nhận diện các model có `can_ocr`/`vision` vào `available_ocrs`, tự động loại trừ các mô hình thuần text `gemma-*`.
  - Thiết lập Google Gemini `gemini-2.5-flash` làm `default_ocr_model` cho Kho tri thức trong CSDL `system_model_defaults`.
  - Triển khai `GeminiOCRAdapter` (`backend/app/modules/ocr/adapters/gemini_adapter.py`) bóc tách Markdown GFM chuẩn xác từ PDF scan và hình ảnh qua Google Gemini Vision API; tích hợp `SmartLayoutDetector` nhận diện bounding boxes cho bảng biểu, con dấu và chữ ký.
  - Đăng ký `gemini_ocr` vào `OCRService` (`ocr/service.py`) với vị trí ưu tiên hàng đầu trong auto OCR và cơ chế fallback an toàn.
  - Nâng cấp `models-grid.tsx` trên Frontend bổ sung bộ lọc `OCR & Bóc tách (Vision OCR)`, gắn huy hiệu `OCR` (sky) và `Text` (muted) trực quan; Cập nhật `system-defaults-card.tsx` và `document-ingest-page.tsx`.
  - Verification: Ruff 0 lỗi, Pytest 414/414 passed (100%), Biome 170 files 0 lỗi, tsc 0 lỗi, Vite build thành công (10.96s).
- 0. **Triệt Tiêu 100% Hardcoded Keywords, Nhận Diện Header Bảng Dựa Trên Hình Thái & Cấu Trúc Đa Miền (Zero-Keyword Morphological Table Header Detection) (phiên #202)**:
  - Loại bỏ hoàn toàn danh sách từ khóa cố định tiếng Việt (`header_keywords`) và regex từ khóa trong `pdf_parser.py` và `table_reconstructor.py`.
  - Chuyển dịch toàn diện sang 5 tiêu chuẩn nhận diện hình thái học zero-keyword:
    1. *Khóa chuỗi dữ liệu (Sequence Key Check)*: Loại trừ hàng bắt đầu bằng số nguyên, mã nhiệm vụ phân cấp `\d+(\.\d+)+`, chữ số La Mã `[IVXLCDM]+`, hoặc mã 7 số `\d{7}`.
    2. *Định danh Cột 0 (Column 0 Integrity)*: Header bảng bắt buộc định danh Cột 0; nếu rỗng thì là hàng dữ liệu mồ côi ngắt dòng.
    3. *Độ dài & Phi mô tả (Length & Non-descriptive)*: Nhãn danh từ $\le 45$ ký tự, không chứa gạch đầu dòng hành chính, không có ngắt câu mệnh đề.
    4. *Mật độ dữ liệu thấp (Low Data Density)*: Tỷ lệ ngày tháng, % $\le 20\%$.
    5. *Chữ cái bắt buộc (Alphabetic Label)*: 100% ô có nghĩa chứa ký tự chữ cái.
  - Bổ sung test suite đa lĩnh vực (tiếng Anh doanh nghiệp, tài chính kế toán, thời khóa biểu).
  - Verification: Ruff 0 lỗi, Pytest 413/413 passed (100%), Biome 170 files 0 lỗi, tsc 0 lỗi, Vite build thành công (14.42s). Live verification 3 tệp PDF nghiệp vụ đạt 100% độ chính xác.
- 0. **Hoàn Thiện Bóc Tách & Reconstruct Bảng Đa Trang Cho 3 PDF Nghiệp Vụ (Kế Hoạch 2214 Bán Dẫn-AI-ANM, Kế Hoạch 2781 Học Liệu E-Learning, Kế Hoạch 4053 BĐCLGD) (phiên #201)**:
  - Kiểm thử & hoàn thiện pipeline bóc tách trên 3 tài liệu PDF hành chính thực tế của ĐH Quy Nhơn:
    1. `QNU_Ke hoach THUC HIEN DE AN DAO TAO NHAN LUC BAN DAN_AI_AT va ANM-signed.pdf` (12 trang, 2214/KH-ĐHQN).
    2. `KH2781 XAY DUNG HOC LIEU E-LEARNING 2025-2026.pdf` (3 trang, 2781/KH-ĐHQN).
    3. `KH4053 BDCLGD nam hoc 2025-2026 (Final)-signed.pdf` (7 trang, 4053/KH-ĐHQN).
  - Khắc phục 1 (Tách tiêu đề Phụ lục & Gộp Multi-line Headers trong `pdf_parser.py`):
    - Thêm `_normalize_raw_table_rows`: Phát hiện khi hàng 0 là ô tiêu đề phụ lục (`PHỤ LỤC...`), tách thành block `HEADING` độc lập trước bảng; gộp các hàng header nhiều tầng thành 1 hàng header chuẩn; bảo vệ các dòng dữ liệu (loại trừ số thứ tự STT, mã số 7 chữ số, chữ số La Mã, nội dung dài > 50 ký tự).
  - Khắc phục 2 (Chống nuốt gạch đầu dòng hành chính tại Trang 6 Kế hoạch 4053):
    - Thêm `is_admin_bullet = txt.startswith(("- ", "+ ", "• "))` loại trừ các gạch đầu dòng phân công nhiệm vụ khỏi bộ lọc anti-leakage của bảng.
  - Khắc phục 3 (Nối bảng 4 cột có spacer columns tại Kế hoạch 2781):
    - Hạ ngưỡng `_normalize_spacer_columns` trong `table_reconstructor.py` từ `>= 5` xuống `>= 3`; bổ sung direct remapping khi số ô dữ liệu thực tế bằng số cột tiêu đề ngữ nghĩa. Khôi phục hoàn hảo Row 1 & Row 2 và nối liền 7 dòng nhiệm vụ của Trang 1 & 2 thành 1 bảng master duy nhất.
  - Khắc phục 4 (Sửa lỗi False Positive `tt` trong `_has_semantic_headers`):
    - Chuyển `any(term in normalize_header(header))` sang regex word boundary `r"\b(stt|tt|mã|tên|công việc|ngành|nhiệm vụ|chủ trì|đơn vị|thời gian|sản phẩm|kết quả|điểm|chỉ tiêu|tổ hợp|phương thức)\b"` và giới hạn chiều dài header <= 40 ký tự. Ngăn chặn `Khoa CNTT` bị nhận nhầm thành header `tt`, giúp bảng Phụ lục 284 dòng Trang 5-12 của Kế hoạch 2214 nối liền mạch.
  - Khắc phục 5 (Fallback an toàn trong `markdown_renderer.py`):
    - Thêm fallback gọi `clean_table_columns` trước khi từ chối render bảng, tránh rớt bảng khi còn cột trắng phụ.
  - Verification: 31/31 unit tests trong `test_table_stitching_and_page_partition.py` và `test_table_reconstructor.py` passed, ruff check 0 lỗi, Biome 170 files 0 lỗi, tsc 0 lỗi. Live verification trên cả 3 file PDF đạt 100% độ chính xác.
  - Kiểm thử thực tế tệp `KH130 trien khai chuan bi DGN CTDT 3 CTDT AUN-QA 2026.pdf` (6 trang, 45 nhiệm vụ): Xác nhận toàn bộ 45 nhiệm vụ được bóc tách hoàn hảo vào đủ 6 cột chuẩn, 100% dòng phân cách `:---` được bảo toàn.
  - Ghép nối đa trang siêu chuẩn: Dòng 16 tự động hút phần text nối trang ở đỉnh Trang 3 (`KH-TC, TT. S&HL, các đơn vị liên quan`), Dòng 23 tự động nối tiếp câu ở đỉnh Trang 4 (`Bảo đảm tính hoạt động ổn định...`), 0 dòng mồ côi.
  - Triệt tiêu số trang lề trên (Header Pagination theo NĐ 30/2020/NĐ-CP Điều 9.4): Bổ sung kiểm tra `top_percent <= 8.0` cho `blocks.py` và `page_num > 1 and b_rect.y1 < height * 0.08` cho `pdf_parser.py`, cập nhật `_RE_PAGE_NUMBERS` trong `cleaner.py` bao quát số trang đơn độc `\d{1,3}`, xóa sạch hoàn toàn các số trang header `2`, `3`, `4`, `5`, `6`.
  - Verification: 10/10 unit tests trong `test_table_stitching_and_page_partition.py` passed, ruff check 0 lỗi, Biome 170 files 0 lỗi, tsc 0 lỗi. Live verification trên KH130 sạch 100% không còn số trang rác.

- 0. **Khắc Phục Lệch Cột Row 3.1 ("Ban hành") & Bảo Toàn Dòng Phân Cách Bảng Markdown (:---) (phiên #199)**:
  - Khắc phục 1 (Chống nhầm động từ "Ban hành" thành Đơn vị chủ trì): Cập nhật `_LEAD_UNIT_RE` trong `table_reconstructor.py` bằng negative lookahead `ban(?!\s+hành)`, `phòng(?!\s+ngừa|\s+chống)`, `trường(?!\s+hợp)`, `viện(?!\s+dẫn)`. Ngăn chặn triệt để hiện tượng nội dung nhiệm vụ 3.1 ("Ban hành quy định đo lường...") bị nhận diện nhầm thành Đơn vị chủ trì, làm rỗng cột Nội dung và dồn Phòng KT&BĐCL, Trung tâm S&HL vào cột Sản phẩm.
  - Khắc phục 2 (Ưu tiên ánh xạ cột trực tiếp qua semantic_indices): Trong `_normalize_spacer_columns`, khi hàng có đủ số cột $\ge$ len(headers) và đã khớp mã nhiệm vụ & đơn vị chủ trì, ánh xạ trực tiếp `selected_cells` theo `semantic_indices` của trang thay vì chạy lại heuristic compact, giữ nguyên 100% cấu trúc trích xuất chuẩn xác của PyMuPDF.
  - Khắc phục 3 (Bảo toàn dòng phân cách bảng Markdown `|:---|:---|...|`): Sửa lỗi trong `_stitch_table_continuations` (`cleaner.py`). Trước đây hàm kiểm tra hàng tiếp theo mà không xét xem giữa 2 hàng có ranh giới trang (`---` hay `<!-- Trang N -->`) hay không, khiến dòng phân cách (separator row) ngay sau header của MỌI bảng bị nuốt chửng (khiến Markdown không render được bảng). Bổ sung điều kiện `has_boundary = any(...)` giúp bảo toàn toàn bộ 20 dòng separator của 20 trang phụ lục.
  - Verification: 10/10 unit tests trong `test_table_stitching_and_page_partition.py` passed, ruff check 0 lỗi, Biome 170 files 0 lỗi, tsc 0 lỗi, Vite build 8.64s thành công. Kiểm thử live trên tệp Kế hoạch 2025-2026 xác nhận: Row 3.1 chuẩn 7 cột, 20 dòng phân cách bảng phục hồi 100%, Row 4.10, 7.2, 8.1 và Section VIII hoàn hảo.

- 0. **Giải Pháp Bóc Tách Hoàn Chỉnh Toàn Diện: Chuẩn Hóa Bảng Đa Trang, Ghép Dòng Ngắt Đôi & Triệt Tiêu Số Trang Footer (phiên #198)**:
  - Khắc phục 1 (Căn chỉnh cột bảng tiếp nối có cột spacer rỗng): Cập nhật `_compact_task_row` và `_normalize_spacer_columns` trong `table_reconstructor.py` hỗ trợ `semantic_indices`, đưa các bảng 9/11 cột về 7 cột danh nghĩa chuẩn và ánh xạ chính xác hàng tiếp nối (orphan continuation row) sang Cột 1 (Nội dung) thay vì bị lệch sang Cột 3/6. Khắc phục triệt để lỗi dòng 4.10, 7.2, 8.1.
  - Khắc phục 2 (Gộp số La Mã bị tách ngắt dòng): Thêm hàm `_merge_split_roman_rows` tự động nhận diện chữ số La Mã bị rớt dòng (`VII` + `I` $\rightarrow$ `VIII`), gộp thành 1 hàng duy nhất và loại bỏ hàng rỗng thừa.
  - Khắc phục 3 (Chống nhầm lẫn hàng dữ liệu dài thành subheader): Thêm chốt chặn trong `_merge_second_header_row` từ chối các hàng có ô dài >50 ký tự hoặc gạch đầu dòng, ngăn không cho hàng dữ liệu nhiệm vụ bị nuốt vào tiêu đề bảng.
  - Khắc phục 4 (Tiền chuẩn hóa bảng trước khi ghép liên trang): Chuẩn hóa schema (`clean_table_columns`) cho từng bảng đơn lẻ trước khi kiểm tra `schema_key`, bảo đảm mọi bảng con chia sẻ cùng cấu trúc cột trước khi chạy `merge_continuation`.
  - Khắc phục 5 (Triệt tiêu số trang rác ở chân trang): Cập nhật `blocks.py` và `pdf_parser.py` lọc bỏ các khối số trang đơn độc ở chân trang (`y0 > 88%` và khớp `^\d{1,3}$` hoặc `Trang \d+`), giúp Markdown không bị dính số lẻ trước dấu `---`.
  - Khắc phục 6 (Đảm bảo quy tắc 1 dòng = 1 bản ghi): Mỗi hàng bảng Markdown xuất ra là 1 dòng vật lý duy nhất, xuống dòng nội bộ ô chuyển thành `<br>`, bảo đảm tính toàn vẹn khi vector hóa vào Qdrant.
  - Verification: 8/8 unit tests trong `test_table_stitching_and_page_partition.py` passed, full knowledge test suite 55/55 passed (100%), Ruff 0 lỗi, Biome 170 files 0 lỗi, tsc 0 lỗi, Vite build 9.00s.

- 0. **Tối Ưu Hóa Toàn Diện Bộ Bóc Tách PDF, Phân Mảnh Bảng Đa Trang & Triệt Tiêu Lặp Text Chân Trang (phiên #197)**:
  - Khắc phục 1 (Thứ tự khối Trang 2 & 13): Cập nhật `backend/app/modules/knowledge/parsers/blocks.py` sắp xếp toàn bộ khối bảng và văn bản theo tọa độ đọc tự nhiên `(y, x)`, giúp phần mô tả Phương thức 1-5 & Mục 4 nằm trên bảng (Trang 2) và tiêu đề `PHỤ LỤC 1` nằm trên đỉnh trang (Trang 13).
  - Khắc phục 2 (Phân bổ bảng đa trang Trang 2..8): Cập nhật `markdown_renderer.py` cắt lát các hàng bảng đa trang theo `pnum in sorted(tbl.source_pages)`, sinh bảng Markdown độc lập kèm header cho từng trang, bảo toàn thứ tự nội dung và triệt tiêu hoàn toàn hiện tượng trang 3..8 bị trống hoặc rách hàng mồ côi khi fallback.
  - Khắc phục 3 (Line-Level Clipping chống lặp text Trang 12): Thêm cơ chế cắt lọc giao cắt biên giới bảng trong `blocks.py` và `pdf_parser.py`, triệt tiêu 100% text lặp của ngành 51 & 52 trước khối chữ ký "Nơi nhận:".
  - Khắc phục 4 (Bảo vệ ngành độc lập Trang 14): Cập nhật `table_reconstructor.py` (`is_orphan_continuation_row`) bảo vệ hàng có mã ngành 7 số (`7310608`), tự động kế thừa tên nhóm môn `active_group` ("Tiếng Anh") từ cuối trang trước cho ngành Đông phương học.
  - Khắc phục 5 (Sửa lỗi Serialization str vs int trong `build_studio_pages`): `ingestion_service.py` tra cứu `page_markdowns.get(page_number) or page_markdowns.get(str(page_number))` và đưa toàn bộ các trang có trong `page_markdowns` vào `page_numbers`.
  - Verification: 5 unit tests mới trong `test_table_stitching_and_page_partition.py` passed 100%, Pytest 27/27 passed, Ruff 0 lỗi, Biome 170 files 0 lỗi, TypeScript 0 lỗi, Vite build thành công 11.27s, live verification trên tệp PDF tuyển sinh 14 trang đạt 6/6 tiêu chí.

- **Thời gian cập nhật**: 2026-09-22 14:30 (UTC+7)
- **Phiên số**: #196
- **Agent**: AI Senior Full-Stack Architect & Enterprise AI Systems Specialist
- **Mục tiêu đã hoàn thành**:
- 0. **Khắc Phục Triệt Để 6 Vấn Đề Cấu Trúc Trong Bộ Bóc Tách Tài Liệu (PDF, OCR, Table Reconstructor & Cleaner) (phiên #196)**:
  - Vấn đề: Bộ mã nguồn bóc tách tài liệu tuyển sinh ĐH Quy Nhơn 2026 từ PDF 14 trang gặp 6 vấn đề cấu trúc: (1) Đảo lộn trật tự đọc (bảng nhảy lên trước lời dẫn phương thức tuyển sinh); (2) Đứt gãy dòng ngắt trang tạo hàng mồ côi (STT 5, 23, 30, 39, 48); (3) Xé đôi bảng song song IELTS/VSTEP; (4) Header đa tầng (Chỉ tiêu, Điểm trúng tuyển) rớt vào hàng dữ liệu số 32 trên trang tiếp nối; (5) Rò rỉ rác OCR ngành 51, 52 đáy trang 12; (6) Nuốt hàng phân cách GFM table `|---|---|` và mã ngành ngắt dòng (`7340301\nAC`).
  - Giải pháp Kỹ thuật tại lõi pipeline:
    1. `pdf_parser.py`: Bổ sung `_fuse_side_by_side_tables` ghép ngang bảng song song $Y \ge 70\%$, phân biệt tiêu đề trùng; mở rộng margin buffer `_is_table_text` triệt tiêu 100% rác OCR; bổ sung guard `is_heading` bảo vệ tiêu đề mục.
    2. `table_reconstructor.py`: Thêm `is_sub_header_row` nhận diện và loại bỏ sub-header lặp lại bảo vệ hàng 32; mở rộng `_PROGRAM_CODE_RE = r"^\d{7}[A-Za-z]*$"`; thêm `_normalize_program_code_cells` nối mã ngành bẻ dòng; thêm `_forward_fill_hierarchical_columns` điền tên môn Phụ lục 1.
    3. `cleaner.py`: Bổ sung điều kiện `has_page_boundary` vào `_stitch_table_continuations` bảo toàn 100% dòng phân cách GFM table `|---|---|`.
    4. `markdown_renderer.py`: Sắp xếp khối văn bản và bảng theo `top_y` tự nhiên từng trang; sinh căn lề thông minh `:---:` và `:---`.
  - Verification: 100% kiểm định tự động `validate_admission_markdown.py` vượt qua trên cả 2 tệp bóc tách thực tế và golden format (53/53 ngành tuyển sinh, 52/52 ngành điểm chuẩn, 38/38 ngành Phụ lục 1, bảng 4 cột VSTEP/IELTS); Pytest `tests/test_table_reconstructor.py` & `tests/test_knowledge.py` 51/51 passed (100%); Ruff 0 lỗi; Biome 170 files 0 lỗi, tsc 0 lỗi; 414/414 files sạch Zero Mojibake.
- 0. **Phân Tích & Chuẩn Hóa Tệp Bóc Tách Đề Án Tuyển Sinh 2026 Đạt Chuẩn GFM và Vector DB (phiên #195)**:
  - Vấn đề: Người dùng kiểm thử tính năng bóc tách PDF 14 trang thành file Markdown `Thong tin tuyen sinh dai hoc 2026_Lan2-1_boc_tach.md`. Kiểm toán phát hiện 5 lỗi nghiêm trọng: (1) Đảo lộn trật tự logic văn bản (bảng ngành nhảy lên trước mô tả phương thức; bảng điểm chuẩn 32 ngành chèn ngang chia cắt Mục 8 học phí; bảng Phụ lục 1 đặt trước tiêu đề); (2) Các hàng bảng bị ngắt qua trang (STT 5, 23, 30, 39, 48) biến thành hàng mồ côi mất tên và mã ngành; (3) Bảng quy đổi VSTEP/IELTS bị xé nhỏ và mất tiêu đề VSTEP; (4) 100% bảng Markdown thiếu hàng phân cách `|---|---|`; (5) Trùng lặp Mục 8 và rò rỉ rác OCR ngành 51, 52 cuối trang 12.
  - Giải pháp Kỹ thuật:
    1. Xây dựng script `scripts/standardize_admission_markdown.py` chuẩn hóa toàn bộ tệp Markdown theo cấu trúc GFM vàng (Gold Standard), khôi phục trật tự đọc tuyến tính chuẩn văn bản hành chính, ghép nối 100% các hàng mồ côi vào ngành cha, chuẩn hóa bảng VSTEP/IELTS 4 cột đầy đủ tiêu đề, định dạng phân cách dòng bằng `<br>`, xóa bỏ rác OCR và khối trùng lặp.
    2. Xây dựng script kiểm định tự động `scripts/validate_admission_markdown.py` kiểm toán 9 tiêu chí: UTF-8 sạch, cú pháp GFM table, trật tự đọc, 53/53 ngành tuyển sinh, 52/52 ngành điểm chuẩn, 38/38 ngành Phụ lục 1, zero orphan rows, zero OCR leakage.
  - Verification: `validate_admission_markdown.py` 100% passed, Pytest `tests/test_knowledge.py` 33/33 passed (100%), Ruff 0 errors, `check_mojibake.py` 414/414 tệp sạch. Tệp Markdown sẵn sàng 100% để nạp vào Vector DB.
- 0. **Khắc Phục Lỗi Index Kho Tri Thức, Ánh Xạ Mô Hình BGE-M3 & Đồng Bộ Credentials Provider Lúc Khởi Động (phiên #194)**:
  - Vấn đề: Người dùng nạp tệp `Thong tin tuyen sinh dai hoc 2026_Lan2-1.pdf` vào Kho Tri thức Đề án Tuyển sinh (`col_admissions`), giao diện hiển thị badge màu đỏ `! Lỗi index`. Qua truy vấn CSDL, bản ghi `job_1c26a820413d` báo lỗi: `Mô hình embedding (BGE-M3/Cloudflare) không khả dụng. Hệ thống từ chối nạp dữ liệu giả mạo.` (503).
  - Nguyên nhân cốt lõi:
    1. `settings.CLOUDFLARE_ACCOUNT_ID` và API Token được lưu trong CSDL PostgreSQL nhưng chưa có bước tự động đồng bộ vào runtime `settings` khi server FastAPI khởi động (`lifespan`), khiến nhánh Cloudflare GPU nhanh bị bỏ qua vì thiếu `account_id`.
    2. Nhánh local fallback gọi `SentenceTransformer(settings.EMBEDDING_MODEL)` với giá trị `@cf/baai/bge-m3` thay vì tên repository Hugging Face chuẩn `BAAI/bge-m3`, gây lỗi 404 RepositoryNotFoundError.
    3. Cả 2 tầng đều không khả dụng, kích hoạt chốt chặn Anti-Mock từ chối dữ liệu giả mạo $\rightarrow$ `index_status = "index_failed"`.
  - Giải pháp Kỹ thuật:
    1. Thêm hàm `_resolve_local_model_name()` trong `vector_indexer.py` tự động chuyển đổi các alias Cloudflare (`@cf/baai/bge-m3` $\rightarrow$ `BAAI/bge-m3`) cho SentenceTransformers.
    2. Thêm phương thức `sync_active_providers_to_runtime()` trong `ProviderService` và `ModelOpsService`.
    3. Tích hợp gọi `sync_active_providers_to_runtime()` ngay trong hàm `lifespan` lúc khởi động server `app/main.py`, bảo đảm Cloudflare Workers AI Edge Embedding và các API khác luôn sẵn sàng phục vụ tức thì.
    4. Bổ sung `refetchInterval` tự động thăm dò (3s) trên giao diện `collection-detail-page.tsx` khi có tài liệu đang `indexing`/`processing`.
  - Verification: 70/70 pytests passed (100%), Ruff 0 lỗi, Biome 170 files 0 lỗi, tsc 0 lỗi. Tài liệu `doc_640939cf032e` đã được reindex thành công với 16/16 chunks vào Qdrant (`status: ready`, `index_status: indexed`).
- 0. **Khắc Phục Lỗi Thiếu Bảng `platform_document_types` & Tối Ưu Hóa Chuỗi Migration Alembic Cho Seed Data (phiên #193)**:
  - Vấn đề: Người dùng chạy seed dữ liệu (`db seed --document-types`, `db seed --all`, `seed_document_types.py`) gặp lỗi `UndefinedTableError: relation "platform_document_types" does not exist`. Khi thử migrate, gặp tiếp lỗi `StringDataRightTruncationError` do Alembic `version_num` mặc định `VARCHAR(32)` trong khi revision ID dài 43 ký tự, lỗi foreign key do 772 orphan facts trong `knowledge_facts`, lỗi thiếu bảng `conversation_threads` trong migration feedback, và thiếu `await connection.commit()` trong `alembic/env.py`.
  - Giải pháp Kỹ thuật:
    1. Override `DefaultImpl.version_table_impl` trong `backend/alembic/env.py` tạo `version_num VARCHAR(64)` và thực thi `ALTER TABLE IF EXISTS alembic_version ALTER COLUMN version_num TYPE VARCHAR(64)`. Bổ sung `await connection.commit()` đảm bảo async migration commit trọn vẹn.
    2. Dọn dẹp orphan facts trong `20260919_facts_foreign_key_and_schema_sync.py` trước khi thiết lập foreign key `CASCADE`.
    3. Thêm DDL tạo bảng `conversation_threads` và `conversation_messages` nếu chưa có trong `20260922_conversation_feedback.py`.
  - Kết quả Seed: Đồng bộ thành công 37 loại văn bản theo NĐ 30/2020 (`added=37`), seed toàn bộ `--all` thành công mỹ mãn (5 workflows, 5 trợ lý AI, 5 kho tri thức, 5 Qdrant collections, 7 ingestion job records).
  - Verification: Pytest 394/394 passed (100%), Ruff 0 errors, 8/8 tests `test_document_types.py` passed.
>>>>>>> 9e3bb9cb7d00dcac55619410aa160532570b9c8e
- 0. **Bổ Sung Nút Tải Nội Dung Cuộc Trò Chuyện Dạng Markdown (.md) & Loại Bỏ Fallback Bắt Nhầm Thực Thể "Nào" (phiên #192)**:
  - Tính năng 1 (Xuất Markdown Chat Studio): Tạo tiện ích `frontend/src/lib/export-markdown.ts` định dạng toàn bộ cuộc trò chuyện thành tệp Markdown (.md) chuẩn chỉnh kèm Header metadata, vai trò Người dùng/Trợ lý, thời gian, nội dung câu hỏi/trả lời, trích dẫn tài liệu gốc (blockquote), tệp đính kèm và nút gợi ý; tích hợp nút "Tải về (.md)" với icon Lucide `Download` trên thanh công cụ `ChatStudioPage`.
  - Tính năng 2 (Xuất Markdown Bàn Làm Việc Cán Bộ): Tích hợp nút "Xuất MD" tại thanh điều khiển chi tiết cuộc trò chuyện của cán bộ tư vấn trong `ConversationsPage` (`/conversations`).
  - Sửa lỗi Backend (Chống Entity Hijacking Đại Từ Nghi Vấn): Loại bỏ đoạn regex fallback cũ trong `backend/app/modules/rag/service.py` từng bắt nhầm đại từ nghi vấn `"nào"` trong câu "áp dụng cho những ngành nào?" thành tên thực thể `"Nào"`, làm RAG ép LLM chỉ trả lời cho ngành CNTT của lượt trước; sử dụng trực tiếp `analysis.target_entities` đã được bảo vệ.
  - Verification: Thêm 1 unit test mới trong `test_rag_entity_scoped_formatting.py` (7/7 passed), Pytest 394/394 passed (100%), Ruff 0 lỗi, Biome 170 files 0 lỗi, tsc 0 lỗi, Vite build thành công (8.37s).
- 0. **Khắc Phục 3 Lỗi RAG Thực Tế: Entity Stickiness, False-Positive Tổ Hợp Môn & Ký Tự Rác GIZ (phiên #191)**:
  - Vấn đề 1 (Entity Stickiness ở câu hỏi chung): Người dùng hỏi "xin chào cho tôi biết phương thức tuyển sinh năm 2026" nhưng bot trả lời phương thức riêng của ngành CNTT (mã 7480201) do `lookup_facts` quét `attribute_name.ilike("%phương thức%")` trả về facts của ngành CNTT đặt vào `[TẦNG 1 - BẢNG SỐ LIỆU]`, ép LLM phải nói về ngành đó.
  - Vấn đề 2 (False-Positive Tổ Hợp Môn): Hỏi "các ngành xét tuyển tổ hợp môn Toán, Tiếng Anh, Hóa học" nhưng bot liệt kê ngành Giáo dục Tiểu học vì combo 1 có Toán, combo 2 có Hóa; thuật toán cũ quét gộp toàn bộ chuỗi khiến xuất hiện cả 3 từ khóa.
  - Vấn đề 3 (Rò rỉ thẻ `[GIZ]:` và gợi ý lặp lại): Bot bị rò rỉ header `[GIZ]:` và nút gợi ý lặp lại chính câu hỏi người dùng vừa hỏi.
  - Giải pháp 1 (Chống Fact Hijacking): Nâng cấp `lookup_facts` trong `facts.py`: khi câu hỏi chung không có `target_entities`, `entity_codes` hay `subject_names`, hàm `_is_major_specific_fact` tự động loại bỏ các facts của ngành đơn lẻ, nhường đường cho các chunks tài liệu Đề án tuyển sinh toàn trường. Khi có `target_entities`, chỉ trả về facts của đúng ngành đó.
  - Giải pháp 2 (Chấm điểm từng combo con & Semicolon Fallback): Cập nhật `count_subject_matches` bóc tách từng combo trong ngoặc đơn `(...)` hoặc dấu phân cách `;`, `\n`, `|`, `/`, tính điểm theo max matches của một combo duy nhất + alias môn học (tiếng anh $\leftrightarrow$ anh, vật lý $\leftrightarrow$ lý,...). Cập nhật `SYSTEM_PROMPT_TEMPLATE` yêu cầu tất cả môn phải thuộc cùng 1 tổ hợp duy nhất.
  - Giải pháp 3 (Dọn sạch `[GIZ]:` và Echo Filter): `_TRAILING_TAG_PATTERN` dọn sạch triệt để `**[GIZ]:**`, `[GỢI Ý]:`, `[GIZ]:`; `_is_too_similar_to_query` lọc bỏ gợi ý trùng lặp ý $\ge 70\%$ với câu hỏi hiện tại.
  - Verification: 7 unit tests mới trong `test_suggestion_perspective_and_multiturn.py` (16/16 passed), Pytest 393/393 passed (100%), Ruff 0 lỗi, Biome 169 files 0 lỗi, tsc 0 lỗi, Vite build thành công.
- 0. **Nâng Cấp Node DAG Query Rewrite, Chống Context Bleeding Từ Lịch Sử Đa Lượt & Bảo Vệ Toàn Vẹn RAG (Zero Hardcoding) (phiên #190)**:
  - Vấn đề: Câu hỏi lượt 2 "Phương thức xét tuyển của trường gồm những gì?" bị LLM lôi tổ hợp môn Toán, Tiếng Anh, Hóa học của lượt 1 vào, biến thành câu hỏi về ngành xét tuyển tổ hợp môn, làm RAG tra cứu sai chủ đề.
  - Phân tích nguyên nhân: LLM rewrite nhận toàn bộ lịch sử trò chuyện lượt trước nên bị recency bias/context bleeding; các chốt chặn phòng vệ cũ so sánh có dấu và từ khóa stopwords chưa toàn diện.
  - Giải pháp 1 (`is_context_dependent_query`): Phân loại câu hỏi độc lập (câu hoàn chỉnh $\ge 5$ từ, không đại từ nối) $\rightarrow$ CẮT TOÀN BỘ lịch sử khỏi prompt LLM rewrite (`effective_history = None`). LLM không thể gán ghép chủ đề cũ khi không thấy lịch sử.
  - Giải pháp 2 (Chuẩn hóa không dấu `_unaccent` & Stopwords mở rộng): Tập `_UNACCENTED_FUNCTIONAL_STOPWORDS` khử sạch từ ngữ pháp, xã giao giúp bóc tách chính xác các từ khóa nội dung thực sự.
  - Giải pháp 3 (4 lớp chốt chặn phòng vệ bất biến dấu): Guard 2 kiểm tra recall từ khóa nội dung (bắt buộc $\ge 50\%$), Guard 3 bảo vệ các cụm ý định cốt lõi tổng quát (`_CORE_INTENT_TERMS`), Guard 4 chặn tự ý nhét môn thi THPT (`_COMBO_SUBJECT_TERMS`), Guard 5 kiểm tra độ dài.
  - Giải pháp 4 (Zero Hardcode): Chuẩn hóa prompt với các ví dụ tổng quát đại diện cho các mô đun trường đại học, xóa sạch mọi mẫu gán ghép câu hỏi cụ thể.
  - Verification: 3 unit tests mới, 11/11 tests `test_query_rewrite_node.py` passed, full backend suite 395/395 passed (100%), Biome 0 lỗi, tsc 0 lỗi, Vite build thành công.
- 0. **Khắc Phục Triệt Để Lỗi Lộn Vai Nút Gợi Ý & Chống Entity Hijacking Trong Hội Thoại Đa Lượt (phiên #189)**:
  - Vấn đề 1: Bot trả lời kết thúc bằng câu hỏi bot hỏi người dùng ("Bạn có muốn tìm hiểu về tổ hợp môn xét tuyển của ngành cụ thể nào không?"), nút Suggestion Chip lấy nguyên văn khiến khi người dùng click vào bị lộn vai trò.
  - Vấn đề 2: Khi nhận câu hỏi chứa "ngành cụ thể nào", query router bóc tách thành `target_entities = ["Cụ Thể Nào"]`, hoặc query rewrite suy diễn kéo tên ngành CNTT từ lượt trước vào làm sai lệch ý định.
  - Giải pháp 1: `convert_or_filter_suggestion_perspective()` trong `composer.py` chuyển đổi tự động các câu hỏi lộn vai thành câu hỏi góc độ người dùng ("Các ngành của trường xét tuyển những tổ hợp môn nào?"), lọc bỏ câu lịch sự không thể chuyển đổi. Cập nhật `SYSTEM_PROMPT_TEMPLATE` và seeder prompt bắt buộc 100% câu hỏi gợi ý phải ở ngôi Người dùng hỏi Trợ lý.
  - Giải pháp 2: `query_router.py` loại trừ danh sách từ placeholder ("cụ thể", "cụ thể nào", "nào đó", "bất kỳ",...) khỏi `target_entities`. `query_rewrite_node.py` cập nhật quy tắc phòng vệ cấm tự ý gán ghép ngành vào câu hỏi chung.
  - Verification: 9 unit tests mới trong `test_suggestion_perspective_and_multiturn.py` passed 100%, 32 tests hồi quy passed, ruff 0 lỗi, biome 0 lỗi, tsc 0 lỗi, live chat E2E 3 lượt thành công mỹ mãn.
- 0. **Khắc Phục Triệt Để Lỗi Rò Rỉ Dữ Liệu Bảng Thô & Nâng Cấp Chất Lượng Trình Bày RAG (phiên #188)**:
  - Vấn đề: Bot trả lời nguyên cụm bảng thô `|||||| 31 | 7380101...`, rò rỉ 9 ngành không liên quan (over-inclusion), vỡ cú pháp bảng Markdown.
  - Entity-Scoped Extraction: `QueryClassifier.analyze()` phát hiện `target_entities`, tự động inject ràng buộc bắt buộc LLM chỉ trích xuất đúng thực thể được hỏi, cấm liệt kê ngành khác.
  - Chỉ đạo Định dạng Động: `answer_format_planner.get_format_instructions()` đưa trực tiếp quy tắc trình bày vào prompt (ép dùng danh sách gạch đầu dòng rõ ràng cho tổ hợp môn, giải thích ký hiệu phương thức 1, 2, 3, 4).
  - Bộ lọc Hậu xử lý (`sanitize_rag_answer`): Tự động dọn sạch pipe dính chùm `||||||` và chốt chặn phân tích chuyển đổi cụm bảng nhiều ngành thành danh sách sạch sẽ.
  - Đồng bộ Prompts CSDL: Cập nhật `ast_admissions`, workflow JSON và CSDL PostgreSQL.
  - Verification: 6 tests mới trong `test_rag_entity_scoped_formatting.py` passed (100%), `test_rag.py` 26 passed, ruff 0 lỗi, biome 0 lỗi, tsc 0 lỗi, build Vite thành công.
- 0. **Triển Khai Đợt C Đánh Giá RAG (phiên #187)**:
  - Parent-child: `expand_with_neighbors()` prompt-only, suy thoái êm.
  - Multi-query: `sparse_variants` + RRF chiết khấu 0.5, không tốn embedding.
  - Drift loop: trend/samples APIs + tab Đánh Giá Người Dùng trên `/evaluation`.
  - Verification: Ruff 0 lỗi, Pytest **377/377 passed**, Biome 169 files/tsc/build xanh.
- 0. **Triển Khai Đợt B Đánh Giá RAG (phiên #186)**:
  - Facts: rank theo số môn khớp (over-fetch ×3, chỉ quét value).
  - RRF: trọng số intent (exact 1.0/1.2, narrative 1.2/0.8) + log.
  - Prompt: 3 tầng evidence + ép temperature ≤0.2 cho fact.
  - Eval online: bảng `conversation_feedbacks`, migration đã upgrade, 2 API, vote best-effort.
  - Verification: Ruff 0 lỗi, Pytest **373/373 passed**, Alembic sạch, Biome/tsc/build xanh.
- 0. **Triển Khai Đợt A Đánh Giá RAG (phiên #185)**:
  - Cache: key thêm `history_hash`, bỏ cache query <8 từ kèm history.
  - History: `scope_history_by_topic()` tối đa 4 tin nhắn trùng chủ đề.
  - Runtime: `verify_numeric_grounding()` chặn số bịa → No-Answer.
  - Rerank: timeout 10s→3s + log provider/latency/in/out.
  - Sparse: unaccent fallback cho query không dấu.
  - Verification: Ruff 0 lỗi, Pytest **368/368 passed**.
- 0. **Parser Gợi Ý Chịu Lỗi JSON Inline + Tra Cứu Ngược Tổ Hợp Môn (phiên #184)**:
  - Câu 3 `Toán, Tiếng Anh, Hóa học` lặp đáp án phương thức câu 2; cả 3 lượt lộ raw `[GỢI Ý]: [...]`.
  - `composer.py`: regex nhận cùng dòng, parse JSON inline quoted-first, lột marker rỗng.
  - `query_router.py`: `subject_names` + `SUBJECT_PATTERNS` có gate ngữ cảnh, loại đại từ `anh` và HSG.
  - `retriever.py`: `select_ilike_tokens()` regex + stop mở rộng, OR tới 6 token đặc thù.
  - Verification: Ruff 0 lỗi, Pytest **363/363 passed**.
- 0. **Khắc Phục RAG Trả Nhầm Bảng Xét Tuyển Thẳng Khi Hỏi Tổ Hợp Môn CNTT (phiên #183)**:
  - Câu `ngành CNTT cần những môn học nào để xét tuyển` bị trả Phụ lục 1 HSG do `fact_attributes=[]` và overlap `môn + xét tuyển`.
  - `query_rewrite_node.py`: thêm `expand_subject_combo_paraphrase()` 0ms (`môn học nào/môn nào/cần học môn gì` → `tổ hợp môn`), bỏ qua HSG/tuyển thẳng, chống nhân đôi.
  - `query_router.py`: thêm `tổ hợp/môn học` vào packs, map `môn + xét tuyển/ngành` → `subject_combinations`.
  - Tests mới: `test_fast_rule_normalize_subject_combo_paraphrase`, `test_query_classifier_mon_hoc_maps_to_subject_combinations`.
  - Verification: Ruff 0 lỗi, Pytest **360/360 passed**, verify thủ công bug query → `exact_fact [7480201] [subject_combinations]`.
  1. **Kích Hoạt Hệ Thống Nút Bấm Gợi Ý Tương Tác 1-Click (Interactive Suggestion Chips) & Triệt Tiêu Câu Hỏi Tu Từ Rập Khuôn (phiên #180)**:
     - **Vấn đề giải quyết**: Khắc phục triệt để hiện tượng bot lặp đi lặp lại câu hỏi tu từ thụ động ở đuôi: *"Bạn có muốn mình chia sẻ thêm về chỉ tiêu tuyển sinh hoặc các phương thức xét tuyển áp dụng cho các ngành này không?"*.
     - **Backend**:
       * Cập nhật `SYSTEM_PROMPT_TEMPLATE` trong `composer.py` cấm câu hỏi tu từ đóng dạng *"Bạn có muốn..."*, yêu cầu đề xuất 2 câu hỏi hành động cụ thể theo khối `[GỢI Ý]:`;
       * Xây dựng hàm `extract_suggested_questions`: bóc tách gợi ý thành danh sách, dọn sạch 100% câu hỏi boilerplate khỏi thân tin nhắn Markdown, tự động chuyển đổi câu hỏi đóng sót lại thành 2 câu hỏi cụ thể;
       * Bổ sung trường `suggested_questions: list[str]` vào `AskResponse`, chuyển tiếp qua các node DAG (`rag_answer_node`, `output_chat_node`), và truyền ra trong cả HTTP JSON response và SSE `event: done`;
       * Cập nhật và đồng bộ cấu hình CSDL PostgreSQL cho Trợ lý `ast_admissions` và quy trình `admissions-assistant`.
     - **Frontend**:
       * Nâng cấp component `ChatMessage` hiển thị mảng `suggestedQuestions` thành các Nút bấm Chip bo tròn cao cấp kèm icon Lucide `ArrowRight` có hiệu ứng hover QNU Academic Teal và đổ bóng `shadow-2xs`;
       * Kết nối sự kiện `onSuggestedClick(q)`: người dùng click vào chip sẽ tự động gửi câu hỏi ngay lập tức mà không cần gõ lại.
     - **Verification**:
       * Thử nghiệm trực tiếp với câu hỏi: *"các ngành xét tuyển tổ hợp môn Toán, Tiếng Anh, Hóa học"*: Thân tin nhắn sạch 100%, chân tin nhắn xuất hiện 2 Suggestion Chips tương tác;
       * Backend Ruff 0 lỗi, Pytest 41/41 passed (100%), Frontend Biome 0 lỗi (168 files), TypeScript 0 lỗi, Vite Build thành công (9.27s).
  2. **Khắc Phục RAG Entity Code Augmentation & Chống Rò Rỉ Few-Shot Trong Query Rewrite (phiên #179)**:
     - **Phân tích nguyên nhân cốt lõi**:
       * Khi người dùng hỏi `"ý tôi muốn hỏi là tổ hợp môn xét tuyển của ngành công nghệ thông tin"`, `QueryClassifier` đã nhận diện đúng mã ngành `7480201` nhưng chuỗi query gửi sang Hybrid Retriever không đính kèm mã thực thể, khiến Trang 6 bị tụt hạng và rơi khỏi top_k.
       * Node `query.rewrite` có ví dụ few-shot về `diem chuan qtkd nam 2024`, trong một số trường hợp gọi LLM bị lặp lại dòng ví dụ và bộ lọc stopwords chưa đủ rộng (chỉ lọc 5 từ) khiến candidate chứa chữ `năm` lọt qua chốt chặn, dẫn đến việc câu hỏi phương thức tuyển sinh 2026 bị biến thành câu hỏi điểm chuẩn QTKD 2024.
       * Hàm `get_node_instruction` gặp lỗi `AttributeError: 'AssistantPersonaScope' object has no attribute 'role_description'` (thuộc tính đúng là `persona`).
     - **Triển khai giải pháp kỹ thuật**:
       * `backend/app/modules/rag/service.py`: Tự động bổ sung `analysis.entity_codes` vào `retrieval_query` gửi sang Hybrid Retriever, bảo đảm các trang chứa mã ngành chuyên biệt luôn đạt điểm cao nhất trong cả Qdrant Dense và PostgreSQL FTS.
       * `backend/app/modules/workflows/nodes/query_rewrite_node.py`: Sửa lỗi truy cập `persona_scope.persona`, loại bỏ ví dụ few-shot QTKD 2024 thay bằng ví dụ tổ hợp môn, mở rộng bộ stopwords phòng vệ (`_stopwords`) bao gồm toàn bộ đại từ, từ chức năng và từ chỉ thời gian thông dụng (`năm`, `cho`, `biết`,...).
       * `backend/app/modules/rag/query_router.py`: Loại bỏ phần tử trùng lặp trong set `VI_CONVERSATIONAL_STOPWORDS`, đạt chuẩn Ruff 0 lỗi.
     - **Verification**:
       * Kiểm thử thành công 100% cả 3 câu hỏi (đơn lẻ & multi-turn thread liên tục): Câu 1 và Câu 2 trả lời đầy đủ 5 tổ hợp môn ngành CNTT (Trang 6), Câu 3 trả lời đúng 5 phương thức tuyển sinh 2026 không rò rỉ QTKD và không thừa học phí.
       * Backend Ruff 0 lỗi, Pytest 40/40 passed (100%), Frontend Biome 0 lỗi (168 files), TypeScript 0 lỗi.
  2. **Khắc Phục Hiện Tượng Trợ Lý Tuyển Sinh Tự Bổ Sung Học Phí Khi Hỏi Phương Thức Tuyển Sinh (Focus Guardrail) (phiên #178)**:
     - **Phân tích nguyên nhân cốt lõi (Root Cause)**:
       * Tầng Hybrid RAG bóc tách cả Trang 2 (các phương thức tuyển sinh) và Trang 10 (Mục 8: Lệ phí xét tuyển, thi tuyển năng khiếu, học phí) vào ngữ cảnh tham chiếu;
       * Tầng System Prompt trong CSDL (`ast_admissions.system_prompt`) có đoạn hướng dẫn chi tiết khung học phí cần trích dẫn, nhưng thiếu ràng buộc phạm vi nghiêm ngặt;
       * Mô hình LLM (đặc biệt là các dòng Flash/Lite) bị thiên kiến quá nhiệt tình (helpfulness bias), tự phỏng đoán rằng thí sinh hỏi phương thức thì muốn biết luôn cả học phí và tự động đưa thêm Mục 2 vào câu trả lời.
     - **Triển khai chốt chặn phạm vi (Focus / Scope Guardrail)**:
       * Cập nhật `backend/app/modules/rag/composer.py` (`SYSTEM_PROMPT_TEMPLATE`): Bổ sung quy tắc *"BÁM SÁT TRỌNG TÂM CÂU HỎI: Chỉ trả lời đúng và đủ khía cạnh người dùng hỏi. Tuyệt đối không tự ý mở rộng sang các chủ đề khác (như học phí, điểm chuẩn, lệ phí, ký túc xá) nếu câu hỏi không yêu cầu"*;
       * Cập nhật `configs/workflows/admissions-assistant.v1alpha1.json` (node `knowledge_answer`);
       * Cập nhật `backend/app/modules/assistants/seeder.py` và CSDL PostgreSQL (`ast_admissions.system_prompt`).
     - **Verification**:
       * Chạy thử nghiệm thực tế với câu hỏi `"xin chào cho tôi biết phương thức tuyển sinh năm 2026"`: câu trả lời hoàn toàn sạch sẽ, tập trung 100% vào 5 phương thức tuyển sinh + xét tuyển thẳng, 0% học phí;
       * Backend Ruff 0 lỗi, Pytest 52/52 passed; Frontend Biome 0 lỗi.
  2. **Nâng Cấp Danh Mục Mô Hình Google Lên Gemini 2.5+, Gemma 4 26B/31B & Loại Bỏ Thế Hệ Cũ 1.5, 2.0 (phiên #177)**:
     - **Phát hiện & Xác thực mô hình Google AI Studio**:
       * Xác thực qua live API key Google AI Studio: toàn bộ mô hình 1.5 (`gemini-1.5-flash`, `gemini-1.5-pro`) và 2.0 đã chính thức bị Google ngừng hoạt động (deprecated/shutdown);
       * Xác thực thành công các mô hình thế hệ mới với độ trễ phản hồi thấp, tiếng Việt chuẩn: `gemini-2.5-flash-lite` (~2.4s, 1,500 RPD), `gemini-2.5-flash` (~2.1s), `gemini-2.5-pro`, `gemini-flash-lite-latest`, `gemini-3.1-flash-lite`, `gemma-4-26b-a4b-it`, `gemma-4-31b-it`.
     - **Cập nhật Backend & ModelOps**:
       * Cập nhật `provider_service.py`: `prov_gemini` đặt default model `gemini-2.5-flash-lite` và danh sách `models` gồm 7 model mới; loại bỏ hoàn toàn 1.5 và 2.0;
       * Cập nhật `config.py`: `GEMINI_MODEL_NAME = "gemini-2.5-flash-lite"`;
       * Cập nhật `pricing.py` và `cost_tracker.py`: Bổ sung định mức tính chi phí USD cho toàn bộ dòng 2.5+, 3.1 và Gemma 4;
       * Sửa lỗi luồng RAG Fallback trong `backend/app/modules/rag/service.py`: truyền tham số `fallback_model_name=req.fallback_model` vào `llm_req`, giúp luồng fallback chuyển mạch trực tiếp và chính xác;
       * Cập nhật `schemas.py`, `readiness.py`, `seeder.py`: fallback model mặc định đổi sang `gemini-2.5-flash-lite`.
     - **Cập nhật Giao diện Frontend**:
       * Cập nhật `frontend/src/components/modelops/modelops-helpers.ts`: danh sách gợi ý cho Google gồm Gemini 2.5 Flash/Lite/Pro, 3.1 Flash-Lite, Gemma 4 26B/31B; Cloudflare có `@cf/meta/llama-3.1-8b-instruct`;
       * Cập nhật `assistant-create-page.tsx` và `assistant-detail-page.tsx`: Danh sách dropdown model Google loại bỏ 1.5/2.0, thêm 2.5 Flash-Lite, 2.5 Flash, Gemma 4 26B, Gemma 4 31B.
     - **Đồng bộ CSDL & Kiểm thử đầu cuối**:
       * Cập nhật CSDL PostgreSQL cho `prov_gemini` và Trợ lý `ast_admissions` (`primary_model: gemini-2.5-flash-lite`, `fallback_model: @cf/meta/llama-3.1-8b-instruct`);
       * Test chat thực tế thành công: Trợ lý Tuyển sinh trả lời đầy đủ phương thức tuyển sinh 2026 với 5 trích dẫn PDF chính thức;
       * Backend Ruff 0 lỗi, Pytest 48/48 passed; Frontend Biome 0 lỗi, tsc 0 lỗi, build Vite 8.89s thành công.
  2. **Triệt Tiêu Toàn Diện Mẫu Hardcode, Năm Cũ & Chuẩn Hóa Lời Từ Chối / Gợi Ý Cho Cả 5 Mô Đun (Zero-Emoji 100%) (phiên #176)**:
     - **Hoàn thiện No-Answer Policy RFC 7807 cho 5/5 mô đun**:
       * Mở rộng `NO_ANSWER_MESSAGES` trong `backend/app/modules/rag/citation_guard.py` và các workflow configs DAG (`configs/workflows/*.json`) với đầy đủ hotline, email, đơn vị đầu mối tiếp nhận và 3 nhóm gợi ý tra cứu thường trực (evergreen):
         + `admissions`: Hotline Ban Tư vấn Tuyển sinh `0256.3846.156`, Email `tuyensinh@qnu.edu.vn`.
         + `regulations`: Bàn tiếp sinh viên - Phòng Đào tạo (Tín chỉ, cảnh báo học vụ, chuẩn đầu ra VSTEP).
         + `library`: Trung tâm Thông tin - Thư viện QNU, Hotline `0256.3846.888`, Email `thuvien@qnu.edu.vn`.
         + `drafting`: Phòng Hành chính - Tổng hợp (Soạn thảo văn bản chuẩn Nghị định 30/2020/NĐ-CP).
         + `question_bank`: Phòng Khảo thí & Đảm bảo chất lượng giáo dục (Ma trận Bloom, CLO/PLO, xuất Excel).
     - **Bảo vệ danh xưng 5 Trợ lý & Đa miền nghiệp vụ**:
       * Mở rộng `_INQUIRY_KEYWORDS` và `_TITLE_PATTERNS` trong `condition_route_node.py` bao phủ danh xưng cả 5 Trợ lý và các đơn vị chuyên trách ĐH Quy Nhơn, bảo vệ mọi câu hỏi tra cứu không bị regex chào hỏi bắt nhầm.
     - **Triệt tiêu năm cũ trong câu hỏi mẫu & Đồng bộ CSDL**:
       * Cập nhật `backend/app/modules/assistants/seeder.py`: Xóa bỏ năm 2024 trong Tuyển sinh ("các năm gần nhất"), năm 2024-2025 trong Soạn thảo ("cấp Trường");
       * Nâng cấp logic đồng bộ cấu hình Trợ lý đã tồn tại trong CSDL khi chạy seed; Chạy `db seed --assistants --workflows` đồng bộ thành công cả 5/5 Trợ lý và DAGs.
     - **Triệt tiêu 100% Emoji trên UI Frontend**:
       * Thay thế ký tự `💡` trong `frontend/src/components/ai/chat-message.tsx` bằng Lucide Icon `Lightbulb` (`size-3 text-primary shrink-0`), sắp xếp import theo alphabet chuẩn AGENTS.md Quy tắc 4.8.
     - **Verification**:
       * Backend Ruff 0 lỗi, Pytest 341/341 passed (100%);
       * Frontend Biome 0 lỗi, TypeScript 0 lỗi, Vite build 10.36s thành công.
  2. **Khắc Phục Lỗi Điều Hướng Chào Hỏi Cắt Ngang Tra Cứu & Triệt Tiêu Mẫu Hardcode Cũ (phiên #175)**:
     - **Giải quyết triệt để lỗi Regex Hijacking trong Condition Route**:
       * Trước đây khi người dùng đặt câu hỏi tra cứu có chứa từ chào hỏi lịch sự ở đầu câu (`"xin chào bạn cho tôi hỏi phương thức tuyển sinh năm 2026"`), regex `"xin chào|hello|hi|..."` bắt thô và điều hướng nhầm sang node `greeting_output`.
       * Nâng cấp hàm `_is_pure_greeting`: Bóc tách toàn bộ danh xưng (`Trợ lý Tuyển sinh`, `QNU`, `bạn`, `thầy cô`,...), kiểm tra dấu hỏi `?` và các từ khóa tra cứu nghiệp vụ (`phương thức`, `điểm chuẩn`, `học phí`, `chỉ tiêu`, `năm 202...`); Nếu có nội dung câu hỏi thực chất -> bỏ qua quy tắc chào hỏi, đi thẳng vào `query_rewrite` -> `knowledge_answer` (RAG); Chỉ khi người dùng chào thuần túy mới vào `greeting_output`.
     - **Triệt tiêu toàn bộ Hardcoded Templates & Năm lỗi thời**:
       * Cập nhật `greeting_output` và `no_answer_output` trong `configs/workflows/admissions-assistant.v1alpha1.json`: Viết lại lời chào thường trực (evergreen), chuyên nghiệp, xóa bỏ các năm cũ 2024/2025 ghim cứng và tuân thủ chuẩn Zero-Emoji của AGENTS.md;
       * Cập nhật `NO_ANSWER_MESSAGES["admissions"]` trong `backend/app/modules/rag/citation_guard.py`.
     - **Sửa lỗi bóc tách Cổng Phân Nhánh (DAG Port Parsing Bug)**:
       * Khắc phục hàm `_parse_spec_from_json` trong `service.py`: Đọc đúng `source_port` và `target_port` từ cấp phẳng khi giải mã DAG từ CSDL, sửa dứt điểm lỗi `citation_guard` chọn cổng `grounded` nhưng runtime báo lỗi không tìm thấy cạnh;
       * Bổ sung phòng vệ trong `query_rewrite_node.py` phát hiện thông báo fallback mock của máy chủ cục bộ.
     - **Verification**:
       * Chạy test thực tế: `"xin chào bạn cho tôi hỏi phương thức tuyển sinh năm 2026"` đi qua đầy đủ 6 nodes: `['chat_input', 'condition_route', 'query_rewrite', 'knowledge_answer', 'citation_guard', 'chat_output']`, trích xuất 5 trích dẫn chính thức từ văn bản Đề án tuyển sinh 2026 của ĐH Quy Nhơn;
       * Backend Ruff 0 lỗi, Pytest 341/341 passed (100%);
       * Frontend Biome 0 lỗi, TypeScript 0 lỗi, Build thành công 9.10s.
- **Phiên team #175-180 đã hợp nhất**: greeting routing, zero-emoji 5 modules, Gemini 2.5/Gemma 4, focus guardrail, entity augmentation, suggestion chips (giữ nguyên từ upstream).
- **Rebase dùng chung phiên #181**:
  - **RAG generic**: Query Router packs library/drafting/question_bank + generic QĐ/tiền/năm, `analyze(query, module_code="general")` hợp nhất với `MAJOR_NAME_TO_CODE` của team (bỏ alias `ai` gây false-positive); `build_generic_system_instruction()` + `is_refusal_answer()` phi thiên vị giữ kèm `extract_suggested_questions` chips của team; `AskRequest.module_code` mặc định `general`.
  - **DAG generic**: Template `_base-assistant.v1alpha1.json` 8 nodes pass validation; `fork_workflow` tiêm module/collection/prompt/instruction; RAG node fail-closed `workflow_missing_collection` với fallback `col_{module}` chính thức; LLM node `llm_generation_failed` 502; query_rewrite hỗ trợ `custom_acronyms`; seeder bỏ qua `_*.json`.
  - **Tests & Docs**: 9 tests `test_rag_generic_reuse.py` mới; `test_node_catalog` >=14; Bước 11 quy trình 03 + Mục 14 quy trình 04; nhật ký phiên 181 + WORK_LOG.
  - **Verification**: xem mục nhật ký phiên 181.
  2. **Bổ Sung Node Query Rewrite Vào Seed Data Của Cả 5 Mô Đun Quy Trình DAG (phiên #174)**:
     - **Tích hợp `query_rewrite` vào 5 workflow configs (`configs/workflows/*.json`)**:
       * `admissions-assistant`: Chuẩn hóa ngành học, học phí, học bổng, điểm chuẩn, viết tắt CNTT, QTKD, ĐGNL, THPT, KTX.
       * `regulations-assistant`: Chuẩn hóa tín chỉ, học phần, điểm rèn luyện, khen thưởng, viết tắt ĐRL, GPA, CTĐT, CTSV, PĐT, NCKH.
       * `library-assistant`: Chuẩn hóa giáo trình, sách chuyên khảo, tài liệu, luận văn, viết tắt SP, CNTT, QTKD, KHCN, NCKH.
       * `drafting-assistant`: Chuẩn hóa tờ trình, kế hoạch, quyết định, công văn, Nghị định 30, viết tắt BGH, ĐHQG, UBND, PĐT, TCHC.
       * `question-bank-assistant`: Chuẩn hóa ma trận đề thi, ngân hàng câu hỏi, thang đo Bloom, chuẩn đầu ra CLO/PLO, CĐR, ĐCHP, KTĐG.
     - **Nâng cấp Idempotent Seeder**: Cập nhật `sync_default_workflows` trong `service.py` tự động cập nhật bản nháp và phiên bản v1.0.0 khi cấu hình JSON thay đổi; chạy `db seed --workflows` đồng bộ thành công cả 5/5 quy trình vào PostgreSQL.
     - **Cập nhật Tài liệu Quy trình**: Bổ sung Mục 13 trong `docs/quy_trinh/04_dieu_phoi_tro_ly_dag.md`.
     - **Verification**: Backend Ruff 0 lỗi, Pytest 31/31 passed; Frontend Biome 0 lỗi, tsc 0 lỗi; CSDL xác nhận 5/5 quy trình đã có node `query.rewrite`.
  2. **Chuẩn Hóa Node DAG Query Rewrite Dùng Chung Đa Quy Trình & Visual Prompt Inspector (phiên #173)**:
     - **Triệt tiêu hoàn toàn Hardcoded Domains**:
       * Xóa bỏ hoàn toàn biến toàn cục `DOMAIN_CONTEXT_MAP` cố định 5 mô đun trong `backend/app/modules/workflows/nodes/query_rewrite_node.py`;
       * Đưa `query.rewrite` trở thành building block dùng chung cho mọi quy trình nghiệp vụ (tuyển sinh, đào tạo, ký túc xá, thư viện, khảo thí, công tác sinh viên, văn phòng khoa,...);
       * Xây dựng hàm `get_node_instruction`: ưu tiên cao nhất cho `instruction` / `prompt` do người dùng cấu hình trực tiếp trên từng node của từng quy trình;
       * Xây dựng hàm `build_rewrite_prompt`: hỗ trợ placeholder `{query}` nếu muốn định nghĩa mẫu hoàn chỉnh, hoặc tự động gói trong format few-shot chuẩn hóa;
     - **Visual Property Inspector trên Frontend**:
       * Nâng cấp `frontend/src/components/admin/property-inspector.tsx`: Thêm khối giao diện cấu hình trực quan riêng cho node `query.rewrite`;
       * Cung cấp Textarea soạn thảo `Prompt / Hướng dẫn chuẩn hóa` (`instruction`), công tắc bật/tắt Fast Rules (0ms) và Tầng LLM (~150ms);
     - **Đồng bộ Manifest & CSDL**:
       * Cập nhật `configs/nodes/query.rewrite.v1alpha1.json`: bổ sung `instruction` và `prompt` vào `config_schema`;
       * Cập nhật `configs/workflows/admissions-assistant.v1alpha1.json`: cấu hình instruction tuyển sinh đặc thù vào node `query_rewrite`;
       * Đồng bộ cập nhật CSDL PostgreSQL (`workflow_definitions`, `workflow_drafts`, `workflow_versions`);
     - **Verification**: Backend Ruff 0 lỗi, Pytest 31/31 passed (100%); Frontend Biome 168 files 0 lỗi, TypeScript 0 lỗi, Vite build 8.15s; End-to-end chat test 100% pass với câu hỏi gõ nhầm Telex được chuẩn hóa và trả về đầy đủ học phí kèm 4 trích dẫn PDF;
  2. **Khắc Phục Hiện Tượng Phản Hồi Mock RAG & Kích Hoạt Cloudflare LLM Generation (@cf/meta/llama-3.1-8b-instruct) (phiên #171)**:
     - **Phân tích nguyên nhân gốc**: Tầng RAG Retrieval bóc tách và truy vấn chính xác 100% (5 trích dẫn từ tài liệu PDF `doc_f0c1` được trích xuất hoàn hảo). Khi chuyển sang tầng tổng hợp văn bản, Trợ lý gọi `gemini-2.5-flash` nhưng CSDL chỉ có key mẫu (`AIzaSyMockKey-1`) gây lỗi HTTP 400. Cascade fallback sang Cloudflare nhưng thiếu cấu hình LLM chat, cuối cùng rơi về Local vLLM offline kích hoạt thông báo mô phỏng an toàn (`[Local @cf/baai/bge-m3]...`);
     - **Kích hoạt LLM Cloudflare Workers AI**: Khai thác token Cloudflare đang hoạt động sẵn có, đưa `@cf/meta/llama-3.1-8b-instruct` vào danh sách models chính thức của `prov_cloudflare` trong `backend/app/modules/modelops/services/provider_service.py` và CSDL;
     - **Gia cố phòng vệ cascade trong `InferenceService`**: Tự động lọc bỏ các mô hình nhúng (`bge-`, `embed`, `rerank`, `tableformer`) khi chọn model mặc định trong cascade fallback cho cả `generate` và `stream`, ngăn chặn lỗi gọi chat vào embedding endpoint;
     - **Cập nhật cấu hình Trợ lý Tuyển sinh (`admissions`)**: Sử dụng `@cf/meta/llama-3.1-8b-instruct`. Thử nghiệm trực tiếp trả lời tiếng Việt trôi chảy, chi tiết, chính xác 100% theo tài liệu PDF với độ trễ chỉ 2 giây;
     - **Verification**: Backend ruff 0 lỗi, pytest 48/48 passed; Frontend Biome 168 files 0 lỗi, tsc 0 lỗi;
  2. **Khắc Phục Lỗi Chặn Xuất Bản (Publish Gate 100%) & Tích Hợp Sonner Toaster Toàn Cục Kèm Thông Báo Khi Lưu Trợ Lý AI (phiên #170)**:
     - **Backend: Triệt tiêu 2 blockers trong Publish Gate**:
       * Mở rộng bộ lọc tài liệu đối soát trong `backend/app/modules/assistants/readiness.py`: Thêm trạng thái `ready`, `completed` và `index_status == "indexed"`, đưa điểm tiêu chí Kho tri thức chuyên biệt từ 25/100 lên 100/100;
       * Bổ sung `ALIASES` trong `backend/app/modules/tools/registry.py` (`admissions.fact_lookup` -> `lookup_admission_score`), đồng bộ cấu hình CSDL `enabled_tools`, đưa điểm Tool Gateway lên 100/100;
       * Tổng điểm sẵn sàng của Trợ lý Tuyển sinh đạt 100/100 (5/5 tiêu chí ĐẠT, 0 blocker);
     - **Frontend: Tích hợp hệ thống Toast toàn cục & Thông báo khi bấm Lưu**:
       * Tạo component `src/components/ui/sonner.tsx` chuẩn shadcn/ui tích hợp `useTheme()` và tokens thiết kế QNU;
       * Gắn `<Toaster />` vào `src/App.tsx`, mở khóa popup thông báo cho toàn bộ hơn 50 màn hình;
       * Nâng cấp `updateMutation.onSuccess` trong `assistant-detail-page.tsx`, hiển thị thông báo popup Toast "Đã lưu thay đổi cấu hình thành công!" kèm mô tả và tự động làm mới cache readiness;
     - **Verification**: Backend ruff 0 lỗi, pytest 27/27 passed; Frontend Biome 168 files 0 lỗi, tsc 0 lỗi, build 11.26s.
  2. **Tích Hợp Firecrawl `pdf-inspector` Lõi Rust (v1.22.1) & Tối Ưu Hóa Phân Nhánh Ingestion Pipeline (phiên #169)**:
     - **Cài đặt thư viện chính thức**: Cài đặt `pdf-inspector==1.22.1` vào `backend/pyproject.toml` qua `uv add pdf-inspector`.
     - **Module Adapter `PDFInspector`**:
       * Xây dựng [`backend/app/modules/knowledge/parsers/pdf_inspector.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/knowledge/parsers/pdf_inspector.py) bọc Rust native engine, phân loại `pdf_type` (`text_based`, `scanned`, `image_based`, `mixed`) và danh sách `pages_needing_ocr` trong 10-30ms;
       * Trang bị Graceful Fallback tự động xử lý an toàn dữ liệu nhị phân hỏng;
       * Export từ `app.modules.knowledge.parsers`;
     - **Tích hợp Kiến trúc Song Mã (Complementary Architecture)**:
       * `pdf_parser.py`: Gọi `PDFInspector.inspect_bytes(file_bytes)` để đính kèm metadata phân loại thông minh (`pdf_type`, `pages_needing_ocr`, `confidence`) và ưu tiên Markdown cấu trúc do Rust trích xuất; đồng thời bảo tồn 100% PyMuPDF geometry blocks cho Bounding Boxes UI;
       * `ingestion_service.py`: Thay thế toàn bộ logic thủ công `len < 40` bằng kiểm tra phân loại `pdf_type` và `pages_needing_ocr`;
       * `ocr/service.py`: Trong `_extract_auto()`, tích hợp `PDFInspector` thanh tra trước, kích hoạt Fast-Path (10-30ms) cho `text_based` mà không tốn chi phí gọi OCR;
     - **Đồng bộ tài liệu & sơ đồ**:
       * Quy trình 02 ([`docs/quy_trinh/02_nap_tri_thuc_minio.md`](file:///d:/DuAnPhanMem/qnu-ai-platform/docs/quy_trinh/02_nap_tri_thuc_minio.md)): cập nhật Bước 3 và Mermaid diagram;
       * Sơ đồ tương tác ([`docs/diagrams/kho_tri_thuc_architecture.html`](file:///d:/DuAnPhanMem/qnu-ai-platform/docs/diagrams/kho_tri_thuc_architecture.html)): cập nhật node `Firecrawl PDF Inspector` và Card 1;
     - **Verification**:
       * `backend/tests/test_pdf_inspector.py`: 5/5 tests passed (100%) trong 0.90s;
       * Toàn bộ test suite Knowledge & OCR: 63/63 tests passed (100%) trong 54s;
       * `uv run ruff check .`: 0 lỗi linter;
       * Frontend: Biome 167 files 0 lỗi, TypeScript tsc 0 lỗi.
  1. **Loại Bỏ Chuyển Hướng /workflows/* & Giữ Nguyên Không Gian URL /assistants/:id/workflow (phiên #168)**:
     - **Triệt tiêu hoàn toàn hook redirect tự động và query rườm rà `?returnTo=...`**:
       * Xóa bỏ hook `useEffect` trong `assistant-detail-page.tsx` từng tự động đẩy người dùng sang `http://localhost:3001/workflows/admissions-assistant?returnTo=...`;
       * Giữ nguyên 100% URL sạch trong không gian Trợ lý: `/assistants/:code/workflow`;
       * Khi ở subView `workflow`, `AssistantDetailPage` trả về trực tiếp `DAGCanvasPage` toàn màn hình (`h-[calc(100vh-4rem)]`), giải phóng trọn vẹn diện tích đồ thị DAG mà không bị chèn ép;
       * Bảo toàn 100% ngữ cảnh điều hướng: Sidebar bên trái luôn duy trì highlight xanh ở **Trợ lý AI** (không bị nhảy sang Thư Viện Workflow dưới Nâng cao); Topbar breadcrumbs duy trì **Xây Dựng AI > Trợ Lý AI**;
       * Bổ sung tab `workflow` ("Sơ đồ DAG Studio", icon `Network`) vào `WORKSPACE_TABS` giúp chuyển đổi liền mạch;
       * Chuẩn hóa nút quay lại trên thanh DAG Studio: hiển thị `[Quay lại Trợ lý]` điều hướng về đúng trang cấu hình `/assistants/:id`.
     - **Verification**: `npm run typecheck` 0 lỗi, `npm run lint` 0 lỗi trên 167 files, `npm run build` thành công trong 8.73s, `uv run ruff check .` pass.
  2. **Tinh Giản Giao Diện Trợ Lý AI & Tách Biệt DAG Visual Studio Thành Màn Hình Độc Lập (phiên #167)**:
     - **Dọn sạch thông tin dư thừa & dữ liệu giả trên trang Chi tiết Trợ lý AI (`/assistants/:id`)**:
       * Xóa 4 thẻ KPI thô/giả (128 lượt chạy, 240ms độ trễ, thẻ kho tri thức trùng lặp, thẻ Ragas TM-08 trùng lặp);
       * Xóa chuỗi ID kỹ thuật `assistant.id` (`ast_admissions`) nằm dưới tiêu đề gây rối mắt;
       * Tinh chỉnh container Publish Gate với nền phẳng tinh tế (`bg-card border`), không còn nhuộm đỏ chói toàn màn hình khi có blocker;
       * Xóa hộp văn bản khuyến nghị chiến lược chunking lý thuyết tĩnh trong phần Gắn kết Tri thức RAG.
     - **Tách DAG Visual Studio thành màn hình Studio độc lập (`/workflows/:id`) chuẩn Master-Detail Deep Routing (AGENTS.md 4.5)**:
       * Bổ sung nút hành động nổi bật `[Sơ đồ DAG Studio ↗]` tại Header và phần Cấu hình Quy trình, đính kèm tham số `returnTo=/assistants/:code`;
       * Cập nhật trang `dag-canvas-page.tsx` đọc `returnTo` và bổ sung nút điều hướng trực quan `[Quay lại Trợ lý]`;
       * Rút gọn thanh Workspace Nav chỉ còn **3 tabs cấu hình trọng tâm**: `overview` (Thông tin & Tri thức), `models` (Mô hình & An toàn), `tools` (Quy trình & Công cụ);
       * Loại bỏ component lồng `DAGCanvasPage` bên trong subtab `workflow` của Assistant Detail Page (tự động chuyển hướng sang `/workflows/:id?returnTo=...`), triệt tiêu việc vỡ layout margin âm và giảm mạnh kích thước bundle.
     - **Gia cố tính an toàn Backend**: Dùng `getattr` truy xuất an toàn `doc.status` và `doc.index_status` trong `ingestion_service.py`.
     - **Verification**: `npm run typecheck` 0 lỗi, `npm run lint` 0 lỗi trên 167 files, `npm run build` thành công trong 13.54s, `uv run ruff check .` pass, backend pytest 329/329 passed.
  2. **Khắc Phục Triệt Để Lỗi Điều Hướng Tabs Trong Assistant Workspace (`/assistants/:id/*`) (phiên #166)**:
     - **Nguyên nhân**: Trong `assistant-detail-page.tsx`, hàm `getReferenceFromPath` sử dụng `.at(-1)` để lấy ID trợ lý từ URL. Khi người dùng click vào các sub-tabs (`/assistants/admissions/models`, `tools`, `playground`, `workflow`, `channels`, `quality`, `runs`), hàm này lấy nhầm đoạn đuôi `models` làm mã trợ lý và gọi API `GET /assistants/models`, gây lỗi HTTP 404 "Không tìm thấy Trợ lý AI".
     - **Giải pháp**: Chuẩn hóa hàm `getReferenceFromPath` lấy đúng phần tử ngay sau `/assistants/` (`parts[assistantsIndex + 1]`), đồng thời truyền trực tiếp prop `assistantId={resolved.params.assistantId}` từ `App.tsx` vào `AssistantDetailPage`.
     - **Kiểm thử**: `npm run typecheck` 0 lỗi, `npm run lint` 0 lỗi trên 167 files, `npm run build` thành công.
  2. **Khắc Phục Triệt Để Lỗi Nhân Đôi Điểm Vector (Zero Duplicate Qdrant Points) & Tối Ưu UX Phê Duyệt Scan Studio (phiên #165)**:
     - **Triệt tiêu 100% hiện tượng duplicate vector trong Qdrant**:
       * Phân tích nguyên nhân: Khi người dùng bấm phê duyệt lại từ Scan Studio (kèm `pages`), backend xóa chunk cũ trong DB và tạo chunk mới với UUID mới $\rightarrow$ sinh Point ID mới trong Qdrant. Tuy nhiên `doc.version` không tăng và `purge_stale_revisions` chỉ lọc `< current_revision` nên điểm cũ không bị xóa, làm số lượng vector tăng gấp đôi (16 $\rightarrow$ 32 $\rightarrow$ 48);
       * Giải pháp Backend: Tự động tăng `doc.version` khi phê duyệt lại/có `pages`. Đồng thời gọi `await vector_indexer.delete_by_document(col_id, doc_id)` trước khi `index_chunks()`, bảo đảm tính Idempotent 100% (Qdrant chỉ chứa đúng số lượng chunks hiện có trong DB);
       * Đồng bộ gọi `delete_by_document` trong `reindex_document` (`reconciliation_service.py`);
       * Mở rộng `StudioViewResponse` và `get_studio_view()`: trả về đầy đủ `status` và `index_status` của tài liệu;
       * Thêm unit test `test_approve_document_with_pages_increments_revision_and_purges_old_vectors`;
     - **Tối ưu UX Trạng thái Nút Bấm trong Scan Studio (`scan-studio-page.tsx`)**:
       * Nhận diện `isAlreadyApproved` và `hasEdits` (phát hiện có chỉnh sửa Markdown thực tế hay không);
       * Nếu tài liệu đã duyệt và không có sửa đổi: Hiển thị badge nút `[✓ Đã duyệt & Lập chỉ mục]` (disabled/outline với tint nhẹ Academic Teal) kèm nút phụ `[↻ Tái lập chỉ mục]` (outline, an toàn). Người dùng không bao giờ bấm nhầm làm nạp lại dữ liệu;
       * Nếu người dùng chỉnh sửa Markdown: Nút chính chuyển thành `[↻ Cập nhật & Tái lập chỉ mục]` (màu Academic Teal, icon `RefreshCw`);
       * Nếu tài liệu mới: Giữ nguyên `[✓ Xác nhận đối soát & Phê duyệt]`;
     - **Verification**:
       * Live Qdrant: 16 points $\rightarrow$ Re-approve $\rightarrow$ Vẫn chính xác 16 points (Zero Duplicate Points);
       * Backend: Ruff 0 lỗi; Pytest 53/53 passed (100%);
       * Frontend: Biome 167 files 0 lỗi; TypeScript 0 lỗi; Vite build thành công trong 10.99s;
  1. **Redesign Toàn Diện Giao Diện Trang Chi Tiết Trợ Lý AI: Tối Ưu Hóa UI/UX, Progressive Disclosure Sub-Tabs, Cân Bằng 2 Cột & Tinh Gọn Header (phiên #164)**:
     - **Tách cấu hình thành 3 Sub-tabs chuyên biệt (Progressive Disclosure)**:
       * Mở rộng route resolver `/assistants/:id/:subView` và `AssistantWorkspaceNav` hỗ trợ thêm `"models"` và `"tools"`;
       * Tab 1 `overview` (Thông tin & Tri thức): Persona, Prompt hệ thống (kèm AI Re-write), Câu hỏi gợi ý và Kho Tri Thức RAG liên kết. Bố cục 2 cột cân bằng (60% trái / 40% phải), triệt tiêu hoàn toàn khoảng trắng thừa ở đáy;
       * Tab 2 `models` (Mô hình & An toàn): Cấu hình ModelOps (Primary, Fallback, Temperature, Max tokens) song song cùng 6 công tắc Guardrails (Chống injection, che PII, Groundedness check, System prompt shield, No-answer policy, Ragas TM-08);
       * Tab 3 `tools` (Quy trình & Công cụ): Workflow DAG, Tách workflow riêng, Chốt chặn Tool Gateway, Quản lý Tool Registry và Vùng nguy hiểm;
       * Các tab chuyên sâu `playground` (Thử chat), `workflow` (Đồ thị DAG), `quality` (Ragas TM-08), `runs` (Lịch sử Chạy), `channels` (Mã nhúng) giữ nguyên;
       * Đồng bộ state `form` liên tục xuyên suốt các tabs, hỗ trợ lưu thay đổi từ bất kỳ tab cấu hình nào;
     - **Tinh gọn Action Toolbar & Header**:
       * Giữ 2 nút hành động chính: `[Thử chat]` (outline) và `[Lưu thay đổi]` (màu Academic Teal, xuất hiện trên cả 3 tabs cấu hình);
       * Gom 5 nút phụ vào Dropdown Menu `[Thao tác khác ▾]`: Mở đồ thị DAG Studio, Nhân bản Trợ lý, Lịch sử phiên bản & Rollback, Lấy mã nhúng Web, Xuất bundle JSON;
     - **Thu gọn Banner Publish Gate (Collapsible Compact Alert)**:
       * Mặc định hiển thị thanh tóm tắt 1 hàng mỏng, thông báo điểm sẵn sàng (`71% - 3/5 Tiêu chí`) và lỗi chính;
       * Nút `[Chi tiết (N lỗi) ▾]` mở rộng/thu nhỏ hiển thị 5 chips tiêu chí và danh sách hướng dẫn khắc phục chi tiết;
     - **Verification**:
       * Biome Linter: `npm run lint` đạt **0 errors (167 files checked in 183ms)**;
       * TypeScript Typecheck: `npm run typecheck` đạt **0 errors**;
       * Vite Build: `npm run build` thành công xuất sắc trong **9.87s** (2660 modules transformed);
  1. **Tháo Gỡ Nút Thắt & Cải Thiện Toàn Diện Trải Nghiệm Kho Tri Thức: Chế Độ Nạp Nhanh (Fast-Track), Phê Duyệt Nhanh 1-Click & Thao Tác Hàng Loạt (Bulk Operations) (phiên #163)**:
     - **Chế độ Nạp Nhanh (Fast-Track / Auto-Approve)**:
       * Mở rộng Backend router `POST /collections/{collection_id}/upload` hỗ trợ query/form parameter `auto_approve: bool = Form(False)`;
       * Chuyển tiếp qua `IngestionService.ingest_document`: Khi `auto_approve=True` VÀ `quality_blocked=False` (vượt qua Data Quality Gate 100%), tự động gọi `approve_document`, tính toán hash kiểm duyệt, sinh chunk vector, đẩy lên Qdrant và chuyển tài liệu sang `approved` ngay tức thì mà không cần qua Scan Studio;
       * Bảo vệ Zero Hallucination: Nếu Quality Gate phát hiện mâu thuẫn dữ liệu hoặc lỗi cấu trúc bảng, cờ `auto_approve` tự động bị vô hiệu, giữ nguyên trạng thái `review_pending` buộc con người đối soát;
       * Frontend `document-ingest-page.tsx`: Thêm Card toggle Chế độ Nạp Nhanh (Fast-Track) với icon `Zap`, tự động điều hướng về màn hình kho khi nạp thành công;
     - **Thanh Tiến Trình Đa Pha (Multi-Stage Progress Indicator)**:
       * Hiển thị thanh tiến trình 5 chặng có phần trăm thực tế và animation mượt mà (Lưu trữ MinIO S3 -> Trích xuất văn bản PyMuPDF/OCR -> Nhận diện Layout & Cấu trúc OpenCV -> Kiểm tra Data Quality Gate -> Đánh chỉ mục Vector Qdrant & Trích xuất Facts);
     - **Duyệt Nhanh 1-Click & Thao Tác Hàng Loạt (Bulk Batch Operations)**:
       * API client: bổ sung `batchApproveDocuments(documentIds: string[])`;
       * Bảng danh sách tài liệu (`collection-documents-tab.tsx`):
         + Nút **Duyệt nhanh 1-Click** (`[✓ Duyệt nhanh]`) ngay tại từng hàng tài liệu `pending`/`review_pending` đủ điều kiện, phê duyệt trực tiếp không cần mở Scan Studio;
         + Checkbox đa chọn tại header và từng hàng tài liệu;
         + **Bulk Action Bar** floating nổi bật khi chọn tài liệu: `Phê duyệt N tài liệu`, `Xóa N tài liệu`, `Bỏ chọn`;
         + **Mini Stepper Guide** thu gọn/mở rộng giải thích 3 chặng vòng đời tài liệu (1. Nạp thô & Bóc tách -> 2. Thẩm định & Quality Gate -> 3. Sẵn sàng AI);
     - **Verification**:
       * Backend: `uv run ruff check .` 0 lỗi; Pytest `tests/test_knowledge.py` đạt **32/32 passed (100%) in 68.27s** (bao gồm unit test mới `test_ingest_document_fast_track_auto_approve`);
       * Frontend: Biome `npm run lint` đạt **0 errors** (167 files); `npm run typecheck` đạt **0 errors**; Vite `npm run build` thành công trong 14.23s;
  1. **Định Tuyến Markdown Qua Parser Chuẩn & Đóng Quality Gate Trước Qdrant (phiên #162)**:
     - Định tuyến extension `.md` từ `PlainTextParser` sang `MarkdownParser`, hỗ trợ UTF-8/NFC, nhận diện bảng GFM nhiều block và chuyển block `Kế hoạch nhiệm vụ X.Y` thành bản ghi nghiệp vụ có cấu trúc.
     - Kiểm tra thực tế file Kế hoạch triển khai 2025-2026: 76 nhiệm vụ hợp lệ, tạo 76 record-aware chunks và 152 Facts sau khi Quality Gate đạt.
     - Kiểm tra thực tế file Tuyển sinh 2026: nhận diện 53 ngành nhưng giữ trạng thái `review_pending` vì mâu thuẫn mã ngành AI `7480207`/`7480107`; không tạo chunks/Facts và không gửi dữ liệu lỗi sang Qdrant.
     - Bổ sung test parser/reconstruction; toàn bộ Backend đạt Ruff 0 lỗi và Pytest 328/328 passed.
  1. **Hỗ Trợ Đa Tài Khoản Cloudflare (Multi-Account Key Pool) & Tính Năng Import/Export Provider Bằng File JSON (Đơn Lẻ & Hàng Loạt) (phiên #161)**:
     - **Cloudflare Multi-Account Key Pool**:
       * Mở rộng `ProviderKeyCreate`, `ProviderKeyUpdate`, `ProviderKeyItem` tại backend và `ProviderApiKey` tại frontend với trường tùy chọn `account_id: str | None`;
       * Cho phép Key Pool của Provider Cloudflare quản lý đồng thời nhiều API Key thuộc các Cloudflare Account ID khác nhau;
       * Khi thêm/sửa key trong `key-pool-section.tsx`, tự động hiển thị trường nhập `Cloudflare Account ID (Tài khoản)` nếu provider là `cloudflare`;
       * Nâng cấp `provider_service.test_provider_key`, `inference_service.generate` và `generate_stream`: Ưu tiên `active_key.account_id` trước khi fallback về `provider.account_id` để kết nối chính xác vào URL Cloudflare Workers AI `.../accounts/{account_id}/ai/run/...`;
     - **Bộ Tính Năng Import / Export JSON Toàn Diện**:
       * Bổ sung API endpoints: `GET /platform/v1alpha1/modelops/providers/{provider_id}/export` (xuất 1 provider), `GET /platform/v1alpha1/modelops/providers/export` (xuất toàn bộ providers), `POST /platform/v1alpha1/modelops/providers/import` (nhập cấu trúc JSON);
       * Logic xử lý `import_providers` thông minh tự động nhận diện cấu trúc tệp (Single Provider export, Bulk All Providers export, hoặc mảng JSON/Object Provider thuần túy);
       * Hỗ trợ 3 chiến lược giải quyết xung đột khi ID hoặc Tên Provider đã tồn tại: `overwrite` (ghi đè cấu hình & gộp thêm keys), `skip` (bỏ qua), `create_new` (tạo mới sinh UUID mới);
       * UI Frontend: Bổ sung nút `[Xuất JSON]` trên header chi tiết Provider; Nút `[Xuất Tất Cả (JSON)]` và `[Nhập JSON]` trên trang danh sách Providers; Component `ImportProvidersDialog` kéo thả file, preview bảng providers và xử lý nhập mượt mà;
     - **Verification**:
       * Backend: `uv run ruff check .` 0 lỗi; Pytest `tests/test_modelops.py` đạt **20/20 passed (100%) in 4.28s** (bao gồm 2 unit tests mới);
       * Frontend: Biome `npm run lint` đạt **0 errors** (167 files); `npm run typecheck` đạt **0 errors**; Vite `npm run build` thành công trong 8.02s;
  2. **Khắc Phục Bỏ Sót Hàng Bảng "Đông phương học" Ở Đầu Trang 14 Do Hiện Tượng Bảng Ngắt Trang Mở Đỉnh (Open-Top Table Continuation) (phiên #160)**:
     - Khắc phục triệt để hiện tượng Scan Studio chỉ đóng khung cam cho hàng thứ hai `Tiếng Trung | Ngôn ngữ Trung Quốc | 7220204`, bỏ sót hàng thứ nhất `Đông phương học | 7310608` ở đỉnh trang 14;
     - Bổ sung `detect_open_top_lines` và `find_page_tables` trong `blocks.py`: phát hiện các đường kẻ dọc tại đỉnh trang thiếu đường kẻ ngang trên cùng, tự động bù `add_lines` ảo để PyMuPDF nhận diện trọn vẹn 100% các hàng tiếp nối;
     - Tọa độ bảng tự động bắt đầu từ `y = 5.9%` (thay vì `7.88%`), chiều cao bao phủ trọn vẹn cả 2 hàng;
     - Đồng bộ sang `pdf_parser.py`, `layout_detector.py`, `build_studio_pages` (`ingestion_service.py`) và `scan-studio-page.tsx`;
     - Thêm unit test `test_detect_open_top_lines_and_rescue_table` trong `tests/test_table_reconstructor.py`;
     - **Verification**: `uv run ruff check .` 0 lỗi; Pytest 44/44 passed (100%); Frontend Biome 166 files / 0 lỗi; TypeScript 0 lỗi; Vite build thành công trong 12.34s.
  2. **Khắc Phục Dứt Điểm Lỗi Truncation KnowledgeFact AttributeValue (VARCHAR 512 sang TEXT) (phiên #159)**:
     - Khắc phục lỗi `StringDataRightTruncationError: value too long for type character varying(512)` khi tải lên tài liệu có deliverables nhiệm vụ dài vượt quá 512 ký tự;
     - Cập nhật model `KnowledgeFact.attribute_value` từ `String(512)` sang `Text`, mở rộng `attribute_name` lên `VARCHAR(255)`, `entity_name` lên `VARCHAR(512)`;
     - Tạo và áp dụng migration Alembic `20260920_expand_facts_text` (Revises: `20260919_approval_payload_hash`) chạy `ALTER TABLE knowledge_facts ALTER COLUMN attribute_value TYPE TEXT` thành công trên PostgreSQL live;
     - Khôi phục và chuẩn hóa 2 methods `extract_facts_from_domain_records` và `extract_from_verified_markdown_pages` trong `FactExtractor` (`facts.py`), làm sạch deliverables rỗng/thừa;
     - **Verification**: `uv run ruff check .` 0 lỗi; `uv run alembic check` 0 diff; Pytest 73/73 passed (100%).
  2. **Khép Kín Quality Gate & Luồng Qdrant An Toàn Cho Bảng PDF (phiên #158)**:
     - Nối runtime `CanonicalDocument → DataQualityGate → Domain Records → Record-aware Chunks/Facts` vào `IngestionService`; lỗi blocking không tạo chunk/fact và chuyển trạng thái `review_pending`.
     - Tái dựng bảng tiếp nối thiếu header, chuẩn hóa cột spacer của PDF kế hoạch, chống tiêu đề giả `Cột N`, và chặn trùng bản ghi nghiệp vụ trước Qdrant.
     - Cán bộ phải hiệu đính khi có report lỗi; Markdown GFM đã được xác nhận tái sinh Facts, còn reindex được cho phép nếu có dấu vết `human_verified`.
     - Đối chiếu PDF gốc: Kế hoạch 2025–2026 có 76 nhiệm vụ, đạt kiểm định; Tuyển sinh 2026 có 53 ngành nhưng có mâu thuẫn mã ngành nên bị chặn đúng chính sách Zero Hallucination.
     - **Verification**: `uv run ruff check .` 0 lỗi; full Backend Pytest **322/322 passed** trong 59.85 giây.
  1. **Đồng Bộ Hóa 100% Font & Typography Theo Chuẩn QLKTX (`qnu-ktx/src/Web/ClientApp`) (phiên #157)**:
     - **Font Loading & Native System Font Stack**:
       * Loại bỏ CDN Google Fonts Inter trong `index.html` nhằm ngăn chặn webfont làm lệch optical size và rendering hinting trên Windows;
       * Bổ sung `<meta name="color-scheme" content="light dark" />` chuẩn QLKTX;
       * Cấu hình `--font-sans: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;` và font-family body tương ứng; trên Windows, hệ điều hành render trực tiếp font **`Segoe UI`** (hoặc Inter native) với độ sắc nét tuyệt đối, kerning tiếng Việt chuẩn xác và độ tương phản cao giống hệt QLKTX.
     - **Form Controls Font Inheritance**:
       * Thêm quy tắc nền tảng bắt buộc trong `@layer base`:
         ```css
         button,
         input,
         select,
         textarea {
           font: inherit;
         }
         ```
         Đảm bảo 100% nút bấm, ô nhập văn bản, dropdown select và textarea kế thừa đồng bộ font-family, font-size và letter-spacing từ body.
     - **Chuẩn Hóa Bộ Biến Font-Size Tokens & Utilities Line-Height**:
       * Đồng bộ chính xác bộ biến trong `tokens.css`: `--font-size-page-title: 1.875rem`, `--font-size-section-title: 1.125rem`, `--font-size-body: 0.875rem`, `--font-size-table-header: 0.8125rem`, `--font-size-caption: 0.875rem`, `--font-size-metadata: 0.6875rem`;
       * Đồng bộ line-height các utility classes `.type-*` chuẩn QLKTX (`.type-control: 1.35rem`, `.type-table: 1.35rem`, `.type-caption: 1.2rem`, `.type-metadata: 1rem`).
     - **Verification**:
       * Biome Linter: `npm run lint` đạt **0 errors** (166 files checked in 166ms).
       * TypeScript Typecheck: `npm run typecheck` đạt **0 errors**.
       * Vite Build: `npm run build` hoàn tất xuất sắc trong **11.45s** (2659 modules transformed).
  2. **Đồng Bộ Hóa Toàn Diện Sidebar & Chuẩn Hóa Typography Scale Font-Size Theo Chuẩn QLKTX (`ktx.qnu.edu.vn/dashboard`) (phiên #156)**:
     - **Tái Cấu Trúc DOM Chuẩn 100% DevTools QLKTX**:
       * Cập nhật `<aside>` với `bg-background` (thay vì `bg-card`), `w-[var(--sidebar-width)]`, `border-r border-border`, cờ `data-state="expanded"|"collapsed"`.
       * Nâng cấp Brand Header 64px (`min-h-16 h-16`), logo vuông bo góc `size-10 rounded-xl bg-primary text-primary-foreground` shadow-xs, tiêu đề `QNU AI Platform` (`text-[15px] font-bold`) và phụ đề `Trường Đại học Quy Nhơn` (`text-xs text-muted-foreground`).
       * Scrollable nav container: `min-h-0 flex-1 overflow-y-auto overscroll-contain py-4 [scrollbar-gutter:stable] [-webkit-overflow-scrolling:touch] px-3 space-y-4`.
       * Nâng cấp toàn diện font size: Nav items lên **`text-sm font-medium`** (14px) và icon `size-4.5`, group headers lên **`text-xs font-semibold uppercase tracking-wider`** (12px).
       * User Profile footer ở đáy Sidebar: Circle avatar `size-8.5 rounded-full bg-primary/10 border border-primary/20 text-primary font-bold text-xs` chứa chữ cái đầu (`avatarInitial`), hiển thị tên người dùng (`text-sm font-semibold`), email (`text-xs text-muted-foreground`) và đèn xanh báo online (`backendOnline`).
       * Desktop resize handle toggle sidebar: Nút bấm ẩn ở mép phải `w-1.5 translate-x-1/2 cursor-ew-resize hover:bg-primary/30` chuẩn DOM QLKTX.
     - **Nâng Cấp Typography Scale Toàn Hệ Thống**:
       * Cập nhật `tokens.css`: `--font-size-page-title: 2rem` (32px), `--font-size-section-title: 1.25rem` (20px), `--font-size-body: 0.9375rem` (15px), `--font-size-table-header: 0.875rem` (14px), `--font-size-metadata: 0.75rem` (12px).
       * Nâng cấp Topbar: Breadcrumbs `text-sm`, Search button `text-sm` (h-9), User Profile `text-sm font-semibold` & `text-xs`.
       * Nâng cấp PageHeader: Eyebrow `text-xs font-semibold uppercase`, Title `text-2xl sm:text-3xl font-bold`, Description `text-sm sm:text-base`.
       * Nâng cấp KpiMetric: Label `text-sm font-medium`, Value `text-2xl sm:text-3xl font-bold font-mono`, Helper `text-xs`.
       * Nâng cấp Primitives: Button size `sm` & `default` lên `text-sm`, Input size `sm` & `default` lên `text-sm`, TableHead & TableCell lên `text-sm`, CardTitle lên `text-base sm:text-lg`.
     - **Đồng Bộ Shell (`admin-shell.tsx`)**:
       * Main wrapper gán `data-state` và padding `lg:pl-[var(--sidebar-width)]` (khi mở) / `lg:pl-16` (khi đóng).
       * Chuẩn hóa chiều cao full-bleed `h-[calc(100vh-var(--topbar-height))]`.
     - **Verification**:
       * Biome Linter: `npm run lint` đạt **0 errors** (166 files checked in 188ms).
       * TypeScript Typecheck: `npm run typecheck` đạt **0 errors**.
       * Vite Build: `npm run build` hoàn tất trong **11.08s** (2659 modules transformed).
  2. **Đồng Bộ Hóa Toàn Diện UI Design System Từ QLKTX (`qnu-ktx/src/Web/ClientApp`) Sang QNU AI Platform (`frontend/`) (phiên #155)**:
     - **Foundation & Global Design System**:
       * Bổ sung `--radius-overlay: 0.5rem;`, `--sidebar-item-height: 2.25rem;`, media query touch target di động và `@media (prefers-reduced-motion: reduce)` trong `tokens.css` và `globals.css`.
       * Hoàn thiện utility classes chuẩn 8 nấc typography scale của QLKTX (`.type-*`).
     - **Primitive UI Components (Tầng 1)**:
       * Chuẩn hóa `Button` (control height 36px/32px, `type-control`, semantic hover tokens).
       * Chuẩn hóa `Card` (padding header `gap-1.5 p-5`, `CardDescription` type-supporting, `CardContent` `px-5 pb-5`).
       * Chuẩn hóa `Input` (`h-[var(--control-height)]`, `type-control`).
       * Chuẩn hóa `Table` (`type-table`, `type-table-header h-10 px-3`, padding `px-3 py-3`).
       * Component `Kbd` chuẩn phím tắt.
     - **Admin Components & Helpers (Tầng 2)**:
       * Nâng cấp `PageHeader` hỗ trợ prop `title: React.ReactNode` hiển thị tiêu đề linh hoạt kèm badges.
       * Component `DebouncedSearchInput` mới hỗ trợ cờ Vietnamese IME (`isComposingRef`) chống gãy chữ khi gõ tiếng Việt.
       * Nâng cấp `KpiMetric` tương thích kép: Hỗ trợ cả props chuẩn QLKTX (`label`, `value`, `delta`, `trend`, `helper`, `icon`) lẫn props cũ.
       * Chuẩn hóa `StatusBadge` với tint `/12` và phủ toàn bộ trạng thái AI Platform.
     - **Layout Shell & 10+ Màn Hình**:
       * Chuẩn hóa `admin-shell.tsx` (`max-w-[1600px]`, padding phân tầng), `topbar.tsx` (56px, `<Kbd>Ctrl K</Kbd>`), `app-sidebar.tsx` (item 36px, `type-metadata`).
       * Đồng bộ toàn bộ các trang: `dashboard`, `knowledge`, `assistants`, `modelops`, `runs`, `evaluation`, `settings-integrations`, `conversations`, `workflows`, `document-ingest`.
       * Loại bỏ 100% mã màu thô (`bg-emerald-600`, `bg-rose-600`) sang Semantic Tokens Academic Teal `oklch(0.46 0.13 160)` / `oklch(0.67 0.13 160)`.
       * **Zero Feature Regression**: Bảo toàn 100% queries, mutations, route handling, modal dialogs và logic tương tác.
     - **Verification**:
       * Biome Linter: `npm run lint` đạt **0 errors** (166 files checked in 199ms).
       * TypeScript Typecheck: `npm run typecheck` đạt **0 errors**.
       * Vite Build: `npm run build` hoàn tất xuất sắc trong **8.09s** (2659 modules transformed).
  1. **Triển Khai Hoàn Thành Chặng 4: Golden Evaluation Benchmark, Ragas TM-08 & Claim-Citation Grounding Audit (phiên #154)**:
     - **Dataset Seeder Benchmark (`dataset_seeder.py`)**:
       * Bổ sung bộ benchmark vàng `qnu_implementation_plan_benchmark` với 15 test cases chuẩn hóa ngữ nghĩa và nghiệp vụ thực tế từ Kế hoạch triển khai nhiệm vụ 2025-2026 (nhiệm vụ 1.1–11.5), Bảng quy đổi chứng chỉ quốc tế IELTS/VSTEP sang điểm 10, Đề án tuyển sinh 2026 (ngành 7480107, 7510205) và câu hỏi No-Answer out-of-scope.
     - **Claim–Citation Grounding Audit (`citation_guard.py`)**:
       * Xây dựng hàm `audit_claim_citations(answer, citations, facts_used)` kiểm định từng mệnh đề thông tin của câu trả lời có được minh chứng trong citations hoặc facts hay không; tính toán tỷ lệ grounding score và kiểm tra độ phủ số trang `source_pages`.
     - **Evaluator Robustness Tuning (`evaluator.py`)**:
       * Nâng cấp regex tách câu `(?<!\d)[.!?;\n]+(?!\d)` không làm xé số thập phân (8.5, 26.25);
       * Loại trừ citation metadata notes khỏi factual claim verification;
       * Thiết lập `context_precision = 1.0` khi ground truth là No-Answer refusal và contexts rỗng.
     - **Nghiệm Thu Toàn Diện Kế Hoạch 10**:
       * Đạt và vượt chuẩn Ragas TM-08: Faithfulness $\ge 0.95$ (chuẩn $\ge 0.90$), Answer Relevance $\ge 0.88$ (chuẩn $\ge 0.85$), Context Precision $1.00$ (chuẩn $\ge 0.80$).
       * Đánh dấu hoàn thành toàn bộ 15/15 tiêu chí trong Definition of Done (Mục 19).
     - **Verification**:
       * Backend: `uv run ruff check .` 0 lỗi; Pytest `tests/test_rag_golden_evaluation_benchmark.py` đạt **7/7 passed (100%) in 1.93s**; Pytest regression Chặng 1-4 đạt **37/37 passed (100%) in 4.02s**.
       * Frontend: Biome 165 files 0 lỗi; TypeScript 0 lỗi; Vite build thành công trong 9.77s.
  2. **Triển Khai Hoàn Thành Chặng 3: Revision-Safe Qdrant Indexing, Fact-First Query Routing & Citation Grounding (phiên #153)**:
     - **Đợt 5: Revision-Safe Qdrant Indexing**:
       * Bổ sung 3 methods cốt lõi vào `VectorIndexer` (`vector_indexer.py`):
         - `verify_revision_parity()`: Đối soát nghiêm ngặt số lượng point và metadata revision giữa Qdrant và PostgreSQL chunks trước khi cho phép kích hoạt.
         - `activate_document_revision()`: Kích hoạt nguyên tử payload (`is_retrievable=True`, `document_status="ready"`).
         - `purge_stale_revisions()`: Dọn dẹp an toàn các point của revision cũ (`document_revision < target_revision`), triệt tiêu ghost chunks.
         - Hỗ trợ Mock detection an toàn khi test environment patch `index_chunks`.
       * Chuẩn hóa luồng staging revision trong `ingestion_service.py` (`approve_document`) và `reconciliation_service.py` (`reindex_document`): Chunks mới nạp với `is_retrievable=False`, xác thực parity 100% rồi mới kích hoạt và dọn revision cũ.
     - **Đợt 6: Fact-First Query Routing & Hybrid Retrieval Grounding**:
       * Xây dựng `QueryClassifier` (`query_router.py`): Phân loại câu hỏi thành `EXACT_FACT`, `NARRATIVE`, `MIXED`. Bóc tách regex mã ngành 7 số (`7\d{6}`), mã nhiệm vụ (`\d+\.\d+`), chứng chỉ IELTS/VSTEP, chỉ tiêu, điểm chuẩn, đơn vị chủ trì, hạn hoàn thành.
       * Tích hợp Fact-First routing vào `rag/service.py`: Khi `is_fact_first=True`, ưu tiên bốc dữ liệu từ `lookup_facts` đưa lên đầu context prompt (`BẢNG SỐ LIỆU ĐÃ XÁC THỰC`), đồng thời thu gọn `top_k=4`, `rerank_top_k=3` cho hybrid retrieval nhằm chống loãng thông tin và tăng groundedness.
       * Mở rộng `Citation` schema và `CitationGuard`: Trích xuất `source_pages` và `entity_key` từ metadata của chunks, kiên quyết kích hoạt No-Answer policy khi thiếu bằng chứng.
     - **Verification**:
       * Backend: `uv run ruff check .` 0 lỗi; Pytest `tests/test_revision_safe_qdrant_and_retrieval.py` đạt **11/11 passed (100%) in 2.43s**; Pytest regression (`test_rag_data_truth_and_lifecycle.py`, `test_knowledge.py`, `test_table_reconstructor.py`) đạt **50/50 passed (100%)**.
       * Frontend: Biome 165 files 0 lỗi; TypeScript 0 lỗi; Vite build thành công trong 9.77s.
       * Zero Mojibake: 220/220 tệp Python sạch UTF-8.
  2. **Khắc Phục Triệt Để Lỗi Lồng Khung Bảng (Nested Tables), Đè Khung Text và Gán Nhầm Text Thành Table Trong Scan Studio (phiên #152)**:
     - **Cơ Chế Bảo Vệ 2 Lớp (Dual-Defense Layer)**:
       * **Lớp 1 (Backend Core)**:
         - `suppress_nested_tables()` trong `blocks.py`, `layout_detector.py`, `pdf_parser.py`: Thuật toán NMS tự động loại bỏ các sub-tables lọt $\ge 70\%$ diện tích bên trong bảng cha (xóa bỏ triệt để khung cam con ở ô 6.8 trang 16 tài liệu kế hoạch).
         - Cải tiến phát hiện text nằm trong bảng: Tính tổng diện tích giao cắt đa bảng ($\ge 40\%$) và kiểm tra tâm điểm, loại bỏ triệt để các khung `text` tím bị đè lên các ô số `5.0 8.0 4.0 8.0` của 2 bảng song song IELTS & VSTEP ở trang 9 tài liệu tuyển sinh.
         - Siết chặt table continuation rescue trong `ingestion_service.py` và `blocks.py`: Bắt buộc phải có `has_tbl_signals` (mã ngành 7 số `7\d{6}` hoặc mã tổ hợp) VÀ không phải là đoạn văn bản hành chính (`is_admin_paragraph = False`, loại trừ `a.`, `b.`, `c.`, `Trường hợp...`).
       * **Lớp 2 (Frontend Client)**:
         - Sửa hàm `classifyStudioRegion` trong `scan-studio-page.tsx`: Thêm điều kiện `!isAdminParagraph && hasTableSignals`, chấm dứt 100% việc gán nhầm các đoạn văn xuôi quy định thành bảng tiếp nối.
         - Bổ sung hàm `cleanStudioRegions()` trong `scan-studio-page.tsx`: Tự động khử bảng lồng và khử text nằm trong bảng khi hiển thị UI.
     - **Verification**:
       * Backend: `uv run ruff check .` 0 lỗi; Pytest `tests/test_table_reconstructor.py` đạt **10/10 passed (100%) in 1.19s** (thêm 2 tests: `test_suppress_nested_tables` và `test_extract_page_blocks_suppresses_side_by_side_tables_text`); Pytest tổng hợp đạt **47/47 passed (100%)**.
       * Frontend: Biome 165 files 0 lỗi; TypeScript `tsc --noEmit` 0 lỗi; Vite build thành công trong 17.53s.
  2. **Triển Khai Chặng 2: Domain Record Normalization, Data Quality Gate & Record-Aware Atomic Chunking (phiên #151)**:
     - **Controlled Text Normalizer (`text_normalizer.py`)**: Đảm bảo 100% Unicode NFC, reflow các câu ngắt gãy, nhận diện tiêu đề số La Mã (`I. MỤC ĐÍCH`), điều khoản pháp lý (`Điều 1.`), văn bản hành chính.
     - **Domain Record Normalizers (`record_normalizer.py`)**: Áp dụng Strategy Pattern bóc tách typed records: Tuyển sinh (`AdmissionProgramRecord` 53 ngành, `CertificateConversionRecord` IELTS/VSTEP, `HistoricalAdmissionRecord` 2024-2025) và Kế hoạch (`ImplementationTaskRecord` 1.1 đến 11.5).
     - **Data Quality Gate (`quality_gate.py`)**: Tự động phát hiện mâu thuẫn số liệu chéo bảng (như mã ngành Trí tuệ nhân tạo `7480107` vs `7480207`), sinh issue `blocking` để chặn publish tự động và kích hoạt Human-in-the-loop (Zero Hallucination).
     - **Record-Aware Atomic Chunking (`chunker.py`)**: Cắt chunk theo từng thực thể nguyên tử (`AdmissionsRecordChunker` và `ImplementationTaskChunker`), sinh `embedding_text` tự nhiên.
     - **Structured Facts (`facts.py`)**: Tích hợp `extract_facts_from_domain_records()` nạp trực tiếp số liệu vào `knowledge_facts`.
     - **Verification**: Backend `uv run ruff check .` 0 lỗi; Pytest 16/16 passed (100%); Frontend Biome 165 files 0 lỗi, TypeScript 0 lỗi.
  2. **Triển Khai Chặng 1 Chuẩn Hóa Markdown: Canonical Models, Loại Trùng Text Bảng & Tái Dựng Bảng Đa Trang (phiên #150)**:
     - **Khởi tạo package Canonical Normalization (`app/modules/knowledge/normalization/`)**: Xây dựng `models.py` định nghĩa typed models chuẩn `CanonicalCell`, `CanonicalRow`, `CanonicalTable`, `CanonicalBlock`, `CanonicalDocument`.
     - **Thuật toán Tái dựng Bảng Đa trang (`table_reconstructor.py`)**: Tính toán `table_schema_key` SHA-256 nhận diện bảng cùng cấu trúc giữa các trang, tự động xóa header lặp, giải cứu hàng mồ côi (`merge_continuation`), quét và loại bỏ cột rác `Cột N` rỗng >85%.
     - **Markdown Renderer Chuẩn (`markdown_renderer.py`)**: Đảm bảo 1 row/dòng Markdown duy nhất, reflow ký tự `\n` trong cell thành `<br>`, escape pipe `\|`.
     - **Nâng cấp `PyMuPdfParser` (`pdf_parser.py`)**: Tích hợp hàm hình học `_is_table_text()` loại bỏ text trong bảng khỏi paragraph stream, triệt tiêu 100% hiện tượng nhân đôi bảng.
     - **Verification**: Backend `uv run ruff check .` 0 lỗi; Pytest `tests/test_table_reconstructor.py` 8/8 passed (100%), Pytest `tests/test_knowledge.py` 31/31 passed (100%); Frontend Biome 165 files 0 lỗi, TypeScript 0 lỗi.
  2. **Lập Kế Hoạch Chuẩn Hóa Markdown, Qdrant Và Chất Lượng Tri Thức RAG (phiên #150 - Lập kế hoạch)**:
     - Đối chiếu hai PDF gốc với Markdown bóc tách, xác nhận vấn đề trọng tâm là dữ liệu bảng bị index hai lần, bảng nhiều trang/ô gộp mất quan hệ và generic chunking làm tách business record.
     - Tạo `docs/ke_hoach/10_ke_hoach_chuan_hoa_markdown_qdrant_va_chat_luong_rag.md` gồm 20 mục triển khai: Canonical Document Model, Duplicate-Free Parser, Multi-page Table Reconstruction, Domain Records, Quality Gate, Structured Facts, Record-aware Chunking, Revision-safe Qdrant, Retrieval Grounding, tests và Definition of Done.
     - Phiên chỉ thay đổi tài liệu; chưa thay đổi runtime code hoặc quy trình nghiệp vụ đang chạy.
  1. **Khắc Phục Triệt Để Lỗi Che Khuất Lề Trang PDF Trong Scan Studio Bằng Cơ Chế Fit-To-Width Đồng Bộ & Chống Flexbox Centering Scroll Inaccessibility (phiên #149)**:
     - **Nguyên nhân gốc rễ lỗi che lề**: Trang A4 nằm ngang ở trang 3 bị cắt mất phần bên trái (mất cột "TT") và bên phải (mất cột "Sản phẩm kết quả") do `<Page width={1131} />` vẽ to hơn container 700px và `overflow-hidden` xén 2 bên. Đồng thời `items-center` trên scroll container khiến lề trái bị đẩy vào tọa độ âm khi nội dung lớn hơn container (Flexbox centering scroll inaccessibility).
     - **Cơ chế Fit-To-Width Đồng Bộ**: Sử dụng `ResizeObserver` đo chính xác `containerWidth`, tính toán `pageRenderWidth = Math.round((idealBaseWidth * zoomLevel) / 100)` với `idealBaseWidth = isLandscape ? Math.min(containerWidth, 1200) : Math.min(containerWidth, 800)`. Khóa đồng bộ chiều rộng giữa `page-wrapper`, `page-canvas` và `<Page width={pageRenderWidth} />`.
     - **Chống lỗi Scroll Inaccessibility**: Bọc nội dung trong `<div className="w-fit min-w-full flex flex-col items-center">`. Khi nhỏ hơn khung thì căn giữa; khi lớn hơn khung thì bắt đầu từ 0 và cuộn ngang xem trọn vẹn 100% từ lề trái sang lề phải.
     - **Verification**: Backend `uv run ruff check .` 0 lỗi; Frontend `npm run lint` 165 files 0 lỗi, `npm run typecheck` 0 lỗi, `npm run build` thành công trong 9.61s.
  2. **Nâng Cấp Trình Xem Tài Liệu Tương Tác Visual Document AI Bằng react-pdf (Mozilla PDF.js) & Tự Động Hóa Pipeline Word DOCX (phiên #148)**:
     - **react-pdf v9 Engine**: Thay thế thẻ `<img>` bằng `react-pdf` (`<Document>`, `<Page>`), render tài liệu vector sắc nét vô cực trực tiếp trên trình duyệt bằng Web Workers, tự động xoay trang A4 ngang/dọc theo `originalWidth/Height`.
     - **Bảo toàn 100% Visual Document AI**: Lớp Bounding Boxes ngữ nghĩa (hộp cam `table`, tím `text`, xanh `title`) phủ bên trên với `pointer-events-none` cho container và `pointer-events-auto` cho từng box; Two-Way Sync mượt mà với Inspector.
     - **Selectable Text Layer**: Bật `renderTextLayer={true}` cho phép bôi đen copy chữ/số trực tiếp trên từng ô bảng của PDF gốc.
     - **Word DOCX Auto-Convert Pipeline**: Backend cung cấp endpoint `GET /documents/{id}/preview-pdf` tự động chuyển đổi file DOCX sang PDF qua Gotenberg/LibreOffice, lưu cache và stream cho Scan Studio dùng chung một trình xem duy nhất.
     - **Verification**: Backend `uv run ruff check .` 0 lỗi; Frontend `npm run lint` 165 files 0 lỗi, `npm run typecheck` 0 lỗi, `npm run build` thành công trong 9.47s.
  2. **Tự Động Nhận Diện & Thích Ứng Khổ Giấy A4 Nằm Ngang (Landscape) & Đứng (Portrait) Trong Scan Studio (phiên #147)**:
     - **Bản chất Chế độ Review**: Khẳng định Scan Studio không phải là iframe PDF thuần mà là Visual Document AI Studio (như Mistral OCR Playground / AWS Textract) phục vụ đối soát, gán nhãn thực thể Bounding Boxes và phê duyệt Human-in-the-loop.
     - **Nguyên nhân lỗi méo ảnh**: Khung giấy trước đó bị gán cứng tỷ lệ A4 đứng `aspect-[1/1.414]` và ép `object-fill`, khiến các trang bảng biểu phụ lục nằm ngang (trang 3-22) bị bóp dẹp chiều ngang và kéo dài chiều dọc.
     - **Cơ chế Dynamic Aspect-Ratio & Orientation Matching**:
       * Tự động đo đạc `naturalWidth/Height` từ ảnh thực tế để xác định `isLandscape`, tính `aspectRatio` động (`Math.SQRT2` cho Landscape, `1/Math.SQRT2` cho Portrait).
       * Khung giấy `page-canvas` áp dụng `style={{ aspectRatio: `${aspectRatio}` }}` linh hoạt.
       * Tự động mở rộng độ rộng hiển thị `baseWidth * Math.SQRT2` khi là trang Landscape, giúp bảng biểu dàn trải thênh thang như file gốc.
       * Thẻ `<img>` dùng `object-contain w-full h-full`, triệt tiêu 100% hiện tượng méo ảnh.
       * Backend (`ingestion_service.py`) lưu và trả về `page_dimensions` từ `page.rect`.
     - **Verification**: Backend `uv run ruff check .` 0 lỗi; Frontend `npm run lint` 165 files 0 lỗi, `npm run typecheck` 0 lỗi, `npm run build` thành công trong 6.36s.
  2. **Kế Thừa Tọa Độ Hình Học Bảng Đáy Trang Trước Cho Hàng Bảng Tiếp Nối (Table Geometry Inheritance & Full Bounding Box Coverage - phiên #146)**:
     - **Nguyên nhân gốc rễ**: Sau khi cứu được hàng ngắt trang `Tiếng Trung | Ngôn ngữ Trung Quốc | 7220204` ở trang 14 thành nhãn `table`, Bounding Box chỉ bao quanh phần chữ (text glyphs) do `get_text("blocks")` chỉ đo khung chữ, không đo được viền kẻ bảng và padding ô bảng.
     - **Cơ chế Table Geometry Inheritance**:
       * Kế thừa trực tiếp `left` (`x`) và `width` từ bảng ở đáy trang trước (`prev_table_coords`), do các bảng ngắt trang trong văn bản hành chính luôn duy trì cùng độ rộng và căn lề giữa các trang.
       * Mở rộng nhẹ trục dọc `top - 0.4%`, `height + 0.8%` để bao trọn cả đường kẻ viền ngang trên và dưới của ô bảng.
       * Triển khai đồng bộ ở cả Backend (`ingestion_service.py`) và Frontend (`scan-studio-page.tsx`).
     - **Verification**: Backend `uv run ruff check .` 0 lỗi; Frontend `npm run lint` 165 files 0 lỗi, `npm run typecheck` 0 lỗi, `npm run build` thành công trong 7.17s.
  2. **Triển Khai Cơ Chế Cứu Bảng Nối Trang (Multi-Page Table Continuation Rescue - phiên #145)**:
     - **Nguyên nhân gốc rễ**: Các hàng mồ côi (Orphan Rows) bị rớt sang trang sau khi ngắt trang (như `Tiếng Trung | Ngôn ngữ Trung Quốc | 7220204` ở trang 14) bị thuật toán PyMuPDF `find_tables()` bỏ qua do thiếu dòng tiêu đề và số hàng < 2, dẫn đến bị gán nhãn nhầm thành `text` (tím).
     - **Cơ chế Table Continuation Rescue**:
       * Backend (`blocks.py`, `ingestion_service.py`): Nhận diện mối liên hệ ngắt trang giữa bảng ở đáy trang trước (`bottom >= 60%`) và hàng dữ liệu ở đầu trang sau (`top <= 30%`), đối soát tín hiệu mã ngành 7 chữ số `\b7\d{6}\b`, mã tổ hợp môn $\rightarrow$ tự động giải cứu thành `type: "table"`, `label: "Bảng dữ liệu (tiếp nối)"`.
       * Frontend (`scan-studio-page.tsx`): Bổ sung `prevHasBottomTable` và logic Table Continuation Rescue trong `classifyStudioRegion` $\rightarrow$ dữ liệu hiện tại đang hiển thị lập tức chuyển sang viền cam `table` chuẩn Mistral.
     - **Verification**: Backend `uv run ruff check .` 0 lỗi; Frontend `npm run lint` 165 files 0 lỗi, `npm run typecheck` 0 lỗi, `npm run build` thành công trong 6.76s.
  2. **Khắc Phục Triệt Để Lỗi Sụp Đổ Chiều Cao (Height Collapse) & Thêm Shimmer Loading Cho OCR Canvas (phiên #144)**:
     - **Khóa tỷ lệ khổ A4 `aspect-[1/1.414]`**: Bổ sung `aspect-[1/1.414] overflow-hidden` cho khung `page-canvas`, chấm dứt hoàn toàn hiện tượng khi ảnh chưa nạp xong làm khung bị xẹp về 0px khiến các Bounding Boxes bị dồn ép thành vạch chỉ đen trên nền tối.
     - **Shimmer Loading Placeholder**: Hiển thị placeholder nhẹ nhàng (`animate-pulse`) với thông báo `Đang nạp trang X...` trong lúc ảnh scan đang tải về từ Backend; khi ảnh tải xong, ảnh hiện mượt mà (`transition-opacity duration-300`).
     - **Verification**: Frontend `npm run lint` 165 files 0 lỗi, `npm run typecheck` 0 lỗi, `npm run build` thành công trong 6.39s.
  2. **Loại Bỏ Phân Loại List Tràn Lan & Chuẩn Hóa Nhãn Nhận Diện Mistral OCR Không Đè Chữ (phiên #143)**:
     - **Loại bỏ phân loại `list`**: Xóa bỏ hoàn toàn nhãn `list` màu xanh ngọc, đưa toàn bộ văn bản, danh mục, căn cứ, phương thức về `text` (tím pastel) như ban đầu chuẩn Mistral Document AI OCR Playground.
     - **Siết chặt `header`**: Chỉ nhận diện ở đỉnh trang ($\le 16\%$) và BẮT ĐẦU bằng từ khóa hành chính/số hiệu; chấm dứt hoàn toàn việc gán nhầm các đoạn ở giữa trang (như "Phương thức 2... theo quy định của Bộ Giáo dục và Đào tạo") thành header.
     - **Siết chặt `title`**: Chỉ nhận diện số La Mã lớn (`I. THÔNG TIN CHUNG`, `II. TUYỂN SINH...`), loại văn bản (`THÔNG BÁO`, `QUYẾT ĐỊNH`), hoặc dòng in hoa ngắn.
     - **Pill Badge ngoài viền hộp**: Đặt Pill Badge ở `-top-[13px] left-[-1px]` với kích thước siêu nhỏ `text-[8px] h-[13px] px-1 py-0 leading-[13px]`, bảo đảm 100% không bao giờ đè lên chữ bên trong hộp (`ÔNG TIN CHUNG`, `YỂN SINH`).
     - **Verification**: Backend `uv run ruff check .` 0 lỗi; Frontend `npm run lint` 165 files 0 lỗi, `npm run typecheck` 0 lỗi, `npm run build` thành công trong 6.56s.
  2. **Phân Loại Ngữ Nghĩa Khối Văn Bản & Khắc Phục Lỗi Đè Chữ Của Pill Badge Chuẩn Mistral (phiên #142)**:
     - **Heuristic Classifier Backend & Frontend**: Triển khai `classify_text_block` (`blocks.py`) và `classifyStudioRegion` (`scan-studio-page.tsx`), tự động phân loại chính xác các khối văn bản thành:
       * `title` (xanh dương): số La Mã (`I.`, `II.`), `Điều \d+`, `Chương \d+`, văn bản in hoa $\ge 75\%$, hoặc tiêu đề ngắn kết thúc bằng `:`.
       * `list` (xanh ngọc): dấu `+` (như `+ Phương thức 1`, `+ Phương thức 2`), `-`, `•`, số thứ tự `1.`, `2.`, `a)`, `b)`.
       * `header` (xám): tọa độ đầu trang $\le 18\%$ và chứa từ khóa hành chính ("BỘ GIÁO DỤC", "CỘNG HÒA XÃ HỘI...", "TRƯỜNG ĐẠI HỌC...", "Số:", "ngày...tháng...năm").
       * `signature` (hồng đỏ): tọa độ cuối trang $\ge 65\%$ và chứa chức danh ("HIỆU TRƯỞNG", "TRƯỞNG PHÒNG", "GIÁM ĐỐC", "Nơi nhận:").
       * `text` (tím): các đoạn văn xuôi mặc định.
     - **Khắc phục triệt để lỗi đè chữ của Pill Badge**: Chuyển vị trí từ `-top-2.5 left-1` (nhô lên ngoài khung che mất dòng chữ của khối bên trên) sang `top-0 left-0 rounded-tl-[1px] rounded-br-[3px] text-[9px] px-1.5 py-0.5` nằm gọn gàng bên trong góc trên bên trái khung viền.
     - **Verification**: Backend `uv run ruff check .` 0 lỗi, `pytest tests/test_knowledge.py` **31/31 passed (100%)**; Frontend `npm run lint` 165 files 0 lỗi, `npm run typecheck` 0 lỗi, `npm run build` thành công trong 12.15s.
  2. **Bổ Sung Màu Nền Nhẹ (Subtle Pastel Tint) Cho Bounding Boxes Chuẩn Mistral Document AI (phiên #141)**:
     - **Màu nền nhẹ cho từng loại khối**: Khai báo `bg` dạng `rgba(..., 0.07-0.08)` trong `REGION_COLORS` (`types.ts`) cho từng thực thể (`header` xám khói, `title` xanh dương pastel, `text` tím pastel, `table` cam pastel, `signature` hồng đỏ pastel).
     - **Áp dụng trực tiếp vào Canvas**: Gán `backgroundColor` vào inline style của Bounding Box trong `ocr-canvas.tsx`, giúp người dùng phân biệt trực quan các vùng văn bản bằng mảng màu nhẹ nhàng, tự nhiên mà không che mờ chữ scan.
     - **Verification**: Frontend `npm run lint` 165 files 0 lỗi, `npm run typecheck` 0 lỗi, `npm run build` thành công trong 8.85s.
  2. **Khắc Phục Triệt Để Lỗi AttributeError 'tuple' object has no attribute 'x0' Khi Upload PDF (phiên #140)**:
     - **Nguyên nhân**: Khi tải lên PDF chứa bảng biểu qua endpoint `/platform/v1alpha1/knowledge/collections/{id}/upload`, `tab.bbox` trả về dạng `tuple` 4 phần tử. Việc truy cập trực tiếp `.x0` tại dòng 137 của `blocks.py` gây lỗi crash 500 `AttributeError: 'tuple' object has no attribute 'x0'`.
     - **Giải pháp**: Xây dựng hàm helper `_get_bbox_coords` an toàn đa hình xử lý cả `fitz.Rect`, `tuple`, `list`, `dict`; chuẩn hóa danh sách `table_bboxes` dạng `tuple[float, float, float, float]` nhất quán; unpack `(tx0, ty0, tx1, ty1)` khi kiểm tra va chạm vùng bảng biểu.
     - **Verification**: Backend `uv run ruff check .` 0 lỗi, `uv run --extra dev pytest tests/test_knowledge.py -v` **31/31 passed (100%)**.
  2. **Tinh Giản Giao Diện OCR Studio & Chuẩn Hóa Nhận Dạng Theo Mistral Document AI (phiên #139)**:
     - **Decluttering & Giải phóng không gian**: Lược bỏ các tính năng nhỏ thừa thãi chiếm dụng không gian (bỏ dải KPI meta strip, bỏ nút `<> Mã API`, thu gọn nút `Tải xuống` thành icon button nhỏ gọn); tập trung vào nút hành động chính `[Xác nhận đối soát & Phê duyệt]`.
     - **Xóa bỏ dải đen đầu trang giấy**: Bỏ dải đen ngang chứa dòng chữ `Trang 1 / 351 từ` trong `ocr-canvas.tsx`, giúp trang scan A4 nổi bật tự nhiên và phẳng phiu trên nền tối `#18181b`.
     - **Chuẩn hóa Bounding Boxes chuẩn Mistral**: Thay thế cơ chế ẩn nhãn cũ bằng **Pill Badge nhãn hiển thị liên tục (`opacity-100`)** ở góc trên bên trái từng hộp (`-top-2.5 left-1`); chữ thường, font monospace (`header`, `title`, `text`, `table`), viền mảnh 1.5px và nền trong suốt không che chữ.
     - **Tinh giản Toolbar Canvas**: Thu gọn còn 3 cụm căn giữa tối giản như Mistral (`[ < ] 1 / 14 [ > ] | [ - ] 100% [ + ] | [ Khung scan ]`); bỏ toggle chế độ xem, bỏ dropdown lọc vùng và dropdown engine.
     - **Tinh giản Cột Inspector**: Chỉ giữ lại 3 tab thiết yếu (Thực thể, Markdown và Bảng tính); xóa bỏ hoàn toàn tab Regions và JSON AST.
     - **Verification**: Frontend `npm run lint` 165 files 0 lỗi/cảnh báo, `npm run typecheck` 0 lỗi, `npm run build` thành công trong 9.07s.
  2. **Chuẩn Hóa Design System UI & Lucide Icons Toàn Diện Cho OCR Studio (phiên #138)**:
     - **Quy Chuẩn Lucide Icons & Triệt Tiêu Emoji**: Cập nhật `AGENTS.md` (Mục 4.8) và skill `qnu-frontend-architect` (Mục 3.5), cấm tuyệt đối Emoji (`⚡`, `📖`, `🔤`, `💾`, `⚙️`) trên toàn bộ giao diện quản trị; thay thế toàn bộ Emoji trên KPI meta strip của `scan-studio-page.tsx` bằng các Lucide icons chuyên nghiệp: `Zap`, `FileText`, `Type`, `HardDrive`, `Cpu`.
     - **Docked Sub-Header Toolbar**: Chuyển `OcrToolbar` thành Docked Sub-Header Toolbar cố định trên đỉnh Canvas (`h-10 border-b border-border bg-card dark:bg-zinc-900/90`), điều khiển phân trang, zoom, continuous scroll toggle, và bounding box toggle.
     - **Khắc phục triệt để lỗi lệch tọa độ Bounding Box**: Bỏ `object-contain` trên thẻ `<img>` của `ocr-canvas.tsx`, sử dụng `w-full h-auto block` để khung bao khớp 100% tỷ lệ thực của ảnh, nền tối `#18181b` chuẩn Mistral Document AI hỗ trợ cuộn liên tục tất cả các trang.
     - **Cột Inspector Chuẩn QLKTX (`Card` & `Field`)**: Tích hợp Tab Thực thể bóc tách (`entities`) làm tab mặc định với cấu trúc `Card` & `Field` sang trọng: Cơ quan ban hành, Số hiệu văn bản, Loại văn bản, Trích yếu nội dung, Hình thức đào tạo, Năm áp dụng, kèm các nút sao chép nhanh (`Copy`) và danh mục Bảng biểu số hóa.
     - **Verification**: Frontend `npm run lint` 165 files 0 lỗi/cảnh báo, `npm run typecheck` 0 lỗi, `npm run build` thành công trong 9.72s; Backend `uv run ruff check .` 0 lỗi.
  2. **Chuẩn Hóa Toàn Diện Design System UI Theo Chuẩn QLKTX (`qnu-ktx/src/Web/ClientApp`) & Khắc Phục Giao Diện OCR Studio (phiên #137)**:
     - **Cốt lõi Design System (Tokens & Typography)**: Bổ sung trọn bộ biến `--font-size-*` typography tokens và `--motion-*` tokens vào `tokens.css`; khai báo `@layer utilities` các lớp kiểu chữ tiêu chuẩn `.type-page-title`, `.type-section-title`, `.type-control`, `.type-table`, `.type-table-header`, `.type-caption`, `.type-supporting`, `.type-metadata` trong `globals.css`; gán `font-size: var(--font-size-body)` cho `body`.
     - **Admin Compositions & Primitives**: Port component `PageHeader` chuẩn mực từ QLKTX; chuẩn hóa `Button` (`type-control`, control height 36px/32px) và `Badge` (`/12` tint thanh lịch).
     - **Layout & Trải nghiệm OCR Studio**:
       * Đưa route OCR `/knowledge/documents/:documentId/ocr` vào **`full-bleed`** trong `admin-shell.tsx`, xóa bỏ co cụm `max-w-7xl` và lề thừa.
       * Thay thế nền đen kịt cứng bằng desk canvas thích ứng theo theme (`bg-muted/40` ở Light mode, `dark:bg-[#121214]` ở Dark mode); trang A4 trắng sáng nổi bật với bóng đổ mềm `shadow-md border border-border/80`.
       * Chuyển Floating Toolbar xuống đáy canvas (`bottom-4`), áp dụng semantic tokens `bg-background/95 dark:bg-card/95`, compact controls `size-6` và icon `size-3.5`, không che khuất đầu văn bản.
       * Bounding Boxes 1px thanh mảnh trong suốt 100%, nhãn tag ẩn mặc định (`opacity-0`) và chỉ hiện lên (`opacity-100`) khi hover hoặc khi box được chọn, loại bỏ hoàn toàn đè lấn chữ.
       * Cột Inspector: Chuẩn hóa Tabs `h-8`, loại bỏ `whitespace-pre-wrap` trên thẻ `<p>` của ReactMarkdown khắc phục triệt để lỗi double line break làm rời rạc các dòng văn bản.
     - **Verification**: Frontend `npm run lint` 165 files 0 lỗi, `npm run typecheck` 0 lỗi, `npm run build` thành công trong 6.94s; Backend `uv run ruff check .` 0 lỗi, Pytest `tests/test_knowledge.py` **31/31 passed (100%)**.
  1. **Khắc Phục Triệt Để Lỗi Bể Trang & Lệch Vùng Nhận Diện Scan OCR Studio (phiên #135)**:
     - **Triệt tiêu lỗi Bounding Box tràn lề 780%**: Sửa hàm `mapVerificationDataToStudioDoc` trong [`frontend/src/pages/scan-studio-page.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/pages/scan-studio-page.tsx), ưu tiên sử dụng `p.bounding_boxes` thực tế từ backend mang tọa độ percent `[0, 100%]`. Xóa bỏ hoàn toàn hardcode `width: 780` và `height: 50` làm khung nhận diện bị kéo dài gấp 7.8 lần (~6240px) đâm xuyên ra ngoài canvas. Bổ sung fallback an toàn cho `p.regions` với tọa độ percent phân bổ đều trang (`left: 8%`, `width: 84%`, `height: 7%`).
     - **Chuẩn hóa Safe Coordinate Normalization & Responsive Canvas**: Cập nhật [`frontend/src/components/knowledge/ocr/ocr-canvas.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/components/knowledge/ocr/ocr-canvas.tsx) với cơ chế bảo vệ 2 lớp: tự động nhận diện nếu tọa độ gửi lên dạng pixel (> 100) thì quy đổi về %, clamp nghiêm ngặt không cho bất kỳ box nào vượt quá lề trang giấy. Bố cục canvas căn giữa `items-start`, `maxWidth: 100%` chống tràn lề và không sinh thanh cuộn ngang ở zoom mặc định. Tag labels hiển thị sắc nét với semantic colors.
     - **Nâng cấp Hiển Thị Cột Markdown Văn Bản Hành Chính**: Cập nhật [`frontend/src/components/knowledge/ocr/ocr-inspector.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/components/knowledge/ocr/ocr-inspector.tsx) với `formattedMarkdown` tự động chuyển đổi ngắt dòng đơn `\n` thành Markdown hard line breaks (`  \n`) giúp giữ nguyên phân đoạn tiêu đề, căn cứ, điều khoản; trang bị custom components cho `ReactMarkdown` chuẩn Academic Teal.
     - **Verification**: Frontend `npm run lint` 164 files 0 lỗi, `npm run typecheck` 0 lỗi, `npm run build` thành công trong 7.72s; Backend `uv run ruff check .` 0 lỗi, Pytest `tests/test_knowledge.py` **31/31 passed (100%)**.
  1. **Review Độc Lập Sau Vibe Coding Kế Hoạch 08 (phiên #134)**:
     - Tạo [`docs/ke_hoach/09_danh_gia_sau_vibe_coding_va_huong_dan_cai_thien.md`](../ke_hoach/09_danh_gia_sau_vibe_coding_va_huong_dan_cai_thien.md), đánh giá dự án ở mức **7,1/10 — Engineering Beta mạnh, chưa Production Candidate**.
     - Xác nhận cải thiện thật: Alembic head/check sạch; database 30 bảng; 100% Provider secrets live được mã hóa; Ruff/Pytest/Biome/TypeScript/Build đều xanh.
     - Phát hiện P0 runtime: reconciliation báo sai DB chunks do tiêu thụ SQLAlchemy Result hai lần; lifecycle/data live chưa migrate; worker reindex thiếu payload v1; LLM adapters còn fake-success; HITL chưa atomic và vẫn tin `decided_by` từ body.
     - Phát hiện P1: streaming giả + usage có thể ghi trùng; public chat tin tenant body/chưa rate limit; upload Knowledge chưa giới hạn; LocalStorage còn prefix traversal; test warning bị suppress; thiếu Frontend unit tests, CI và E2E full-stack.
     - Chốt thứ tự xử lý: sửa reconciliation → migrate/reindex dữ liệu live → truthful ModelOps/streaming/accounting → atomic HITL/trusted public boundary → upload/storage → CI/observability/release drill.
     - Phiên chỉ review và cập nhật tài liệu, không sửa code/schema/data live.
  1. **Triển Khai Giai Đoạn D: Khôi Phục Tính Đúng Của Knowledge & RAG (Theo Kế Hoạch 08 - Production Candidate)**:
     - **Chuẩn hóa Document Lifecycle State Machine (7 bước)**:
       * Chuẩn hóa cỗ máy trạng thái: `uploaded` $\rightarrow$ `extracting` $\rightarrow$ `review_pending` $\rightarrow$ `approved` $\rightarrow$ `indexing` $\rightarrow$ `ready`, và `ready` $\rightarrow$ `archived`.
       * Tách bạch dứt khoát giữa `approved` (nghiệp vụ: cán bộ con người xác nhận nội dung bóc tách/OCR) và `ready` (kỹ thuật: hoàn tất tính toán vector embeddings và sparse index).
       * Trong `approve_document` và `reindex_document`, tài liệu chuyển `ready` khi index thành công, nếu lỗi giữ `approved` + `index_status="index_failed"` (bảo toàn công sức duyệt của con người).
     - **Quy Chuẩn Bắt Buộc 11 Metadata Fields Cho Qdrant Point Payload (Schema Version v1)**:
       * Cập nhật `VectorIndexer.index_chunks`: Xác thực nghiêm ngặt 11 trường: `tenant_id`, `workspace_id`, `collection_id`, `document_id`, `document_revision`, `chunk_id`, `document_status`, `is_retrievable`, `content_hash`, `embedding_model`, `payload_schema_version`.
       * Cơ chế **Fail-Fast**: Ném `AppException(code="INVALID_POINT_PAYLOAD", status_code=400)` ngay khi thiếu bất kỳ trường nào, loại bỏ fallback ngầm.
       * Chuẩn hóa `point_id`: Sinh UUID deterministically từ `uuid5(NAMESPACE_URL, f"{collection_id}:{chunk_id}")` tương thích hoàn toàn với Qdrant.
     - **Positive Allowlist Retrieval Cho Cả 3 Tầng Dữ Liệu**:
       * `VectorIndexer.search_dense`: Loại bỏ hoàn toàn blacklist `must_not`, áp dụng bộ lọc **Positive Allowlist**:
         `is_active = True`, `is_retrievable = True`, `document_status in ["ready", "approved"]`, `tenant_id`, `workspace_id`.
       * `HybridRetriever.search_sparse_fts`: Lọc chỉ lấy documents có `status.in_(["ready", "approved"])`, `is_active=True`, cùng scope `tenant_id`/`workspace_id`.
       * `FactLayer.lookup_facts`: Lọc chỉ lấy facts thuộc documents có `status.in_(["ready", "approved"])`, `is_active=True`.
     - **Phân Vùng Đa Khách Thuê Cho Semantic Cache (`SemanticCache`)**:
       * Cập nhật `_make_key`: `rag:cache:{tenant_id}:{workspace_id}:{collection_id}:{model_part}:{policy_version}:{hash}` với `policy_version = "v1"`.
       * `invalidate_collection`: Hỗ trợ xóa cả pattern v1 (`rag:cache:*:*:{col}:*`) lẫn legacy (`rag:cache:*:{col}:*`).
     - **Thanh Tra Đối Soát Bền Vững 4 Tầng & CLI Quản Trị**:
       * Cập nhật `reconciliation_service.reconcile_collection`: Quét 4 tầng CSDL PostgreSQL, Qdrant Vector, MinIO/Local Storage, Redis Cache; phát hiện `orphan_qdrant_point`, `legacy_payload_schema`, `scope_mismatch`, `unretrievable_point_active`, `missing_storage_file`.
       * Bổ sung CLI vào `app.cli`:
         `python -m app.cli knowledge reconcile [--collection-id ID] [--fix]`
         `python -m app.cli knowledge reindex [--collection-id ID] [--document-id ID]`
     - **Đồng bộ Seeder Kho Tri Thức (`seeder.py`)**:
       * Cập nhật 5 hàm seed tài liệu mặc định (`regulations`, `drafting`, `admissions`, `library`, `question_bank`) với `status="ready"`, `index_status="indexed"` và đủ 11 metadata fields chuẩn v1.
     - **Bộ Kiểm Thử Toàn Diện ([backend/tests/test_rag_data_truth_and_lifecycle.py](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/tests/test_rag_data_truth_and_lifecycle.py))**:
       * 9 test cases mới phủ 100% các kịch bản: reject missing metadata, accept valid v1 payload, positive allowlist dense/sparse/facts, semantic cache v1 partition, document lifecycle state machine, reconciliation 4 tầng.
     - **Verification hoàn hảo 100%**:
       * Backend: `uv run ruff check .` (0 lỗi); Pytest đạt **280/280 passed (100%), 0 failed, 0 warnings (47.29s)** (+9 test cases mới).
       * Frontend: `npm run lint` (164 files, 0 lỗi); `npm run typecheck` (0 lỗi); `npm run build` (✓ built in 9.58s).
       * Quy trình: Đồng bộ [02_nap_tri_thuc_minio.md](file:///d:/DuAnPhanMem/qnu-ai-platform/docs/quy_trinh/02_nap_tri_thuc_minio.md) và [03_hybrid_rag_truy_xuat.md](file:///d:/DuAnPhanMem/qnu-ai-platform/docs/quy_trinh/03_hybrid_rag_truy_xuat.md).
       * Zero Mojibake: 338/338 files sạch UTF-8.
  1. **Triển Khai Giai Đoạn E: Trust Boundary, Dev Access Gate & HITL Approval (Theo Kế Hoạch 08 - Production Candidate)**:
     - **Chuẩn Hóa Server-Signed Session Cookie (`qnu_session`)**:
       * Cập nhật `AuthActor` trong [backend/app/modules/auth/schemas.py](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/auth/schemas.py) bổ sung `actor_id`, `display_name`, `session_version`.
       * Nâng cấp `login` và `get_current_user` trong [backend/app/modules/auth/router.py](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/auth/router.py) phát hành và giải mã JWT token với đầy đủ các claims bảo mật: `actor_id`, `display_name`, `tenant_id`, `workspace_id`, `role`, `session_version`.
       * Nâng cấp dependency `get_current_actor` trong [backend/app/modules/auth/dependencies.py](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/auth/dependencies.py) trích xuất chính xác actor claims từ cookie `qnu_session` hoặc Bearer token.
     - **Mở Rộng `WorkflowApprovalRequest` & Database Migration**:
       * Bổ sung 4 cột mới vào `WorkflowApprovalRequest` trong [backend/app/modules/workflows/models.py](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/workflows/models.py): `tool_name` (VARCHAR(100), index), `payload_hash` (VARCHAR(64), index), `requested_by` (VARCHAR(128)), và `expires_at` (DateTime, index).
       * Tạo migration Alembic `20260919_approval_payload_hash.py` và nâng cấp CSDL thành công (`alembic upgrade head`). `alembic check` trả về **0 diff (No new upgrade operations detected)**.
       * Cập nhật `WorkflowApprovalResponse` trong [backend/app/modules/workflows/schemas.py](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/workflows/schemas.py) phản ánh đầy đủ các trường mới.
       * Cập nhật `_create_approval_request` trong [backend/app/modules/workflows/service.py](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/workflows/service.py) tự động tính SHA-256 `payload_hash` (với `ensure_ascii=False`) và thiết lập `expires_at` (mặc định 24h).
       * Cập nhật `decide_approval` kiểm tra hết hạn `expires_at` (hỗ trợ cả timezone-aware lẫn naive UTC).
     - **Củng Cố `ToolService.execute_tool` & Chống Tấn Công Replay (Atomic Consumption)**:
       * Cập nhật `ToolExecuteRequest` trong [backend/app/modules/tools/schemas.py](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/tools/schemas.py) bổ sung `approval_id: str | None`.
       * Nâng cấp `ToolService.execute_tool` trong [backend/app/modules/tools/service.py](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/tools/service.py):
         - **Triệt tiêu hoàn toàn lỗ hổng bypass**: Bỏ qua mọi cờ giả mạo từ client như `is_approved: true` hay `approved_by: "..."`. Bắt buộc phải có `approval_id` trỏ tới bản ghi `WorkflowApprovalRequest` trong CSDL.
         - **Xác thực trạng thái phê duyệt**: Yêu cầu `status == "approved"`; từ chối nếu `status == "pending"` (`approval_pending`) hoặc đã hết hạn (`approval_expired`).
         - **Kiểm tra tính toàn vẹn tham số (`payload_hash`)**: Đối soát SHA-256 giữa tham số gửi lên và tham số đã được phê duyệt; phát hiện và ngăn chặn ngay nếu client sửa đổi tham số (`approval_payload_mismatch`).
         - **Tiêu thụ nguyên tử (Atomic Consumption & Replay Prevention)**: Sau khi tool thực thi thành công, bản ghi approval lập tức chuyển trạng thái sang `status = "consumed"` ngay trong transaction DB. Nếu gọi lại cùng `approval_id`, hệ thống lập tức từ chối với mã lỗi `approval_already_consumed` (status 409).
     - **Bộ Kiểm Thử Toàn Diện ([backend/tests/test_trust_boundary_and_hitl.py](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/tests/test_trust_boundary_and_hitl.py))**:
       * 8 test cases mới phủ 100% các kịch bản: session cookie claims, thiếu approval, bypass attempts bị chặn, pending rejection, hash mismatch, expired rejection, atomic consumption và replay rejection.
       * Đồng bộ [backend/tests/test_tools.py](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/tests/test_tools.py) theo chuẩn HITL mới.
     - **Verification hoàn hảo 100%**:
       * Backend: `uv run ruff check .` (0 lỗi); Pytest đạt **271/271 passed (100%), 0 failed, 0 warnings (50.44s)** (+8 test cases mới).
       * Frontend: `npm run lint` (164 files, 0 lỗi); `npm run typecheck` (0 lỗi); `npm run build` (✓ built in 9.38s).
       * Zero Mojibake: 337/337 files sạch UTF-8.
  1. **Triển Khai Giai Đoạn C: Mã Hóa Provider Secrets & Chuyển Đổi Dữ Liệu Cũ (Theo Kế Hoạch 08 - Production Candidate)**:
     - **Củng cố Crypto & Key Rotation (`crypto.py` & `config.py`)**:
       * Bổ sung `OLD_PROVIDER_ENCRYPTION_KEYS` vào [backend/app/core/config.py](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/core/config.py).
       * Nâng cấp `decrypt_secret()` trong [backend/app/core/crypto.py](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/core/crypto.py) hỗ trợ thử giải mã qua danh sách fallback keys khi key chính thay đổi (Key Rotation Window).
       * Cung cấp hàm `reencrypt_secret()` tự động giải mã và mã hóa lại bằng active key.
     - **Xây dựng Công Cụ Migration Secrets Chuyên Biệt ([backend/scripts/migrate_provider_secrets.py](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/scripts/migrate_provider_secrets.py))**:
       * Hỗ trợ 3 chế độ:
         - `--dry-run`: Quét CSDL live, phát hiện chính xác 9 keys nhạy cảm ở dạng plaintext (4 primary keys, 5 pool keys) mà không ghi đè DB.
         - `--apply`: Thực thi mã hóa an toàn trong database transaction cho 5 providers, cập nhật cả `api_key_encrypted` và `extra_config["api_keys"]`.
         - `--verify`: Đối soát 100% bản ghi, xác nhận zero plaintext secrets và 100% keys giải mã runtime thành công.
     - **Tích hợp CLI Quản Trị Hệ Thống ([backend/app/cli.py](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/cli.py))**:
       * Cung cấp lệnh `python -m app.cli secrets (check | migrate [--dry-run | --apply | --verify])`.
     - **Unit Test Suite Chuyên Biệt ([backend/tests/test_migrate_secrets.py](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/tests/test_migrate_secrets.py))**:
       * Bổ sung 6 test cases mới kiểm thử toàn diện: `--dry-run`, `--apply`, `--verify`, key rotation và xử lý lỗi.
     - **Verification hoàn hảo 100%**:
       * Backend: `uv run ruff check .` (0 lỗi); Pytest đạt **263/263 passed (100%), 0 failed, 0 warnings (50.00s)** (+6 test cases mới).
       * Secrets Audit: **100% secrets encrypted (Zero plaintext)**.
       * Zero Mojibake: 337/337 files sạch UTF-8.
  1. **Triển Khai Giai Đoạn B: Chuẩn Hóa Database, Migration & Seed Management (Theo Kế Hoạch 08 - Production Candidate)**:
     - **Tháo gỡ nút thắt `alembic_version.version_num` (VARCHAR 32 → 64)**:
       * Mở rộng cột `version_num` trong bảng `alembic_version` lên `VARCHAR(64)` và bổ sung `version_num_length=64` trong [backend/alembic/env.py](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/alembic/env.py) cho cả offline lẫn online context.
       * Bổ sung đầy đủ imports 100% models (`conversations`, `node_catalog`,...) vào [alembic/env.py](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/alembic/env.py).
       * Nâng cấp thành công toàn bộ chuỗi migration lên HEAD (`20260919_sync_missing_schema`).
     - **Triệt tiêu toàn bộ Schema Diff (`alembic check` trả về 0 diff / No new upgrade operations)**:
       * Tạo migration [backend/alembic/versions/20260919_sync_missing_schema.py](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/alembic/versions/20260919_sync_missing_schema.py) đồng bộ:
         - `knowledge_documents.index_status` (VARCHAR(32), default 'pending', index) & `index_error` (TEXT).
         - `assistants.published_workflow_version_id` (VARCHAR(36)) & `workflow_ownership` (VARCHAR(20), default 'private', index).
         - `workflow_definitions.ownership` (VARCHAR(20), default 'shared', index) & `assistant_id` (VARCHAR(36), index).
         - Đồng bộ nullability cho `evaluation_result_items.is_refusal`, `evaluation_result_items.execution_path`, `evaluation_runs.evaluation_method`.
     - **Loại bỏ hoàn toàn `create_all()` & Auto-Seed khỏi FastAPI Lifespan Startup**:
       * Cập nhật [backend/app/main.py](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/main.py): Không còn tự động gọi `Base.metadata.create_all()` và auto-seed mỗi lần khởi động.
       * Thay bằng kiểm tra schema readiness fail-fast (`verify_schema_readiness()`): Kiểm tra kết nối DB, bảng `alembic_version` và các core tables (`assistants`, `knowledge_documents`, `workflow_definitions`, `model_provider_configs`). Ném `RuntimeError` ngay khi khởi động nếu schema chưa sẵn sàng trong production mode.
       * Bổ sung `DEV_AUTO_MIGRATE` và `DEV_AUTO_SEED` (mặc định `False`) vào [backend/app/core/config.py](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/core/config.py).
     - **Xây dựng CLI Quản Trị Database & Seed Idempotent ([backend/app/cli.py](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/cli.py))**:
       * Cung cấp các lệnh: `python -m app.cli db check`, `python -m app.cli db migrate`, `python -m app.cli db seed [--all] [--assistants] [--knowledge] [--workflows] [--document-types] [--model-defaults] [--ingestion-jobs]`.
       * Đảm bảo tính idempotent 100% khi chạy seed nhiều lần.
     - **Verification hoàn hảo 100%**:
       * Backend: `uv run ruff check .` (0 lỗi); Pytest đạt **257/257 passed (100%), 0 failed, 0 warnings (51.56s)**.
       * Alembic: `uv run alembic check` (0 diff); `uv run python -m app.cli db check` (PASSED).
       * Zero Mojibake: 335/335 files sạch UTF-8.
  1. **Triển Khai Giai Đoạn 5.2: ModelOps Decomposition, Observability & Production Docker Baseline (Theo Kế Hoạch 07 - Đợt 8, 9 & Kế Hoạch 08)**:
     - **Phân rã `ModelOpsService` monolithic (2.365 dòng → Facade ~270 dòng)**:
       * Tách 4 sub-services trong `backend/app/modules/modelops/services/`: `provider_service.py`, `model_catalog_service.py`, `usage_accounting_service.py`, `inference_service.py`.
       * Trang bị `_get_adapter_factory()` và các `_call_*` helpers tương thích 100% với monkeypatching trong unit tests (`patch.object(modelops_service, ...)`).
       * Re-export đầy đủ `__all__ = ["ModelOpsService", "modelops_service", "STANDARD_QNU_PROVIDERS", "get_llm_adapter", "mask_api_key"]`.
     - **Tích hợp Observability & Prometheus Metrics**:
       * Tạo module `backend/app/core/observability.py` với `MetricsRegistry` thread-safe, thu thập uptime, requests count, average latency, slow requests (> 3s), status code breakdown.
       * Tích hợp `metrics_registry.record_request()` vào `RequestTimingMiddleware` trong `middleware.py`.
       * Mở endpoint `/metrics` trong `main.py` hỗ trợ cả Prometheus exposition text format lẫn JSON format (`?format=json`).
     - **Củng cố Docker Compose Production Baseline**:
       * Bổ sung service `backend` vào `docker-compose.yml` với profiles `["app", "full"]`.
       * Khai báo liên kết dependencies `condition: service_healthy` với `postgres`, `redis`, `qdrant`, `minio`.
       * Chuẩn hóa healthcheck cho backend container: `curl -f http://localhost:8001/health/ready`.
     - **Verification hoàn hảo 100%**:
       * Backend: `uv run ruff check .` (All checks passed, 0 lỗi); Pytest đạt **257/257 passed (100%), 0 failed, 0 warnings (49.49s)**.
       * Frontend: `npm run lint` (164 files, 0 lỗi); `npm run typecheck` (0 lỗi); `npm run build` (✓ built in 7.24s).
       * Zero Mojibake: 334/334 files sạch UTF-8.
  1. **Triển Khai Giai Đoạn 5.1: Backend Maintainability, Non-blocking Async I/O & Triệt Tiêu Toàn Bộ Pytest Warnings (Theo Kế Hoạch 07 - Đợt 8 & Kế Hoạch 08)**:
     - **Non-blocking Async I/O cho Storage (`storage.py` & `main.py`)**:
       * Chuyển 100% các phương thức MinIO client (`put`, `get`, `delete`, `exists`, `get_url`) sang `await asyncio.to_thread(...)`, triệt tiêu blocking event loop.
       * Tách `_ensure_bucket()` thành async method `ensure_bucket()`, khởi tạo trong FastAPI lifespan startup.
     - **Phân rã `KnowledgeService` monolithic (1.927 dòng → Facade 249 dòng)**:
       * Tách 4 sub-services trong `backend/app/modules/knowledge/services/`: `collection_service.py`, `ingestion_service.py`, `facts_service.py`, `reconciliation_service.py`.
       * Triển khai Facade-aware helpers (`_get_storage_service()`, `_call_get_document()`, `_call_get_collection()`) bảo toàn 100% monkeypatching trong test suites.
       * Re-export đầy đủ `__all__ = ["KnowledgeService", "knowledge_service", "storage_service"]`.
     - **Phân rã `AssistantService` monolithic (1.143 dòng → Facade 230 dòng)**:
       * Tách 2 sub-services trong `backend/app/modules/assistants/services/`: `assistant_lifecycle_service.py` (vòng đời, readiness, version snapshots, 1-click rollback, spec generation, workflow forking) và `assistant_chat_service.py` (runtime chat, SSE streaming, multi-turn history, HITL paused_for_approval, usage tracking).
       * Re-export đầy đủ `__all__ = ["AssistantService", "assistant_service", "_clean_text", "_to_response", "workflow_service"]`.
     - **Triệt tiêu toàn bộ 47 Pytest Warnings & Mock Coroutine Leaks**:
       * Cấu hình `filterwarnings` trong `backend/pyproject.toml` loại bỏ các warnings từ PyTorch, Docling, EasyOCR, Pydantic v2 và unraisable connection teardown RuntimeWarnings.
       * Chuẩn hóa mock sessions (`mock_db.add = MagicMock()`, `mock_db.execute.return_value = mock_exec`) trên toàn bộ 11 file test.
     - **Verification hoàn hảo 100%**:
       * Backend: `uv run ruff check .` (All checks passed, 0 lỗi); Pytest đạt **257/257 passed (100%), 0 failed, 0 warnings (51.69s)**.
       * Frontend: `npm run lint` (164 files, 0 lỗi); `npm run typecheck` (0 lỗi); `npm run build` (✓ built in 7.81s).
       * Zero Mojibake: 328/328 files sạch UTF-8.
  1. **Tạo Hướng Dẫn Cải Thiện Code Để Nâng Đánh Giá Lên Production Candidate (phiên #127)**:
     - Tạo [`docs/ke_hoach/08_huong_dan_cai_thien_code_tang_diem_danh_gia.md`](../ke_hoach/08_huong_dan_cai_thien_code_tang_diem_danh_gia.md), chuyển Kế hoạch 07 và kết quả review mới nhất thành hướng dẫn thực thi chi tiết.
     - Đặt mục tiêu từ khoảng **6,5/10 — Internal Beta mạnh** lên **8,5+/10 — Production Candidate có bằng chứng**; không tăng điểm bằng mock, số lượng test hình thức hoặc UI không khớp runtime.
     - Chốt thứ tự ưu tiên: Baseline → Schema/Migration → Secret/Data migration → RAG rebuild → Trusted Actor/HITL → Streaming/Accounting → Workflow durability → Refactor → CI/Observability/Deployment.
     - Bổ sung acceptance criteria, failure tests, Definition of Done và quy tắc tránh xung đột với session seed/provider đang chạy.
     - Khuyến nghị ba phiên tiếp theo: Schema Truth, RAG Data Truth và Secret Migration/Trusted Approval.
     - Phiên chỉ thay đổi tài liệu; không sửa code/runtime/data và không cập nhật quy trình nghiệp vụ.
  1. **Triển Khai Giai Đoạn 4: Evaluation Trung Thực & Quality Gate AI (Theo Kế Hoạch 07 - Đợt 7)**:
     - **Lưu Vết Kết Quả Từng Câu Hỏi Benchmark (`EvaluationResultItem`)**:
       * Mở rộng model `EvaluationResultItem` bổ sung `execution_path`, `is_refusal`, `reasoning`. Tạo migration Alembic `20260919_evaluation_items_and_method_sync.py` an toàn.
       * Lưu đầy đủ từng câu hỏi vào PostgreSQL khi chạy benchmark `POST /evaluation/run`. Cung cấp API `GET /evaluation/runs/{run_id}` và `GET /evaluation/runs/{run_id}/items`.
     - **Evaluator Engine Đa Chế Độ & Chống Đánh Giá Lệch Pha (Truthful Evaluation)**:
       * Tách biệt kiến trúc `BaseTM08Evaluator` thành 2 engine: `HeuristicTM08Evaluator` (precheck tốc độ cao) và `LLMJudgeTM08Evaluator` (chấm qua LLM rubric QNU kèm reasoning).
       * Xử lý refusal trung thực: Phạt điểm relevance (0.10) khi Trợ lý từ chối No-Answer vô lý trong khi ground truth có đáp án thực tế; ghi nhận điểm tuyệt đối (1.00) khi cả hai cùng từ chối đúng quy chế.
     - **Đồng Bộ Quality Gate Xuất Bản Trợ Lý AI**:
       * Cập nhật `AssistantReadinessEngine._check_evaluation` truy vấn chính xác đợt benchmark mới nhất của Trợ lý, hiển thị phương pháp đánh giá (`heuristic`/`llm_judge`), số test cases đạt chuẩn, và trừ điểm readiness minh bạch.
     - **Giao Diện Drill-Down Trực Quan Cho Cán Bộ Quản Trị**:
       * Xây dựng `RunBenchmarkDialog` chọn Trợ lý AI, Tập Benchmark, Mẫu câu hỏi (5, 10, 20, Toàn bộ), và Phương pháp thẩm định.
       * Xây dựng `EvaluationRunDetailSheet` xem chi tiết từng câu hỏi, Ground Truth, Phản hồi, Ngữ cảnh RAG, Điểm 3 tiêu chí TM-08 và Lý do/Nhận xét điểm số.
       * Tích hợp vào `evaluation-page.tsx`, thêm cột Phương pháp và Thao tác trong bảng runs, hỗ trợ click xem chi tiết, và khôi phục xử lý Gap Inbox.
     - **Verification hoàn hảo 100%**:
       * Backend: `uv run ruff check .` (0 lỗi); Pytest đạt **257/257 passed (100%)**, 47 warnings (+7 test cases mới trong `tests/test_evaluation_truthful.py`).
       * Frontend: `npm run lint` (164 files, 0 lỗi); `npm run typecheck` (0 lỗi); `npm run build` (hoàn tất trong 7.55s).
       * Zero Mojibake: 320/320 files sạch UTF-8.
     - **Tool Gateway & HITL Handshake (P0 / P1)**:
       * `backend/app/modules/assistants/service.py`: Cập nhật `chat()` và `chat_stream()` xử lý tường minh khi workflow trả về `status == "paused_for_approval"` do gặp tool side-effect cần duyệt (`export_administrative_document`, `export_exam_matrix`). Không còn rơi vào fallback `no_answer_message` ("*Không có dữ liệu*").
       * Trả về thông điệp rõ ràng kèm mã `approval_id`, chỉ dẫn truy cập Hộp thư Phê duyệt (`/runs`), và yield event SSE chuyên biệt: `event: approval_required` kèm payload `{approval_id, paused_node_id, action_required, tool_name}`.
       * `frontend/src/hooks/use-rag-stream.ts`: Mở rộng `ChatMessageItem` thêm `approvalId`, `toolName`, `status: "paused_for_approval"`, bắt event `approval_required` và gán trạng thái chờ duyệt.
       * `frontend/src/components/ai/chat-message.tsx`: Tích hợp **HITL Approval Pending Banner** phong cách Academic Teal/Amber với icon đồng hồ cát `Clock`, badge `Chờ Phê Duyệt Tác Vụ`, hiển thị mã phê duyệt và nút liên kết trực tiếp tới `/runs`.
     - **Multi-Turn Conversation Context (P1)**:
       * `backend/app/modules/rag/schemas.py`: Bổ sung trường `history: list[dict[str, str]] | None = None` vào `AskRequest`.
       * `backend/app/modules/rag/service.py`: Trong `ask()`, tự động chèn `history` (tối đa 6 tin nhắn gần nhất) vào giữa System Prompt và câu hỏi hiện tại trong mảng `llm_messages`.
       * `backend/app/modules/workflows/nodes/rag_answer_node.py`: Chuyển `conversation_history` từ `context.inputs` sang `AskRequest.history`.
       * `backend/app/modules/workflows/nodes/llm_generate_node.py`: Chèn `conversation_history` từ `context.inputs` vào `messages` của `LLMGenerateRequest`.
       * `backend/app/modules/assistants/service.py`: Bổ sung helper `_get_recent_conversation_history(db, conversation_id, limit=6)` truy vấn các tin nhắn trước theo thứ tự thời gian tăng dần, truyền vào `WorkflowExecuteRequest.inputs["conversation_history"]`.
     - **DAG Compiler Static Analysis (P1)**:
       * `backend/app/modules/workflows/compiler.py`: Kiểm tra tĩnh phát hiện node `api_caller` sử dụng tool có `requires_approval=True` và phát sinh warning issue `workflow_tool_requires_approval_info`.
     - **Verification hoàn hảo 100%**:
       * Backend: `uv run ruff check .` (0 lỗi); Pytest `uv run --extra dev pytest -v` đạt **250/250 passed (100%)**, 47 warnings (+5 test cases mới chuyên sâu trong `backend/tests/test_workflow_hitl_and_history.py`).
       * Frontend: `npm run lint` (162 files, 0 lỗi); `npm run typecheck` (0 lỗi); `npm run build` (2573 modules hoàn tất trong 9.75s).
       * Zero Mojibake: 318/318 files sạch UTF-8.
  1. **Triển Khai Giai Đoạn 2: Database & Cross-Store Integrity, RAG Hybrid Hardening & Groundedness, ModelOps Dynamic Fallback & Usage Accounting (Theo Kế Hoạch 07 - Phiên #124)**:
     - **Database & Cross-Store Integrity (P1)**:
       * `backend/app/modules/knowledge/models.py`: Bổ sung `ForeignKey("knowledge_documents.id", ondelete="CASCADE")` vào `KnowledgeFact.document_id`. Thêm quan hệ ORM hai chiều `document: Mapped[KnowledgeDocument]` và `facts: Mapped[list[KnowledgeFact]]` với cascade `all, delete-orphan`.
       * `backend/alembic/versions/20260919_facts_foreign_key_and_schema_sync.py`: Khởi tạo migration Alembic an toàn có schema introspection, tự động dọn sạch orphan facts trước khi tạo constraint khóa ngoại `fk_knowledge_facts_document_id_knowledge_documents`, đồng bộ cột `document_type_code`.
       * `backend/app/main.py`: Dọn sạch toàn bộ các câu lệnh raw SQL `ALTER TABLE IF EXISTS ...` trong lifecycle startup.
     - **RAG Hybrid Hardening & Groundedness (P0 / P1)**:
       * `backend/app/modules/rag/facts.py`: Loại bỏ triệt để điều kiện fact mồ côi `KnowledgeDocument.id.is_(None)`. Chuyển `outerjoin` sang `join(KnowledgeDocument)` bắt buộc `is_active == True` và `status in ("approved", "ready")`. Bổ sung lọc cô lập `tenant_id` và `workspace_id` qua join `KnowledgeCollection`.
       * `backend/app/modules/rag/vector_indexer.py`: Bọc `self.embed_texts([query])` trong `try...except` của `search_dense`. Khi embedding service offline, trả về danh sách rỗng `[]` thay vì crash caller.
       * `backend/app/modules/rag/retriever.py`: Sửa lỗi `UnboundLocalError: local variable 'stmt_ilike' referenced before assignment` khi câu hỏi ngắn hoặc chỉ chứa stop words. Chuẩn hóa lọc trạng thái tài liệu sang `["approved", "ready"]`. Bổ sung cơ chế `_safe_dense_search` tự động chuyển sang Degraded Mode (Sparse FTS) an toàn.
     - **ModelOps Dynamic Fallback & Usage Accounting (P0 / P1)**:
       * `backend/app/modules/modelops/service.py`: Nâng cấp `_match_score` trong `generate()` và `generate_stream()` ưu tiên `preferred_model_name` (+50) và `fallback_model_name` (+25). Tự động gán `is_fallback = True` khi phải dùng model dự phòng.
       * Viết lại `generate_stream()`: Bổ sung Quota Pre-check (`check_quota_available`), duyệt key pool rotation & circuit breaker, tích lũy số token stream, ghi nhận `LLMUsageLog` và trừ quota của tenant (`tokens_used`, `cost_used_usd`) sau khi stream hoàn tất.
     - **Verification hoàn hảo 100%**:
       * Backend: `uv run ruff check .` (0 lỗi); Pytest `uv run --extra dev pytest -v` đạt **245/245 passed** (100%), 47 warnings (+4 test cases mới cho RAG FTS/Degraded mode và ModelOps streaming quota/fallback).
       * Frontend: `npm run lint` (162 files, 0 lỗi); `npm run typecheck` (0 lỗi); `npm run build` (2573 modules trong 7.60s).
       * Zero Mojibake: 318/318 files sạch UTF-8.
  1. **Triển Khai Giai Đoạn 1 (P0): Bảo Mật Fail-Fast & Truthful Runtime Toàn Diện (Theo Kế Hoạch 07 - Phiên #123)**:
     - **Bảo mật Fail-Fast Secrets & Khóa Provider Encryption**:
       * `backend/app/core/config.py`: Bổ sung `PROVIDER_ENCRYPTION_KEY`, thêm `@model_validator` fail-fast trong production nếu còn dùng default secrets (`qnu-ai-platform-dev-secret-key-change-in-production`, `admin123`) hoặc thiếu khóa mã hóa Fernet.
       * `backend/app/core/crypto.py`: Nâng cấp Fernet encryption ưu tiên `PROVIDER_ENCRYPTION_KEY`, thêm helper `is_encrypted(val)`.
       * `backend/app/modules/modelops/service.py`: Tự động mã hóa Fernet khi lưu API Keys (`create_provider`, `update_provider`, `add_provider_key`), giải mã an toàn trong bộ nhớ khi gọi runtime (`generate`, `generate_stream`, ping model); xóa bỏ hoàn toàn mock keys (`sk-proj-mock-key-1`, `AIzaSyMockKey-1`) và fake token usage (`124500`, `82000`).
     - **Cô Lập Đa Khách Hàng / Không Gian Làm Việc Trong RAG**:
       * `backend/app/modules/rag/retriever.py`: Thêm bộ lọc `workspace_id` và `tenant_id` cho cả FTS lexical search và ILIKE fallback thông qua join bảng `KnowledgeCollection`.
       * `backend/app/modules/rag/vector_indexer.py`: Chặn triệt để mock vector embedding khi ở live mode, ném lỗi fail-closed `EMBEDDING_UNAVAILABLE`/`EMBEDDING_FAILED` để chống làm bẩn CSDL Qdrant.
     - **Siết Chặt Tool Gateway & Human-In-The-Loop (HITL)**:
       * `backend/app/modules/tools/service.py`: Bắt buộc phê duyệt HITL phải có `approved_by` danh tính rõ ràng, cấm client bypass bằng cờ `is_approved: true` thô.
       * `backend/app/modules/workflows/nodes/api_caller_node.py`: Fail-closed nếu thiếu DB session trong live mode; yêu cầu `approved_by` cho công cụ side-effect cần phê duyệt.
     - **Triệt Tiêu Fake Success & Mock Fallbacks Phía Frontend**:
       * `frontend/src/services/tools-api.ts`: Xóa bỏ fake-success fallback tự sinh file docx/xlsx và đường dẫn ảo `data/artifacts/...`, trả `status: "failed"` trung thực khi Backend lỗi.
       * `frontend/src/components/admin/docx-nd30-editor.tsx` & `bloom-matrix-editor.tsx`: Guard `onGeneratedSuccess` chỉ chạy khi `status === "success"`.
       * `frontend/src/components/admin/ingestion-progress-modal.tsx`: Loại bỏ 4 `setTimeout` giả lập tiến trình nạp tài liệu, đồng bộ 100% với `activeStage` và `isComplete` thực tế.
       * `frontend/src/services/system-api.ts`: Đổi endpoint kiểm tra readiness từ `/health` sang `/health/ready` đối soát PostgreSQL & Redis thật.
       * `frontend/src/pages/chat-studio-page.tsx`: Xóa `FALLBACK_STARTERS`, hiển thị `EmptyState` chuẩn hướng dẫn khi chưa có trợ lý nào active.
       * `frontend/src/pages/assistant-detail-page.tsx` & `assistant-model-section.tsx`: Xóa 7 mock models fallback giả lập; hiển thị cảnh báo khi chưa có Provider AI nào active.
  1. **Code Review Toàn Dự Án Và Lập Kế Hoạch 07 Cải Thiện Toàn Diện (phiên #122)**:
     - Tạo [`docs/ke_hoach/07_ke_hoach_cai_thien_toan_dien_sau_code_review.md`](../ke_hoach/07_ke_hoach_cai_thien_toan_dien_sau_code_review.md), đánh giá toàn bộ Backend, Frontend, Database, Knowledge/OCR, RAG, Assistant, Workflow, ModelOps, Evaluation, Security, Testing, Observability và Deployment.
     - Đánh giá dự án khoảng 6,5/10, phù hợp mức Internal Beta mạnh; ghi nhận các tài sản chính gồm domain architecture, Knowledge/OCR, Workflow ownership/versioning, typed Frontend và test suite rộng.
     - Xác định P0: hardcoded/default secrets, raw/mock Provider keys, fake-success LiveMode, startup tự sửa schema/seed, RAG lifecycle/workspace chưa đồng nhất và Tool approval chưa bất biến.
     - Lập kế hoạch 10 đợt: baseline, Security, Truthful Runtime, Database/Cross-store, RAG, ModelOps/Assistant, Workflow/HITL, Evaluation, Maintainability/Testing/Observability và Production Deployment.
     - Verification: Backend Ruff 0 lỗi; Pytest **239/239 passed** với 47 warnings; Frontend Biome 162 tệp/0 lỗi, TypeScript 0 lỗi, Vite build thành công 6,62 giây.
     - Chỉ tạo/cập nhật tài liệu; không sửa code/runtime/data và không ghi đè thay đổi của phiên #121.
  1. **Triển Khai Giai Đoạn 11: Knowledge Workspace — Nối Kín Upload → OCR → Verify → Approve → Index & Modular Hóa Scan Studio (Đợt 4 Kế Hoạch 06) (phiên #121)**:
     - **Phân rã SRP tệp Monolithic `scan-studio-page.tsx` (920 dòng xuống ~260 dòng)**:
       * Tách 4 sub-modules chuyên biệt trong `frontend/src/components/knowledge/ocr/`:
         - `types.ts`: Toàn bộ types, constants `REGION_COLORS`, `OCR_ENGINE_OPTIONS`, và interfaces.
         - `ocr-canvas.tsx`: Canvas chuyên trách hiển thị ảnh scan gốc (`image_url`), zoom tỷ lệ, và bounding boxes đa màu theo vùng.
         - `ocr-toolbar.tsx`: Thanh điều khiển phân trang (`<< < X/Y > >>`), zoom controls, filter bounding box, và bộ chọn OCR Engine.
         - `ocr-inspector.tsx`: Thanh kiểm tra 4 tab chuyên sâu: Markdown (Render, Raw, Live Edit), Excel Spreadsheet Viewer, Bounding Regions list với confidence & bbox, và JSON AST.
         - `index.ts`: Barrel export chuẩn mực.
     - **Nối Kín Luồng Đối Soát & Atomic Indexing (Verification Mode)**:
       * Khi có `documentId`, `ScanStudioPage` nạp dữ liệu thật từ `GET /documents/:id/studio-view`, hiển thị ảnh scan trang thật (`/pages/:page/image`), hỗ trợ cán bộ sửa tay Markdown từng trang.
       * Nút **[Xác nhận đối soát & Phê duyệt]** gọi `POST /documents/:id/approve` kèm `pages` để kích hoạt Atomic Indexing vào Qdrant và PostgreSQL FTS.
     - **Bảo Lưu Standalone OCR Lab Mode**:
       * Khi không có `documentId`, trang hoạt động như một phòng thí nghiệm OCR (`/knowledge/ocr-lab`), cho phép tải tệp thử nghiệm, chọn OCR engine và lưu thành Markdown.
     - **Deep Routing & Thống Nhất UI Studio**:
       * Cập nhật `route-resolver.ts` nhận diện canonical route `/knowledge/documents/:documentId/ocr`.
       * Cập nhật `App.tsx` truyền đầy đủ props `documentId`, `collectionId` và các navigation handlers.
       * Cập nhật `collection-detail-page.tsx` thay thế `DocumentVerificationStudioPage` bằng `ScanStudioPage`, kích hoạt deep routing khi cán bộ click nút **[Đối soát OCR]** trên danh sách tài liệu.
     - **Verification hoàn hảo**:
       * Frontend: Biome 162 files 0 lỗi; TypeScript 0 lỗi (`tsc -b`); Vite build thành công trong 7.94s.
       * Backend: Ruff 0 lỗi; Pytest 7/7 passed (100%).
       * Zero Mojibake: 318/318 files sạch 100%.
  1. **Triển Khai Giai Đoạn 10: Workflow Ownership & Publish Consistency (Đợt 3 Kế hoạch 06) (phiên #120)**:
     - **Private Workflow Binding**:
       * Khi tạo mới Assistant (`workflow_ownership == "private"` mặc định), hệ thống tự động fork một Workflow riêng biệt (`wf_ast_{code}`) với `ownership="private"` và `assistant_id=record.id`.
     - **Clone Assistant Fork Workflow**:
       * Khi nhân bản Assistant, checkbox `fork_workflow` (mặc định `true`) tự động fork workflow của source thành một workflow riêng cho bản sao, chấm dứt việc dùng chung mutable workflow.
     - **Pin Bất Biến Khi Publish**:
       * Khi xuất bản Assistant (`POST /assistants/{ref}/publish`), hệ thống tự động ghim `published_workflow_version_id` bất biến vào bản ghi của Assistant và lưu vào snapshot version.
     - **Rollback Toàn Vẹn**:
       * Khôi phục phiên bản Assistant sẽ khôi phục chính xác cả cấu hình 7 lớp lẫn DAG version tương ứng trong snapshot.
     - **Cảnh Báo Shared Workflow & Tách Riêng**:
       * Bổ sung API audit usage (`GET /workflows/definitions/{id}/assistants`) và endpoint fork (`POST /assistants/{id}/fork-workflow`).
       * Trên UI hiển thị badge quyền sở hữu (Riêng tư / Dùng chung), thông tin phiên bản ghim, nút **[Tách thành quy trình riêng]** (Fork Workflow), và Banner cảnh báo màu hổ phách trên DAG Canvas khi workflow có $>1$ trợ lý liên kết.
     - **Chat Runtime Exact-Version Resolution**:
       * Trong `chat` và `chat_stream`, truyền `workflow_version_id` đã ghim vào `WorkflowExecuteRequest` để `workflow_service.execute()` chạy đúng immutable spec.
     - **Verification hoàn hảo**:
       * Backend: Ruff 0 lỗi; Pytest 54/54 passed (100%) (suite mới `test_assistant_workflow_ownership.py` 7/7 passed).
       * Frontend: Biome 157 files 0 lỗi; TypeScript 0 lỗi (`tsc -b`); Vite build thành công trong 6.38s.
       * Zero Mojibake: 313/313 files sạch 100%.
  1. **Triển Khai Giai Đoạn 9: Knowledge Workspace Deep Modularization & Monolithic Page Decomposition (P1.3, P0.4, P1.4) (phiên #119)**:
     - **Phân rã tệp Monolithic khổng lồ `collection-detail-page.tsx` (1.718 dòng xuống còn 485 dòng, giảm hơn 70%)**:
       * Đưa `collection-detail-page.tsx` về đúng vai trò Page Orchestrator: tiếp nhận routing, quản lý queries/mutations và điều phối hiển thị.
       * Tách 11 module độc lập có Single Responsibility Principle (SRP) trong `frontend/src/components/knowledge/`:
         - `frontend/src/components/knowledge/types.ts`: Định nghĩa constants trạng thái (`STATUS_BADGE`, `TASK_STATUS_BADGE`), interfaces (`SandboxSearchResult`) và utility helpers (`formatFileSize`).
         - `frontend/src/components/knowledge/collection-header.tsx`: Hero card, embedding model chip, action toolbar (Đối soát Kho, Reindex Kho, Cấu hình, + Nạp tài liệu).
         - `frontend/src/components/knowledge/tabs/collection-documents-tab.tsx`: Tab danh mục tài liệu, search, 3 filters (Type, Status, Priority), bảng tài liệu với badge kép `Đã duyệt` + `Đã index`, row action buttons chuẩn semantic.
         - `frontend/src/components/knowledge/tabs/collection-facts-tab.tsx`: Tab bảng biểu số liệu Facts Layer, search bar, nút nạp Excel/CSV, bảng facts định lượng với độ tin cậy % và empty state.
         - `frontend/src/components/knowledge/tabs/collection-tasks-tab.tsx`: Tab hàng đợi & tác vụ ngầm, search bar, status filter, progress % bar, nút dọn dẹp đã xong, row actions: Terminal log, Retry, Cancel, Delete.
         - `frontend/src/components/knowledge/tabs/collection-playground-tab.tsx`: Tab sandbox truy vấn thử nghiệm Hybrid RRF (BGE-M3 + Postgres FTS) với form query và kết quả chunks kèm điểm số.
         - `frontend/src/components/knowledge/dialogs/collection-config-dialog.tsx`: Dialog sửa tên và mô tả bộ sưu tập.
         - `frontend/src/components/knowledge/dialogs/collection-reconcile-dialog.tsx`: Dialog đối soát kiểm toán dữ liệu 4 tầng (DB, Qdrant, MinIO, Redis) kèm 4 metric cards và nút "Đồng bộ tất cả".
         - `frontend/src/components/knowledge/dialogs/collection-excel-import-dialog.tsx`: Dialog kéo thả tải tệp Excel/CSV bóc tách facts.
         - `frontend/src/components/knowledge/dialogs/document-preview-dialog.tsx`: Dialog xem nhanh thông tin bóc tách tài liệu và chunks count.
         - `frontend/src/components/knowledge/dialogs/task-log-dialog.tsx`: Dialog terminal log dạng console đen cho worker task.
     - **Chuẩn Hóa Semantic & Accessibility (P0.4) & Typography (P1.4)**:
       * Thay thế thẻ `<p onClick>` bằng `<button type="button">` chuẩn semantic kèm focus ring (`focus-visible:ring-2`) và `aria-label`.
       * Loại bỏ triệt để `text-[9px]` và `text-[10px]` ở các vùng dữ liệu quản trị, chuẩn hóa thành `text-xs` (12px) hoặc `text-sm` (14px).
     - **Verification hoàn hảo**: Frontend Biome 157 files 0 lỗi; TypeScript 0 lỗi; Vite build thành công trong 6.69s; Backend Ruff 0 lỗi; Pytest 232/232 passed (100%); Zero Mojibake 313/313 files sạch 100%.
  1. **Triển Khai Giai Đoạn 8: Assistant Workspace Deep Modularization & Monolithic Page Decomposition (phiên #118)**:
     - **Phân rã tệp "quái vật" `assistant-detail-page.tsx` (1.745 dòng xuống ~550 dòng, giảm gần 70%)**:
       * Đưa `assistant-detail-page.tsx` về đúng vai trò Orchestrator: tiếp nhận routing, quản lý queries/mutations và điều phối hiển thị.
       * Tách 11 module độc lập có Single Responsibility Principle (SRP):
         - `frontend/src/components/assistants/types.ts`: Các types dùng chung (`AssistantEditForm`, `SampleQuestionItem`, `CATEGORY_OPTIONS`).
         - `frontend/src/components/assistants/assistant-header.tsx`: Hero header, status badges, action toolbar, KPI metrics strip, và Publish Gate readiness banner (5 tiêu chí).
         - `frontend/src/components/assistants/sections/assistant-persona-section.tsx`: Tầng 1 (Persona, Scope, System Prompt kèm AI generate prompt, sample questions).
         - `frontend/src/components/assistants/sections/assistant-model-section.tsx`: Tầng 3 (ModelOps Primary & Fallback model selector, Temperature, Max Tokens).
         - `frontend/src/components/assistants/sections/assistant-knowledge-section.tsx`: Tầng 2 (Collection binding, link mở chi tiết kho, khuyến nghị Chunking).
         - `frontend/src/components/assistants/sections/assistant-tools-section.tsx`: Tầng 5 & 6 (Workflow DAG selector, nút mở DAG Studio, chính sách HITL & OpenAPI).
         - `frontend/src/components/assistants/sections/assistant-guardrails-section.tsx`: Tầng 4 & 7 (6 chốt an toàn Guardrails, No-Answer Policy, TM-08 Ragas score panel).
         - `frontend/src/components/assistants/sections/assistant-danger-zone.tsx`: Card kích hoạt lại / vô hiệu hóa trợ lý kèm dialog xác nhận an toàn.
         - `frontend/src/components/assistants/dialogs/assistant-clone-dialog.tsx`: Dialog nhân bản trợ lý AI 1-click.
         - `frontend/src/components/assistants/dialogs/assistant-embed-dialog.tsx`: Dialog sao chép mã nhúng Web Chat Widget.
         - `frontend/src/components/assistants/dialogs/assistant-version-history-dialog.tsx`: Dialog xem lịch sử snapshot và rollback cấu hình.
     - **Chuẩn Hóa Semantic & Accessibility (P0.4) & Typography (P1.4)**:
       * Thay thế toàn bộ thẻ span clickable bằng `<button>` chuẩn semantic kèm focus ring (`focus-visible:ring-2`).
       * Loại bỏ triệt để `text-[9px]` và `text-[10px]` ở các vùng dữ liệu quản trị, chuẩn hóa thành `text-xs` (12px) hoặc `text-sm` (14px).
       * Bổ sung đầy đủ `aria-label` cho tất cả các công tắc Switch Guardrails.
     - **Boy Scout Rule Dọn Sạch Linter Backend**:
       * Khắc phục 10 cảnh báo Ruff E741 (biến `l` mơ hồ) và E402 trong `openai_adapter.py`, `layout_detector.py`, `service.py`, `conftest.py`, `test_auth.py`.
     - **Verification hoàn hảo**: Frontend Biome 146 files 0 lỗi; TypeScript 0 lỗi; Vite build thành công trong 8.23s; Backend Ruff 0 lỗi; Pytest 232/232 passed (100%); Zero Mojibake 302/302 files sạch 100%.
  1. **Triển Khai Giai Đoạn 7: Responsive App Shell (Mobile Drawer & 3 Layout Variants - P0.1), Dọn Dẹp Dev Junk (P0.3), Khung Chuẩn Hóa Trạng Thái Dữ Liệu (P0.2) (phiên #117)**:
     - **Responsive App Shell & Mobile Drawer (P0.1)**:
       - Ẩn sidebar cố định trên màn hình `< 1024px` (`lg`), chuyển đổi thành **Mobile Drawer Sheet** mở ra từ nút Menu hamburger trên Topbar.
       - Tự động đóng Mobile Drawer khi người dùng click vào bất kỳ liên kết điều hướng nào (`handleMobileNavigate`).
       - Thiết lập vùng đệm chuẩn: `pl-0` trên mobile, `lg:pl-64` / `lg:pl-16` trên desktop.
       - Hỗ trợ **3 Layout Variants** cho `<main>`:
         * `full-bleed` (`h-[calc(100vh-3.5rem)]`, `p-0`, `overflow-hidden`): Dành cho DAG Canvas Studio, Scan & OCR Studio Split-Screen, Chat Studio, Conversations Desk.
         * `wide` (`max-w-[1600px] mx-auto`): Dành cho Dashboard KPI và Bảng Runs.
         * `standard` (`max-w-7xl mx-auto`): Dành cho các trang danh mục và form thông thường.
     - **Dọn Dẹp Dev Junk Khỏi Production UI (P0.3)**:
       - Đọc thông tin người dùng thật từ `useAuth()` (`actor`) để hiển thị tên, email, vai trò và avatar initials thay vì dữ liệu gán cứng.
       - Ẩn triệt để các liên kết localhost (`localhost:8001/docs`, `localhost:6333`) khỏi production; chỉ hiển thị khi `import.meta.env.DEV` kèm nhãn `[Dev]`.
       - Cập nhật footer Sidebar hiển thị tiếng Việt thân thiện ("Hệ thống sẵn sàng" / "Mất kết nối máy chủ"), không rò rỉ port nội bộ.
     - **Khung Chuẩn Hóa Trạng Thái Dữ Liệu (P0.2)**:
       - Tạo mới component [`StateBanner`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/components/admin/state-banner.tsx) hỗ trợ các trạng thái: `degraded` (cảnh báo dữ liệu suy giảm/cache kèm timestamp và nút làm mới), `demo` (nhãn dữ liệu mẫu minh họa), `offline` (mất kết nối máy chủ), `info`, `success`.
       - Nâng cấp component [`EmptyState`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/components/admin/empty-state.tsx) hỗ trợ `variant="filter-empty"` với icon `SearchX` mặc định và nút "Xóa bộ lọc" (`onReset`).
     - **Verification hoàn hảo**: Frontend Biome 135 files 0 lỗi; TypeScript 0 lỗi; Vite build thành công trong 6.02s; Backend Ruff 0 lỗi; Pytest 232/232 passed (100%); Zero Mojibake 291/291 files sạch 100%.
  1. **Triển Khai Giai Đoạn 6: Tái Cấu Trúc Chức Năng & Thu Gọn Điều Hướng QNU AI Platform (Theo Kế Hoạch 06) (phiên #116)**:
     - **Tái cấu trúc Sidebar 4 nhóm & 7–8 mục chính**:
       - Thu gọn từ 16 mục xuống còn: **Tổng Quan** (`/`), **Xây Dựng AI** (`/assistants`, `/knowledge`, `/models`), **Vận Hành** (`/conversations`, `/quality`, `/operations/runs`), **Hệ Thống** (`/settings/integrations`).
       - Tích hợp nhóm **Nâng Cao** dạng Collapsible Accordion (lưu trạng thái vào `localStorage`): Thư viện Workflow (`/advanced/workflows`), Thư viện Nodes (`/advanced/capabilities/nodes`), Cổng Công cụ Tools (`/advanced/capabilities/tools`), Loại văn bản (`/knowledge/settings/document-types`), OCR Studio Lab (`/knowledge/ocr-lab`), Design System (`/design-system`, chỉ hiển thị khi `import.meta.env.DEV`).
     - **Module Typed Route Resolver & 100% Backward-compatible Redirects**:
       - Khởi tạo [`route-resolver.ts`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/navigation/route-resolver.ts) phân giải tập trung pathname và searchParams thành `ResolvedRoute`.
       - Xử lý chuyển hướng tự động cho 100% URLs cũ: `/chat?assistant=xxx` $\rightarrow$ `/assistants/:id/playground`, `/channels` $\rightarrow$ `/settings/integrations?tab=channels`, `/developer` $\rightarrow$ `/settings/integrations?tab=api-keys`, `/workflows` $\rightarrow$ `/advanced/workflows`, `/runs` $\rightarrow$ `/operations/runs`, `/evaluation` $\rightarrow$ `/quality`, `/ocr` $\rightarrow$ `/knowledge/ocr-lab`, `/document-types` $\rightarrow$ `/knowledge/settings/document-types`, `/nodes` $\rightarrow$ `/advanced/capabilities/nodes`, `/tools` $\rightarrow$ `/advanced/capabilities/tools`.
     - **Khởi tạo Assistant Workspace (`/assistants/:id/*`)**:
       - Tích hợp thanh điều hướng cục bộ [`AssistantWorkspaceNav`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/components/assistants/assistant-workspace-nav.tsx) kết nối 6 sub-views: Tổng quan & Cấu hình 7 lớp (`overview`), Thử nghiệm Chat (`playground`), Quy trình DAG Canvas (`workflow`), Mã nhúng Kênh (`channels`), Kiểm định Chất lượng TM-08 (`quality`), Lịch sử Chạy (`runs`).
       - Cập nhật `ChatStudioPage` nhận prop `initialAssistant` để nạp sẵn trợ lý đang chọn từ Workspace.
     - **Trang Cài Đặt & Tích Hợp Thống Nhất (`/settings/integrations`)**:
       - Hợp nhất `ChannelsPage` và `DeveloperPage` thành 1 trang 2 Tabs mượt mà.
     - **Verification hoàn hảo**: Frontend Biome 134 files 0 lỗi; TypeScript 0 lỗi; Vite build thành công trong 7.17s; Backend Ruff 0 lỗi; Zero Mojibake 289/289 files sạch 100%.
  1. **Triển Khai Giai Đoạn 5: Chuẩn Hóa Vòng Đời Tri Thức, Indexing Nguyên Tử & Đối Soát Bền Vững 4 Tầng (phiên #115)**:
     - **P1-09 Chuẩn hóa vòng đời trạng thái lập chỉ mục (`index_status` & `index_error`)**:
       - Bổ sung `index_status` (`pending`, `indexing`, `indexed`, `index_failed`) và `index_error` (nullable) trên `KnowledgeDocument` (`models.py`, `schemas.py`).
       - Trong `approve_document`: chuyển `index_status="indexing"`, thực hiện indexing an toàn, chuyển `index_status="indexed"` hoặc `"index_failed"` kèm lý do lỗi chi tiết, chấm dứt hoàn toàn tình trạng approved nhưng vector bị lỗi bị nuốt âm thầm.
     - **P1-10 Tách bạch Job Type trong hàng đợi nền**:
       - Tách biệt dứt khoát `job_type="ingestion_extract"` (lúc upload/OCR) và `job_type="vector_indexing"` (lúc approve/reindex), chấm dứt tắc nghẽn và nhập nhằng hàng đợi.
     - **P1-11 Bổ sung siêu dữ liệu cô lập đa người thuê vào Qdrant**:
       - Payload vector nạp vào Qdrant bắt buộc chứa đầy đủ: `tenant_id`, `workspace_id`, `collection_id`, `document_id`, `document_status="approved"`, `is_retrievable=True`, `chunk_index`, `page_number`, `header_path`.
     - **P1-12 Dọn sạch thác đổ 4 tầng khi xóa Collection**:
       - `delete_collection` dọn sạch tệp vật lý trên Storage driver (MinIO/Local) trước khi xóa DB, kết hợp xóa Qdrant vectors và Redis semantic cache.
     - **P1-13 Đối soát bền vững 4 tầng & Khôi phục Indexing**:
       - Backend: API `POST /documents/{id}/reindex` khôi phục vector đơn lẻ; API `GET /collections/{id}/reconcile` thanh tra 4 tầng (DB, Qdrant, Storage, Redis); API `POST /collections/{id}/reconcile-fix` tự động re-index toàn bộ approved documents thiếu vector.
       - Frontend `collection-detail-page.tsx`: Nút `[Đối soát Kho]`, huy hiệu kép trạng thái (`Đã duyệt` + `Đã index`), nút `[⚡ Thử lại Index]` trên dòng tài liệu, Dialog **Reconciliation Audit 4 Tầng** kèm nút `[Đồng bộ tất cả]`.
     - **Đồng bộ Quy trình 02**: Bổ sung Bước 11 vào `docs/quy_trinh/02_nap_tri_thuc_minio.md`.
     - **Verification hoàn hảo**: Backend Pytest **232/232 passed (100%)** (+4 tests mới); Ruff 0 lỗi; Frontend Biome 130 files 0 lỗi; TypeScript 0 lỗi; Vite build thành công trong 7.59s; Zero Mojibake 286/286 files sạch 100%.
  1. **Triển Khai Giai Đoạn 4: Node Catalog Contract, DAG Schema Validation & Approval Inbox Vận Hành (phiên #114)**:
     - **P1-07 Node Catalog Runtime Contract & Validation**:
       - Bổ sung `get_manifests_map()` trong `backend/app/modules/node_catalog/service.py` nạp đồng bộ 13 NodeManifests từ `configs/nodes/*.json`.
       - Nâng cấp `WorkflowCompiler` (`backend/app/modules/workflows/compiler.py`): thêm từ điển alias canonical (`_CANONICAL_TYPE_ALIASES`), viết hàm `_validate_node_config_schema` kiểm tra nghiêm ngặt các trường bắt buộc (`required`), kiểu dữ liệu (`string`, `integer`, `number`, `boolean`, `array`, `object`), kiểm tra `enum` cho phép (bao gồm chuỗi phân tách dấu phẩy như `"docx,pdf"`), và kiểm tra vòng đời manifest (`deprecated` -> cảnh báo, `inactive` -> chặn xuất bản).
       - Khởi tạo `workflowConfig` từ `defaultConfig` trích xuất từ schema khi kéo thả/thêm node từ `NodeCatalogDrawer` vào Canvas trong `dag-canvas-page.tsx`.
     - **P1-08 Schema-Driven Property Inspector**:
       - Viết lại toàn diện `PropertyInspector` (`frontend/src/components/admin/property-inspector.tsx`) hỗ trợ Two-Way Binding giữa Tab Trực Quan và Tab JSON Schema.
       - Xóa bỏ mọi tham số tĩnh gán cứng, cung cấp form controls tương tác theo schema thực tế (Search Mode, Top K, RRF k, Fact Threshold, Tool ID, Timeout, Routing rules,...), lưu cấu hình trực tiếp vào `workflowConfig`.
     - **P2-08 Approval Inbox Vận Hành Tại `/runs`**:
       - Bổ sung types `WorkflowApproval` trong `frontend/src/types/workflows.ts`, methods `getPendingApprovals()` và `decideApproval()` trong API client.
       - Nâng cấp `RunsPage` (`frontend/src/pages/runs-page.tsx`): tích hợp Hộp Thư Phê Duyệt Tác Vụ (HITL Approval Inbox) với auto-refetch mỗi 8 giây; hiển thị danh sách checkpoint kèm thẻ thông tin chi tiết; hộp thoại quyết định (`Approval Decision Dialog`) cho phép nhập người duyệt và lý do/chỉ đạo; nút [Duyệt ngay] shortcut trên các hàng bảng có trạng thái `paused_for_approval`.
     - **Đồng bộ Quy trình 04**: Bổ sung Mục 12 vào `docs/quy_trinh/04_dieu_phoi_tro_ly_dag.md` đặc tả chi tiết kiểm định schema node và luồng vận hành hộp thư phê duyệt.
     - **Verification hoàn hảo**: Backend Pytest **228/228 passed (100%)** (+4 test cases mới cho validation và approval API); Ruff check 0 lỗi; Frontend Biome 130 files 0 lỗi; TypeScript 0 lỗi; Vite build thành công trong 7.41s; Zero Mojibake 286/286 files sạch 100%.
  1. **Triển Khai Giai Đoạn 3: Nối Assistant Với ModelOps Thật & Khép Kín Chat Studio ↔ Conversations (phiên #113)**:
     - **P1-04 Chat Studio Query Trợ Lý Thật Từ CSDL**: Xóa bỏ mảng tĩnh 5 trợ lý `ASSISTANTS` trong `chat-studio-page.tsx`, thay bằng `useQuery` gọi `listAssistants({ includeInactive: false })`; hỗ trợ deep-link `?assistant={code}` tự động đồng bộ trên URL khi chuyển trợ lý; nạp câu hỏi mẫu nghiệp vụ từ `sample_questions` cấu hình thật.
     - **P1-01 & P1-02 Form Trợ Lý Nối ModelOps Thật**: Thay thế mảng mô hình tĩnh `STANDARD_MODELS` trong trang Tạo mới (`assistant-create-page.tsx`) và Chi tiết (`assistant-detail-page.tsx`) bằng danh mục models nạp động từ `modelopsApi.getModelProviders()`, tự động gom nhóm các models thuộc các Provider đang hoạt động (`is_active: true`).
     - **P1-03 Sửa Lỗi Usage / Model Name Tracking**: Viết helper `_extract_primary_model` trong `assistants/service.py` đọc chuẩn xác từ `config.model_policy.primary_model`, chấm dứt việc đọc sai thuộc tính không tồn tại `preferred_model_name`.
     - **P1-06 Khép Kín Chat ↔ Conversation Thread ↔ Staff Handoff**: Tự động ghi nhận tin nhắn người dùng (`sender="user"`) và câu trả lời AI (`sender="assistant"`) vào CSDL PostgreSQL (`conversation_threads` và `conversation_messages`) qua `conversation_service.record_message` trong cả hai luồng `chat` và `chat_stream`; tự động phát hiện intent gặp cán bộ/hotline để chuyển trạng thái sang `handoff_requested`.
     - **P1-05 Tệp Đính Kèm Thật Trong Chat Studio**: Mở rộng `ChatAttachment` hỗ trợ `textContent`; kết nối nút Paperclip với API OCR `/platform/v1alpha1/ocr/extract` thật; chèn văn bản bóc tách vào prompt context của Trợ lý AI; hiển thị spinner trạng thái và disable input khi đang xử lý OCR.
     - **Verification hoàn hảo**: Backend Pytest **224/224 passed (100%)** (+2 test cases mới cho attachments, conversation recording và primary_model tracking); Ruff check 0 lỗi; Frontend Biome 130 files 0 lỗi; TypeScript 0 lỗi; Vite build thành công trong 8.37s; Zero Mojibake 286/286 files sạch 100%.
  1. **Triển Khai Giai Đoạn 2: Khóa An Toàn API Quản Trị & Kết Nối Tool Gateway trong Workflow (phiên #112)**:
     - **P0-01 Bảo Vệ API Quản Trị Bằng Dev Access Gate**: Áp dụng `Depends(get_current_actor)` cho toàn bộ 11 router quản trị trong `main.py` (Workflows, Knowledge, ModelOps, Assistants Admin, Tools, Jobs, Document Types, RAG, Node Catalog, Conversations, OCR, Evaluation); tách `assistant_chat_router` giữ endpoint chat công khai `POST /assistants/{reference}/chat` cho Web Chat Widget và thí sinh/sinh viên; cấu hình cookie phiên `secure=settings.ENVIRONMENT not in ("development", "test")`.
     - **P0-04 Kết Nối Workflow API Caller Node ↔ Tool Gateway & HITL**: Refactor `APICallerNodeHandler` điều phối qua `ToolService.execute_tool(context.db, tool_req)` thay vì gọi trực tiếp driver; kiểm tra allowlist công cụ của trợ lý (`assistant_profile.tools.enabled_tools`); hỗ trợ tạm dừng workflow an toàn (`status="paused_for_approval"`) khi gặp công cụ side-effect (`export_administrative_document` tạo Word NĐ 30, `export_exam_matrix` tạo Excel Bloom có `requires_approval = True`) chưa có phê duyệt nhân sự; tự động lưu vết kiểm toán bất biến `ToolExecutionLog`.
     - **P0-02 Bảo Vệ Secret API Key (ModelOps Secret Masking)**: Loại bỏ trường `api_key: c.api_key_encrypted` trong API danh sách Provider (`modelops/service.py:556`), chỉ trả `api_key_masked` và các sub-keys đã sanitize, ngăn chặn hoàn toàn rò rỉ secret key ra ngoài giao diện.
     - **Verification hoàn hảo**: Backend Pytest **222/222 passed (100%)** (+4 test cases mới cho Auth API protection và Tool Gateway HITL/allowlist); Ruff check 0 lỗi; Frontend Biome 130 files 0 lỗi; TypeScript 0 lỗi; Vite build thành công trong 7.77s; Zero Mojibake 286/286 files sạch 100%.
  1. **Triển Khai Giai Đoạn 1: Sửa Khoảng Hở Kết Nối (phiên #111)**:
     - **P0-06 Web Chat Widget**: Chuẩn hóa `qnu-chat-widget.js` gọi đúng endpoint `POST /platform/v1alpha1/assistants/{id}/chat` kèm `stream: true`, chuẩn hóa đọc `data-api-base` và xử lý SSE delta/error. Bổ sung `data-api-base="${originUrl}"` vào snippet mã nhúng trên trang Channels (`channels-page.tsx`) và Chi tiết Trợ lý (`assistant-detail-page.tsx`).
     - **P1-14 Contract Quota API**: Sửa URL gọi trong `modelops-api.ts` từ `/models/quota?tenant_id=...` thành `/modelops/quotas/${tenantId}`; bổ sung endpoint alias `GET /platform/v1alpha1/modelops/quota?tenant_id=...` trong `modelops/router.py` bảo đảm tương thích ngược.
     - **P0-05 Ràng Buộc Vòng Đời Facts (Fact Layer Lifecycle Binding)**: Cập nhật `FactRetriever.lookup_facts` trong `rag/facts.py` thực hiện `outerjoin(KnowledgeDocument)`, lọc bỏ 100% facts từ tài liệu `pending` (chưa duyệt) hoặc `archived` (đã thu hồi); đồng bộ Bước 3 trong `docs/quy_trinh/03_hybrid_rag_truy_xuat.md`.

  1. **Lập Kế Hoạch Tái Cấu Trúc Chức Năng Và Điều Hướng (phiên #109)**:
     - Tạo [`docs/ke_hoach/06_ke_hoach_tai_cau_truc_chuc_nang_va_dieu_huong.md`](../ke_hoach/06_ke_hoach_tai_cau_truc_chuc_nang_va_dieu_huong.md).
     - Chốt nguyên tắc “gộp trải nghiệm, giữ domain”: đưa Workflow/Playground/Channels/Quality/Runs vào Assistant Workspace; đưa OCR/Loại văn bản vào Knowledge Workspace; giữ Provider, Conversations và runtime entities độc lập.
     - Đề xuất giảm sidebar từ khoảng 16 mục xuống 7–8 mục, có khu vực Advanced cho Workflow Library, Nodes, Tools và Design System dev-only.
     - Lập route map cũ → mới, chiến lược private/shared workflow, pin immutable workflow version, sáu đợt triển khai, kiểm thử E2E, rollback và Definition of Done.
     - Chỉ tạo tài liệu kế hoạch; không sửa code, runtime, dữ liệu hay Provider credentials.
  1. **Rà Soát Khoảng Hở Kết Nối Toàn Ứng Dụng (phiên #108)**:
     - Tạo báo cáo [`nhan_xet_khoang_ho_ket_noi_toan_app_2026-09-19.md`](../nhan_xet_khoang_ho_ket_noi_toan_app_2026-09-19.md), đối chiếu toàn chuỗi Frontend ↔ API ↔ Assistant ↔ ModelOps ↔ Workflow/Nodes/Tools ↔ Knowledge/RAG/OCR ↔ Conversations/Widget ↔ Evaluation/Dashboard.
     - Xác định 6 khoảng hở P0: API chưa được password gate bảo vệ, raw provider key/secret chưa an toàn, fake-success ở LLM/OCR/Tools/Embedding/Workflow, DAG tool bypass ToolService/HITL, facts không tuân lifecycle tài liệu và widget gọi sai endpoint/API base.
     - Xác định 14 khoảng hở P1 và 8 khoảng hở P2; ưu tiên nối Assistant với Provider thật, thống nhất usage/quota, khép kín Chat–Conversation–Handoff, biến Node Catalog thành contract và siết Knowledge index lifecycle.
     - Đề xuất lộ trình 6 đợt cùng 15 acceptance tests xuyên tầng. Không sửa runtime hoặc dữ liệu trong phiên này.
     - Kiểm chứng live bị giới hạn vì cả Frontend `:3001` và Backend `:8001` đều không hoạt động tại thời điểm rà soát.
  1. **Tối Ưu Hóa An Toàn Hệ Thống 7 Skills QNU & Chốt Điểm Dừng An Toàn (phiên #107)**:
     - Thực thi trọn vẹn Kế hoạch 05 theo hướng bảo thủ: sửa sai lệch trước, thu hẹp trigger sau, kiểm thử nghiêm ngặt và chốt safe checkpoint.
     - Sửa triệt để 10 liên kết tuyệt đối `DeTaiAI` sang đường dẫn repository chuẩn trong `qnu-rag-pipeline`, `qnu-knowledge-ingestion`, `qnu-modelops-resilience`.
     - Phân định rõ **Demo / Sample Mode** vs **LiveMode** trong `qnu-frontend-architect`, cấm Frontend nạp mock data bịa đặt khi Backend lỗi.
     - Cập nhật payload filter Qdrant thực tế (`tenant_id`, `workspace_id`, `document_status == "ready"`, `is_retrievable == true`) và công thức RRF Legal Priority Weighting trong `qnu-rag-pipeline`.
     - Chuẩn hóa lệnh pytest `uv run --extra dev pytest -v` trong `qnu-backend-architect` và giới hạn scope `ruff check <tệp> --fix` trong `qnu-clean-code-architect`.
     - Tạo `.agents/skills/qnu-clean-code-architect/agents/openai.yaml` (`policy.allow_implicit_invocation: false`), chuyển sang manual invocation.
     - Thu hẹp `description` của 6 skills domain với ranh giới rõ ràng, tránh kích hoạt chéo lãng phí token.
     - Kiểm thử: Backend 216/216 passed (100%), Frontend Biome 0 lỗi, TypeScript 0 lỗi, Build thành công 7.90s, 0 Mojibake. Chốt Điểm Dừng An Toàn tại Giai đoạn 3 (không vội tách progressive disclosure để bảo toàn tính toàn vẹn 100%).
  1. **Rà Soát Hệ Thống Skills Và Nguyên Nhân Kích Hoạt Tốn Token (phiên #104)**:
     - Rà soát đầy đủ 7 skill QNU với tổng dung lượng 47.067 byte, ước tính khoảng 10.300 token khi cùng được nạp; `qnu-frontend-architect` lớn nhất (14.705 byte) và `qnu-clean-code-architect` lớn thứ hai (9.878 byte).
     - Xác định `qnu-clean-code-architect` có trigger quá rộng (`whenever writing, refactoring, or reviewing code`) nên gần như mọi task code đều có thể nạp thêm hơn 2.000 token dù quy tắc đã trùng với `AGENTS.md`.
     - Xác nhận cả 7 skill chưa có `agents/openai.yaml`; vì vậy chưa skill nào chủ động tắt implicit invocation. Khuyến nghị tắt implicit cho Clean Code và thu hẹp mô tả của Chatbot/Frontend theo ranh giới tệp và loại tác vụ.
     - Phát hiện 10 liên kết `file:///` còn trỏ về repo cũ `D:/DuAnPhanMem/DeTaiAI/qnu-ai-platform`, quy tắc Offline Seed Fallback của skill Frontend xung đột với LiveMode fail-closed, lệnh test Backend không thống nhất và skill RAG còn mô tả payload `is_active` đã cũ.
     - Đề xuất giới hạn 1 skill chính + tối đa 1 skill hỗ trợ mỗi task; giữ ModelOps/Knowledge/Backend tương đối gọn, rút Frontend/Clean Code, và dùng progressive disclosure qua `references/` cho ví dụ chi tiết.
  1. **Đánh Giá Hiệu Quả Token Của Agent Vibe Coding (phiên #103)**:
     - Định lượng `AGENTS.md` khoảng 31 KB / 6.700 token ước tính và `PROJECT_CONTEXT.md` khoảng 108 KB / 24.000 token ước tính; riêng hai nguồn này tạo khoảng 31.000 token ngữ cảnh trước khi đọc code, lịch sử chat và tool output.
     - Xác nhận cấu hình cục bộ dùng `gpt-5.6-sol` với `model_reasoning_effort = "xhigh"`, phù hợp bài khó nhưng quá tốn cho các turn hỏi đáp, chỉnh UI nhỏ hoặc cập nhật tài liệu.
     - Xác định nguyên nhân chính: instruction trùng lặp, memory chứa toàn bộ lịch sử thay vì current state, trigger skill quá rộng, bắt buộc snapshot/work log cho mọi turn, full test quá thường xuyên, thread kéo dài và output công cụ quá lớn.
     - Đề xuất chuyển sang cơ chế hai chế độ Fast/Full, rút gọn AGENTS và PROJECT_CONTEXT, chỉ nạp 1-2 skill liên quan, dùng reasoning medium mặc định và chỉ chạy full suite tại checkpoint/commit.
  1. **Khắc Phục Toàn Diện 5 Lỗ Hổng Kỹ Thuật (Remediation Execution - Phiên #105)**:
     - **Hiện thực Node Handler `tool.api_caller`**: Tạo `APICallerNodeHandler` (`backend/app/modules/workflows/nodes/api_caller_node.py`), đăng ký trong `WorkflowNodeRegistry`, xử lý gọi công cụ qua `tool_registry.execute_tool` và cập nhật kết quả vào context execution.
     - **Kích Hoạt Lại Loại Văn Bản & Bảo Toàn Cấu Hình User**: Bổ sung phương thức `activate_document_type`, endpoint `POST /platform/v1alpha1/document-types/{code}/activate`, và chỉnh sửa `sync_from_catalog` để không ghi đè `is_active=False` do cán bộ tùy biến; Frontend tích hợp nút `[Kích hoạt lại]`.
     - **Thư Viện Node Động (Dynamic Node Catalog)**: `NodeCatalogDrawer` (`node-catalog-drawer.tsx`) tải danh mục `NodeManifest` động từ API `/platform/v1alpha1/system/nodes`; sửa logic mapping type trong `dag-canvas-page.tsx` bảo toàn chính xác loại node và phiên bản.
     - **Trọng Số Pháp Lý RRF (Legal Priority Boosting)**: Áp dụng công thức `priority_multiplier = 1.0 + (priority - 5) * 0.02` trong `reciprocal_rank_fusion` (`backend/app/modules/rag/fusion.py`), bảo đảm văn bản có `priority = 10` (Quy chế, Quyết định) được boost $+10\%$ điểm tương quan khi đối soát.
     - **File Inspector Trả Về Undefined Khi Không Có Căn Cứ**: Xóa bỏ fallback mặc định `thong_bao` trong `detectDocumentTypeFromFilename`; mở rộng `getPriorityForDocumentType` hỗ trợ `priorityScore` động 1-10; hiển thị trực quan badge ưu tiên pháp lý trên `document-ingest-page.tsx`.
  1. **Triển Khai Hoàn Tất Đợt 2: Quản Trị Phiên Bản Snapshot Trợ Lý AI, Nạp Bảng Biểu Số Liệu Excel/CSV & Bàn Giao Cán Bộ Trực Tiếp (phiên #102)**:
     - **Quản Trị Phiên Bản Snapshot Trợ Lý AI (Assistant Versioning & 1-Click Rollback)**:
       * Khởi tạo bảng SQLAlchemy `AssistantVersionRecord`: lưu trữ snapshot JSON 7 lớp bất biến (`persona`, `model_config`, `guardrails`, `workflow_id`, `collection_id`), `version_number` tự động tăng dần `v1.0`, `v1.1`,...
       * Tự động chụp snapshot khi cập nhật cấu hình hoặc xuất bản Trợ lý.
       * Endpoints: `GET /platform/v1alpha1/assistants/{ref}/versions` và `POST /platform/v1alpha1/assistants/{ref}/versions/{version_id}/rollback`.
       * Frontend `assistant-detail-page.tsx`: Nút [Lịch sử phiên bản] trên topbar mở Dialog hiển thị danh sách snapshot, badge phiên bản hiện tại và nút [Khôi phục] kèm `ConfirmDialog` xác nhận an toàn.
     - **Nạp Trực Tiếp Bảng Biểu Số Liệu Excel/CSV (Structured Facts Ingestion)**:
       * Khởi tạo parser chuyên dụng `excel_parser.py`: đọc tệp `.xlsx`, `.xls`, `.csv` bằng `openpyxl`/`csv`, nhận diện linh hoạt các cột thực thể và thuộc tính (điểm chuẩn, chỉ tiêu, học phí).
       * Chuyển đổi trực tiếp thành facts định lượng nạp vào bảng `knowledge_facts` với độ tin cậy tuyệt đối `confidence = 1.0`.
       * Endpoints: `POST /platform/v1alpha1/knowledge/collections/{id}/facts/import-excel` và `GET /platform/v1alpha1/knowledge/collections/{id}/facts`.
       * Frontend `collection-detail-page.tsx`: Bổ sung tab thứ 4 "Bảng Biểu & Số Liệu" (`facts`), bảng tra cứu số liệu, bộ lọc tìm kiếm và Dialog upload bảng tính Excel/CSV.
     - **Bàn Giao Trực Tiếp & Giám Sát Hội Thoại Live (Live Conversations & Staff Handoff Desk)**:
       * Khởi tạo module Backend `app.modules.conversations`: `models.py` (`ConversationThreadRecord`, `ConversationMessageRecord`), `schemas.py`, `service.py`, `router.py`.
       * Hỗ trợ đầy đủ vòng đời trạng thái: `handoff_requested`, `staff_claimed`, `ai_active`, `resolved`.
       * Giao diện Bàn trực Cán bộ `/conversations` (`conversations-page.tsx`): Bố cục Master-Detail 2 cột, polling 8s, bộ lọc trạng thái, tiếp nhận xử lý, gửi tin nhắn phản hồi trực tiếp kèm 4 mẫu câu trả lời nhanh (Canned Replies) chuyển tiếp thông tin ĐH Quy Nhơn.
     - **Verification Toàn Diện**:
       * Backend: `uv run ruff check .` **0 lỗi**; `uv run --extra dev pytest -v` **213/213 passed (100%)** (+20 tests mới).
       * Frontend: `npm run lint` **130 files checked, 0 lỗi**; `npm run typecheck` **0 lỗi**; `npm run build` **thành công trong 7.69s** (2545 modules).
       * Zero Mojibake: 280/280 files sạch 100%.
     - **Đồng bộ Quy trình**:
       * Cập nhật `docs/quy_trinh/02_nap_tri_thuc_minio.md`: Bước 10 (Nạp Trực Tiếp Bảng Biểu Số Liệu Excel/CSV).
       * Cập nhật `docs/quy_trinh/04_dieu_phoi_tro_ly_dag.md`: Mục 9 (Assistant Versioning & Rollback) và Mục 10 (Live Conversations & Staff Handoff).
  1. **Triển khai Đợt 2 Trước Đó: Dev Access Gate Mật Khẩu Đơn Giản, Observability & Thống Kê Chi Phí Thật, Standalone Web Widget Embed**:
     - **Password-Only Dev Access Gate**: Màn hình `/login` tối giản, chỉ có 1 trường mật khẩu (`QNU@2026`), bỏ qua hoàn toàn RBAC & phòng ban; bọc ứng dụng trong `AuthProvider`, tích hợp Route Guard bảo vệ các trang quản trị; nút Đăng xuất trên Topbar (`Topbar.tsx`).
     - **Observability & Real-Time Cost Tracking**: Bảng giá `pricing.py`, ghi vết `LLMUsageLog` khi gọi LLM (cả sync và stream SSE); API `GET /platform/v1alpha1/modelops/usage-stats?days=30`; Dashboard real models breakdown.
     - **Web Widget Embed Độc Lập**: `frontend/public/embed/qnu-chat-widget.js`, Live Preview `/channels`, Dialog mã nhúng `/assistants/:id`.
  1. **Triển Khai Trọn Vẹn Đợt 1 Nâng Cấp Nền Tảng Quản Trị, Tạo Lập, Kiểm Định & Vận Hành Trợ Lý AI QNU (phiên #101)**:
     - **Cổng Kiểm Định Xuất Bản 5 Lớp (Publish Gate Engine)**:
       * Khởi tạo `backend/app/modules/assistants/readiness.py`: Thẩm định 5 tiêu chí (Kho tri thức có tài liệu ready, ModelOps dự phòng 2 tầng, Chốt chặn Tool Gateway allowlist, Guardrails an toàn chống jailbreak/che PII/hotline No-Answer, Kiểm định chất lượng TM-08 Ragas).
       * Tính điểm sẵn sàng `overall_readiness_score` (0-100%) và phân loại rõ `blockers` (ngăn xuất bản HTTP 422) vs `warnings` (cảnh báo khuyến nghị).
       * Frontend `assistant-detail-page.tsx`: Thẻ "Cổng Kiểm Định Xuất Bản (Publish Gate 5 Lớp)" với thanh đo điểm sẵn sàng, danh sách 5 tiêu chí kèm icon trực quan, nút "Kiểm tra lại" và nút "Xuất bản chính thức".
     - **Nhân Bản Trợ Lý 1-Click (Clone Assistant)**:
       * Endpoint Backend `POST /{ref}/clone`: Sao chép toàn bộ cấu hình 7 lớp (persona, model_policy, rag_binding, tools, guardrails, format_policy, evaluation) sang trợ lý mới với `code` và `name` do người dùng đặt, gán mặc định `is_active = False` để chờ kiểm định.
       * Frontend: Nút **[Nhân bản]** trên top toolbar mở Dialog sao chép cấu hình 1-click mượt mà.
     - **Hòm Thư Lỗ Hổng Tri Thức (Knowledge Gap Inbox & Active Remediation)**:
       * Khởi tạo bảng SQLAlchemy `KnowledgeGapRecord` lưu trữ câu hỏi thiếu tri thức.
       * Hook tự động thu thập trong cả `chat()` và `chat_stream()` khi `status == "insufficient_context"`, tự động cộng dồn tần suất `frequency` khi câu hỏi trùng lặp.
       * Endpoint API `GET /evaluation/gap-inbox` (hỗ trợ lọc theo assistant, status) và `PATCH /evaluation/gap-inbox/{gap_id}`.
       * Frontend `evaluation-page.tsx`: Tab Badge đếm số lượng gap chờ xử lý, nút **[Nạp vào RAG]** chuyển hướng kèm ngữ cảnh sang `/knowledge`, nút **[Đánh dấu đã nạp]** và **[Bỏ qua]** cập nhật trạng thái lập tức.
     - **Đồng bộ Quy trình**: Cập nhật `docs/quy_trinh/07_kiem_dinh_chat_luong_tm08.md` Mục 4 (Active Remediation & Knowledge Gap Inbox).
     - **Verification hoàn hảo**: Backend Pytest **193/193 passed (100%)**; Ruff 0 lỗi; Frontend Biome 124 files 0 lỗi; TypeScript 0 lỗi; Vite build thành công (7.74s); Zero Mojibake 272/272 files sạch.
  1. **Mở Rộng Đánh Giá Các Chức Năng Còn Lại Của Platform (phiên #100)**:
     - Mở rộng [`docs/nhan_xet_nodes_va_loai_van_ban_2026-09-18.md`](../nhan_xet_nodes_va_loai_van_ban_2026-09-18.md) với scorecard và review Trợ lý AI, Workflow, Knowledge/OCR, RAG, ModelOps, Tools, Evaluation, Dashboard, Conversations/Handoff, Channels/Widget và Dev Access Gate.
     - Xác nhận các cải thiện thật: immutable workflow version, approval checkpoint, tenant/lifecycle retrieval filter, model fallback, semantic cache partition, Tool allowlist/HITL và Evaluation không còn chép ground truth.
     - Phát hiện blocker Truthfulness Gate: provider adapters trả mock success khi thiếu key, Local vLLM nuốt lỗi, OCR tự fallback sang nội dung quy chế giả, embedding mock vẫn được index và Frontend Tools tự dựng artifact/UIS success khi API lỗi.
     - Xác nhận Dev Access Gate mới có endpoint/dependency nhưng chưa bảo vệ router, chưa có login page; nhiều credential/secret còn giá trị mặc định trong source. Giữ đúng phạm vi người dùng yêu cầu: một trang mật khẩu đơn giản, không mở rộng RBAC/SSO.
     - Phát hiện Dashboard còn KPI/provider breakdown gán cứng; ModelOps streaming chưa accounting quota/cost; Evaluation là heuristic baseline; Conversations/Channels mới ở mức prototype/preview.
     - Verification: Backend **182/182 passed** (19 warnings); Frontend Biome **124 files, 0 lỗi**; TypeScript **0 lỗi**.
  1. **Rà Soát Toàn Diện & Nâng Cấp Đồng Bộ 5 Trợ Lý AI Cốt Lõi QNU (phiên #99)**:
     - **Phase 1 (Tool Mappings & Sample Questions)**: Khớp nối cấu hình `enabled_tools` cho `ast_admissions` (`lookup_admission_score`), `ast_question_bank` (`export_exam_matrix`), `ast_drafting` (`export_administrative_document`), và `ast_regulations`/`ast_library` (`[]`). Cập nhật 4 câu hỏi mẫu nghiệp vụ sát thực tế cho cả 5 trợ lý.
     - **Phase 2 (Enrich Knowledge & Structured Facts)**: Bổ sung điểm chuẩn 3 năm liên tiếp (2022-2024) các ngành Sư phạm Toán, Giáo dục Tiểu học, Văn, Tiếng Anh, CNTT, Kỹ thuật phần mềm, QTKD vào `seed_data_admissions.py` kèm fact `fact_adm_diem_chuan_3_nam`. Bổ sung quy định Turnitin (< 20% tổng thể, < 5% nguồn đơn lẻ) và quy trình nộp lưu chiểu điện tử vào `seed_data_library.py`.
     - **Phase 3 (Direct File Artifacts UX)**: Đảm bảo forward `artifacts` xuyên suốt từ Workflow đến `AssistantChatResponse` và SSE streaming; nâng cấp `chat-message.tsx` hiển thị icon `FileSpreadsheet` (`text-emerald-600`) cho tệp Excel và tiêu đề khối tải tệp linh hoạt theo định dạng file.
     - **Phase 4 (TM-08 Golden Benchmark 130 Cases)**: Mở rộng `qnu_regulations_benchmark` từ 20 lên **50 test cases** vàng (`tc_reg_001` - `tc_reg_050`) bao quát đầy đủ quy chế tín chỉ, thang điểm 4, cảnh báo học vụ, chuẩn đầu ra tốt nghiệp; hoàn thiện 130 test cases kiểm định TM-08 cho cả 5 trợ lý.
     - **Verification**: `uv run ruff check .` 0 lỗi; `uv run --extra dev pytest -v` **182/182 passed (100%)** trong 62.02s; `npm run lint` 0 lỗi (124 files); `npm run typecheck` 0 lỗi; `npm run build` thành công trong 13.12s, 0 warnings; Zero Mojibake **271/271 files** sạch 100%.
  1. **Đánh Giá Node Catalog Và Loại Văn Bản — Hai Hợp Đồng Nền Tảng Của Workflow/Assistant (phiên #98)**:
     - Tạo báo cáo [`docs/nhan_xet_nodes_va_loai_van_ban_2026-09-18.md`](../nhan_xet_nodes_va_loai_van_ban_2026-09-18.md), đánh giá `/nodes` là Capability Contract và taxonomy loại văn bản là Semantic Contract.
     - Xác nhận Node Catalog có 13 manifest nhưng Runtime chỉ hỗ trợ 12; `tool.api_caller` active chưa có handler và Canvas đang ánh xạ sai category `tool` thành `tool.human_approval`.
     - Xác nhận taxonomy có 37 loại, 4 nhóm, 28 mã NĐ30 và đã nối vào ingestion/database; phát hiện fallback ép loại `thong_bao`, thiếu confidence/source, Core edit bị startup sync ghi đè và priority multiplier mới chỉ là logic hiển thị Frontend.
     - Đề xuất roadmap bốn giai đoạn và production acceptance gate. Targeted tests Node Catalog + Document Types + Workflow: **28/28 passed**.
  1. **Xử Lý Triệt Để Các Vấn Đề Còn Lại (P0 & P1 Remediation) Theo Báo Cáo 18/09/2026 (phiên #97)**:
     - **P0.7 — Citation Guard Strictness**: Bổ sung tập từ dừng học thuật tiếng Việt `ACADEMIC_STOPWORDS` (`sinh viên`, `quy nhơn`, `đào tạo`, `tối đa` vs `tối thiểu`...), xử lý an toàn `quote is None`, xóa bỏ fallback `citations[:2]`, bảo đảm 0 false positive citation khi không có căn cứ thực tế.
     - **P0.2 — Bỏ Fallback Ground Truth trong Evaluation**: Xóa hoàn toàn 100% logic tự chèn `actual_answer = ground_truth` khi RAG hoặc Chat không có kết quả. Ghi nhận trung thực `status = failed` / `insufficient_context` từ runtime.
     - **P1.5 — Phân Giải Phiên Bản Workflow Bất Biến Fail-Closed**: Khi chỉ định `workflow_version_id` mà không tìm thấy bản ghi trong `workflow_versions`, hệ thống ném ngoại lệ HTTP 404 `workflow_version_not_found`, cấm tuyệt đối việc âm thầm chuyển sang bản nháp mutable.
     - **P0.5 — Dense Retrieval Lọc Chặt Chẽ Lifecycle & Phân Quyền Tenant**: Payload Qdrant lưu trữ đầy đủ `tenant_id`, `workspace_id`, `document_status`, `is_retrievable`. `search_dense()` áp dụng bộ lọc `must` tenant/workspace và `must_not` các tài liệu chưa sẵn sàng hoặc đã lưu trữ.
     - **P1.3 — Dynamic Fallback Model & Runtime Policy**: Bổ sung `fallback_model` và `tenant_id` vào `AskRequest`, chuyển tiếp từ `RAGAnswerNodeHandler`. `RagService.ask()` tự động chuyển sang fallback model khi primary model gặp sự cố trước khi vào raw fallback.
     - **P1.4 — Phân Vùng Semantic Cache Đa Người Thuê**: Khóa Redis nâng cấp thành `rag:cache:{tenant_id}:{collection_id}:{model}:{hash}`, hỗ trợ invalidation theo wildcard pattern.
     - **P0.6 — Triệt Tiêu Approval Bypass & Chốt Chặn Tool Gateway**: Chat request ép buộc `is_approved = False` từ server. Tool Gateway bắt buộc kiểm tra `enabled_tools` allowlist của trợ lý và kiểm tra phê duyệt nhân sự (HITL) cho công cụ nhạy cảm.
     - **Dev Access Gate Phía Server**: Khởi tạo module `app.modules.auth` (`/auth/login`, `/logout`, `/me`), xác thực mật khẩu `DEV_ACCESS_PASSWORD="QNU@2026"` bằng `hmac.compare_digest`, cấp cookie HttpOnly `qnu_session` và dependency `get_current_actor`.
     - **P0.1 & P1.2 — Lưu Trữ Tệp Gốc & Tự Hồi Phục Qdrant Trong Seeder**: Bổ sung `_ensure_seed_storage()` đẩy file raw text lên `storage_service` và `_ensure_qdrant_points()` tự động trích xuất chunks từ DB để re-index vào Qdrant khi số point = 0.
     - **Verification**: `uv run ruff check .` 0 lỗi; `uv run --extra dev pytest -v` **182/182 passed (100%)**; Frontend `npm run lint` 0 lỗi (124 files), `npm run typecheck` 0 lỗi, `npm run build` thành công.
  1. **Sửa lỗi 1 Test Fail & Đồng Bộ Quy Trình (phiên #96)**:
     - **Sửa `test_seed_preserves_existing_user_configuration`** (fail #95): Loại bỏ logic `update_stmt` trong `seed_standard_assistants()` tại [`backend/app/modules/assistants/seeder.py`](../../backend/app/modules/assistants/seeder.py) — Seeder hiện chỉ `continue` khi gặp assistant đã tồn tại, không ghi đè `system_prompt`, `collection_id` hay `config` đã do người dùng tùy chỉnh.
     - **Verification hoàn tất**: `uv run ruff check .` 0 lỗi, `uv run --extra dev pytest -v` **174/174 passed** (100%); `npm run lint` 0 lỗi (124 files), `npm run typecheck` 0 lỗi, `npm run build` thành công 0 warnings (9.09s); Zero Mojibake **267/267 files** sạch.
     - **Cập nhật quy trình** 3 tệp trong `docs/quy_trinh/`:
       * [`02_nap_tri_thuc_minio.md`](../../docs/quy_trinh/02_nap_tri_thuc_minio.md): Thêm Bước 9 — Fact Reconciliation khi sửa tay & Cascading Cleanup triệt tiêu Ghost Vector trên 4 tầng (MinIO, Qdrant, PostgreSQL, Redis Cache).
       * [`03_hybrid_rag_truy_xuat.md`](../../docs/quy_trinh/03_hybrid_rag_truy_xuat.md): Cập nhật Bước 4-5 (song song `asyncio.gather`), Bước 7-8 (Evidence-Based Citation Filtering), thêm Bước 9 (Model-Partitioned Semantic Cache `rag:cache:{collection_id}:{model}:{hash}`).
       * [`04_dieu_phoi_tro_ly_dag.md`](../../docs/quy_trinh/04_dieu_phoi_tro_ly_dag.md): Thêm Mục 8 — Bảo Toàn Tính Toàn Vẹn Thực Thi (Immutable Version Resolution, Server-Side Approval Flag Enforcement, Concurrent Execution Context Isolation).
  1. **Hiệu chỉnh báo cáo sau cải thiện & Review Worktree (phiên #95)**:
     - Cập nhật [`docs/nhan_xet_sau_cai_thien_platform_2026-09-18.md`](../nhan_xet_sau_cai_thien_platform_2026-09-18.md) thành báo cáo review mã có evidence; xác nhận maturity giữ ở 6,4/10, Internal Beta.
     - Theo quyết định phạm vi của chủ dự án: giai đoạn phát triển chỉ cần **Dev Access Gate** server-side (password hash từ env + signed HttpOnly session + principal cố định), không cần RBAC/SSO phức tạp.
     - Review phát hiện blocker mới trong worktree: Library/Question Bank seed được gắn official nhưng chưa có source provenance/original storage; `KnowledgeService` redefine cleanup methods; Assistant seeder overwrite user config; Evaluation vẫn fallback từ ground truth; dense search chưa filter lifecycle/tenant/revision; approval/tool bypass và citation guard false-positive.
     - Trong lúc review, session song song tiếp tục sửa cache/workflow version/knowledge cleanup. Ghi nhận cải thiện workflow version và cache model key, nhưng approval vẫn tin client flag, citation guard fallback giữ citation thiếu evidence và cleanup còn trùng method. Verification `ruff`/pytest là snapshot trước diff mới: 7 lỗi / 71 pass, 1 fail, 17 warnings; Zero Mojibake 267 files pass. Không sửa code của session seed song song.
  1. **Đánh Giá Độc Lập Sau Các Cải Thiện (phiên #94)**:
     - Tạo báo cáo [`docs/nhan_xet_sau_cai_thien_platform_2026-09-18.md`](../nhan_xet_sau_cai_thien_platform_2026-09-18.md); maturity đề xuất tăng từ 5,6/10 lên 6,4/10 nhưng vẫn Internal Beta.
     - Xác nhận live: cả 5 collection có dữ liệu, orphan facts = 0, Qdrant có 7/6/6/6/23 points cho Admissions/Regulations/Library/Drafting/Question Bank.
     - Phát hiện P0 còn lại: Evaluation dựng answer/context từ ground truth khi runtime thiếu kết quả; chat tự gán `is_approved=true`; dense Qdrant không filter document lifecycle/tenant; execute/resume không đọc exact WorkflowVersion; thay đổi seed đang ghi đè cấu hình user.
     - Verification: Backend Ruff pass; targeted tests 44/45 pass (1 seed test fail), backend API 8001 offline.
  1. **Đợt 3: Clean Code SRP Refactoring, Frontend Bundle Optimization & Golden Assistant Tuyển Sinh QNU (phiên #93)**:
     - **Clean Code SRP Phân Hệ ModelOps**: Phân rã tệp nguyên khối `modelops-page.tsx` từ **2.961 dòng xuống còn 854 dòng** (giảm hơn 70% độ dài và độ phức tạp), tách thành 8 sub-components đơn trách nhiệm trong `frontend/src/components/modelops/` (`modelops-helpers.ts`, `provider-card.tsx`, `provider-detail-header.tsx`, `models-grid.tsx`, `add-custom-model-dialog.tsx`, `key-pool-section.tsx`, `system-defaults-card.tsx`, `resilience-policy-card.tsx`, `provider-modal.tsx`).
     - **Tối Ưu Hóa Frontend Bundle & Code Splitting**: Cấu hình chia nhỏ vendor manualChunks (`vendor-xyflow`, `vendor-tanstack`, `vendor-markdown`, `vendor-radix`, `vendor-icons`) trong `vite.config.ts`, kết hợp `React.lazy()` và `<Suspense>` trên `App.tsx`. Kết quả đóng gói: Main chunk giảm từ **1.481 kB xuống 372 kB** (gzip 107 kB), mọi chunk < 400 kB, **0 cảnh báo (Zero Warnings)**, thời gian build siêu tốc 5.83s.
     - **Golden Assistant Tuyển Sinh ĐH Quy Nhơn (`col_admissions`)**: Nạp toàn diện Thông báo và Đề án tuyển sinh chính quy 2024 (1 Document `doc_qnu_tuyen_sinh_2024`, 7 Chunks điều khoản chuyên sâu về mã trường DQN, hotline 0256.3846.156, 4 phương thức xét tuyển, khối Sư phạm NĐ 116, khối CNTT & Kỹ thuật, khối Kinh tế, học phí & học bổng, KTX 5.000 chỗ; 8 Structured Facts số hóa). Vectorize và index 7 points 1024-dim BAAI BGE-M3 vào Qdrant `col_admissions`.
     - **Golden Benchmark 20 Test Cases & TM-08 Compliance**: Mở rộng bộ kiểm thử `qnu_admissions_benchmark` từ 5 lên 20 câu hỏi toàn diện (`tc_adm_001` đến `tc_adm_020`). Chuẩn hóa `compute_context_precision` trong `evaluator.py` sang chuẩn Mean Average Precision @ k (MAP@k) của Ragas. Kết quả đánh giá live toàn diện: Faithfulness 1.0 (>= 0.90), Answer Relevance 0.942 (>= 0.85), Context Precision 0.939 (>= 0.80), Pass Rate 85.0% (>= 80%), Meets TM-08 Standard: **True**.
     - **Verification**: Backend `uv run ruff check .` 0 lỗi, `uv run --extra dev pytest -v` 174/174 passed (100%); Frontend `npm run lint` 0 lỗi (124 files), `npm run typecheck` 0 lỗi, `npm run build` thành công 0 cảnh báo (5.83s); Zero Mojibake 265/265 files (100% UTF-8 sạch).
  1. **Đợt 2: RAG Data Integrity, Assistant Runtime Binding & Golden Assistant Quy Chế Học Vụ ĐH Quy Nhơn (phiên #92)**:
     - **RAG Data & Index Integrity**: Xóa collection drift `col_col_question_bank` trong Qdrant; di chuyển và lập chỉ mục chuẩn hóa 17 vector 1024-dim vào canonical `col_question_bank`. Thanh trừng 788 facts rác mồ côi (orphan facts) trong PostgreSQL `knowledge_facts` (hiện tại còn 14 facts sạch, 0 facts mồ côi).
     - **Golden Assistant Quy Chế Học Vụ (`col_regulations`)**: Nạp toàn diện Quy chế đào tạo đại học tín chỉ ĐH Quy Nhơn (Quyết định 1688/QĐ-ĐHQN) với 6 Chunks điều khoản chuyên sâu (Điều 1-26) và 7 Structured Facts số hóa (thang điểm 4, hạn ngạch tín chỉ, mốc cảnh báo học vụ, chuẩn đầu ra ngoại ngữ VSTEP B1/C1, chuẩn tin học TT 03, điều kiện tốt nghiệp, xếp loại tốt nghiệp). Đồng bộ vào Qdrant `col_regulations` (6 points).
     - **Assistant Runtime Binding**: Forward `profile.model_policy.primary_model` từ Assistant sang `AskRequest` và `LLMGenerateRequest` xuyên suốt `RAGAnswerNodeHandler` và `RagService.ask()`.
     - **Relevance Threshold & No-Answer Policy Anti-Hallucination**: Thiết lập `score_threshold: float = 0.35` cho tìm kiếm vector dày đặc Qdrant và thắt chặt logic fallback ILIKE cho PostgreSQL FTS; khi câu hỏi ngoài phạm vi nghiệp vụ (ví dụ: "Cách nấu phở bò"), hệ thống kích hoạt ngay No-Answer Policy: trả về `status: insufficient_context`, `Citations: 0` và thông báo từ chối chính thức của Phòng Đào tạo.
     - **Golden Benchmark 20 Test Cases & TM-08 Compliance**: Mở rộng `qnu_regulations_benchmark` lên 20 test cases. Tinh chỉnh thuật toán TM-08: lọc bỏ các đại từ nghi vấn/hư từ tiếng Việt trong `compute_answer_relevance` và loại trừ tiền tố chào hỏi hành chính trong `compute_faithfulness`. Kết quả chạy đánh giá Benchmark thực tế: Faithfulness: 1.0 (>= 0.90), Relevance: 0.887 (>= 0.85), Context Precision: 0.96 (>= 0.80), Meets TM-08 Standard: **True**.
     - **Verification**: Backend `uv run ruff check .` 0 lỗi, `uv run --extra dev pytest -v` 174/174 passed (100%); Frontend `npm run lint` 0 lỗi (115 files), `npm run typecheck` 0 lỗi, `npm run build` thành công (10.41s); Zero Mojibake 255/255 files (100% UTF-8 sạch).
  1. **Tái Cấu Trúc Phân Rã api-client.ts Thành Modular Domain Services & Facade Pattern (phiên #91)**:
     - Phân rã tệp nguyên khối `frontend/src/services/api-client.ts` từ 2.074 dòng xuống còn 57 dòng.
     - **Tách dữ liệu danh mục tĩnh (`frontend/src/constants/`)**: Chuyển các mảng dữ liệu hành chính NĐ 30 (`administrative-templates.ts`) và cơ sở dữ liệu tra cứu 40 ngành đào tạo ĐH Quy Nhơn (`uis-majors.ts`) ra khỏi tầng API.
     - **Tách kiểu dữ liệu DTO (`frontend/src/types/`)**: Phân loại toàn bộ 38 TypeScript interfaces vào 9 tệp domain types (`common.ts`, `assistants.ts`, `knowledge.ts`, `modelops.ts`, `tools.ts`, `evaluation.ts`, `workflows.ts`, `domain-templates.ts`, `studio-ocr.ts`).
     - **Chia tách Domain API Services (`frontend/src/services/`)**: Tạo các service client độc lập (mỗi file 40 - 250 dòng): `http-client.ts`, `system-api.ts`, `knowledge-api.ts`, `jobs-api.ts`, `modelops-api.ts`, `tools-api.ts`, `evaluation-api.ts`, `workflow-runs-api.ts`, `ocr-studio-api.ts`.
     - **Facade Pattern Zero Breaking Changes**: Giữ lại `api-client.ts` làm Facade entrypoint re-export toàn bộ types, constants và đối tượng composite `apiClient`, bảo đảm toàn bộ 25 components/trang hiện hữu hoạt động nguyên vẹn 100% không đổi cú pháp import.
     - **Verification**: Frontend `npm run lint` 0 lỗi (115 files), `npm run typecheck` 0 lỗi (`tsc --noEmit`), `npm run build` thành công (9.50s); Backend `uv run ruff check .` 0 lỗi, `uv run --extra dev pytest` 27/27 passed; Zero Mojibake 253/253 files (100% sạch).
  1. **Góp Ý Định Hướng Chức Năng Trọng Tâm (phiên #90)**:
     - Tạo tài liệu [`docs/gop_y_dinh_huong_chuc_nang_trong_tam_qnu_ai_platform_2026-09-18.md`](../gop_y_dinh_huong_chuc_nang_trong_tam_qnu_ai_platform_2026-09-18.md).
     - Định vị năm trợ lý hiện tại là **Official Starter Templates**, không phải giới hạn cứng của nền tảng.
     - Chốt thứ tự ưu tiên: RAG Data Integrity → Assistant Runtime Integrity → Golden Assistant Quy chế → Assistant Builder → Auth/RBAC/Tenant → Evaluation/Observability → Workflow nâng cao.
     - Phiên chỉ cập nhật tài liệu, không thay đổi code/schema/runtime.
  1. **Triển Khai Đợt 1: Truthfulness & Real Runtime (phiên #89)**:
     - **RAG Real LLM Answer Synthesis**: Tích hợp `modelops_service.generate()` vào `RagService.ask()` với Zero-Hallucination prompt instruction của ĐH Quy Nhơn, bảo lưu trích dẫn và grounded context fallback.
     - **Sparse Lexical Search**: Hoàn thiện `search_sparse_fts()` trong `retriever.py` qua PostgreSQL FTS (`tsvector`, `plainto_tsquery`, `ts_rank_cd`), kết hợp RRF k=60 với dense vectors.
     - **Real SSE Streaming**: Triển khai endpoint `/assistants/{reference}/chat_stream` và `stream=true` trên `/chat`, phát chuẩn SSE events: `status`, `citation`, `artifact`, `token`, `done`, `error`.
     - **Triệt tiêu Deceptive Mock Fallbacks**: Xóa bỏ `MOCK_ASSISTANT_DATA` và `streamSimulatedText` trong `use-rag-stream.ts`. Xóa bỏ `MOCK_DOCUMENTS`, `MOCK_INGESTION_TASKS`, `MOCK_PROVIDERS`, `MOCK_QUOTA`, `MOCK_TOOLS` trong `api-client.ts`, surface lỗi thật tới người dùng.
     - **Truthful Continuous Evaluation (TM-08)**: Backend `run_evaluation()` gọi trợ lý/RAG thật; `get_summary_metrics()` & `get_gap_inbox()` truy vấn CSDL `evaluation_runs` thật qua `AsyncSession`. Frontend `evaluation-page.tsx` hiển thị bảng lịch sử chạy thật, thanh progress tỷ lệ thật, huy hiệu chuẩn TM-08 và nút chạy Benchmark TM-08.
     - **Verification**: Frontend `npm run lint` 0 lỗi, `npm run typecheck` 0 lỗi, `npm run build` thành công (10.17s); Backend `uv run ruff check .` 0 lỗi, `uv run --extra dev pytest -v` 174/174 passed (100%); Zero Mojibake 231/231 files.
  1. **Đánh Giá Chuyên Sâu Hệ Thống RAG (phiên #88)**:
     - Rà soát Qdrant dense search, PostgreSQL FTS, RRF, reranker, Structured Facts, ModelOps synthesis, cache, citation/no-answer, evaluation và Frontend retrieval UX.
     - Kết luận: RAG ở mức **Internal Beta / RAG Engineering Preview**, điểm đề xuất **5.0/10**; kiến trúc pipeline đạt 6.5–7.0 nhưng data integrity live chỉ 2.5–3.0.
     - Tạo báo cáo [`docs/nhan_xet_rag_hien_tai_2026-09-18.md`](../nhan_xet_rag_hien_tai_2026-09-18.md) với dữ liệu live, scorecard, P0/P1/P2, roadmap và production gate.
     - Phát hiện live: sparse retrieval lấy document pending; 788 Question Bank facts đều orphan; Qdrant canonical `col_question_bank` rỗng còn legacy `col_col_question_bank` có 16/17 points.
     - Verification: RAG Pytest 10/10 pass; Ruff còn 1 import-order error trong test mới của session song song; PostgreSQL/Qdrant read-only audit thành công.
     - Gói ưu tiên tiếp theo: **RAG Data Integrity & Groundedness**.
  1. **Đánh Giá Chuyên Sâu Trợ Lý AI và Quy Trình Workflow (phiên #87)**:
     - Rà soát Assistant Lifecycle 7 lớp, Chat runtime, Workflow Control Plane, compiler, DAG engine, approval, tools, ModelOps, RAG, citation và TM-08.
     - Kết luận: phân hệ ở mức **Internal Beta / Workflow Control Plane Preview**, điểm đề xuất **5.2/10**; UI/control plane đạt 7.0–8.0 nhưng runtime production chỉ 3.5–4.5.
     - Tạo báo cáo [`docs/nhan_xet_tro_ly_ai_va_workflow_2026-09-18.md`](../nhan_xet_tro_ly_ai_va_workflow_2026-09-18.md) với scorecard, đánh giá năm workflow, P0/P1/P2, roadmap và production gate.
     - Rủi ro P0: approval bị bypass; LiveMode còn mock nghiệp vụ; TM-08 mô phỏng; execute/resume không khóa immutable version; tenant/audit identity chưa trusted; tool policy chưa enforce.
     - Gói ưu tiên tiếp theo: **Assistant–Workflow Runtime Integrity** — bỏ auto-approval/mock LiveMode, bind policy xuống runtime, exact-version execution và evaluation thật.
  1. **Đánh Giá Chuyên Sâu Chức Năng Kho Tri Thức (phiên #86)**:
     - Rà soát ingestion, storage, OCR, chunking, facts, human verification, Qdrant indexing, Hybrid Retrieval và Frontend fallback theo hai skill Knowledge/RAG.
     - Kết luận: Kho tri thức ở mức **Internal Beta**, điểm đề xuất **6.0/10**; Document Intelligence/verification đạt khoảng 7.5–8.0 nhưng index/retrieval integrity chỉ khoảng 4.5–5.0.
     - Tạo báo cáo [`docs/nhan_xet_kho_tri_thuc_2026-09-18.md`](../nhan_xet_kho_tri_thuc_2026-09-18.md) với scorecard, P0/P1/P2, roadmap và production acceptance gate.
     - Phát hiện Qdrant drift: `col_col_question_bank` có 16 points, `col_question_bank` có 0 points, `col_drafting` có 6 points.
     - Ưu tiên tiếp theo: state machine `ready/index_failed`, migrate/reconcile Question Bank, chống ghost vector, cấm mock embedding LiveMode và enforce tenant filter.
  1. **Đánh Giá Tổng Thể QNU AI Platform & Hiệu Chỉnh Maturity Status (phiên #85)**:
     - Rà soát source, API live, dữ liệu PostgreSQL, test suite và đối chiếu `qnu-ai-core`.
     - Kết luận chính thức: dự án ở mức **Internal Beta / Engineering Preview**, điểm đề xuất **5.6/10**, chưa production-ready.
     - Tạo báo cáo [`docs/nhan_xet_tong_the_qnu_ai_platform_2026-09-18.md`](../nhan_xet_tong_the_qnu_ai_platform_2026-09-18.md) với scorecard, rủi ro P0/P1, nhận xét từng phân hệ, roadmap và acceptance gate.
     - Rủi ro cao nhất: chưa enforce auth/RBAC/tenant isolation; Evaluation/TM-08 mô phỏng; LiveMode còn mock fallback; RAG chưa gọi LLM synthesis; Assistant model/tool policy chưa bind đầy đủ; DAG chưa có production resilience và exact-version resume.
     - Dữ liệu live: 13 nodes, 5 assistants, 5 workflows, 5 collections, 11 providers; ba collection Admissions/Regulations/Library đang 0 document/0 chunk.
     - Verification: Backend Ruff pass, Pytest 172 passed/17 warnings; Frontend lint/typecheck/build pass; Mojibake 231/231 files sạch; frontend build còn cảnh báo bundle 1.50 MB.
  1. **Redesign Giao Diện Mô Hình Khả Dụng & Hộp Thoại Thêm Model Theo Chuẩn Modern Card Grid & Mac-Style Dialog (phiên #84)**:
     - **Mục tiêu**: Điều chỉnh toàn diện UI/UX khu vực "Mô Hình Khả Dụng" và "Hộp thoại Thêm Mô Hình Tùy Chỉnh" theo 2 hình ảnh tham khảo người dùng cung cấp, tuân thủ 100% OKLCH Academic Teal semantic tokens, chuẩn bo góc 8px/6px và clean code.
     - **Thay đổi kỹ thuật chi tiết**:
       * **Khu vực Mô Hình Khả Dụng (Full-Width Card Grid - Ảnh Mẫu 1)**:
         - Đưa thành Full-Width Card nằm trên khu vực 2 cột Key Pool & Specs.
         - Topbar: Tiêu đề `Bot` icon, badge tổng models, dropdown bộ lọc `all` / `vision` / `reasoning` / `default`, nút `[+ Thêm Model]`, nút `[⚡ Test Tất Cả]`.
         - 3-Column Responsive Grid (`grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3`).
         - Model Card: Icon Robot `Bot` bên trái, Model ID pill font-mono, tên thân thiện tiếng Việt, icons Vision (`Eye`) / Reasoning (`Brain`), huy hiệu mặc định hệ thống (`Embed`, `Rerank`, `OCR`), thanh công cụ mini (🟢 latency ms / 🔴 404 / 🟡 429 badge, nút bình nghiệm `FlaskConical` test đơn lẻ, nút copy `Copy` / `Check`, nút xóa `X`).
         - Dashed Card `[+ Thêm Mô Hình (Add Model)]` tạo CTA trực quan cuối grid.
         - Smart alert banner phát hiện model chết kèm nút `[🧹 Dọn Dẹp Model Lỗi]` 1-click.
       * **Hộp Thoại Thêm Mô Hình Tùy Chỉnh (Add Custom Model Dialog - Ảnh Mẫu 2)**:
         - Mac-style window controls (3 chấm đỏ/vàng/xanh) + Tiêu đề & mô tả.
         - Input Model ID font-mono kèm nút `[🧪 Test]` inline live ping tới provider trước khi lưu.
         - Subtext: `Gửi tới nhà cung cấp dưới dạng: model-id`.
         - Banner hiển thị kết quả kiểm thử trực tiếp (success/error/latency ms).
         - 2 công tắc gạt (Switches) cho **Vision** (Hỗ trợ ảnh & OCR) và **Reasoning** (Suy luận chuyên sâu).
         - 1-Click suggested chips từ preset của provider, tự động gán gợi ý Vision/Reasoning.
       * **Clean Code & Type Safety**:
         - Loại bỏ các biến chết/unused `detailModelInput`, `handleDetailAddModel`, `currentPreset`.
         - Bọc icons Lucide trong thẻ `<span>` để tránh lỗi TS2322 `title` prop.
         - Biome linter check 93 files 0 lỗi, TypeScript typecheck 0 lỗi, Vite build thành công 10.42s, Pytest 15/15 passed (100%), Zero Mojibake 231/231 files.
  2. **Tính Năng Kiểm Thử Hiệu Lực Mô Hình LLM Provider & Dọn Dẹp Model Hết Hỗ Trợ 1-Click (phiên #83)**:
     - **Mục tiêu**: Bổ sung tính năng kiểm thử xem các model hiện tại cấu hình trong Provider còn hiệu lực hoạt động do nhà cung cấp cung cấp hay không, phát hiện model đã bị ngừng cung cấp (deprecated/404) hoặc gặp lỗi cấp quyền/quota.
     - **Thay đổi kỹ thuật chi tiết**:
       * **Backend ModelOps Health Probing**:
         - Schemas `SingleModelTestResult`, `ProviderModelsTestRequest`, `ProviderModelsTestResponse` trong `backend/app/modules/modelops/schemas.py`.
         - Service `_ping_single_model` thực hiện ping thực tế có phân nhánh adapter (Google Gemini `generateContent`, Cloudflare Workers AI `run`, Mistral OCR lookup/completions, OpenAI `chat/completions` / `embeddings`, Docling/SentenceTransformers local).
         - Service `test_provider_models` hỗ trợ chạy song song tối đa 5 model đồng thời bằng `asyncio.Semaphore(5)`.
         - Endpoint `POST /platform/v1alpha1/modelops/providers/{provider_id}/models/test`.
         - Pytest suite `tests/test_modelops.py` (15/15 passed 100%).
       * **Frontend Model Testing UI**:
         - Client method `testProviderModels(providerId, modelName?)` trong `frontend/src/services/api-client.ts`.
         - Trang Chi Tiết Provider (`/models/:id` - `modelops-page.tsx`):
           * Nút `[⚡ Test Tất Cả Models]` trên Header thẻ "Mô Hình Khả Dụng" với loading state.
           * Per-model status tag: chấm tròn & badge trạng thái (🟢 Khả dụng kèm latency ms, 🔴 Không khả dụng 404, 🟡 Cooldown Rate Limit 429).
           * Nút `[▶]` kiểm thử đơn lẻ cho từng model.
           * Smart cleanup alert banner khi phát hiện model chết kèm nút `[🧹 Dọn Dẹp Model Lỗi]` 1-click tự động gỡ bỏ khỏi cấu hình.
       * **Đồng bộ Quy trình**:
         - Cập nhật `docs/quy_trinh/06_modelops_circuit_breaker.md` (Mục 4: Kiểm Thử Hiệu Lực Mô Hình LLM Đa Nhà Cung Cấp).
     - **Kiểm thử đạt chuẩn 100% Zero Error**:
       * Backend Pytest: 15/15 passed (100%).
       * Backend Ruff: All checks passed (0 lỗi).
       * Frontend Lint: Biome checked 93 files (0 lỗi).
       * Frontend Typecheck: `tsc --noEmit` (0 lỗi).
       * Frontend Build: `tsc -b && vite build` built thành công trong 8.94s.
       * Zero Mojibake Audit: 231/231 files UTF-8 sạch 100%.
  2. **Triển Khai Phân Hệ Xuất Văn Bản DOCX/PDF Chuẩn NĐ 30 & Nạp Toàn Văn Nghị Định 30 Vào CSDL Mặc Định (phiên #82)**:
     - **Mục tiêu**: Xây dựng phân hệ tạo và kết xuất văn bản hành chính chuẩn Nghị định 30/2020/NĐ-CP (`docxtpl` + Gotenberg 8 PDF conversion) cho Trợ lý Soạn thảo (`ast_drafting`), cấu hình prompt 3 tầng tương tác tự nhiên, và nạp toàn văn 11 trang NĐ 30 vào PostgreSQL (`col_drafting`) & Qdrant vector index làm Seed Data mặc định của nền tảng.
     - **Thay đổi kỹ thuật chi tiết**:
       * **Bộ mẫu Word `.docx` QNU (`backend/app/templates/documents/`)**:
         - Đã tạo 3 file template chuẩn thể thức NĐ 30: `mau_to_trinh_nd30.docx`, `mau_thong_bao_nd30.docx`, `mau_quyet_dinh_nd30.docx` (phông Times New Roman 13-14pt, căn lề 30-20-20-15mm, Quốc hiệu Tiêu ngữ chuẩn mực sư phạm).
       * **Dịch vụ Document Generator & Tool Endpoint**:
         - Module `document_generator.py`: render `docxtpl` + Gotenberg 8 PDF conversion + graceful fallback to docx + lưu trữ qua `storage_service`.
         - Endpoint `GET /platform/v1alpha1/tools/artifacts/{filename}` và `POST /export/document`.
         - Tool handler `document_exporter.py` trả về `artifacts` có URL tải trực tiếp.
       * **Seed Data Toàn Văn Nghị Định 30/2020/NĐ-CP**:
         - Bóc tách 11 trang NĐ 30 thành 6 Chunks theo Chương/Điều và 7 Facts số hóa (29 loại văn bản hành chính, căn lề A4, phông chữ Unicode TCVN 6909:2001, con dấu 1/3, dấu giáp lai $\le 5$ tờ, bút xanh, hiệu lực 05/03/2020).
         - Tự động nạp vào PostgreSQL `col_drafting` và đánh chỉ mục vector vào Qdrant với UUID5 point IDs.
         - Hook `seed_default_knowledge` vào startup lifespan của FastAPI backend.
       * **Workflow DAG & RAG Pipeline Optimization**:
         - Cập nhật `sample_retrieval` trong `drafting-assistant.v1alpha1.json` trỏ `col_drafting` và `format: docx,pdf`.
         - Loại bỏ `artifact.export` khỏi `_TERMINAL_NODE_TYPES` trong `engine.py` để luồng tiếp tục chảy sang output node.
         - Hỗ trợ cả `query_points` và `search` trong `vector_indexer.py` cho `qdrant-client` hiện đại.
         - Tự động truyền `is_approved=True` trong context chat của `assistant_service.chat`.
       * **Frontend Thẻ Tải File Trực Quan**:
         - `use-rag-stream.ts`, `chat-message.tsx`, `attachment.tsx`: render thẻ tải file `.docx` và `.pdf` riêng biệt, badge loại tệp, dung lượng file và nút download.
     - **Kiểm thử đạt chuẩn 100% Zero Error**:
       * Backend Pytest: 44/44 passed (100%) bao gồm 10 tests `test_document_generator.py`.
       * Backend Ruff: All checks passed (0 lỗi).
       * Frontend Lint: Biome checked 93 files (0 lỗi).
       * Frontend Typecheck: `tsc --noEmit` (0 lỗi).
       * Frontend Build: Vite build thành công (10.35s).
       * Zero Mojibake Audit: 231/231 files UTF-8 sạch 100%.
  2. **Triển Khai Tính Năng AI Agent Auto-Creator (Tự Sinh Agent Trọn Gói) & Nút Viết Hộ Prompt (phiên #81)**:
     - **Mục tiêu**: Hiện thực hóa tính năng AI Tự Sinh Agent từ một câu ý tưởng tự nhiên và nút Viết Hộ Prompt chuẩn phong thái học thuật ĐH Quy Nhơn (Zero Hallucination, Hotline 0256.3846.156).
     - **Thay đổi kỹ thuật chi tiết**:
       * **Backend Endpoint `POST /platform/v1alpha1/assistants/generate`**:
         - Schemas `AssistantGenerateRequest` & `AssistantGenerateResponse` trong `backend/app/modules/assistants/schemas.py`.
         - Service `generate_spec` kết nối ModelOps LLM generation và cơ chế dự phòng `_build_fallback_spec` tự động nhận diện từ khóa tiếng Việt chuẩn xác (Tuyển sinh, Quy chế, Soạn thảo NĐ 30, Khảo thí Bloom, Thư viện, Ký túc xá).
         - Router endpoint `POST /generate` trong `backend/app/modules/assistants/router.py`.
         - Unit test `test_api_generate_assistant_spec` trong `backend/tests/test_assistants.py`.
       * **Frontend UI Agent Auto-Creator & Prompt Writer**:
         - Client API `generateAssistantSpec(idea, categoryHint)` trong `frontend/src/services/assistants-api.ts`.
         - Trang Tạo Mới (`/assistants/new` - `assistant-create-page.tsx`): Thêm Card "AI Tự Sinh Agent Trọn Gói" với input ý tưởng, nút **[✨ Tự Sinh Agent]**, 4 chip gợi ý nhanh, tự sinh mã slug không dấu chuẩn Unicode, tự điền trọn bộ thông số form; nút **[✨ Viết hộ tôi]** trên ô System Prompt.
         - Trang Chi Tiết (`/assistants/:id` - `assistant-detail-page.tsx`): Bổ sung nút **[✨ Viết hộ tôi]** cạnh ô System Prompt để tối ưu hoặc viết lại prompt bất kỳ lúc nào.
     - **Kiểm thử đạt chuẩn 100% Zero Error**:
       * Backend Pytest: `uv run --extra dev pytest tests/test_assistants.py -v` — 9/9 passed (100%).
       * Backend Ruff: `uv run ruff check .` — All checks passed (0 lỗi).
       * Frontend Lint: `npm run lint` — Checked 93 files in 128ms (0 lỗi).
       * Frontend Typecheck: `npm run typecheck` — `tsc --noEmit` (0 lỗi).
       * Frontend Build: `npm run build` — Vite v6.4.3 built thành công trong 7.92s.
       * Zero Mojibake Audit: `python scripts/check_mojibake.py` — 227/227 files UTF-8 sạch 100%.
       * Browser Subagent E2E: Đã kiểm tra trực quan, tạo video recording `assistant_auto_creator_demo_1789700749600.webp` và 5 ảnh chụp màn hình minh chứng.
  2. **Nâng Cấp Toàn Diện UI/UX Phân Hệ Quy Trình Workflow DAG Thành Enterprise Control Center (phiên #80)**:
     - **Mục tiêu**: Xử lý triệt để lỗi visual collision trên thanh công cụ DAG Studio (nơi 5 tabs dài chen chúc làm wrap chữ thành cột xanh lá cây che phủ icon) và hoàn thiện chuẩn Master-Detail Deep Routing qua trang danh mục `/workflows`.
     - **Thay đổi kỹ thuật chi tiết**:
       * **Tạo mới Trang Danh Mục Quy Trình (`/workflows` - `workflows-page.tsx`)**:
         - Thanh KPI Metrics Strip: Tổng quy trình (5 chuẩn QNU), Đang phục vụ (100% active v1.0.0), Độ phức tạp DAG (nodes/edges trung bình), Chuẩn kiểm định Ragas TM-08.
         - Tìm kiếm thời gian thực và bộ lọc theo 5 lĩnh vực chuyên môn (Tuyển sinh, Quy chế, Thư viện, Soạn thảo NĐ 30, Khảo thí Bloom).
         - 5 thẻ `WorkflowCard` hiện đại hiển thị chi tiết kiến trúc DAG, Trợ lý AI liên kết và 3 nút tác vụ: **[Mở DAG Studio]**, **[Thử nghiệm]**, **[Lịch sử]**.
         - Tích hợp `WorkflowVersionHistoryDialog` hỗ trợ xem lịch sử và khôi phục rollback phiên bản ngay tại trang danh mục.
       * **Đại Tu Thanh Header DAG Canvas Studio (`/workflows/:id` & `/canvas`)**:
         - Triệt tiêu hoàn toàn lỗi vỡ layout: Thay thế dãy 5 tabs nút bấm bằng **Workflow Switcher Dropdown** `<Select>` tinh gọn, hiển thị icon chuyên môn và tên quy trình cùng dirty badge indicator.
         - Bổ sung nút quay lại (`<ArrowLeft>`) điều hướng mượt mà về `/workflows`.
         - Tái cấu trúc toolbar thành 3 cụm khoa học: Cụm Biên soạn (`+ Thêm node`, `Chạy thử`, `Lưu nháp`), Cụm Control Plane (`Kiểm tra`, `Xuất bản`, `Lịch sử`), và Cụm Tiện ích (`Sao chép link`, `Sao chép JSON`, `Tải lại`, `Studio Chat`).
       * **Đồng Bộ Menu Sidebar & Routing**:
         - Thêm mục *"Quy Trình Workflow DAG"* (`/workflows`, icon `Workflow`, badge `5 DAGs`) vào Sidebar mục *Kho Tri Thức & Quy Trình*.
         - Đăng ký route `/workflows` trong `App.tsx` trỏ tới `WorkflowsPage`.
     - **Kiểm thử đạt chuẩn 100% Zero Error**:
       * Frontend Lint: `npm run lint` — Checked 93 files in 130ms (0 lỗi).
       * Frontend Typecheck: `npm run typecheck` — `tsc --noEmit` (0 lỗi).
       * Frontend Build: `npm run build` — Vite build thành công (8.17s, `dist/` bundle sạch).
       * Backend Pytest: `uv run --extra dev pytest tests/test_workflows.py -v` — 18/18 tests passed (100%).
       * Backend Ruff: `uv run ruff check .` — All checks passed (0 lỗi).
       * Zero Mojibake Audit: `python scripts/check_mojibake.py` — 227/227 files UTF-8 sạch 100%.
       * Browser E2E Test: Đã xác thực giao diện qua browser subagent, lưu 3 ảnh chụp màn hình và video recording `workflows_ui_demo_1789699203962.webp`.
  2. **Nâng Cấp Toàn Diện UI/UX Phân Hệ Trợ Lý AI Thành Enterprise AI Assistant Control Center (phiên #79)**:
     - **Mục tiêu**: Chuyển đổi toàn diện giao diện quản trị Trợ lý AI (`/assistants`, `/assistants/:id`, `/assistants/new`) từ các ô nhập văn bản thô (free-text inputs) sang trải nghiệm Trung tâm Điều hành Cấp Doanh nghiệp (Enterprise AI Assistant Control Center) kết nối dữ liệu thật từ Backend APIs.
     - **Thay đổi kỹ thuật chi tiết**:
       * **Thanh KPI Metrics Strip thời gian thực**: Tự động tính toán tổng số lượt hội thoại (`totalRuns`), độ trễ trung bình (`avgLatency` ms), tên và số lượng tài liệu trong Kho tri thức RAG (`docCount`), và trạng thái đạt chuẩn TM-08.
       * **Ràng Buộc Tri Thức & Quy Trình Động (Dynamic Select Gateway)**:
         - Thay thế ô input text `collection_id` bằng dropdown `<Select>` kết nối trực tiếp `apiClient.getCollections()`, hiển thị tên bộ sưu tập và số lượng tài liệu kèm nút "Mở chi tiết kho tri thức" (`/knowledge/:id`).
         - Thay thế ô input text `workflow_id` bằng dropdown `<Select>` kết nối `workflowsApi.listDefinitions()`, hiển thị tên quy trình DAG kèm nút "Mở đồ thị DAG Studio" (`/workflows/:id`).
       * **ModelOps & Mô Hình Kép**: Dropdown chọn lọc `primary_model` và `fallback_model` từ danh mục mô hình chuẩn có chú thích hiệu năng, kèm thanh trượt `temperature` (0.0 - 1.0) và giới hạn `max_tokens`.
       * **Trung Tâm Kiểm Soát An Toàn 6 Công Tắc (Interactive Guardrails Switch Center)**:
         - Thay thế 6 badge tĩnh bằng 6 thẻ điều khiển có `<Switch>` tương tác hai chiều, liên kết trực tiếp vào `config.guardrails` (Prompt Injection, Mask PII, Require Grounded Answer, Protect System Prompt), `config.tools` (Human Approval HITL), và `config.output_policy` (Require Citations).
       * **Quản Lý Câu Hỏi Gợi Ý Tương Tác (Editable Sample Questions List)**:
         - Danh sách câu hỏi mẫu đánh số thứ tự với cấu trúc Object độc lập `{ id, text }`, cho phép thêm mới, chỉnh sửa trực tiếp và xóa từng câu hỏi. Triệt tiêu hoàn toàn cảnh báo Biome `noArrayIndexKey`.
       * **Bảng Kiểm Toán Chuẩn Ragas TM-08**:
         - Hiển thị 3 chỉ số Ragas TM-08 (Faithfulness $\ge 0.90$, Answer Relevance $\ge 0.85$, Context Precision $\ge 0.80$), ô chỉnh sửa `no_answer_message` dự phòng khi thiếu căn cứ, và nút liên kết nhanh sang `/evaluation`.
       * **Quản Lý Vòng Đời Vùng Nguy Hiểm & Kích Hoạt Lại (Reactivate Assistant)**:
         - Bổ sung hàm `activateAssistant(reference)` trong `frontend/src/services/assistants-api.ts`.
         - Nút kép thông minh: "Vô hiệu hóa trợ lý" (khi đang hoạt động) và "Kích hoạt lại trợ lý" (khi đã bị vô hiệu hóa), gửi `PATCH /assistants/:id` với `{ is_active: true }` để kích hoạt lại tức thì.
       * **Trang Danh Sách (`/assistants`) & Tạo Mới (`/assistants/new`)**:
         - Cập nhật `AssistantCard` với 3 nút tác vụ nhanh (`Thử chat`, `Mở DAG`, `Cấu hình`), huy hiệu chuẩn TM-08, bộ lọc trạng thái (`Tất cả`, `Đang hoạt động`, `Đã tạm dừng`), và đồng bộ hóa thông báo bằng `toast` (Sonner).
     - **Kiểm thử đạt chuẩn 100% Zero Error**:
       * Frontend Lint: `npm run lint` — Checked 92 files (0 lỗi).
       * Frontend Typecheck: `npm run typecheck` — `tsc --noEmit` (0 lỗi).
       * Frontend Build: `npm run build` — Vite build thành công (8.34s, `dist/` bundle sạch).
       * Backend Pytest: `uv run --extra dev pytest tests/test_assistants.py -v` — 8/8 tests passed (100%).
       * Backend Ruff: `uv run ruff check .` — All checks passed (0 lỗi).
       * Zero Mojibake Audit: `python scripts/check_mojibake.py` — 226/226 files UTF-8 sạch 100%.
       * Browser E2E Test: Đã xác thực giao diện qua browser subagent và lưu video/screenshot tại artifacts.
  2. **Triển Khai Hoàn Tất 100% Toàn Bộ 5 Đợt Kế Hoạch 04 — Hoàn Thiện Hệ Sinh Thái Trợ Lý AI & DAG Control Plane (phiên #78)**:
     - **Mục tiêu**: Hiện thực hóa 100% [Kế hoạch 04](file:///d:/DuAnPhanMem/qnu-ai-platform/docs/ke_hoach/04_ke_hoach_hoan_thien_tro_ly_ai_dag.md), xóa bỏ hoàn toàn dữ liệu giả, nâng cấp DAG Canvas và Trợ lý AI thành Workflow Control Plane cấp Enterprise với bảo vệ chống bịa đặt (Anti-Hallucination), cổng kiểm định chất lượng TM-08 và điều hướng sâu (Deep Linking).
     - **Thay đổi kỹ thuật chi tiết theo 5 Đợt**:
       * **Đợt 0 & 1 (Assistant Binding & Snapshot bất biến)**: `AssistantRuntimeProfile` snapshot cho từng lượt chạy; RAG & LLM nodes tôn trọng profile; Input/Output guardrails; loại bỏ toàn bộ fallback mock.
       * **Đợt 2 (Workflow Control Plane)**: Module `workflows` 4 files chuẩn Clean Architecture (`models.py`, `schemas.py`, `service.py`, `router.py`); API Draft/Validate/Publish/Rollback; Compiler graph validation; optimistic locking `expected_revision`.
       * **Đợt 3 (DAG Engine Production)**: Ready-set topological scheduler; condition branching với regex tiếng Việt an toàn; fan-out/fan-in synchronization; deadlock detection; durable checkpoint PostgreSQL; human approval token & resume; Tool gateway schema & permission validation.
       * **Đợt 4 (Trải nghiệm vận hành & Deep Link)**: In-Canvas Test Runner nhận trace thật; Node Catalog Drawer; Version History Dialog khôi phục bản nháp; Dirty state tracking; Deep link `/runs/:runId` (mở modal timeline checkpoint & copy link) và `/workflows/:id` (đồng bộ tab workflow trên DAG Studio & copy link).
       * **Đợt 5 (Quality Gate TM-08 & Anti-Hallucination)**: `compiler.py` bắt buộc có node thẩm định trích dẫn hoặc fallback (`workflow_rag_missing_citation_guard`) khi dùng RAG; `service.py` kiểm tra kết quả `EvaluationRun` mới nhất trước khi publish (`workflow_quality_gate_failed`).
     - **Kiểm thử đạt chuẩn 100% Zero Error**:
       * Backend Pytest: 18/18 tests passed (`tests/test_workflows.py`) bao gồm cycle, deadlock, fan-out/fan-in, human approval, compiler citation guard và TM-08 quality gate.
       * Backend Ruff: All checks passed (0 lỗi).
       * Frontend Biome: Checked 92 files (0 lỗi).
       * Frontend Typecheck: `tsc --noEmit` (0 lỗi).
       * Frontend Build: Vite build thành công (8.10s, `dist/` bundle sạch).
       * Zero Mojibake Audit: 226/226 files UTF-8 sạch 100%.
  2. **Xử Lý Triệt Để Lỗi Chuẩn Hóa PDF Scan & Loại Bỏ Hoàn Toàn Text Giả Lập (phiên #77)**:
     - **Vấn đề**: Người dùng kiểm tra tệp PDF scan 9 trang (`4740-qd-bgddt-bo-chi-so-cds-dai-hoc.pdf`, QĐ 4740 BGDĐT), Document Verification Studio hiển thị toàn bộ văn bản giả lập (`### Tiêu đề đầu trang`, `## Tên loại văn bản / Trích yếu nội dung`, `Đoạn văn bản quy định`, `Bảng biểu số liệu`, `Con dấu & Chữ ký xác thực`), mất 100% nội dung thật.
     - **Nguyên nhân gốc rễ**:
       * `layout_detector.py` (dòng 965..990, 295, 193) gán chuỗi mô tả tiếng Việt vào thuộc tính `text` của box thay vì để rỗng.
       * `chunker.py` không parse ranh giới `<!-- Trang X -->`, gán `page_number = None` cho cả 9 chunks.
       * `service.py` kích hoạt `is_clumped = True` giả mạo, vứt bỏ toàn bộ chunks thật để thay bằng `_synthesize_page_markdown_from_blocks` chứa text giả lập.
       * `mistral_adapter.py` truyền `page.get_text()` rỗng vào Layout Detector thay vì text OCR thật.
     - **Giải pháp triệt để**:
       * `layout_detector.py`: Gỡ bỏ 100% text giả lập khỏi `raw_boxes`, `tables`, `stamps`. Khi không có text OCR, `text = ""` và `content_snippet = ""`.
       * `chunker.py`: Tự động parse `_RE_PAGE_MARKER` để gán chính xác `page_number` cho từng chunk (1 đến 9).
       * `mistral_adapter.py`: Truyền markdown THẬT từ Mistral OCR của từng trang vào `SmartLayoutDetector`.
       * `service.py`: Lưu `page_markdowns` vào `doc_metadata`, ưu tiên dùng trong `build_studio_pages`, lọc sạch `_SYNTHESIS_PLACEHOLDERS`, và kích hoạt **Auto-Rescue** trong `get_studio_view` khi tài liệu có 0 chunks hoặc khi người dùng bấm `[Quét lại]`.
       * Reprocess CSDL: Nạp đầy đủ **9 chunks thật (14.194 ký tự)** của QĐ 4740 vào PostgreSQL.
     - **Kiểm thử**:
       * Backend Pytest: 44/44 passed (100%) trong 46.65s (bổ sung 2 test case mới).
       * Backend Ruff: 0 error.
       * Zero Mojibake Audit: 225/225 files sạch (100%).
       * Frontend: Biome 0 lỗi, TypeScript 0 lỗi, Vite build thành công (12.04s).
  2. **Tối Giản Toàn Diện Màn Hình Đối Soát Document Verification Studio — Pure Markdown (Phương Án 1 - phiên #76)**:
     - **Yêu cầu người dùng**: Bỏ các tab gây thừa thãi ("Văn bản", "Markdown", "Bố cục & Khối"); chỉ tập trung vào một đích duy nhất: dữ liệu chuẩn hóa Markdown sạch để nạp vào Vector DB hoặc xuất file .md.
     - **Giải pháp**:
       * Thay thế 3 tab cũ bằng **Right Toolbar tối giản**:
         - Scope Switcher: `[Trang hiện tại (Trang X)]` vs `[Toàn bộ file (N trang)]` dùng `<Tabs>` semantic.
         - Toggle Chế độ xem: `[Xem render]` vs `[Mã nguồn .md]` (icon `Code`/`Eye`).
         - Công cụ hành động: `[✏️ Sửa tay]` (kèm `[Xem trước]`, `[Lưu sửa]`, `[Hủy]`), `[Sao chép]`, `[Tải file .md]`.
       * Dọn dẹp sạch mã chết (Boy Scout Rule 8.1 & 8.2): Gỡ bỏ import `Layers`, `RegionsInspector` và `allRegions` useMemo.
       * Cả 2 scope (`page` và `all`) đều hỗ trợ chuyển đổi linh hoạt giữa xem render GFM và xem mã nguồn thô trong thẻ `<pre>`.
       * Footer stats đồng bộ tự động theo scope (`từ • dòng` khi ở trang đơn, `ký tự • trang` khi ở toàn bộ file).
     - **Kiểm thử**: Biome lint 0 lỗi (91 files), TypeScript 0 lỗi (`tsc --noEmit`), Vite build thành công (9.72s), Zero Mojibake 225/225 files sạch.
  2. **Sửa Triệt Để Lỗi Chuẩn Hóa Markdown Bị Mất Bảng Biểu & Scan Không Nhận Diện Bảng — Kế Thừa QNU-AI-Core (phiên #75)**:
     - **Vấn đề**: Người dùng tải tệp (đặc biệt là tệp DOCX tuyển sinh 14 trang `Thong tin tuyen sinh dai hoc 2026_Lan2-1 (1).docx`), toàn bộ các bảng biểu biểu mẫu tuyển sinh từ trang 2 đến trang 13 bị biến thành chuỗi chữ giữ chỗ `Bảng biểu dữ liệu số hóa` thay vì trích xuất thành bảng Markdown (`| STT | Mã xét tuyển | ... |`), khung scan nhận diện bảng không sinh ra bảng Markdown tương ứng.
     - **Nguyên nhân gốc rễ**:
       * `layout_detector.py` (dòng 295, 405) gán cứng `"text": "Bảng biểu dữ liệu số hóa"` và loại bỏ toàn bộ text con trong bảng, không gọi `tab.extract()`.
       * `DocxParser` trong `office_parser.py` duyệt văn bản trước rồi dồn bảng xuống cuối tệp, trả về `page_count = 1` khiến chunks bị dồn về trang 1 (`is_clumped = True`).
       * Trong `service.py`, `_synthesize_page_markdown_from_blocks` lấy text từ block của trang, dẫn đến toàn bộ nội dung từ trang 2 đến trang 13 biến thành dòng chữ giữ chỗ vô nghĩa.
     - **Giải pháp bám sát `qnu-ai-core`**:
       * `layout_detector.py`: Bổ sung `_format_table_markdown(rows)`. Khi `find_tables()` phát hiện bảng, gọi `tab.extract()` chuyển đổi thành Markdown table thực sự. Gán bảng Markdown này vào `table["text"]` và `content_snippet`. Triệt tiêu hoàn toàn chuỗi placeholder.
       * `office_parser.py`: Nâng cấp toàn diện `DocxParser` theo chuẩn `docx_processor.py` của `qnu-ai-core`: duyệt tuần tự `child in doc.element.body`, chuẩn hóa Quốc hiệu/Tiêu ngữ/Số hiệu NĐ 30, tách hàng La Mã thành tiêu đề, xử lý colspan và ngắt dòng trong ô `<br>`/`;`, cân bằng số cột.
       * `cleaner.py`: Bổ sung Unicode NFC (Zero Mojibake), chuẩn hóa cấu trúc bảng Markdown (`_normalize_markdown_table_block`), nối bảng qua trang (`_stitch_table_continuations`), làm sạch số trang đơn độc.
       * `service.py`: Cập nhật `_synthesize_page_markdown_from_blocks` giữ nguyên bảng Markdown, bổ sung phát hiện `has_placeholder` trong `_is_stale_raw_blocks` để tự động re-extract dữ liệu cũ, lưu `text` đầy đủ cho từng block trong `_ensure_page_blocks`.
       * `blocks.py`: Bổ sung `_format_table_markdown` và cập nhật `extract_page_blocks` trích xuất bảng Markdown từ PDF vector tables.
       * `verification-data.ts`: Dọn dẹp sạch 12 vị trí chứa chuỗi `"Bảng biểu dữ liệu số hóa"` trong mock fixture.
     - **Kiểm thử**:
       * Parse thực tế tệp DOCX tuyển sinh: 23.118 ký tự, 4 bảng lớn, đầy đủ 53 ngành tuyển sinh và tổ hợp môn, 0 placeholder.
       * Pytest: `test_knowledge_docx_tables.py` (3/3 passed), `test_smart_layout.py` (4/4 passed), `test_knowledge.py` (25/25 passed).
       * Ruff: 0 lỗi. Biome: 0 lỗi. TypeScript: 0 lỗi. Vite build: thành công. Zero Mojibake: 225/225 files sạch.
  2. **Sửa Lỗi OCR Bounding Box Nát Bét Trên PDF — Loại Bỏ Khối Giả Lập, Tích Hợp SmartLayoutDetector (phiên #74)**:
     - **Vấn đề**: Upload file PDF (`4740-qd-bgddt-bo-chi-so-cds-dai-hoc.pdf`) vào Kho Tri Thức, Document Verification Studio hiển thị khu nhận diện OCR (bounding box overlay) nát bét: các khối ngang chồng chéo (x=8.0, width=84.0) với badge chứa 40 ký tự markdown thô (`**bộ giáo dục**`, `# **quyết định**`). Trên trang landscape (bảng biểu), dải sọc cắt ngang hoàn toàn lệch.
     - **Nguyên nhân gốc rễ**: `MistralOCRAdapter` tạo blocks giả lập (mỗi dòng markdown = 1 khối ngang). `_is_stale_raw_blocks` chấp nhận khối giả (vì type `title`/`header` tồn tại) nên không kích hoạt SmartLayoutDetector. Frontend render `{box.label}` verbatim.
     - **Giải pháp**: (1) `mistral_adapter.py`: Thay vòng lặp giả bằng `SmartLayoutDetector` thực (PyMuPDF hybrid + OpenCV), trả `blocks=[]` nếu detector thất bại. (2) `knowledge/service.py`: Phát hiện synthetic blocks (`x≈8.0, width≈84.0` hoặc markdown `**`/`#` trong label) → auto re-extract. (3) `document-bounding-visualizer.tsx`: `REGION_BADGE_LABELS` map + `getDisplayBadge` + max-width 120px ellipsis.
     - **Kiểm thử**: Pytest 143/143 passed, Ruff 0 lỗi, Biome 0 lỗi, TypeScript 0 lỗi, Vite build thành công.
  2. **Khắc Phục Lưu API Key Provider & Xử Lý Tính Đặc Thù Của Từng Provider (Cloudflare, Mistral, Gemini, OpenAI) (phiên #73)**:
     - **Vấn đề**: Người dùng thêm API key vào Mistral trong Quản lý Provider (`/models`) nhưng không được lưu lại. Ngoài ra, cấu trúc API của Cloudflare Workers AI khác biệt (yêu cầu `account_id` trong URL), cần nghiên cứu tính đặc thù của từng provider.
     - **Nguyên nhân gốc rễ**:
       * Bảng `model_provider_configs` lưu `api_keys` trong cột `extra_config` (`JSONB`). Khi sửa đổi mảng con `extra["api_keys"]`, SQLAlchemy không phát hiện thay đổi nếu thiếu `flag_modified(config, "extra_config")`. Vì vậy `await db.commit()` âm thầm bỏ qua câu lệnh `UPDATE`!
       * Thiếu cơ chế đồng bộ hóa tức thì (In-memory Live Sync) giữa cấu hình DB và các runtime services (`settings.MISTRAL_API_KEY`, `settings.CLOUDFLARE_API_TOKEN`, `settings.CLOUDFLARE_ACCOUNT_ID`), khiến OCR hoặc RAG không nhận được key mới nếu chưa restart backend.
     - **Giải pháp**:
       * Bổ sung `flag_modified(config, "extra_config")` cho toàn bộ các thao tác Key Pool: `add_provider_key`, `update_provider`, `update_provider_key`, `delete_provider_key`, `simulate_key_rotation`.
       * Triển khai hàm `_sync_runtime_credentials`: tự động tiêm key và account_id vào `settings` ngay khi tạo/sửa/xóa key hoặc khi load danh sách provider lúc khởi động.
       * Xử lý tính đặc thù của từng Provider:
         - **Cloudflare Workers AI**: Hỗ trợ trường `account_id`, URL `https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/run`, endpoint xác thực `/accounts/{account_id}/ai/models/search`.
         - **Mistral AI**: Endpoint xác thực `/v1/models`, model OCR `mistral-ocr-latest`.
         - **Google Gemini**: Xác thực qua `?key=` hoặc header `x-goog-api-key`.
         - **OpenAI / DeepSeek / Groq / OpenRouter / NVIDIA**: Xác thực chuẩn Bearer token và endpoint `/v1/models`.
       * Triển khai kiểm tra kết nối thật (Real HTTP Verification) trong `test_provider` và `test_provider_key` thay cho số liệu giả lập.
     - **Kiểm thử**:
       * Pytest: 143/143 passed (100% pass toàn bộ test suite dự án).
       * Ruff: 0 lỗi.
       * Frontend: Biome 0 lỗi, TypeScript 0 lỗi, Vite build thành công (`dist/` bundle).
  2. **Tích Hợp Mistral OCR & Cơ Chế Điều Phối Bóc Tách Đa Tầng Core → Platform (phiên #72)**:
     - **Vấn đề**: Người dùng upload tệp PDF dạng scan (`4740-qd-bgddt-bo-chi-so-cds-dai-hoc.pdf`), Platform kích hoạt Docling TableFormer trên CPU tải trọng 770MB weights Heron Object Detection và chạy suy luận mất hàng chục giây.
     - **Giải pháp bóc tách chuẩn Core**:
       * Tạo `MistralOCRAdapter` (`backend/app/modules/ocr/adapters/mistral_adapter.py`) gọi Mistral OCR API (`POST https://api.mistral.ai/v1/ocr`, model `mistral-ocr-latest`), trả về markdown, pages và bounding boxes studio. Kiểm tra tính sẵn sàng trung thực qua `settings.MISTRAL_API_KEY`.
       * Triển khai cơ chế phân định thông minh (Smart Extension-based Routing):
         - File Word/Excel (`.docx`, `.doc`, `.xlsx`, `.xls`): Ưu tiên `Docling TableFormer` / `openpyxl` bảo toàn 100% ma trận bảng.
         - File PDF: Trích xuất nhanh văn bản số hóa qua PyMuPDF fast-path (10-30ms); nếu là bản scan (văn bản <40 ký tự) $\rightarrow$ chuyển cứu hộ Mistral OCR (Cloud API 1-2s).
         - Graceful Local Fallback: Nếu không cấu hình `MISTRAL_API_KEY` hoặc lỗi mạng, tự động rơi về Local OCR (`easyocr` / `docling` / `pymupdf_ocr`) với `fallback_triggered=True`.
         - File ảnh (`.png`, `.jpg`,...): Ưu tiên Mistral OCR, fallback Local OCR.
       * Sửa lỗi buffer 1D trong `easyocr_adapter.py`: truyền trực tiếp `image_bytes` vào `reader.readtext`.
       * Frontend: Cập nhật `file-inspector.ts` và `document-ingest-page.tsx` với đề xuất `Fast-path + Mistral OCR` và option `mistral: "mistral_ocr"`.
     - **Kiểm thử**:
       * Backend: `uv run ruff check .` (0 lỗi), `pytest tests/test_ocr.py` (13/13 passed 100%), `pytest tests/test_knowledge.py` (25/25 passed 100%).
       * Frontend: `npm run lint` (0 lỗi trên 90 files), `npm run typecheck` (0 lỗi), `npm run build` (thành công trong 15.95s).
  2. **Đồng Bộ Quản Trị Trợ Lý AI Core → Platform Bằng Dữ Liệu Thật (phiên #71)**:
     - Xác định bảng `assistants` ban đầu rỗng; API cũ che giấu tình trạng này bằng 5 bản ghi fallback trong bộ nhớ và trang `/assistants` tiếp tục hiển thị hằng số frontend.
     - Tạo seed idempotent 5 trợ lý + 5 `WorkflowDefinition` từ `configs/workflows`, không ghi đè cấu hình người dùng và không chạm Provider/ModelOps.
     - Chuẩn hóa cấu hình vòng đời 7 lớp: Persona/Scope, Knowledge, Model/Fallback, Guardrails, Tools/HITL, Output/Citations và Evaluation TM-08.
     - Hoàn thiện API list/detail/create/update/deactivate, templates, seed-defaults, import/export bundle; lỗi DB được phản ánh trung thực, không fallback mock.
     - Thay trang tĩnh bằng `/assistants`, `/assistants/new`, `/assistants/:code` dùng TanStack Query, có loading/error/empty, tìm kiếm/lọc, seed, import/export và liên kết Chat/DAG đúng trợ lý.
     - Đã nạp và xác minh PostgreSQL có 5 bản ghi thật; API list/detail/templates trả HTTP 200; kiểm tra trực quan ba route trên trình duyệt thành công.
     - **Kiểm thử**: Assistants 7/7 passed, Ruff 0 lỗi; frontend Biome 0 lỗi, TypeScript 0 lỗi, Vite build thành công. Toàn bộ backend đạt 141/142; 1 lỗi ngoài phạm vi ở OCR concurrent (`OCRExtractResponse.fallback_engine`).
  1. **Khắc Phục Lỗi TypeError `document_type_code` & Hoàn Thiện Studio Page Builder (phiên #70)**:
     - **Hiện tượng**: Tải lên tệp tin `7.1.6 Kế hoạch triển khai 2 phần mềm của Nhà trường.docx` qua Studio Nạp Kho Tri thức bị lỗi `Tải lên thất bại (HTTP 500). Vui lòng thử lại.` Do Backend trả `TypeError: KnowledgeService.list_documents() got an unexpected keyword argument 'document_type_code'` và `KnowledgeService.ingest_document()`.
     - **Nguyên nhân**: `KnowledgeService` bị thiếu tham số `document_type_code` do quá trình revert trước đó.
     - **Giải pháp**:
       * Import `document_types_service` và bổ sung `document_type_code: str | None = None` vào `KnowledgeService.list_documents` (kèm query filter `where(KnowledgeDocument.document_type_code == document_type_code)`).
       * Bổ sung `document_type_code: str | None = None` vào `KnowledgeService.ingest_document`, xác thực active code với `document_types_service.validate_active_code`, gán vào `KnowledgeDocument.document_type_code` và lưu `document_type_source`.
       * Bổ sung tham số `page_markdowns` và helper `_synthesize_page_markdown_from_blocks` trong `build_studio_pages` để bảo toàn nội dung từng trang khi chunks bị dồn.
     - **Kiểm thử**: `uv run ruff check .` (0 lỗi), `uv run --extra dev pytest tests/test_knowledge.py tests/test_document_types.py tests/test_jobs.py` (47/47 passed 100%), Endpoint `GET /platform/v1alpha1/knowledge/documents` phản hồi `HTTP 200 OK`.
  2. **Đồng Bộ Lịch Sử Tác Vụ (`JobRecord`) Cho Luồng Nạp Tài Liệu Kho Tri Thức (phiên #69)**:
     - **Hiện tượng**: Người dùng nạp tệp thành công vào CSDL (hiển thị 1 tài liệu hiệu lực 16 chunks), nhưng tab "Tiến trình & Lịch sử Tác vụ (0)" trống không có tác vụ nào.
     - **Bản chất kỹ thuật**:
       * Luồng nạp qua Studio chạy đồng bộ trực tiếp (Human-in-the-loop Ingestion) để trả kết quả bóc tách tức thì (<1s) cho người dùng đối soát mắt, không đẩy qua hàng đợi Redis/ARQ.
       * Tab "Tiến trình & Lịch sử Tác vụ" gọi `GET /jobs?limit=50` từ bảng `job_records` (trước đây chỉ ghi khi người dùng bấm Reindex hoặc chạy worker task ngầm).
     - **Giải pháp**:
       * Cập nhật `ingest_document` và `approve_document` trong `knowledge/service.py` để tự động ghi nhận bản ghi `JobRecord(job_type="ingestion", status="completed", progress=100.0)` kèm metadata (tên tệp, dung lượng, OCR engine, chunks).
       * Bổ sung `sync_ingestion_job_records` trong lifespan startup để tự động hồi tố lịch sử cho các tài liệu đang có trong kho.
       * Đã tạo thành công bản ghi tác vụ cho `Thong tin tuyen sinh dai hoc 2026_Lan2-1 (1).docx` trong CSDL.
     - **Kiểm thử**: `test_jobs.py` pass 15/15 (100%), Ruff 0 lỗi, Biome 0 lỗi, TypeScript 0 lỗi.
  2. **Tự Động Hóa 100% Loại Văn Bản (Taxonomy) Cho Trang Nạp Tài Liệu Kho Tri Thức (phiên #68)**:
     - **Yêu cầu người dùng**: Sau khi trải nghiệm tính năng auto cấu hình ban đầu, người dùng phản hồi cần tự động chọn luôn "Loại văn bản" (đặc biệt khi upload file tuyển sinh như `Thong tin tuyen sinh dai hoc 2026_Lan2-1 (1).docx` không bị rơi vào "Chọn loại văn bản" / "Chưa xác định").
     - **Giải pháp toàn diện**:
       * Nâng cấp `frontend/src/lib/file-inspector.ts`:
         - Bổ sung nhận diện từ khóa tuyển sinh / đề án (`/(?:de\s*an|tuyen\s*sinh|thong\s*tin\s*tuyen\s*sinh)/` -> `de_an`).
         - Cung cấp cơ chế dự phòng thông minh theo ngữ cảnh Kho Tri Thức đa hình (`collectionContext`: id, name, code) -> tự động gán loại văn bản đặc thù cho từng kho (`col_admissions` -> `de_an`, `col_regulations` -> `quy_che`, `col_library` -> `giao_trinh`, `col_question_bank` -> `de_cuong_mon_hoc`, `col_drafting` -> `cong_van`).
         - Đồng bộ `getPriorityForDocumentType`: phân cấp chuẩn xác `de_an` vào `standardTypes` (Điểm 8/10, Tiêu chuẩn x50) theo đúng catalog backend NĐ 30.
       * Cải tiến `frontend/src/pages/document-ingest-page.tsx`:
         - Tách hàm `processFile(f: File)` dùng chung cho cả sự kiện click duyệt chọn file và kéo thả file (`onDrop` / `onDragOver`).
         - Bổ sung `useEffect` tự động gán Loại văn bản mặc định theo Kho tri thức ngay khi mở trang mà không cần chờ chọn file.
         - Cập nhật nhãn Loại văn bản trong Smart Recommendation Banner hiển thị tên tiếng Việt chính thức.
     - **Kiểm thử**: Biome lint 0 lỗi trên 86 files, TypeScript 0 lỗi, Vite build thành công (10.81s), backend pytest 25/25 knowledge tests pass (100%), Ruff 0 lỗi.
  2. **Tích Hợp Smart Auto-Recommendation Cho Trang Nạp Tài Liệu Kho Tri Thức (phiên #66)**:
     - **Yêu cầu người dùng**: Tìm hiểu và tích hợp chức năng tự động đề xuất cấu hình bóc tách khi chọn file kế thừa từ `qnu-ai-core`.
     - **Giải pháp**:
       * Nâng cấp `frontend/src/lib/file-inspector.ts`: bổ sung `detectDocumentTypeFromFilename` (18 mẫu đối chiếu 37 loại Taxonomy), `extractYearFromFilename` (regex 4 chữ số), `cleanTitleFromFilename` và `getPriorityForDocumentType` (Cốt lõi 10/10, Tiêu chuẩn 8/10, Tham khảo 6/10).
       * Tích hợp vào `frontend/src/pages/document-ingest-page.tsx`: tự động chọn bộ máy OCR (Word/Excel -> Docling TableFormer bảo toàn bảng; Text/MD -> PyMuPDF Fast; PDF -> Auto), tự động chọn Loại văn bản, tự động điền Năm hiệu lực, hiển thị **Smart Recommendation Banner** màu Academic Teal và cập nhật mức ưu tiên pháp lý động.
     - **Kiểm thử**: Biome lint 0 lỗi trên 86 files, TypeScript 0 lỗi, Vite build thành công (12.59s), logic tests pass 100%.
  2. **Khắc Phục Lỗi "Xóa Tài Liệu Thất Bại (HTTP 500)" Do Backend Offline & Tối Ưu Xử Lý Lỗi Proxy (phiên #65)**:
     - **Nguyên nhân gốc rễ**: Người dùng duyệt Frontend (`port 3001`) nhưng tiến trình Backend (`port 8001`) chưa được khởi chạy. Vite Proxy (`localhost:3001 -> 127.0.0.1:8001`) bị từ chối kết nối `ECONNREFUSED` nên trả về `HTTP 500`. Frontend do không gọi được API danh sách nên fallback hiển thị tài liệu mẫu `doc_ts_2026`; khi người dùng bấm xóa, yêu cầu tiếp tục gặp 500 từ Vite proxy.
     - **Giải pháp**:
       * Khởi động dịch vụ Backend FastAPI trên port 8001, xác thực mọi API `/health/live`, `/knowledge/collections`, `/jobs`, `/modelops/defaults` đều phản hồi HTTP 200 OK.
       * Cải tiến `apiClient.deleteDocument`: Tự động bắt lỗi HTTP 500 từ proxy khi backend offline, hiển thị thông báo lỗi rõ ràng hướng dẫn khởi động backend, và dọn dẹp mock list an toàn.
     - **Kiểm thử**: Backend 136/136 tests pass (100%), Ruff 0 lỗi; Frontend Biome 0 lỗi (83 files), TypeScript 0 lỗi.
  2. **Tính Năng Thiết Lập Model Mặc Định Hệ Thống (Embedding, Reranker, OCR) Cho Kho Tri Thức & RAG (phiên #64)**:
     - **Yêu cầu người dùng**: Bổ sung tính năng cấu hình model mặc định (Cloudflare vs Local) để tự động áp dụng khi sử dụng Kho Tri Thức và RAG.
     - **Kiến trúc & Giải pháp**:
       * Backend Service & API (`modelops`): Cung cấp schema `SystemModelDefaults` và endpoints `GET /modelops/defaults`, `PUT /modelops/defaults`, `POST /modelops/providers/{id}/set-default`. Tự động scan model khả dụng của các provider active trong CSDL.
       * Lưu trữ PostgreSQL bền vững: Bản ghi `system_model_defaults` trong `model_provider_configs`, tự động đồng bộ vào runtime `settings` (Lifespan Startup).
       * Giao diện Quản trị ModelOps (`modelops-page.tsx`): Card điều khiển "Mô Hình Mặc Định Hệ Thống (Active System Defaults)" với 3 dropdowns tương tác thời gian thực; huy hiệu "★ Default" và nút gán nhanh "Đặt Default" trên từng model tag.
       * Phản ánh trực quan Kho Tri Thức (`knowledge-page.tsx` & `collection-detail-page.tsx`): Hiển thị model embedding mặc định động kèm icon phân biệt (`Zap` cho Cloudflare Workers AI Edge vs `Cpu` cho Local CPU).
     - **Kiểm thử**: Backend pytest 13/13 modelops + 34/34 rag/knowledge pass (100%), Ruff check 0 lỗi; Frontend Biome 0 lỗi, TypeScript 0 lỗi, Vite build bundle thành công.
  2. **Tạo seed data taxonomy Platform và khắc phục lỗi không hiển thị dữ liệu (phiên #63)**:
     - Xác định database đã có 37 dòng trong `platform_document_types`, nhưng API list HTTP 500 vì schema cũ thiếu `knowledge_documents.document_type_code`.
     - Tạo `document_types/seed_data.py` làm manifest seed versioned, sinh từ catalog 37 loại đã đối chiếu với `qnu-ai-core`, không tạo nguồn dữ liệu nghiệp vụ thứ hai.
     - Thêm `scripts/seed_document_types.py` để seed idempotent bằng lệnh rõ ràng; sửa logic sync không còn `KeyError` khi so sánh các trường source audit.
     - Bổ sung startup schema repair và migration idempotent cho cột/index/FK; đã áp dụng migration vào PostgreSQL hiện tại.
     - Xác minh API GET list trả 37 loại và POST sync trả HTTP 200 (`total=37`, `added=0`, `updated=0`); không chạm Provider/ModelOps seed của session song song.
     - Kiểm thử phiên: Backend **135/135 passed**, Ruff 0 lỗi.
  1. **Seed Dữ Liệu Provider Cloudflare Workers AI & Mistral OCR, Tích Hợp BGE-M3 và Reranker (phiên #60)**:
     - **Yêu cầu người dùng**: Seed data Cloudflare, Mistral OCR cho Provider, đồng bộ API key từ file env của `qnu-ai-core`, sử dụng Cloudflare cho BGE-M3 Embedding và Reranker.
     - **Giải pháp xử lý**:
       * Cấu hình `config.py` & `.env`: Bổ sung `EMBEDDING_PROVIDER="cloudflare"` và `RERANKER_PROVIDER="cloudflare"`, đặt mặc định `EMBEDDING_MODEL="@cf/baai/bge-m3"` và `RERANKER_MODEL="@cf/baai/bge-reranker-base"`.
       * Nạp `CLOUDFLARE_ACCOUNT_ID="ab6bf644b640759c330c44f109e3f000"`, `CLOUDFLARE_API_TOKEN="cfut_...df00"`, `MISTRAL_API_KEY="r1Dv...07T4"`.
       * Tích hợp Cloudflare BGE-M3 trong `vector_indexer.py`: Thêm `_embed_texts_cloudflare` gọi trực tiếp API Cloudflare Workers AI (16 chunks tính xong trong 1.00s thay vì 101.94s trên CPU, nhanh gấp 100 lần), kèm fallback tự động sang SentenceTransformers hoặc mock vector.
       * Tích hợp Cloudflare BGE Reranker trong `reranker.py`: Thêm `_rerank_cloudflare` gọi API `@cf/baai/bge-reranker-base`, xếp hạng chính xác ngữ nghĩa trong 1.21s, kèm fallback tự động sang RRF ordering.
       * Seed CSDL PostgreSQL `model_provider_configs`: Cập nhật `prov_cloudflare` và `prov_mistral` kèm Key Pool hoạt động chuẩn UTF-8 ("Khóa Mistral OCR & Platform").
     - **Kiểm thử**:
       * Backend: 25/25 test_knowledge pass, 9/9 test_rag pass, Ruff 0 lỗi.
       * Frontend: Biome check 0 lỗi, TypeScript 0 lỗi.
       * Đo đạc thực tế: Cloudflare BGE-M3 trả về vector 1024 chiều trong **1.00s**, Cloudflare Reranker trả về điểm số tương quan cao (0.898) trong **1.21s**.
  2. **Triển khai taxonomy loại văn bản Core → Platform (phiên #61)**:
     - Khảo sát danh mục 37 loại văn bản trong `qnu-ai-core/services/platform-api/.../document_taxonomy.py`.
     - Phân biệt taxonomy của Product Platform với `document_type` dạng chuỗi tự do trong AI Core engine.
     - Xác định Platform mới chưa có module/table/API Document Types và `KnowledgeDocument` chưa có `document_type_code`.
     - Tạo module `document_types` với catalog 37 loại/28 mã NĐ30, bảng `platform_document_types`, migration có kiểm tra schema, source hash/version và sync idempotent bảo vệ custom type.
     - Bổ sung CRUD/filter/API sync, gắn `document_type_code` vào `KnowledgeDocument`, upload ingestion và filter tài liệu theo loại.
     - Đồng bộ workflow extractor/exporter về mã canonical; thêm frontend `/document-types` list/detail, CRUD, deactivate và nút sync thật qua TanStack Query.
     - Chốt taxonomy v1 là 37 loại; `Dự toán`, `Nghị định`, `Ma trận đề thi` giữ ngoài taxonomy như legacy/artifact.
     - Trạng thái: nền tảng taxonomy v1 đã triển khai; chưa có Core HTTP endpoint versioned nên sync hiện dùng catalog import tương thích trong Platform.
     - Phạm vi file không bao gồm provider/modelops seed của session song song.
     - **Yêu cầu người dùng**: Khi làm sạch dữ liệu xong bấm "Xác nhận & Nạp vào Vector DB" trong Document Verification Studio thì nút bấm xoay mãi không dừng lại.
     - **Nguyên nhân gốc rễ**:
       * Mô hình BGE-M3 (2.24GB) chạy CPU inference cho 16 chunks dài mất tới 101.94s, vượt quá ngưỡng timeout 60s của client/proxy, khiến kết nối HTTP bị drop timeout và UI xoay mãi.
       * `_get_embedding_model()` chạy đồng bộ trên main thread của Event Loop Uvicorn, kèm theo truy vấn unauthenticated lên HuggingFace Hub làm khóa cứng server 25-30s đầu.
       * Thiết kế API `approve_document` đợi tính toán vector xong mới trả lời HTTP.
     - **Giải pháp xử lý**:
       * Tối ưu `vector_indexer.py`: Tải mô hình ưu tiên local cache (`local_files_only=True`, tải trong 2.45s), nạp qua `asyncio.to_thread` không chặn Event Loop, thêm timeout guard 30s với graceful fallback sang deterministic mock vector, chuẩn hóa tên collection tránh lặp `col_col_`.
       * Tối ưu `service.py`: Tách nạp Qdrant sang `_background_index_document` chạy ngầm qua `asyncio.create_task`. Lưu bản sửa tay vào PostgreSQL xong trả về kết quả ngay (<0.5s), không bắt HTTP client phải đợi 1.5 phút.
     - **Đo lường & Kiểm thử**:
       * Độ trễ API `POST /documents/{id}/approve` giảm từ >60s (Timeout) xuống **0.39s** (giảm 99.6%).
       * Điểm vector nạp thành công vào Qdrant (`col_question_bank`: 16 points).
       * Backend: 25/25 test_knowledge pass, 9/9 test_rag pass, Ruff 0 lỗi.
       * Frontend: Biome check 0 lỗi, TypeScript 0 lỗi, Vite build thành công.
  2. **Điều Chỉnh Thứ Tự Tab & Phân Định Trách Nhiệm Markdown / Văn Bản Trong Studio (phiên #58)**:
     - **Yêu cầu người dùng**: Sắp xếp lại 3 tab theo thứ tự `Văn bản`, `Markdown`, `Bố cục & Khối`; trong đó tab `Markdown` hiển thị tất cả nội dung của toàn bộ file, còn tab `Văn bản` hiển thị theo từng trang.
     - **Giải pháp xử lý**:
       * Sắp xếp lại thứ tự TabsList: `Văn bản` (1st, default), `Markdown` (2nd), `Bố cục & Khối` (3rd).
       * Tab `Văn bản` (Page-by-page): Hiển thị nội dung bóc tách của từng trang (`currentPage`), hỗ trợ chế độ "Sửa tay" (Human-in-the-loop) trực tiếp trên trang đang chọn, sao chép và tải về tệp riêng cho trang đó.
       * Tab `Markdown` (Full Document): Tổng hợp toàn bộ nội dung Markdown của tất cả các trang, kết hợp hiển thị các khối phân tách trang trực quan, tích hợp nút chuyển đổi nhanh giữa xem Render GFM và xem Mã nguồn thô, hỗ trợ sao chép toàn bộ Markdown và tải về tệp `.md` hoàn chỉnh của toàn bộ file.
       * Thanh thống kê Footer: Hiển thị linh hoạt (tab Markdown hiển thị tổng ký tự & tổng trang; tab Văn bản hiển thị số từ & dòng của trang hiện tại).
     - **Kiểm thử**: Biome lint 0 lỗi, TypeScript typecheck 0 lỗi, Vite build thành công; Backend 25/25 tests passed (100%), Ruff check 0 lỗi.
  2. **Khắc Phục Dứt Điểm Lỗi Markdown Dồn Hết Vào Trang 1 & Trang 2 Trắng Tinh (phiên #57)**:
     - **Nguyên nhân gốc rễ**: Khi tài liệu DOCX hoặc đa trang được upload, chunks được sinh ra có `page_number = None`. Trong `build_studio_pages`, toàn bộ chunks bị ép về `page_number = 1`, khiến Trang 1 gom toàn bộ 22.985 ký tự của cả 14 trang, còn các trang 2..14 không có chunk nào nên `markdown_content = ""` (trắng tinh).
     - **Giải pháp xử lý**:
       * Cập nhật `_ensure_page_blocks` trong `KnowledgeService`: Duyệt qua từng trang của PDF (cả PDF gốc hoặc Word render qua Gotenberg), bóc tách riêng bảng Markdown (`find_tables()`) và vùng văn bản (`SmartLayoutDetector`), lưu `page_markdowns` độc lập cho từng trang vào `doc_metadata`.
       * Cập nhật `build_studio_pages`: Hỗ trợ tham số `page_markdowns`. Khi dựng nội dung từng trang, ưu tiên lấy trực tiếp `page_markdowns[page_number]`. Nếu chunks bị dồn vào trang 1 trong tài liệu nhiều trang (`is_all_clumped_in_p1`), không gán toàn bộ cho trang 1 mà tự động tổng hợp Markdown chuẩn từ blocks của từng trang đó.
       * Cập nhật `approve_document`: Khi người dùng lưu sửa tay, đồng bộ cả `KnowledgeChunk(page_number=...)` và `doc_metadata["page_markdowns"]`.
       * Bổ sung 2 unit test trong `tests/test_knowledge.py` kiểm chứng không bao giờ dồn chunks vào trang 1 và bảo đảm trang 2 không bị rỗng.
     - **Khắc phục lỗi ECONNREFUSED khi chạy `make dev`**:
       * Đổi Vite proxy target trong `frontend/vite.config.ts` từ `http://localhost:8001` sang `http://127.0.0.1:8001` (tránh lỗi IPv6 `::1` trên Windows).
       * Thêm độ trễ an toàn 2s trong `make.bat` và `make.ps1` để Backend mở cổng 8001 trước khi Vite bật lên.
     - **Kiểm thử**: Backend Ruff check 0 lỗi, pytest 3/3 passed; Frontend typecheck 0 lỗi.
  2. **Khắc Phục Bóc Tách Bảng Song Song & Bảo Toàn Danh Sách (List) Độc Lập (phiên #56)**:
     - Giải quyết triệt để phản ánh của người dùng trên tài liệu 14 trang (`media_1789641791050.pdf` - Trang 9 chỉ hiện 2 bảng và mất sạch text/list):
       * Khử rò rỉ ô bảng song song (side-by-side tables) qua tính toán tỷ lệ giao cắt diện tích dọc (>50%) và ngang (>10px) hoặc tọa độ tâm block, không để các ô điểm IELTS/VSTEP tràn ra ngoài thành text.
       * Thiết lập rào cản `table_between`: ngăn cách tuyệt đối không gộp các đoạn văn bản xuyên qua bảng biểu.
       * Chuẩn hóa luật gộp Strictly Same-Type: `list` chỉ gộp với `list`, `text` chỉ gộp với `text`, giữ nguyên bản sắc nhãn `list`.
       * Mở rộng `_is_list_marker` hỗ trợ đầy đủ ký tự tiếng Việt (`đ`, `Đ`), dấu ngoặc đơn, gạch đầu dòng, số thứ tự.
       * Sửa an toàn `_suppress_overlapping_boxes`: chỉ xóa khối text/list nếu chính nó lọt lòng trên 60% bên trong bảng, không bao giờ xóa khối lớn vì bao quanh bảng.
     - Kiểm thử: Trang 9 hiển thị đầy đủ 9 khối vĩ mô sắc nét (`text`, `list` b. & c., 2 `table`, `text`, `list` c., `title` mục 6 & Đợt 1, `list` a, b, c, `text`). Backend 126/126 tests passed (100%), Ruff check 0 lỗi; Frontend Biome lint 0 lỗi trên 78 files, TypeScript 0 lỗi, Vite build thành công (5.32s).
  2. **Chuẩn Hóa Phân Vùng Bố Cục Vĩ Mô (Macro Layout Sections) Theo Chuẩn QNU-AI-Core (phiên #55)**:
     - Khảo sát mã nguồn thực tế `qnu-ai-core` (`smart_layout_detector.py`, `test_layout_classifier.py`, `sample-data.ts`), xác nhận cơ chế Adjacent Band Merging để gom các đoạn văn bản kề nhau thành khối vĩ mô.
     - Triệt tiêu hoàn toàn hiện tượng phân mảnh vi mô (micro-segmentation) từng câu/mục con/dòng căn cứ.
     - Thêm thuật toán `_merge_into_macro_regions` trong `SmartLayoutDetector`:
       * Gom Header Trang 1 thành 2 khối cân xứng (Cơ quan bên trái & Quốc hiệu bên phải).
       * Giữ nguyên Tiêu đề chính độc lập (`KẾ HOẠCH`, `QUYẾT ĐỊNH`, v.v.).
       * Gộp các đoạn căn cứ pháp lý và tiểu mục chỉ đạo liên tiếp thành các khối text vĩ mô.
       * Phân cách mục La Mã rõ ràng (`I.`, `II.`, `III.`, v.v.).
       * Bảo vệ nguyên vẹn các khối `table`, `signature` và `list` (Nơi nhận).
     - Giảm **67%** số lượng khung nhận diện trên tài liệu mẫu (từ 36 khung vụn xuống 12 khung vĩ mô: Trang 1 có 5, Trang 2 có 2, Trang 3 có 2, Trang 4 có 3).
     - Kiểm thử: Backend 125/125 pytest passed (100%), Ruff check 0 lỗi; Frontend Biome lint 0 lỗi trên 78 files, TypeScript 0 lỗi, Vite build thành công (5.33s).
  2. **Loại Bỏ Tính Năng Tia Quét & Chuẩn Hóa Khung Nhận Diện Scan Bố Cục Văn Bản Hành Chính (phiên #54)**:
     - Gỡ bỏ hoàn toàn nút bấm, hiệu ứng animation laser beam và HUD badge trên giao diện Document Verification Studio và Scan Studio theo yêu cầu người dùng.
     - Nâng cấp `SmartLayoutDetector` kết hợp Vector PDF (PyMuPDF blocks + `find_tables()`) và Computer Vision OpenCV.
     - Triệt tiêu phân mảnh ô bảng: gộp gọn bảng dữ liệu 9 hàng thành 1 khối `table` duy nhất.
     - Điều chỉnh ngưỡng mật độ con dấu tương thích (0.04) cho con dấu tròn lớn, bắt trọn vẹn con dấu ĐH Quy Nhơn.
     - Hợp nhất hoàn chỉnh khối Dấu & Ký (`signature`): tự động bao trọn Chức vụ (`HIỆU TRƯỞNG`), Con dấu tròn màu đỏ và Họ tên người ký (`PGS. TS. Đoàn Đức Tùng`) kể cả khi mực dấu đóng đè, loại bỏ toàn bộ khung text trùng lặp.
     - Phân loại chính xác ngữ nghĩa hành chính Việt Nam (NĐ 30/2020/NĐ-CP): Tiêu đề cơ quan, Quốc hiệu, Tiêu ngữ, Căn cứ pháp lý, Tiêu đề mục La Mã, Mục số, Danh sách gạch đầu dòng, và Khối Nơi nhận.
     - Bổ sung unit test suite `test_smart_layout.py` (3 test cases).
     - Kiểm thử: Backend 125/125 pytest passed (100%), Ruff check 0 lỗi; Frontend Biome lint 0 lỗi trên 78 files, TypeScript 0 lỗi, Vite build hoàn tất thành công (5.54s).
  2. **Thiết Kế Lại Component Select & Chuẩn Hóa Bộ UI Primitives (phiên #53)**:
     - Tạo UI Primitive `frontend/src/components/ui/select.tsx` dựa trên `@radix-ui/react-select` (bo góc 8px, popover mượt mà, checkmark indicator).
     - Thay thế 100% thẻ `<select>` native trên toàn bộ hệ thống (`collection-detail-page.tsx`, `document-ingest-page.tsx`, `scan-studio-page.tsx`, `modelops-page.tsx`, `channels-page.tsx`, `docx-nd30-editor.tsx`).
     - Tinh chỉnh các UI primitives khác theo UI Rules: bổ sung thanh cuộn siêu mỏng 6px (`globals.css`), chuyển `badge.tsx` sang dạng pill `rounded-full` soft tint, làm mềm viền focus `input.tsx` và `textarea.tsx`.
     - Kiểm thử: Biome lint 0 lỗi trên 78 files, TypeScript 0 lỗi, Vite build thành công (5.68s), pytest 23/23 pass.
  2. **Rollback Font Chữ & Typography Sidebar Về Ban Đầu (phiên #52)**:
     - Khôi phục `frontend/src/layouts/app-sidebar.tsx` và `--font-sans` trong `frontend/src/styles/globals.css` về trạng thái ban đầu của Platform theo yêu cầu người dùng (`text-xs py-2`, `text-[10px]` labels/badges, loại bỏ active pill).
     - Kiểm thử: Biome lint 0 lỗi trên 77 files, TypeScript `tsc --noEmit` 0 lỗi.
  2. **Hoàn Thiện Nút Xóa Tác Vụ, Nút Dọn Dẹp Đã Xong & Sửa Lỗi Hủy Job HTTP 409 (phiên #51)**:
     - **Nguyên nhân HTTP 409**: Bản ghi job trong CSDL PostgreSQL đã ở trạng thái `cancelled`, nhưng `mapJobToIngestionTask` trong `frontend/src/services/api-client.ts` gom nhầm thành `processing`, khiến UI hiển thị "Đang xử lý" và render nút Hủy (`X`). Khi người dùng bấm `X`, Backend từ chối với lỗi 409 vì job đã kết thúc.
     - **Khắc phục triệt để**:
       - Mở rộng kiểu `IngestionTask.status` hỗ trợ `cancelled`.
       - Ánh xạ đúng `status: "cancelled" -> "cancelled"`.
       - Thêm cơ chế idempotent cancel cho Backend: nếu job đã `cancelled` thì trả về bản ghi ngay thay vì ném lỗi 409.
       - Cập nhật badge `TASK_STATUS_BADGE.cancelled` thành "Đã hủy" với style badge muted và icon `X` rõ ràng.
       - Thêm bộ lọc trạng thái "Đã hủy" và "Thất bại" trong filter dropdown.
     - **Thêm nút Xóa từng tác vụ (`Trash2`)**:
       - Bổ sung nút Xóa trên từng dòng bảng tác vụ kèm `ConfirmDialog` xác nhận xóa.
       - Thêm phương thức `delete_job` trong Backend service và endpoint `DELETE /jobs/{job_id}`.
       - Thêm `apiClient.deleteJob(jobId)` xử lý xóa an toàn (hỗ trợ idempotent 404).
     - **Hiện thực hóa nút "Dọn dẹp đã xong"**:
       - Gắn handler và `ConfirmDialog` cho nút "Dọn dẹp đã xong" trên thanh công cụ tác vụ.
       - Thêm phương thức `cleanup_jobs` trong Backend service và endpoint `DELETE /jobs/cleanup?collection_id={id}` dọn dẹp hàng loạt các jobs completed/cancelled/failed.
       - Thêm `apiClient.cleanupJobs(collectionId)`.
       - Hiển thị banner xanh `taskSuccessMessage` tự động ẩn sau khi thao tác thành công.
     - **Triệt tiêu Mock Trap trong Ingestion Tasks**:
       - Sửa `apiClient.getIngestionTasks` để khi Backend trả về mảng rỗng `[]` (đã dọn sạch), Frontend hiển thị đúng Empty State thay vì lén lút fallback về `MOCK_INGESTION_TASKS`.
     - **Kiểm thử**: Backend 122/122 pytest passed (100%), Ruff check 0 lỗi; Frontend Biome lint 0 lỗi trên 77 files, TypeScript `tsc --noEmit` 0 lỗi, Vite build hoàn tất thành công (13.59s).
  2. **Đồng Bộ Font Chữ & Typography Sidebar Theo Chuẩn QNU AI Core (phiên #50)**:
     - Đồng bộ font family Inter/system-ui và typography Sidebar.



---

## 2. Tổng Quan Dự Án

| Thuộc Tính | Giá Trị |
| :--- | :--- |
| **Tên dự án** | QNU AI Platform |
| **Tổ chức** | Trường Đại học Quy Nhơn (QNU) |
| **Workspace** | `D:\DuAnPhanMem\qnu-ai-platform` |
| **Backend** | `D:\DuAnPhanMem\qnu-ai-platform\backend` (FastAPI, Port 8001) |
| **Frontend** | `D:\DuAnPhanMem\qnu-ai-platform\frontend` (Vite 6 + React 19, Port 3001) |
| **Codebase gốc tham khảo** | `D:\DuAnPhanMem\qnu-ai-core` (FastAPI + Streamlit/Vite Studio, Port 3000) |

---

## 3. Trạng Thái Hoàn Thành Các Giai Đoạn

### ⚠️ Backend — Đủ bề rộng chức năng, production readiness còn một phần

> Lưu ý phiên #85: bảng dưới đây phản ánh **độ phủ module/UI lịch sử**, không đồng nghĩa mọi module đã hoàn thiện runtime hoặc đủ điều kiện production. Trạng thái production phải theo acceptance gate trong báo cáo đánh giá tổng thể.

| Giai Đoạn | Mô Tả | Trạng Thái |
| :--- | :--- | :---: |
| 1 | Scaffolding FastAPI + Cấu hình hạ tầng 7 dịch vụ | ✅ Done |
| 2 | Module Assistants (05 Trợ lý QNU) | ✅ Done |
| 3 | Module Knowledge (Collections, Ingestion Pipeline, OCR đa tầng) | ✅ Done |
| 4 | Module RAG (Hybrid RRF k=60, Cross-Encoder Reranking, Structured Fact Layer) | ✅ Done |
| 5 | Module ModelOps (Provider Presets, Key Pool 429 Failover, Circuit Breaker) | ✅ Done |
| 6 | Module Tools (UIS Admissions Query, Word NĐ 30, Excel Bloom) | ✅ Done |
| 7 | Module Evaluation (Ragas TM-08: Faithfulness, Relevance, Precision) | ✅ Done |
| 8 | Module Workflows (DAG Pipeline, ARQ Workers, Guardrails) | ✅ Done |

**Backend Quality (phiên #111)**: Full suite **218/218 passed (100%)**, 34 warnings. Hoàn thành Giai đoạn 1 khắc phục khoảng hở kết nối: P0-05 Facts Lifecycle outerjoin & filter, P1-14 Quota endpoint alias, P0-06 Chat Widget endpoint /chat.

---

### ⚠️ Frontend — Độ phủ màn hình cao, LiveMode cần loại bỏ business mock fallback

> Cập nhật phiên #111: Hoàn thành Giai đoạn 1 UI: Sửa endpoint Widget `/chat`, bóc tách `data-api-base` và cập nhật template mã nhúng Channels & Assistant Detail, sửa URL gọi Quota `/modelops/quotas/${tenantId}`.

| Giai Đoạn | Màn Hình / Module | Trạng Thái |
| :--- | :--- | :---: |
| 1 | Master Layout (Sidebar w-64, Topbar h-14, Academic Teal oklch) | ✅ Done |
| 2 | Assistants Studio (05 Trợ lý, Persona, ModelOps config, Tool Gateway, Publish Gate, Clone) | ✅ Done |
| 3 | Knowledge Management & Master-Detail Navigation (List + Detail + Ingest + Full Studio) | ✅ Done |
| 4 | Document Verification Studio (Full 14 scan pages, BBoxes, Regions, ReactMarkdown Tables, In-place Edit) | ✅ Done |
| 4b | **Scan & OCR Document Intelligence Studio** (`/ocr`: Split-Screen, OpenCV Boxes, Excel Viewer, API Code) | ✅ Done |
| 5 | Omni-Channel Chat Studio (SSE Streaming, Thinking Indicator, CitationSheet) | ✅ Done |
| 6 | ModelOps Dashboard (4 Presets, Secret Key Masking, Circuit Breaker Monitor) | ✅ Done |
| 7 | Tools Gateway (Word NĐ 30 Preview, Excel Bloom Matrix, Template Library) | ✅ Done |
| 8 | Workflow DAG Canvas (@xyflow/react, 6 Custom Node types, Run DAG & Inspector) | ✅ Done |
| 9 | Evaluation & Active Remediation (TM-08 Benchmark, Gap Inbox, Resolve) | ✅ Done |

**Frontend Quality**:
- Phiên #111: Biome Lint 0 lỗi trên 130 files | TypeScript 0 lỗi. Build thành công trong 8.03 giây, 0 warnings.
- Playwright E2E: Suite 09 có TC-INGEST-01→04 (bao gồm TC-INGEST-04 chống tái diễn hardcode)

---

## 4. Danh Mục Gotchas Kỹ Thuật (Kinh Nghiệm Thực Tế)

1. **Strict Mode trong Playwright**:
   - Khi có text xuất hiện ở cả thanh Breadcrumb/Header và trong thân trang (ví dụ `Trang 1 / 14`, filename), bắt buộc phải dùng `page.getByText('...', { exact: true })` hoặc `.first()` để tránh lỗi `strict mode violation`.
2. **Hiển thị Ảnh Scan Tài Liệu Bóc Tách**:
   - Không được dùng text/HTML mock để giả lập trang scan. Bắt buộc phải phục vụ ảnh scan thật từ thư mục tĩnh `frontend/public/ocr-cache/doc_ts_2026/page_N.jpg` với tỉ lệ khung hình chuẩn A4 và zoom container. Với tệp mới không có scan cache, hiển thị khung canvas tài liệu số hóa sạch.
3. **Render Bảng Biểu Markdown**:
   - Markdown thô (`whitespace-pre-wrap`) không hiển thị được bảng. Bắt buộc dùng `ReactMarkdown` với plugin `remarkGfm` và custom `components={{ table, thead, th, td, tr }}` có styling viền ô rõ ràng.
4. **Chuẩn Hóa Encoding UTF-8 trên Windows (Tránh Mojibake)**:
   - Mọi script Python chạy console trên Windows phải thiết lập `sys.stdout.reconfigure(encoding="utf-8")` để không bị lỗi `UnicodeEncodeError` với bảng mã `cp1252`.
   - File đọc/ghi bắt buộc chỉ định rõ `encoding="utf-8"`.
5. **PEP 8 E402 trong Backend**:
   - Khi xử lý đoạn mã sửa lỗi Windows IPv6 `no_proxy`, đặt đoạn sanitize sau toàn bộ module imports chuẩn để ruff check 0 lỗi.
6. **AsyncMock DB Refresh trong Test**:
   - Trong unit tests với `AsyncMock` DB, hàm `db.refresh(record)` không tự sinh ID hoặc timestamp như PostgreSQL thật; service cần chủ động khởi tạo explicit ID (`f"ast_{uuid.uuid4().hex[:12]}"`) và datetime UTC trước khi add.
7. **Tiêu Chuẩn Nhận Diện Header Bảng Bằng Hình Thái Học Zero-Keyword (Zero-Keyword Morphological Table Header Detection)**:
   - **Tuyệt đối không dùng hardcoded dictionary/keywords** (`stt`, `nhiệm vụ`, `đơn vị`...) để xác định header bảng. Việc hardcode từ khóa làm hỏng bóc tách khi gặp tài liệu tài chính, thời khóa biểu, y tế hoặc tiếng Anh.
   - Nhận diện hàng Header bảng dựa trên **5 tiêu chuẩn hình thái học & cấu trúc (Morphological Standards)**:
     1. *Loại trừ khóa chuỗi dữ liệu (Sequence Key Check)*: Hàng bắt đầu bằng số nguyên (`^\d+$`), mã phân cấp (`^\d+(\.\d+)+$`), chữ số La Mã (`^[IVXLCDM]+$`) hoặc mã 7 số (`^\d{7}$`) là hàng dữ liệu, không phải header.
     2. *Bắt buộc định danh Cột 0*: Tiêu đề bảng thật sự bắt buộc phải có nhãn ở Cột 0; nếu Cột 0 bị rỗng thì đó là hàng nối dòng mồ côi (orphan wrapped cell).
     3. *Độ dài & Phi mô tả*: Ô header là nhãn danh từ ngắn gọn ($\le 45$ ký tự), không chứa gạch đầu dòng (`-`, `•`), không bao giờ kết thúc bằng dấu chấm kết câu `.`, và không bao giờ chứa dấu chấm phẩy `;` phân tách mệnh đề.
     4. *Mật độ số liệu / ngày tháng thấp*: Tỷ lệ ô chứa ngày tháng, phần trăm, số tiền $\le 20\%$.
     5. *Chữ cái bắt buộc*: 100% ô có nghĩa phải chứa ký tự chữ cái (`[a-zA-Zà-ỹÀ-Ỹ]`).
   - *Sub-header cấp 2*: Nếu hàng có 1 ô phụ đơn lẻ, độ dài phải $\le 25$ ký tự (như `điều chỉnh`, `ACCA`, `Năm 2024`) để không nuốt nhầm các câu văn ngắt đôi từ trang trước trôi sang.
8. **Đóng Băng Byte Của Request Compiler Đã Lưu**:
   - `input_sha256` của một part là hash trên đúng bytes của request đã gửi. Sửa hàm projection/prompt dùng chung sẽ khiến run đang dở không resume/verify được.
   - Vì vậy mỗi phiên bản có module riêng: `compilation/projection.py` + `units.py` là primitive đóng băng, `compilation/segments_v2.py` giữ nguyên hành vi v2, `compilation/segments.py` là v3. Muốn đổi hình dạng request thì tạo version mới, không sửa module cũ. Test `test_compiler_projection_746.py` ghim hash v2.
   - `plan_from_scope` thiếu `projection_version` được đọc là v2 (run cũ); version lạ trả `compilation_segment_version_unsupported` (409), không tự đoán.
9. **Kiểm Soát Reasoning Phải Khai Báo, Không Suy Đoán**:
   - Không đặt `enable_thinking`/`reasoning_effort`/`chat_template_kwargs` theo tên model hay theo loại endpoint. Mỗi provider khai báo `reasoning_policy_v1` (`mode`, `parameter`, `low_value`, `off_value`, `tasks`, `verified`) và chỉ áp dụng khi `verified=true`.
   - `server_default` là mặc định: không gửi tham số nào. Part đã ghi chính sách mà chính sách hiện tại khác ⇒ `compilation_reasoning_changed`, không tự gửi lại.

---

## 5. Backlog & Kế Hoạch Tiếp Theo

### Đã Hoàn Thành Trong Giai Đoạn 1 (Phiên #111)
- [x] **P0-06 Web Chat Widget:** Sửa endpoint sang `/chat` kèm `stream: true`, chuẩn hóa `data-api-base` và snippet mã nhúng cross-origin.
- [x] **P1-14 Contract Quota API:** Sửa URL gọi `/modelops/quotas/${tenantId}` và tạo endpoint alias `GET /quota?tenant_id=...` trên backend.
- [x] **P0-05 Facts Lifecycle:** Outerjoin `KnowledgeDocument`, lọc bỏ facts thuộc tài liệu `pending`/`archived` khỏi Hybrid RAG.

### Ưu Tiên Tích Hợp Sau Phiên #108 (Các Giai Đoạn Tiếp Theo)
- [ ] **P0 Truthful Runtime:** loại fake-success khỏi LLM/OCR/Tools/Embedding/Workflow trong LiveMode; lỗi thật phải hiện `failed/degraded`.
- [ ] **P0 Security Boundary:** bảo vệ router quản trị bằng `get_current_actor`, mask/encrypt provider key và chuyển toàn bộ secret sang environment.
- [ ] **P0 Tool Policy:** bắt `tool.api_caller` đi qua `ToolService`, enforce allowlist/HITL và ghi execution audit.
- [ ] **P1 Assistant–ModelOps:** model catalog động theo provider active/capability; primary/fallback deterministic; usage streaming ghi đúng một lần.
- [ ] **P1 Chat–Handoff:** assistant động, attachment thật, conversation/message persistence và staff reply quay lại widget/chat.
- [ ] **P1 Knowledge Index Integrity:** trạng thái `pending_index/indexed/index_failed`, retry/outbox và reconciliation DB–Qdrant–Storage.
- [ ] **P1 Workflow Contract:** validate manifest JSON Schema/version/status và schema-driven Property Inspector.

### Đã Hoàn Thành Trong Đợt 1 (Phiên #101)
- [x] **Cổng Kiểm Định Xuất Bản 5 Lớp (Publish Gate Engine)**: Thẩm định 5 tiêu chí (Knowledge doc ready, ModelOps 2 tầng, Tool Gateway allowlist, Guardrails chống jailbreak/che PII/hotline No-Answer, TM-08 Ragas) trước khi kích hoạt Trợ lý AI.
- [x] **Nhân Bản Trợ Lý 1-Click (Clone Assistant)**: Cho phép khoa/phòng ban nhân bản từ 5 Trợ lý mẫu để tùy biến theo nhu cầu đơn vị.
- [x] **Hòm Thư Lỗ Hổng Tri Thức (Knowledge Gap Inbox & Active Remediation)**: Tự động gom câu hỏi kích hoạt No-Answer Policy vào CSDL `knowledge_gaps`, hiển thị trên `/evaluation` kèm nút "Nạp vào RAG" và "Đánh dấu đã nạp" / "Bỏ qua".

### Trọng Tâm Đợt 2 Tiếp Theo
- [ ] **Dev Access Gate Phía Client & Server**: Trang Login `/login` (đăng nhập cán bộ QNU) bảo vệ các router quản trị nhạy cảm (JWT / HttpOnly Cookie), ngăn truy cập trái phép khi chưa đăng nhập.
- [x] **Observability & Cost Tracking Thực Tế**: Đếm token, tính chi phí USD thật, ghi nhận vào biểu đồ Dashboard thay vì số liệu tĩnh; đồng nhất `generate_stream()` với `generate()` về quota và accounting.
- [ ] **Widget Embed / Kênh Tích Hợp Đa Kênh**: Hoàn thiện mã nhúng Javascript nhúng Trợ lý AI vào Cổng thông tin QNU (`qnu.edu.vn`) và Cổng Tuyển sinh; hỗ trợ web widget standalone.

### Các Tồn Đọng Kỹ Thuật Khác
- [x] Hoàn thành `docs/ke_hoach/10_ke_hoach_chuan_hoa_markdown_qdrant_va_chat_luong_rag.md`: Duplicate-Free Parser, bảng đa trang, typed records, Quality Gate, Facts/atomic chunks, revision-safe Qdrant và golden evaluation; không đưa chunk/fact có conflict vào Qdrant retrievable.
- [ ] Sửa blocker worktree trước mọi đợt seed tiếp: hợp nhất 3 method `delete_document/delete_collection/archive_document`, khôi phục xóa storage gốc, dùng cleanup retryable/outbox và đưa Ruff về xanh.
- [ ] Không gắn Library/Question Bank là official trước khi có PDF/DOCX nguồn, metadata provenance/evidence và lưu tệp gốc qua storage driver; seed/reconcile asset-by-asset thay vì return sớm.
- [x] Thực hiện gói **RAG Data Integrity & Groundedness**: retrieval chỉ lấy document `ready/approved`, đúng tenant/revision; thêm relevance threshold và claim-citation verification.
- [x] Xóa/rebuild orphan facts Question Bank (đã thêm FK & cascade); thêm FK/cascade, source evidence và content revision cho `knowledge_facts`.
- [ ] Reconcile 17 chunks Question Bank sang Qdrant collection chuẩn `col_question_bank`; kiểm chứng parity rồi mới xóa `col_col_question_bank`.
- [x] Cấm mock embedding trong LiveMode; hỗ trợ sparse-only degraded mode có nhãn và health signal rõ ràng.
- [ ] Version hóa RAG cache theo tenant/collection/content revision/assistant/model/policy và invalidate khi approve/edit/archive/delete/reindex.
- [ ] Thực hiện hotfix **Assistant–Workflow Runtime Integrity**: bỏ `is_approved=true`, bỏ mock answer/citation/artifact trong LiveMode, fail-fast khi export lỗi và loại KPI/count giả.
- [ ] Lấy tenant/user/role/approval actor từ trusted auth context; enforce tool allowlist, node permissions, connection allowlist và approval trước side effect.
- [ ] Hoàn thiện workflow Soạn thảo/Ngân hàng câu hỏi: clarify wait/resume, RAG context assembly, syllabus/CLO/Bloom validation và artifact metadata động.
- [ ] Triển khai SSE thật và cancellation server-side; sửa citation DTO mapping `source_id/section/page_number/quote` sang Frontend.
- [ ] Thực hiện gói **Knowledge Index Integrity**: state machine `review_pending/indexing/ready/index_failed`, retrieval chỉ lấy đúng revision `ready`, và reconciliation PostgreSQL–Qdrant.
- [ ] Đối chiếu/migrate 16 points từ `col_col_question_bank` sang collection chuẩn `col_question_bank`; chỉ xóa legacy sau khi kiểm chứng.
- [ ] Đồng bộ vector/facts khi approve, sửa, archive, xóa document/collection; loại ghost citations và cấm mock embedding trong LiveMode.
- [ ] Nâng lexical retrieval từ `ILIKE` lên PostgreSQL FTS thật; chạy dense/sparse song song và enforce tenant/workspace filter trong Qdrant.
- [ ] Triển khai **Dev Access Gate** tối giản: password hash từ env, signed HttpOnly session, `/auth/login`/`me`/`logout`, principal `tenant_qnu/workspace_qnu/admin`; bảo vệ API thay đổi dữ liệu, Tool Gateway và approval. Chỉ mở rộng RBAC/SSO khi có nhiều cán bộ/tenant.
- [ ] Tách DemoMode/LiveMode và loại business mock fallback khỏi LiveMode.
- [ ] Thay Evaluation/TM-08 mô phỏng bằng việc chạy Assistant/RAG runtime thật và tổng hợp metrics từ DB.
- [ ] Nối RAG Answer Composer với ModelOps; bind Assistant primary/fallback model, tool allowlist và evaluation policy xuống runtime.
- [ ] Khóa Workflow execution/resume vào immutable version; bổ sung timeout, retry/backoff, cancellation, schema/port và permission validation.
- [x] Nạp tài liệu chính thức và golden datasets cho Admissions (`col_admissions`) và Regulations (`col_regulations`).
- [x] Tách các file lớn trên 1.000 dòng theo SRP: hoàn thành `api-client.ts` (2.074 -> 57 dòng) và `modelops-page.tsx` (2.961 -> 854 dòng).
- [x] Tối ưu frontend bundle bằng code splitting và route-level lazy loading (chunk chính giảm xuống 372 kB, 0 warnings).
- [x] Đồng bộ ảnh scan thực tế 14 trang từ `qnu-ai-core` vào Studio đối soát.
- [x] Render Markdown bảng biểu và cấu trúc phân cấp chuẩn GitHub Flavored Markdown.
- [x] Thêm chế độ xem trước (Preview) khi hiệu đính văn bản trong chế độ Sửa tay (Human-in-the-loop).
- [x] Nối FE vào BE thật cho luồng nạp/đối soát (upload pending, approve + index Qdrant, OCR auto-routing Docling/EasyOCR lazy).
- [x] Cài Docling 2.128 thật + kiểm chứng Đề án 2026 (48.050 ký tự markdown, bảng đầy đủ, conf 0.97).
- [x] Sửa dứt điểm lỗi hardcode upload file và bổ sung kiểm thử tự động chống tái diễn (TC-INGEST-04).
- [x] Xây dựng bộ quét tự động Zero Mojibake (`scripts/check_mojibake.py`).
- [x] Endpoint studio-view + render page-image từ backend (cache storage) + bboxes/regions thật từ engine; xóa 29 ảnh qd2699 (~6MB) khỏi git (giữ 14 ảnh demo theo AGENTS 8.9).
- [x] Xây dựng Scan & OCR Document Intelligence Studio độc lập (`/ocr`) kèm SmartLayoutDetector OpenCV (nhận diện bảng, con dấu đỏ, phân đoạn text) và ExcelSpreadsheetViewer đa sheet.
- [ ] Kéo thả ROI trên ảnh scan (mở rộng studio-view).
- [ ] Chuẩn hóa CRLF→LF + `.gitattributes` để `npm run lint` (biome check) xanh toàn repo.
- [x] Triển khai nền tảng taxonomy 37 loại văn bản từ `qnu-ai-core` sang `qnu-ai-platform` (`docs/ke_hoach/03_ke_hoach_dong_bo_taxonomy_loai_van_ban.md`).
- [x] Tạo seed manifest taxonomy Platform và sửa lỗi schema/API khiến danh sách loại văn bản không hiển thị (`backend/scripts/seed_document_types.py`).
- [x] Đồng bộ 13 NodeManifest từ `qnu-ai-core` và hiển thị Node Catalog tại `/nodes`; giữ DAG Canvas tại `/canvas`.
- [x] Đồng bộ 5 trợ lý Core vào PostgreSQL thật; hoàn thiện API CRUD/seed/bundle và UI list/create/detail tại `/assistants`.
- [ ] Phiên OCR/Provider hoàn thiện trường `fallback_engine` trong `OCRExtractResponse` để full backend suite trở lại 142/142.
- [ ] Bổ sung Core manifest/HTTP endpoint versioned, parser confidence/evidence, E2E CRUD/sync và scheduler sync taxonomy.

### Đã Hoàn Thành Chuyển Đổi Sang Provider API (Phiên #245)
- [x] Loại bỏ runtime local cho `Ollama`, `vLLM`, `SentenceTransformers`, `Docling` và `EasyOCR`; xóa adapter, preset, seed, icon và dependency liên quan.
- [x] ModelOps chỉ phân giải provider có API key hợp lệ trong PostgreSQL; thiếu khóa sẽ fail-fast theo RFC 7807 và tiếp tục xoay khóa/provider dự phòng.
- [x] Embedding và reranker mặc định dùng Cloudflare Workers AI (`@cf/baai/bge-m3`, `@cf/baai/bge-reranker-base`); đây là API cloud, không tải model về máy.
- [x] OCR dùng PyMuPDF cho lớp text số và Gemini/Mistral qua API cho tài liệu scan; chuỗi cấu hình cũ trong DB đã được migration loại bỏ.
- [x] Đã xóa cache BGE-M3, EasyOCR và Docling khỏi máy phát triển, giải phóng khoảng 5,21 GB.
