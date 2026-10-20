# Phiên565 — Source-grounded entity và metric resolution

Ngày 2026-10-20. Người dùng duyệt triển khai prompt Context565 và5bổ sung: canonical row cho metadata code cũ, không lọc mất metric cũ trước resolver, explicit code thắng alias/fallback, unit là tọa độ fact, read-only compatibility không thay approval.

## Kết quả đã thực chạy

Code/metric nhận từ cấu trúc nguồn; mã chữ-số/zero đầu không bị nhầm thành tên. Exact row/column source scope và metric eligibility áp trong SQL trước LIMIT. View deepcopy được đối chiếu artifact/raw cell/hash/revision; không sửa DBfacts hoặc source. Scalar selection giữ year/unit/qualifier; missing/ambiguous không mượn ô khác.

Live RED bắt rewrite bỏ current recorded-count constraint, trả quota sai dù citation hợp lệ. Đã sửa server-owned current metric/unit constraint tại Fact Resolution, không đổi Intent Router/Memory/model prompt. Selected facts qua published fact guard → atomic pack → claim projection; notes có phạm vi gốc và exact citations. Debug trace chỉ cho admin.

Focused cuối **253PASS**,54testinstances mới. RED ban đầu20FAIL/5PASS; baseline-focused59PASS trước sửa. SQL test dùng PostgreSQL thật trong DBnonce, transaction rollback; exact match tồn tại sau20rows khác và2metadata metric cũ. Ruff17file/diffcheck/UTF8noBOM-LF PASS. Full gate chốt theo [VALIDATION_REPORT](../bao_cao/context565/VALIDATION_REPORT.md), không gọi suite có lỗi nền là PASS.

ASGI realupstream13/13, TCP8/8 và2scalar cuối đạt. Audit độc lập23responses đối chiếu selected fact với canonical row/column/value và exactspan/hash. Numeric direct0LLM/dense/reranker; TCP2Qwensuccess chỉ resolve follow-up. Prose case riêng thực chạy embedding/Qdrant/reranker/Qwen, final từ verifiedcanonicalfallback. Không claim dense cho numeric request.

Một assertion cũ trong `test_facts.py` đổi theo contract được user yêu cầu: bare Số lượng giữ rawheader/unknown, không sinh quota sai; giữ fixture/value, thêm negative. Không che lỗi bằng thay gold. Numeric gold lấy livecanonical, không số trong prompt.

## Phạm vi

Thêm `knowledge/entity_codes.py`, `knowledge/metric_roles.py`, `rag/source_fact_resolution.py`, `tests/test_context565_entity_metric.py`; sửa các caller facts/table/sourceartifact/queryrouter/temporal/service/proof/debug liên quan. Danh sách file/hàm và tests tại [IMPLEMENTATION_REPORT](../bao_cao/context565/IMPLEMENTATION_REPORT.md), [REGRESSION_IDS](../bao_cao/context565/REGRESSION_IDS.md). Bảo toàn các sửa chưa commit Context564. Không frontendcode/schema migration.

## Dữ liệu và giới hạn

Preflight DB/MinIO/Qdrant loopback; DB test nonce riêng, Storage riêng, networktestport1; source đọc READONLY. EncryptedModelOps3providers/2credentialrows sao vào DBtest để giữ paritybaseline, không đổi config gốc/in secrets. Before/after seals5collections/23bindings/2sources/27indexes/5assistants/13providerconfigs khớp.

14ownthreads/6gaps đã dọn, usageauditgiữ; cleanup DB/runtime chốt ở validationreport. Evidenceprivate `backend/storage/context565` giữ đối soát, không Git corpus/credentials. Không commit/push/deploy/restart/reindex/republish/sourcewrites/modelconfigchanges.

Read-only legacy compatibility cần exact row/columnlocator; thiếu thì từ chối an toàn. Chưa benchmark85%, toàn dạngsource, concurrency/load hoặc productionready. [Bàn giao](../bao_cao/context565/REVIEW_READY.md).

## Chốt regression và cleanup

Full-verified: **2747PASS/18FAIL/17SKIP+23subtestsPASS**,exit1. Exact Context564→565:54addedPASS/0changed/0removed,18failureIDs/causes giữ nguyên. Full-current lần đầu có2newFAIL do orchestration unit fixtures chưa mock strategy boundary; cập nhật đúng2mock giữ toànassertions,70PASS rồi chạy full lại. Không sửa production để phát hiện/bỏ qua mock. Các tests đó không làm bằng chứng numeric E2E.

DB test đã dọn; xóa runtime Storage riêng bị kiểm duyệt tự động chặn **blocked by policy**. Giữ runtime, không bypass hoặc đổi cách xóa; evidence và usage audit giữ lại.
