# Phiên #405 — Fix duyệt Studio OCR và duyệt nhiều nguồn

## Mục tiêu

Sửa trường hợp cán bộ đã mở Studio OCR nhưng thao tác duyệt không ghi nhận được khi revision mang `status=ready` còn structured artifact vẫn `review.required`; đồng thời bổ sung duyệt nhiều nguồn trước khi xuất bản.

## Nguyên nhân và quyết định kiến trúc

- Trạng thái vòng đời parse (`revision.status`) và trạng thái kiểm duyệt dữ liệu cấu trúc là hai khái niệm khác nhau.
- Studio trước đây chỉ bật nút Duyệt khi `revision.status=review_required`, nên trạng thái legacy `ready + artifact required` không thể gọi API duyệt.
- Backend publish lại đọc artifact nên vẫn chặn đúng với `FACT_SET_REVIEW_REQUIRED`; frontend chỉ đọc source status nên hiển thị sai khả năng xuất bản.
- Structured artifact được chọn làm nguồn sự thật. Backend dẫn xuất `structured_review_status`, `requires_structured_review`, `structured_issue_count` tại read boundary; không tự duyệt và không dùng Redis làm trạng thái duyệt.

## Thay đổi chính

- Thêm helper dẫn xuất trạng thái duyệt dùng chung và trả trạng thái này trong source revision, binding và Studio response.
- Studio OCR cho phép duyệt cả revision `ready` nếu artifact thực sự còn yêu cầu duyệt; sau duyệt ghi audit actor/comment/time vào artifact.
- Thêm API duyệt hàng loạt tối đa 200 revision; khóa nguồn theo thứ tự ổn định, kiểm tra toàn bộ target trước rồi commit một lần.
- Dialog nạp vector hiển thị chính xác danh sách nguồn đang chặn publish, cho chọn nhiều nguồn bằng Checkbox và yêu cầu xác nhận trước khi duyệt.
- Frontend không còn bật Publish khi `requires_structured_review=true`; trang chi tiết cũng hiện banner duyệt cho trạng thái legacy lệch contract.
- Không tự động duyệt 8 nguồn hiện tại, không publish, không re-index và không xóa Redis.

## Tệp chính

- `backend/app/modules/knowledge/services/source_artifact.py`
- `backend/app/modules/knowledge/services/source_ingestion_service.py`
- `backend/app/modules/knowledge/services/binding_service.py`
- `backend/app/modules/knowledge/services/generation_candidate.py`
- `backend/app/modules/knowledge/{models.py,schemas.py,router.py}`
- `backend/tests/test_knowledge_source_ingestion.py`
- `frontend/src/features/knowledge/components/bulk-source-review.tsx`
- `frontend/src/features/knowledge/components/vector-load-controls.tsx`
- `frontend/src/components/knowledge/ocr/document-studio-workspace.tsx`
- `frontend/src/features/knowledge/utils/{studio-actions.ts,vector-workflow.ts}`
- `frontend/src/{services/knowledge-api.ts,types/knowledge.ts,types/studio-ocr.ts}`

## Kiểm thử

- Ruff toàn backend: đạt.
- Module source ingestion: `9 passed`.
- Regression review/bulk ban đầu: `4 passed`; tương thích Studio SimpleNamespace sau full suite: `4 passed`.
- Frontend utility regression: `9 passed`.
- Biome 11 tệp thay đổi: đạt.
- Vite build + TypeScript: đạt.
- Full backend chạy được 1009 test: tại thời điểm chạy có `982 passed, 15 failed, 9 errors, 3 skipped`. Bốn lỗi Studio phát sinh do DTO giả thiếu property mới đã được sửa và chạy lại `4/4`; 11 failure và 9 error còn lại là baseline ngoài phạm vi (quyền temp Windows, exporter/seed và API permission/role cũ).

## Bài học

Không được suy luận quyền publish chỉ từ một cột trạng thái tổng hợp. Mọi write gate, read DTO và UI action phải cùng đọc bất biến artifact; thao tác duyệt hàng loạt phải pin chính xác revision và chỉ commit sau khi toàn bộ mục đều hợp lệ.
