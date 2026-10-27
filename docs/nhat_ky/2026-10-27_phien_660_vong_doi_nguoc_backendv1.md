# Context660 — Vòng đời ngược tài liệu và chatbot backendV1

## Yêu cầu và phạm vi

Người dùng yêu cầu bổ sung xử lý ngược: xóa tài liệu cũ, nạp bản mới, dừng/xóa
chatbot và các tài nguyên liên quan. Triển khai riêng backendV1, giữ các sửa đổi
frontend/SSO/skill đồng thời. Context659 thuộc công việc frontend khác; số660 được
giữ qua snapshot riêng. Tệp kiểm thử có hậu tố659 do tạo trước khi phát hiện số đã dùng.

Mặc định xóa vào thùng rác, khôi phục được; giữ nguồn, raw OCR và artifact dẫn xuất
để truy vết theo AGENTS. Không deploy, migrate DB phục vụ, restart, đổi ModelOps
hay xóa tài liệu người dùng. Chỉ dùng corpus tổng hợp và inference HTTP giả lập
trong kiểm thử; PostgreSQL cô lập và Qdrant/Redis cục bộ là hạ tầng thật.

## Thay đổi

- Module lifecycle có model/schema/router/service và các hàm target, guard,
  effects, replacement. Preview gắn actor, workspace, tham số, phạm vi ảnh hưởng,
  hash trạng thái và thời hạn; accept kiểm lại quyền/snapshot, có idempotency/audit.
- Lưu trữ/xóa/khôi phục source, collection, compiled document, assistant và owned
  conversation. Chặn API/tải tệp, tác vụ và retrieval; lịch sử trả lời cũ kiểm lại nguồn.
- Pause/resume giữ revision cấu hình khi chỉ đổi cờ hoạt động. Cancel OCR,
  Compiler, index, review, kiểm chính tả, auto-review và lượt hỏi bằng trạng thái
  cancelled. Kết quả muộn không được hoàn tất; usage đo được vẫn được ghi nhận.
- Source có serving_revision_no riêng. Upload revision staged giữ bản đang phục
  vụ. Phiên bản đã duyệt được chuẩn bị generation mới; transaction cuối chuyển
  serving pointer, publication, index. Lỗi giữ bản cũ; storage retry tái dùng embedding.
- Chặn nguồn dùng chung làm văn bản đang xuất bản khác mất hiệu lực. Thay thế
  một compiled document mỗi action; chưa triển khai batch nhiều document.
- Cleanup chỉ vector/chunk generation ngừng dùng; không chạm namespace/target
  khác. Chỉ mục active không còn tài liệu khả dụng có thể retire trước dọn.
  Intent được lưu trước I/O; lỗi giữ pending, gửi lại cùng key để hoàn tất.
- Migration0015 thêm hai bảng lifecycle, serving pointer và trạng thái cancelled;
  cập nhật ownership/fixture/migration parity và OpenAPI. Giữ 92 path cũ.

## Kiểm chứng và các lỗi đã phát hiện

Kiểm thử viết trước API đã tái hiện404. Sau triển khai, regression phát hiện guard
kho cha chưa được áp ở source detail, đã sửa và giữ assertion. Ca hủy lúc sinh
phát hiện lease của lượt hỏi không cho null, sửa thành thời gian hết hạn.

Full đầu phát hiện hai regression review: bản mới nhất để review bị lẫn với bản
đang phục vụ. Sửa bằng tham số serving riêng cho read_published/publication;
review vẫn theo latest, staged cho phép chuẩn bị riêng. Không bỏ guard hay đổi
assertion để đạt xanh. Lượt full đó còn lỗi teardown TestClient và hai test queue
NOT RUN do chưa cấp TEST_REDIS_URL; không tính lượt đó PASS.

Ca bổ sung hủy auto-review giữa claim và tạo review con tái hiện một request model
thừa; thêm parent-state check dưới khóa workspace trước tạo con, test sau sửa PASS.
Queue được chạy lại trên Redis với queue riêng và dọn đúng key do test tạo.

Các lần full bị ngắt giữ trạng thái chưa nghiệm thu. Lượt đầy đủ chia63file thành
bốn nhóm không trùng, mỗi nhóm DB riêng. Nhóm lỗi chạy lại trọn nhóm; các ca
publication, thay thế, auto-review, queue và cancellation chạy lại sau sửa.

Kết quả cuối và tên database/exit code nằm ở
[verification.json](../bao_cao/context660/verification.json). Chỉ ghi PASS cho test
thực chạy đạt; kết quả lỗi ban đầu được giữ riêng trong receipt.

## Lệnh và bằng chứng

Cwd `backendV1`; Python3.12 trong `.venv/Scripts/python.exe`.

- `storage/context659/run_tests.py <test paths> -q`: wrapper đọc credential hạ tầng
  trong bộ nhớ, dùng scripts/test_database.py tạo DB thử loopback, không sao chép DB
  phục vụ/credential ModelOps. Chạy migration head, giữ sentinel legacy và drop DB thử.
- `storage/context659/full_gate.py`: toàn bộ suite, manifest file/group không trùng.
- `storage/context659/recheck.py`: trọn nhóm lỗi và boundary bị ảnh hưởng sau sửa.
- `storage/context659/quality.py`: Ruff/format trên file thuộc batch, UTF-8/LF,
  OpenAPI giữ route cũ, seal byte475file legacy so với snapshot đầu batch658.
- `storage/context659/cleanup_audit.py`: dọn đúng DB bị ngắt sau kiểm sentinel,
  xác minh/drop vector có tên và target đã lưu trong DB thử; không xóa wildcard.

Script/log/XML nằm trong storage được ignore; không ghi credential hạ tầng/ModelOps thật.
Không đưa raw OCR/prompt, corpus nội bộ hay API key vào nhật ký.

## Bàn giao và giới hạn

[Hợp đồng API](../../backendV1/docs/resource-lifecycle.md) ·
[Quy trình31](../quy_trinh/31_vong_doi_nguoc_backendv1.md).

Chưa chạy inference server AI thật cho batch này, chưa benchmark tải/chất lượng,
chưa UI vòng đời, purge file gốc/dẫn xuất hoặc batch replacement nguồn chung.
Không bảo đảm upstream ngừng tính request đã nhận. Áp migration0015 và khởi động
API/worker mới là bước vận hành riêng trước khi dùng API mới trên môi trường phục vụ.

## Kết quả cuối

Hợp 563 PASS / 0 FAIL / 0 SKIP;23ca mới/0mất so540. Nhóm lỗi chạy lại trọn
nhóm PASS;37ca boundary sau sửa PASS. Ruff/format49file PASS, OpenAPI96path123op
giữ92path cũ;475legacybyte giữ. Cleanup kiểm28tên DB thử,
0DB còn,0vector v1 quan sát sau dọn. Các FAIL/NOT RUN ban đầu giữ trong receipt.
