# Phiên 988 — Gắn năm có dẫn chứng cho hai bảng quy đổi của P2

## Phạm vi và cách làm

- So hai bảng IELTS trang 9 với nguồn. Mỗi PDF ghi rõ mùa tuyển sinh trong tiêu đề. Bảng không ghi năm nhưng được giới thiệu bằng câu quy đổi trực tiếp. [Quy tắc năm](../../backendV1/qnu/domains/knowledge/compilation/table_year.py) chỉ gắn năm nếu lưới hợp lệ, bảng thuộc đoạn quy đổi tại nguồn, có đủ hai dẫn chứng cùng phiên bản và không gặp năm cạnh tranh hay dấu hiệu hồi cứu. Mỗi cột dùng lại hợp đồng annotation, mã metadata v6.
- Hai năm có căn cứ qua danh mục ô thì gắn nhãn vào phần trả lời. Nếu câu so sánh chỉ chọn được ô có căn cứ cho một phần các năm, giao diện trả kết quả đã kiểm chứng kèm thông báo năm chưa xác minh. [Chọn ô](../../backendV1/qnu/domains/rag/answer/table_selection.py) · [Kết xuất ô](../../backendV1/qnu/domains/rag/answer/cells.py)

## Kiểm chứng và bàn giao

- **P2 PASS** trên kho thử `col_14ba3e802039`, biên dịch source-first `cmp_aa37684781b5`, phiên bản `cver_3c16f06c21a1`, index `idx_7a92425c0faf` hoàn tất. Dùng FastAPI TestClient với hàng đợi tại chỗ để gọi trực tiếp worker hiện hành và provider đã cấu hình. Qwen trả **2025 → 10.0** từ `ocr_a56d558068a0:ev_p009_b006_c03_01`, **2026 → 9.0** từ `ocr_66956c993bcf:ev_p009_b007_c03_01`. Lượt quyết định phê duyệt bản thử ghi rõ bỏ qua rà soát. Đã lưu kết quả tại `%TEMP%/qnu_c3_988_p2_e2e.json`. Chỉ thay version/index của kho thử, không đổi nguồn PDF.
- Ruff phạm vi, 93 unit test trên bảy tệp và 2 integration test qua API đăng ký metadata trong DB cô lập đều đạt. Có ca hồi quy từ chối dẫn chứng thiếu một vế hoặc nguồn có dấu hiệu hồi cứu. Chưa chạy toàn bộ backend. Không chạy lại bộ 100 câu. Chưa đo nhánh Qwen đề xuất metadata vì P2 đã xác định được từ quy tắc.
- **P5 đang phân tích.** Nguồn OCR PDF 2025 trang 9 tách nhãn đăng ký của QNU và hai mốc ngày qua ba khối liên tiếp, nhãn đăng ký trên hệ thống Bộ và cửa sổ ngày qua hai khối. Chạy bộ nhận diện trên từng khối trả rỗng cho cả hai sự kiện. Phát lại các câu đã nối theo đúng thứ tự nguyên bản thu được cả hai khoảng ngày và hai kênh đúng. Cần nối có căn cứ trong cùng câu rồi dùng phạm vi năm sự kiện khi tra cứu. **P7 chưa triển khai.** Vẫn cần xử lý thiếu ô từ nguồn và kiểm chứng hành vi thiếu căn cứ.
