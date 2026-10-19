# Bản vá context547 — triển khai phiên548

## Thay đổi chính

| Nhóm | File/hàm và hành vi |
|---|---|
| Context review | `semantic_context_review.py`: issue identity theo contract/source/revision/input/kind/tập tọa độ và unit IDs, không theo câu reason; chuẩn hóa legacy/unresolved; một summary backend cho application/publication/policy/preview |
| Stage/review | `semantic_annotations.py`: proposed khi có issue, empty chỉ khi thật sự không còn việc; envelope/hash/actor kiểm độc lập; application guard cần quyết định riêng từng issue, reject/change không gọi apply |
| Scope | `semantic_binding.py`: full canonical unit tham gia screening; nhiều năm/năm học giữ quote và tạo scope issue; single-year conflict/sai nguồn/span/hash/sibling vẫn bị chặn |
| Budget | `semantic_context.py`: union public unit/container/full row IDs, directory tính bytes nhưng không giả đã đọc full rows; dùng chung accounting tại split/prose/accepted/expand/preflight |
| Deadline | `semantic_run_budget.py`: một monotonic run deadline, bounded top-level call gồm retry/fallback; phân biệt run/call/provider timeout, giữ cancellation; stage trong bản copy và kiểm hạn ngay trước mutation |
| Persistence | `semantic_store.py`: v1 hash recipe giữ nguyên, version2 bind context và decisions; replay kiểm lại source-bound decisions; latest rejected context còn chặn source nhưng không thay active annotation set |
| Policy/publication | `source_limitations.py`, `source_artifact.py`, `source_ingestion_service.py`: context blockers riêng với unknown cell; guard duyệt nguồn dùng cùng summary; Studio copy read-only bổ sung summary cho dữ liệu cũ |
| UI/API | schema, types, API client, preview/source detail: full source/target/reason, issue history ở cả empty/rejected/verified, gửi ý định riêng; actor/authority không nhận từ client; summary quyết định khả năng áp dụng |
| Runner/evidence | `verify_semantic_modelops.py` dùng cùng policy với API; tracked audit/isolation/export/cleanup scripts thay harness chỉ ignored; ZIP allowlist có JUnit, exact comparison, command/hash/live summary và manifest |

## Quyết định theo issue

`scope_confirmation_required` nhận `scope_confirmed`; `deferred_reference` nhận
`not_applicable_to_target`. Intent gồm issue ID, target, full canonical evidence
binding/quote và reason. Backend kiểm đúng pending proposal/input/revision/hash,
issue/target/action, full code-point span và source text. Actor lấy từ phiên xác
thực; không nhận một object “checked” từ client/model. Chỉ sau kiểm tra mới lưu
actor/thời điểm/proposal hash vào review envelope riêng; payload gốc không bị sửa
sau băm. Generic comment hoặc acknowledged_limits không giải quyết context issue.

Missing-context không nhận checkbox quyết định. Một lần reprocess có thể chọn
evidence IDs của đơn vị prose bổ sung đã cấp; backend xác minh rồi thay issue đó
bằng scope-review issue mới, vẫn cần người đối chiếu. Lịch sử prior issues, prior
proposal hash và lý do thay thế được giữ. Model bỏ nhắc issue không làm nó mất.

`packets_complete`, `semantic_complete`, `requires_more_context`,
`application_blocked` và `publication_blocked` có nghĩa riêng. Selected-tables
không được coi là toàn tài liệu; guard publication vẫn chặn. Kết quả một bảng
không được thay thế bộ annotation toàn tài liệu đang hiệu lực.

## Tương thích và tính nguyên tử

- Snapshot path/schema hiện hữu được tái sử dụng. `semantic_hash_version=2` chỉ
  cho snapshot mới có context; v1 tiếp tục đúng recipe cũ, không ghi lại bytes.
  V1 có unresolved không được tự nâng thành đã review đầy đủ.
- Fingerprint chuẩn hóa các context counters trung tính trong policy legacy;
  source/binding/revision và semantic seals không bị vô hiệu vì thêm counter0.
- Reject/changes_requested lưu history, giữ active pointer. Rebuild overlay issue
  mới nhất để không làm mất blocker. Không gọi model khi reload/replay.
- Mọi packet phải thành công mới stage. Timeout/cancel ở packet2 hoặc trong thread
  stage không để lại nửa bộ annotation trên caller artifact.
- Không sửa parser/OCR/Markdown Standard/retrieval strategy, không thêm persistence
  hoặc worker mới, không đổi model/provider/endpoint/timeout DB dùng chung.

## Giới hạn

Numeric screening không phải bộ hiểu phủ định tiếng Việt hay kiểm định pháp lý.
Full quote và ID hợp lệ chỉ chứng minh căn cứ có thật; người có quyền còn phải
kiểm phạm vi/ngữ nghĩa. Không có thao tác duyệt thay người dùng.

Live hiện **BLOCKED tại schema**: provider phản hồi nhưng JSON có phần dư; không
sửa response hoặc thêm quan hệ hardcode thay model. Chi tiết thực chạy trong
[VALIDATION_REPORT](VALIDATION_REPORT.md). Chưa tuyên bố RAG sẵn sàng hoặc benchmark90%.
