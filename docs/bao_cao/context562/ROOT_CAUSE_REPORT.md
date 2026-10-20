# Context562 — Nguyên nhân và phạm vi

Ngày kiểm tra: 2026-10-20. Prompt gốc mang số Context559; dùng số 562 để bảo toàn các phiên 559–561 đã có. Người dùng cho triển khai prompt cùng các bổ sung đã thống nhất.

## Vì sao “xin chào” bị từ chối

`RAGService._ask_conversation` trước đây gọi `resolve_followup`, rồi chuyển mọi câu không phải thao tác hội thoại sang `_ask`. Khi chưa có lịch sử, lời chào đi thẳng tới tìm kiếm/bằng chứng. Không có nguồn chứng minh lời chào nên hệ thống dùng phản hồi thiếu căn cứ. Đây là thiếu bước phân luồng hội thoại, không phải bằng chứng cần nạp thêm tài liệu.

Đã viết 7 regression tái hiện trước sửa, gồm cả mixed intent và trạng thái SSE. Lượt `red` có 7 FAIL, exit 1. Sau sửa, lời chào/cảm ơn dùng tên và phạm vi cấu hình trợ lý, không gọi model, embedding, reranker hoặc retrieval.

## Những khoảng hở được kiểm tra cùng luồng

- Lịch sử trước đây lấy một cửa sổ tin nhắn vật lý; nhiều lời cảm ơn có thể làm mất chủ đề hữu ích. Cửa sổ mới giữ các lượt kiến thức, kiểm tra đúng trợ lý và thời điểm cấu hình.
- Biết conversation ID không phải bằng chứng sở hữu. Regression handler với DB test tái hiện một client khác nối vào phiên; đã bổ sung continuation capability gắn đúng trợ lý/phiên, chữ ký tách miền khỏi token đăng nhập.
- Trên trang chat công khai, chọn đoạn chat khác trước đây chỉ đổi các bong bóng hiển thị. Nay khôi phục cả phiên server thuộc đoạn chat đó; lịch sử cũ chưa có capability bắt đầu phiên server mới, không tiếp tục bằng phiên của đoạn chat đang mở trước đó.
- Giao diện loading trước đây nói đang truy xuất RAG ngay cả lời chào. Đổi thành thông báo xử lý tin nhắn chung, không khẳng định một bước chưa chạy.

## Lỗi Knowledge thật được phát hiện riêng

Lượt hỏi mixed về mã AM-0007/năm 2026 thực sự vào nhánh Knowledge nhưng API trả HTTP 409 `EVIDENCE_CONTEXT_MISSING`. Không coi kết quả này là LIVE Knowledge E2E PASS.

Đối soát chỉ đọc trên nguồn đã xuất bản: 272 canonical blocks, 6 reviewed fact blocks; closure của tập đầy đủ đạt, không thiếu tham chiếu trực tiếp. Probe đóng gói một fact bằng hàm hiện hành tạo 4 blocks và thiếu chính canonical source row của fact; dựng lại dependency closure của tập đã đóng gói trả cùng mã lỗi 409. Trong `_fact_groups`, dòng nguồn được kiểm tra tồn tại nhưng không được đưa vào nhóm trả về. Đây là khoảng hở đóng gói bằng chứng đã tồn tại trong mã ngoài thay đổi routing; không phải kết luận DOCX bị mất dữ liệu.

Probe trên chứng minh độc lập một khoảng hở có thể sinh cùng lỗi 409; không lưu toàn bộ plan/stack của lượt live nên chưa kết luận đây là nhánh gây lỗi duy nhất của lượt đó. Không gọi lại model để mở rộng điều tra trong phiên này.

Giữ nguyên guard, nguồn, fact, hash và publication. Chưa sửa các hàm đóng gói/evidence dependencies vì prompt yêu cầu giới hạn thay đổi retrieval ở lỗi tích hợp do routing. Cần một thay đổi có regression riêng cho việc mang theo dòng nguồn và toàn bộ dependency khi đóng gói, trước khi nghiệm thu Knowledge E2E của DOCX này.

Bằng chứng riêng tư tại `backend/storage/context562`: `live-results.json`, `source-context-closure.json`, `packed-closure-probe.json`. Không đưa nội dung nguồn, token hoặc cấu hình kết nối vào báo cáo Git.
