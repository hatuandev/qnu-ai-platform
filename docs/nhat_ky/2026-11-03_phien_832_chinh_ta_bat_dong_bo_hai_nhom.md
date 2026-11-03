# Phiên832 — Chính tả bất đồng bộ hai nhóm

## Yêu cầu và phương pháp

User xác nhận hai Qwen độc lập trên hai GPU, mỗi instance parallel1 và yêu cầu áp
dụng thử xử lý bất đồng bộ. Theo skill frontend/clean code, chỉ sửa điều phối FE;
không sửa cấu hình inference, reasoning, server/router, quota hay workflow duyệt.
Kiểm tra readonly DB trước sửa: spelling_running=0, unexpired_running=0.

`checkWholeDocument` dùng hai slot async, cùng hàng đợi chỉ số; mỗi slot tự lấy
nhóm tiếp theo sau khi hoàn tất. Không chờ cả cặp. Giới hạn mặc định2 **mỗi lượt**;
không phải semaphore toàn server/nhiều tab. Helper có lựa chọn1 để kiểm regression
tuần tự; UI dùng mặc định2. Giữ thứ tự báo cáo và mapping nguồn dù phản hồi đảo thứ tự.

Giữ version/hash/model request/idempotency từng nhóm và không retry. Lỗi cần dừng
toàn lượt/stop/scope/session/unmount chặn nhóm chưa gửi; chờ đủ các request đang
chạy, lưu trạng thái thật thay vì bỏ kết quả. Phần chưa gửi là not_run. Tiến độ
hiển thị số nhóm active và đủ trang, nút dừng nói rõ chờ các nhóm hiện tại.

## File và kiểm chứng

- Logic: `frontendV1/src/features/knowledge/ocr-spelling-batch.ts`.
- Progress: `document-spelling-report.tsx` cùng thư mục.
- Tests: concurrency832, progress832 mới; planner831 giữ regression serial rõ ràng,
  scope831 đổi fixture3trang để kiểm2inflight và1unsent. Quy trình27 cập nhật.

Các lệnh ở frontendV1:

1. Trước sửa, concurrency832 **5FAIL/exit1**, đúng vì chỉ gửi1request.
2. Sau sửa, focused4file **37PASS/exit0**: hai slot, bù việc độc lập, out-of-order,
   stop/quota/uncertain/source conflict, drain2active, không retry, scope/session.
3. Full `npm exec -- vitest run`: **729PASS/85file,0FAIL, exit0**,70,29s.
4. `npm run build`: **PASS/exit0**, Vite+TypeScript; cảnh báo chunk>500KB giữ nguyên.
5. Biome6file sửa/thêm: **PASS/exit0**. `git diff --check`: PASS.
6. Browser desktop1365/mobile390 trên app thật, intercept riêng check POST bằng
   fixture kiểm soát: thấy2active, bấmstop, drain2, không gửi nhóm3, có báo cáo
   chưa kiểm xong và0pageerrors. Không ghi backend trong thí nghiệm UI này.
   Harness ban đầu chờ mọi animation nên treo ở spinner vô hạn; dừng hai lượt
   harness, sửa chỉ chờ animation hữu hạn rồi đạt. Không retry model vì ca UI mock.

## Mẫu API/model thật — một lần, không retry

Playwright dùng module app hiện hành + v1Client đang đăng nhập; đọc review mới nhất
qua server rồi chọn1đoạn có chữ100–1.000ký tự từ mỗi trang1/2. Dùng version/hash
thật, model Chat mặc định ModelOps, không chép key hoặc source text ra log.

- 2nhóm/2đoạn, **2completed/0failed/0uncertain**; không apply/save.
- HTTP inflight peak2; bắt đầu1ms và3ms, kết thúc16.280ms và10.378ms, tổng16,280s.
- CheckIDs `spl_593192eceb5e`, `spl_03064ab7fc32`, mỗi check0suggestion/withheld.
- Chỉ chứng minh app/API có overlap và upstream hoàn tất; không có baseline serial
  cùng tải, không xác nhận router đưa đúng mỗi GPU, không kết luận OCR hết lỗi hay
  cả32trang nhanh gấp đôi. Không chạy lại474đoạn của tài liệu.

Artifact local: tmp/spelling832-before.log, focused.log, full.log, build.log,
biome.log (đều prefix spelling832-), live.json, browser.json, active-*.png.

## Giới hạn

NOT RUN: full32trang model thật/benchmark tốc độ, backendfull vì server không đổi.
Điều phối vẫn trong trình duyệt, cần giữ màn hình mở. Không tự phục hồi sau reload.
Giữ thay đổi829–831; không restart, đổi model/quota, compiler, publish/reindex/push.
