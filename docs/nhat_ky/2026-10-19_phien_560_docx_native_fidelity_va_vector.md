# Phiên 560 — Kiểm chứng nguyên văn DOCX và nạp vector

## Yêu cầu và phạm vi

Xử lý tám cảnh báo của tài liệu DOCX phức tạp, kiểm thử nạp tự động và vector; không hạ Quality Gate, không xuất bản, không commit/push. Người dùng xác nhận riêng bản chép Hình 1 và cho phép khởi động lại riêng worker local khi không có job khác. Sau đó người dùng nhận tự chạy BE/worker/FE; không mở rộng quyền restart.

## Thực hiện

- Thêm `docx_layout_fidelity.py`: đối chiếu mọi ô, span và hàng với OOXML; bảng chưa biết vai trò chỉ được giữ như nguyên văn, không tạo fact số chắc chắn. Hàng gộp toàn chiều ngang giữ một literal, không suy phạm vi nhóm.
- Sửa đối sánh trang cho mục danh sách có dấu ngoặc kép; không dùng từ điển nội dung của tài liệu.
- Thêm `source_figure_review.py`: xác nhận hình gắn source/image/transcription hash và revision đang chờ; lưu actor, phạm vi và thời điểm. Không duyệt các proposal khác.
- Gắn kiểm chứng native layout/hình vào ingestion và kiểm tra lại trước indexing/publication. OCR thật không đọc đủ Hình 1, nên dùng đúng xác nhận của người dùng; không báo OCR đạt giả.
- Tách DTO thuần sang `review_contracts.py`, giữ re-export tương thích, xử lý vòng import phát hiện khi worker khởi động lạnh.

## Kết quả tại thời điểm phiên 560

Revision 4 `ks_rev_a5ac6f9d416f`: 233 khối, 10 bảng, ba footnote Word; raw cells/spans giữ nguyên. `READY_WITH_LIMITATIONS`, không blocker nội dung; footnote thứ ba giữ anchor nhưng chưa biết trang preview. Vector job `job_492ddb297973` hoàn thành, 262 chunks, 368 facts; chỉ mục staging, chưa xuất bản.

Focused: 261 PASS và 23 subtests, exit 0; nhóm worker/semantic/figure sau sửa cold-start: 86 PASS, exit 0. Scoped Ruff đạt. Full suite của phiên này bị ngắt, **không phải PASS**. Evidence riêng: `backend/storage/context560/`.

## Phần tiếp nối bắt buộc

Thao tác xuất bản sau đó phát hiện 105 entity_key khác nhau giữa projection và ORM, dù 368 giá trị và provenance tương ứng khớp. Nguyên nhân: tạo identity bằng trang đầu bảng rồi thay provenance bằng trang của hàng. Phiên 561 xử lý bằng policy identity theo provenance cuối, giữ nguyên phép đối soát nghiêm ngặt.

Full regression phiên 561 cũng phát hiện ba ca header/association chưa được nhóm focused trên bao phủ. Phiên 561 giữ lại nhãn header chưa rõ với trạng thái chỉ nguyên văn và yêu cầu association duy nhất trước khi xét vai trò header; không được coi focused phiên 560 là bằng chứng không hồi quy toàn bộ.

Database test phiên 560 đã dọn ở phiên 561. Xóa thư mục runtime test bị kiểm duyệt tự động chặn với lý do `blocked by policy`; giữ lại và không bypass. Nguồn Knowledge revision 4 về sau được xóa trong phạm vi người dùng duyệt dọn toàn `col_admissions` ở phiên 561; đây là trạng thái lịch sử, không phải nguồn hiện phục vụ.
