# Phiên 472 — Chẩn đoán câu hỏi điểm chuẩn các năm gần nhất

## Mục tiêu và phương pháp

Người dùng yêu cầu tìm nguyên nhân, chưa yêu cầu sửa code. Đọc hội thoại xuất lúc 17:18:22 và mã runtime; hai lượt truy vấn PostgreSQL với `SET TRANSACTION READ ONLY`, không gọi model, không tạo hội thoại mới. Dùng skill qnu-rag-pipeline để lần theo retrieval và kiểm chứng.

Câu hỏi: “Điểm chuẩn ngành Sư phạm Toán học và Công nghệ thông tin các năm gần nhất là bao nhiêu?”

## Bằng chứng

- Tìm đúng hội thoại `conv_edc020682b75`: hỏi 10:17:34 UTC, từ chối 10:17:38 UTC (17:17 giờ địa phương).
- Kho hiện có 21 nguồn xuất bản. `load_row_anchors` lấy được hai hàng lịch sử ở đầu danh sách, `build_catalog` giữ đúng các ô/header.
- Nguồn `Thông tin TSĐH cập nhật.pdf`, binding `bnd_70465c368929`, index `idx_rev_8a86d7979f3a`, source `ks_rev_ee85a12d415e`:

| Ngành | Điểm trúng tuyển 2024 | Điểm trúng tuyển 2025 | Trang bảng |
| --- | --- | --- | --- |
| Sư phạm Toán học | 26.5 | 25.85 | 11 |
| Công nghệ thông tin | 16.5 | 21.5 | 11–12 |

Đây là giá trị/nhãn trong nguồn canonical đã xuất bản; chưa kiểm chứng lại ảnh PDF vật lý trong phiên này. Bảng trên không tự bổ sung phương thức khi header nguồn chỉ ghi “Điểm trúng tuyển”. Nguồn 2025 khác cũng chứa lịch sử 2023–2024 phân phương thức; không được trộn các phương thức thành một số duy nhất.

## Nguyên nhân và mức chắc chắn

1. Phân loại nhận đúng `exact_fact`, `cutoff_score` và hai mã ngành. Không có năm dạng số trong câu “các năm gần nhất”, nên `is_temporal_table_question` trả false và `decide_table_answer` không dùng nhánh bảng theo năm cố định.
2. Nhánh ô nguồn mới chạy `_metric_payload`, nhưng lọc bỏ mọi scope unit bắt đầu bằng `|`. Vì vậy header chứa “2024/2025 - Điểm trúng tuyển” không được gửi cho bước nhận diện metric. Các đoạn còn lại của hai hàng đúng chủ yếu là mục 9, mục 10 và tiêu đề chung “Thông tin về tuyển sinh của 2 năm gần nhất”.
3. Luồng này yêu cầu intro chứng minh loại số liệu trước khi cho chọn ô. Khi intro không rõ loại số liệu, nó từ chối dù các ô/header trả lời đã có. Đây là false refusal do hợp đồng kiểm chứng bị thiếu ngữ cảnh cấu trúc, không phải kết luận kho rỗng.
4. Nhật ký đúng conversation chỉ có một lượt Qwen3.5-9b, 1129 prompt tokens/11 completion tokens. Điều này khớp dừng ở bước MetricScope trước SELECT/AUDIT (thay vì đủ ba bước). Nội dung JSON model và reason code của lượt cũ không được lưu trong bảng hội thoại/usage, nên `ROW_METRIC_SCOPE_UNRESOLVED` là suy luận có bằng chứng mạnh, không phải JSON response đã đọc trực tiếp.
5. Không có bằng chứng lỗi do max_tokens=5000 hay hết context ở lượt này. Badge Faithfulness trên UI không chứng minh câu hỏi đã được trả lời; không có citation vì nhánh từ chối trả danh sách rỗng.

## Đề xuất trước khi sửa

- Cấp cho nhận diện metric cấu trúc header gốc, đường dẫn cột/năm và intro của cùng bảng; không chỉ đoạn văn trước bảng. Giữ raw spans và ranh giới nguồn, không đưa số mẫu/đáp án kỳ vọng vào prompt.
- Giải quyết thời gian tương đối từ các năm dữ liệu thực có trong cột, trả rõ “nguồn hiện có ghi nhận 2024–2025”; không tự suy đó là toàn bộ các mùa mới nhất ngoài kho.
- Giữ đủ hai entity và phân biệt metric/method, chỉ render ô đã kiểm chứng; không lấy điểm sàn 2026 thay điểm trúng tuyển.
- Regression phải phủ intro chung + header định nghĩa metric, nhiều ngành/nhiều năm, phương thức khác nhau, thiếu một ngành, dữ liệu thật sự không có.
- Lưu reason code/traces phù hợp để chẩn đoán chính xác mà không phải tái gọi model.

## Thay đổi và kiểm thử

Chỉ bổ sung nhật ký/snapshot/context/index tài liệu. Không sửa runtime, không chạy pytest/Ruff/build vì không đổi code; không gọi OCR/model, không đổi DB/vector/config hoặc push. Các tệp chuẩn bị từ phiên 471 vẫn staged, chưa commit/push do bước đó đang chờ xác nhận riêng.
