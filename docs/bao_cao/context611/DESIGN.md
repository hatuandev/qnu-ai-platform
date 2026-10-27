# Context611 — Đóng gói theo request và checkpoint từng giai đoạn

Phạm vi: sửa compiler và đường truyền ModelOps để thử ba DOCX 2024–2026 bằng GPT-OSS medium/output8192. Không thay nguồn, Quality Gate, model mặc định hoặc index/publication. Kết quả nghiệm thu ghi riêng; thiết kế không chứng nhận nội dung model đã đúng.

## Ngân sách

CompilerPolicy mang output/context budget và reasoning_effort được xác thực bằng Pydantic. Cùng một policy đi qua planner, kiểm request thực, generator và configuration hash. Reasoning effort là trường riêng trong ModelOps request/adapter; không suy medium từ thinking_budget dạng số. Adapter không hỗ trợ phải báo lỗi. Không thêm API key vào môi trường.

Mặc định cũ vẫn là output2500/context24000,4primary/gói,30gói,64calls/600s và tổng64calls. Lượt thử được cấp server-side output8192/context24000,medium,12primary/gói; mỗi lần thực thi tối đa64calls/600s, toàn bản biên soạn tối đa128calls, tính cả các lần tiếp tục. Client không được chọn model/budget qua CompilationRequest.

Trích xuất và review là hai request riêng. Không cộng hai lần quote và một dự phòng review lớn vào request trích xuất. Mọi request vẫn dự phòng đầu ra đầy đủ và bị chặn trước inference nếu không vừa. Review đo payload thật; khi cần chia assertions, giữ toàn bộ raw evidence/dependency context trong mỗi phần. Gộp ledger và kiểm chính xác item IDs; missing/duplicate/foreign checks không được biến thành PASS. Deferred/missed evidence vẫn qua hai coverage audits độc lập và tối đa một repair theo chính sách cũ.

Thời gian còn lại phải đủ cho request timeout và khoảng chừa lưu trạng thái trước call mới. Hết cửa sổ calls/time khi chưa có call đang dở thì lưu paused. Hết tổng budget thì chặn; resume không đặt lại bộ đếm. Không bảo đảm mọi model luôn hoàn thành trong8192; length/timeout/provider failure vẫn là lỗi thật.

## Checkpoint ứng viên

Identity mỗi logical call gồm ordinal, schema, instruction, payload và configuration hash. Ordinal giữ hai CoverageAudit cùng payload là hai lần độc lập. Configuration hash gồm policy thực, protocol packing/checkpoint và cấu hình ModelOps có bảo vệ.

Trước inference, lưu started và số calls dưới collection lock rồi commit, không giữ lock qua network. Sau contract validation, lưu object bất biến qua StorageDriver, đọc lại kiểm checksum rồi ghi completed. Đây là candidate, không phải approval. Các ràng buộc nguồn/scope/time/unknown/coverage/Quality Gate được chạy lại khi dựng tiếp.

JSON/schema rejection đã hoàn thành được lưu để dùng lại feedback/correction có giới hạn. Started/uncertain ở cấp **inference stage** và lỗi provider không được gửi lại tự động. Object/hash/identity hỏng, nguồn/config thay đổi hoặc mất quyền đều chặn. Checkpoint I/O lỗi không được coi hoàn tất.

Khi existing_assertions làm coverage/repair vượt request budget, server có thể tách các trường lặp lại thành shared_assertion_contexts. Kiểm tra mở rộng ngược phải khớp hoàn toàn từng assertion; không bỏ giá trị, raw evidence, scope hoặc năm. Nếu vẫn không vừa thì chặn. Feedback sửa JSON quá lớn có thể thu gọn thành mã lỗi cấu trúc, không cắt nguồn để nhường chỗ.

## Tiếp tục qua API hiện có

Chỉ paused hoặc job uncertain **có đầy đủ prefix xác định** được tiếp tục. Job uncertain ở ranh giới xử lý xác định có thể chứa toàn bộ completed/rejected và chưa bắt đầu call tiếp theo; khác với inference stage uncertain. Server kiểm số call khớp số checkpoints, identity/config/hash, loại rejection và không có stage started/uncertain trước khi cho resume. Receipt uncertain cũ thiếu checkpoint không đủ điều kiện.

Client gửi lại topic/source/hash, idempotency_key mới, resume_from_job_id và expected_resume_version. Server kiểm nguồn hiện hành, cấu hình, version, trạng thái và quyền trước khi cấp job mới có checkpoint references cũ. Parent chỉ có một child; version và audit checkpoint_resumed được cập nhật. Intent khác không chiếm job đang chạy. Tập packet cache được ghim khi reserve để cache mới xuất hiện không làm lệch ordinal trong lần tiếp tục; cache phụ thuộc bị thu hồi thì chặn.

Cùng idempotency_key trả receipt hiện có, không inference thêm. Revision/config/hash khác không dùng checkpoint cũ. Context610 chỉ có debug artifacts, thiếu identity checkpoint mới; không tự nhập cache hoặc coi đã xác minh checkpoint. Chỉ dùng chúng để mô phỏng dung lượng ngoại tuyến, không làm facts/approvals.

Public record bổ sung resumable, completed_stages, model_calls_count và resumed_from_job_id. Audit quyết định cũ giữ nguyên; checkpoint_audit là chuỗi riêng có actor/checksum, không prompt/credential/reasoning text. Read/approve vẫn cần quyền; không tự publication/vector writes.

## Tương thích và kiểm chứng

Không migration DB; tái dùng registry collection/StorageDriver. Request cũ vẫn hợp lệ; hai trường resume là cặp tùy chọn. Compiler hash thay đổi; artifact/checkpoint khác protocol không được tái sử dụng.

Regression: DB/ASGI resume, idempotency/OCC/concurrency, thiếu quyền, nguồn/config thay đổi, checksum hỏng, uncertain no-resend, independent coverage, format correction đã checkpoint, tổng budget, review đủ raw context, Storage failure. Mock chứng minh contract; ModelOps thật và full regression có báo cáo riêng.
