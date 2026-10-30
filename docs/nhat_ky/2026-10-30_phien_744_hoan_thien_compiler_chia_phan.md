# Phiên 744 — Tiếp tục phần OpenCode đang dở

- Người dùng giao tiếp tục implementation sau OpenCode hết token. Giữ toàn bộ diff OpenCode; không reset, không restart, migrate DB, gọi model hoặc tự chạy test/build/lint theo yêu cầu trước.
- Đã đọc: manifest/projector/compiler execution, review planner/service/execution, output generations, lease, schema/migration, E2E admissions và test mới. OpenCode đã tạo khung chia phần/compiler/review/progress/migration0008.
- Sửa lỗi review single-call: prepare mới cần trả material để execution thực sự gọi model, thay vì trả status running ngay.
- Bổ sung review execution token khi tiếp quản, recheck provider hiện tại/scope/expiry trước sau call, no-autoflush trước kiểm owner, khóa row khi xử lý lỗi; writer cũ không được đổi trạng thái writer mới. Usage vẫn settle theo call quan sát, không retry uncertain.
- Output blob dùng ID duy nhất thay đường dẫn số generation có thể va chạm giữa writer; chỉ chuyển output pointer sau khi cả JSON/MD readback hợp lệ.
- Giữ tất cả citation bắt buộc/header/row context; không retry bằng cách bỏ context. Sắp context theo thứ tự nguồn để input hash tái tạo ổn định. Tabular documents giữ notes ngoài bảng và header context; compiler coverage chứng minh không thiếu/trùng ownership. Không suy nối bảng chỉ từ số cột.
- Đưa CPU planning vào asyncio.to_thread. Giữ allocator cận trên byte an toàn và check capacity trước call, không đổi provider/tokenlimit/quota.
- Thêm regression ownership/output-pair failure/citation cap/cross-page conditions/duplicate coverage. Test tồn tại nhưng NOT RUN. Test OpenCode cũng chưa chạy trong phiên này.
- Thêm hướng dẫn V1_COMPILER_TAI_LIEU_LON. Tái sử dụng trong cùng snapshot/run; cache xuyên revision chưa triển khai (chấp nhận cache miss để không gắn sai nguồn). Chưa thêm UI riêng; progress/partial API và E2E có sẵn được giữ.
- Test/build/lint/typecheck/migration/live: NOT RUN. Chỉ đọc diff/code và ghi source/docs; không khẳng định runtime PASS hay full suite PASS. Lỗi nền lịch sử737 vẫn giữ nguyên. Nghiệm thu theo lệnh trong hướng dẫn, dùng DB test riêng cho integration.
