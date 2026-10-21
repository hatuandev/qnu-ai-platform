# Context582 — Gỡ chặn PDF bằng chứng nguồn và regression mở rộng

## Kết quả thực tế

- PDF nguồn giữ nguyên SHA256 `082c412e145a9ef39ae50110ae16cc80c17d612e2f0e00f9d16ee78c7c1c3b02`, 18 trang.
- Revision cuối: `ks_rev_fef00606f91f`, revision 4 của `bnd_12190866d5ec`, parser `pdf-evidence-structure/v5`.
- Trạng thái `ready` / **READY_WITH_LIMITATIONS**, **0 mục chặn**. Revision 2 trước sửa có 70 mục chặn.
- Đối soát đủ 10 bảng logic, 12 phần bảng vật lý: **695/695 vị trí ô khớp** DOCX gốc sau bỏ khác biệt khoảng trắng. Bảng 1 giữ 16×12, header 3 tầng, 192 vị trí ô.
- Dòng dài của Bảng 2 bị cắt qua trang được giữ ở hai vùng nguồn và có dependency. Chỉ nối bản sao khi đối soát với DOCX; không ghi đè hoặc điền mã vào ô trống của fragment.
- Giữ 3 footnote, 1 khối mã có thụt dòng và 1 hình. Markdown chuẩn, JSON, bản đọc tải thật đều HTTP200; kiểm tra cặp/hash/projection và tái đối chiếu PDF nguồn đạt.
- Nạp vector thật qua service hiện có và ModelOps: **327 chunks / 415 facts**, index `idx_rev_bba8c17700d0`, generation `vg_a6e3190d11af`, parity 327/327.
- **Chỉ staging, chưa xuất bản.** Kiểm tra điều kiện trước xuất bản đạt; transaction kiểm tra có khóa và rollback, không đổi active index hoặc epoch. Benchmark64 **NOT RUN** trong lượt này, không lấy điểm DOCX làm điểm PDF.

[Mở revision PDF cuối](http://localhost:3000/knowledge/col_admissions/sources/bnd_12190866d5ec?revision=ks_rev_fef00606f91f&tab=content).

## Nguyên nhân và cách xử lý

| Nhóm trước sửa | Số mục | Xử lý và ranh giới bảo vệ |
| --- | ---: | --- |
| Heading suy từ typography | 35 | Xác minh glyph hiển thị và giữ chữ nguồn; cấp mục vẫn là cấu trúc trình bày, không phải quyết định ngữ nghĩa. |
| Vùng hình chưa chép | 14 | 12 nền dòng mã được nhận bằng font đơn cách và các dải nền liền kề; gộp OCR trùng vùng ảnh; hình thật vẫn chặn nếu chưa có xác nhận nội dung. |
| Native/OCR khác nhau | 8 | Ưu tiên chữ native có bằng chứng thao tác vẽ hiển thị, loại lớp text ẩn khỏi bằng chứng. Giữ OCR khác biệt trong JSON; vùng OCR không đối chiếu được vẫn chặn. |
| Dòng gộp chưa rõ vai trò | 4 | Kiểm tra lưới phủ kín, giữ literal và nguồn ô gộp; không suy đó là header, nhóm hay fact. |
| Bảng nối trang | 2 | Cần trang liền nhau, cùng schema header đã xác minh, trục cột khớp và không có tiêu đề bảng mới xen giữa. Giữ từng bảng vật lý. |
| Native header cần review | 2 | Bằng chứng header phải độc lập với proposal engine; nếu không có, giữ đủ dòng dưới hạn chế literal. |
| Header chưa rõ | 2 | Không nuốt Alpha/North; mọi ô của bảng chưa xác minh vai trò cột chỉ dùng như literal. |
| MISSING_COLUMN_HEADER | 2 | Không tạo fact hoặc lỗi header của fact từ trường vốn không được phép tạo fact. Không bỏ lỗi header của trường present. |
| Footnote cần review | 1 | Bảo toàn chữ nguồn, không gán phạm vi cho bảng chỉ vì gần hoặc giống chữ. Thêm nhận dạng footnote bằng marker và đường phân cách. |

Đối soát mở rộng còn phát hiện **7 tên trường mất vị trí dấu `_`** dù thư viện vẫn trả chuỗi ký tự. Chuyển đổi dựa trên baseline/tọa độ glyph trong ô, giữ `matrix` gốc, `glyph_matrix` dẫn xuất và glyph audit. Chỉ tự sửa thứ tự khi không thêm/bớt ký tự; khác ký tự hoặc chữ số phải tạo blocker `native_cell_glyph_conflict`.

Không dùng từ điển header, tên chương trình, mã hoặc câu benchmark trong thuật toán.

## Xác nhận hình và giới hạn nội dung

Hình 1 trong PDF đã được kiểm tra trực quan và đối chiếu bản chép người dùng từng xác nhận ở Context560. Ảnh export được lấy mẫu lại, **không có cùng byte/pixel hash với PNG DOCX**. Vì vậy không tự chuyển receipt DOCX bằng giả định hash tương đương: ghi receipt riêng cho ảnh PDF, hash nguồn PDF, binding và actor đã xác thực, tham chiếu xác nhận người dùng trước đó. Receipt chỉ xác nhận bản chép hình, không duyệt proposal khác hoặc cấp quyền xuất bản.

51 hạn chế được ghi theo trường: 44 trường ambiguous và 7 ô blank. Nhiều trường ambiguous là cùng một dòng gộp được biểu diễn qua các cột, bảng không header, hoặc fragment qua trang; **không phải 51 lỗi mất dữ liệu hay 51 ký hiệu thiếu định nghĩa**. Những trường này không tạo fact chắc chắn. Ký hiệu và ô trống giữ nguyên, không đổi thành 0; nội dung chú giải vẫn có nguồn riêng.

## Bảo vệ và phạm vi mã

- `pdf_evidence.py`: chữ hiển thị, định danh ảnh, đối chiếu glyph; giữ nguyên evidence gốc và các chuyển đổi dẫn xuất.
- `pdf_header_roles.py`: ngăn dòng gộp toàn chiều ngang phía dưới header bị ăn vào header.
- `pdf_reconciliation.py`: đối chiếu OCR, nền mã, footer, footnote và kiểm tra phủ lưới.
- `pdf_structure.py`, `pdf_tables.py`: giữ literal, bảng nối trang, dependency fragment, code, ảnh và các nguồn tương ứng; cache PDF đổi theo builder v5.
- `pdf_fidelity.py`, `automatic_ingestion.py`: đọc sidecar đúng hash, capture lại PDF gốc và so block/field/geometry trước indexing/publication; thiếu/sai evidence phải chặn.
- `source_figure_review.py`: hỗ trợ receipt ảnh PDF qua cơ chế quyền và audit hiện có.
- `source_ingestion_service.py`: áp bản chép nguồn đã xác nhận trong khóa xử lý PDF native.
- `source_artifact.py`: không phát sinh fact/header error từ trường non-present.
- Thêm `tests/test_pdf_content_fidelity.py`, **27 trường hợp mới**. Parser DOCX và core chuẩn/projection giữ nguyên hash; regression DOCX vẫn được chạy vì có helper dùng chung.

Quality Gate và policy `automatic-content-v1` giữ nguyên. Không sửa status DB để vượt gate; status ready và active source do luồng ingestion chính thức quyết định. Không tự duyệt proposal, chủ động chạy migration, đổi model/config, restart BE/worker/FE, commit, push hoặc deploy. BE vốn chạy chế độ reload theo cấu hình sẵn có; không gọi lifespan từ harness. Seal dữ liệu ngoài phạm vi và cấu hình được đối chiếu cả với cuối Context581, trước các sửa mã của lượt này.

## Kiểm chứng

Môi trường regression: DB test có prefix/nonce riêng trên PostgreSQL local; metadata schema chỉ tạo trong DB test. Storage test local riêng; DB ứng dụng chỉ preflight đọc. MinIO/Qdrant xác minh loopback; endpoint dịch vụ trong regression chuyển tới `127.0.0.1:1`, tắt auto-migrate/seed. Các lượt xử lý PDF và embedding thật chỉ ghi đúng nguồn/kho local đã được giao.

| Kiểm tra | Kết quả |
| --- | --- |
| Baseline focused trước sửa | 102 PASS, exit0 |
| Canary trước sửa | 10 FAIL / 1 PASS, exit1; 4 failure hành vi và 6 guard chưa được triển khai, không phải 10 lỗi mất dữ liệu độc lập |
| Focused cuối: parser/nguồn/ảnh/serving/studio/automatic ingestion/DOCX | 159 PASS, exit0 |
| Ruff 11 file thay đổi trong lượt này | PASS, exit0 |
| Source/pair/projection/tái capture PDF | PASS |
| Đối soát 10 bảng / 695 ô | PASS, 0 khác biệt nội dung sau bỏ khoảng trắng |
| 3 định dạng tải qua API thật | HTTP200 |
| Embedding/Qdrant staging/parity | PASS, 327/327 |
| Kiểm tra cổng trước xuất bản | PASS; rollback, chưa publish |
| Full Pytest cuối | **FAIL**, exit1: 2.985 PASS / 18 FAIL nền / 17 SKIP, 23 subtests PASS; 473,27 giây; 27 ca mới PASS, 0 test cũ đổi trạng thái, 18 lỗi giữ đúng ID và nguyên nhân |
| Benchmark64 / publication / frontend build | NOT RUN trong lượt sửa backend này |

Một lượt full sớm đã bị dừng khi kiểm tra độc lập bổ sung guard glyph; không coi lượt đó là PASS. Full cuối chạy trên DB test mới với hash mã đã chốt. Lần preview đầu dùng transaction read-only bị PostgreSQL từ chối `SELECT FOR UPDATE`; lần kiểm tra cuối giữ khóa đúng thiết kế, xác nhận không có ORM mutation rồi rollback. Đây không phải hạ guard.

Bằng chứng riêng ở `backend/storage/context582/`: `test-comparison.json` sau full, `glyph-final/fidelity-audit.json`, `glyph-final/live-validation.json`, `glyph-final/vector-verification.json`, `glyph-final/publication-preflight-final.json`. Không đưa corpus hoặc raw OCR vào Git.

## Dọn môi trường và giới hạn bàn giao

Cả hai DB test đã xóa và kiểm tra không còn sau xác minh nonce. Xóa Storage tạm bằng PowerShell trên đường dẫn đã xác minh không có link/file tracked bị hệ thống kiểm duyệt tự động từ chối: `blocked by policy`. Không thử công cụ khác, không tắt bảo vệ; giữ hai thư mục Storage tạm và báo cáo. Nguồn, revision, index staging và usage/audit thật là kết quả người dùng yêu cầu giữ lại.

Model Luna chính/Qwen dự phòng, Repository, dữ liệu ngoài kho được giao và các revision PDF trước lượt xử lý được đối chiếu seal trước/sau. Không kết luận chất lượng trả lời 64 câu hoặc production readiness từ kiểm tra parser này.

[Test IDs và nguyên nhân lỗi nền](VALIDATION_REPORT.md).
