# Phiên 451 — Kiểm thử cẩm nang 2025 mới sau xuất bản

## Mục tiêu và phạm vi

Người dùng đã nạp vector/xuất bản bản cẩm nang đầy đủ, yêu cầu test câu hỏi liên quan. Dùng skill qnu-rag-pipeline và bước đánh giá của qnu-chatbot-builder để kiểm tra nguồn, câu trả lời và citations; clean-code giữ harness nhỏ/phạm vi diagnostic. Không sửa runtime/DB/config/model, không restart/reset/reindex/publish. Giữ nguyên dirty changes các phiên trước.

## Công việc

- Thêm `backend/scripts/evaluate_camnang_451.py`: exact file SHA-256 preflight, snapshot/source/index/Qdrant parity, 20 câu tuần tự hội thoại mới, model usage, lưu từng kết quả; dừng khi lỗi hạ tầng, kiểm tra fingerprint sau test.
- Generated artifacts: `backend/storage/admissions_eval451_preflight.json`, `admissions_eval451_camnang20.json`, `admissions_eval451_verified.json`.
- Review thủ công và DB read-only canonical/selection/facts; tạo `docs/kiem_thu/2026-10-14_test_cam_nang_2025_20_cau.md`, đồng bộ journal index, memory và WORK_LOG.

## Kết quả

Đúng hash e6ddb2c…; nguồn ks_rev_988ea265f24c/index919d97a25b33 active; snapshot6180f8f51b791da886a2/21sources. 1257 retrievable points/parity đạt, 0facts; mục con mất tên ngành trong section, scope proposed:unknown.

20/20 HTTP200, 8supported/3partial/9missing; 0DAG, trung bình24,96s/max34,66s. 99usage success primary gpt-oss120b/fallback gemma4. Span/hash/identity:26canonical+4facts, 0lỗi. Runtime/config/publication không đổi.

Review nội dung chính:6đạt+1từchối an toàn đúng;13cần xử lý, khôngaccuracy/TM08. P1:2001 mượn việc làm Toán ứng dụng cho SPToán;2006 đáp điểmchuẩn thaytổhợp;2108 dùng9440122 sauđạihọc thay7440122 đại học, audit kéo bằng ViệtNamhọc. 2002 thiếu4,5năm;2005 cócitationlớp10–12 nhưng đápđiểmchuẩn;2101/2102/2109/2110/2111 nguồn có mà không trả;2105 córecord đúngnhưng cross-source binding bịchặn.2112/2113 missing, chưa nghiệmthu historical2025cónhãn, chưatraceđủ đểkếtluậnnhánh.2114 từchối100% việc làm đúng, khôngmượn95%SPToán.

## Kiểm tra và giới hạn

Ruff harness451 đạt (fix import order). Khi chốt lại, `python -m ruff` trong venv báo thiếu module; chạy executable Ruff đã cài trên máy, `ruff check scripts/evaluate_camnang_451.py`, đạt. Không sửa mã app nên không chạy full Pytest/Vite; không dùng mock/đápánmẫu. Kiểm tra JSON xác nhận20HTTP200, fingerprintskhôngđổi, verifier0lỗi và6tệpdocsđủ/khôngký tựthaythế. Một lượt20, không full82, không chứng minh stability nhiều lượt hay độ chính xác chung. Bài học: chứng cứ nguyên văn đúng vẫn có thể gắn sai ngành/trình độ/thuộc tính; các lỗi missing cần phân biệt thiếu tài liệu và thiếu selection/binding. Chỉ đề xuất ưu tiên tiếp theo, chưa triển khai fix.
