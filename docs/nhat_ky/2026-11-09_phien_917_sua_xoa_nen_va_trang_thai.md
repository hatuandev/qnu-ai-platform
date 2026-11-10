# Phiên917 — Sửa xóa nền và trạng thái phiên bản nguồn

## Phạm vi

Sửa ba phát hiện khi kiểm tra luồng ngược backend V1 sau phiên 916. Giữ nguyên API
và migration `0020_reverse_flow`.

1. **Xóa nguồn khi chỉ mục chưa có manifest.** Xác minh phản hồi embedding đã lưu
   theo thứ tự chunk và hash vector từ PostgreSQL, kể cả biên nhận cũ chỉ có
   `start/count`. Biên nhận mới giữ thứ tự `chunk_ids`. Lô dùng chung giữ vector
   của tài liệu còn lại. Với lô bị ngắt sau khi ghi tệp và trước khi commit, dùng
   phạm vi chunk của `pending_batch` để tìm khóa raw chưa được tham chiếu.
2. **Đổi worker trong khi dọn chỉ mục.** Xác minh lease trước khi ghi tệp dẫn
   xuất, trước khi commit manifest/biên nhận/danh sách dọn, và khi xóa các khóa
   đã ghi nhận. Lỗi lưu trữ giữ biên nhận để chạy tiếp. Lỗi ánh xạ cần xác minh
   được báo qua `purge_index_mapping_unverified`.
3. **Trạng thái phiên bản.** Dùng revision thật của lượt chuẩn bị hoặc bóc tách
   đang chạy. Giữ phân biệt giữa bản còn phục vụ và bản đang chờ lập chỉ mục.
   Khi bản cũ đã thu hồi, bản thay thế thất bại và không còn lượt xử lý,
   `preparing_revision_no` là `null`.

## Kiểm chứng

- Chạy từ root repo. Ruff check và kiểm tra định dạng đạt trên sáu tệp Python
  thuộc phạm vi sửa. `git diff --check` đạt trước khi cập nhật nhật ký.
- Các ca PostgreSQL dùng `backendV1/scripts/test_database.py` với cơ sở dữ liệu
  cô lập và dịch vụ embedding giả lập. Có ca chỉ mục đã/chưa có manifest, lô
  chưa commit, chuyển lease giữa chừng, lỗi lưu trữ rồi tiếp tục, và thu hồi
  bản cũ trong khi bản thay thế thất bại.

### Kết quả thực chạy

- **PASS** — 54 ca trọng tâm, exit 0. Chạy từ root bằng
  `uv run --project backendV1 --frozen --env-file .env python backendV1/scripts/test_database.py tests/unit/test_source_purge_716.py tests/integration/test_source_purge_716.py tests/integration/test_lifecycle_runtime_659.py tests/integration/test_knowledge_summary_api.py -q`.
  Pytest mất 517,42 giây. Biên nhận
  `backendV1/storage/context636/qnu_v1_test_a1d9b7c0101344c1/receipt.json`
  xác nhận DB test đã dọn và sentinel legacy được giữ.
- **PASS** — Ruff check, Ruff format check trên sáu tệp Python sửa, exit 0.
  `git diff --check`, kiểm tra UTF-8 không BOM và LF đạt.
- **PASS** — Ca bổ sung
  `tests/integration/test_preparation_intents.py::test_source_summary_reports_preparation_step_and_stop_action`,
  exit 0, 6,31 giây. Tái hiện trước đó thất bại vì assertion cũ yêu cầu
  `preparing_revision_no=null` ngay khi intent đang queued. Cập nhật contract
  của test để khớp revision của intent và kiểm thêm `null` sau khi hủy. Lượt
  đạt dùng DB `qnu_v1_test_37c117da178341ff`, đã dọn và giữ sentinel. Tổng
  phạm vi trọng tâm là **55 ca đạt** qua hai lượt kiểm chứng.
- **PASS** — Ruff check cho tệp test bổ sung. **FAIL có sẵn** — Ruff format
  check của tệp này. Đã kiểm trên nội dung trước hai assertion vừa sửa bằng
  stdin, formatter vẫn exit 1 ở các đoạn khác. Giữ diff hai assertion theo
  contract.
- **INCOMPLETE** — Lượt full ban đầu
  `qnu_v1_test_d39d7fd7555b41eb` bị ngắt trước kết luận. Sau khi xác nhận
  không còn kết nối, DB test của lượt này đã được dọn. Biên nhận ghi
  `pytest_exit=null`, `interrupted=true`.
- **FAIL / INCOMPLETE** — Full suite sau đó được chia đủ 185 tệp thành tám nhóm,
  mỗi nhóm dùng harness với DB riêng. Nhóm 7 dừng do Python trên Windows báo
  `Windows fatal exception: access violation`, exit 3221225477. Stack lúc
  xảy ra lỗi ở Proactor event loop, khi chạy
  `tests/integration/test_lifecycle_runtime_659.py::test_archive_excludes_evidence_and_restore_preserves_original_index`.
  Các nhóm còn lại được dừng chủ động sau khi lỗi tiến trình làm lượt full
  không thể hoàn tất. Dấu thất bại assertion ở nhóm 1 đã được tái hiện và
  kiểm lại bằng ca preparation summary nêu trên. Không coi lượt full đạt.
  Dấu vết phân nhóm và biên nhận tại
  `backendV1/storage/context636/session917-suite/`. Toàn bộ 54 ca của lượt
  trọng tâm đã hoàn tất trước đó, gồm cả tệp integration này. Cả tám biên
  nhận đều xác nhận DB test đã dọn và sentinel được giữ. Script điều phối
  tạm đã xóa, giữ log, phân nhóm và kết quả.

## Giới hạn kiểm chứng

Kiểm chứng backend qua API, PostgreSQL cô lập và embedding giả lập. Không có
kết quả model thật hoặc kiểm chứng giao diện trong batch này. Mã ứng dụng đã
sửa ba phát hiện, nhưng full suite cần chạy lại trong môi trường ổn định để
chốt kết quả toàn bộ.
