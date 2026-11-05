# Phiên874 — Đối chiếu ba bản biên soạn nhanh

Người dùng yêu cầu đọc ba run trong collection col_539580c0ee19. Chỉ gọi GET
qua API có xác thực/quyền workspace; tải artifact và nguồn về tmp bỏ qua Git.
Không sửa ứng dụng, nguồn, phát hành, chỉ mục hoặc gọi model/restart.

## Kết quả theo từng lượt

| Run | Nguồn | Thời gian | Trang | Khối chính | Mảnh bảng/ô | Citation |
|---|---|---:|---:|---:|---:|---:|
| cmp_a5e2e1f064d6 | Báo cáo công tác Tư vấn tuyển sinh năm2025 dự thảo | 0,245402s | 8 | 157 | 9/303 | 463 |
| cmp_a77c8dd5bc95 | Dữ liệu RAG Trường Đại học Quy Nhơn2026 | 0,192777s | 8 | 264 | 0/0 | 264 |
| cmp_d603a9bed3bd | Phương hướng tuyển sinh2024 | 0,233334s | 7 | 101 | 6/547 | 648 |

Cả ba completed/source_first=true, nativev3, chưa có review AI. So với đúng
canonical ghim: giữ toàn bộ khối có text và literal tables, không đổi chữ/ô,
không có reference ngoài evidence. Hash source/canonical/manifest khớp snapshot
server. Đây là giữ nguyên dữ liệu bóc tách; không phải kết luận mọi số liệu đúng.

### Báo cáo2025

Không có cảnh báo mapping bảng; 9 bảng Docling nguồn được đọc. Có hai ảnh biểu
đồ tại trang4/7, bốn text OCR con và hai ghi chú cần đối chiếu ảnh. MinerU chưa
đưa tỷ lệ phần trăm bên trong biểu đồ vào text con, nhưng các tỷ lệ tương ứng
được viết rõ trong văn bản ngay cạnh ảnh và đã giữ trong draft. Không kết luận
chỉ dựa vào tiêu đề/legend OCR rằng đã hiểu đầy đủ đồ thị. Chưa test RAG.

### Dữ liệu RAG2026

Nguồn DOCX không có bảng, canonical và draft đều không có bảng. Không cảnh báo
ảnh/bảng cần review; 264 khối nguyên văn. Tiêu đề draft là demo1. Chưa đánh giá
ngữ nghĩa toàn văn hoặc chạy bộ câu hỏi retrieval.

### Phương hướng2024 — còn vấn đề ở đầu nguồn

- Sáu mảnh bảng trang4–7 vẫn cần đối chiếu. Nguồn có header/ô gộp nhiều tầng,
  bảng nối trang và một hàng trống kết thúc bảng có lưới không đầy đủ. Bộ đọc
  Docling nhận4 bảng nhưng một bảng không qua kiểm grid và không được dùng
  để phục hồi header. Native v3 giữ mảnh PDF và cảnh báo, không đoán mapping.
- Dòng tổng cuối tài liệu Word lưu các giá trị1070/451/402/351 và bốn field
  `=SUM(ABOVE)`. Không có tracked changes/deleted text ở đây.
- PDF Gotenberg–LibreOffice đã lưu (hash khớp manifest) hiển thị dòng này thành
  67502118/208561309/1070/451, ngắt nhiều dòng trong ô. Canonical và draft đang
  giữ đúng những chữ/số từ PDF sai lệch này. Đã xem ảnh trang7 để xác nhận.
- Như vậy sai lệch đã có ở bước chuyển DOCX→PDF, liên quan tính lại field công
  thức bảng; không phải LLM Compiler bịa số. Cần xử lý chuyển đổi/căn cứ ô nguồn
  và đối soát header/span trước khi phát hành bản này. Không tự lấy cache Word
  làm số đã phê duyệt, cũng không chạy AI để đoán lại dòng tổng.

## Kiểm chứng và phạm vi

GET status/progress/draft/markdown/reviews, GET nguồn/canonical/manifest/evidence
và content ba tài liệu đều HTTP200; GET render PDF nguồn2024 HTTP200. Script đối
chiếu cuối exit0, lưu tmp/compilation-review-874/comparison.json. Kiểm Word/XML
và ảnh nguồn tại tmp cùng scope. Không đưa corpus vào Git; chỉ nhật ký/snapshot.
Không chạy Pytest/build vì không sửa code; không thay trạng thái full gate FAIL
đã ghi phiên872. Chưa duyệt/phát hành/reindex hay đánh giá câu trả lời model.
