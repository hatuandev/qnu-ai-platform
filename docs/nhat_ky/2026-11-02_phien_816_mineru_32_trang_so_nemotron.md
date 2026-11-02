# Phiên 816 — MinerU đủ 32 trang và đối chiếu Nemotron gốc

Ngày: 2026-11-02. Người dùng yêu cầu OCR toàn bộ PDF Quy chế 363 và so độ chuẩn tiếng Việt với Nemotron-3.5-Parse.

## Thực hiện

- Chạy trực tiếp API MinerU được chỉ định, một create/upload cho PDF 32 trang; không retry. Không sửa mã ứng dụng, ModelOps, bản OCR đã rà, compiler, publication hoặc index.
- Cùng PDF SHA256 `59444d277a5e904808537ce70544c1fc83c0bf0a2f2653b78af362af59d5cccc`. MinerU server báo parser 4.1.3, standard/OCR. Baseline Nemotron là canonical version 0 trong artifact lịch sử, chưa sửa chính tả; không gọi lại Nemotron.
- Chốt gold từ ảnh nguồn trước khi đọc đầu ra MinerU: 14 đoạn/10 trang, 755 từ/3.449 ký tự. Trợ lý chép, chưa có chấm độc lập; sửa một lỗi chép R11 trước xem đầu ra, có manifest truy vết. NFC/casefold/khoảng trắng/loại định dạng; giữ dấu, không sửa chữ. Căn chỉnh cùng chính sách trên cùng trang.

## Kết quả thực chạy

- PASS xử lý: 32/32 trang không rỗng; 906,47 giây từ create đến observed completed, parser báo 897.753 ms. HTTP 202/200/200; ZIP 12 tệp được kiểm hash, 409 bbox block hợp lệ về hình thức, 9 ảnh tham chiếu tồn tại.
- Mẫu tiếng Việt: MinerU 5 lỗi ký tự (CER 0,145%), 6 lỗi từ (WER 0,795%); Nemotron 23 lỗi ký tự (CER 0,667%), 23 lỗi từ (WER 3,046%). Đây không phải CER/WER toàn 32 trang.
- Probe sẵn có: cùng 14/16 nhưng khác mục trượt. Không có kết quả 16/16.
- Bảng trang 32 MinerU khớp ảnh 4×8 với 29 ô trống, Nemotron gốc 3×10. Không nghiệm thu toàn bộ nối bảng xuyên trang.
- Chất lượng chưa đạt tuyệt đối: MinerU vẫn nhầm dấu; kiểm tra độ dài 32 trang và ảnh gốc phát hiện bỏ vùng ký tên trang 30 trong cả hai JSON. Lỗi mới ngoài mẫu được báo riêng, không đổi mẫu để làm xanh.
- Thời gian baseline Nemotron là lịch sử và pipeline/render/concurrency khác; không suy xếp hạng tốc độ model từ hai lượt này.

## Lệnh và artifact

Chạy bằng Python venv backendV1: `tmp/mineru816/run_full.py` (exit 0), `tmp/mineru816/compare.py` (exit 0). Sáu kiểm tra thuật toán căn chỉnh đạt; source hash được kiểm lại. Một lệnh đọc chẩn đoán ban đầu lỗi console cp1252, đã chạy lại với stdout UTF-8; không tạo lại task OCR.

Kết quả riêng, không đưa corpus/credential vào Git: `tmp/mineru816/REPORT.md`, `comparison.json`, `integrity-and-diagnostics.json`, ZIP, MD và hai JSON gốc. Giữ source/ảnh/gold và raw baseline để truy vết. Không app build/unit suite vì không đổi ứng dụng; không commit/push/restart.

Kết luận có phạm vi: MinerU tốt hơn về chữ trên mẫu PDF này, có lỗi mất vùng bố cục nên chưa thay thế mặc định. Giữ rà soát/xác nhận trước compiler.
