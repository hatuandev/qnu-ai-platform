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

## Assertion độc lập và tham chiếu liên quan

Một source unit có thể chứa nhiều điều kiện khác phạm vi. Annotation nội bộ mới dùng `assertion_version=1` để giữ exact EvidenceBinding và target riêng; backend dựng span canonical dẫn xuất, không sửa Structured Document hoặc gắn cả unit hỗn hợp cho mọi dòng. `related_evidence` giữ những điều kiện dẫn chiếu nguyên văn theo cùng phạm vi. Cột có thể giới hạn thêm tập dòng, ví dụ giao nhóm chương trình và nhóm cột năm. Facts/chunks mang `context_scopes`; không biến metadata này thành xác nhận dữ liệu.

Selector wire v1/v2 không đổi. Snapshot cũ tiếp tục replay theo liên kết unit cũ; metadata assertion rỗng được bỏ khi serialize để không đổi seal cũ. Span con của v2 mới cần scope review; một list nhiều khoản không được chọn nguyên unit làm điều kiện toàn bảng.

ContextBuilder mở subtree đầy đủ của heading trong giới hạn. Một heading đơn lẻ không đủ cho kết luận về reference. Phân tích reference có source bindings và assertion IDs là advisory, chưa phê duyệt. Reference liên quan dùng quyết định riêng `related_context_reviewed` với đầy đủ supporting evidence, actor/quyền server và exact proposal hash; không dùng `not_applicable_to_target` để bỏ tham chiếu đã được xác định liên quan. Nếu chưa đủ body/binding hoặc thiếu một scope decision, áp dụng vẫn bị chặn.

`prepare_semantic_review_checkpoint.py` tạo checkpoint offline mới từ bản gốc đã seal và kế hoạch đối soát, giữ bản gốc cùng tám issue ID. Không nhập checkpoint thành approval hoặc pending revision trong ứng dụng. [Bản đối soát Context553](../bao_cao/context553/REVIEW_READY.md) minh họa quy trình chờ người dùng, không phải nguồn đã duyệt.

## Nhập checkpoint vào review có xác thực

Từ Context555, hộp kiểm duyệt nguồn có đường nhập riêng `semantic-checkpoint`. Chọn đúng revision nháp, tải gói contract `qnu-semantic-checkpoint-v1` và ghi căn cứ. Server kiểm tài khoản/quyền, collection/binding/revision, draft/lease, cặp MD/Structured Document và cấu trúc/manifest/ô chính xác; không match theo tên file. Source hash khác phải dừng. Không tự sửa hash hay đưa offline ID vào DB như revision thật.

Nhập chỉ tạo pending: server rebind evidence, đổi assertion/issue ID nếu cần và tính proposal hash mới kèm audit nguồn offline và actor staging. Mọi quyết định cũ vẫn phải đối chiếu lại theo revision/hash mới; chuỗi approved trong file không cấp quyền. Nhập lặp cùng gói là idempotent; phải xử lý đề xuất đang mở trước khi nhập gói khác, và chỉ đúng hash hiện hành khi thay gói đã yêu cầu sửa/từ chối. Không xác nhận một scope cũ sai để vượt guard; nếu vấn đề cũ còn được giữ lại mà chưa có cách xử lý hợp lệ thì dừng đối soát.

Workflow note là ngữ cảnh hồ sơ/quy trình có chủ thể và điều kiện, không phải data-field dependency. Nó có assertion/chunk riêng, không tự gắn vào các fact số. `ReferenceAssessment.links` có vai trò direct/protective/conditional và evidence; conditional cần ghi điều kiện. Các vai trò là advisory, không tự phát sinh effective graph edges. Snapshot/selector cũ giữ khả năng đọc; metadata trung tính không đổi seal.

Sau stage, mở Preview A/O/S, xem toàn nguồn, target, điều kiện và loại trừ rồi dùng từng quyết định hiện có. Áp dụng annotation vào nháp và xuất bản nguồn là hai bước khác nhau. Test với actor TEST không chứng minh người dùng thật đã duyệt. Chưa có review thật phải ghi `IMPLEMENTATION_VERIFIED — WAITING_FOR_REVIEW` nếu triển khai đã kiểm chứng; blocker source/revision vẫn ghi riêng. [Bàn giao Context555](../bao_cao/context555/REVIEW_READY.md).
