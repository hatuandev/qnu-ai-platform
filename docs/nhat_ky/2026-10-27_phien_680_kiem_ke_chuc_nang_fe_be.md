# Phiên680 — Kiểm kê chức năng FE và BE chưa nối

Yêu cầu: xem chức năng FE còn thiếu và khả năng backendV1 chưa nối vào frontendV1.
Chỉ kiểm kê, không được hiểu là cho phép triển khai tất cả ý tưởng mới.

Đọc AGENTS/memory/Git, routes/schema/request/hook/component thực tế; áp dụng
clean-code và frontend skill đã dùng trong phiên trước. AST kiểm128HTTP
operations,96path helpers;5route không khai báo FE gồm answers và4health/metrics.
Đối chiếu caller thay vì chỉ đếm tên: raw review Compiler và GET spelling check
chưa có UI caller. Search/evaluation thiếu document picker; một số lịch sử chỉ
đọc trang đầu. Dashboard vẫn KTX template. Luồng nghiệp vụ chính đã có FE.

Đề xuất ưu tiên: phân trang/chọn tài liệu → mở lại spelling check → thử answers
trực tiếp; raw download ưu tiên thấp. Dashboard và lưu lịch sử evaluation làm
sau theo nhu cầu. Streaming/feedback/share/restore web còn thiếu API; không xem
là chức năng BE có sẵn chỉ cần nối. Compiler history quá100 cũng cần BE offset.

Artifact inventory/hash ở `storage/artifacts/context680-fe-be-inventory`.
NOT RUN build/test/API/browser/model vì không sửa ứng dụng. Không suy kết quả
test287 từ679 thành nghiệm thu mới. Chỉ tài liệu/memory/index được ghi; kiểm
hash ứng dụng, UTF-8/LF và link sau cùng. Không đổi runtime, migration/index,
provider, dữ liệu, deployment hay Git push.

[Báo cáo và bằng chứng](../bao_cao/context680/FE_BE_INVENTORY.md),
[snapshot](../memory/snapshots/2026-10-27_session_680.md).
