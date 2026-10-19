# Kiểm chứng Context555

**Trạng thái triển khai: `IMPLEMENTATION_VERIFIED — WAITING_FOR_REVIEW`.**

Đường stage thật **BLOCKED bởi cặp source hash không khớp**. Human approval và nghiệm thu E2E thật **NOT RUN**. Full suite vẫn **FAIL 18 lỗi nền**, không đổi thành PASS. Dọn Storage còn bị policy chặn.

## Môi trường an toàn

Audit cấu hình xác nhận DB ứng dụng local `qnu_ai_platform`, MinIO local:9000 và Qdrant local:6333. Chỉ đọc DB này bằng transaction READ ONLY để đối chiếu cấu hình/hash nguồn. Không chạy tests, migration hoặc stage vào DB dùng chung.

Runner tạo DB test mới có nonce và ownership comment: `qnu_test_context548_abdc51dce9be`, 49 bảng trong DB test. ModelOps cấu hình và credential đã mã hóa được sao chép chỉ đọc vào DB test để baseline nhất quán; không xuất secret. Tests dùng ENVIRONMENT=test, LocalStorage tạm riêng; MinIO/Qdrant/Redis chuyển về `127.0.0.1:1`; auto-migrate/auto-seed tắt. Không dùng Storage nguồn làm Storage kiểm thử.

Trước baseline đóng băng mã backend; đối chiếu hash/diff thực tế, giữ các thay đổi từ phiên trước. Không gọi lại model để phân tích/sửa tài liệu, không sửa nguồn, không ghi nguồn thật/apply/index/publish hoặc đổi cấu hình ModelOps.

## Lệnh và kết quả thực tế

Python dùng `backend/.venv/Scripts/python.exe` (3.12). Runner `backend/scripts/context_patch_validation.py` cấp env cô lập cho mọi lệnh pytest bên dưới; cwd pytest là `backend`. Lệnh/args/exit đầy đủ ở [commands.json](commands.json).

| Kiểm tra | Kết quả | Exit |
|---|---|---|
| `audit_context_patch.py --output backend/storage/context555-safety.json` | PASS: kết nối local đọc được, yêu cầu cô lập trước test | 0 |
| Runner setup + seed-modelops | PASS: DB/Storage test riêng, dữ liệu cấu hình nguồn chỉ đọc | 0, 0 |
| Baseline `pytest -q` từ frozen code | **18 FAIL / 2398 PASS / 17 SKIP / 23 subtests PASS**, 430,72 giây | **1** |
| Lượt red đầu dùng sai đường dẫn test theo cwd | **NOT RUN**, không coi là test đỏ tái hiện | 4 |
| Red tái hiện `tests/test_semantic_checkpoint_import.py` | **12 FAIL / 1 PASS**: thiếu loại workflow, typed reference và schema/service import | 1 |
| Focused-first: checkpoint import + scope assertions + lifecycle | **65 PASS** | 0 |
| Focused-final: 8 file semantic/selector/context/lifecycle/limitations/serving | **206 PASS / 1 FAIL** ở test HTTP mới đọc nhầm field response không công khai | 1 |
| Focused-confirmed: `tests/test_semantic_checkpoint_import.py` sau sửa test HTTP đọc DB thật | **18 PASS**, bao gồm kiểm hash offline/stale và thiếu quyết định | 0 |
| Full cuối `pytest -q` | **18 FAIL / 2416 PASS / 17 SKIP / 23 subtests PASS**, 429,21 giây | **1** |
| Supplementary `storage/context555-evidence/test_role_persistence.py` | **6 PASS**: 3 vai trò qua import/review/đóng phiên/reload/rebuild; 3 negative role-target/evidence | 0 |
| `verify_review.py` trên canonical đã seal | **91 checks PASS, 86 bindings, 278 chunks**; chỉ bản sao trong bộ nhớ | 0 |
| `node --test src/features/knowledge/components/semantic-review-preview.test.mjs` từ frontend | **21 PASS** | 0 |
| `npx biome check --line-ending=lf <6 frontend files>` | PASS | 0 |
| `python -m ruff check <8 backend/test/script files>` | PASS | 0 |
| `npm run build` từ frontend (`vite build && tsc --noEmit`) | PASS build và typecheck | 0 |

Test HTTP trung gian thất bại vì schema response chủ động không lộ `parse_provenance`; không sửa API để lộ nội bộ cho test. Test được sửa để đọc artifact từ một session DB test thật sau HTTP 200. Full cuối đã chạy bản test sửa này. Biome cấu hình repo chọn CRLF, khác yêu cầu LF của AGENTS; chỉ file đã sửa được chuẩn hóa UTF-8/LF, kiểm Biome bằng CLI override, không sửa config.

Supplementary probes nằm trong evidence local, chạy tường minh với cùng runner DB test; không cộng sáu probe đó vào số PASS của full suite. Có [JUnit riêng](typed-persistence.xml).

## Đối chiếu regression theo từng ID

- Có **18 ID mới**, cả 18 PASS.
- **0 ID bị bỏ**, 0 trạng thái ID cũ thay đổi, **0 ID FAIL/ERROR mới**.
- **18/18 lỗi nền có cùng ID và cùng message nguyên nhân đầu tiên** trước/sau. Các lỗi gồm fixture collection/facts thiếu, quyền 403, thiếu bảng alembic trong DB test, Redis/capacity bị cô lập, OCR/embedding dependency và một assertion schema cũ.
- SKIP vẫn 17; không skip hay sửa assertion cũ để làm xanh.

Xem [bảng 18 lỗi và nguyên nhân](REGRESSION_IDS.md), [JSON đối chiếu mọi test ID](regression-comparison.json), [baseline JUnit](baseline.xml) và [full cuối JUnit](after-final.xml). JUnit xuất đã bỏ raw traceback/corpus/log và chỉ giữ kết quả/cause đã che thông tin nhạy cảm.

## Phủ T01–T20

| Yêu cầu | Bằng chứng đã chạy / kết quả |
|---|---|
| T01–T03 | Workflow không nhận column targets, không đi vào row/field/fact context của A hoặc B; raw tables không đổi. Probe canonical giữ đủ quote l006/l014 và đúng r001–r006, giữ điều kiện và loại trừ. PASS. |
| T04–T06 | Typed direct/protective/conditional stage được, conditional thiếu điều kiện bị chặn. Role metadata không tự thành graph edges. Ba role giữ nguyên qua persistence/rebuild; sai target, span hoặc mượn body ngoài assessment bị từ chối. PASS. |
| T07–T09 | Heading expansion có body và budget; O03 chỉ lấy role evidence từ body. O04 khoản 3 chỉ direct A05, khoản 2 bảo vệ năm. O05 đúng 2 direct/6 protective/3 conditional, không A01. PASS. |
| T10 | Scope assertions/lifecycle giữ string codes, canonical raw tables không đổi; A12 c02/3 dòng và A04/A10 AM-0007 giữ nguyên. PASS. |
| T11 | 14 file gốc + 5 file checkpoint553 khớp checksum trước/sau. Hash proposal555 mới, envelope đúng; manifest mới khớp. PASS. |
| T12–T13 | API thiếu quyền 403, missing revision/source/collection/binding/unsupported contract và hash/span/structured/manifest sai bị từ chối trước ghi. Rebind khác offline document/revision chỉ với cặp nguồn/manifest đúng. PASS trong TEST; stage thật BLOCKED hash. |
| T14–T16 | Import chỉ pending, graph/facts/fields/effective pointer không đổi. Lặp cùng gói idempotent; replay sau áp dụng bị chặn. Hash offline cũ, thiếu một issue decision không apply. PASS. |
| T17–T18 | Actor TEST qua service/API thật; lưu DB + LocalStorage, đóng session, đọc lại, rebuild; workflow/roles/bindings giữ nguyên, không sinh điều kiện gia hạn trên số liệu. PASS TEST, không thay human approval thật. |
| T19 | Selector v1/v2, snapshot legacy, neutral serialization, serving/lifecycle cùng suite đều chạy. Không lỗi regression mới. PASS phạm vi này. |
| T20 | Full và focused đã đối chiếu exact IDs/cause; suite toàn bộ vẫn FAIL nền như công bố. |

## Checkpoint và staging trace

Original552 `80308912...fc3`, prior553 `33d9cdae...fc2`, revised555 `0ae13c8d...6840`. Full hash ở [REVIEW_READY](REVIEW_READY.md). Cả 8 issue gốc được giữ; có 10 scope mới, 12 assertions; không có quyết định thật nào đã được ghi.

Xem [mapping trước/sau](mapping-before-after.json), [canonical verification đã giảm dữ liệu](canonical-verification.json), [trace staging TEST và audit source chỉ đọc](trace-staging.json). Gói nguồn riêng giữ ngoài ZIP/public reports. Stage thật chưa thực hiện vì không có revision khớp cặp MD/JSON; không dùng fuzzy matching hoặc ghi DB thủ công.

## Dọn dữ liệu và giới hạn

DB test đã DROP sau kiểm prefix/nonce/ownership comment, dừng connection đúng DB test và SELECT xác minh không còn. DB ứng dụng dùng chung không bị đổi schema/migration hay dữ liệu nguồn.

Storage runtime mới `backend/storage/context548-runtime-abdc51dce9be`: preflight **2006 file / 28.186.927 byte**, không link/junction/reparse/hardlink, không Git tracked, đường dẫn thuộc đúng Storage dự án. **Kiểm duyệt tự động chặn lệnh xóa có guard** với `blocked by policy`; không có lý do chi tiết hơn. Thư mục vẫn còn; cleanup Storage **chưa đạt**. Không đổi policy hoặc thử cách xóa khác. Runtime cũ của phiên553 giữ nguyên.

Bước xuất bằng chứng từng ghi nhầm 15 bản vào `D:/DuAnPhanMem/docs/bao_cao/context555`. Thao tác chuyển/dọn chúng cũng bị `blocked by policy`; bản đúng đã được tạo lại tại thư mục báo cáo trong repo. Các bản thừa ở thư mục cha còn lại, được ghi trong [cleanup.json](cleanup.json). Không tính các bản đó là gói bàn giao chính.

Giữ checkpoint gốc/revised và evidence theo yêu cầu audit. Không tự xóa chúng. Việc dọn phần còn lại phải tuân chính sách máy đang áp dụng, không tắt bảo vệ.

Kiểm UI browser/hình ảnh thủ công **NOT RUN**; test React markup, API, auth và stale đạt không thay việc duyệt thật. Human decision, live apply/persistence và publication **NOT RUN**. Không E2E PASS, không commit/push/deploy/restart hoặc migration production.
