# Hoàn thiện bốn phần backendV1

Đã triển khai human review gate, dọn dẫn xuất mồ côi, recovery vào đích mới và
readiness/worker heartbeat. Phạm vi chỉ backendV1 và môi trường thử riêng.

## Kết quả

- **604 PASS / 0 FAIL / 0 SKIP** trong hợp kiểm chứng cuối, **29 mới / 0 mất** so
  575 ca trước. Ba nhóm full mặc định đạt 453 ca; nhóm TCP/Redis chạy lại với
  Selector đạt149; boundary CLI và readiness/quota bổ sung hai ca mới, dedupe ID.
- Lượt full đầu **FAIL/INCOMPLETE**, một nhóm148 bodies đạt nhưng TestClient kẹt
  Windows Proactor.close trước JUnit. Lặp cùng nhóm tái hiện. Dừng đúng child
  pytest, parent harness dọn DB; không coi body summary là full PASS. Cờ test-only
  `QNU_TEST_WINDOWS_SELECTOR_LOOP=true` giúp nhóm TCP/Redis kết thúc. Các assertion,
  service/SQL/model boundaries giữ; production loop không đổi. Recovery async
  subprocess vẫn được kiểm trên Proactor mặc định. Root cause Windows còn mở.
- Ruff/format **37 file** đạt; UTF-8/LF/link kiểm ở bước kết thúc.
  Head0002, 43 bảng, OpenAPI101path/128operation, path cũ giữ. 475 file backend cũ
  và nguồn baseline/archive giữ nguyên hash.
- API HTTP thật + token dev riêng + PostgreSQL/Redis/ARQ/Local/Qdrant thật: PDF
  2 trang qua Nemotron → Qwen Compiler → auto-review → duyệt thử theo phạm vi đã
  cho phép → BGE-M3 index → hybrid/rerank answer5nguồn/4413token. Restore18 tệp và
  query embedding thật trả5hit. Đây không phải phê duyệt chất lượng/ngữ nghĩa.
- MinIO thật giữ object mới khi ETag đổi và xóa có điều kiện thành công; bucket
  thử đã dọn. DB/vector thử kiểm lại qua receipt, không dọn tài nguyên ngoài scope.

## Hành vi và bằng chứng

1. Review completed phải khớp input/draft/bundle, report hash và latest review;
   con người xác nhận, giải trình đủ findings. Không tự khai fixed trên hash cũ.
   Preview và approval receipt ghim ack; publish/replacement kiểm lại. Không tự
   duyệt từ verdict model hoặc tự sửa/xóa báo cáo gốc.
2. GC admin có preview/accept/key/audit, tuổi tối thiểu24h, terminal owner và
   references toàn workspace. Giữ nguồn/raw/backup/namespace chưa biết. Intent
   pending trước I/O và conditional delete chống thay bytes sau preview.
3. Bundle recovery mã hóa/xác thực dữ liệu đủ43 bảng v1 và tệp được tham chiếu;
   master key ngoài bundle. Restore chỉ DB mới/kho trống, không SQL từ archive,
   kiểm metadata/bytes/vector, remap **cả generation inactive** để cleanup bản
   phục hồi không xóa index nguồn. CLI xác thực token quản trị thật.
4. Readiness quan sát DB/schema, Redis, worker đúng queue, Qdrant, storage và
   ModelOps/capacity; quota thiếu/0/blocked không thành ready, unlimited phải
   được cấu hình tường minh. GET không tự tuyên bố live inference verified.

Regressions trước sửa gồm thiếu ack, S3 nuốt503, namespace inactive sau restore
và CLI headless bỏ sót model assistant. Các lỗi fixture (thiếu đối số job_union,
DTO không lộ vector collection, fixture publication cũ thiếu ack, quota probe
thiếu default OCR) được ghi riêng trong nhật ký; không tính là bằng chứng lỗi
sản phẩm hoặc sửa assertion để xanh.

## Giới hạn/bàn giao

Chưa áp migration0002 hoặc restart/deploy phục vụ. Client duyệt cần gửi review_ack;
bản approved theo hợp đồng cũ cần thu hồi/duyệt lại trước publish/replace tiếp.
Không purge nguồn gốc, batch replacement hoặc tự bật lại job/worker sau restore.
CLI restore hiện có target local; service dùng port S3, adapter conditional-delete
đã thử MinIO. Bundle512MiB/10kobject/100krow mỗi bảng; không phải DR legacy/full
cluster. SSO QNU thật và benchmark ngữ nghĩa NOT RUN; dev smoke không chứng minh
production authentication. Thử thực tế không thay quyết định duyệt nội dung phục vụ.

[Receipt](verification.json) · [Runtime](runtime-results.json) ·
[Nhật ký](../../nhat_ky/2026-10-27_phien_666_duyet_gc_recovery_va_readiness_backendv1.md) ·
[Quy trình](../../quy_trinh/32_duyet_don_du_lieu_va_phuc_hoi_backendv1.md) ·
[Recovery](../../../backendV1/docs/recovery.md) · [Readiness](../../../backendV1/docs/readiness.md).
