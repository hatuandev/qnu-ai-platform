# Phiên911 — Làm sạch backend V1 trước FE mới

## 1. Yêu cầu, phạm vi và giả định

Người dùng giao **triển khai sửa code và kiểm chứng** đợt làm sạch backend V1 theo báo cáo
[phiên910](./2026-11-09_phien_910_ra_soat_backend.md), không chỉ lập kế hoạch. Mục tiêu sản phẩm:
người dùng thường hoàn tất **Tải tài liệu → Chuẩn bị nội dung → Xem và chỉnh sửa → Duyệt và phát
hành → Sẵn sàng cho trợ lý** mà không phải chọn công cụ OCR, context/input/output, chunking hay
thế hệ chỉ mục; backend tự điều phối theo loại tài liệu, cấu hình ModelOps được phép và trạng thái
dữ liệu thật. Batch này **chỉ backend**, không xây frontend mới và không thiết kế lại UI V1.

Giữ nguyên các bất biến: tệp gốc, canonical OCR, bảng/ô/header/footnote/bbox, revision/hash và
bằng chứng; quyền workspace và kiểm nguồn hiện hành ở server; hoàn tất chuẩn bị không đồng nghĩa
đã duyệt/phát hành; chỉ nội dung đủ điều kiện mới vào chỉ mục phục vụ; chỉ mục mới chỉ thay bản
đang phục vụ sau khi kiểm chứng; giữ idempotency, lease, hủy, audit và trạng thái `uncertain`;
lỗi hạ tầng/provider phải báo thật, không thành công giả hay "không có dữ liệu"; model giải quyết
động qua ModelOps, giữ reasoning off đã xác nhận; không thêm trần output cố định khi caller để
tự động; không khôi phục quota token tháng; không hardcode ngành/năm/tài liệu/đáp án benchmark;
không xóa parser/projection cũ khi dữ liệu còn cần.

Không clear/reset/seed/reindex, không upload lại, không thay publication, không restart phiên người
dùng, không deploy, không Git push. Không chạy test trên DB ứng dụng và không cài thêm dependency.
Dùng lại bảng kiểm chứng [verification](../../.agents/rules/verification.md) và quy trình
[workflow/memory](../../.agents/rules/workflow-and-memory.md).

## 2. Kết quả theo phạm vi

### A — Hợp đồng chuẩn bị tự động là luồng chính

- `PreparationRequest.mode` mặc định **`auto`**; caller thường chỉ cần `Idempotency-Key` và thân
  yêu cầu tối giản. Server chọn policy được phép, không để client chọn cờ compiler.
- Tách `preparation/plan.py` làm một nguồn duy nhất cho: hash yêu cầu, `plan_flags`, chọn policy
  tự động, xác minh policy đã ghim, khóa tái sử dụng và truy vấn run tái sử dụng. `service.py`
  giảm 198 dòng, không còn hai bản logic.
- `auto` không chặn khi thiếu chat tùy chọn: chỉ các mã thiếu cấu hình chat đã biết mới chuyển
  policy sang `disabled` và chạy source-only; lựa chọn provider/model tường minh vẫn lỗi rõ.
  Danh sách mã nằm ở `modelops/public_api.py:OPTIONAL_CHAT_UNAVAILABLE_CODES`.
- Run source-only không ghi provider giả: `kb_compilation_runs.provider_id` cho phép null
  (migration `0019_source_only_compilation`), schema API `provider_id: str | None`; run lịch sử
  giữ provider đã ghim.
- Replay tôn trọng hợp đồng đã lưu: khóa idempotency cũ của yêu cầu bỏ trống mode (đã hash là
  `source`) vẫn trả đúng intent thay vì báo xung đột; yêu cầu khác nội dung vẫn `idempotency_conflict`.
- Thay đổi model/chính sách giữa chừng bị phát hiện bằng `configuration_hash` đã ghim
  (`preparation_policy_changed`), không âm thầm đổi model.
- Sửa draft vẫn kế thừa review/provider khi có; run source-only không tạo cấu hình review rỗng
  (`compilation/workflow/edits.py`).
- API compiler nhiều bước, review và index thủ công vẫn giữ cho quản trị/tích hợp.

### B — Tích hợp OCR ở composition root

- `api/wiring.py` tạo `ManagedOcrEngine(NemotronOcrEngine(), document_adapter=MineruOcrEngine())`.
  Adapter trang và adapter tài liệu được tiêm từ composition root.
- `ManagedOcrEngine` đổi tên trung tính `name = "ocr"`; domain không còn tự nhập hay tự tạo
  `MineruOcrEngine`. Thiếu adapter tài liệu trả `503 ocr_document_adapter_missing`, không fallback
  giả.
- Giữ nguyên artifact, fingerprint, quyền, hash, lease và các nhánh OCR trang/tài liệu; không đổi
  hành vi đọc tài liệu chỉ có text.

### C — Loại cấu hình không còn hiệu lực

- Bỏ khỏi `Settings` và mọi template/help/runner: `COMPILER_MAX_OUTPUT_TOKENS`,
  `RAG_MAX_OUTPUT_TOKENS`, `CONVERSATION_REWRITE_MAX_OUTPUT_TOKENS`, `QDRANT_COLLECTION`,
  `VECTOR_SIZE`. Giá trị cũ trong môi trường được bỏ qua, không còn trông như đang áp dụng.
- Ngân sách output lấy từ ModelOps/caller; tên/kích thước collection lấy theo run/model embedding.
- Giữ nguyên các cấu hình còn hiệu lực: concurrency, upload, lease, I/O timeout, OCR max output
  tường minh.
- Thêm `tests/unit/test_retired_env_config.py` khẳng định biến cũ không tạo thuộc tính.

### D — Hoàn tất deprecate quota tháng

- `GET /workspaces/{id}/quota` chỉ đọc thống kê kỳ: `monthly_token_limit` luôn null,
  `is_blocked` luôn false; `configured` chỉ phản ánh có dòng sử dụng.
- `PUT /workspaces/{id}/quota` là shim tương thích: nhận body cũ nhưng bỏ qua, chỉ bảo đảm kỳ sử
  dụng tồn tại; không áp giới hạn, không chặn inference/index.
- Không cần khởi tạo quota tháng để gọi model; reservation/settlement, chống ghi trùng và audit
  giữ nguyên. Không sửa hàng loạt DB ứng dụng.
- Thêm test đọc quota trước khi có usage: trả 0, limit null, không block.

### E — Dọn stub/khung không dùng

- Xóa `qnu/adapters/providers/gemini.py` và `paddleocr.py` (constructor chỉ ném
  `NotImplementedError`) sau khi xác minh không có import/wiring/caller.
- Xóa các gói khung rỗng: `domains/document_types`, `node_catalog`, `tools`, `workflows` (+`nodes`),
  `knowledge/{chunks,facts,glossary,imports,maintenance,normalization,parsers,wiki}`,
  `rag/{diagnostics,evidence,query,search}`.
- Giữ literal `provider_type` (`gemini`, `paddleocr`) trong ModelOps vì là giá trị cấu hình đã lưu
  và registry mô tả "chưa có adapter"; không xóa dữ liệu/khế ước cũ theo tên tệp.
- OpenAPI vẫn sinh đủ 163 path/205 operation, không đổi hợp đồng API.

### F — Tách coordinator lớn theo trách nhiệm

- `compilation/access.py` + `compilation/reads.py`: quyền/khóa/đọc run/draft/progress ra khỏi
  `compilation/service.py` (giảm 320 dòng); `service` giữ entry point công khai và re-export ổn định.
- `compilation/review/access.py` + `review/readers.py`: quyền, expire/lease, target hash, danh sách,
  artifact/reading ra khỏi `review/service.py` (giảm 389 dòng); `__all__` giữ tên công khai.
- `preparation/plan.py`: planner thuần cho hash/policy/flags/reuse (mục A).
- `rag/answer/packing.py`: tách `pack_messages` khỏi `answer/service.py`; thân hàm giữ nguyên từng
  bước, service chỉ còn pipeline tuyến tính.
- `knowledge/index/router.py`: chuyển truy vấn danh sách IndexRun vào `index/service.list_runs`
  sau authorize; router mỏng trở lại.
- Giữ nguyên transaction, lease, idempotency, quyền, trạng thái nguồn và retry. Các executor còn
  lại (`compilation/execution.py`, `review/execution.py`, `review/parts.py`) là vòng lặp bền vững
  dùng chung session/lease/transaction; tách tiếp sẽ tạo import helper private chéo module, trái
  yêu cầu, nên không tách cơ học.

## 3. Tệp thay đổi

- Backend: `qnu/api/wiring.py`, `qnu/platform/config.py`, `qnu/platform/schema.py`,
  `qnu/domains/modelops/{public_api.py,usage/router.py,resilience/execution.py}`,
  `qnu/domains/knowledge/preparation/{schemas.py,service.py,plan.py}`,
  `qnu/domains/knowledge/compilation/{models.py,schemas.py,service.py,access.py,reads.py}`,
  `qnu/domains/knowledge/compilation/review/{service.py,access.py,readers.py}`,
  `qnu/domains/knowledge/compilation/workflow/edits.py`,
  `qnu/domains/knowledge/index/{router.py,service.py}`,
  `qnu/domains/rag/answer/{service.py,packing.py}`; xóa 2 adapter stub và các gói khung rỗng.
- Migration: `alembic/versions/0019_source_only_compilation.py`.
- Test: `tests/integration/test_preparation_intents.py` (3 ca mới),
  `tests/integration/test_workspace_model_boundaries.py` (1 ca quota),
  `tests/unit/test_retired_env_config.py` (mới).
- Cấu hình/tài liệu: `.env.example`, `.env.dokploy.example`, `backendV1/.env.example`,
  `docker-compose.yml`, `scripts/v1_e2e_session.py`, `docs/architecture.md`,
  `backendV1/docs/{compiler-v1.md,feature-port-matrix.md,runtime-ownership.md}`,
  `docs/quy_trinh/V1_MODELOPS_NGAN_SACH_TU_DONG.md`, `docs/quy_trinh/47_hop_dong_luong_chinh_backend_v1.md`.

## 4. Kiểm chứng

Mọi lệnh dưới chạy trong `backendV1` trên DB cô lập của `scripts/test_database.py` (trừ Ruff,
OpenAPI và rg). Không chạy trên DB ứng dụng.

| Nhóm | Lệnh | Kết quả thực chạy | Receipt/thời gian |
| :--- | :--- | :--- | :--- |
| A | `uv run python scripts/test_database.py tests/integration/test_preparation_intents.py` | **20 passed** | `qnu_v1_test_9f34e96440224ee2`, 72,97s |
| A+E | `... test_preparation_intents.py test_preparation_publication_chain.py tests/unit/test_automatic_budget_791.py tests/unit/test_automatic_metadata_896.py` | **42 passed** | `qnu_v1_test_4f39947b42a64c22`, 81,39s |
| B | `... test_auto_extraction_710.py test_mineru_823.py test_modelops_resilience_695.py` | **50 passed** | `qnu_v1_test_06a3e29fe0664d7b`, 129,11s |
| C | `... tests/unit/test_retired_env_config.py test_model_capacity_641.py test_ocr_config.py test_index_budget_869.py` | **44 passed** | `qnu_v1_test_ba3c168be91c4725`, 9,16s |
| D | `... test_workspace_model_boundaries.py test_readiness_666.py test_ocr_observability_644.py` | **23 passed** | `qnu_v1_test_98305cb706134d65`, 68,61s |
| F compiler | `... test_compiler_api_645.py test_compiler_segments_api_744.py test_compiler_source_first_854.py test_compiler_review_652.py test_index_api_647.py tests/unit/test_compilation_segments_744.py tests/unit/test_compilation_review_parts_744.py` | **85 passed** | `qnu_v1_test_0c99d460399c40e4`, 327,89s |
| F review/index | `... test_compiler_review_652.py test_compiler_review_segments_750.py test_compiler_refinement_751.py test_manual_review_queue_852.py test_review_budget_758.py test_review_empty_blocks_736.py test_review_literal_751.py test_review_gate_666.py test_review_schema_655.py test_index_api_647.py test_index_readiness_819.py tests/unit/test_compilation_fencing_744.py tests/unit/test_compilation_review_parts_744.py tests/unit/test_compiler_review_budget_757.py tests/unit/test_compiler_review_refinement_755.py` | **118 passed** | `qnu_v1_test_4f7359dfa3004496`, 441,55s |
| F RAG | `... tests/unit/test_rag_clause_context_856.py tests/unit/test_rag_context_908.py tests/unit/test_rag_modelops_budgets_767.py tests/integration/test_rag_context_908.py tests/integration/test_answers_api_648.py tests/integration/test_answer_coverage_861.py tests/integration/test_rag_scope_context_672.py tests/integration/test_rag_verification_policy_672.py tests/unit/test_answer_*.py` | **140 passed, 1 failed** (lỗi nền fixture, mục 5) | `qnu_v1_test_bce0392e849d487e`, 464,25s |
| F RAG solo | `... "tests/integration/test_rag_verification_policy_672.py::test_assistant_chat_uses_persisted_hybrid_rerank_policy_and_checks_provider_access"` | **1 failed** (tái hiện độc lập) | `qnu_v1_test_c07d04e51ead46f7`, 20,41s |
| Ruff | `uv run ruff check <26 file .py đã đổi>` | **All checks passed** | — |
| OpenAPI | `uv run python -c "from qnu.main import app; ..."` | **163 path / 205 operation / 1 deprecated PUT quota** | — |
| Full suite | `uv run python scripts/test_database.py tests` | **NOT RUN — đã dừng trước khi hoàn tất** | `qnu_v1_test_9f76fb9421be44e1` đã bị dừng khi bắt đầu batch sửa tiếp theo; không dùng kết quả dở dang |

Ghi chú phương pháp: lần chạy đầu dùng `source ../.env` bị exit 2 vì `.env` có biến rỗng phá
môi trường; đã chuyển sang chỉ export `DATABASE_URL`/`REDIS_URL` bằng vòng đọc `IFS='='`. Đây là
lỗi công cụ chạy lệnh, không phải kết quả test.

## 5. Lỗi nền, giới hạn và rủi ro

- **Lỗi nền đã giữ nguyên:** `test_rag_verification_policy_672.py::test_assistant_chat_uses_persisted_hybrid_rerank_policy_and_checks_provider_access`
  thất bại vì fake chat trong `test_answers_api_648.py:FakeAnswerChat._respond` đọc thẳng
  `incoming["tables"]`, trong khi envelope chỉ có khóa này khi có ô bảng được chọn; không có bảng thì
  provider thread ném `KeyError: 'tables'` và lượt chat trả 504 `chat_provider_uncertain`. Nguyên
  nhân phía fixture: `FakeRerank` chấm điểm cao nhất cho tài liệu **cuối** danh sách ứng viên, còn
  thứ tự ứng viên RRF dùng `chunk_id` làm khóa phá hòa (`index/hybrid.py:fuse`), mà `chunk_id` sinh
  bằng `uuid4` mỗi lần chạy (`ocr/ids.py:new_id`); khi điểm hòa, lựa chọn bảng/đoạn có thể đổi giữa
  các lần chạy. Ca này từng PASS lúc 08:42 và FAIL lúc 10:46 trên cùng nhánh làm việc; thân
  `_pack_messages` chuyển sang `packing.py` giống HEAD từng ký tự nên refactor không đổi hành vi.
  Ca cũng tái hiện khi chạy một mình trên DB mới. Không nới assertion để làm xanh; sửa fixture phải
  làm fake chịu được envelope không có bảng (hoặc chọn ứng viên theo nội dung) trong việc riêng.
- **F13 của phiên908 vẫn là lỗi chất lượng riêng**, chưa sửa và không được tính là đã đạt bởi
  refactor hay test mock.
- **NOT RUN:** model/OCR thật, benchmark RAG, kiểm tải, trình duyệt/FE, migration trên DB ứng dụng.
  Full suite đã bị dừng trước khi hoàn tất và không có kết quả dùng được; phiên912 chạy lại nhóm
  đích trên DB cô lập riêng.
- **Migration 0019 chưa áp lên DB ứng dụng.** Khi người dùng cho phép khởi động lại môi trường dev,
  cần áp `0019_source_only_compilation` trước khi chạy API/worker mới; batch này không tự migrate.
- Giữ nguyên working tree của các phiên909/910 và không commit/push.

## 6. Bước tiếp theo

1. Chờ full suite hoàn tất, ghi receipt thật và phân loại mọi lỗi còn lại (nền hay mới).
2. FE mới dùng hợp đồng luồng chính tại [47 — Hợp đồng luồng chính backend V1](../quy_trinh/47_hop_dong_luong_chinh_backend_v1.md);
   không đưa cờ compiler/OCR/context/output vào luồng người dùng thường.
3. Khi được phép: áp migration 0019 cho môi trường dev, chạy lại `make dev` và E2E từng bước.
4. Sửa riêng fixture RAG và xử lý F13 bằng đo lường chất lượng, không trộn với batch cấu trúc này.
