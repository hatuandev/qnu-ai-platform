# Phiên 626 — Thử cx/gpt-6-luna và tiếp tục compiler

Ngày 2026-10-24. User yêu cầu dùng `cx/gpt-6-luna` thử lại bước chưa thực hiện được. Giữ ba nguồn, Quality Gate, timeout request 30 giây, thinking medium; không đổi defaults toàn app.

Retry 86 PASS JSON/materialization trong 15,734 giây, 6 assertion/6 entity; review 87 đánh giá 6/6 supported. Chạy tiếp 87–123 bằng model mới, tổng Context626 38 phản hồi stop/0 fallback. Bundle cuối 58 assertion/9 section/1 relation, lưu/đọc mới/idempotency đạt; **needs_attention, chưa APPROVED**. Các mốc 5.948/2024, 5.081 nhập học/2025 và 5.173/2026 đúng nguồn/năm.

Đổi cấu hình làm đổi ID namespace: lần tiếp tục đầu bị chặn ở 35, 0 call mới. Test adapter ánh xạ một-một bằng transport hiện có và kiểm request wire tương đương; replay 1–86 đạt, 3 ca âm namespace và 4 ca âm receipt/recovery đạt. Có 30 request ánh xạ có provenance/audit; không sửa app hoặc checkpoint cũ, không giả model mới tạo các candidate cũ. Ranh giới production không đổi.

Còn 6/14 packet chưa complete; 4 section unresolved; điều kiện PT1/PT4, nhãn 17/40, vai trò năm, header/cột và coverage chưa đủ; relation 4.500→5.173 đảo chiều so với source. Independent acceptance FAIL/exit 1 đúng. Không sửa các vấn đề này trong phạm vi thử model.

Lệnh thực từ repo root:

```text
backend/.venv/Scripts/python.exe .antigravity-bridge/validation/context626_retry_stage86.py
backend/.venv/Scripts/python.exe .antigravity-bridge/validation/context626_retry_stage86.py --execute
backend/.venv/Scripts/python.exe .antigravity-bridge/validation/context626_continue.py --execute
backend/.venv/Scripts/python.exe .antigravity-bridge/validation/context626_diagnose_replay.py
backend/.venv/Scripts/python.exe .antigravity-bridge/validation/context626_diagnose_replay.py --allow-namespace
backend/.venv/Scripts/python.exe .antigravity-bridge/validation/context626_continue2.py --execute
backend/.venv/Scripts/python.exe .antigravity-bridge/validation/context626_review2.py
```

Preflight/retry/continuation cuối/replay cuối exit 0; continuation đầu exit 1/0 inference; acceptance review exit 1. Bản thử ánh xạ đầu bị guard chặn trước khi triển khai ánh xạ đã kiểm chứng; kết quả cuối và negative probes được lưu riêng. Môi trường hạn chế ban đầu không qua import/preflight, được dừng trước khi có intent; lần chạy có quyền truy cập local đã hoàn tất. Không có automatic approval rejection.

Hash toàn bộ app và shared seals giữ. Không tạo DB mới; acceptance DB/Storage cũ giữ để đối soát, không bypass xóa. Không full/64/reindex/publish/restart/commit/push. Full Context625 là kết quả lịch sử FAIL với 18 lỗi nền. [Báo cáo đầy đủ](../bao_cao/context626/REVIEW.md).
