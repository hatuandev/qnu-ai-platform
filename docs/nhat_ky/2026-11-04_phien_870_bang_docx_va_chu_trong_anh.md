# Phiên870 — Ký tự bảng DOCX và chữ trong ảnh nhúng

## Yêu cầu và nguyên nhân

Người dùng cho phép xử lý điểm2/3 của lần đối chiếu DOCX: dấu gạch dưới bị
đẩy xuống dòng trong ô bảng; sơ đồ ảnh trang13 thiếu chữ bên trong các khung.
Thay đổi ngân sách chỉ mục phiên869 đang có trong checkout được giữ nguyên.

- PyMuPDF table extraction có thể đưa glyph thấp (dấu gạch dưới) sang dòng
  sau. Đọc chữ trực tiếp theo cell rectangle cho đúng thứ tự trên PDF render.
- MinerU toàn trang coi sơ đồ là image, chỉ đọc được chú thích. Thử riêng toàn
  ảnh với `ocr_mode=ocr` cũng còn thiếu nhãn; cần bổ sung vùng trong các khung.

## Thay đổi

- `native_tables.py`: so multiset ký tự không trắng trước khi dùng thứ tự glyph
  của cell; không thêm/bỏ ký tự hoặc đoán tên trường. `native_docx.py` đồng bộ
  text bảng với cell nguồn khi nội dung khớp duy nhất.
- `image_regions.py`: tìm khung chứa các thành phần chữ theo hình học, tạo PDF
  gồm ảnh nguyên và các vùng trong khung ở độ phân giải nguồn. Không có từ điển
  theo câu hỏi, không diễn giải mũi tên. Có chặn tài nguyên cho ảnh nhiều nét.
- `image_ocr.py`, `mineru_execution.py`: mỗi asset có task/checkpoint, usage,
  ZIP bất biến và guard quyền/hash/config. Dùng task ID để tiếp tục, không tự
  gửi lại thao tác POST/PUT chưa rõ kết quả. Tính toán ảnh chạy ngoài event loop.
- `ports/ocr_engine.py`, adapter MinerU: truyền và ghim `ocr_mode`; checkpoint
  khác mode bị từ chối. Trang scan vẫn dùng luồng OCR tài liệu hiện có.
- `mineru_layout.py`, `layout.py`, canonical: giữ raw crop, hash PDF/ZIP, số
  vùng và bbox quy về ảnh/trang nguồn; thêm `source_image_asset_no` và cờ cần
  đối chiếu. Giữ cảnh báo vùng rỗng, loại bản sao nguyên văn có cùng vị trí.
- Native fingerprint tăng lên `qnu-native/v2`; kết quả cũ giữ nguyên, không tự
  backfill/reindex/publish/restart ứng dụng.

## Kiểm chứng thực chạy

Cwd root `D:/DuAnPhanMem/qnu-ai-platform`, trừ Ruff chạy trong `backendV1`.

- Trước sửa: ca glyph underscore tái hiện thất bại; ca giữ số gốc đạt.
- `python -m pytest ...test_native_source_870.py ...test_native_extraction_710.py
  ...test_mineru_823.py -q`: **42 PASS**, exit0. Dùng Python venv V1.
- `python backendV1/scripts/run_isolated_tests.py
  tests/integration/test_image_ocr_870.py tests/integration/test_mineru_823.py
  tests/integration/test_auto_extraction_710.py -q`: **20 PASS, 1 FAIL**, exit1.
  Hai ca mới qua API/worker đều PASS (hoàn tất và uncertain, raw/provenance,
  source không đổi, không tự gửi trùng, outsider bị chặn). DB thử đã xóa.
- Ca FAIL là lỗi nền đã ghi ở phiên869:
  `test_auto_extraction_710.py::test_docx_table_has_real_structure_and_original_is_unchanged`,
  assertion header; không sửa assertion hoặc tự suy header để làm xanh.
- Ruff trên các file code/test phiên870: **PASS**, exit0.
- Full gate `PYTEST_ADDOPTS=-x; .\make.ps1 test-be`: **39 PASS, 1 FAIL**, exit1,
  dừng ở cùng ca header DOCX710 nêu trên. Harness397,92s; DB thử đã xóa,
  sentinel được giữ. Tổng gate vẫn FAIL, các test sau điểm dừng chưa chạy.
- `git diff --check`: **PASS**, exit0 tại lúc kiểm tra.

Đối chiếu nguồn thật (tệp giữ trong `tmp/docx-review-869/`, không đưa corpus vào
Git): đọc lại PDF render18 trang và gắn bảng DOCX bằng Docling. Đủ **11 bảng,
660 ô**; các tên trường có dấu gạch dưới trở lại đúng thứ tự, giữ `0012`, dấu
nối, số0 và ký hiệu `/`. Bytes DOCX nguồn không đổi.

Thử MinerU thật trên cùng ảnh sơ đồ, dùng runtime/khóa ModelOps của scope đã
được cấp phép; DB chỉ đọc, không log khóa. Lần thử toàn ảnh giữ để đối chiếu.
Lần thử PDF ảnh +3 vùng khung mất **2,91s**, đọc được chữ trong cả **3/3 khung**.
Kết quả vẫn có hai lỗi chữ/dấu (một ở chú thích, một trong khung); không sửa
thành dữ kiện đã xác minh. Cần bước rà soát chính tả/ảnh hiện có.

## Giới hạn và bước sau

Chưa chứng minh đọc đủ mọi sơ đồ, không khôi phục ngữ nghĩa mũi tên. Chưa chạy
lại toàn bộ extraction→compiler→publication của tài liệu ứng dụng; dữ liệu cũ
chưa thay đổi. Sau khi nạp backend mới, tạo lượt bóc tách mới trên cùng revision,
kiểm tra bảng/chữ ảnh và biên soạn từ lượt mới. Không cần xóa file hay reset DB.
