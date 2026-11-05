# Phiên877 — Dẫn chứng bảng PDF nối trang

Kiểm tra lượt biên soạn PDF `cmp_d70e3358f632` bằng API đọc có xác thực.
PDF Inspector 1.25.2 xử lý 14 trang native. Biên soạn nhanh giữ 13 bảng,
955 ô và 1.111 dẫn chứng. Mảnh ở trang 3 kết thúc tại 88,4% chiều cao
trang, thấp hơn mốc 90%, làm mất liên kết đến các trang 4–8.

- Điều chỉnh biên cuối trang xuống 88%, kết hợp toàn bộ điều kiện ghép
  sẵn có về vị trí, số cột, thứ tự và khối chen giữa. Hàng khuyết phải
  trống các ô đầu dùng để nhận diện và có nội dung ở cột sau.
- Khi một kết quả chứa hàng cuối có phần nối, lấy mảnh đầu trang tiếp
  và tiêu đề trong cùng phiên bản xuất bản và phạm vi metadata. Bổ sung
  gắn tiêu đề cho mảnh hỗ trợ theo quan hệ đã xác minh.
- Giữ nguồn và canonical. Nguồn đã lập chỉ mục có thể dùng thay đổi sau
  khi nạp mã backend vì RAG tính lại quan hệ từ snapshot đã ghim.

## Kiểm chứng

- Regression trước sửa tái hiện mất chuỗi tại 88,4% và thiếu nửa sau khi
  kết quả chính nằm ở trang trước.
- Phát lại cục bộ trên snapshot thật từ API xác nhận chuỗi trang 2–8.
  Khi xuất phát từ một trong hai trang 2 và 3, catalog giữ đủ hai phần
  tổ hợp môn của Giáo dục Thể chất. Dòng Công nghệ thông tin ở trang 6
  dùng tiêu đề trang 2 và giữ dẫn chứng ô ở cả hai trang.
- Full gate dừng tại lỗi nền Redis namespace
  `test_chat_shared_admission_751.py::test_real_redis_enforces_shared_limit_and_releases_own_leases`.
- Pytest trực tiếp cho bốn bộ unit về bảng, hợp đồng trả lời và ngân sách
  sau cùng có 47 PASS và 1 FAIL. Ca cũ
  `test_ingestion_quality_and_dependencies_are_derived_not_source_rewrites`
  vẫn kỳ vọng chunker v4 trong khi mã HEAD đã là v5.
- Harness cô lập chọn `table_context_769`, `table_grounding_770`,
  `answer_contract_788`, `index_budget_869`, `answers_api_648`,
  `answer_coverage_861` có 104 PASS, 1 FAIL cùng assertion phiên bản
  cũ, 0 ERROR, thời gian 358,740 giây. Không bỏ test lỗi để báo toàn bộ PASS.
- Ruff format/check trong năm tệp sửa và `git diff --check` đạt.
- Chưa gọi model thật, phát hành, tạo chỉ mục hay khởi động lại ứng dụng.
  Phạm vi nối là bảng có số thứ tự với chứng cứ cấu trúc đủ chặt.
