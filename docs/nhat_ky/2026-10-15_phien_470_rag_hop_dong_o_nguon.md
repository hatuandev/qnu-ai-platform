# Phiên 470 — Tiếp giai đoạn 4 với hợp đồng ô nguồn

Chốt lúc 17:03 ngày 2026-10-15 (UTC+7). Người dùng yêu cầu tiếp tục sau khi phiên 469 xác nhận generation
vẫn sai dù truy hồi đã có hàng đầy đủ. Đã triển khai nhánh trả lời bằng tọa độ ô và
kiểm chứng trên đúng hai câu điểm sàn; chưa chạy 20/82 hoặc đo accuracy tổng thể.

## Ranh giới và quy chuẩn

Theo RAG/Backend/Clean Code/ModelOps Resilience: thay đổi cục bộ, tái dùng source-unit,
context graph, span binding và ModelOps structured_call. Không bật evidence policy ngầm,
không thay provider/model/max_tokens/thinking/quota/config đã lưu, không reset/migrate,
không reparse/index/publish/OCR, không sửa docs/tai_lieu/Git index hay commit/push/restart.

## Hợp đồng trả lời bảng

### 1. Catalog tọa độ thuộc snapshot

`source_rows` bổ sung nguyên source-unit của header vào metadata `row_headers`.
`row_answer_contract` dùng đúng matrix/header paths và định danh hàng từ bảng đã pin.
Mỗi ô có ID server, tên thực thể, đường dẫn cột, giá trị gốc và raw references hàng/header.
Không sửa raw giá trị, không nhận số hoặc câu trả lời model tự viết. Tách intro trước hàng
và notes sau hàng theo vị trí source-unit; không đoán metric từ tên tệp/năm ban hành.

Kiểm collection/tenant/workspace request với snapshot trước model; kiểm binding/index
trong catalog. Nguồn/hash/review/parity/manifest/graph đã được loader kiểm như phiên 468.
Thiếu header provenance hoặc matrix không phân giải được thì không tạo catalog giả;
đường cũ vẫn xử lý khi chưa có catalog. Nguồn/index sai phải trả AppException.

### 2. Ba nhiệm vụ model độc lập với số liệu công khai

1. `MetricScope`: chọn ID đoạn dẫn gốc định nghĩa loại số liệu người hỏi muốn tìm.
   Chỉ cung cấp introductions, chưa đưa giá trị ô; dùng nghĩa trong nguồn thay từ điển
   đồng nghĩa gõ tay. Thu hẹp các bảng về đoạn dẫn cùng loại metric đã chọn.
2. `RowSelection`: chọn ID ô/phạm vi/ghi chú từ bảng trong nhóm đã khoanh. ID ngoài
   nhóm metric, ngoài catalog hoặc mượn scope nguồn khác đều bị từ chối.
3. `RowAudit`: độc lập chọn bộ ô/phần ngữ cảnh cần có để trả đủ câu hỏi; không nhìn
   selection trước. Có dữ liệu gốc để kiểm scope, nhưng không được thay giá trị.
   Chỉ trả supported khi hai bộ tọa độ khớp, compatible/scope/complete đạt, không conflict
   và không có missing constraints. Không bỏ verdict false để lấy kết quả mong muốn.

Chuyển tiếp `assistant_scope` từ persona_scope đang cấu hình để câu không nêu tên trường
không bị hiểu thành hỏi tất cả trường. Persona chỉ là identity, không là bằng chứng số liệu.
Giữ nguyên câu hỏi gốc, primary/fallback/provider và lịch sử ModelOps. Mỗi structured_call
dùng hợp đồng hiện hữu, có tối đa một lần repair JSON; không retry semantic đến khi đạt.
Thông thường 3 generate, tối đa 6 nếu từng JSON cần repair, cộng failover hữu hạn có sẵn.

### 3. Giữ dấu và điều kiện theo cấu trúc

`close_empty_cells` giữ các ô rỗng/dấu nằm **giữa hai cột đã chọn** cùng họ header có
tiền tố chung ít nhất hai token, xét trên toàn đoạn cột liên tiếp. Không chèn giá trị
số còn thiếu, không mở rộng mọi ô ngoài khoảng hoặc biến dấu thành 0/không xét tuyển.
Ý nghĩa dấu chỉ xuất hiện từ chú giải gốc. Ca RED đã phát hiện việc chỉ lấy common prefix
của hai cột ngoài làm mất cột học bạ; đã sửa bằng prefix chung toàn đoạn.

`close_context` tái dùng numbered-branch và sentence-continuation helpers trong cùng
binding/index/hash. Dependency nhóm điều kiện chỉ dùng unit loại list; paragraph chú giải
độc lập không bị gắn vào điều luật hoàn chỉnh đứng ngay trước. Nối câu đứt qua trang cần
câu trước chưa kết thúc và phần sau mở đầu chữ thường, không nối nguồn khác.

Không dùng audit để xóa điều kiện đã được lượt đọc đầu chọn: audit có thể bỏ sót chú ý.
Giữ nguyên các nhánh và ngoại lệ, hiển thị rõ đây là ghi chú chung của bảng, từng mục chỉ
áp dụng cho nhóm/phương thức được chính mục đó nêu. Không tự áp điều kiện sư phạm/Luật/
Giáo dục thể chất cho mọi ngành. Cách này bảo thủ và còn dài, chưa là phần tóm tắt điều kiện.

### 4. Render không sinh lại số

Hệ thống dựng bảng từ entity/header/value gốc, giữ bốn cột riêng biệt. Citation mang
raw quote, source/index/binding, canonical hash, span_start/end và trang thật của từng
header/hàng/note. Không lọc lại bằng word-overlap để làm mất header/chú giải.
Output guardrail thay đổi nội dung nguồn thì từ chối, không coi phần bị sửa là trích nguyên văn.
Decision version `source-cells-v1`, có cells/references/digest để trace. Không giả làm
contract evidence-claims-v1 và không tự bật evidence policy sau reset.

Trong `RagService.ask`, khi có row anchors và classifier hiện hữu là fact-first, thử nhánh
này trước free synthesis. Rejection trả insufficient_context, không rơi xuống model tự viết
và không cache như success. Không có catalog thì giữ nhánh cũ; cache legacy tăng version.
Các câu deterministic temporal-table xử lý trước đó vẫn giữ đường riêng, không bị đổi âm thầm.

## Tệp thay đổi

- Mới `backend/app/modules/rag/row_answer_contract.py`: DTO/cell catalog/binding/closure/render.
- Mới `backend/app/modules/rag/row_answer.py`: metric scope/select/independent audit/orchestration.
- Sửa `backend/app/modules/rag/source_rows.py`: header source-units có tọa độ.
- Sửa `backend/app/modules/rag/service.py`: gọi nhánh mới, version cache.
- Mới `backend/tests/test_row_answer_contract.py`: scope/ID/year/column/note/provider/error controls.
- Sửa `backend/tests/test_rag_rows_stage3.py`: mock dependency answer_from_rows=None trong đúng
  ca chỉ kiểm lắp prompt cũ. Chức năng mới có integration rejection/PG loader controls riêng;
  không thêm fake fallback runtime hoặc thay assert để che model chưa đúng.
- Đồng bộ nhật ký/memory/snapshot/WORK_LOG/mục lục/quy trình 03. Diagnostic tái dùng script469,
  artifact đánh dấu phase4, không tạo bản sao script hoặc đưa đáp án chuẩn vào model.

## Kiểm thử và các vòng thử thật

- Baseline lỗi thực đã có 2 genuine chats phiên469. Test mới ban đầu chưa có module;
  lượt RED đó còn fixture tenant/workspace một ký tự không hợp DTO, **không coi là red bug**.
- Windows sandbox treo ngay lúc tạo socketpair của asyncio; faulthandler xác định
  `_fallback_socketpair`/accept trước thân test. Dừng riêng các tiến trình chẩn đoán/test
  của phiên, chạy ngoài sandbox; không khởi động lại BE/worker/server hoặc đổi config mạng.
- Focus các mốc: 28 pass; sau thêm branch/continuation1fail85pass (fixture short-caption
  kết thúc nhóm note theo đúng graph); final extended121pass/8,01s; boundary87pass/8,47s.
- RED có ý nghĩa ở invariant ô dấu: 1fail33pass; sau sửa prefix family17pass. Final boundary
  **35 passed/4,47s** gồm row contract18 + source rows10 + generation7. Nền scope lỗi,
  unknown ID, conflict, missing cell, provider outage đều fail closed, không thành fake answer.
- Ruff toàn Backend đạt. Full đầu **1401 pass/11 fail/16 skip/54 errors/168,16s**:
  errors là Access denied thư mục mặc định `C:/Users/AnhTuan/AppData/Local/Temp/pytest-of-AnhTuan`.
  Không sửa quyền/xóa thư mục đó. Một lượt cùng đường mặc định đã dừng; chạy gate cuối
  với **basetemp mới trong backend/storage**, kiểm đường nằm trong workspace và chưa tồn tại.
- **Full cuối 1.456 passed, 11 failed, 16 skipped, 0 errors/191,45s**,
  `storage/pytest470_final.xml`. So exact classname/name với `pytest469_verified.xml`:
  cùng 11 lỗi nền, **không lỗi mới**. Temp ACL errors đã hết khi dùng basetemp mới,
  không sửa mã runtime để che lỗi môi trường. Không tuyên bố toàn suite xanh.
  Không FE build do không thay Frontend. Dùng Python venv hiện hữu chạy Ruff/Pytest,
  không cài/cập nhật dependency hoặc sửa lockfile.

### Diễn biến model thật

Giữ các báo cáo trong `backend/storage/rag_stage4_470/` để không che lượt chưa đạt:
first_report, independent_report, grouped_report, metric_report, coordinate_report,
scoped_report, handoff_report, verified_report. Tổng 16 hội thoại test/8 lượt hai câu;
có usage/key-health/gap log bình thường, không claim toàn DB read-only.

Các vòng đầu còn bỏ dấu, chọn quá nhiều notes hoặc independent audit từ chối dù có hàng.
Không cưỡng ép supported. Khoanh metric từ intro giúp bỏ lẫn điểm chuẩn/chỉ tiêu/năm cũ.
Thử audit chỉ nhận header không nhận value làm model hiểu dữ liệu thiếu; đã bỏ cách đó.
Thiếu assistant_scope khiến model tự đòi thông tin mọi trường; đã chuyển tiếp identity thật.
Vài lượt trả JSON schema thay JSON instance, repair hiện hữu hoạt động; không coi schema là
verdict hợp lệ. Một warning ghi gap bị charmap ở tool không UTF8 được giữ trong log vòng giữa;
lượt cuối chạy `-X utf8`, không sửa encoding dữ liệu nguồn để vá console.

### Lượt cuối trên mã cuối

`verified_report.json`: cả hai dùng **vllm/qwen3.5-9b primary**, mỗi câu 3 generate,
không fallback. Manual đối chiếu raw canonical/PDF đã xác minh ở phiên466:

| Câu | Giá trị trả lời theo cột | Thời gian service | Nhận xét |
| --- | --- | --- | --- |
| Quản lý giáo dục 2026 | 15 / 18 / 600 / 15 | 18.299,94ms | Đủ4phương thức, 18 giữ đúng cột kết quả học tập, không lấy điểm chuẩn cũ |
| Sư phạm Toán học 2026 | 20 / – / – / 20 | 4.865,66ms | Đủ4cột kể cả dấu, có chú giải và điều kiện2/a/b đầy đủ nguyên văn |

Không thêm năm mới vào metadata của ô; phạm vi2026 có quote đoạn dẫn cùng nguồn.
Ghi chú còn dài và có mục không áp dụng cho ngành đang hỏi, nhưng giữ rõ đối tượng của
từng mục, không diễn giải thành điều kiện chung. Đây là kết quả hai ca, không accuracy/p95
hoặc cam kết mọi câu đều ổn định. Lượt handoff trước đó6,82/5,95s không thay mốc cuối.

Config/snapshot/target source+facts+chunks/collection metadata/inventory fingerprints
trước/sau mỗi vòng bằng nhau; snapshot c61c923b10b4f8f1aa58,21 nguồn. Không chạm Qdrant write.
Đối soát READ ONLY sau full cuối: **21/21 citation raw spans/hash/source ID khớp canonical**;
toàn bộ protected fingerprints vẫn bằng nhau. UTF-8/NFC và scoped diff-check đạt;
docs/tai_lieu không có diff. Không coi log tool console bị charmap là dữ liệu source bị lỗi font.

## Bàn giao và giới hạn

BE/worker cần nhận code mới trước test giao diện. Chưa restart/deploy/commit/push.
Nên kiểm 20 câu đa dạng trước 82, gồm năm cũ, phương thức chỉ định, câu không có dữ liệu,
metric khác cùng ngành và câu nhiều ý. Chưa tự chạy20/82 trong phiên này.

Nhánh mới chỉ hỗ trợ row anchors đủ source/header provenance và fact-first classifier.
Không thay toàn bộ pipeline narrative/historical-reference hoặc policy evidence. Generic metric
classification, conditions selection và independent audit vẫn phụ thuộc model, có thể false-refuse;
không cho phép lỗi đó biến thành bịa số. Phần số/render có kiểm chứng cấu trúc xác định;
phần rút gọn ghi chú/semantic completeness cho corpus rộng cần benchmark tiếp.
