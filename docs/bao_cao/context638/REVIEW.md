# Context638 — Rà soát độc lập kho tri thức backendV1

Ngày 2026-10-26. Yêu cầu: xem lại phần triển khai theo prompt collection/upload trực tiếp. Kết luận: **CHANGES REQUESTED**. Không sửa mã ứng dụng để làm test xanh.

## Phát hiện đã tái hiện

### F1 · P1 — Writer thua có thể làm hỏng file đã commit

`SourceService.upload` ghi blob cùng khóa SHA256 trước khi DB chọn người thắng bằng unique constraint (`sources/service.py:102`). LocalBlobStore ghi trực tiếp bằng `path.write_bytes` (`adapters/storage/local.py:27`), không có bước xuất bản file nguyên vẹn sau khi ghi xong.

Repro dùng hai upload cùng bytes/cùng collection đã qua precheck. Writer đầu ghi blob và commit thành công; writer thứ hai đã qua precheck trước commit, sau đó ghi cùng key và gặp lỗi I/O giả lập giữa chừng. Writer thứ hai trả storage_unavailable, nhưng file của nguồn đã commit bị cắt từ53 còn8byte. API tải lại nguồn đầu trả502/blob_integrity_failed. Chặn trùng ở DB không bảo vệ bytes vì ghi file xảy ra trước đó.

Đề nghị: ghi staging/temp hoàn chỉnh, kiểm tra và xuất bản nguyên vẹn theo cơ chế atomic/put-if-absent phù hợp driver; writer lỗi không được chạm bytes đang được revision đã commit tham chiếu. Thêm regression giữ nguyên file thắng khi writer cùng key thất bại. Đây là fault injection trên file tổng hợp trong storage test, không phải mất file nghiệp vụ thật.

### F2 · P2 — Idempotency bỏ qua title

`_request_hash` (`sources/service.py:48`) không nhận title, trong khi tạo nguồn lưu title ở dòng117. POST cùng key/file/filename nhưng đổi title từ Original title sang Different title vẫn HTTP200 và trả Original title, thay vì409/idempotency_conflict theo hợp đồng cùng key khác yêu cầu.

Đề nghị: fingerprint gồm metadata có tác dụng nghiệp vụ sau chuẩn hóa, nhất là title hiệu lực. Quy định rõ title ở endpoint thêm revision: thực sự hỗ trợ hay loại khỏi request. Thêm regression thay title với key cũ; không chỉ thay bytes/filename.

### F3 · P2 — Downgrade báo thành công nhưng chặn upgrade tiếp theo

`0005_knowledge_collections.py:133` downgrade rỗng nên Alembic ghi version0004 dù bốn bảng kb_* vẫn còn. Upgrade head sau đó chạy guard dòng29 và dừng vì bảng đã tồn tại ngoài lịch sử v1. Đã tái hiện bằng lệnh Alembic thật trên DB tạm.

Đề nghị: nếu không được xóa evidence thì từ chối downgrade tường minh trước khi version thay đổi, như policy migration0004; hoặc cung cấp rollback bảo toàn dữ liệu có thể upgrade trở lại. Không xóa dữ liệu để làm test xanh.

## Kiểm chứng

- Suite sẵn có: **104 PASS /0FAIL/0SKIP**,31,24s, exit0. Lệnh `.venv\Scripts\python.exe scripts/run_isolated_tests.py tests -q`, cwd backendV1, DB qnu_v1_test_04a2e2244e044990.
- Ba probe bổ sung độc lập: **3 FAIL /0PASS**,7,81s, exit1; đúng ba nguyên nhân trên, không lỗi fixture. Lệnh tương tự với `storage/context638/review_probes.py -q --tb=short`, DB qnu_v1_test_d32e3cbb1c224465.
- Ruff `check .`: PASS, exit0, không auto-fix.
- Hai DB của lượt review đã dọn, receipt db_dropped=true và legacy_sentinel_preserved=true. Có DB test khác ngoài ownership của lượt này; không đụng/xóa nó. DB phục vụ chưa có version table v1.
- Hash141 file qnu/migration so với đầu review giữ nguyên. Không migrate DB phục vụ, không restart dịch vụ, không sửa source/test suite chính.

Probe, source seal, XML và receipt ở backendV1/storage/context638 và context636, được Git ignore. Chỉ dùng file tổng hợp; không gửi corpus hoặc credential ra provider. Log testcase migration giữ version sai chỉ trong DB review và DB đó đã được xóa.

Các giới hạn đã được Context637 công bố như chưa GC orphan, body limit cần reverse proxy, chưa revert nội dung cũ và chưa OCR không được tính lại như lỗi mới. Khóa ngoại tổ hợp, scope lookup, bytes/checksum và trạng thái stored đã có kiểm thử hữu ích; suite104PASS vẫn chưa bao phủ ba lỗi này.
