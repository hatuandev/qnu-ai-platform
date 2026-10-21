# Context579 — Vì sao Bảng 1 từ 12 cột thành 34 cột?

Nguyên nhân trực tiếp đã được tái hiện: bộ nhận bảng đang dùng các cạnh hình chữ nhật tô nền trong PDF như đường chia ô. Vì vậy, lưới bị chia nhỏ ngay ở bước đọc PDF, trước khi tạo Structured JSON và Markdown. Đây là lỗi tái dựng hình học của parser; riêng Bảng 1 không chạy OCR hoặc gọi LLM.

## Phạm vi và bằng chứng

- PDF người dùng export: 18 trang; SHA256 `082c412e145a9ef39ae50110ae16cc80c17d612e2f0e00f9d16ee78c7c1c3b02`.
- Bảng 1 ở trang 6. Đối chiếu hình render với bảng đầu trong DOCX nguồn: **12 cột, 16 hàng**, gồm 3 hàng tiêu đề, 12 chương trình và 1 hàng tổng.
- Revision đã nhập: `ks_rev_1071c152fab0`, binding `bnd_12190866d5ec`; khối JSON `p0006_b0004`, ID trong projection `qnu:p0006_b0004`.
- Đọc raw evidence đã lưu qua StorageDriver từ MinIO local/development; kiểm hash khớp metadata revision. Không gọi dịch vụ OCR/LLM mới, không ghi DB hoặc sửa artifact nguồn.
- Bằng chứng và probe riêng nằm trong `backend/storage/context579/`, được Git ignore. Mã ứng dụng và hai file nguồn được so SHA256 trước/sau, giữ nguyên.

## 1. Lỗi phát sinh ở bộ nhận đường kẻ

Luồng thực tế:

1. [capture_native_page](../../../backend/app/modules/knowledge/parsers/pdf_evidence.py) gọi `find_page_tables`.
2. [find_page_tables](../../../backend/app/modules/knowledge/parsers/blocks.py) gọi `page.find_tables()` mà không chọn chiến lược phân biệt nền và đường kẻ. Thư viện PyMuPDF đang cài là **1.28.2**, mặc định dùng `lines`.
3. Kết quả thô đã là **27 hàng × 34 cột**. Probe đọc lại PDF tái hiện chính xác ma trận trong raw evidence và Structured JSON đã lưu.
4. [native_table / table_blocks](../../../backend/app/modules/knowledge/parsers/pdf_tables.py) nhận ma trận đó, giữ dữ liệu và tạo cột `c01…c34`. Markdown phản ánh lưới sai đã có; không phải tầng hiển thị tự tạo thêm cột.

Trang 6 có **744 path đồ họa, tất cả dạng tô màu `f`**. Chúng bao gồm cả nền ô, nền chữ và viền bảng được vẽ bằng hình chữ nhật rất mỏng. Với ngưỡng mặc định của thư viện, có 148 path tô nền rộng/cao hơn 3 point và 596 path còn lại. Đây là thống kê của probe trên file này, không phải ngưỡng sản phẩm đề xuất.

Cạnh của các mảng nền bên trong ô, ví dụ tọa độ x khoảng `68.04`, `114.74`, `163.58`, `293.33`, `338.57`, bị nhận thành ranh giới cột. So với lưới 12 cột, có **22 ranh giới x nội bộ thừa**. Những dải nhỏ khoảng 4–5 point quanh chữ trở thành cột giả; tương tự, cạnh nền theo chiều ngang tạo hàng giả.

| Thử nghiệm offline trên cùng trang 6 | Hàng | Cột | Kết luận |
| --- | ---: | ---: | --- |
| Hàm hiện tại, mặc định `lines` | 27 | 34 | Tái hiện chính xác lỗi đang lưu |
| `lines_strict` | 16 | 12 | Hết cột/hàng giả, nhưng tiêu đề còn sai |
| Vẫn `lines`, loại đúng 148 path nền trong bộ nhớ | 16 | 12 | Ma trận bằng `lines_strict`; xác nhận quan hệ nhân quả |
| Dò theo vị trí chữ `text`, không giới hạn vùng bảng | 51 | 19 | Kéo cả nội dung ngoài bảng vào; không thể đổi mù sang cách này |

Hàm bù đường kẻ bảng nối trang `detect_open_top_lines` trả danh sách rỗng ở trang 6. Đường kẻ nhân tạo không gây ra ca lỗi này.

## 2. Chỉ đổi sang `lines_strict` vẫn chưa đủ

Sau khi bỏ nền, ba ô đầu tiêu đề bị gộp thành một ô:

| Nguồn | Kết quả probe `lines_strict` |
| --- | --- |
| `Nhóm` / `Mã CT` / `Tên chương trình` là ba ô riêng | `Nhóm Mã CT Tên chương trình` / rỗng / rỗng |

PDF không giữ bảng dưới dạng ô như DOCX; nó lưu chữ và các lệnh vẽ. Các đường dọc giữa ba ô đầu không liên tục qua toàn bộ phần tiêu đề. Ví dụ quanh x≈110, đường xuất hiện tới y≈91.82 rồi không có đoạn dọc nối tới y≈136.58. Loại toàn bộ nền giúp bỏ ranh giới giả nhưng cũng mất một phần bằng chứng phân vùng các ô tiêu đề.

Vì vậy cần phối hợp đường kẻ thật, vùng nền có vai trò ô, vị trí chữ, ô gộp và các cột ổn định ở phần dữ liệu. Không được coi “đếm lại đủ 12 cột” là đã sửa xong. Các nhãn năm, metric, đơn vị và phạm vi phải gắn đúng từng cột.

## 3. Những khoảng hở khiến lỗi chưa được phục hồi

**Nhánh OCR chưa nhận tín hiệu lỗi cấu trúc bảng.** Raw evidence xác nhận chỉ trang 13 được OCR; trang 6 là `native`, không có alternative OCR. Điều kiện trong [build_native_pages](../../../backend/app/modules/knowledge/services/source_extraction.py) chủ yếu xét chữ hỏng, encoding và ảnh chưa được phủ bởi chữ. Nó chưa dùng lưới bất thường hoặc mất header làm điều kiện fallback. Do đó không có kết quả OCR thứ hai để đối chiếu Bảng 1. Đây là khoảng hở phục hồi, không phải bằng chứng OCR chắc chắn sẽ làm đúng.

**Header chưa được xác minh tự động bằng cấu trúc.** `native_table` cố ý đặt `header_depth=0`, giữ đề xuất engine riêng để tránh nuốt dòng dữ liệu đầu. Hành vi bảo vệ này cần giữ; hiện còn thiếu bước xác minh vai trò header bằng bằng chứng độc lập. Toàn bộ 34 cột của Bảng 1 đang có `header_path=[]`. Nó làm tăng cảnh báo thiếu header và chưa tạo được quan hệ năm–chỉ tiêu–đơn vị tin cậy. Không được giải quyết bằng lấy mọi dòng đầu làm header hoặc thêm từ điển nhãn viết tay.

**Một số đoạn viền bảng bị coi là hình nội dung.** Ở trang 6, `_native_items` phát ra 20 figure từ những path viền mỏng. Ví dụ path 12 có kích thước khoảng **0.48 × 4.56 point**. Bộ lọc [grid furniture](../../../backend/app/modules/knowledge/parsers/pdf_structure.py) yêu cầu đoạn dài ít nhất 10 lần bề dày; đoạn này có tỷ lệ khoảng 9.5 nên lọt qua. Bbox bảng được thư viện xê dịch nhẹ khiến tiêu chí nằm trong bảng ≥90% cũng không bắt được đoạn viền ngoài. Đây là 20 cảnh báo hình sai ở trang đã đối soát, không có nghĩa toàn bộ 229 figure trong tài liệu đều là cảnh báo giả.

## 4. Hướng sửa theo nguyên nhân chung

Thứ tự đề xuất cho đợt sửa tiếp theo:

1. **Tái dựng lưới từ bằng chứng hình học:** phân loại nền/viền/đồ họa, gom đoạn viền liên quan, so các phương án nhận bảng bằng độ ổn định cột và mức bảo toàn chữ. Giữ raw paths và liên kết cell/bbox. Không hardcode tên bảng, 12 cột hoặc nội dung câu benchmark.
2. **Khôi phục header nhiều tầng và ô gộp:** dùng hàng dữ liệu, tọa độ, typography và vùng ô để xác minh vai trò; gắn năm–metric–đơn vị đúng cột. Chưa đủ bằng chứng thì giữ raw và unresolved, không nuốt dòng đầu.
3. **Kiểm tra độ tin cậy trước khi chốt native:** phát hiện dải cột giả, hàng rỗng phát sinh, header bị dính và mâu thuẫn cấu trúc; chỉ định OCR cục bộ khi cần. Nếu hai bản khác nhau, giữ cả hai và đối soát, không lấy số ô có bbox làm bảo đảm nội dung đúng.
4. **Nhận diện viền theo nhóm hình học:** tránh biến đoạn viền thành figure, đồng thời bảo toàn hình/biểu đồ thật và raw evidence. Không hạ Quality Gate hay tự giải quyết tất cả cờ hình.

Regression cần phủ bảng có nền màu ở header/body, nhiều tầng năm, ô gộp, viền đứt/viền mỏng, bảng không nền, bảng không viền và nối trang. Phải kiểm nội dung từng ô, số 0 đầu mã, dấu thập phân, chú thích và phạm vi năm; không chỉ assert số cột. Giữ ca âm tính dòng đầu là dữ liệu và ca không đủ chứng cứ header.

## 5. Kiểm chứng và giới hạn

Chạy từ root repo:

`backend/.venv/Scripts/python.exe backend/storage/context579/diagnose.py`

Exit code **0**: probe điều tra hoàn thành, **8 kiểm chứng nguyên nhân PASS**. Đây không phải kết luận chất lượng PDF đã PASS.

| Test ID | Kết quả | Bằng chứng |
| --- | --- | --- |
| D01 | PASS | Hash PDF/raw evidence/revision khớp |
| D02 | PASS | Ma trận native tái hiện đúng artifact đang lưu |
| D03 | PASS | Trang 6 không OCR, không alternative; chọn native |
| D04 | PASS | Không thêm đường kẻ giả open-top |
| D05 | PASS | Loại nền cho ma trận bằng `lines_strict` |
| D06 | PASS | Phương án bỏ nền trở về 16×12 như DOCX |
| D07 | PASS | Xác định 22 ranh giới x nội bộ thừa |
| D08 | PASS | Nguồn DOCX/PDF và mã parser nguyên hash |
| Q01 | FAIL | Bảng hiện tại vẫn 27×34, yêu cầu 16×12 |
| Q02 | FAIL | Thử `lines_strict` còn gộp ba nhãn đầu |
| Q03 | FAIL | Bảng hiện tại thiếu 34 header path |

Không sửa ứng dụng nên Ruff/full pytest, live OCR và ingestion E2E mới **NOT RUN**. Bộ test cũ có 18 lỗi nền vẫn là kết quả lịch sử, không đổi thành PASS. Không tái xử lý toàn tài liệu qua pipeline, không tạo revision/index/vector, không publish, đổi model/config, restart, commit hoặc push. Revision hiện hành và Quality Gate được giữ nguyên; báo cáo này xác định nguyên nhân và phạm vi sửa, chưa phải nghiệm thu bản sửa.
