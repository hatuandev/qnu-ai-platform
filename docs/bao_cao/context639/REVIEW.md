# Context639 — Sửa ba lỗi kho tri thức backendV1

Ngày 2026-10-26. Phạm vi được người dùng giao: sửa F1–F3 đã tái hiện ở
[review638](../context638/REVIEW.md). Kết quả: **ba lỗi đã được sửa và kiểm chứng**.

## Thay đổi và bằng chứng

| Lỗi | Bản sửa | Kiểm chứng hành vi |
|---|---|---|
| F1/P1 — Writer lỗi cắt file đã commit | LocalBlobStore ghi file tạm cùng thư mục, kiểm tra đủ bytes, đóng rồi atomic replace; dọn temp khi kết thúc | Hai upload đã qua precheck: writer đầu commit, writer sau ghi dở rồi lỗi; download nguồn đầu vẫn200 và đúng toàn bộ bytes |
| F2/P2 — Cùng idempotency key đổi title vẫn replay | Fingerprint JSON v2 gồm title hiệu lực; chuẩn hóa giống giá trị lưu. Sổ cũ phải khớp hash cũ và title đã lưu; không viết lại lịch sử | Đổi title trả409; title tương đương sau trim/default filename replay200; sổ hash cũ vẫn replay đúng và từ chối title khác |
| F3/P2 — Downgrade giả thành công, upgrade sau bị chặn | Migration0005 từ chối downgrade tường minh trước khi đổi version | Alembic downgrade thật trả lỗi; version vẫn0005; upgrade head tiếp theo thành công; file gốc vẫn tải đúng bytes |

Endpoint thêm revision loại title khỏi OpenAPI và trả422 nếu client vẫn gửi trường
này; không âm thầm bỏ qua hoặc đổi title nguồn. Upload nguồn mới vẫn nhận title.

Trong lúc kiểm chứng F1, stress test tái hiện thêm hai vấn đề Windows ngay tại driver:
`resolve()` đôi lúc thêm tiền tố đường dẫn dài `\\?\`, làm kiểm tra chuỗi nhầm file
hợp lệ là vượt root; hai rename đồng thời có thể gặp WinError5. Driver chuẩn hóa
tiền tố chỉ để so quan hệ thư mục, vẫn từ chối đường dẫn ngoài root. Khi replace bị
từ chối, chỉ trả thành công nếu đọc lại file đích khớp toàn bộ payload; file khác
nội dung vẫn gây lỗi. Có unit test deterministic cho cả nhánh khớp và không khớp,
traversal sang thư mục có cùng tiền tố, khác hoa/thường và extended path Windows.

## Kiểm thử đã chạy

Tất cả lượt pytest dưới đây dùng Python3.12/venv đã khóa của v1, PostgreSQL loopback
riêng, file tổng hợp và harness `scripts/run_isolated_tests.py`. Harness chỉ nhận
credential hạ tầng trong bộ nhớ, không sao chép dữ liệu ứng dụng và chặn mạng ngoài.

| Lượt | Kết quả | Cơ sở dữ liệu tạm |
|---|---|---|
| Ba regression trước sửa | **3FAIL**, 4,93s, exit1; đúng F1–F3 | `qnu_v1_test_645ffabff86447a7` |
| Focused cuối: regression639 + local driver + concurrency cũ | **24PASS/0FAIL/0SKIP**, 13,90s, exit0 | `qnu_v1_test_3c10adfa5f9543c9` |
| Full v1 cuối | **121PASS/0FAIL/0SKIP**, 40,58s, exit0 | `qnu_v1_test_61c63efd4b9d47e9` |

Các lượt focused trung gian có FAIL do đường dẫn dài/rename đồng thời nêu trên;
đã giữ log và sửa nguyên nhân trước gate cuối. Không nới assertion hoặc bỏ test để
đạt PASS. Tổng cộng thêm17 ca:8 tích hợp và9 unit cho local driver.

Lệnh, cwd `backendV1` (DATABASE_URL hạ tầng truyền trong bộ nhớ bởi wrapper):

```powershell
.venv\Scripts\python.exe -X utf8 scripts/run_isolated_tests.py tests/integration/test_knowledge_regressions_639.py tests/unit/test_local_blob_store.py tests/integration/test_knowledge_concurrency.py -q --tb=short
.venv\Scripts\python.exe -X utf8 scripts/run_isolated_tests.py tests -q --tb=short
.venv\Scripts\ruff.exe check .
.venv\Scripts\ruff.exe format --check qnu/adapters/storage/local.py qnu/domains/knowledge/sources/service.py qnu/domains/knowledge/sources/router.py alembic/versions/0005_knowledge_collections.py tests/unit/test_local_blob_store.py tests/integration/test_knowledge_regressions_639.py tests/integration/test_knowledge_concurrency.py
.venv\Scripts\python.exe -X utf8 scripts/export_openapi.py
```

Ruff toàn v1 PASS/exit0; format7file PASS/exit0. OpenAPI export PASS/exit0,31path;
đối chiếu multipart upload có file/title, append revision chỉ có file. Full suite
bao gồm migration/ORM, workspace/auth, ModelOps và các ca API kho tri thức sẵn có.
Hai cảnh báo deprecation của Starlette/httpx/anyio còn tồn tại, không có test skip.

## Phạm vi và bảo toàn

- Hash616file đầu phiên: chỉ4file app/migration v1 thay đổi (`local.py`, source
  service/router, migration0005);475file legacy `backend/app` giữ hash.
- 10 DB test thuộc phiên đã được harness dọn; đối soát catalog chỉ đọc cho thấy 0 DB
  còn lại, toàn bộ receipt giữ sentinel/version legacy. Không đụng DBtest ngoài
  ownership. DB chính chưa có bảng version v1; không chạy migration/restart/deploy.
- Test mới nằm trong suite chính. Artifact/log/XML/receipt và source seal ở
  `backendV1/storage/context639` và các thư mục DB dưới `storage/context636`, Git ignore.
- Không thay schema bảng, không backfill sổ idempotency, không xóa file nghiệp vụ.
  S3 adapter không đổi; chưa live S3/OCR/inference trong phiên này. Atomic replace
  bảo vệ ghi dở, không phải cam kết chịu mất điện. Luồng vẫn dừng ở `stored`.

[Hợp đồng cập nhật](../../../backendV1/docs/knowledge-collections.md).
[Quy trình v1](../../quy_trinh/20_kho_tri_thuc_backendv1.md).
