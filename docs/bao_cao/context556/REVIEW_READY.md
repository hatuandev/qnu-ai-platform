# Context556 — Kết quả để quyết định

**RECONCILIATION_BLOCKED: chưa có proposal mới trong ứng dụng để bạn duyệt.**

1. **Vì sao khác hash?** Cùng một DOCX, nhưng revision đang lưu dùng pipeline cũ: thiếu ba footnote và có đoạn lặp từ ô bảng làm dịch ID. Nội dung và cấu trúc thực sự khác. Builder lịch sử tái hiện đúng 299 core records của bản lưu; builder hiện tại tái hiện đúng 233 core records của bản offline.

2. **Đã giải quyết hoàn toàn chưa?** Đã xác định nguyên nhân và có công cụ chuyển binding bằng chứng có kiểm chứng. Chưa thể chuyển trọn bộ vì A12 cần footnote 2 không tồn tại trong canonical cũ. Dữ liệu dẫn xuất đang lưu cũng không khớp khi tái dựng bằng code hiện tại.

3. **Có canonical revision hợp lệ chưa?** Đã xác minh revision đúng nguồn `ks_rev_84c4950c9ce2`; cặp MD/JSON vượt kiểm tra toàn vẹn. Tuy nhiên, revision này **chưa đủ nội dung và projection để nhập proposal đủ 12 mục**. Chưa tạo revision mới.

4. **Proposal đang gắn revision nào?** Revised Context555 vẫn gắn `offline544/draft544`; hash và binding cũ giữ nguyên. Context556 chưa tạo proposal hash hoặc import-package hợp lệ cho canonical thật.

5. **12 quan hệ còn đủ không?** Giữ đủ A01–A12. A01–A11 map được bằng nội dung và vai trò nguồn chính xác; A12 bị chặn riêng. A03 vẫn là hồ sơ thiết bị nhóm A, kế hoạch 2027, gia hạn tối đa 15 ngày làm việc khi đủ điều kiện; không gắn vào c10–c12 là các cột số liệu sinh viên. Nhóm B và AM-0070 không nhận nhầm ngoại lệ.

6. **Có bao nhiêu issue chờ duyệt?** Offline Context555 còn 18 issue: O01–O08 và S01–S10, chưa duyệt hoặc đóng. Revision thật chưa có pending proposal ngữ nghĩa; Context556 stage mới **0 issue**. Không xem issue offline là issue đã nhập ứng dụng.

7. **Mở đâu để duyệt?** Khi đã có revision và proposal hợp lệ: đăng nhập → Kho tri thức → Tuyển sinh → nguồn DOCX phức tạp → chi tiết revision → nhập checkpoint/đối soát ngữ nghĩa. Hiện chưa có gói hợp lệ để nhập. Browser đã tới trang SSO; màn hình duyệt thật ghi `UI_LIVE_NOT_RUN` vì chưa có session người dùng được cấp.

8. **Bước tiếp theo cụ thể?** Cần cho phép tạo **revision nháp mới** của đúng binding bằng pipeline hiện tại, giữ revision cũ để audit, chưa approve/index/publish. Trước khi chạy phải kiểm lại policy annotation và worker. Bản đang audit có `unit_temporal_annotation=null`; code hiện tại bỏ qua inference khi policy null/disabled, nên không cần bật ModelOps để tạo lại bằng chứng. Reparse tạo revision mới qua hàng đợi và sao chép policy nguồn; không tự chỉnh cấu hình hoặc restart. Sau đó kiểm đủ footnote 2, hash MD/JSON và projection replay; chạy mapping không gọi LLM; tạo proposal hash mới rồi nhập có xác thực trong môi trường được cho phép.

9. **Còn bị chặn gì?** A12 thiếu bằng chứng canonical; projection đang lưu không khớp khi replay; chưa có xác nhận tạo revision thật mới theo điều kiện của prompt; chưa có session quản trị để kiểm UI thật. O03/O05 có body nhưng chứa đích A12 chưa map; O08 thiếu footnote. Không mặc định mọi reference chặn toàn Bảng 1. Storage tạm khoảng 10 MB còn vì kiểm duyệt tự động chặn xóa.

10. **Đã apply/publish chưa?** Chưa. Không có phê duyệt người dùng, không ghi nguồn/revision/DB thật, không gọi LLM, không commit/push/deploy/migration. Nhập, lưu pending và đọc lại đã PASS ở DB/Storage TEST với actor TEST; kết quả này không phải E2E thật.

Kết quả mới: focused **146 PASS + 23 subtests**, frontend **21 PASS**, build/Ruff/Biome PASS. Full backend vẫn **18 FAIL nền, 2.429 PASS, 17 SKIP**; giữ đúng 18 test ID và nguyên nhân của Context555, thêm 13 test đều PASS. Probe bổ sung với nguồn offline đầy đủ chuyển đủ 12 quan hệ, 18 issue và giữ các vai trò tham chiếu; không thay thế bằng chứng thiếu ở revision thật.

Xem [nguyên nhân](ROOT_CAUSE_REPORT.md), [12 quan hệ và reference](RECONCILIATION_REPORT.md), [triển khai](IMPLEMENTATION_REPORT.md), [kiểm chứng](VALIDATION_REPORT.md), [test ID còn lỗi](REGRESSION_IDS.md).
