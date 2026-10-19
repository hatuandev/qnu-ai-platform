# Phiên552 — Evidence binding và semantic selector

## Thiết kế và phạm vi

Bản vá giữ Context547/548, pipeline ModelOps, parser tài liệu, retrieval và annotation/snapshot schema. Không đổi model, endpoint, credential, context, output reserve hoặc timeout. Chỉ sửa đường chọn/binding bằng chứng, scope review, preview và runner chẩn đoán/checkpoint.

`semantic_binding.py` thêm wire v2 cho notes/cells/limitations, giữ v1 nguyên hình dạng. V2 dùng evidence ID để lấy owner từ registry packet, kiểm ID/key/public evidence nhất quán, kiểm canonical owner/span/hash rồi mới chuẩn hóa thành selection nội bộ cũ. Không tìm ID ở registry toàn tài liệu, không chữa v1 sai owner, không dùng owner do model thêm vào v2. Target/raw/business validators tiếp tục chạy sau binding. Lỗi ghi category/index, evidence ID, owner thực/khai và target; lỗi liên quan nhiều annotation ghi tập candidates thay vì bịa vị trí một phần tử.

`output_contract.py` cache schema theo contract name; resolver và response format ghim name/version/business-wire hashes. `semantic_selector.py` parse cả response theo expected contract, không thử phiên bản khác sau lỗi. Schema v1 có cùng hash với551; schema v2 khác và có cache riêng. `semantic_modelops.py` ghim cùng phiên bản cho prompt/request/parser/binder, giữ retry/fallback cùng phiên bản và atomic staging; trace bổ sung contract, policy/hash, raw response hash và latency quan sát.

## Scope không suy từ sự xuất hiện mã

Row/group luôn tạo issue cần người đối chiếu toàn canonical source unit. Đây là lựa chọn bảo thủ được prompt cho phép khi chưa có thuật toán xác minh nghĩa tự nhiên đủ tin cậy. Bỏ heuristic đếm mã/mở khoảng mã để quyết định nghĩa, không thêm từ điển phủ định theo fixture. Các guard target/hash/source vẫn từ chối lỗi kỹ thuật. Full source không thể biểu diễn trong review hoặc thiếu collector thì không tạo proposal giả hoàn tất.

Issue ID, full-unit decision, server actor/time, exact target/proposal hash, reject/changes_requested và snapshot cũ tiếp tục do các service hiện có kiểm. Không viết lại store/review. Preview chỉ bổ sung tên/mã dòng và header cột cạnh toàn câu nguồn; vẫn có truy vết kỹ thuật trong phần mở rộng. Không xây editor annotation.

## Lỗi tích hợp phát hiện trong kiểm thử

Ca có cả cell meaning và limitation thất bại vì kiểm lại input hash sau khi cell meaning đã thay đổi bản sao dẫn xuất; nhiều limitation cũng có thể tự đổi input hash giữa vòng lặp. Sửa hẹp: kiểm toàn bộ binding trước mutation, xử lý limitation trước cell changes, và kiểm binding của toàn bộ tập limitation trước khi thêm record dẫn xuất. Không tắt verify hoặc thay input hash để cứu payload. Guard cùng một ô không được vừa interpret vừa acknowledge vẫn giữ.

## Tương thích và kiểm chứng

Wire v1 vẫn dùng được khi ghim v1; default của OutputContract độc lập giữ v1. SemanticContextPolicy mới chọn v2. Không đổi phiên bản annotation/context review lưu trữ; pending/snapshot cũ không được nâng phiên bản hoặc đổi hash. Rebuild không gọi model. Nguyên tắc unknown/slash/zero và scope theo dòng/cột được kiểm qua luồng thật và Storage.

Runner selected-table ghi checkpoint có hash/source/policy/packet nếu proposal hợp lệ; không tự phê duyệt. API verifier tra schema theo request contract thay vì luôn ghi hash v1. Evidence được allowlist và giữ trước cleanup; checkpoint offline không được gọi là ứng dụng job đã resume.

Xem [validation](VALIDATION_REPORT.md), [diagnosis](DIAGNOSIS_REPORT.md), [quy trình](../../quy_trinh/14_semantic_selector_va_scope_review.md).
