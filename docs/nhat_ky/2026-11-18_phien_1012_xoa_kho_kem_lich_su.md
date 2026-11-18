# Phiên 1012 — Xóa kho tri thức kèm lịch sử hội thoại

## Yêu cầu

- Người dùng đã gỡ kho "Tuyển sinh đại học QNU 2025" (`col_af3ea7d6d5fb`) khỏi
  trợ lý nhưng không xóa được kho: hệ thống báo "Kho còn hội thoại cũ đang trỏ
  vào. Hãy xóa các hội thoại đó trước khi xóa kho."
- Người dùng chọn phương án **"Thêm bước xóa kèm lịch sử"**: hộp thoại hiện số
  hội thoại/bài kiểm thử cũ đang giữ kho, kèm ô xác nhận "Xóa cả lịch sử hội
  thoại cũ"; giữ nguyên trợ lý; lần sau gỡ kho là xóa được.
- Kết thúc phiên: chạy xóa thật kho này tới trạng thái hoàn tất.

## Nguyên nhân

- `chat_conversations.collection_id` và `kb_answer_reviews.collection_id` là
  tham chiếu ngữ nghĩa (không FK) tới kho. Gỡ kho khỏi trợ lý chỉ đổi bảng liên
  kết, không đổi các dòng lịch sử, nên purge graph từ chối xóa kho.
- Trước đây chỉ đường xóa trợ lý mới giải phóng được các tham chiếu này.

## Thay đổi

- **`qnu/domains/lifecycle/purge_graph.py`**
  - `COLLECTION_TABLES` thêm `chat_conversations`, `kb_answer_reviews`,
    `kb_answer_review_items`.
  - `collection_history_counts()` đếm hội thoại và bài kiểm thử theo workspace +
    kho.
  - `_add_collection_history()` thêm hội thoại, các lượt hỏi của chúng, bài
    kiểm thử và các mục của bài kiểm thử vào graph.
  - `graph_for_collection(..., include_history=False)`: giữ nguyên chặn khi
    không kèm lịch sử (mã `collection_in_use_by_conversations`,
    `collection_in_use_by_answer_reviews`), chỉ đổi câu hướng dẫn sang "chọn xóa
    kèm lịch sử hội thoại".
- **`qnu/domains/lifecycle/purge.py`**
  - `_graph_for()` đọc `row.parameters["include_history"]` khi dựng lại đồ thị ở
    bước kiểm tra, xác nhận và thực thi (phòng vệ nhiều lớp).
  - `inspect_purge()` nhận `parameters`; impact của kho có thêm
    `history_included`, `conversations_to_delete`, `answer_reviews_to_delete`,
    `history_available_to_delete`.
- **`qnu/domains/lifecycle/schemas.py`**: `PreviewRequest.include_history`
  (mặc định `False`), chỉ hợp lệ với `(kind, action) == ("collection", "delete")`.
- **`qnu/domains/lifecycle/service.py`**: bỏ khóa `include_history` khỏi tham
  số đã lưu khi là `False`; truyền `parameters` vào `inspect_purge`.
- **`qnu/workers/settings.py`**: đăng ký thêm model `answer_review` và
  `conversations` cho tiến trình ARQ (xem mục lỗi bên dưới).
- **`frontendV2/src/api/lifecycle/types.ts`**: `LifecyclePreviewRequest` thêm
  `include_history`.
- **`frontendV2/src/components/knowledge/lifecycle-delete-dialog.tsx`**: khi
  preview trả 409 `collection_in_use_by_*` thì hiện bảng cảnh báo cam kèm ô
  "Xóa cả lịch sử hội thoại cũ"; bật ô này tạo lại preview kèm lịch sử; nút xóa
  chỉ bật khi preview hợp lệ; thêm dòng "Kèm theo N hội thoại và M bài kiểm thử
  câu trả lời cũng sẽ bị xóa vĩnh viễn."; đóng hộp thoại thì đặt lại trạng thái.

## Lỗi gặp trong phiên và cách xử lý

- Lần chạy thật đầu tiên: worker trả `source_purge_incomplete
  error_type=KeyError` cho biên nhận `lca_9cb2d9d14c5f`, chưa xóa dòng nào.
- Tái hiện bằng script chỉ đọc (dựng lại đồ thị + `_settled_plan` +
  `_assert_exclusive_blobs`, không xóa): `Base.metadata.tables["kb_answer_reviews"]`
  ném `KeyError` vì tiến trình ARQ không nạp model `answer_review`. Đây là lỗi
  phụ thuộc thứ tự import, không phải logic xóa.
- Sửa: đăng ký model `answer_review` và `conversations` trong
  `qnu/workers/settings.py`, cạnh dòng đăng ký `knowledge.review` đã có sẵn theo
  đúng quy ước repo. Không đổi logic purge.
- Sau khi khởi động lại worker, công việc chạy lại tự động và hoàn tất.

## Kiểm chứng

### Tĩnh (PASS)

- Ruff đạt trên `purge_graph.py`, `purge.py`, `schemas.py`, `service.py`,
  `workers/settings.py`; `ruff format --check` đạt.
- Biome đạt và `tsc --noEmit` đạt trên `frontendV2` (sau khi sửa FE trong phiên).
- Import smoke: `import qnu.workers.settings` → `kb_answer_reviews`,
  `chat_conversations`, `kb_review_submission_actions` đều có trong
  `Base.metadata.tables`.

### Sống (PASS)

- Preview kèm `include_history=true` + accept qua API :8002 thành công (biên nhận
  `lca_9cb2d9d14c5f`), chứng minh chuỗi preview → accept → worker chạy đúng.
- Worker lần 3 hoàn tất: `source_purge_job` trả `completed` trong 0,75 giây.
- Đọc lại DB sau khi xóa (chỉ đọc, workspace `ws_623614ba7fb8`):
  - `kb_collections`, `kb_sources`, `kb_folders`, `kb_upload_requests`,
    `kb_index_runs`, `kb_index_sync`, `chat_conversations`,
    `kb_answer_reviews`, `chat_assistant_collections` theo `col_af3ea7d6d5fb`:
    tất cả **0**.
  - Kho còn lại trong đơn vị: 1 (`col_e07f7b7ebb1b`, còn 1 nguồn).
  - Trợ lý `ast_44fc63a77512` còn nguyên, `collection_id = NULL`.
  - Toàn workspace còn 0 hội thoại và 0 bài kiểm thử cũ.
- Kết quả biên nhận: `files_deleted=2`, `sources_deleted=0`,
  `folders_deleted=0`, `permanent=true`, `restore_available=false`.

### NOT RUN

- Nhánh 409 khi preview **không** kèm lịch sử chưa chạy lại trên dữ liệu mới
  (kho đã bị xóa; không còn hội thoại nào ghim kho để tái hiện). Mã nhánh giữ
  nguyên điều kiện chặn cũ, chỉ đổi câu hướng dẫn.
- Kiểm tra trình duyệt cho hộp thoại mới (ô xác nhận + bảng cảnh báo) chưa chạy
  sống vì không còn kho nào có lịch sử ghim để tái hiện; FE mới qua Biome/tsc.
- Full suite, pytest, commit/push, deploy: **không chạy** theo quy ước phiên.

## Rủi ro và bước sau

- Người dùng cần biết: xóa kèm lịch sử là **không thể hoàn tác**, xóa cả hội
  thoại và bài kiểm thử cũ; trợ lý không bị xóa.
- Nếu sau này muốn giữ lịch sử, cần thiết kế chuyển lịch sử sang kho khác thay
  vì xóa (chưa làm).
- Worker dev đang chạy mã mới; API :8002 vẫn là tiến trình cũ nhưng không cần
  nạp lại cho thay đổi này (chỉ worker và FE dùng đường mới).
