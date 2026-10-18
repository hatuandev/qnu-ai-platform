# Phiên 512 — Giữ cấu hình để seed sau reset và review prompt

## Yêu cầu và quyền thực hiện

Người dùng xác nhận: lưu cấu hình hiện tại để khôi phục sau reset, không reset
DB lúc này. Đọc prompt chatbot tuyển sinh thực trong DB để đánh giá; không được
suy prompt runtime chỉ từ template seed. Không sửa prompt hoặc đổi model/policy.

## Thay đổi

- Phát hiện seeder trợ lý ghi đè prompt/config/tên/mô tả dù docstring nói ngược.
  Regression thêm so sánh cả trạng thái object FAIL trước sửa, PASS sau sửa.
  Sửa tối thiểu: trợ lý đã tồn tại được giữ nguyên. Test cũ chỉ kiểm tra không
  thêm object nên bỏ sót việc sửa thuộc tính trực tiếp.
- Thêm `backups/configuration_seed.py` và CLI `scripts/configuration_seed.py`.
  Capture transaction read-only/repeatable-read; tệp mã hóa qua StorageDriver,
  SHA-256/readback/decryption verification, chỉ in summary không in prompt/key.
- Restore mặc định preview, yêu cầu hash/actor; apply riêng và chỉ nhận target
  cấu hình rỗng, schema revision/cột khớp. Allowlist 13 bảng, không arbitrary SQL
  tables. Khóa chung bootstrap + table locks, atomic transaction, không overwrite.
- Giữ cấu hình và archive quy tắc điểm; không phục hồi active publication hoặc
  rule-source IDs đã mất vào runtime. Glossary mặc định tắt sau restore để rà scope.
  Quy trình12 mô tả đầy đủ thứ tự migrate → restore → seed phần thiếu.

## Gói cấu hình đã tạo thực

Ban đầu PostgreSQL và Docker Desktop chưa chạy. Sau khi người dùng bật stack,
capture thành công và preview load thành công trên cấu hình hiện tại.

- StorageDriver: **S3StorageDriver**, không giả là tệp local.
- Object key:
  `snapshots/configuration-seed/20261017T044510Z_70b5fc00c165432da1ba7af060dd1371.enc`
- SHA-256: `b207db21d1a6593c4af9bb74a561dec48dfa6b8cedb4652e36a33a5e5e3d0c2c`.
- Alembic: `20261015_glossary_terms`.
- 5 assistants; 12 model provider configs (có system defaults); 1 provider key;
  5 collections; 5 workflow definitions + 5 drafts + 5 versions; 37 document types.
  Assistant versions, tool definitions và glossary tables đều 0; không tự tạo dữ liệu.
- Gói đã save/get/decrypt kiểm tra thành công. Preview trả target không rỗng,
  đúng mong đợi; **không chạy apply trên DB đang dùng**.
- Đối chiếu lại 5 prompt/config chatbot với gói đã lưu: unchanged=true; chỉ in
  boolean/count, không đưa prompt/key vào báo cáo. Gói vẫn giải mã được.
- Không DB reset, seed-all, nguồn/vector/reindex, migration, restart, deploy,
  benchmark/model call hoặc Git commit/push. Chỉ tạo một object snapshot mã hóa.

## Review prompt (đã đọc bản DB, không chép prompt riêng vào tài liệu)

Thực tế admissions dùng mode RAG, model qwen3.5-9b trên provider nội bộ;
fallback null, max output 5000, TopK20/20/30/5, max context36000. Không thay đổi.

Điểm phù hợp: giọng thân thiện, đi thẳng câu hỏi, tránh lặp lời chào, ghi rõ
năm/phương thức và giữ ngữ cảnh. Các điểm cần người dùng quyết định ở batch riêng:

1. Không cam kết chắc trúng tuyển từ khoảng chênh điểm trong prompt. Những quy tắc
   định lượng đó không phải dữ kiện nguồn hoặc công cụ tính đã được duyệt.
2. Không hứa file đã xuất khi tool chưa chạy thành công. `chat_with_rag` hiện không
   dispatch workflow/tool xuất file và trả artifacts rỗng.
3. Không ép gợi ý thêm trong thân câu trả lời khi UI dùng suggested_questions.
4. Tránh dùng ví dụ số/quy định/đặc điểm ngành trong prompt như evidence. Bổ sung
   chính sách tham khảo khác năm có nhãn riêng, không áp năm cũ cho năm mới.
5. System prompt không phải toàn bộ RAG: nhánh structured audit/prose dùng hợp
   đồng riêng, một số đáp án render từ claims. Chỉ sửa persona không giải quyết
   tự động context overflow, verifier hoặc JSON contract lỗi.

Không xác minh tính đúng của pháp luật/số liệu bằng web; đây là đánh giá chỉ dẫn
và ranh giới bằng chứng, không tư vấn pháp lý hay kết luận số liệu chính thức.

## Kiểm chứng

- Targeted đầu 22PASS/3FAIL: 3 API tests không kết nối được PostgreSQL lúc stack
  tắt, không phải sửa assertion để né. Thử thêm 26PASS/4ERROR vì quyền thư mục
  Temp chung; chuyển basetemp riêng trong workspace, không xóa Temp của người dùng.
- Final scoped **41 PASS**, exit0 (7,92 giây), XML local
  `backend/storage/config512-drill-focused.xml`. Ruff có phạm vi PASS.
- PostgreSQL drill thật: schema fixture tên UUID trong outer transaction,
  khôi phục prompt/config/DateTime, chặn overwrite, gây lỗi insert cuối để xác
  nhận các insert trước rollback. Cuối cùng rollback cả schema, không đụng bảng app.
- CLI capture và restore preview thật PASS, không gọi model hoặc vector.
- Full suite: **1942 PASS / 11 FAIL / 17 SKIP**, exit1, 229,76 giây;
  `backend/storage/config512-full.xml` và `.txt`. Exact IDs trùng baseline511;
  tổng suite vẫn FAIL, không tuyên bố toàn app ổn định. 11 lỗi:

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

- UTF-8 không BOM/LF, liên kết local và diff check phạm vi: PASS.

Lệnh (cwd backend):

```text
.venv/Scripts/python.exe -m scripts.configuration_seed capture --actor local-admin-cli
.venv/Scripts/python.exe -m scripts.configuration_seed restore --actor local-admin-cli --path snapshots/configuration-seed/20261017T044510Z_70b5fc00c165432da1ba7af060dd1371.enc --sha256 b207db21d1a6593c4af9bb74a561dec48dfa6b8cedb4652e36a33a5e5e3d0c2c
.venv/Scripts/python.exe -m pytest tests/test_configuration_seed.py tests/test_configuration_seed_db.py tests/test_assistants.py tests/test_clean_knowledge_seed.py tests/test_local_provider_seed.py -q --tb=short --basetemp=storage/config512-drill-temp --junitxml=storage/config512-drill-focused.xml
.venv/Scripts/python.exe -m pytest -q --tb=short --basetemp=storage/config512-full-temp --junitxml=storage/config512-full.xml
```

## Giới hạn

Gói này không thay full backup. Không khôi phục thử vào DB người dùng hoặc server
demo. CLI local dành cho người vận hành, không tự cấp quyền qua client/model.
Phải giữ khóa mã hóa hạ tầng bên ngoài DB/storage; gói mã hóa không tự chứa khóa
giải mã. Server web chưa được capture hay seed trong phiên này.
