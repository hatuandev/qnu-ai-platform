# Phiên 747 — Sửa các điểm P1/P2 của compiler song song

## Phạm vi

Người dùng yêu cầu sửa các điểm P1/P2 sau review. Giữ thay đổi chưa commit từ IDE khác. Theo chỉ dẫn đã xác nhận trong phiên, không tự chạy test/build/lint/typecheck/live model; không đổi DB/checkpoint/config phục vụ, restart, migration, reindex, deploy hoặc push.

## Thay đổi

1. Scheduler đóng admission trước khi nhả semaphore khi worker lỗi/trả terminal; hủy orchestrator hoặc lỗi partial writer cũng dừng phần chưa bắt đầu trước khi drain phần đang chạy.
2. Projection v4 giữ đuôi chú thích vượt 6 block/4000 byte và ghi chú sau bảng giữa tài liệu. Phạm vi `unresolved` không được biến thành điều kiện áp cho mọi hàng. Không vừa ngân sách phải báo lỗi, không cắt context.
3. Settle usage phần bằng session riêng. Nhánh phản hồi lỗi kiểm claim trước raw/status/draft; không thể commit phần stale qua commit bên trong usage service. Recovery giữ usage đã đo khi yêu cầu settle unknown gặp record terminal.
4. Redis admission dùng chung cho managed chat theo endpoint/model, namespace deployment; mặc định 4 lượt tổng, queue 300s. Mỗi compiler mặc định 2 phần; giới hạn hiệu dụng lấy mức thấp nhất giữa snapshot, policy hiện tại và cap model. Lỗi admission chưa dispatch ghi usage 0; cancellation/uncertain giữ lease đến TTL, không retry.
5. Single-call compiler ghim/truyền directive reasoning giống segmented path và so sánh trước dispatch. Legacy thiếu directive giữ mặc định.
6. E2E dùng `ceil(parts/concurrency)` và đủ một deadline cho một phần; cộng queue budget tách biệt. Log tiến độ không coi elapsed đơn thuần là thay đổi trạng thái.
7. V4 không suy nối bảng từ trang kề/header giống/số cột giống. V2/v3 replay bằng contract cũ; scope/hash cũ không chuyển ngầm sang v4. E2E replan chỉ run cũ failed, giữ lịch sử.

## File chính

- `backendV1/qnu/domains/knowledge/compilation/{scheduler,execution,segments,service,schemas}.py`.
- `backendV1/qnu/domains/modelops/resilience/{admission,execution}.py`, `backendV1/qnu/platform/config.py`.
- `frontendV1/e2e/stages/{session,progress-budget,admissions-publication}.ts`.
- Regression mới `test_compiler_fixes_747.py`, `test_model_chat_admission_747.py`, `progress-budget.test.ts`; bổ sung tests projection/scheduler 746.
- [Hướng dẫn compiler](../quy_trinh/V1_COMPILER_TAI_LIEU_LON.md).

## Kiểm chứng thực hiện

- Đọc AGENTS/skills/memory, `git status --short`, `git diff`, `rg` và các file thực tế. Không dùng báo cáo cũ làm bằng chứng runtime mới.
- `git diff --check` từ repo root: exit 0. Đọc byte UTF-8 strict/LF trên 22 file trong phạm vi không thấy BOM/CR; đọc lại tiếng Việt và xác nhận file liên kết mới tồn tại. Đây chỉ là kiểm tra tệp/diff.
- Regression đã viết cho dừng hàng đợi, cancellation/writer failure, claim lost ở nhánh lỗi, ledger đã đo, single-call reasoning, note dài/giữa bảng, header/column không chứng minh liên kết, v3 replay, queue deadline và slot cleanup.
- Test/build/lint/typecheck/E2E/live inference: **NOT RUN** theo yêu cầu; chưa có pass/fail count mới. Mock Redis chưa chứng minh atomicity hoặc cap dưới tải nhiều process.
- Gate backend rộng lịch sử phiên 737 còn **FAIL**; không thay trạng thái bằng đọc tĩnh hoặc test chưa chạy.

## Giới hạn và bước sau

Chưa đo lại thời gian/số phần với v4. Giữ đủ chú thích có thể làm input lớn hơn; lỗi budget vẫn là lỗi thật. Redis/namespace/cap cần nhất quán giữa process. Lease QNU không chứng minh server dừng generation sau timeout; TTL chỉ hạn chế nhận thêm request trong khoảng không chắc chắn.

Người dùng đợi lượt hiện tại kết thúc, restart đúng serve để nạp mã rồi chạy lại admissions-compilation, PASS mới publication/chat. Không cleanup/init khi tiếp tục phiên. Các lệnh kiểm chứng nằm trong hướng dẫn; integration phải dùng DB/cache cô lập.
