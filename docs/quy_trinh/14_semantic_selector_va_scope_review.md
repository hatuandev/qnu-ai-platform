# 14 — Selector có phiên bản và đối chiếu scope chú thích

Luồng này bổ sung cho Markdown Standard và lifecycle annotation hiện có; không đổi định dạng Markdown hoặc schema annotation lưu trữ.

## Hợp đồng chọn bằng chứng

Backend ghim OutputContract trước gọi ModelOps. `qnu_semantic_selector_v1` vẫn yêu cầu evidence ID và owner; thiếu/sai owner bị từ chối. `qnu_semantic_selector_v2` chỉ nhận evidence ID, reason và các tọa độ đích theo schema; owner, quote, span và hash lấy từ registry đúng packet rồi kiểm với canonical source. Không nhận owner/quote/approval do model thêm vào v2.

SemanticContextPolicy mới mặc định v2. Caller tương thích có thể ghim v1 qua `output_contract.name`; OutputContract độc lập vẫn mặc định v1. Schema prompt, provider payload, parser, binder và trace dùng cùng contract; retry/fallback chỉ đổi output mode theo capability/policy, không đổi phiên bản selector. Các snapshot/pending cũ giữ nguyên bytes và authority, không được đổi hash để nâng phiên bản.

ModelOps tiếp tục quyết định model/provider qua DB. Capability chưa xác minh native JSON Schema thì mode hiệu lực có thể là `prompt_only` theo policy cho phép; JSON/schema đạt ở backend không phải chứng minh native schema enforcement.

## Scope cần người đối chiếu

Một mã xuất hiện trong câu không chứng minh quan hệ áp dụng tích cực; nó có thể nằm trong phủ định hoặc ngoại lệ. Backend không đếm mã hoặc tự mở khoảng mã để chứng nhận row/group scope. Mọi đề xuất row/group cần issue `scope_confirmation_required`, chứa toàn canonical source unit và đúng tập dòng/cột. Scope cột nhiều năm giữ cơ chế review hiện có.

Thiếu collector, hoặc không biểu diễn đủ toàn nguồn trong giới hạn review hiện tại, phải báo chưa hoàn tất. Không cắt câu loại trừ cho vừa giới hạn. ID không tồn tại/ngoài packet, registry bị sửa, source/revision/hash/span sai hoặc target sai vẫn là lỗi kỹ thuật, không chuyển thành warning.

Preview hiển thị tên/mã dòng, header cột và toàn câu nguồn. Người duyệt phải kiểm cả đối tượng áp dụng và bị loại trừ; giữ nguyên mã dạng chuỗi, kể cả số0 đầu. Nếu tập đích sai, dùng `rejected`/`changes_requested` rồi tạo proposal sửa với hash mới; không xác nhận scope sai để đi tiếp.

Quyết định phải khớp issue ID, target, proposal hash và full-unit evidence. Server ghi actor/thời điểm. Một ghi chú chung không giải quyết issue riêng. Pending không được dùng làm dữ liệu hiệu lực; từ chối proposal mới không xóa snapshot hiệu lực cũ. Replay/rebuild giữ quyết định đã kiểm chứng và không gọi lại model.

## Checkpoint kiểm chứng

Runner `backend/scripts/verify_semantic_modelops.py` hỗ trợ selected tables và ngân sách hữu hạn. Nếu có pending hợp lệ, runner ghi `checkpoint.json`, proposal, projection và hash/policy/contract/packet anchors để chờ review. Đây là checkpoint offline, không phải job/resume endpoint của ứng dụng và không cấp quyền áp dụng.

Trình tự nghiệm thu: deterministic tests → model thật trên bảng chọn → người có quyền đối chiếu từng issue → lưu/đọc lại/rebuild qua luồng thật → đánh giá đủ budget trước chạy API toàn tài liệu. Test actor chỉ dùng trong kiểm thử, không thay bằng chứng người dùng thật duyệt. Một bảng đạt hoặc packet đầu đạt không xác nhận toàn tài liệu hoàn tất.

Giữ giới hạn context/output, deadline/run/call, retry/fallback/expansion và atomic staging. Không tạo worker mới, cắt packet hoặc tăng timeout vô hạn để né blocker.
