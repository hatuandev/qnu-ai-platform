# Phiên872 — Bảng nối trang và cảnh báo ảnh đã có chữ OCR

Người dùng yêu cầu sửa hai điểm còn lại từ đối chiếu phiên871: header/mapping
bảng DOCX nối trang và cảnh báo ảnh rỗng không phản ánh text OCR con. Không sửa
hai lỗi chính tả bên trong ảnh; không thay nguồn hay kết quả ứng dụng đã lưu.

## Thay đổi

- `native_docx_fragments.py`: chứng minh duy nhất toàn bảng theo thứ tự từng ô,
  có header lặp và cell ngắt tại ranh giới trang. Không so khớp mờ hay suy giá trị.
  Giữ các mảnh vật lý, bbox, ô trống, spans và chữ; khôi phục header nguồn, thêm
  mapping bảng/hàng/ô/khoảng text. Mơ hồ, thiếu/sai ký tự/số, đảo cột, ngắt trang
  hoặc merge dọc chưa hỗ trợ vẫn giữ cảnh báo.
- `native_docx.py`, `layout.py`, `native.py`, `artifacts/canonical.py`: đưa mapping
  qua snapshot/canonical; native version tăng v3, không dùng parser mới giải lại
  run v2. Không cần migration. Bảng literal trong Compiler giữ metadata mapping.
- `compilation/limitations.py`: kiểm text OCR theo asset trên cùng trang, cùng
  tài liệu; có text thì ghi rõ đã OCR nhưng chưa xác minh chữ/bố cục/độ đầy đủ.
  Dẫn chứng ảnh và từng khối con được giữ, chia nhóm citation theo contract.
- Regression mới `test_docx_fragments_872.py` và
  `test_compilation_image_limits_872.py`; cập nhật hướng dẫn OCR/quy trình43.

## Kiểm chứng

- Root repo, venv Python: 57/57 unit PASS, exit0, gồm hai file mới và các ca
  native710/native870/limitations740. Scoped Ruff PASS, exit0.
  Ca bảng độc lập có prefix giống bảng lớn đã tái hiện FAIL trước khi thêm
  guard, sau sửa PASS; không nuốt bảng độc lập thành mảnh nối trang.
- Offline trên cùng DOCX và PDF render đã lưu, không gọi OCR/LLM/converter mới:
  18 trang, 11 mảnh bảng, 660 ô giữ nguyên text/rowspan/colspan. Ba mảnh trang9–11
  gắn cùng bảng nguồn, header nguồn khôi phục; không còn warning mapping ở file
  này. Cell nối trang được ghi đúng hàng nguồn. SHA256 tệp gốc không đổi.
- Qua build canonical → source-first Compiler: bảng giữ toàn bộ mapping/cell;
  validation source_copy=retained. Cảnh báo ảnh có đủ 7 citation (ảnh +6 khối
  chữ OCR), không còn kết luận ảnh chưa có text. Báo cáo tại thư mục bỏ qua Git
  `tmp/table-mapping-872/`; không đưa corpus vào nhật ký hoặc commit.
- Full gate `PYTEST_ADDOPTS=-x; .\make.ps1 test-be`: FAIL, exit1,
  39 PASS/1 FAIL (314,88s), tại lỗi nền đã ghi nhận phiên869/870/850:
  `tests/integration/test_auto_extraction_710.py::test_docx_table_has_real_structure_and_original_is_unchanged`.
  Assertion header nguồn DOCX710 chưa đạt; không đổi assertion/fixture để xanh.
- Sau guard chống nuốt bảng độc lập, full gate cuối
  `PYTEST_ADDOPTS='-x --failed-first'; .\make.ps1 test-be` tiếp tục FAIL,
  exit1, 1 FAIL/0 PASS (10,09s), cùng ID lỗi nền; toàn suite chưa hoàn tất.
  Cả hai harness xác nhận `db_dropped=true`, sentinel legacy được giữ.
  Log bỏ qua Git: `tmp/test-be-872.log`, `tmp/test-be-final-872.log`.

## Phạm vi và bước tiếp

Không restart, ghi DB ứng dụng, publish/index hoặc sửa artifact cũ. Không đánh
giá lại chất lượng model/RAG trong phiên này. Người dùng khởi động lại app để
nạp mã, chạy bóc tách generation mới trên nguồn hiện có rồi biên soạn mới;
không cần xóa hay upload lại. Bản rà soát chính tả dẫn xuất cũ không tự chuyển
sang run mới, nên phải xem lại bản nguồn được chọn trước khi biên soạn.
