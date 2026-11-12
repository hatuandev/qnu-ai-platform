# Phiên 927 — Tiếp tục soát chính tả sau nhóm lỗi

## Phạm vi và nguyên nhân

Người dùng báo tài liệu 32 trang dừng ở 75/600 đoạn. Truy vấn chỉ đọc DB ứng dụng xác nhận lượt tự động dùng Qwen, ba nhóm đầu hoàn tất mỗi nhóm 25 đoạn, nhóm thứ tư thất bại với mã `ocr_spelling_invalid`. Kiểm tra chỉ xác định phản hồi không qua bộ xác thực gợi ý, chưa xác định chính xác gợi ý nào bị loại trong phản hồi thật.

Luồng tự động trước đây dừng toàn tài liệu khi gặp lỗi xác thực ở một nhóm. Giao diện phản ánh đúng phạm vi đã soát.

## Thay đổi

- `backendV1/qnu/domains/ocr/review/automatic.py` tiếp tục các nhóm chưa gửi khi một nhóm trả gợi ý không hợp lệ. Nhóm lỗi không được tính vào phạm vi đã soát. Lượt cuối vẫn báo lỗi và giữ mã lỗi.
- Lỗi token xác định tiếp tục theo cơ chế chia nhóm hiện có. Lỗi quyền, thay đổi nguồn/model, quota và hạ tầng tiếp tục dừng lượt.
- Test qua worker, API và HTTP model giả lập kiểm tra phạm vi sau nhóm lỗi, bảo toàn văn bản, số request và idempotency.
- Cập nhật hợp đồng luồng chính tại `docs/quy_trinh/47_hop_dong_luong_chinh_backend_v1.md`.

## Kiểm chứng

- Trước sửa, regression `test_automatic_review_preserves_coverage_after_batch_error[invalid_suggestion]` thất bại đúng tại danh sách đoạn đã soát. Harness DB cô lập thoát 1, DB được dọn.
- Sau sửa, ba tệp test OCR text review, context review và anchors đạt 40 ca, exit 0 trong 155,55 giây. Harness `qnu_v1_test_f9c10f4d660245ff` xác nhận DB đã dọn và sentinel giữ nguyên.
- Ruff scoped và `git diff --check` đạt.
- Full Pytest được khởi chạy một lượt với `-q --tb=short --maxfail=1`, chủ động dừng vì thời gian chạy tổng hợp vượt phạm vi kiểm chứng trọng tâm. Kết quả INCOMPLETE, không báo PASS. Harness `qnu_v1_test_47f3e6f3a6584a27` ghi exit `4294967295`, thời gian 181,88 giây, DB được dọn và sentinel giữ nguyên.

## Giới hạn và vận hành

Chưa chạy lại tài liệu thật với model sau sửa. Chưa khởi động lại ứng dụng hoặc thay đổi lượt cũ. Bản sửa cần worker nạp lại mã. Lượt lỗi cũ vẫn có độ bao phủ 75/600 và giữ lịch sử.
