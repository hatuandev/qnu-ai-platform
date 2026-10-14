# Phiên #439 — Đối soát nguyên nhân thất bại RAG/DAG

## Mục tiêu và phạm vi

Giải thích vì sao câu hỏi có dữ liệu vẫn thất bại sau test #438. Chỉ đọc artifacts và mã xử lý, cập nhật tài liệu. Dùng skill qnu-rag-pipeline để phân tích các bước truy hồi, nguồn/năm, binding và kiểm chứng. Không sửa mã, không gọi model thêm, không đổi DB/config/publication.

## Bằng chứng

- Artifact #435 và #438 cùng publication fingerprint `733f3faf2f247c16e3a2` và revision nguồn.
- Context #438 có nguyên nội dung DQN, 53/56,15/30,83–97/112,3 triệu, học bổng lịch sử và hỗ trợ3.630.000 đồng/tháng.
- Câu9 #438 thiếu PT1–PT5 trong packed context, trong khi #435 lấy được danh sách từ cùng publication.
- Câu25 nhận cả chính sách2025 và2026 trái nhau; không thể xem đó là mâu thuẫn cùng năm.
- Audit nhiều lần viết qualifier quote bằng source revision ID, thêm dấu ba chấm hoặc thay câu thay vì copy nguyên văn. Có audit yêu cầu cộng chỉ tiêu/đợt, danh sách ngành hoặc bảng quy đổi ngoài yêu cầu chính.
- Verification timing trung bình19,81s DAG/19,26s RAG; retrieval1,84s/1,80s (chỉ các lượt có timing).

## Kết luận

Phần lớn các ví dụ đã đối soát không phải thiếu dữ liệu: có lỗi lựa chọn context (câu9), scope (38), temporal (25), lỗi quote/numeric/atomic binding (1/19/80/81/82) và false partial do mở rộng coverage (11/16/66). Cũng có thiếu qualifier thật (6/13/22/48/82); supported chưa phải accuracy. Không thể gán toàn bộ lỗi numeric cho parser số vì artifact không giữ raw proposal cuối của các lượt thiếu claim. URL cụ thể ở75 chưa có trong đoạn chọn, chưa kết luận không có ở toàn corpus.

Đợt audit bổ sung #437 tăng độ nghiêm nhưng tạo nhiều false negative và vòng repair; cần hiệu chỉnh trước nghiệm thu. Không có chứng cứ lỗi chủ yếu do max_tokens5000/context window.

Chi tiết bổ sung trực tiếp trong [báo cáo #438](../kiem_thu/2026-10-14_20_cau_rag_dag_sau_khoi_dong_lai.md).

## Kiểm tra và giới hạn

Không chạy lint/Pytest/build vì không đổi mã. Probe Python đọc DB không chạy được do interpreter `.venv` thiếu `pydantic`; không cài dependency hoặc sửa môi trường. Kết luận nguồn dựa trên artifacts có cùng publication/revision, không tuyên bố đã kiểm tra DB hiện tại. Không kiểm tra pháp lý nguồn ngoài hay chạy đủ82/Ragas.
