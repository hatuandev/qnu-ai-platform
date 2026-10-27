# Phiên620 — Thử gh/gpt-5.6-luna không ghim trần context

Yêu cầu: thử đúngaliasgh/gpt-5.6-luna và chạy lại compiler, giữ nguồn/QG. Alias probePASS, providertrảgpt-5.6-luna; contextmetadata1050000/output128000, tokenizerregistryo200k_base/framing2010. Khôngmanual200K/khôngclaimvôhạn hoặc đãtest1M. Defaulttoànappgh/gpt-6-lunagiữ, overrideprimarychỉtiếntrìnhthử.

Phát hiện prerequisiteModelOps: observed_at được ghi lại dù capability không đổi, làm configurationhash/cachediscoverythayđổi. Initialservice0compilerinferenceFAIL; directdiagnostic16stagecomplete/stage17mayuncertain dừngINCOMPLETE, khôngresendintent. Sửa3dòng trongchat_capabilities.py: cùngendpoint/capabilities thìkhôngUPDATE/commit; thayđổi thật vẫn lưu. Khôngcompilersemantic/QGchange. Baseline4test3PASS/1FAIL→5regressionPASS; focused124PASS/Ruff2PASS. Full3764PASS/18FAILnền/17SKIP/exit1,798,54s; exact18ID/causekhớp6183759/18/17,5IDthêmPASS/khôngregression.

Finalnormalsservice3DOCX381proof,hashgiữ,66Lunainference/0fallback/allstop,max32452input/1927output,delta0,1schema correction. Pause64 rồiresume2call, không gọi lại checkpointcomplete. FinishFAILgrounded_coverage_review_missing. Replay66exactcheckpoint/0LLM dựng12assertions/3sections,machinecompletefalse: targetgender5081đúng/2assertions/data2025; nhưng2026explicit5173bịunknown/null vàsynthesiscontradicted,3packetcoverageincomplete. ChưaAPPROVED, không64benchmark.

DB/MinIO/Qdrantloopback kiểm trước,testDBnonce/StorageLocalriêng. BaDB620đãdọn/Storagechứngcứgiữpolicy. Finalservicepostchecknguồn/default/provider/domainsealsgiữ; cácprobeđầucóobservationwriteModelOpshợplệ,khônggiấuthayđổi. Khôngreindex/publish/restart/deploy/commit/push, khôngđotạivectorpayloadhash.

Lệnh Python3.12venv: context620_probe.py, context620_checks.py setup/run/cleanup, context620_service_final.py(exit1), context620_receipt_review.py(exit0 chẩn đoánkhôngphảiE2EPASS), context620_compare.py(exit0). ArtifactXML/receipts/metrics/backend/storage/context620. [Báo cáo620](../bao_cao/context620/REVIEW.md).
