# Phiên 389 — PDF/DOCX hỗn hợp hình ảnh, bảng và tiến độ xử lý

## Mục tiêu và phạm vi

Triển khai bốn nhóm sửa đã thống nhất ở phiên 388, bổ sung tài liệu có chữ native, ảnh chứa chữ và biểu đồ. Không hứa mọi file đều nhận dạng đúng 100%, không tự duyệt/publish để che dữ liệu thiếu. Không reset DB, sửa credentials, dừng hoặc restart dev/worker của người dùng.

## Thay đổi

- `services/page_visuals.py`: mặt nạ 256x256 tính hợp vùng ảnh, trừ vùng văn bản native; không cộng diện tích ảnh chồng lấp, không bỏ OCR vì có caption dài hơn 80 ký tự.
- `services/source_extraction.py`: layout-v8-mixed-visuals; route trang ảnh chưa được native bao phủ; giữ nội dung native của trang khi canonical renderer bỏ trống; ghép các dòng có bằng chứng chưa có trong OCR/Docling, bảo toàn ảnh chứa chữ trên cùng trang DOCX. Khóa native PDF trong process, không khóa HTTP OCR, tránh chạy MuPDF đồng thời trên các thread.
- `services/blank_pages.py`: raster-components-v2; phân bố nhiễu thưa, kích thước component và dấu hiệu glyph thẳng hàng. Trang trắng nhiễu được giữ manifest; chữ mờ, đường kẻ, nền tối và nhiễu dày vẫn không được coi trắng.
- `parsers/inspector_process.py`, `pdf_parser.py`: PDF Inspector chạy trong child process ẩn có timeout 15 giây, dừng đúng child sở hữu khi timeout/cancel; giữ native evidence khi inspector lỗi, không dùng thread timeout để giả rằng native task đã dừng.
- `parsers/table_continuation.py`: phục hồi header cho bảng native nối trang chỉ khi chiều rộng, vị trí ngang, trang liền kề và ordinal phù hợp; trả lại dòng dữ liệu đầu đã bị nhận làm header.
- `services/html_tables.py`: parse HTML table bằng HTMLParser, bảo toàn spans trong grid và Markdown; giới hạn span, không đoán ô thiếu. HTML lỗi giữ bằng chứng để review.
- `services/table_context.py`: năm trong subheader có nhãn nhóm, nhãn định danh lặp, nối fragment cùng trang hoặc qua trang có ordinal/declared-header evidence. Chọn identity dựa độ phân biệt cột, không dùng từ điển tên ngành.
- `services/source_artifact.py`: structured-source-v4-mixed-tables; row_context tham gia đối chiếu conflict; bảng chỉ có mã–tên vẫn sinh fact mã, không thêm fact mã thừa vào bảng điểm/năm. Header chứa dòng dữ liệu không rõ bị chặn khỏi facts. Loại vùng prose bố trí khoảng trắng khỏi cảnh báo bảng thiếu; giữ vùng chart/figure/image đáng kể với VISUAL_CONTENT_REVIEW, không bịa số liệu biểu đồ.
- `source_ingestion_service.py`: layout issues áp dụng khi import, reparse và hiệu đính, không bỏ review khi chỉ lưu MD.
- `ocr/adapters/paddleocr_adapter.py`: không tìm chữ table trong toàn bộ prunedResult/model_settings; dùng Markdown/HTML/vùng table thực. Chuẩn hóa bảng HTML trước luồng cleaner.
- `jobs/ingestion_progress.py`, FE import-progress/utils/modal: terminal processing = 100%, status succeeded/failed/review_required độc lập. Đổi nhãn Tiến độ xử lý và tooltip, không đồng nhất 100% với thành công hoặc đã xuất bản.
- Tests: `test_ingestion_mixed_regressions.py`, cập nhật blank/progress/Paddle regression contracts. Script `scripts/validate_ingestion_corpus_389.py` kiểm tra thật, có --analyze để phân tích lại evidence mà không gọi OCR.

## Kiểm chứng thật

- Batch imp_batch_dc04584eee1f, SHA-256 20 bản gốc khớp. PostgreSQL READ ONLY, dùng provider Paddle thật qua Tailscale; không thay đổi sources/revisions/pointers/facts trong DB. OCR service có thử ghi audit nhưng bị READ ONLY từ chối và rollback; không nới transaction để cho ghi.
- 20/20 bóc tách được, 0 exception ở extraction. Đây KHÔNG phải chứng nhận mọi ô dữ liệu đúng hoặc tất cả đủ điều kiện xuất bản.
- BC khảo sát tuyển sinh 2022: 8 trang, trang 8 được ghi blank, khoảng 10.313 ký tự; không còn EMPTY_OCR_PAGE.
- Poster Các ngành tuyển sinh 2025: OCR thật khoảng 3.068 ký tự; 52 fact ánh xạ mã–tên, còn vùng ảnh cần review.
- TB điểm sàn 26: khoảng 17.030 ký tự thay vì 8.826 ở report cũ; đủ 8 trang, 7 bảng; không conflict/header issue sau phục hồi native.
- Phương hướng 2024 DOCX giữ context năm 2021/2022/2023; vẫn có một số bảng mất header cần review, không đoán schema khác chiều rộng.
- Phân tích lại evidence bằng code cuối: 12/20 không structured warning, 8/20 cần review. Bảy tệp có vùng hình; NQ57 có thêm header chưa phục hồi; DOCX Phương hướng 2024 còn header chưa phục hồi. Review không phải failed. Chưa kiểm định ngữ nghĩa mọi bảng, chưa chạy import-worker/browser/publish E2E.
- Báo cáo riêng: `backend/storage/ingestion389_corpus_final_report.json` (có raw extraction evidence, không credentials). Tệp cẩm nang 170MB ngoài batch20 chưa được kiểm chứng.

## Quality gates

- Ruff toàn backend: đạt (một số thư mục test storage cũ bị permission warning).
- Biome 3 file FE: đạt; 2 ca progress FE đạt; Vite + TypeScript build đạt.
- Targeted ingestion/layout/blank/Paddle/temporal/review suites: 92 passed; kiểm tra riêng sau tinh chỉnh subheader: 29 passed.
- Full backend gần nhất: 962 passed, 13 failed, 2 skipped. 11 nhóm failure đã ghi ở phiên trước; thêm hai export admissions phụ thuộc published facts sau DB reset. Không chứng nhận full suite xanh, không sửa lan auth/GC/tools/export ngoài phạm vi. Hai regression temporal do fact mã thừa đã sửa và temporal suite đạt; full gần nhất không còn hai lỗi này.

## Bàn giao và giới hạn

Cần backend và worker nhận code mới trước khi Bóc tách lại những nguồn cũ cần kiểm tra; không cần reset DB hoặc xóa originals. Phiên này không tự restart hoặc reparse nguồn DB của người dùng. RAG/DAG năm, bảng/header không rõ và hình/biểu đồ vẫn phải qua kiểm tra; 100% tiến độ chỉ có nghĩa xử lý kết thúc. Không có đảm bảo 100% mọi PDF/DOCX, không tự diễn giải đồ thị thành facts. Việc phân biệt ảnh trang trí/ảnh chứa số liệu, schema thay đổi giữa trang và benchmark concurrency production còn cần mở rộng.
