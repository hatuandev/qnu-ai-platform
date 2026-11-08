# Nhật ký phiên 901 — Xuất bản, cập nhật và trạng thái phục vụ trung thực

- Ngày: 2026-11-08.
- Nhánh: `feat/v1-user-workflow`, baseline `09a173a2`.
- Kế hoạch nguồn: [15 — Trải nghiệm người dùng QNU V1](../ke_hoach/15_ke_hoach_trai_nghiem_nguoi_dung_qnu_v1.md), gói P5.
- Trạng thái: P5 đã triển khai, kiểm chứng trong phạm vi; P6–P7 chưa bắt đầu. Không commit/push, không migrate DB ứng dụng.

## 1. Yêu cầu và giả định

Yêu cầu của người dùng: “tiếp tục giai đoạn 5” — xuất bản, cập nhật không gián đoạn và trạng thái phục vụ phải trung thực.

Giả định đã dùng, bám theo P5 trong kế hoạch 15:

- Tái sử dụng index sync outbox, readiness binding và replacement atomic hiện có; P5 chủ yếu là read model và cách trình bày trung thực, không dựng cơ chế đồng bộ mới.
- Không thay ranking/chunking trong batch này.
- Server là nguồn sự thật cho “đang phục vụ”: chỉ hiển thị bản phục vụ khi readiness `ready` và binding chỉ mục trỏ đúng phiên bản; không suy từ thời điểm hay thứ tự danh sách.
- “Bản cũ vẫn phục vụ” chỉ được nói sau xác nhận server (`current_publication_retained === true`); nếu không xác nhận được thì yêu cầu người dùng kiểm tra trang tài liệu.
- Luồng revision thay thế mặc định `staged=true` ở UI, backend vẫn giữ mặc định `staged=False` cho client khác; preview thay bản giải thích điều kiện chặn và không hứa thay thế hàng loạt.
- Dẫn chứng hội thoại cũ tiếp tục được kiểm quyền/lifecycle khi đọc lịch sử; lý do không khả dụng là trường phản hồi, không thêm cột DB.

## 2. Thay đổi Backend

### 2.1. Tham chiếu chuẩn bị / xuất bản / phục vụ

[publication/schemas.py](../../backendV1/qnu/domains/knowledge/publication/schemas.py#L171) — `DocumentSummaryResponse` thêm:

- `prepared_version`: phiên bản `draft`/`approved` mới nhất của tài liệu (nếu có).
- `served_version`: phiên bản mà readiness đang thật sự phục vụ (nếu có).

[publication/summary.py](../../backendV1/qnu/domains/knowledge/publication/summary.py#L118):

- `prepared` lấy bản `draft`/`approved` có `version_no` lớn nhất, cùng tài liệu.
- `served` chỉ truy vấn khi `readiness.status == "ready"` và `readiness.version_id` có giá trị; truy vấn giới hạn đúng `document_id`, `workspace_id`, `collection_id` để không trả phiên bản ngoài phạm vi.
- `published_version` giữ nguyên nghĩa “bản được chọn để xuất bản”; ba tham chiếu có thể khác nhau trong lúc chờ đồng bộ hoặc khi thay bản thất bại.

Không cần migration cho P5.

### 2.2. Lý do nguồn cũ không còn khả dụng

[conversations/schemas.py](../../backendV1/qnu/domains/conversations/schemas.py) — `TurnResponse` thêm `source_status_reason: str | None = None` (chỉ phản hồi, không lưu DB).

[conversations/history.py](../../backendV1/qnu/domains/conversations/history.py#L18) — ánh xạ mã lỗi kiểm chứng sang lý do người đọc hiểu được: `resource_unavailable`, `answer_evidence_changed`, `index_outdated`, `index_configuration_changed`, `embedding_dimension_stale`, `provider_inactive`, `provider_not_found`, `publication_source_stale`, `published_compilation_not_found`. Mã lạ dùng câu chung; không mở artifact bằng đường dẫn khi chưa qua guard.

### 2.3. Test backend

- `tests/integration/test_knowledge_summary_api.py`: summary trả `prepared_version`/`served_version` đúng; tài liệu đã xuất bản nhưng chưa có chỉ mục thì `served_version` và `prepared_version` đều `null`.
- `tests/integration/test_lifecycle_runtime_659.py`: sau thay bản thất bại, `served_version` và `published_version` vẫn là bản cũ, `prepared_version` là bản ứng viên đã duyệt; sau thành công, `prepared_version` về `null` và serving khớp bản mới.
- `tests/integration/test_conversations_649.py`: lượt cũ sau thu hồi trả `source_status_reason` nêu bằng chứng/phiên bản đã thay đổi.

## 3. Thay đổi Frontend

### 3.1. Thẻ “Tham chiếu phục vụ” (P5.2)

- [summary-types.ts](../../frontendV1/src/features/knowledge/summary-types.ts): thêm `prepared_version`, `served_version`.
- Mới [serving-references.tsx](../../frontendV1/src/features/knowledge/serving-references.tsx): một thẻ ba cột “Bản chuẩn bị / Bản đã xuất bản / Bản đang phục vụ”, mỗi cột có số phiên bản và liên kết mở đúng version; phần cảnh báo nêu rõ khi bản xuất bản chưa được xác nhận là bản đang phục vụ, hoặc khi serving đang là bản cũ hơn bản xuất bản.
- [compiled-document-detail-page.tsx](../../frontendV1/src/features/knowledge/compiled-document-detail-page.tsx): gắn thẻ sau banner xuất bản; badge “Đang phục vụ” chỉ gắn khi `summary.served_version.id === version.id`, không dùng `serving_matches_published` làm suy luận thay thế.

### 3.2. Thay bản trung thực (P5.3, P5.4)

- [action-receipt.tsx](../../frontendV1/src/features/lifecycle/action-receipt.tsx): trạng thái `pending`/`failed` của `replace` chỉ nói bản xuất bản hiện tại được giữ khi `action.result.current_publication_retained === true`; nếu thiếu xác nhận, hiển thị “Đang chờ máy chủ xác nhận…” hoặc yêu cầu kiểm tra trang tài liệu. Trạng thái `completed` với `current_publication_retained === false` mới nói đã chuyển bản xuất bản và chỉ mục.
- [document-replacement.tsx](../../frontendV1/src/features/lifecycle/document-replacement.tsx): giải thích bản xuất bản hiện tại được giữ trong lúc chuẩn bị và chỉ chuyển khi chỉ mục mới sẵn sàng; nêu rõ chỉ phiên bản đã duyệt được chọn, preview sẽ báo tài liệu chưa xuất bản/nguồn dùng chung xung đột và hệ thống không tự thay thế hàng loạt.
- [revision-upload-dialog.tsx](../../frontendV1/src/features/knowledge/revision-upload-dialog.tsx) đã mặc định `staged=true` từ trước; P5 giữ nguyên và không đổi backend default `staged=False`.
- [Quy trình 34](../quy_trinh/34_frontend_vong_doi_thay_the_va_van_hanh.md) cập nhật lời xác nhận thay bản: chỉ nói bản cũ được giữ khi server xác nhận, và mô tả ba tham chiếu trên trang tài liệu.

### 3.3. Dẫn chứng và chẩn đoán (P5.6, P5.7)

- [types.ts](../../frontendV1/src/features/conversations/types.ts): `TurnResponse.source_status_reason`.
- [chat-message-item.tsx](../../frontendV1/src/features/conversations/chat-message-item.tsx): cảnh báo nguồn không khả dụng hiển thị lý do server, fallback câu chung; vẫn nói rõ câu trả lời cũ không còn hiệu lực.
- [chat-view.tsx](../../frontendV1/src/features/conversations/chat-view.tsx): lượt đang gửi (optimistic) có `source_status_reason: null`.
- [citation-sheet.tsx](../../frontendV1/src/features/conversations/citation-sheet.tsx): bỏ câu khẳng định “đã qua kiểm tra xuất bản” như trạng thái vĩnh viễn; ghi “Dẫn chứng được xác minh khi tải câu trả lời; mở nguồn sẽ kiểm tra lại quyền và trạng thái xuất bản.”
- [search-availability.tsx](../../frontendV1/src/features/knowledge/search-availability.tsx): mã lỗi kỹ thuật chỉ hiển thị khi `canRetry` (người có quyền); nút “Thử cập nhật” vẫn chỉ dành cho người có quyền, “Kiểm tra lại” là đọc lại trạng thái.

### 3.4. Test frontend

- Mới `tests/serving-references-p5.test.ts` (5 ca): ba tham chiếu tách biệt; cảnh báo khi bản xuất bản chưa được xác nhận phục vụ; nêu cả hai phiên bản khi serving cũ hơn; bản nháp không bị mô tả là “chờ quyết định xuất bản”; không render khi thiếu summary.
- Mới `tests/conversation-source-unavailable-p5.test.tsx` (1 ca): hiển thị đúng lý do server và câu “Câu trả lời cũ không còn hiệu lực.”
- Cập nhật `tests/replacement-ui-678.test.tsx`, `tests/lifecycle-operations-ui-678.test.tsx` theo lời xác nhận server; thêm ca chuyển bản hoàn tất với `current_publication_retained: false`.
- Cập nhật fixture `tests/v1-conversations.test.ts`, `tests/conversation-direct-reply-855.test.tsx`, `tests/rag-ui-674.test.tsx` cho trường mới.

## 4. Phương pháp và lệnh thật

### 4.1. Backend

Từ `backendV1`, dùng harness DB cô lập (không chạy trên DB ứng dụng):

```bash
export DATABASE_URL="$(grep -m1 '^DATABASE_URL=' ../.env | cut -d= -f2-)"
uv run python scripts/run_isolated_tests.py \
  tests/integration/test_knowledge_summary_api.py \
  tests/integration/test_lifecycle_runtime_659.py \
  tests/integration/test_conversations_649.py \
  -k "summary or replacement or old_source_content"
```

Kết quả: `13 passed, 42 deselected` trong 124,54s; receipt `qnu_v1_test_b470112d6a6e4aa6`, `db_dropped: true`, `legacy_sentinel_preserved: true`, `pytest_exit: 0`, `seconds: 132.53`.

```bash
uv run python scripts/run_isolated_tests.py \
  tests/integration/test_publication_index_sync_878.py \
  tests/integration/test_index_readiness_819.py
```

Kết quả: `13 passed` trong 81,94s; receipt `qnu_v1_test_7e9428e81f2b410b`, `db_dropped: true`, `legacy_sentinel_preserved: true`, `pytest_exit: 0`, `seconds: 89.72`. Hai file này phủ publish → sync chậm/lỗi/thành công, nhiều publication trong collection, thu hồi trong lúc build và retry idempotent.

Ruff scoped:

```bash
uv run ruff check \
  qnu/domains/knowledge/publication/schemas.py \
  qnu/domains/knowledge/publication/summary.py \
  qnu/domains/conversations/schemas.py \
  qnu/domains/conversations/history.py \
  tests/integration/test_knowledge_summary_api.py \
  tests/integration/test_lifecycle_runtime_659.py \
  tests/integration/test_conversations_649.py
```

Kết quả: `All checks passed!`.

Full backend suite: **NOT COMPLETED** trong phiên này (không chạy lại toàn bộ); giữ ghi nhận lỗi nền Redis751 và lần chạy chưa hoàn tất ở phiên 900. Không tuyên bố toàn hệ thống PASS.

### 4.2. Frontend

Từ `frontendV1`:

```bash
npx biome check <17 file P5>   # Checked 17 files. No fixes applied.
npm run typecheck              # tsc --noEmit, không lỗi
npm run test                   # 109 file / 901 test passed, 54,93s
npm run build                  # vite build thành công; còn cảnh báo chunk >500 kB có sẵn
```

### 4.3. NOT RUN

- Kiểm thị giác/tương tác trình duyệt cho thẻ tham chiếu phục vụ, thay bản và cảnh báo dẫn chứng: **NOT RUN** — không có dev server API/web trong phiên; DB ứng dụng vẫn ở `0014_publication_index_sync`, migration `0015/0016` chưa áp dụng và migrate DB ứng dụng nằm ngoài phạm vi được giao.
- Không deploy, không migrate DB ứng dụng, không reindex, không gọi model thật, không restart dịch vụ.

## 5. Rủi ro và bước sau

- Cần áp migration `0015/0016` ở môi trường phát triển được phép rồi kiểm đầu-cuối: publish → sync chậm/lỗi/thành công; thay bản khi collection có nhiều publication; thu hồi trong lúc build; mở dẫn chứng cũ sau thu hồi; phân quyền retry/chẩn đoán.
- Khi nghiệm thu, xác nhận trên UI rằng ba tham chiếu không bị nhập nhằng và cảnh báo chỉ xuất hiện đúng trạng thái server.
- Full backend suite cần chạy lại ở môi trường đủ nhanh; lỗi nền Redis751 vẫn phải xử lý riêng.
- P6 (trợ lý dễ cấu hình và kiểm tra câu trả lời) và P7 (pilot) chưa bắt đầu.
