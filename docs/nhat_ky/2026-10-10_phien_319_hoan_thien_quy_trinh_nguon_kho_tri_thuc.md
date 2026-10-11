# Nhật Ký Phiên #319 — Hoàn Thiện Quy Trình Nguồn Kho Tri Thức: Staging Index, Retry & Workspace Isolation

- **Thời gian**: 2026-10-10
- **Phiên làm việc**: #319
- **Tác giả**: Senior Full-Stack Architect & Enterprise AI Systems Specialist
- **Mục tiêu**: Hoàn thiện toàn diện quy trình gắn Nhóm tài liệu vào Kho tri thức (`Thêm nguồn → Tạo liên kết → Build staging index → Chờ xuất bản → Promote active index → Sẵn sàng`), bảo đảm tính đúng đắn dữ liệu, cô lập Workspace, khôi phục retry khi gặp lỗi bóc tách, chuẩn hóa xử lý lỗi RFC 7807 và tinh gọn giao diện Group-first.

---

## 1. Bối Cảnh & Vấn Đề Giải Quyết

Trước phiên #319:
1. **Thiếu Staging Index Khi Attach**: `attach_group_source` chỉ tạo bản ghi binding và cập nhật `last_membership_hash` mà chưa thực sự gọi quy trình build staging index cho từng tài liệu. Nếu `auto_activate=False`, nguồn bị xem là `review_required` giả dù chưa có index nào được tạo.
2. **Race Condition & Mất Vết Lỗi Trong Retry**: Binding và `last_membership_hash` bị cập nhật trước khi build staging thành công. Khi một tài liệu bị lỗi, lần bấm "Thử lại" hoặc "Đồng bộ" tiếp theo xem tài liệu đó là `unchanged` và bỏ qua không build lại.
3. **Publish Không Kiểm Tra Staging Revision**: `publish_group_source` có thể báo thành công dù không có revision nào được promote (0 revision), gây nhầm lẫn trạng thái `ready` cho người dùng.
4. **Thiếu Workspace Isolation**: Nhiều hàm chỉ so sánh `tenant_id` mà bỏ qua `workspace_id`, tiềm ẩn rủi ro gắn chéo nhóm tài liệu giữa các không gian làm việc khác nhau trong cùng một trường học.
5. **Collection Fallback Giả & CTA Trùng Lặp Trên UI**: `collection-detail-page.tsx` tự bịa dữ liệu Kho tri thức fallback khi API chưa sẵn sàng; tab "Chọn riêng lẻ" vẫn xuất hiện dù chưa có màn hình publish riêng lẻ; nút "Thêm nguồn" bị lặp lại ở cả header và tab toolbar.

---

## 2. Kiến Trúc & Cải Tiến Kỹ Thuật

### 2.1. Chuẩn Hóa State Machine Nguồn Tri Thức
Áp dụng 5 trạng thái chuẩn tắc dựa trên bất biến dữ liệu:
- `pending`: Nguồn vừa được khởi tạo, đang chờ hoặc chưa hoàn thành staging build.
- `syncing`: Đang tính toán diff và thực hiện build staging index.
- `review_required`: Đã build staging index thành công cho các tài liệu sẵn sàng, có revision hợp lệ chờ người quản trị phê duyệt xuất bản.
- `ready`: Đã có active index hợp lệ và toàn bộ thay đổi cần thiết đã được promote xuất bản thành công.
- `failed`: Build staging hoặc publish gặp lỗi.

### 2.2. Quy Trình `attach_group_source` & `sync_group_source` Chuẩn
1. Xác thực chặt chẽ quyền sở hữu: Cả `collection` và `document_group` phải cùng `tenant_id` VÀ cùng `workspace_id`.
2. Tạo nguồn liên kết `KnowledgeGroupSource` với trạng thái ban đầu `syncing`.
3. Tạo / cập nhật các `KnowledgeBinding` ở trạng thái chờ.
4. Thực thi build staging index cho từng tài liệu `ready` (`target_source_revision_id = doc_rev.id`).
5. Thu thập kết quả chi tiết từng tài liệu (`DocumentSyncItemResult`):
   - `document_id`, `binding_id`, `source_revision_id`, `staging_revision_id`, `status` (`success` / `failed`), `error_code`, `error_message`.
6. **Bảo vệ Pointer**: Chỉ cập nhật `binding.source_revision_id` sang revision mới khi tài liệu đó build staging thành công. Nếu tài liệu lỗi, giữ nguyên con trỏ cũ.
7. **Bảo vệ Retry**: Không cập nhật `last_membership_hash` nếu còn bất kỳ tài liệu nào build staging thất bại. Lần sync/retry kế tiếp sẽ tiếp tục nhận diện đúng tài liệu lỗi và xử lý lại.
8. Nếu toàn bộ thành công:
   - `auto_activate=False`: Nguồn chuyển sang `review_required`.
   - `auto_activate=True`: Thực hiện promote sang active index; chỉ khi promote thành công mới chuyển sang `ready`.

### 2.3. Quy Trình `publish_group_source` Bảo Đảm An Toàn
- **Cấm Publish Giả**: Nếu không có staging revision nào sẵn sàng (`len(ready_revisions) == 0`), ném ngay ngoại lệ RFC 7807 với mã lỗi `NO_PUBLISHABLE_INDEX_REVISION` (HTTP 400).
- Duyệt qua từng binding có staging revision hợp lệ, promote sang `active_index_revision_id` và xóa cờ staging.
- Chỉ tăng `published_count` sau khi promote thành công.
- Nếu có lỗi trong quá trình promote: nguồn chuyển sang `failed`, trả danh sách lỗi theo từng tài liệu, giữ nguyên active index cũ không bị mất mát.
- Chỉ chuyển nguồn sang `ready` khi: có ít nhất 1 active index hợp lệ, không còn staging revision bắt buộc nào chưa xử lý, và toàn bộ promote thành công.

### 2.4. Bổ Sung Toàn Diện Workspace Isolation
Cưỡng chế kiểm tra `workspace_id` xuyên suốt:
- `preview_group_source`
- `attach_group_source`
- `sync_group_source`
- `publish_group_source`
- `detach_group_source`
- `get_group_source_detail`
Nghiêm cấm người dùng thuộc workspace A thao tác hoặc nhìn thấy nhóm tài liệu thuộc workspace B dù cùng tenant.

### 2.5. Tách Modular Service (Tránh Big-Ball-of-Mud)
Tách file monolith `group_source_service.py` thành 4 service chuyên biệt theo đúng Tôn chỉ 2 của `AGENTS.md`:
1. `group_source_diff_service.py`: Chịu trách nhiệm snapshot membership, diff 6 nhóm trạng thái (`added`, `updated`, `removed`, `unchanged`, `not_ready`, `failed`), tính hash và preview.
2. `group_source_sync_service.py`: Chịu trách nhiệm tạo binding, điều phối build staging index cho từng tài liệu, xử lý retry và cô lập partial failure.
3. `group_source_publish_service.py`: Chịu trách nhiệm validate readiness, promote staging sang active, tính toán trạng thái nguồn và detach an toàn.
4. `group_source_service.py`: Facade mỏng điều phối các luồng chung, cung cấp hàm tính toán metrics cho collection và re-export các helper tương thích ngược.

---

## 3. Cải Tiến Frontend & Tinh Gọn Trải Nghiệm (Group-First)

1. **Loại bỏ tab chọn riêng lẻ**: Trong `add-documents-page.tsx`, xóa bỏ hoàn toàn tab "Chọn riêng lẻ", tập trung 100% vào luồng Nhóm tài liệu trực quan, rõ ràng.
2. **Xóa bỏ Mock Collection Giả**: Trong `collection-detail-page.tsx`, xóa sạch mock object fallback ("Kho Tri Thức", chunker giả), hiển thị trạng thái Loading Skeleton hoặc Not Found rõ ràng kèm nút quay lại.
3. **Dọn CTA trùng lặp**: Trong `collection-group-sources-tab.tsx`, xóa nút "Thêm nguồn" dư thừa trên tab toolbar; giữ duy nhất 1 nút chính tại Topbar hoặc Empty state. Trên thẻ nguồn, chỉ giữ 1 hành động mở trang chi tiết.
4. **Trang chi tiết nguồn minh bạch (`source-detail-page.tsx`)**:
   - Dịch toàn bộ trạng thái nguồn sang tiếng Việt (`Đang chờ xử lý`, `Đang đồng bộ`, `Chờ xuất bản`, `Sẵn sàng`, `Lỗi xử lý`, v.v.).
   - Khi nguồn bị lỗi hoặc partial failure, hiển thị Banner cảnh báo nổi bật kèm nút **"Thử lại"** và bảng liệt kê chi tiết từng tài liệu bị lỗi kèm mã lỗi/nguyên nhân.
5. **Chuẩn hóa đọc lỗi RFC 7807**: Cập nhật helper `extractErrorMessage()` trong `knowledge-api.ts` để đọc ưu tiên: `detail` → `message` → chuỗi mặc định.

---

## 4. Kết Quả Kiểm Thử & Xác Nhận Chất Lượng

### 4.1. Backend Pytest Target Suite
Chạy kiểm thử bộ 15 ca test chuyên biệt tại `backend/tests/test_knowledge_group_sources.py`:
- `test_membership_hash_order_independence`: **PASSED**
- `test_attach_creates_staging_revision`: **PASSED**
- `test_attach_auto_activate_false_leads_to_review_required`: **PASSED**
- `test_attach_auto_activate_true_builds_and_promotes_to_ready`: **PASSED**
- `test_attach_auto_activate_error_fails_and_not_ready`: **PASSED**
- `test_publish_without_ready_staging_raises_rfc7807`: **PASSED**
- `test_publish_zero_revisions_does_not_set_ready`: **PASSED**
- `test_partial_publish_reports_errors`: **PASSED**
- `test_failed_new_build_retains_old_active_index`: **PASSED**
- `test_failed_staging_build_leaves_binding_revision_untouched`: **PASSED**
- `test_membership_hash_not_updated_when_sync_fails`: **PASSED**
- `test_subsequent_preview_detects_failed_documents`: **PASSED**
- `test_retry_success_updates_binding_and_hash_and_status`: **PASSED**
- `test_same_tenant_different_workspace_rejected`: **PASSED**
- `test_source_and_collection_metrics_based_on_real_active_indices`: **PASSED**

**Kết quả: 15/15 passed (100%) trong 4.31 giây.**

### 4.2. Backend Linter (Ruff)
```bash
uv run ruff check .
```
**Kết quả: All checks passed! (0 lỗi, 0 cảnh báo).**

### 4.3. Frontend Build (Vite & TypeScript)
```bash
npm run build
```
**Kết quả: Biên dịch thành công trong 3.68 giây, 0 lỗi TypeScript, 0 lỗi cú pháp.**

---

## 5. Danh Sách Tệp Thay Đổi

### Backend
- `backend/app/modules/knowledge/schemas.py`: Bổ sung `DocumentSyncItemResult`, `PublishGroupSourceResponse`, `DetachGroupSourceResponse`, mở rộng `SyncGroupSourceResponse`.
- `backend/app/modules/knowledge/services/group_source_diff_service.py`: Module tính diff, snapshot và workspace isolation.
- `backend/app/modules/knowledge/services/group_source_sync_service.py`: Module attach, build staging và retry.
- `backend/app/modules/knowledge/services/group_source_publish_service.py`: Module validate, promote và publish an toàn.
- `backend/app/modules/knowledge/services/group_source_service.py`: Facade điều phối và tính toán metrics.
- `backend/app/modules/knowledge/router.py`: Chuẩn hóa response models cho publish và detach.
- `backend/tests/test_knowledge_group_sources.py`: Bộ 15 ca kiểm thử bất biến toàn diện.

### Frontend
- `frontend/src/types/knowledge.ts`: Kiểu dữ liệu đồng bộ với backend schemas mới.
- `frontend/src/services/knowledge-api.ts`: Helper `extractErrorMessage` đọc RFC 7807 và chuẩn hóa kiểu dữ liệu trả về.
- `frontend/src/features/knowledge/collection-detail-page.tsx`: Xóa mock fallback, an toàn kiểu dữ liệu.
- `frontend/src/features/knowledge/add-documents-page.tsx`: Chuyển 100% sang Group-first flow.
- `frontend/src/components/knowledge/tabs/collection-group-sources-tab.tsx`: Dọn CTA trùng lặp, dùng design tokens.
- `frontend/src/features/knowledge/source-detail-page.tsx`: Dịch status tiếng Việt, nút Thử lại, bảng lỗi chi tiết theo tài liệu.

---

## 6. Cam Kết An Toàn
- **100% Không chỉnh sửa repository `qnu-sso`**.
- Không tự ý commit hoặc push git.
- Không tạo migration dư thừa hoặc phá vỡ cấu trúc cơ sở dữ liệu hiện hữu.
