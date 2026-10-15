# Phiên 485 — Một phạm vi ứng dụng và sửa glossary

Ngày: 2026-10-16. Người dùng xác nhận bỏ tenant/workspace **trên toàn app**, không chỉ glossary, rồi sửa 5 lỗi review. Không reset DB, đổi ModelOps, nạp lại nguồn, restart, deploy hoặc Git push.

## Quyết định và tương thích

- API và FE không còn trường/chọn tenant/workspace. `SingleApplicationModel` loại bỏ đầu vào cũ, không công bố hai trường trong OpenAPI/JSON. Đăng nhập, actor, roles, permissions và audit vẫn giữ.
- Truy vấn SQL/Qdrant bỏ phân vùng; vẫn giới hạn collection/binding/revision, published/candidate và lifecycle. Dense Qdrant có điều kiện collection tường minh; snapshot khác collection bị từ chối trước đọc rule/tính điểm.
- **Không xóa cột, không gộp/xóa bản ghi hay object lưu trữ cũ.** Một số cột, đối số và thuộc tính chỉ đọc còn giữ làm cầu tương thích DB/worker; chúng không phải bộ lọc hoặc căn cứ cấp quyền. Hạn ngạch dùng một khóa lưu trữ cũ cố định cho ứng dụng; thống kê usage đọc toàn bộ log. Các dòng cấu hình quota cũ khác không bị sửa/gộp tự động.
- Semantic cache chuyển sang `rag:cache:app-v1:{collection_id}:...`, giữ epoch/snapshot/model/policy/history. Lease nguồn worker dùng `qnu:source-execution:app-v1:{collection_id}:{resource}`; advisory lock hàng đợi dùng một khóa ứng dụng.
- FE bỏ payload/type/hook scope, quota chuyển `/modelops/quotas/current`; bỏ ô tên/slug workspace và đổi nhãn quản trị thành ứng dụng. Workspace canvas OCR/assignment không phải phân vùng dữ liệu, không bị xóa.

## Năm lỗi đã sửa

1. Khóa thuật ngữ/settings với `populate_existing=True` trước kiểm tra `expected_version`; khóa collection khi duyệt/sửa để serialize lần tạo settings đầu tiên.
2. Đọc glossary trong savepoint; chỉ thiếu bảng PostgreSQL `42P01` mới trở về baseline. Sai quyền/cột/lỗi DB khác trả 503, không nuốt thành dữ liệu rỗng.
3. Scope có schema typed: năm nguyên nghiêm ngặt, danh sách nhãn có giới hạn; dữ liệu sai bị chặn khi tạo/sửa. Scope cũ sai hình dạng bị cách ly bằng reason, không làm sập chat.
4. Lọc scope trước phát hiện target xung đột; cùng cụm nhưng hai năm tách biệt không tự triệt tiêu nhau. Nếu cả hai cùng phù hợp vẫn skip xung đột.
5. Fact/hybrid kiểm scope phương thức/thực thể bằng nhãn nguyên cụm xuất hiện trong câu gốc khi không có planner; evidence dùng nhãn planner đã phân giải. Không thêm model call hoặc từ điển keyword theo câu test.

Glossary mới không có cột/đối số tenant/workspace, chỉ collection. Migration additive `20261015_glossary_terms` vẫn **chưa apply**. Sửa bài persistence để kiểm tra trạng thái tắt trước, bật có version rồi mới kỳ vọng cache version dương.

## Kiểm chứng

- Regression chính: **323 passed, 2 skipped** (`storage/pytest-singleapp-485-regression.xml`).
- Nhóm integration/RAG bổ sung: **94 passed, 1 failed**; lỗi là baseline `test_reconciliation_detects_discrepancies`, không gọi đây là PASS (`storage/pytest-singleapp-485-integration.xml`).
- Ruff scoped: **PASS**; `git diff --check` scoped: **PASS**.
- FE Biome scoped 22 file: **PASS**, có `--line-ending=lf` theo AGENTS (config formatter hiện dùng CRLF); production build gồm TypeScript: **PASS**; auth tests **46 passed**.
- Full backend cuối: **FAIL — 11 failed / 1666 passed / 17 skipped**, 200.42 giây, exit 1; exact IDs khớp 11 lỗi nền, không có ID lỗi mới (`storage/pytest-singleapp-485-final.xml`). Lần trước cập nhật contract: **42 failed / 1634 passed / 17 skipped**, gồm assertion cũ đòi phân vùng; không coi là PASS.
- Persistence glossary với `TEST_DATABASE_URL` riêng: **NOT RUN**, chưa có URL; không dùng DB app thay thế. Test ORM identity map dùng SQLite in-memory, không chứng minh lịch khóa PostgreSQL thực tế.
- Không chạy 20/82 câu hoặc benchmark/model thật; không tuyên bố chất lượng trả lời tăng từ unit test. Chưa kiểm chứng UI trực tiếp trên trình duyệt.

## Bàn giao vận hành

- Khi triển khai, cần cập nhật FE/BE/worker cùng phiên bản. Để tác vụ worker cũ hoàn tất trước khi thay worker vì namespace lease đã đổi; không trộn worker hai phiên bản.
- Không cần reset database hoặc di chuyển file/vector cũ. Cột legacy được giữ; muốn xóa vật lý phải có đợt migration/backup riêng.
- Ghi nhận phạm vi ngoại lệ single-application trong AGENTS. Không mở rộng ngoại lệ này sang repo khác.
- Các skill clean-code/backend/frontend/RAG giới hạn thay đổi và kiểm tra nguồn/quyền; admin-frontend-design hướng dẫn bỏ controls workspace mà giữ primitives/layout hiện có.

## Lệnh và lỗi nền chính xác

Cwd `backend`: `.venv/Scripts/python.exe -X utf8 -m pytest -q --tb=short -p no:cacheprovider --basetemp=storage/pytest-singleapp-485-final --junitxml=storage/pytest-singleapp-485-final.xml` → exit 1. Ruff scoped → exit 0. Cwd `frontend`: `npm run build`, `npm test`, Biome check scoped `--line-ending=lf` → exit 0. Không chạy thêm vòng full sau khi chốt; chỉ cập nhật tài liệu.

11 ID lỗi nền (đối chiếu tự động tập ID XML, bằng nhau tuyệt đối):

1. `tests/test_consulting_dispatcher.py::test_dispatch_admissions_with_export`
2. `tests/test_consulting_dispatcher.py::test_dispatch_regulations_with_export`
3. `tests/test_publishing_v2_cutover_and_gc.py::test_gc_api_endpoint`
4. `tests/test_publishing_v2_cutover_and_gc.py::test_canary_policy_get_and_update_api`
5. `tests/test_publishing_v2_decommissioning_and_system_gc.py::test_direct_upload_blocked_when_flag_disabled`
6. `tests/test_publishing_v2_decommissioning_and_system_gc.py::test_direct_upload_allowed_when_flag_enabled`
7. `tests/test_publishing_v2_decommissioning_and_system_gc.py::test_rest_api_system_wide_gc_and_decommissioning_audit`
8. `tests/test_publishing_v2_e2e_canary.py::test_api_routes_canary_and_rollback`
9. `tests/test_rag_data_truth_and_lifecycle.py::test_reconciliation_detects_discrepancies`
10. `tests/test_trust_boundary_and_hitl.py::test_auth_session_cookie_actor_claims`
11. `tests/test_universal_tools.py::test_dispatch_admissions_with_dynamic_facts`
