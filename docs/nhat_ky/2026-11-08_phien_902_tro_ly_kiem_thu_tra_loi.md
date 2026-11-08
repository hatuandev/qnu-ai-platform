# Nhật ký phiên 902 — Trợ lý dễ cấu hình và kiểm thử câu trả lời

- Ngày: 2026-11-08.
- Nhánh: `feat/v1-user-workflow`, baseline `09a173a2`.
- Kế hoạch nguồn: [15 — Trải nghiệm người dùng QNU V1](../ke_hoach/15_ke_hoach_trai_nghiem_nguoi_dung_qnu_v1.md), gói P6.
- Trạng thái: P6 đã triển khai và kiểm chứng trong phạm vi; P7 chưa bắt đầu. Không commit/push, không migrate DB ứng dụng.

## 1. Yêu cầu và giả định

Yêu cầu của người dùng: “tiếp tục giai đoạn 6” — trợ lý dễ cấu hình và kiểm tra câu trả lời trung thực.

Giả định đã dùng, bám theo P6 trong kế hoạch 15:

- Form cơ bản chỉ ưu tiên tên, mục đích, kho được phép dùng và hướng dẫn trả lời; model/retrieval nâng cao giữ sau một khối mở rộng, không đổi default hiện hành.
- Kiểm thử trả lời tái sử dụng `answer()` hiện hành, không viết pipeline mới và không gọi model trong test.
- Chỉ tài liệu đã xuất bản được đưa vào phạm vi kiểm thử; collection không có tài liệu xuất bản thì từ chối chạy, UI nói rõ lý do, không mở draft vào retrieval công khai.
- Nhãn `correct/missing/wrong_source/wrong_year` là đánh giá của người kiểm thử, lưu schema riêng; không phải nhãn vàng retrieval và không ghi vào `gold_chunk_ids`.
- Lỗi hội thoại phải tách biệt: câu hỏi cần làm rõ, thiếu quyền, lỗi hạ tầng/model, kết quả kiểm chứng và “không đủ căn cứ” không được gộp thành một thông báo.

## 2. Thay đổi Backend

### 2.1. Readiness và phạm vi tri thức (P6.2)

- [assistants/schemas.py](../../backendV1/qnu/domains/assistants/schemas.py#L59) — thêm `AssistantReadiness` gồm `status`, số tài liệu đã xuất bản/đang phục vụ, `collection_name`, `index_run_id`, `index_generation`, lỗi sync.
- [assistants/service.py](../../backendV1/qnu/domains/assistants/service.py#L155) — `assistant_readiness()` đối chiếu snapshot xuất bản hiện hành với binding của active `IndexRun`/`IndexInput`, trạng thái `IndexSync` và readiness hiện có để trả `empty | syncing | ready | outdated | not_indexed | failed | uncertain`. Không suy “sẵn sàng” từ việc collection có tài liệu; `served_document_count` chỉ đếm binding khớp đúng document/version/publication/bundle/state.
- [assistants/router.py](../../backendV1/qnu/domains/assistants/router.py#L44) — `GET /workspaces/{workspace_id}/assistants/{assistant_id}/readiness`, kiểm quyền qua service hiện hành.

### 2.2. Answer review trên tài liệu đã xuất bản (P6.3–P6.6)

- Domain mới `backendV1/qnu/domains/answer_review/` với router prefix `/workspaces/{workspace_id}/assistants/{assistant_id}/answer-reviews`.
- [models.py](../../backendV1/qnu/domains/answer_review/models.py#L25) — hai bảng riêng `kb_answer_reviews` và `kb_answer_review_items`; item ghim `assistant_revision`, `index_run_id`, `generation`, `result` JSON và nhãn người kiểm tra (`label`, `label_note`, `labelled_by`, `labelled_at`).
- [schemas.py](../../backendV1/qnu/domains/answer_review/schemas.py#L13) — tối đa 3 câu hỏi, câu hỏi 1–8000 ký tự; nhãn chỉ thuộc bốn giá trị; `Idempotency-Key` bắt buộc cho POST.
- `service.py` — kiểm membership/role qua `resolve_workspace_access`; trợ lý phải active và collection phải có tài liệu đã xuất bản; chạy từng câu qua `answer()` với snapshot/collection/provider của trợ lý; item `answered | insufficient_evidence | failed | uncertain`; chỉ item `answered`/`insufficient_evidence` được gắn nhãn; admin/editor/reviewer mới được gắn, mọi thành viên được chạy/đọc.
- [0017_answer_review.py](../../backendV1/alembic/versions/0017_answer_review.py#L8) — migration additive `down_revision = "0016_review_submission"`, FK/unique/check theo workspace và tài nguyên; đăng ký ownership/schema/alembic/env.
- P6.6 giữ benchmark retrieval tách biệt: answer review không đọc/ghi `gold_chunk_ids`, không tự sinh nhãn.

### 2.3. Test backend

- `tests/integration/test_answer_review_p6.py` (4 ca): chạy trên nguồn đã xuất bản và lưu nhãn người; `insufficient_evidence` giữ trung thực; lỗi provider ghi theo từng item; trợ lý inactive/không có nguồn xuất bản bị từ chối.
- `tests/integration/test_assistant_readiness_p6.py` (3 ca): collection rỗng → `empty`; có xuất bản nhưng chưa index → không `ready`; index hoàn tất → `ready` kèm số tài liệu được phục vụ.

## 3. Thay đổi Frontend

### 3.1. Form trợ lý cơ bản/nâng cao (P6.1)

- [assistant-form-dialog.tsx](../../frontendV1/src/features/assistants/assistant-form-dialog.tsx#L108) — khối cơ bản giữ tên, mục đích, collection, hướng dẫn trả lời; model/retrieval/guardrail nằm trong `Collapsible` “Nâng cao”, mặc định đóng và không đổi giá trị hiện hành.

### 3.2. Phạm vi và readiness ở chi tiết trợ lý (P6.2)

- [readiness.ts](../../frontendV1/src/features/assistants/readiness.ts) — bảng badge và giải thích dùng chung; trạng thái `empty` nói rõ câu trả lời sẽ báo thiếu căn cứ, không dùng kiến thức ngoài kho.
- [assistant-detail-page.tsx](../../frontendV1/src/features/assistants/assistant-detail-page.tsx) — thẻ phạm vi tri thức + readiness, nút “Kiểm thử” cạnh “Trò chuyện”.

### 3.3. Bộ câu hỏi kiểm thử và nhãn (P6.3–P6.6)

- `features/answer-review/types.ts`, `permissions.ts`, `requests.ts`, `queries.ts`, `format.ts`: contract API, quyền gắn nhãn, query key theo `sessionId/workspace/assistant`, poll 4 giây chỉ khi review `running`, format lỗi riêng.
- [answer-review-sheet.tsx](../../frontendV1/src/features/answer-review/answer-review-sheet.tsx#L67) — Sheet “Kiểm thử trả lời” 1–3 câu hỏi; chặn chạy khi trợ lý inactive hoặc collection `empty`; `Idempotency-Key` giữ nguyên khi thử lại cùng bộ câu hỏi; POST dùng `timeoutMs: null` vì chạy đồng bộ nhiều câu.
- [ReadinessNotice](../../frontendV1/src/features/answer-review/answer-review-sheet.tsx#L448) — “Phạm vi kiểm thử: tài liệu đã xuất bản”; nói rõ không dùng bản nháp và không bổ sung kiến thức ngoài kho.
- [answer-review-item-card.tsx](../../frontendV1/src/features/answer-review/answer-review-item-card.tsx#L262) — hiển thị câu hỏi, câu trả lời, dẫn chứng mở qua `CitationSheet`, coverage, snapshot cấu hình/chỉ mục/generation và token sinh; [LabelSection](../../frontendV1/src/features/answer-review/answer-review-item-card.tsx#L291) chỉ hiện với người có quyền, kèm ghi chú nhãn không phải gold retrieval.
- [answer-review-result.tsx](../../frontendV1/src/features/answer-review/answer-review-result.tsx#L57) — thời gian chạy ghi rõ “đo tại trình duyệt”, không trộn với usage của model.

### 3.4. Phân loại lỗi hội thoại (P6.7)

- [schemas.ts](../../frontendV1/src/features/conversations/schemas.ts#L136) — `classifyConversationFailure()` tách `clarification | permission | verification | infrastructure | state | not_found | cancelled | unknown`; `formatConversationError()` bổ sung thông điệp cho `conversation_clarification_required`, `answer_scope_clarification_required`, `conversation_history_limit`, `conversation_route_invalid`, `chat_provider_changed/unavailable`, `conversation_turn_failed/uncertain/cancelled`, `workspace_forbidden/suspended/not_found`.
- [chat-message-item.tsx](../../frontendV1/src/features/conversations/chat-message-item.tsx#L374) — `FailedTurnAlert` hiển thị riêng: làm rõ câu hỏi (warning, không retry), thiếu quyền (destructive, không retry), kiểm chứng (warning, không retry), lỗi hạ tầng/model (destructive, có “Hỏi lại câu này”), lỗi trạng thái/khác. Lượt `uncertain` dùng lý do theo mã lỗi thay vì luôn nói “quá lease”.
- [chat-view.tsx](../../frontendV1/src/features/conversations/chat-view.tsx#L341) — lỗi clarification đưa câu hỏi trở lại ô nhập và toast warning; lỗi khác toast error. Trang lỗi hội thoại tách “không có quyền” (403/permission) khỏi “không tìm thấy”. [handleRetryLast](../../frontendV1/src/features/conversations/chat-view.tsx) luôn tạo lượt mới với khóa mới vì backend không chạy lại lượt đã thất bại theo khóa cũ; sau lỗi, invalidate chi tiết hội thoại để trạng thái failed/cancelled đã lưu hiện trong lịch sử.

### 3.5. Test frontend

- Mới `tests/v1-answer-review-p6.test.ts` (6 ca): URL/paging, POST câu hỏi đã trim + Idempotency-Key, PUT nhãn/ghi chú, ma trận quyền, query key theo phiên/workspace/assistant, phân biệt lỗi “không có nguồn xuất bản” với lỗi hạ tầng.
- Mới `tests/v1-conversation-errors-p6.test.ts` (4 ca): phân loại 4 nhóm lỗi; copy riêng cho clarification/permission/infrastructure/verification; “không khớp dữ liệu” khác lỗi hạ tầng; model switch/history limit có bước tiếp theo.
- Cập nhật `tests/template-boundary.test.ts`: allowlist `features/answer-review/` là mã V1 được gọi `v1Client`.

## 4. Phương pháp và lệnh thật

### 4.1. Backend

Từ `backendV1`, harness DB cô lập (không dùng DB ứng dụng):

```bash
export DATABASE_URL="$(grep -m1 '^DATABASE_URL=' ../.env | cut -d= -f2-)"
uv run python scripts/run_isolated_tests.py \
  tests/integration/test_answer_review_p6.py \
  tests/integration/test_assistant_readiness_p6.py -q
```

Kết quả: `7 passed, 2 warnings` trong 53,97s; receipt `qnu_v1_test_4b3102fecc634c6d`, `db_dropped: true`, `legacy_sentinel_preserved: true`, `pytest_exit: 0`, `seconds: 62.09`.

Ruff scoped:

```bash
uv run ruff check qnu/domains/answer_review \
  qnu/domains/assistants/{service,router,schemas}.py qnu/api/routes.py \
  alembic/env.py alembic/versions/0017_answer_review.py \
  tests/integration/conftest.py tests/integration/test_answer_review_p6.py \
  tests/integration/test_assistant_readiness_p6.py \
  qnu/platform/ownership.py qnu/platform/schema.py
```

Kết quả: `All checks passed!`.

Full backend suite: **NOT COMPLETED** — đã khởi chạy trên DB cô lập, 13 ca đầu đạt (không có F/E) rồi dừng vì tốc độ ~4 ca/phút không thể hoàn tất trong phiên; DB test đã được drop và thư mục runtime đã dọn. Giữ ghi nhận lỗi nền Redis751 từ các phiên trước; không tuyên bố toàn hệ thống PASS.

### 4.2. Frontend

Từ `frontendV1`:

```bash
npx biome check --write <các file P6>   # sạch sau khi format
npm run typecheck                       # tsc --noEmit, không lỗi
npx vitest run                          # 111 file / 911 test passed, 52,09s
npm run build                           # vite build + tsc thành công; còn cảnh báo chunk >500 kB có sẵn
```

### 4.3. NOT RUN

- Kiểm thị giác/tương tác trình duyệt cho “Kiểm thử trả lời”, dẫn chứng desktop/mobile và các trạng thái lỗi chat: **NOT RUN** — API/web không chạy trong phiên; DB ứng dụng vẫn ở `0014_publication_index_sync`, migration `0015/0016/0017` chưa áp dụng và migrate DB ứng dụng nằm ngoài phạm vi được giao.
- Citation chỉ được rà tĩnh: `CitationSheet` dùng `w-full sm:max-w-xl md:max-w-2xl`, metadata grid `grid-cols-2 sm:grid-cols-3`, trích đoạn cuộn trong khung; chưa chứng minh bằng ảnh chụp desktop/mobile.
- Không deploy, không migrate DB ứng dụng, không reindex, không gọi model thật, không restart dịch vụ.

## 5. Rủi ro và bước sau

- Cần áp migration `0015/0016/0017` ở môi trường phát triển được phép rồi kiểm đầu-cuối: chạy 1–3 câu trên collection có/không có tài liệu xuất bản; nhãn người kiểm tra; mở nguồn từ kết quả; các trạng thái clarification/permission/provider/verification trên desktop và mobile.
- Nghiệm thu P6: hội thoại thuộc đúng actor; query key không lẫn phiên; đúng assistant binding/snapshot; người kiểm tra mở được nguồn; latency đo tại trình duyệt tách khỏi token model; live model chỉ dùng provider/corpus được phép.
- Full backend suite cần chạy lại ở môi trường đủ nhanh; lỗi nền Redis751 vẫn phải xử lý riêng.
- P7 (pilot) chưa bắt đầu; không commit/push khi chưa có xác nhận.
