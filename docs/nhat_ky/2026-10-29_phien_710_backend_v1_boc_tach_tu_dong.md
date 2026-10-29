# Context710 — Backend V1 bóc tách tự động PDF/DOCX sau upload

Ngày 2026-10-29. Người dùng giao làm backend V1 trước: upload tự tạo MD/JSON,
ưu tiên đọc chữ trực tiếp, xử lý ảnh/scan phù hợp, giữ nguồn và chuẩn bị cho FE
đơn giản hơn. Không đổi FE trong phiên này. Lựa chọn giữ model/default/grants/
quota hiện tại của phòng ban vẫn có hiệu lực; không chạy OCR thật/corpus phòng ban.

## Phạm vi và phương pháp

- `knowledge/sources/{service,router,schemas}.py`: upload/revision PDF/DOCX mặc
  định `auto_extract=true`; source/revision/upload ledger và run cùng transaction,
  dispatch sau commit. Queue lỗi giữ ý định để reconcile/dispatch lại. Source
  vẫn `stored`; `processing` độc lập được trả cả khi upload, đọc nguồn và list
  theo batch của revision hiện tại. Opt-out chỉ lưu giữ API tương thích.
- `ocr/native*.py`: đo text/cell/bbox từ PDF và PDF fixed-layout của DOCX; giữ
  header/spans DOCX khi khớp duy nhất với bảng nguồn HTML. Chữ không dùng được
  hoặc ảnh cần OCR; vùng chữ/ảnh tách nhau giữ native và bổ sung OCR trong ảnh.
  Lớp chữ chồng ảnh dùng một layout OCR, tránh nối trùng lớp chữ scan.
- `ocr/automatic.py`, `execution.py`, `service.py`, `schemas.py`: tái dùng run/
  queue/lease/fencing hiện có. Native thuần không gọi model hoặc reserve token;
  OCR vẫn qua ModelOps/quota/policy. Ghim version native/PyMuPDF; lỗi vẫn lỗi,
  không giả provider/raw/progress. Unknown usage không bị số 0 native che lấp.
- `ocr/artifacts/{canonical,docx_html}.py`, `layout.py`: evidence phân biệt native
  và raw OCR; giữ ảnh, thứ tự và nguồn. Sửa truyền ô gốc cho vMerge trên hai hàng;
  merge thiếu gốc báo lỗi. Ảnh DOCX không hỗ trợ không được báo hoàn tất đầy đủ.
- `ocr/exports.py`, `router.py`: tải ảnh có kiểm hash/quyền và ZIP portable gồm
  MD/JSON/ảnh. ZIP giới hạn64MB, tạo ngoài event loop, không nhận path từ client.
- Migration `0007_native_extraction`: chỉ thêm hai loại artifact vào constraint,
  không tạo bảng mới hay sửa bằng chứng cũ. Migrate chỉ DB thử. Cập nhật các test
  head/count cho revision0007; hai assertion0005 đã lỗi từ708 được cập nhật vì
  task này thay migration head, không bỏ kiểm model/schema/sentinel/downgrade.
  `qnu/platform/schema.py` đồng bộ head0007 cho API/worker/recovery; test baseline
  thêm invariant code head bằng Alembic head để không lặp sai lệch khi có revision mới.

Không import nguyên module `backend/`, không mang ranh giới dữ liệu chung sang
V1. Mọi nguồn vẫn qua workspace resolver; worker kiểm lại sau native/OCR.
Không tự Compiler/approve/publish/index, không backfill hoặc đổi bản phục vụ.

## Kiểm chứng

Trong `backendV1`, Python3.12 từ `.venv`/uv lock hiện có; không cài gói mới.

| Kiểm tra | Kết quả đã chạy |
|---|---|
| Test native mới trước triển khai | ERROR import module chưa có, xác nhận chưa có nhánh native |
| Ba ca bổ sung trước sửa cuối | 2unitFAIL (ảnh bị bỏ qua, rowspan chỉ2), 1integrationFAIL (usage unknown thành0) đúng nguyên nhân |
| Native + DOCX renderer regression sau sửa | `python -m pytest tests/unit/test_native_extraction_710.py tests/unit/test_ocr_docx_html.py -q`:22PASS/exit0 |
| HTTP/worker native-first | `uv run --no-sync --env-file ../.env python scripts/run_isolated_tests.py tests/integration/test_auto_extraction_710.py -q`:14PASS/exit0, DB `qnu_v1_test_d04f35fb4ad442a3` đã dọn, sentinel giữ |
| Schema/worker unit sau đồng bộ head |6PASS/exit0 (`test_migration_baseline_661.py`, `test_rag_worker_schema_672.py`)|
| Bao phủ kiểm tra cuối |835/835ID PASS, 0FAIL/0SKIP/mất0/trùng0;28ca mới. Gồm210call PASS trước gián đoạn và625PASS qua5lệnh hoàn tất exit0; không phải một lệnh full suite liên tục |
| Ruff |26tệp Python PASS/exit0; log `ruff-final.log` |
| OpenAPI |131path, bundle/images/strategy/processing/results_ready đúng schema, không `$ref` thiếu |
| Link/UTF-8/LF/BOM/diff |PASS theo kiểm tra phạm vi cuối |

Ca mới gồm native không model/quota, Unicode, bảng/ô trống/0/dấu gạch/spans/header,
DOCX chèn ảnh đúng thứ tự, PDF cột, scan/lớp chữ ẩn, raw model giữ riêng,
queue outage/replay/rollback, bản mới giữ bản cũ, reuse/force, membership/source
guard, ảnh chéo quyền, ZIP và đầu vào Compiler đọc đúng revision.

Full lượt đầu đã chủ động dừng ở16% trước ba sửa cuối, không tính PASS/full gate;
harness dọn DB `qnu_v1_test_e888454e41be411a` và giữ sentinel. Lượt cuối dùng
`storage/artifacts/native-extraction-710/gate-manifest.json` bao phủ toàn bộ835ID,
không bỏ test. Mỗi nhóm có PostgreSQL/storage riêng, Redis test12–15 được kiểm
rỗng trước sử dụng; recovery chạy riêng với Proactor vì cần subprocess trên Windows.
Không dùng xdist hoặc thêm dependency. Sau cùng đối chiếu JUnit với manifest.

Lượt chia nhóm đầu ghi826PASS/5FAIL trong831ca chính: ba ca staged replacement
đang upload mặc định rồi yêu cầu OCR thủ công (run thứ hai bị409 đúng hợp đồng),
hai ca readiness/heartbeat phát hiện code head còn0006 trong khi DB là0007.
Fixture `staged_version` trong `test_lifecycle_runtime_659.py` đặt rõ
`auto_extract=false` vì đang dựng luồng OCR thủ công; không sửa assertion/thay
hành vi auto mặc định. Ba ca chạy lại3PASS/exit0; code head được sửa và toàn bộ
835ca đang chạy lại trên bản chốt. Hai nhóm cũ205/295PASS không được dùng để
tuyên bố full gate bản chốt đã đạt. Redis test13/14 còn job fixture đã được kiểm
đúng key/queue, dọn cụ thể3+2key; không FLUSHDB, không chạm Redis DB đang phục vụ.

Lượt cuối bị kết thúc ngoài dự kiến trước receipt của bốn nhóm chính; không
khẳng định bốn lệnh đã exit0. Log đã ghi210ca PASS trên mã cuối, ca tiếp theo
chưa hoàn tất được đưa vào danh sách chạy tiếp. Không có FAIL trong prefix này.
Recovery riêng4PASS/exit0, DB `qnu_v1_test_8bd43acea2a9477b` đã dọn, Redis test10
còn0key. Bốn DB thử bị gián đoạn được kiểm sentinel/legacy head, dọn đúng tên
trong artifact `interrupted-final-cleanup.json`, Redis riêng12–15 dọn đúng key.
Chỉ621ca chưa hoàn tất chạy lại trên DB mới; manifest nối210+621+4=835, không
lấy kết quả bản mã trước để lấp phần thiếu. Dynamic ID của4ca worker/schema đổi
theo `SCHEMA_HEAD`0007; đã collect lại để gọi đúng ID, không đổi assertion.

Kết quả tiếp nối:112PASS/125PASS/166PASS/218PASS, cả4lệnh exit0; recovery4PASS
exit0. Tổng625ca của lệnh hoàn tất +210ca prefix =835ID duy nhất. Đối chiếu bằng
`verify_gate.py` với JUnit từng nhóm, manifest và hash28file backend: không thiếu,
không trùng, hash không đổi. `verified-final-coverage.json` ghi rõ giới hạn không
có một lệnh full suite chạy liên tục. Không gộp5FAIL của lượt cũ thành PASS.
Tất cả DB thử đã dọn/sentinel giữ; Redis riêng10–15 đều0key sau dọn đúng2key
auto-review fixture còn lại ởDB14, receipt `final-cleanup.json`.

So với danh sách807ca lịch sử708, giữ đủ các hành vi cũ;4ID tham số của worker
đổi0006→0007 theo schema được hỗ trợ. Thêm28ca mới, không bỏ hoặc skip test cũ.

OpenAPI app xuất131path, `$ref` không lỗi; bản xuất mới ở artifact
`openapi-710.json`. Snapshot tracked cũ giữ nguyên để tránh kéo toàn bộ thay đổi
API các phiên trước vào task. Router/DTO hiện hành là contract thực.

## Giới hạn và vận hành

DOCX giữ số trang/tọa độ theo PDF render; header/footer theo section vẫn báo
không hỗ trợ, cần PDF đầy đủ. Bảng không kẻ/đa cột phức tạp cần review. OCR ảnh
dùng cả trang rồi lọc vùng, chưa crop riêng và chưa diễn giải số liệu biểu đồ.
Không suy dữ kiện hoặc năm từ tên tệp. Model chưa được cấp thì phần cần OCR
báo lỗi, nguồn còn; không tự mở quyền/hạn mức để vượt cấu hình.

Chưa live inference, benchmark chất lượng, đổi bố cục FE, áp migration vào DB
đang phục vụ, restart API/worker, publish/reindex hoặc commit/push. Cần deploy
schema0007 và chạy API/worker mới trước khi người dùng sử dụng luồng mới.
Thay đổi FE từ709 và các sửa workspace/navigation/ModelOps xuất hiện đồng thời
được giữ nguyên; không đưa các thay đổi đó vào phạm vi hoặc kết quả kiểm BE.

[Quy trình43](../quy_trinh/43_boc_tach_tu_dong_backend_v1.md).
