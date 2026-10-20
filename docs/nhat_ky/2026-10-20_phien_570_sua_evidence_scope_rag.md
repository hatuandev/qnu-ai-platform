# Phiên570 — Sửa pipeline RAG, bước2

Ngày20/10/2026. Người dùng giao sửa các đường lỗi đối soát569; giữ model/source/QualityGate, chưa benchmark64, khôngreindex/republish/commit/push.

SửaRAGscope/condition/caption/packing/reason;focused155PASS/replay9PASS;full2810PASS/18FAIL/17SKIP;0newFAIL;noLLM/64benchmark/reindex/pub/modelchange/restart/Gitwrites

Thay đổi17fileappRAG và1filetest25cases, khôngfrontend/parser/schema. Source conditions cóID/publicretention, chronological listguard, matrix boundary/row recovery, caption/section locators, unit/role refusal và trace/cachev6. Model vẫn quyết định semanticrequired; không gọi outputschema như proof correctness độc lập. Numericguard không nới. Chưa kết luận13câu sẽPASS.

## Kiểm chứng

DB/MinIO/Qdrantloopbackverified; sharedDBREADONLY, testDBnonce49tables/localStorageriêng/endpointport1/egressguard. Focused155PASS/Ruff18filePASS/replay9PASS. Full2810PASS/18FAIL/17SKIP, exit1, 0newFAIL/0oldmissing/0statuschanged/25addedPASS. Testbaseline20FAIL5PASS được chấm bằng app snapshot cũ sau khi viết tests; không gọi là TDD trước sửa.

Lượt đầu helper chặnsocketpairWindows→6errors, đã giới hạn ngoại lệ chỉsocketpair nội bộ. OrdinalsplitpositiveFAIL→sửa sentenceboundary, giữ failure receipts. Full lỗi nền vàcause đối chiếu trongreport, khôngcheFAIL.

Source/configsealđọc lại khớp568:5collections/23bindings/2sources/27indexes/5assistants/13ModelOpsrows. TestDBđãdọn, Storage `database_and_storage_removed`; giữprivate evidence/không đụngruntimecũ. Khôngmodelcall, benchmark mới/holdout/pubE2ENOTRUN.

[Triển khai](../bao_cao/context570/IMPLEMENTATION_REPORT.md) · [Kiểm chứng vàlệnh](../bao_cao/context570/VALIDATION_REPORT.md). Private receipts `backend/storage/context570/`. CWDroot/pytestbackend; không sourcecode/secrets/corpus trongmemory. Không tự restart; chưa xác minh mã trong process đang phục vụ. Bước3 cần xác nhận runtimecode rồi frozen64Luna-only, không đổi source/model/gold.
