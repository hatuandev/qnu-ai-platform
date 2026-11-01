# Phiên 799 — Chẩn đoán sửa chính tả sai nghĩa

Người dùng chỉ ra đề xuất `bán → huyên` sai; đúng trong cụm là `cơ bản`.

- Đọc mã `ocr/review/detection.py`, `anchors.py` và artifact phiên 797–798; không sửa ứng dụng hoặc dữ liệu DB.
- Xác nhận `ev_p015_b007`, check `spl_94e72b37e387`: OCR thô `bệnh viện cấp cơ bán trở lên`; AI đề xuất `bán → huyên`, lý do tự giả định nguồn là `cấp huyện`. Bản sửa 797 chứa `cấp cơ huyên`.
- Render và đối chiếu ảnh gốc trang 15: văn bản thực ghi **bệnh viện cấp cơ bản trở lên**. Ảnh dẫn xuất tại `tmp/ocr798/page15-context-check.png`; PDF không bị sửa.
- Request hiện gửi toàn bộ text từng unit được chọn, nên không thể kết luận chỉ do thiếu phần câu bên trong unit. Model không được cấp ảnh gốc, không có quan hệ ngữ cảnh ngoài các unit đã chọn. Prompt v3 yêu cầu không chắc thì bỏ qua nhưng không bảo đảm tuân thủ.
- Validator chỉ kiểm schema, source span/anchor, overlap, replacement khác rỗng và chuỗi số không đổi. PASS các điều kiện này không chứng minh đúng nghĩa hoặc đúng hình ảnh. Literal anchoring không phải semantic verification.

Hướng khắc phục đề xuất: cho model ngữ cảnh cấu trúc lân cận và ảnh crop nguồn đúng trang/bbox; kiểm tra cả câu sau thay; giữ chưa chắc chắn nếu ảnh mờ/mâu thuẫn. Không dùng từ điển thay thế cố định. Trước compiler phải tạo bản sửa dẫn xuất mới có hash/version, không ghi đè OCR hoặc lịch sử cũ.

Kiểm chứng thực chạy: đọc artifact JSON; render PyMuPDF và xem ảnh; kiểm source hash so với SHA256 đã ghim; kiểm encoding/link/diff tài liệu. Unit/integration/live model: NOT RUN, vì đây là chẩn đoán và đề xuất; chưa triển khai bộ kiểm đúng nghĩa.
