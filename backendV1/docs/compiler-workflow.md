# Nối hậu OCR, review tự động và sửa bản Compiler

Phạm vi: backendV1. Schema đã nằm trong `0001_initial_schema` (trước đây0013);
xem [migration](migrations.md). Frontend làm sau.
Workspace là biên quyền đơn vị theo ADR v1, không thay phạm vi backend cũ.

## 1. Chọn văn bản đầu vào

POST tạo Compiler giữ `topic`, `ocr_run_ids`, provider và budget cũ; thêm:

```json
{
  "topic": "Tổng hợp nội dung đã rà soát",
  "ocr_run_ids": ["ocr_example"],
  "text_versions": {"ocr_example": 1},
  "auto_review": true,
  "review_max_output_tokens": 8192
}
```

`text_versions` ánh xạ OCR run → số phiên bản đã lưu. Bỏ trống hoặc chọn `0`
dùng OCR gốc; không ngầm dùng bản sửa mới nhất. ID ngoài tập OCR bị từ chối422;
phiên bản không tồn tại/khác kho bị từ chối404. Có thể chọn riêng mỗi nguồn.

Compiler ghim ID, số phiên bản, hash JSON/Markdown đã sửa, hash canonical gốc và
manifest gốc. Worker, review, publication và index đọc lại đúng các binding đó,
kiểm cả hai tệp dẫn xuất. Một lần lưu văn bản mới không đổi nguồn Compiler cũ.
Muốn dùng phiên bản mới cần tạo lượt Compiler mới với lựa chọn tương ứng.

Citation của bản sửa có `artifact=text_review_document`, `text_version`,
`original_canonical_sha256` và `original_artifact`. Page/path/bbox/ô vẫn truy về
nguồn; manifest là manifest OCR gốc, không được coi là manifest của bản sửa.
Lưu sửa chữ chưa chứng minh đã đối chiếu ảnh. Raw/canonical/MD OCR gốc giữ nguyên.

## 2. Review tự động sau hoàn tất

Compiler mới mặc định `auto_review=true`. Có thể gửi `review_provider_id` để chọn
reviewer được cấp quyền; bỏ trống ghim ID provider của Compiler. Reviewer giải
quyết lại runtime ModelOps khi chạy, có grant/capacity/quota/usage riêng. Cấu hình
review không thay provider Compiler hoặc default của workspace. API review thủ công
cũ vẫn dùng default chat hiện hành khi không chỉ định provider.

Khi Compiler hoàn tất, cùng transaction lưu một intent trong
`kb_compilation_review_jobs`. Worker gửi việc `compiler_review_job` vào queue v1;
cron `compiler_review_reconcile` mỗi 5 phút tìm việc thiếu giao hoặc lease hết hạn.
Queue lỗi giữ intent; lỗi reviewer không làm Compiler đã hoàn tất thành thất bại.

GET `.../compilation-runs/{run_id}/auto-review` trả `status`, `review_id`, mã lỗi
và thời điểm. Đọc báo cáo bằng `/reviews/{review_id}/report` hoặc `/markdown` như
API cũ. Chưa có intent trả404, chẳng hạn run cũ hoặc đã chọn `auto_review=false`.

Khóa nội bộ `auto:{run_id}` cố định; giao trùng, mất worker hoặc mất cập nhật job
chỉ đọc lại cùng review đã lưu, không gửi lại request model. Lease job900giây;
review có thời hạn riêng tối thiểu900giây và checkpoint trước/sau HTTP. Nếu còn
review đang chạy, job chờ lần reconcile sau; quá hạn chuyển uncertain. Failed/
uncertain không tự retry model. Muốn kiểm tra lại cần chủ động tạo review thủ công
với key mới. Tiền tố `auto:` dành riêng, API thủ công từ chối key này.

Run cũ không được backfill review. Replay yêu cầu Compiler cũ không có các lựa
chọn mới vẫn dùng hash/hành vi cũ. Không tự tạo vòng lặp sửa, duyệt hay xuất bản.

## 3. Người dùng sửa bản biên soạn

Tiền tố: `/platform/v1alpha1/workspaces/{workspace_id}/collections/{collection_id}/compilation-runs/{run_id}`.

| API | Chức năng |
|---|---|
| GET `/edit-context` | Nội dung có thể sửa, bundle hash, số bản sửa, citation/bảng/nguồn bảo vệ |
| POST `/edit-previews` | Kiểm nội dung đề xuất, trả trước/sau, hash, hạn và căn cứ review |
| POST `/edits` | Chấp nhận chính xác preview, tạo Compiler run con đã lưu hoàn tất |

Chỉ admin/editor được sửa. Preview gắn actor, run, scope, hash bản gốc, số bản sửa,
reason và thời hạn theo `PUBLICATION_PREVIEW_TTL_SECONDS`. Request preview gồm:

```json
{
  "expected_bundle_sha256": "<hash từ edit-context>",
  "reason": "Bổ sung điều kiện bị bỏ sót sau đối chiếu nguồn",
  "review_id": null,
  "content": {
    "title": "Tiêu đề",
    "sections": [{"heading": "Nội dung", "paragraphs": [
      {"text": "Đoạn đã sửa", "citations": ["ocr_example:p1:b1"]}
    ]}],
    "unknowns": []
  }
}
```

`review_id` tùy chọn phải là báo cáo completed của đúng parent và đúng bundle;
server ghim hash báo cáo. Model không cung cấp actor/quyền/approval. Client không
được sửa bảng nguồn, citations metadata, source scope hoặc trạng thái xuất bản.
Các citation ID trong đoạn sửa vẫn phải thuộc nguồn đã ghim; lỗi nội dung trả422.

POST `/edits` bắt buộc Idempotency-Key và body `preview_id`, `preview_sha256`.
Server kiểm lại quyền, actor, expiry, nguồn hiện hành, hash preview/bundle/report,
và cạnh tranh lưu. Preview cũ/đã dùng bị từ chối; cùng key/body trả cùng child.
Key đã dùng cho preview khác trả409. Khoảng key nội bộ `edit:` dành cho bản sửa.

Child có `origin=user_edit`, `parent_run_id`, nguồn đã ghim giống parent; JSON và
Markdown mới được lưu/đọc kiểm toàn vẹn trước commit. Không có raw LLM giả, không
gọi lại Compiler, không tính token biên soạn giả. Reason/actor/preview/report/parent
bundle được ghi trong provenance và audit; parent và báo cáo cũ giữ nguyên.
Child luôn có intent review mới, sau đó vẫn cần đăng ký/duyệt/xuất bản riêng.
Review chưa phải cổng bắt buộc của publication và không bảo đảm đúng ngữ nghĩa.

Lỗi lưu tệp rollback toàn bộ bản mới. Blob ghi dở có thể còn mồ côi theo giới hạn
lưu trữ hiện có; chưa thêm GC. Không tự migrate/restart/reindex dữ liệu phục vụ.
