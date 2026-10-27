# 21 — Xử lý OCR backendV1 có kiểm ngân sách và nguồn truy vết

1. Upload lưu revision gốc bất biến và run queued bền vững trong DB; dispatch sau commit.
2. Worker nạp cấu hình, claim bằng token riêng, kiểm lại quyền workspace và revision.
3. Ghim identity provider/endpoint/model/capacity và prompt. Thay identity khi resume
   phải dừng; muốn xử lý bằng cấu hình mới thì tạo generation mới.
4. Render trang; DOCX có header/footer theo section chưa được converter giữ đầy đủ
   trả lỗi tường minh, không âm thầm bỏ nội dung. File gốc vẫn đọc lại được.
5. Trước từng request, kiểm ModelOps capacity và accounting ảnh/prompt. Thiếu căn cứ
   hoặc vượt phạm vi phải báo lỗi; quota reserve cả input bound và output.
6. Lưu in_flight trước HTTP, lưu raw bytes đã nhận trước parse; lỗi/truncated giữ raw.
   Canonical/Markdown/manifest là dẫn xuất, không tự sửa chính tả OCR.
7. Heartbeat gia hạn lease; mọi commit kiểm quyền sở hữu. Cron phục hồi job hết lease
   hoặc delivery cũ. Trang chưa rõ kết quả giữ uncertain, không tự gửi lại.
8. Đọc kết quả qua đủ scope workspace/collection/source/revision/run và checksum.
   Hoàn tất xử lý kỹ thuật chưa đồng nghĩa duyệt nội dung, publication hoặc Compiler.

[Hợp đồng OCR](../../backendV1/docs/ocr-processing.md) ·
[Capacity/accounting](../../backendV1/docs/model-capacity.md).

## Theo dõi và nghiệm thu

[Hướng dẫn nghiệm thu OCR](../../backendV1/docs/ocr-acceptance.md) mô tả trace từng
bước, API raw theo trang và cách xuất báo cáo từ JUnit/receipt. Báo cáo kiểm tra
kỹ thuật không tự kết luận chất lượng Nemotron so với ảnh nguồn hoặc duyệt Compiler.
