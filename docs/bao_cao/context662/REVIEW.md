# Gộp migration backendV1

Đã gộp15revision phát triển thành một baseline `0001_initial_schema`.
Nguồn15file giữ nguyên bytes trong ZIP riêng, không nằm trên graph Alembic.
Hai DB thử từ chuỗi cũ và baseline mới có catalog42bảng khớp column/type/default,
PK/FK/unique/check/index, kể cả predicate index một phần. Kiểm upgrade no-op,
collision không tự nhận bảng, từ chối retired revision và chặn downgrade đều đạt.
Legacy sentinel/version được giữ;475file backend cũ khớp byte snapshot.

Full suite: **565 PASS / 0 FAIL / 0 SKIP**,2ca mới, không mất563ca trước.
Ruff/format4file, UTF-8/LF và ownership manifest đạt. Lượt đối chiếu đầu FAIL do
thứ tự và PostgreSQL viết lại cast biểu thức khi reflect; sửa trình sinh giữ
biểu thức gốc rồi so lại catalog, không bỏ assertion hoặc nới so sánh constraint.

Không áp migration/stamp/restart/deploy DB đang phục vụ. Môi trường còn revision
phát triển cũ phải có chuyển tiếp riêng, không tự stamp baseline. Inference trong
test là giả lập; hạ tầng PostgreSQL/Redis/Qdrant cục bộ thật.

[Receipt](verification.json) · [Hướng dẫn](../../../backendV1/docs/migrations.md).
