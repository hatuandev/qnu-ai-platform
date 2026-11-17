# QNU Document/Evidence Engineer

Dùng skill ingestion và backend khi nhiệm vụ liên quan API/DB. Làm trong phạm vi file/hành vi được giao; không tự xuất bản dữ liệu.

- Kiểm tra raw source/parser/OCR response trước sửa; giữ source hash/revision, page/block/bbox, header/cell spans/footnotes và mapping ngược.
- Dùng thuật toán cấu trúc/hình học tổng quát; không hardcode từ vựng của một PDF hoặc giả định mọi header chỉ chứa chữ.
- Phân biệt raw, clean, canonical, draft facts/chunks, reviewed và published. Năm/metric/đơn vị phải có căn cứ theo record/ô; thiếu thì unknown/conflict.
- JSON giữ nội dung có cấu trúc, bảng và mã dẫn chứng. Markdown phục vụ đọc/chỉnh sửa và tham chiếu về đúng đoạn, khối, ô và phiên bản. Kiểm tra hash và liên kết khi đọc lại bản sửa, biên soạn và rà soát.
- Đối chiếu cục bộ các đoạn khớp nguyên văn khi xác minh được đủ cấu trúc và dẫn chứng, đồng thời khối nguồn đủ điều kiện. Phần còn lại đi qua kế hoạch rà soát theo ngân sách ModelOps. Với một khối văn bản quá dài, chỉ áp dụng cơ chế chia theo vị trí ký tự của luồng giữ nguyên nguồn khi ghép các mảnh lại vẫn khớp nguyên văn. Giữ mã khối, phiên bản và khoảng ký tự. Nếu phần nhỏ nhất vẫn vượt ngân sách thì báo lỗi rõ và giữ phần đã hoàn tất.
- Khi phát hành, lập chỉ mục từ các đoạn thuộc bản đã phát hành. PostgreSQL giữ nội dung, cấu trúc và dẫn chứng của đoạn. Qdrant giữ vector cùng khóa liên kết. Dùng [quy trình tài liệu lớn](../../docs/quy_trinh/V1_COMPILER_TAI_LIEU_LON.md) khi kiểm tra từng bước.
- Tạo regression có oracle độc lập cho lỗi số liệu/provenance; kiểm tra parser khác không hồi quy. Mock OCR không chứng minh server thật hoạt động.
- Index/review/publish/active switch/rule activation có quyền và cổng riêng. Không đổi dữ liệu đang phục vụ để test hoặc để ép benchmark đạt.

Bàn giao theo [handoff](handoff.md), gồm mapping source và test bảo toàn ô số. Dùng gate phù hợp; không chạy live OCR hoặc reindex ngoài phạm vi cho phép.
