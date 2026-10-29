# ADR-005 — Bằng chứng và revision

**Quyết định:** giữ nguyên bất biến của hệ cũ: raw OCR/tệp gốc bất biến, canonical
MD/JSON là dẫn xuất, index revision có parity trước khi activate, citation trỏ
revision/hash/trang.

**Hệ quả:** không có đường tắt "publish nhanh" bỏ qua quality gate.

## Ngoại lệ ngày 2026-10-29 — xóa vĩnh viễn nguồn chưa phát hành

Người dùng yêu cầu xóa trực tiếp tài liệu nguồn trong kho tri thức, không qua
trang Tài nguyên/thùng rác. Áp dụng riêng `backendV1 source/delete`, sau preview
và xác nhận của quản trị viên: cho phép xóa toàn bộ revision, raw và dữ liệu dẫn
xuất phụ thuộc. Không cho xóa nếu còn bản `published`; phải `withdraw` trước.
Worker kiểm lại quyền và publication, ghim target/phạm vi, có biên nhận bền vững,
retry cùng ý định và audit tối thiểu. Không sửa âm thầm bằng chứng; đây là hủy
dữ liệu có chủ ý, không thể restore từ QNU sau khi chấp nhận.

Các thao tác archive, collection/document delete và nguyên tắc giữ bằng chứng
khi xử lý/sửa lỗi vẫn giữ nguyên. Bundle backup, audit/hash/idempotency được giữ
theo chính sách riêng; không mở rộng thành purge tự động hay áp dụng cho `backend/`.
Chi tiết: [vòng đời tài liệu](../resource-lifecycle.md#xóa-vĩnh-viễn-tài-liệu-nguồn--ngoại-lệ-có-phạm-vi).
