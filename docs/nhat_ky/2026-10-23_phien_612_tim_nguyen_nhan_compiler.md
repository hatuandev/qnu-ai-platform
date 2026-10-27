# Phiên 612 — Tìm nguyên nhân compiler chưa tổng hợp

## Yêu cầu và phạm vi

Người dùng yêu cầu xác định nguyên nhân compiler không tổng hợp được. Chỉ đọc mã, diff, checkpoint và canonical đã lưu; áp dụng skill mã sạch/backend. Không sửa app, gọi model, kết nối DB/MinIO/Qdrant, đổi nguồn/Quality Gate, reindex, xuất bản hoặc Git sync.

## Kết quả

- Tái hiện đúng lỗi tổng: 92 thực thể / 145 assertion vượt 64/128, dù từng phần tử hợp lệ schema. Hai mươi hai đầu ra PacketDraft cộng đúng tổng; một nguồn riêng đã có 70 thực thể.
- Mã kiểm draft tổng tại dòng 440 trước batching dòng 442; cuối luồng dòng 471 và binding vẫn dùng cùng hợp đồng tổng. Đây là điểm chặn thực trước khi synthesis được gọi.
- Phát hiện thêm điểm chặn ngoại tuyến: synthesis planner cộng 5.000 dự phòng ngoài đầu ra 8.192; bốn request đơn lẻ bị chặn, dù request ban đầu đều vừa 24K. Trường hợp lớn nhất 20.839 → 25.839. Không sửa hoặc bỏ guard.
- Service bọc ValidationError thành HTTP502 / uncertain / generic failure, làm khó nhận diện lỗi dung lượng xác định.
- Có 74 tên khác nhau, một thực thể không được dùng; gộp tên hoặc dọn orphan không giải quyết được. Chưa chứng nhận ngữ nghĩa các ứng viên.

## Kiểm chứng thực chạy

Từ root, `backend/.venv/Scripts/python.exe .antigravity-bridge/validation/context612_diagnose.py`, exit0, D01–D12 PASS cho chẩn đoán; compiler vẫn FAIL được tái hiện. Đối soát raw DOCX/canonical 381proof, schema/boundary controls, AST thứ tự gọi, tổng packet, planner và 145 request. Artifact mới trong `backend/storage/context612`; source/corpus cũ không ghi lại.

Probe cuối không có network attempt. App Python, JSON Context611 và ba DOCX giữ hash. Một lệnh xem shape ban đầu gặp lỗi console cp1252; đã sửa cấu hình stdout trong helper riêng và chạy kiểm chứng cuối thành công. Không sửa encoding nguồn. Một lần import thăm dò trước probe cuối có khởi tạo client tương thích; socket đã bị chặn, không có kết nối thành công. Harness cuối tránh package export có side effect và không thử network.

Không đổi app nên không chạy Ruff/full Pytest, API/LLM live, benchmark hoặc browser E2E: NOT RUN. Không tạo dữ liệu DB nên không có DB thử để dọn; Storage cũ giữ nguyên. Kết quả full611 là lịch sử, vẫn FAIL18nền.

## Bàn giao

[Báo cáo nguyên nhân](../bao_cao/context612/ROOT_CAUSE_REPORT.md). Hướng sửa: manifest tổng và nhóm có ranh giới bằng chứng; ngân sách riêng từng request; lỗi capacity rõ ràng; đối soát relevance trước inference mới. Chưa triển khai sửa hoặc tuyên bố APPROVED.
