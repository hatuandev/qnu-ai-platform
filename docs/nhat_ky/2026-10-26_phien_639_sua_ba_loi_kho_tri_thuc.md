# Phiên639 — Sửa ba lỗi kho tri thức backendV1

Người dùng yêu cầu sửa cả ba phát hiện review638. Đã đọc context, Git, source thực,
skill backend/clean-code và quy tắc kiểm chứng; giữ các sửa đổi đồng thời ngoài phạm vi.

- Local driver: ghi staging cùng thư mục rồi atomic replace, lỗi giữa chừng không
  hỏng file đã commit. Sửa nhầm scope đường dẫn dài Windows và kiểm bytes thật nếu
  replace bị từ chối do writer đồng thời; không che lỗi khi nội dung đích khác.
- Idempotency: JSON fingerprint v2 có title hiệu lực, giữ replay sổ cũ khi title
  khớp và không viết lại ledger. Append revision từ chối trường title422; cập nhật OpenAPI.
- Migration0005: từ chối downgrade tường minh, giữ version/data và upgrade tiếp được.

Ba regression trước sửa3FAIL đúng nguyên nhân. Các focused trung gian phát hiện
đường dẫn dài và WinError5, đã sửa trước gate cuối. Focused cuối24PASS/13,90s,
full v1 121PASS/0FAIL/0SKIP/40,58s, exit0. Ruff toàn v1/format7file/OpenAPI31path
PASS. Có17ca mới. Lệnh/cwd/DB và giới hạn trong [báo cáo639](../bao_cao/context639/REVIEW.md).

Chỉ4file app/migration v1 thay đổi so source seal616file;475legacy app giữ hash.
10DBtest của phiên đã dọn và sentinel legacy giữ, đối soát catalog0còn lại. DB
phục vụ chưa migrate; không restart/deploy/commit/push. Chưa live S3 hoặc nối OCR/RAG.

Cập nhật hợp đồng kho tri thức, ma trận port, quy trình20, báo cáo và memory/index.
Batch sau có thể triển khai xử lý nguồn theo phạm vi được giao; hiện source vẫn `stored`.
