# Phiên 499 — Session DB truy hồi và nhãn chất lượng trung thực

Ngày: 2026-10-16.

## Phạm vi được thực hiện

Tiếp báo cáo 493 và batch 498: sửa hai điểm trong batch kế tiếp, không coi đây là
hoàn tất toàn bộ báo cáo 493. Dùng hướng dẫn Clean Code, Backend, RAG, Frontend và
admin design của repo; tái dùng thành phần và token giao diện hiện có.

Giữ thay đổi chưa commit. Không thay nguồn, vector, snapshot đang xuất bản, DB,
ModelOps, policy provider hoặc migration; không reindex, restart, deploy, commit/push.
Không gọi model thật hoặc chạy benchmark 10/20/82 câu.

## Nguyên nhân và thay đổi

### Session DB bị dùng chồng trong hybrid retrieval

`HybridRetriever.retrieve` dùng `asyncio.gather` để chạy truy vấn lexical gốc,
hai biến thể và hai truy vấn glossary trên cùng AsyncSession. SQLAlchemy async
session không phải tài nguyên cho nhiều thao tác đồng thời. Lỗi biến thể bị nhánh
degradation bắt nên có thể mất candidate thay vì hiện lỗi rõ ở mức request.

- Cho toàn bộ SQL lexical dùng session của caller tuần tự, giữ nguyên thứ tự,
  giới hạn, trọng số và chính sách degradation hiện có.
- Tìm kiếm vector độc lập vẫn chạy song song với SQL.
- Nếu SQL gốc lỗi hoặc request bị hủy, hủy và thu hồi task vector trước khi trả về;
  không commit/rollback/close session của caller.
- Giữ cùng đối tượng retrieval snapshot cho mọi nhánh, không đổi phạm vi năm,
  collection, binding hay revision.

Tệp: `backend/app/modules/rag/retriever.py`;
regression mới `backend/tests/test_retrieval_session_safety_499.py`.

### Nhãn Faithfulness cố định

Playground luôn hiện dấu kiểm xanh và `Faithfulness ≥ 0.90`, kể cả khi không có
phép đo cho câu trả lời. Hook hiện tại không cung cấp điểm Faithfulness thực.

- Đổi thành nhãn trung tính **Faithfulness: Chưa đo**.
- Nêu rõ trích dẫn không đồng nghĩa với điểm chất lượng; không suy điểm từ số
  trích dẫn, trạng thái answered hay retrieval hits.
- Không thêm phép chấm tự động hoặc trường API giả. Không sửa readiness score
  của cấu hình trợ lý: đây là chỉ số khác, ngoài phạm vi.

Tệp: `frontend/src/features/assistants/assistant-playground-tab.tsx`.

## Kiểm chứng thực chạy

### Regression trước/sau sửa

Bốn ca mới: SQL gốc + 2 biến thể + 2 glossary không chồng session; vector vẫn
song song; lỗi SQL/hủy request thu hồi vector; lỗi biến thể được trace và các
biến thể sau vẫn chạy đúng thứ tự. Kiểm tra giữ session/snapshot và tập candidate.

- Trước sửa: **2 FAIL / 2 PASS**, tái hiện mất bốn biến thể do chồng session và
  task vector còn chạy sau lỗi SQL.
- Sau sửa, bộ mới + lân cận: **57 PASS**.
- Ruff scoped: **PASS**.

Lệnh (thư mục `backend`; basetemp riêng có hậu tố UUID):

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_retrieval_session_safety_499.py tests/test_configurable_retrieval_489.py tests/test_revision_safe_qdrant_and_retrieval.py tests/test_rag.py -q -p no:cacheprovider --basetemp $sessionTemp499
.\.venv\Scripts\ruff.exe check app/modules/rag/retriever.py tests/test_retrieval_session_safety_499.py
.\.venv\Scripts\python.exe -m pytest -q --tb=short -p no:cacheprovider --basetemp $gate499 --junitxml=storage/session-safety499-full.xml
```

### Full backend — tổng thể vẫn FAIL

**1799 PASS / 11 FAIL / 17 SKIP**, 210,27 giây. So sánh classname + testcase
với `backend/storage/safety498-final-verified.xml`: không thêm/bớt ID lỗi.
Artifact hiện tại: `backend/storage/session-safety499-full.xml`.

11 ID lỗi nền (không sửa trong batch):

```text
tests.test_consulting_dispatcher::test_dispatch_admissions_with_export
tests.test_consulting_dispatcher::test_dispatch_regulations_with_export
tests.test_publishing_v2_cutover_and_gc::test_gc_api_endpoint
tests.test_publishing_v2_cutover_and_gc::test_canary_policy_get_and_update_api
tests.test_publishing_v2_decommissioning_and_system_gc::test_direct_upload_blocked_when_flag_disabled
tests.test_publishing_v2_decommissioning_and_system_gc::test_direct_upload_allowed_when_flag_enabled
tests.test_publishing_v2_decommissioning_and_system_gc::test_rest_api_system_wide_gc_and_decommissioning_audit
tests.test_publishing_v2_e2e_canary::test_api_routes_canary_and_rollback
tests.test_rag_data_truth_and_lifecycle::test_reconciliation_detects_discrepancies
tests.test_trust_boundary_and_hitl::test_auth_session_cookie_actor_claims
tests.test_universal_tools::test_dispatch_admissions_with_dynamic_facts
```

### Frontend và giao diện thật

Trong `frontend`:

```powershell
npm exec -- biome check --line-ending=lf src/features/assistants/assistant-playground-tab.tsx
npm run build
```

- Biome scoped: **PASS**, dùng LF theo AGENTS (không đổi cấu hình formatter chung).
- Build production gồm Vite và `tsc --noEmit`: **PASS**, exit 0. Lần build trong
  sandbox bị chờ đã dừng; kết quả PASS là lần chạy lại có quyền công cụ phù hợp.
- UI localhost, desktop/light, trang playground: **PASS** cho nhãn trung tính và
  lời giải thích mới. Không gửi câu hỏi. Screenshot:
  `backend/storage/ui499-faithfulness.png`.
- Mobile/dark, hội thoại có lượt trả lời thật: **NOT RUN**.

## Giới hạn và bước tiếp theo

- Chưa đo hiệu năng SQL/PostgreSQL/Qdrant thật khi có tải đồng thời; regression
  mô phỏng biên session, không phải benchmark throughput hoặc accuracy.
- NOT RUN: live inference, UI hội thoại có model, Docker build, benchmark và
  log server AI. Không tuyên bố RAG đạt 80% hoặc toàn hệ thống ổn định.
- Batch tiếp: schema echo và verdict/evidence ID, rồi completeness và hội thoại
  theo các nhóm còn lại của báo cáo 493, với phạm vi riêng được xác nhận.
- Giữ policy provider nội bộ của phiên 498; lỗi model/hạ tầng vẫn phải là lỗi thật,
  không mở cloud hay biến thành câu trả lời “không có dữ liệu”.
