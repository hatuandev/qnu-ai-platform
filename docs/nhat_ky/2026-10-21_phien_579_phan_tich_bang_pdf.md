# Phiên579 — Phân tích Bảng 1 PDF bị tách 34 cột

Người dùng yêu cầu tìm nguyên nhân; phạm vi chỉ điều tra, chưa sửa parser. Dùng skill qnu-knowledge-ingestion, đọc mã và artifact thật của Context578 trên nhánh `v1.0.1`.

Đã đối chiếu render trang 6, DOCX nguồn 16×12, raw evidence đúng hash và JSON đang lưu 27×34. PyMuPDF 1.28.2 dùng `lines` nhận cả cạnh nền; loại 148 path nền khỏi 744 path đưa bảng về 16×12, nhưng ba ô header đầu còn gộp. Có 22 ranh giới x nội bộ thừa. Trang 6 không OCR; 20 đoạn viền bị phân loại figure do ngưỡng hình học và bbox. Chưa kết luận mọi cảnh báo ở toàn tài liệu cùng nguyên nhân.

`backend/.venv/Scripts/python.exe backend/storage/context579/diagnose.py`, cwd root, exit0. D01–D08 PASS xác minh nguyên nhân; Q01–Q03 FAIL về lưới hiện tại, tiêu đề thử nghiệm và header binding. Full pytest/Ruff/live OCR/E2E mới NOT RUN vì không sửa ứng dụng. Kết quả cũ 18 FAIL vẫn là lịch sử.

[Báo cáo đầy đủ](../bao_cao/context579/PDF_TABLE_ROOT_CAUSE.md). Evidence ignored ở `backend/storage/context579/`: raw evidence tải chỉ đọc từ MinIO local, probe, diagnosis và hash. Không ghi DB/artifact phục vụ, không tái xử lý toàn tài liệu/index/publish, không sửa model, restart hoặc commit/push. Giữ toàn bộ thay đổi Context578 chưa commit.

File Git mới: báo cáo, nhật ký này, snapshot579. Cập nhật có phạm vi WORK_LOG, index nhật ký và PROJECT_CONTEXT. Bước sau nếu được giao: sửa lưới/header/routing/viền bằng thuật toán chung, regression bảo toàn nội dung rồi kiểm thử revision mới trong phạm vi được phép.
