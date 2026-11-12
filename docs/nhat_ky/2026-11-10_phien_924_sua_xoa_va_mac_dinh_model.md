# Phiên 924 — Sửa xóa tài liệu, Cài đặt và model của chỉ mục

- FE V2 dùng `id` trả từ lifecycle preview để gửi `preview_id` khi xác nhận xóa. Hộp thoại kiểm tra đúng nguồn và hiển thị lỗi tại chỗ.
- Cài đặt phân biệt thiếu quyền, lỗi tải và dữ liệu đã đồng bộ. Phần tài khoản chỉ hiển thị thông tin từ phiên đã xác thực. Danh sách model loại các lựa chọn có kết nối cha thiếu hoặc đã tắt.
- Migration `0021_index_system_embedding` ghi nhận generation được tạo bằng quyền mặc định hệ thống. Quyền này chỉ dùng với generation đang chờ, đang chạy hoặc đang phục vụ, trong đúng workspace và provider. Kiểm tra được áp dụng ở lúc phân giải model, giữ chỗ sử dụng và cấp khóa. Quyền workspace, trạng thái provider và đối chiếu cấu hình vẫn được kiểm tra.
- Với generation có trước migration, chỉ ghi nhận các lượt đủ điều kiện đang dùng đúng model mặc định tại thời điểm nâng cấp. Các lượt dùng model đã đổi trước thời điểm đó không có thêm quyền ngầm.

## Kiểm chứng

- Tái hiện trước sửa bằng harness PostgreSQL cô lập. Ca đổi mặc định Embedding làm tác vụ chỉ mục thất bại với `provider_not_found`. Sau khi sửa, cùng ca đạt và kiểm tra lần tạo mới dùng model mới, yêu cầu tự chọn model cũ bị từ chối.
- Từ `frontendV2`, `node --test tests/studio-browser.mjs tests/default-models.test.ts` đạt 23/23. `npm run build` và Biome trên các tệp sửa đều thoát 0.
- Từ `backendV1`, Ruff trên các tệp sửa thoát 0. Harness `scripts/run_isolated_tests.py` chạy nhóm kiểm tra migration, quyền, Embedding và index với 10 ca đạt, 16 ca ngoài phạm vi lọc, thoát 0. DB kiểm thử đã được dọn sau khi chạy.
- Cùng harness, `tests/integration/test_source_purge_716.py -k 'unpublished_purge_is_durable_irreversible_and_keeps_other_uploads or published_source_delete_withdraws_before_background_cleanup'` đạt 2 ca, 14 ca ngoài phạm vi lọc, thoát 0. Đã kiểm thu hồi bản phát hành, dọn nền và giữ tài liệu khác.
- Full gate `scripts/run_isolated_tests.py tests -x -q --tb=short --show-capture=no` đã khởi chạy trên DB cô lập. Chưa có kết quả cuối tại thời điểm bàn giao.
- Chưa áp migration hoặc chạy thao tác xóa trên dữ liệu ứng dụng. Kiểm thử dùng PostgreSQL/Qdrant local và provider giả lập.
