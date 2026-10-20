# Context565 — File và hành vi thay đổi

| File trong `backend/` | Thay đổi phục vụ Context565 |
|---|---|
| `app/modules/knowledge/entity_codes.py` | Candidate, exact token boundary, lossless normalization và code-cell syntax |
| `app/modules/knowledge/metric_roles.py` | Compositional quantity roles, unit extraction |
| `app/modules/knowledge/facts.py` | Dùng metric role chung; giữ bare quantities dưới raw header/unknown; tách recorded/estimate/rate |
| `app/modules/knowledge/services/source_artifact.py` | Thêm metric attributes/unit theo role, extractor version mới |
| `app/modules/knowledge/services/table_context.py` | Code/name riêng, bảo toàn underscore, nối trang chữ-số theo cấu trúc |
| `app/modules/rag/query_router.py` | Code candidates, không chèn static major code khi explicit code có mặt; thêm requested quantities |
| `app/modules/rag/source_fact_resolution.py` | Read-only canonical row/column resolution, sealed fact validation và selected fact proof |
| `app/modules/rag/facts.py` | Exact row + canonical metric predicates trước LIMIT; trả detached view, không update fact |
| `app/modules/rag/temporal_answer.py` | Exact code/metric/year/unit/context; missing/ambiguous/conflict; current constraint override |
| `app/modules/rag/evidence_facts.py` | Optional server-selected fact IDs trước fetch để dùng lại proof builder, không nạp toàn fact pool cho câu hỏi scalar |
| `app/modules/rag/source_rows.py` | Exact code/name fallback dùng chung normalization, code rõ ràng thắng name, không match mã trong metric |
| `app/modules/rag/retrieval_diagnostics.py` | Không đưa fact-resolution trace vào phản hồi public; chỉ debug được cấp quyền |
| `app/modules/rag/schemas.py` | Private server-owned current constraints, không thêm client DTO field |
| `app/modules/rag/service.py` | Nối resolver/lookup/proof, chặn fallback đổi thực thể/metric, canonical citations và required source context |
| `tests/test_context565_entity_metric.py` | Unit, source fixture, SQL rollback, guard, current metric và compatibility tests |
| `tests/test_facts.py` | Một assertion contract cũ được cập nhật theo yêu cầu unknown quantity, thêm negative chống tạo quota sai |
| `tests/test_revision_safe_qdrant_and_retrieval.py` | Hai unit tests orchestration mô phỏng rõ ranh giới source-cell strategy để tiếp tục kiểm nhánh hybrid weights/composer; giữ toàn bộ expected/assertions cũ |

Không sửa hai file packing `evidence_blocks.py`/`evidence_dependencies.py` thuộc diff Context564 đang tồn tại. Không ghi đè các thay đổi chưa commit của người dùng.

## Thay đổi hợp đồng test được công khai

Test `test_extract_admissions_table_row_facts` trước đây yêu cầu cột bare `Số lượng` thành `Chỉ tiêu`. Yêu cầu Context565 trực tiếp loại bỏ hành vi này. Fixture/value giữ nguyên; assertion nay yêu cầu nhãn `Số lượng`, không có fact `Chỉ tiêu`, `attribute_code=None`. Đây là đổi contract có căn cứ sản phẩm, không sửa expectation để che một đáp án sai. RED ban đầu và lần focused có lỗi này được giữ trong evidence.

Full-current lần đầu có2newFAIL ở unit tests kiểm hybrid composer/intent weights: các test này đã mock lookup/retriever/model và dùng AsyncMock DB không có canonical source result. Khi strategy mới chạy, result giả không thể duyệt như SQL result thật. Fixture nay mock source-cell strategy/temporal decision tại ranh giới của unit test, giữ nguyên question/value/assertions về hybrid weights/temperature/facts. Không có production branch kiểm mock hoặc bỏ guard. New-source strategy có54tests và runtime23responses riêng; không dùng2unit tests này làm bằng chứng numeric E2E. `orchestration-compat`70PASS và full gate cuối chạy lại sau thay fixture.

## Bất biến và giới hạn

Không schema migration, provider/model/config/context/top-K change; không sửa published artifact/source/index/approval, không reindex/republish/restart/deploy/Git writes. Old artifact version giữ nguyên khi đọc; chỉ dẫn xuất mới mang version mới.

Không thêm Entity Service hoặc framework mới. Loader tái dùng publication/snapshot/evidence guards; không nhận model/client code như quyền truy cập. Debug tiếp tục qua cơ chế admin hiện có; không thêm raw corpus hoặc keys vào log/docs.

Sau batch live ban đầu, focused thêm guard multi-entity coverage, khác đơn vị và code/name fallback. `focused-current` có253PASS,54testinstances mới; TCP bổ sung2scalar requests trên mã cuối xác nhận public không có trace và debug có trace, không gọi model. Ruff17files gồm2testfiles cũ được thay đổi có giải thích.

Current metric enforcement là lỗi tích hợp được live test chứng minh, không refactor Intent Router/Memory. Kiểm thử E2E không yêu cầu bật `evidence_policy.enabled` đang false. Raw canonical và materialized facts được giữ cùng proof; scalar numeric answer không cần LLM, dense hoặc reranker.

Artifact thiếu exact row/column mapping được từ chối an toàn; không tuyên bố hỗ trợ mọi format legacy. Chưa chạy benchmark chất lượng 85%, concurrency/load hoặc đo SLA production.
