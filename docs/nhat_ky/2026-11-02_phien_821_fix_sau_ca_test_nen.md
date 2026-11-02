# Phiên 821 — Sửa sáu ca test nền để chốt V1

## Yêu cầu và giới hạn

Người dùng yêu cầu sửa sáu ca lỗi nền, kiểm tra lại và dọn cache/tệp tạm trước
khi tự chạy app rồi cân nhắc demo trên server. Không có yêu cầu deploy, Git
commit/push, reset E2E hay xóa backend/frontend cũ. Giữ thay đổi815–820.
Áp dụng skill clean-code và backend-architect; không thay quy trình nghiệp vụ.

## Sáu sửa đổi

1. Unit purge716: cung cấp `actor_id` xác thực trong fixture; giữ nguyên kiểm tra
   publication xuất hiện sau preview và assert không gọi prepare/xóa.
2. Lifecycle659: kiểm rõ platform actor thiếu workspace membership bị404;
   sau đó thêm membership admin qua API và tiếp tục kiểm actor-bound preview,
   stale state. Không bỏ guard của background actor.
3. Compiler654: kiểm đúng metadata ở immutable input snapshot đã kiểm hash và
   CompilationInput DB, gắn với bản sửa đã chọn thay vì bản mới hơn. Vẫn assert
   nội dung thực gửi model, citation đúng text_version và OCR gốc không đổi.
4. Migration639: dùng `SCHEMA_HEAD`, giữ failed downgrade, version không bị đổi,
   upgrade lại và bytes nguồn còn nguyên.
5. Migration schema: đối chiếu đồng thời head DB, Alembic ScriptDirectory và
   `SCHEMA_HEAD`; giữ so schema/ORM và sentinel legacy nguyên vẹn.
6. Integration purge716: gửi `collection_id` cho API danh sách; kiểm HTTP200 rồi
   danh sách rỗng. Giữ toàn bộ assert xóa bytes đúng, nguồn khác còn và không thể
   restore nguồn đã purge.

Chỉ sửa sáu file test; mã ứng dụng và cấu hình đang chạy không đổi trong821.

## Kiểm chứng

Regression trước sửa: bảy FAIL trong1.285ca của820; một ca phục hồi là lỗi loop
Windows, kiểm riêng Proactor đã PASS. Sáu FAIL còn lại đều tái hiện trên HEAD sạch.

- Focused: chín ca (sáu ca cần sửa và ca bảo vệ lân cận) PASS,25,07s,exit0;
  không sửa quyền hay assertion để chỉ làm xanh, không retry inference thật.
- Ruff sáu file test: PASS; UTF-8 không BOM/LF và git diff --check PASS.
- Full backend: **1.285/1.285 PASS, 0 FAIL, 0 ERROR, 0 SKIP**, exit0;
  wall1.068,86s (17 phút49s). Bốn nhóm771/330/180/4 đều exit0;
  sentinel legacy nguyên vẹn, database riêng còn0; tập node collector/JUnit khớp chính xác.

Full collector/JUnit phải khớp tập node chính xác, không thiếu/thừa/trùng. Chia
file thành ba nhóm TCP và một nhóm phục hồi dùng Proactor Windows. Mỗi nhóm có
DB/cache/queue/storage riêng, bảng legacy/sentinel đúng harness chuẩn. Provider
regression là loopback giả lập; chặn mọi kết nối ngoài loopback. Không OCR/compiler
với model thật trong821. Giữ kết quả/error820 riêng, không ghi đè.

Lệnh tại root: `backendV1/.venv/Scripts/python.exe tmp/fix821/focused.py`,
`backendV1/.venv/Scripts/python.exe tmp/fix821/run.py`. Tiến trình Pytest cwd
backendV1, `-v --tb=short`, JUnit/basetemp riêng. Artifact `tmp/fix821`.

## Dọn dẹp và bàn giao

Đã xác nhận database của lượt focused và bốn nhóm full không còn (remaining=0).
Lập danh sách ba thư mục cache sinh tự động, không được Git theo dõi:
`.pytest_cache`, `backendV1/.pytest_cache`, `backendV1/.ruff_cache` (preview28file,
235.213byte trước full). Lệnh xóa cache bị automatic approval review từ chối:
`blocked by policy`. Không hỏi lại quyền hoặc đổi công cụ để vượt chặn; không có
thao tác xóa filesystem nào thực hiện. Ba thư mục vẫn giữ nguyên.

Đọc lại Redis của test: còn2key trong namespace riêng của lượt821, TTL=-1;
chưa xóa và không flush Redis. Chỉ ghi số lượng/trạng thái, không xuất nội dung
cache hoặc secret. Đây là phần dọn dẹp còn lại, không gọi toàn bộ cleanup PASS.
Receipt `tmp/fix821/cleanup-status.json` lưu rõ việc chặn và phần chưa dọn.

Giữ báo cáo/JUnit, ảnh/PDF/DOCX/OCR, corpus, key ModelOps, dữ liệu test E2E,
node_modules, virtualenv và lịch sử phiên bản. Không flush Redis chung, không
xóa workspace/worktree cũ, không restart API/worker chính, không deploy/push.

FE700/700 và47check model thật là kết quả819, không chạy lại trong821 vì không
sửa frontend và không cần gọi lại upstream chỉ để sửa fixture. Chốt backend
regression không thay cho việc người dùng chạy UI và nguồn thật trước demo.

Hướng dẫn app: [Chạy QNU V1](../quy_trinh/38_huong_dan_chay_qnu_v1.md).
Từ root, người dùng có thể chủ động chạy `.\make.ps1 v1-check` rồi
`.\make.ps1 v1-dev` sau khi đã dừng đúng phiên cũ. Không cần cleanup/init E2E
để dùng app chính. Hướng dẫn này được đọc từ repo, không tự chạy app trong821.
