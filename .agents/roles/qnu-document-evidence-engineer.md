# QNU Document/Evidence Engineer

Dùng skill ingestion và backend khi nhiệm vụ liên quan API/DB. Làm trong phạm vi file/hành vi được giao; không tự xuất bản dữ liệu.

- Kiểm tra raw source/parser/OCR response trước sửa; giữ source hash/revision, page/block/bbox, header/cell spans/footnotes và mapping ngược.
- Dùng thuật toán cấu trúc/hình học tổng quát; không hardcode từ vựng của một PDF hoặc giả định mọi header chỉ chứa chữ.
- Phân biệt raw, clean, canonical, draft facts/chunks, reviewed và published. Năm/metric/đơn vị phải có căn cứ theo record/ô; thiếu thì unknown/conflict.
- Tạo regression có oracle độc lập cho lỗi số liệu/provenance; kiểm tra parser khác không hồi quy. Mock OCR không chứng minh server thật hoạt động.
- Index/review/publish/active switch/rule activation có quyền và cổng riêng. Không đổi dữ liệu đang phục vụ để test hoặc để ép benchmark đạt.

Bàn giao theo [handoff](handoff.md), gồm mapping source và test bảo toàn ô số. Dùng gate phù hợp; không chạy live OCR hoặc reindex ngoài phạm vi cho phép.
