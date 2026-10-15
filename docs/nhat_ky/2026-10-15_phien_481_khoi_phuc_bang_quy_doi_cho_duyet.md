# Phiên 481 — Khôi phục bảng quy đổi và tạo revision chờ duyệt

## Mục tiêu và quyền thao tác

User đồng ý khôi phục bảng của riêng PDF quy đổi 2026, đối chiếu từng cột rồi tạo bản mới để user duyệt/xuất bản. Không tự duyệt, nạp vector hoặc xuất bản. Không thay file PDF gốc, ModelOps, rule quy đổi, DB schema, restart/deploy hoặc Git. Áp dụng skills ingestion, backend, clean-code và PDF (đọc/đối chiếu hình ảnh, không chỉnh PDF).

## Nguyên nhân và cách sửa

Header cha là mã chữ-số có ô gộp; bộ nhận diện header cũ xem mã như dữ liệu, để lại tên cột trống. `_normalize_spacer_columns` tiếp tục coi chúng là khoảng cách trình bày và cắt mất các cột con có số. Hai regression RED tái hiện: 7 cột thành 3, cột trống tiêu đề nhưng có số bị xóa.

- `parsers/native_headers.py` mới: nhận diện prefix header hữu hạn trước hàng khóa số/phần trăm; dựa trên bbox ô gộp bao tâm cột dữ liệu để xây đường dẫn cha/con. Không forward-fill nhãn bằng phỏng đoán, không từ điển tên tổ hợp/model.
- `parsers/pdf_parser.py`: sử dụng matrix header hình học trước normalize/reconstruct. Các layout không đủ chứng cứ giữ nguyên cho đường review cũ, không đoán.
- `normalization/table_reconstructor.py`: không cắt cột có dữ liệu chỉ vì thiếu tên. Giữ nhánh compact/remap hình thái đã có và bảng task cũ; một regression compact4cột lộ trong lượt đầu đã sửa bằng điều kiện cấu trúc số ô, không thay assertion để làm xanh.
- `services/source_extraction.py`: tăng version `layout-v11-native-headers` để lần parse tương lai không tái dùng artifact thiếu cột của parser cũ. Không kích hoạt parse hàng loạt hoặc thay source đã xuất bản.
- `services/native_table_review.py` mới: đối chiếu tất cả bảng/ô cũ với PDF native, bổ sung cột thiếu; giữ nguyên ký tự ngoài đúng đoạn bảng. Tạo bản bất biến mới `review_required` trong transaction do caller quản lý, khóa source và chặn sai hash/binding/base/tiến trình đang chạy/nháp trùng. Không đổi con trỏ binding hay index.
- `scripts/prepare_native_table_review.py` mới: dry-run mặc định; apply tường minh. Kiểm tra fingerprint source đang dùng, binding pointers/status, epoch/config, số chunks/facts trước-sau; lệch thì không commit. Không OCR/LLM/API ngoài hoặc storage write.
- `tests/test_native_table_review.py` mới: 13 ca về header/ô số, thay bảng không đổi prose, xung đột giá trị/page/hàng/header, tạo draft cô lập và lỗi hash/base/DB/duplicate.

## Kết quả dữ liệu thật

PDF hash `96207cca90ecd30df23d9ffcf74fb982a6277e4d89b08270e3465a4a2bd5dc8e`.

| Hạng mục | Kết quả |
| --- | --- |
| Nguồn | `col_admissions` / `bnd_e52fd3712ac3` |
| Bản đang dùng, giữ nguyên | `ks_rev_5d0af627f4e7`, revision 2 |
| Index đang dùng, giữ nguyên | `idx_rev_8c79cf8eb463` |
| Bản mới đã lưu | `ks_rev_259de8772948`, revision 3, `review_required` |
| Bảng trang 3 | Từ 9 thành 23 cột, giữ đủ 22 hàng; bổ sung 14 cột HB/THPT |
| Bảng trang 4–5 | 45 + 5 = 50 dòng, khớp toàn bộ; không thay nội dung bảng này |
| Đối chiếu ô số | 556 ô so trực tiếp với words nằm trong bbox ô, không chỉ tin table.extract |
| Draft facts | 534, đều kèm native cell bbox + hash file; chưa ghi thành active knowledge_facts |
| Hash canonical mới | `ddceee8b1442a36cb3359e2ce9f54850646384a3086be87c25e25a2c8bc9fd2f` |
| Protected fingerprint | `1b5e703ecf3a0cb2aff41d888b48291ad07b76f6e29b1613ebb5792c6b0c7420`, trước = sau = đọc lại sau commit |

Chỉ đoạn bảng trang 3 đổi, offsets bản cũ 3107–4766; không normalize lại toàn bộ văn bản. Page manifest trang sửa đánh dấu layout/text alignment stale, không giả bbox cũ đã căn theo text mới. Người tạo được ghi là công cụ hỗ trợ, không giả danh người duyệt; review.status vẫn required.

[Mở revision 3 để duyệt](http://localhost:3000/knowledge/col_admissions/sources/bnd_e52fd3712ac3?revision=ks_rev_259de8772948&tab=content).

Artifacts local ignored: `backend/storage/rag_enumeration_481/dry_a/` và `apply_a/` gồm candidate.md, native_cells.json, report.json. Không commit raw tài liệu. Apply đã commit đúng một source revision mới; không chạy lại `--apply` để tạo bản trùng.

## Kiểm chứng

- RED: 2 ca fail đúng mất cột trước sửa.
- Focus: **47 passed** (13 ca mới + table reconstruction/stitching cũ); gate bổ sung source-ingestion/cache version cuối phiên **59 passed**, 23,77 giây.
- PDF thật qua runtime native parser: bảng 23 cột/22 hàng; bảng mapping nối 50 hàng. Rust inspector process thoát lỗi nên giữ bằng chứng native, không gọi OCR/LLM bù; ghi nhận cảnh báo, không xem inspector là pass.
- Dry-run đúng mục tiêu, chỉ 1 đoạn sửa. Apply + đọc lại DB độc lập xác nhận trạng thái/chỉ mục/fingerprint như trên.
- Ruff toàn Backend đạt, còn cảnh báo ACL ở thư mục tạm cũ (không sửa ACL/xóa).
- Full pytest: **1569 passed / 11 failed / 16 skipped / 0 errors**, 216,26 giây. XML `pytest481_final.xml` so với `pytest480_final.xml`: exact11failureIDs giống nhau, không lỗi mới; không tuyên bố full suite xanh. Version bump cuối phiên đã được kiểm tra thêm bằng suite source ingestion 59pass, không chạy lặp full chỉ cho thay đổi constant.

Logs ignored: `backend/storage/pytest481_final.xml`, `pytest481_final.log`, `pytest481_focus.log`, `ruff481_final.log`. 11 lỗi nền thuộc consulting dispatch (2), publishing cutover/GC (2), decommissioning/system GC (3), canary/rollback (1), RAG reconciliation (1), auth session claims (1), universal tools (1), exact IDs trong XML/log.

## Còn lại

User mở bản số 3 để đối chiếu và duyệt, rồi nạp vector/xuất bản theo quy trình app. Chưa kích hoạt rule tính điểm: cần xác nhận rounding và cấu hình bằng đúng facts/index của bản mới sau publication. Không suy rằng duyệt bảng là đã duyệt công thức/cấu hình tool. Chưa test 20/82 hoặc model thật. Runtime parser ở process không reload cần nhận code mới khi user triển khai; draft đã lưu không phụ thuộc việc restart để xem.
