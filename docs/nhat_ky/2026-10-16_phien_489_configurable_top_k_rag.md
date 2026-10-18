# Phiên 489 — Configurable Top K và chẩn đoán RAG

## Yêu cầu và phạm vi

User cho phép áp dụng đề xuất từ ZIP và paper 2407.01219v1, hướng tới RAG dùng
chung nhiều chatbot. Batch này là đợt 1: cấu hình K xuyên suốt, đối chứng/tùy chỉnh,
telemetry và retrieval-only inspector. Không tuyên bố đã xử lý mọi lĩnh vực.

Đọc skill clean-code, backend, frontend/admin design, RAG pipeline và evaluation;
dùng component/contracts sẵn có, giữ thay đổi chưa commit của phiên 487/488 và
corpus người dùng. Không copy ZIP/corpus vào repo, không thay provider, model,
schema DB, nguồn/vector/publication; không restart, commit, push hoặc deploy.

## Triển khai

- `backend/app/core/retrieval_policy.py`: contract legacy/configured; K dense và
  lexical độc lập (null dùng retrieval_limit); fusion, context, ký tự có giới hạn
  và kiểm tra context<=fusion. Legacy mặc định không đổi hành vi đang chạy.
- Assistant knowledge schema/API config JSONB chứa policy mới, runtime profile
  hiện hữu truyền xuống RAG. Không cần migration hoặc backfill DB.
- `rag/retriever.py`: áp từng K đúng bước, giới hạn fusion trước rerank;
  anchor prefetch có thể giữ fusion candidates thay vì cắt sớm còn final K;
  trace content-free với counts/timings/score-observed/degrade. Giữ RRF và quyền,
  snapshot, provenance hiện hữu; không gọi PostgreSQL FTS là BM25.
- `rag/service.py`, schemas và `retrieval_diagnostics.py`: search nhận policy hoặc
  assistant_code đúng collection/active; assistant policy ưu tiên khi được chọn.
  Ask trả trace của nhánh thực; cache không báo như retrieval mới. Ngân sách
  fact/hybrid giữ nguyên nhóm hàng/header/neighbor hoặc loại cả nhóm, không cắt
  giữa đoạn. Không append lại neighbors đã bị loại trong composer. Facts cũng
  được tính vào ngân sách, quá giới hạn báo CONTEXT_BUDGET_INSUFFICIENT.
- `evidence_pipeline.py`/`evidence_retrieval.py`: policy tùy chỉnh áp anchor,
  canonical/BM25 fusion, rerank và packing, kể cả corrective/historical. Giữ
  kiểm chứng năm/nguồn/list dependency hiện có.
- Assistant DTO và `assistant_rag_chat.py` chuyển trace qua JSON/SSE done;
  frontend hook nhận trace ở cả hai kiểu response.
- UI tại Cấu hình: card dùng primitives/Field sẵn có, preset chỉ điền form,
  validation Zod và backend; khóa Top K legacy khi đang tùy chỉnh. Policy-update
  lưu qua API trợ lý hiện hữu, không gọi API cấu hình mới hoặc giả submit.
- Playground: chẩn đoán và form TanStack Form/Query kiểm tra chunk search không
  sinh đáp án, có pending/error/empty, rõ khác toàn pipeline chatbot.
- Thêm `probe_retrieval_489.py`, tests backend/FE, quy trình 09.

## Kiểm tra đã chạy

Từ backend, Python `.venv/Scripts/python.exe -X utf8`; các lượt async được chạy
ngoài sandbox Windows vì sandbox từng kẹt proactor/socketpair, không sửa event loop.

| Kiểm tra | Kết quả thực tế |
|---|---|
| Ruff scoped 11 file Python cuối batch | PASS, exit 0 |
| Pytest scoped configurable/retrieval/488/evidence/chat | 69 passed, exit 0 |
| Full Pytest `-q --basetemp=storage/pytest-basetemp-489-final --junitxml=storage/pytest-489-final.xml` | **FAIL: 1706 passed / 11 failed / 17 skipped**, 205.30s, exit 1 |
| XML so với `pytest-488-locked-delivery.xml` | exact failure IDs bằng nhau, không thêm/bớt |
| FE Node retrieval-policy tests | 3 passed, exit 0 |
| FE Node auth tests | 46 passed, exit 0 |
| Biome scoped 11 files, `--line-ending=lf` | PASS, không còn fix |
| `npm run build` cuối batch | PASS, Vite 4.24s + tsc, exit 0; log storage/fe-build-489-final.log |

Full suite có cảnh báo đóng kết nối asyncpg trên event loop đã đóng; không sửa
ngoài phạm vi hoặc đổi assertion để che lỗi. 11 failure IDs:

1. tests/test_consulting_dispatcher.py::test_dispatch_admissions_with_export
2. tests/test_consulting_dispatcher.py::test_dispatch_regulations_with_export
3. tests/test_publishing_v2_cutover_and_gc.py::test_gc_api_endpoint
4. tests/test_publishing_v2_cutover_and_gc.py::test_canary_policy_get_and_update_api
5. tests/test_publishing_v2_decommissioning_and_system_gc.py::test_direct_upload_blocked_when_flag_disabled
6. tests/test_publishing_v2_decommissioning_and_system_gc.py::test_direct_upload_allowed_when_flag_enabled
7. tests/test_publishing_v2_decommissioning_and_system_gc.py::test_rest_api_system_wide_gc_and_decommissioning_audit
8. tests/test_publishing_v2_e2e_canary.py::test_api_routes_canary_and_rollback
9. tests/test_rag_data_truth_and_lifecycle.py::test_reconciliation_detects_discrepancies
10. tests/test_trust_boundary_and_hitl.py::test_auth_session_cookie_actor_claims
11. tests/test_universal_tools.py::test_dispatch_admissions_with_dynamic_facts

## Retrieval thật 20 câu

Lệnh từ backend: `python -X utf8 -m scripts.probe_retrieval_489 --live --limit 20`.
Exit 0, **40/40 records** trên 20 câu đầu file 82 câu hiện có, cùng snapshot
fingerprint `b7456674dcc9b51ce736`, 22 active bindings. Pin snapshot xuyên hai
profile. HTTP allowlist chỉ server AI nội bộ/loopback; không gọi LLM generation.

Đây là ablation tại retriever: legacy 12/12, không cap fusion, final 5 so với
30/30/30/5, cùng reranker/threshold và query; không phải hai lượt full chatbot có
intent/facts/enumeration. Không có gold IDs đã duyệt nên accuracy/recall NOT SCORED.

| Quan sát | Legacy | Configured |
|---|---:|---:|
| Requests hoàn tất | 20 | 20 |
| Câu còn hits sau rerank | 18 | 18 |
| Dense hits tổng | 240 | 600 |
| Lexical hits tổng | 222 | 546 |
| Mean ms | 527.36 | 500.31 |
| Median ms | 469.75 | 486.105 |
| p95 nearest-rank ms, n=20 | 856.65 | 626.52 |

13/20 câu thay đổi tập hoặc thứ tự kết quả. Câu 16 và 18 có candidates trước
rerank nhưng trả 0 sau rerank ở cả hai profile; không kết luận thiếu tài liệu.
Ngưỡng hiện tại giữ nguyên, không hạ để làm đẹp số hit. Không thấy degrade ở trace.
Chạy tuần tự, warmup/cache chưa kiểm soát; không suy preset mới nhanh hơn từ bảng.

Artifact runtime: `backend/storage/retrieval_489/comparison.json`,
`storage/retrieval-489-live.log`; không stage vào Git. Fingerprints assistant
config, collection metadata và publication trước/sau **đều không đổi**.
ModelOps có thể cập nhật lease/thống kê vận hành như request thông thường.

## UI và giới hạn

Browser local đã đăng nhập: thấy legacy mặc định; preset điền đúng 30/30/30/5;
ô legacy bị khóa; nhập context 31 hiển thị lỗi (không lưu); reload bỏ dữ liệu
thử. Đã xem screenshot viewport hẹp khoảng 711px, form không tràn ngang. Playground
hiển thị inspector/no-telemetry honest. Không bấm lưu cấu hình thật, không chạy
chat generation qua browser; chưa kiểm desktop rộng/dark toàn diện hoặc lưu/F5
round-trip trên DB thật. Build/typed schema không thay thế kiểm chứng này.

Chưa chạy 82 câu sinh đáp án; chưa có đánh giá đúng/sai từng câu, ground-truth
retrieval hoặc benchmark đa lĩnh vực. Chưa thêm normalized fusion alpha*sparse+dense,
BM25 vào nhánh legacy, HyDE, model monoT5/TILDEv2 hay repacking. RAG hiện hữu vẫn có
các giới hạn synthesis/OCR được ghi ở phiên 488. Không gọi batch này là RAG hoàn hảo
cho mọi chatbot hoặc bật toàn bộ kết luận paper mặc định.

Tiếp theo: review căn cứ cho 20 câu và hai ca bị lọc sau rerank; thử riêng một biến
fusion hoặc repacking, giữ snapshot/nguồn/model. Chỉ cân nhắc kích hoạt preset sau
khi có kết quả đúng năm/metric/citation và hồi quy đạt.
