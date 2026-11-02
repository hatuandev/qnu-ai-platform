# Phiên 824 — Kiểm tra chất lượng chữ OCR MinerU

Yêu cầu: kiểm tra lỗi chính tả của kết quả MinerU hiện tại. Phạm vi chỉ đọc artifact của lượt OCR823 và ảnh PDF Quy chế363; không sửa app, OCR, DB hoặc cấu hình.

Áp dụng qnu-knowledge-ingestion và qnu-rag-evaluation. Nguồn/ZIP/gold đã kiểm hash; đủ32trang có văn bản. Đối chiếu mẫu14đoạn/10trang/755từ/3.449ký tự và nhìn thêm trang1,15,20,24,31,32. Bảng trang32 giữ4×8/29ôtrống. Không gọi model lại.

Kết quả mẫu: 4lỗi ký tự/CER0,116%; WER thô5/755=0,662% gồm dấu câu/tách từ. Lỗi đã đối chiếu: phản→phần, tố→tổ, GDĐT→GDDT trang24; tuyển→tuyền tiêu đề31. Ngoài mẫu, trang1 còn sai tên đơn vị/dấu đóng/chữ dấu và thiếu dòng chức danh ở vùng dấu chồng chữ. Vì vậy không coi4lỗi là tổng cảPDF, chưa nghiệm thu chính xác toàn32trang.

Gold cha816 có hai lỗi chép nguồn trong R11: ảnh trang24 in `thực tuyển`, gold ghi `trực tuyến`. Tạo revision chỉ trong tmp/ocr824, giữ nguyên gold cũ, ghi amendment/hash và bằng chứng crop. Đây là đối chiếu sau khi xem OCR, không chấm mù/không human-adjudicated. CER gold cha0,174% được giữ ở artifact để truy vết. Cụm `bệnh viện cấp cơ bản` trang15/20 OCR đọc đúng.

Lệnh đã chạy: `backendV1/.venv/Scripts/python.exe tmp/ocr824/evaluate.py` tại root, exit0; xác minh hash/coverage và chấm mẫu thành công. 15/16probe khớp,1không do tiêu đề31. Không chạy test ứng dụng (không thay code); không retry, compiler, publish, reindex, restart hoặc push. Không có kết quả PASS toàn tài liệu.

Báo cáo/bằng chứng cục bộ: `tmp/ocr824/review-report.md`, `summary-source-reviewed.json`, `passages-source-reviewed.json`, nhãn revision riêng và ảnh crop. Corpus/ZIP chỉ ởtmp, không đưa vàoGit. Các source/docs đang sửa trước được giữ nguyên; chỉ bổ sung nhật ký/index/context/snapshot824.

Bước sau: giữ nguyên raw và bước người dùng xác nhận các sửa đề xuất; nếu cần chỉ số toànPDF phải chép chuẩn đủ32trang và kiểm mất đoạn/thứ tự bảng, không suy rộng mẫu.
