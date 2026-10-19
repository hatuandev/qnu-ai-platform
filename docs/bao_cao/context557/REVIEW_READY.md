# Context557 — Sẵn sàng để bạn đối soát

**STAGED — WAITING_FOR_REVIEW. Đã có bản nháp và proposal chờ duyệt trong ứng dụng local.**

1. **Revision nháp mới đã tạo chưa?** Đã tạo đúng một bản từ DOCX kiểm thử qua pipeline chính thức hiện tại; revision cũ còn nguyên.

2. **ID revision mới?** `ks_rev_2b5e0352565f`, source `bnd_21c09bbc6ca0`, collection `col_admissions`.

3. **Đủ ba footnote chưa?** Đủ. Đã kiểm nguyên văn trong XML DOCX, locator và liên kết hai chiều về đoạn gốc. Footnote 2 giữ `0012`, `00027`, `AM-0007` dạng chuỗi. Footnote 3 chưa xác minh được trang PDF nên vẫn ghi unknown.

4. **Đã reconcile đủ 12/12 chưa?** Đủ 12/12; cả 6 reference map được. Nội dung, điều kiện và ngoại lệ giữ nguyên.

5. **Còn assertion bị chặn không?** Không còn blocker binding/parser của Context556. Điều kiện nghiệp vụ vẫn cần bạn đối soát. A03 chỉ chi phối hồ sơ thiết bị nhóm A, kế hoạch 2027; không sửa số liệu sinh viên. Đây chưa phải xác nhận tài liệu đúng để publish.

6. **Proposal hash đang chờ duyệt?** `543ddd61aa0b1527babe8c6adcb122c5cb2157f30d542c91d1de6fa5407207df`. Gói chuẩn bị có hash khác vì importer tạo metadata/thời điểm staging mới; hãy dùng hash pending hiện tại trên giao diện.

7. **Đã stage chưa?** Đã POST qua API thật, đọc lại trong session DB mới và rebuild khớp pending. Actor là development actor có quyền đang được ứng dụng local cấu hình, không phải quyết định SSO của bạn. Chưa có annotation hiệu lực hoặc phê duyệt.

8. **Mở đâu để duyệt?** [Mở đúng revision nháp](http://localhost:3000/knowledge/col_admissions/sources/bnd_21c09bbc6ca0?revision=ks_rev_2b5e0352565f&tab=content). Đăng nhập tài khoản có quyền, mở phần Kiểm duyệt/Đối soát ngữ nghĩa, xem 12 quan hệ và từng issue trước khi chọn quyết định. Có thể yêu cầu sửa/từ chối; không cần đồng ý với mục bạn thấy sai. Browser kiểm thử hiện ở SSO, nên thao tác review sau đăng nhập bằng tài khoản thật chưa được kiểm chứng.

9. **Còn bao nhiêu issue cần quyết định?** **18 issue**: 8 issue gốc O01–O08 và 10 xác nhận phạm vi S01–S10. Không issue nào được tự duyệt hoặc đóng. Cảnh báo chất lượng nguồn/preview là nhóm riêng, vẫn cần xem trước khi duyệt nguồn.

10. **Có dữ liệu nào đã apply/publish chưa?** Chưa. Pending chưa làm thay đổi bảng, facts, đồ thị hoặc manifest đã lưu; active pointers/epoch và DB index revisions/chunks/facts giữ nguyên. Không gọi lại LLM annotation, không commit/push/deploy.

Kiểm thử mới: **158 test tập trung + 23 subtests**, **6 kiểm tra artifact** và **21 test frontend** đều đạt; build/Ruff/Biome đạt. Full backend vẫn **2.429 PASS, 18 FAIL nền, 17 SKIP**; đúng từng test ID và nguyên nhân của Context556, không phát sinh regression mới. Không nhận là E2E RAG PASS.

DB test đã dọn. Kiểm duyệt tự động chặn xóa Storage test mới với lý do `blocked by policy`; khoảng 7,9 MB còn, không vượt chính sách hoặc đụng các thư mục cũ bị chặn.

Xem [revision và giới hạn](REVISION_CREATION_REPORT.md), [12 quan hệ](SEMANTIC_RECONCILIATION_REPORT.md), [kiểm chứng](VALIDATION_REPORT.md), [receipt](staging-receipt.json).
