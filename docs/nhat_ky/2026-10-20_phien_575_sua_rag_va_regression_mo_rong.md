# Phiên575 — Sửa RAG và mở rộng phòng hồi quy

Context575 sửa phạm vi/điều kiện RAG, thêm 67 ca regression; frozen64 59/60 = 98.33%, social 4/4; full 2905 PASS / 18 FAIL / 17 SKIP, không có lỗi pytest mới theo ID/nguyên nhân; Ruff 18 file PASS; biến thể gọi thật 3/4. 8 lỗi gốc đạt, còn N18 và B03; Storage tạm bị policy chặn xóa. Giữ nguồn/model/index/publication; không Git/restart/deploy.

Người dùng yêu cầu sửa theo nguyên nhân và bổ sung ca phòng ngừa. Tái dùng bằng chứng Context574: nội dung nguồn còn đủ, nên không thay parser. Các thay đổi giới hạn ở module RAG và test mới, bảo toàn thay đổi chưa commit khác.

- [Triển khai](../bao_cao/context575/IMPLEMENTATION_REPORT.md)
- [Kiểm chứng và lệnh/evidence](../bao_cao/context575/VALIDATION_REPORT.md)
- [So sánh 64 ID](../bao_cao/context575/CASE_COMPARISON.md)
- [Regression mở rộng](../bao_cao/context575/EXTENDED_TESTS.md)

Lệnh chính: `python -B backend/storage/context575/checks.py run --label full-handoff tests`; `python -B backend/storage/context575/benchmark-handoff/run.py`; `python -B backend/storage/context575/robustness-live/run.py`; `python -m ruff check` với 17 app file trong `final-app-files.json` và test575. Các receipt giữ nguyên exit code và toàn bộ lịch sử, không lấy retry để thay FAIL.

Bước sau: dùng thêm tài liệu và câu hỏi chưa tham gia phát triển để đo độ bao phủ; theo dõi false-abstention/provider timeout. Không tự đổi runtime/config hoặc reindex nguồn để cải thiện điểm.
