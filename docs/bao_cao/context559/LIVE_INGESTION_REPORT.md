# Context559 — Kiểm thử thực tế DOCX phức tạp qua Automatic Ingestion

## Kết quả chính

Đã tạo đúng **một revision mới số 3**, `ks_rev_9c93b4b4e2be`, từ DOCX phức tạp đã có. Markdown và Structured JSON hợp lệ, giữ nguyên nội dung cấu trúc so với bản đối chứng native. **Chưa nạp được vector**: Quality Gate trả `NEEDS_ATTENTION` với 8 cảnh báo chặn. Không tự duyệt, hạ policy hoặc xuất bản để vượt qua.

Binding: `bnd_21c09bbc6ca0`; collection: `col_admissions`; job: `job_db44750a8c07`. Hai revision trước giữ nguyên.

## Phạm vi được phép và môi trường

Người dùng cho phép kiểm thử thật bằng đúng DOCX trước đó, tạo revision mới và nạp staging nếu đạt chất lượng; chưa xuất bản. Đây là thao tác được ủy quyền trên ứng dụng development local, không phải regression ghi vào DB dùng chung. Trước ghi đã xác minh DB 127.0.0.1:5432, MinIO 127.0.0.1:9000 và Qdrant 127.0.0.1:6333; API/Qdrant trả200 và Storage đọc đúng hash. Không migration, seed, đổi model/config, restart hoặc deploy.

DOCX 102.423 byte trong docs/tai_lieu/tuyen_sinh khớp bytes snapshot MinIO. SHA-256: `58b3f7806529e4e506a6e2569a83ac688b8468fba955d0fe6638444a02099274`. Chỉ actor development hiện có được resolver xác thực, qua quyền view/update/upload; không token hoặc auth override. Không coi đây là kiểm chứng human SSO.

Dùng queue_reparse dispatch=False chính thức, tạo reservation và chạy leased worker hiện tại inline. Không phải POST reparse qua browser/ARQ broker; đây là pipeline/job/service thật với DB và MinIO thật. Không dùng mock parser, storage, vector adapter hoặc QC. Job hoàn tất xử lý không có nghĩa nội dung đã đạt Quality Gate.

## Bảng nghiệm thu

| ID | Kiểm tra | Kết quả thực tế |
|---|---|---|
| L01 | Source bytes, collection, quyền và cấu hình kết nối | PASS |
| L02 | Tạo một revision mới qua pipeline hiện tại | PASS; revision3, worker completed |
| L03 | QNU Markdown Standard v1.0 | PASS; 233block, 0error/0warning của validator chuẩn |
| L04 | MD/JSON pair, projection binding, source/resources hash | PASS qua Storage và API download200 |
| L05 | Core body/type/parent/order với native oracle và revision trước | PASS; khớp từng block, không chỉ đếm |
| L06 | Mọi bảng/header/hàng/raw/state | PASS; khớp bản native oracle, 10bảng |
| L07 | Footnote và mã định danh | PASS; 3footnote/locator, 0012/00027/AM-0007/AM-0070 giữ chuỗi |
| L08 | Readiness nội dung | **NEEDS_ATTENTION**; 8blocker, không AUTO_READY |
| L09 | Nạp vector thực tế qua API | **BLOCKED**; HTTP404 SOURCE_NOT_FOUND trước tạo job/index |
| L10 | Không publication hoặc thay revision cũ | PASS; old rows/pairs, bindings, collections, generation nguyên |
| L11 | Qdrant revision mới | PASS kiểm tra bảo vệ; 0point, không phải embedding PASS |

Validator chuẩn ở L03 kiểm tra định dạng/nhất quán, không xác nhận nội dung hình hoặc vai trò hàng gộp. Core/native oracle khớp không tự giải quyết các vấn đề ngữ nghĩa hoặc định vị nguồn.

## Tám cảnh báo đang chặn

| Mã | Vị trí | Ý nghĩa và giới hạn |
|---|---|---|
| page_unresolved | l002, danh sách dưới s006 | Một số mục chưa định vị trang chắc chắn, giữ locator và page unknown |
| spanning_row_needs_review | r014, r030, r046, r047 của t002 | Bốn hàng gộp chưa phân biệt chắc dữ liệu, nhãn nhóm hoặc chú thích |
| table_header_unresolved | t004 | Header engine đề xuất chưa có bằng chứng vai trò từ DOCX; mọi hàng vẫn được giữ |
| spanning_row_needs_review | r072 của t004 | Một hàng gộp chưa rõ vai trò |
| figure_content_unverified | fg001 | Giữ bytes ảnh, chưa phiên âm/kiểm chứng phần chữ trong hình |

Tổng:1list +5hàng gộp +1header +1hình =8. `spanning_row` ở đây là hàng gộp chưa rõ vai trò, không đồng nghĩa dòng qua trang. Không được kết luận tám cảnh báo là tám chỗ mất dữ liệu. Chưa sửa mã/policy hoặc tự đóng bất kỳ cảnh báo nào.

## Các dữ kiện có giới hạn

| Ô | Raw | Trạng thái |
|---|---|---|
| qnu:t005:row:1/c02 | (trống) | blank / source_blank |
| qnu:t005:row:4/c02 | – | ambiguous / literal_uninterpreted |
| qnu:t005:row:5/c02 | / | ambiguous / literal_uninterpreted |
| qnu:t009:row:6/c03 | / | ambiguous / literal_uninterpreted |

Bốn ô giữ nguyên, không thành0 và không có fact chắc chắn tương ứng. Ba ký hiệu chưa diễn giải và một ô trống là limitations, không nằm trong tám blocker. Không khẳng định tất cả ký hiệu đều đã được chứng minh là nguồn không định nghĩa. Diễn giải đã đề xuất ở revision cũ không tự trở thành effective trên bản mới.

Footnote3 chưa xác định trang preview nhưng có locator Word và neo được xác minh; được giữ thành warning thay vì blocker theo policy hiện có.

## Thử nạp vector và publication

Đã POST thật đúng một lần tới `/platform/v1alpha1/knowledge/collections/col_admissions/vector-load` với đúng revision mới và generation BGE-M3 `vg_a6e3190d11af`, provider `prov_rtx5090_vllm`. API trả404/SOURCE_NOT_FOUND với thông báo nguồn không thuộc kho hoặc không hoạt động. Trong ca này nguồn thực sự tồn tại và đúng collection, nhưng binding vẫn pending vì revision chưa qua Quality Gate. Đây là lỗi diễn đạt của thông báo API; không phải file bị mất. Chưa sửa UI/API trong nhiệm vụ kiểm thử này.

Không có vector job/index mới được ghi. Model embedding chưa được gọi, không có embeddings để nghiệm thu. Không thể gọi kết quả này là E2E upload→vector PASS. Qdrant count exact theo binding/source_revision_id xác nhận0point cho revision mới. Không gọi activate/publish hoặc chuyển active_index/collection epoch.

| Dữ liệu | Trước | Sau |
|---|---|---|
| knowledge_source_revisions | 13 | 14 |
| knowledge_index_revisions | 26 | 26 |
| knowledge_chunks | 56 | 56 |
| knowledge_facts | 0 | 0 |
| llm_usage_logs | 1774 | 1774 |

Toàn bộ cột của hai revision cũ khớp seals trước phiên; MD/JSON cũ vẫn đọc được. Mọi binding/collection và generation khớp trước phiên. Active_source và active_index của nguồn vẫn null. LLM usage log không tăng; không tạo hoặc duyệt semantic proposal. Pipeline báo engine docling+native+paddleocr_vl: phần preview/OCR là luồng cấu hình thật, không tuyên bố hoàn toàn offline. PDF Inspector có warning process nonzero và giữ native evidence; không che warning này hoặc dùng nó làm bằng chứng nội dung hình đã đúng.

## Artifact và lệnh thực chạy

- [Markdown mới](../../../backend/storage/context559/canonical/standard.md)
- [Structured JSON mới](../../../backend/storage/context559/canonical/structured.json)
- [Mở revision trong ứng dụng](http://localhost:3000/knowledge/col_admissions/sources/bnd_21c09bbc6ca0?revision=ks_rev_9c93b4b4e2be&tab=content)
- Evidence riêng: backend/storage/context559/{before,safety,created-receipt,validation,api-validation,final-integrity}.json; nguồn/corpus không được sao chép vào báo cáo Git.

Từ root repo, đã chạy:

```powershell
backend/.venv/Scripts/python.exe backend/storage/context559/preflight.py
backend/.venv/Scripts/python.exe backend/storage/context559/create_revision.py
backend/.venv/Scripts/python.exe backend/storage/context559/validate_revision.py
backend/.venv/Scripts/python.exe backend/storage/context559/final_integrity.py
```

Preflight/create/final validation/final integrity exit0. Helper validate_revision lần đầu exit1 do dùng async generator với all trong script đối chiếu; đã sửa riêng helper, chạy lại trên cùng revision và đạt, không tạo revision thứ hai. Log đầu/final giữ riêng. Thất bại helper không phải lỗi pipeline ứng dụng. Không chạy full regression/build/lint ứng dụng vì không sửa source. Không dùng kết quả test lịch sử như kết quả live hiện tại.

## Giữ dữ liệu và việc còn lại

Giữ revision3 cùng artifacts MinIO để người dùng xem kết quả. Đây là dữ liệu ứng dụng người dùng yêu cầu giữ, không tự xóa như DB test tạm; không tạo DB regression tạm. Không đụng các runtime cũ đang bị policy chặn cleanup. Không commit/push/deploy hoặc sửa mã ứng dụng.

Để tiếp tục nạp vector cần xử lý có bằng chứng các vị trí structural/visual/page ở trên rồi tạo revision/kiểm tra lại theo lifecycle hợp lệ. Không dùng việc giữ nguyên raw hay đóng semantic proposal để thay thế kiểm chứng này. Chưa đưa tài liệu vào chatbot.
