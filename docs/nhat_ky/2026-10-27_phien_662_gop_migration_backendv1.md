# Context662 — Gộp migration khởi tạo backendV1

## Phạm vi được đồng ý

Người dùng đồng ý đề xuất gộp15migration phát triển backendV1 thành một migration
khởi tạo. Kiểm tra trước đó cho thấy DB cục bộ `qnu_ai_platform` không có bảng v1
hoặc `alembic_version_backendv1`; DB mặc định `qnu_backend_v1` chưa tồn tại.
Không suy kết luận đó sang server khác. Chỉ sửa mã/migration/docs và DB thử riêng;
không áp migration hoặc stamp/restart/deploy môi trường đang phục vụ.

## Thay đổi

- Thư mục `backendV1/alembic/versions/` còn một revision `0001_initial_schema`,
  root không có dependency. Schema đầy đủ đến `0015_resource_lifecycle` trước đó.
-15file cũ được lưu nguyên bytes trong
  `backendV1/alembic/archive/0001-0015_20261027.zip`; kiểm hash từng file và ZIP.
  Archive ngoài `versions`, không được Alembic nạp và không chứa dữ liệu/secret.
- Baseline dùng90câu DDL cố định cho42bảng; không import model app khi chạy.
  Trình sinh chỉ dùng model expressions một lần để giữ biểu thức constraint và
  partial-index ban đầu, tránh PostgreSQL viết lại cast khác cấu trúc khi reflect.
- Kiểm trùng toàn bộ tên bảng v1 trước DDL; không tự nhận schema có sẵn. Bảng
  version riêng và khóa migration giữ nguyên. Downgrade bị từ chối để giữ evidence.
- Cập nhật migration parity test sang revision mới; regression downgrade dùng
  `base`, vẫn yêu cầu từ chối thật và giữ revision/file gốc sau upgrade lại.
- Bổ sung unit test một baseline và xuất SQL offline; cập nhật README, hướng dẫn
  migration, ownership, ADR và tài liệu chức năng. Giữ số revision trong nhật ký
  và báo cáo lịch sử. Ownership YAML bổ sung hai bảng lifecycle đã có trong code.

## Phương pháp và lỗi đã phát hiện

Tạo PostgreSQL thử riêng chạy đủ15revision cũ, reflect schema rồi sinh baseline.
Tạo DB thử thứ hai bằng baseline và đối chiếu column/type/default/nullability,
PK/FK/unique/check/index. Bản sinh ban đầu có SQL cast mảng được PostgreSQL viết
lại khác dạng catalog khi reflect rồi phát DDL; hai lượt so sánh đầu FAIL, không
bỏ assertion. Sửa trình sinh để giữ biểu thức gốc rồi đối chiếu catalog lại:
42bảng khớp hoàn toàn. Baseline vẫn chứa literal SQL, không phụ thuộc model sau này.

Unit regression trước sửa FAIL vì còn15revision; sau sửa2PASS. Kiểm chứng DB
riêng đạt: schema cũ/mới bằng nhau; upgrade lặp no-op; collision dừng và giữ row
sentinel; downgrade dừng và giữ version; DB ở revision cũ bị từ chối chuyển ngầm.
Sentinel và `alembic_version` của backend cũ được giữ ở mọi DB đối chiếu.

## Lệnh kiểm chứng

Cwd `backendV1`, Python3.12 `.venv/Scripts/python.exe`.

- `-m pytest tests/unit/test_migration_baseline_661.py -q`: kiểm graph/SQL offline.
- `storage/context661/compact.py`, `regenerate.py`, `verify.py`: tạo DB thử sở hữu
  riêng, chạy chuỗi cũ/baseline, so catalog, kiểm collision/no-op/downgrade/retired
  revision, giữ hash source và dọn DB thử trong finally. Không reset DB phục vụ.
- `storage/context661/full_gate.py`: manifest toàn suite thành nhóm không trùng;
  mỗi nhóm có DB thử riêng qua harness hiện có; provider HTTP tổng hợp,
  PostgreSQL/Redis/Qdrant cục bộ thật. Không gọi AI server thật.
- Ruff/format có phạm vi, UTF-8/LF/link và kiểm archive; không auto-fix toàn repo.

Kết quả cuối và giới hạn ghi trong
[báo cáo](../bao_cao/context662/REVIEW.md) và
[receipt](../bao_cao/context662/verification.json). Các FAIL ban đầu không tính PASS.

## Bàn giao

DB mới dùng `alembic upgrade head`, kết quả `0001_initial_schema`. Những thay đổi
schema tiếp theo tạo revision mới, bắt đầu `0002_...`. DB đang ở revision phát
triển cũ phải có kế hoạch chuyển tiếp riêng sau đối chiếu/backup, không `stamp
head` hoặc xóa version table để bỏ qua. Baseline không thực hiện chuyển dữ liệu.

[Hướng dẫn migration](../../backendV1/docs/migrations.md).

## Kết quả cuối

Full 565 PASS / 0 FAIL / 0 SKIP;2mới/0mất so563. Ruff/format4file,
UTF-8/LF/ownership/archive PASS.42bảng catalog khớp; collision/retired revision/
downgrade/no-op/legacy sentinel PASS.475legacybyte giữ;0DB thử còn trong receipt,
0collection vector v1 quan sát sau cleanup. Chưa áp DB phục vụ.
