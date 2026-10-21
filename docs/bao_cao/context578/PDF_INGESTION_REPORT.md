# Context578 — Dọn kho tuyển sinh và nạp PDF phức tạp

Đã dọn Knowledge của kho `col_admissions` và tiếp nhận đúng PDF người dùng vừa export. Bóc tách đã hoàn tất; kết quả **NEEDS_ATTENTION / review_required**, chưa đủ chất lượng nạp vector và chưa xuất bản. Không sửa mã ứng dụng hoặc hạ Quality Gate.

## Phạm vi và môi trường

Người dùng yêu cầu dọn kho rồi tải PDF trong thư mục tuyển sinh. Dùng phạm vi toàn `col_admissions` đã được xác nhận trước, giữ Kho Tài liệu trung tâm, file local và các kho khác. Preflight xác minh development, PostgreSQL/MinIO/Qdrant loopback, kiểm quyền hiện có ở server; không cấu hình lại auth/provider/model. Đây là thao tác live local được giao, không phải regression ghi vào production.

PDF có 18 trang, 648851 bytes; SHA256 `082c412e145a9ef39ae50110ae16cc80c17d612e2f0e00f9d16ee78c7c1c3b02`. Đã xem bản render trang 3 và trang 6. PDF có lớp văn bản; pipeline thực tế dùng `native+paddleocr_vl` với phiên bản `layout-v22-document-structure`. Không suy rằng PDF có lớp văn bản thì bảng đã đúng.

## Dọn kho và lưu nguồn

- Một nguồn DOCX có 5 revision, 524 chunks, 783 facts được dọn qua API pause/purge chính thức; job `job_b367f66b6d61` completed. Vector cũ 524 về 0.
- 22 tombstone có từ trước và tombstone nguồn DOCX vừa dọn tiếp tục giữ lịch sử xuất bản; không xóa event kiểm toán. Snapshot thuộc Knowledge được dọn qua StorageDriver; Repository và file gốc không bị xóa. Không dọn file mồ côi ngoài phạm vi.
- So hash các row Repository có từ trước, cấu hình model/assistant và các collection/binding/revision/index ngoài phạm vi: không thay đổi, cả sau upload. Repository chỉ thêm tài liệu PDF được giao.
- Upload thật `POST /documents/intake`: HTTP202. Import thật `POST /knowledge/collections/col_admissions/imports`: HTTP201; worker hiện có hoàn thành bóc tách, không chạy worker giả hoặc restart dịch vụ.
- Document `rep_doc_acef7b5efd8b`; batch `imp_batch_a898ebd16512`; binding `bnd_12190866d5ec`; revision `ks_rev_1071c152fab0`.

## Kết quả đối soát

| Kiểm tra | Kết quả |
| --- | --- |
| Bytes snapshot khớp file local và source SHA256 | PASS |
| Cặp Markdown/JSON khớp hash, binding và revision | PASS |
| Cú pháp QNU RAG Markdown | PASS |
| Projection gắn đúng canonical | PASS |
| Số trang manifest | 18 |
| Chất lượng nội dung | NEEDS_ATTENTION — chưa đạt |
| Index/vector mới | 0; Quality Gate đã giữ chặn |
| Xuất bản | Chưa thực hiện |

Đúng cú pháp/hash không chứng minh bảng đã được tái dựng đúng. JSON có 626 khối: 35 section, 139 text, 48 list, 229 figure, 12 vùng bảng, 161 table_row, 2 note. Các vùng bảng gồm những phần nối trang, chưa được chứng nhận là 12 bảng logic độc lập. Có 2883 trường literal: 2038 present, 840 blank, 5 ambiguous; artifact facts hiện là 0. Không tự biến ô mơ hồ thành dữ kiện hoặc 0.

Ví dụ đã đối chiếu trực quan: **Bảng 1 trang 6 có 12 cột**, nhưng artifact `qnu:p0006_b0004` nhận **34 cột, 27 hàng** và chưa có header path. Đây là lỗi cấu trúc cần xử lý, không phải chỉ thiếu người bấm duyệt. Các vùng hình/chú thích, heading suy luận, bảng nối trang và khác biệt native/OCR cũng cần đối chiếu; chưa kết luận mọi cờ figure đều là một hình bị mất nội dung.

Có 1541 **mục chặn sinh ra**, không phải chừng ấy lỗi độc lập. Một nguyên nhân về header có thể tạo nhiều mục theo cột/ô:

| Loại mục chặn | Số lượng |
| --- | ---: |
| `MISSING_COLUMN_HEADER` | 1228 |
| `heading_inferred_typography` | 35 |
| `visual_content_untranscribed` | 229 |
| `native_header_needs_review` | 12 |
| `table_header_unresolved` | 12 |
| `spanning_row_needs_review` | 14 |
| `table_continuation_needs_review` | 2 |
| `native_ocr_conflict` | 8 |
| `footnote_needs_review` | 1 |

## Tải qua API thật

| Dạng | HTTP/kết quả | Khớp artifact |
| --- | --- | --- |
| md | 200 | True |
| json | 200 | True |
| reader | 200 | True |

Các kiểm tra này chỉ đọc nguồn/artifact đã lưu, không reparse toàn tài liệu để làm lại kết quả. Không tự duyệt semantic proposal, sửa metadata để mở gate hoặc gọi benchmark chatbot. Frontend browser E2E chưa chạy: tab kiểm tra vào màn hình đăng nhập nên đã đóng; không giả đăng nhập. Không sửa app nên không chạy lại Ruff/full pytest; kết quả full suite cũ 18 FAIL vẫn là lịch sử, không nâng thành PASS hiện tại.

## Bàn giao

[Mở revision PDF trong kho](http://localhost:3000/knowledge/col_admissions/sources/bnd_12190866d5ec?revision=ks_rev_1071c152fab0&tab=content). Markdown và JSON được giữ để người dùng đối chiếu. Báo cáo thô, receipt, manifest hash và render kiểm tra nằm trong `backend/storage/context578/` được Git ignore; không đưa corpus hoặc ảnh nguồn vào báo cáo Git.

Muốn tiếp tục nạp vector cần sửa nguyên nhân tái dựng lưới bảng/header và đối soát hình/chú thích, thêm regression từ dạng cấu trúc tương ứng rồi tạo revision mới. Phiên này dừng ở kết quả upload/kiểm tra thật, chưa được giao sửa parser. Không commit/push/deploy, không restart và không thay mô hình. File PDF local vẫn nguyên hash, chưa được stage vào Git. Không xóa Storage tạm của các phiên trước.
