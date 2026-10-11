# Phiên #343 — Sửa DAG join và dữ liệu theo dây nối

## Mục tiêu và ranh giới

Xử lý điểm 1 và 2 của review #342 theo chấp thuận của người dùng. Không sửa OCR Studio đang được triển khai song song, qnu-sso, credentials, migrations hoặc reset DB; không chủ động restart API/worker. Những findings scope/provider/fallback còn lại của #342 chưa được xử lý trong phiên này.

## Thay đổi

- `backend/app/modules/workflows/engine.py`: join chờ cả tiền nhiệm còn có thể tới từ các node đang pending, không chỉ tiền nhiệm đã active. Duyệt đồ thị với tập visited; không chờ nhánh đã bị conditional loại. Lưu selected edges và pending frontier trong checkpoint để resume sau phê duyệt vẫn chờ đúng nhánh. Thiếu source port hoặc trùng explicit target port báo lỗi, không âm thầm bỏ dữ liệu.
- `backend/app/modules/workflows/nodes/base.py`: context giữ payload upstream đã được chọn để bảo toàn metadata cùng nguồn.
- `backend/app/modules/workflows/nodes/routed_inputs.py`: đọc payload/text theo cổng, kiểm tra đầu vào; chỉ giữ fallback cho workflow legacy/control không có cổng văn bản. Metadata citations/context/status đi cùng nguồn được nối, không lấy kết quả toàn cục của nhánh khác.
- Các handlers `llm_generate_node.py`, `rag_answer_node.py`, `query_rewrite_node.py`, `condition_route_node.py`, `citation_guard_node.py`, `output_chat_node.py`: tiêu thụ routed inputs; guard/output sử dụng bằng chứng của câu trả lời được nối. LLM thêm alias `response` tương thích manifest hiện có.
- `backend/tests/test_dag_routing_regression.py`: 12 regression tests, gồm nhánh lệch độ sâu, conditional, HITL resume, RAG/LLM wired text, cổng thiếu/sai/trùng, cô lập citations và metadata nguồn.

## Kiểm chứng

- Theo skill backend và clean-code, viết 4 test tái hiện trước khi sửa: cả 4 thất bại đúng lỗi cần xử lý.
- Sau sửa: bộ DAG/workflows/HITL/citation guard **45 passed**. Các lời gọi inference trong unit tests được thay thế có kiểm soát; đây không phải bằng chứng kết nối AI server hay E2E.
- Ruff phạm vi workflows và test mới đạt; Ruff toàn backend exit 0 nhưng có cảnh báo quyền truy cập một số thư mục.
- Full backend cuối cùng: **794 passed, 9 failed, 2 skipped, 5 errors**. Chín failures thuộc publishing/legacy auth/reconciliation/workers, cùng nhóm đã ghi nhận ở #340; năm setup errors thuộc fixture thư mục tạm Windows. Đổi basetemp riêng không giải quyết được các setup errors. Không tuyên bố toàn suite đạt.
- Không thay đổi frontend nên không chạy Vite build. Chưa chạy browser/chatbot DAG E2E sau sửa để tránh can thiệp runtime trong lúc OCR đang triển khai.

## Bài học và bước tiếp

Activation không đủ làm tiêu chí join: cần xét các tiền nhiệm vẫn có thể được kích hoạt từ frontier. Routing nội dung phải mang theo provenance/bằng chứng, không chỉ đổi câu hỏi hoặc answer text. Khi OCR hoàn tất, chạy lại luồng chatbot/DAG thực tế, gồm nhánh song song và pause/resume; giải quyết các findings còn lại của #342 ở phạm vi riêng.
