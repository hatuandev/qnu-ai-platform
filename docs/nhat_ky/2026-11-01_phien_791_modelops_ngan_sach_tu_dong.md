# Phiên791 — Backend ModelOps tự động và prompt FE

Ngày 01/11/2026. Người dùng yêu cầu tìm hiểu kỹ llm_wiki, triển khai BE trước và cung cấp prompt để vibe FE riêng.

## Kết quả và phương pháp

Đối chiếu upstream và code QNU: llm_wiki dùng override/preset/default, ngân sách context bằng ký tự và output tùy nhánh; probe nhỏ không khám phá capacity thật. QNU học cách giảm nhập tay nhưng giữ quota, nguồn thông số và hash runtime.

- Thêm `capacity/automatic.py`, recipe `qnu.operational-budget/v1`. Giữ declaration unknown; chat dự phòng envelope32768/output4096, embedding/rerank2048 cho từng input/cặp. Partial chỉ bổ sung phần thiếu; context/output đã biết không bị trần global mới. OCR ảnh thiếu cận trên không được suy từ Base64.
- ProviderResponse/Summary thêm `operational_budgets` theo capability, trạng thái declared/provisional/blocked và nguồn từng trường. Sync lưu nguồn manual riêng với server fields. Không thêm migration/dependency/registry bên ngoài.
- Chat request/limits, embedding, rerank dùng cùng policy; fingerprint có version/provenance khi provisional. Giữ hash legacy cho runtime khai báo đầy đủ, stale/access/grants/credential/quota/usage, cận đầu vào và lỗi overflow tường minh. Readiness nhận provisional nhưng giữ inference_verified=false.
- Tạo model không có thông số tay tự dùng snapshot discovery mới nhất đúng identity và model nếu có; không HTTP ẩn hoặc dùng snapshot cũ sau thất bại/key thay đổi. Input tay vẫn ưu tiên; discovery_check_id tường minh vẫn strict. Không tự sync model cũ đang phục vụ.
- Viết prompt FE và tài liệu hợp đồng; không sửa code frontend. Không thực hiện auto-retry/đổi provider/học trần từ lỗi chung400/422.

## File và bằng chứng

BE sửa trong ModelOps capacity, connections, inference, public_api, embedding/runtime, rerank, providers/service, schemas và operations/readiness. Tests: `test_automatic_budget_791.py` ở unit/integration; cập nhật test641 từ unknown-block sang provisional, giữ stale-block.

- [Quy trình và nguồn upstream](../quy_trinh/V1_MODELOPS_NGAN_SACH_TU_DONG.md).
- [Prompt FE](../ke_hoach/PROMPT_FE_MODELOPS_TU_DONG_791.md).

## Kiểm chứng thực chạy

Từ backendV1 bằng `.venv/Scripts/python.exe` (Python3.12 theo lock):

| Kiểm tra | Kết quả |
|---|---|
| Regression mới lần đầu trước module | ERROR import vì module chưa có; không coi là tái hiện hành vi |
| Unit mới sau thêm module | 10PASS |
| Targeted automatic641/ragbudget767/projection746 | 63PASS,3.37s,exit0 |
| Targeted automatic+641 sau bổ sung nguồn từng trường | 33PASS,0.54s,exit0 |
| API/DB scoped đầu (791/641/733/workspace/diagnostics/compiler) | 62PASS4ERROR,162.72s; lỗi fixture791 import bị Ruff bỏ, đã sửa đăng ký fixture; không lỗi sản phẩm trong nhóm đã chạy |
| API791 lần kế | 10PASS1FAIL; test đọc config trong DTO không có field đó, sửa đọc CompilationRun đã lưu qua DB |
| API/DB cuối (791/641/733/OCR643) | **38PASS**,65.32s,exit0 |
| Full pytest cuối, không TEST_DATABASE_URL | **658PASS1FAIL74SKIP**,28.18s,exit1; API không cấu hình DB riêng được skip, không gọi là full integration PASS |
| Ruff trên file BE/test sửa | PASS,exit0 |
| Diff/encoding/link tài liệu | git diff --check PASS; 25 file UTF-8/no BOM/LF và link tài liệu mới PASS; đã đọc lại prompt tiếng Việt |

Full failure duy nhất: `tests/unit/test_source_purge_716.py::test_accept_rechecks_publication_after_preview_before_preparing_purge`, `invalid_identity`401 do fixture thiếu actor_id, cùng exact ID phiên790. Không sửa ngoài phạm vi. Full suite vẫn FAIL.

Logs trong tmp (ignored): `verification791-integration-first.log`, `verification791-integration-fixture.log`, `verification791-integration.log`, `verification791-full-pytest.log`, `verification791-full-pytest-final.log`. DB test tạo riêng `qnu_v1_test_budget791_*`, migrations đếnhead, cuối mỗi lượt đã drop DB sở hữu; không truncate DB phiên live. API mock dùng secret/test content tổng hợp, không upstream thật.

## Giới hạn và bàn giao

Không restart, cleanup/init E2E, reindex, publication, đổi key/quota/ModelOps DB hiện hành, gọi model thật hoặc gửi lại I25-04. Giữ phiên93faa11f0caf/cohort789 8PASS1UNCERTAIN. Không áp thông số Qwen163840/32768 chỉ từ tin nhắn vào DB; sync server theo luồng có chủ ý.

FE chưa triển khai; đã giao prompt theo API này. E2E model thật/53câu và giao diện mới NOT RUN. Provisional có thể bị server từ chối nếu model nhỏ hơn ngân sách ban đầu; không hứa mọi model không gặp lỗi token. OCR ảnh/dimension cần căn cứ riêng, không hạ guard cho thuận tiện. Không tự cài adapter giao thức mới hoặc sao chép default ký tự204800 của llm_wiki thành token.
