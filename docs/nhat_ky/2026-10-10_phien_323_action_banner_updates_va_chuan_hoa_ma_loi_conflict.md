# NHẬT KÝ LÀM VIỆC — PHIÊN #323: HOÀN THIỆN ACTION BANNER UPDATES & CHUẨN HÓA MÃ LỖI CONFLICT NGUỒN NHÓM

- **Thời gian**: 2026-10-10
- **Dự án**: QNU AI Platform (`D:\DuAnPhanMem\qnu-ai-platform`)
- **Kỹ sư phụ trách**: Senior Full-Stack Architect & Enterprise AI Systems Specialist
- **Mục tiêu**: Sửa dứt điểm 3 vấn đề còn lại trong quy trình `Nhóm tài liệu → Nguồn Kho tri thức → Đồng bộ → Staging → Publish → Active RAG`:
  1. Frontend hiển thị thiếu action banner cho trạng thái `updates` (`needs_build_count > 0` hoặc `updates_available`) và còn trùng lặp nút CTA chính.
  2. Backend publish và sync ghi sai mã lỗi xung đột sở hữu thành `DOCUMENT_REVISION_FAILED` do duyệt lỗi revision chung trước khi duyệt `conflict_docs`.
  3. Đồng bộ hóa số liệu thực tế về số dòng mã nguồn và kết quả kiểm thử trong toàn bộ tài liệu dự án, bảo đảm tính trung thực tuyệt đối.

---

## 1. Phân Tích Nguyên Nhân Gốc Rễ (Root Cause Analysis)

### 1.1. Vấn đề 1: Thiếu Action Banner Cho Trạng Thái `updates` Trên Frontend
- **Nguyên nhân**: Trong `frontend/src/features/knowledge/source-detail-page.tsx`, biến `bannerType` được lấy từ `resolveSourceActionBanner(source)` (có thể trả về `"failed" | "review" | "updates" | "none"`). Tuy nhiên, trang chi tiết chỉ định nghĩa `shouldShowFailedBanner` và `shouldShowReviewBanner`, bỏ quên hoàn toàn `updates`. Khi nguồn có tài liệu mới cần build hoặc ở trạng thái `updates_available`, người dùng không nhìn thấy banner hành động phía trên. Đồng thời, tại `CardHeader` của Changes Diff Breakdown Card bên dưới, nút CTA chính "Đồng bộ / Thử lại" vẫn hiển thị song song kể cả khi banner phía trên đã kích hoạt, gây dư thừa và nhầm lẫn thao tác.

### 1.2. Vấn đề 2: Ghi Sai Mã Lỗi Conflict Thành `DOCUMENT_REVISION_FAILED`
- **Nguyên nhân**: Trong cả `group_source_publish_service.py` và `group_source_sync_service.py` (cả fast path lẫn post-sync re-evaluation), luồng xử lý lỗi duyệt danh sách `diff_after["items"]` trước. Với tài liệu xung đột, diff cũng phân loại vào `category="failed"`, dẫn đến việc tài liệu đó bị gắn mã lỗi chung `DOCUMENT_REVISION_FAILED`. Đến vòng lặp duyệt `diff_after["conflict_docs"]`, do kiểm tra `not any(it.document_id == doc.id for it in items)` trả về `False`, mã lỗi chuyên biệt `DOCUMENT_BOUND_TO_ANOTHER_GROUP_SOURCE` bị bỏ qua. Kết quả là `failed_count` được khử trùng đúng nhưng `error_code` và thông báo lỗi trả về sai ngữ nghĩa nghiệp vụ.

### 1.3. Vấn đề 3: Lệch Số Liệu Dòng Mã Nguồn Trong Tài Liệu Dự Án
- **Nguyên nhân**: Nhật ký phiên #322 và bảng tiến trình trước đó ghi nhận `group_source_sync_service.py` từ 917 dòng xuống còn 484 dòng (giảm 433 dòng). Trong thực tế, sau các bước bổ sung xử lý an toàn và types, file có 754 dòng (sau khi trích xuất helper hiện tại là 712 dòng). Cần cập nhật số liệu chuẩn xác, không tiếp tục lưu giữ số liệu ước lượng cũ.

---

## 2. Giải Pháp Kỹ Thuật Đã Triển Khai

### 2.1. Frontend: Action Banner "Có tài liệu cần đồng bộ" & Khử Trùng Lặp Nút CTA
- **Tệp sửa đổi**: `frontend/src/features/knowledge/source-detail-page.tsx`.
- **Triển khai**:
  1. Khai báo biến cờ:
     ```ts
     const shouldShowUpdatesBanner = bannerType === "updates";
     ```
  2. Bổ sung Action Banner thứ 3 theo thứ bậc ưu tiên bất biến `failed > review > updates > none`:
     - Container: `Card` với `border-warning/30 bg-warning/5 p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3`.
     - Icon Lucide: `Sparkles` (`size-5 text-warning`).
     - Tiêu đề: "Có tài liệu cần đồng bộ".
     - Mô tả: "Nhóm tài liệu đã có phiên bản tài liệu mới hoặc có thay đổi chưa được tạo chỉ mục staging. Bấm Đồng bộ để cập nhật."
     - Nút CTA chính: Tên ngắn gọn **"Đồng bộ"**, icon `RefreshCw`, gọi `syncMutation.mutate()`, disabled khi `isSyncing || publishMutation.isPending`.
     - 100% semantic design tokens, 0 emoji, responsive mượt mà trên mobile.
  3. Khử trùng lặp nút CTA ở `Changes Diff Breakdown Card`:
     - Nút phụ "Kiểm tra lại" (`refetchDiff()`) luôn hiển thị.
     - Nút CTA chính bên cạnh chỉ hiển thị khi `bannerType === "none"`. Khi đã có action banner ở trên (`failed`, `review`, hoặc `updates`), nút hành động chính ở dưới được ẩn đi để người dùng tập trung vào banner duy nhất.

### 2.2. Backend: Helper `populate_failed_items_from_diff` Chuẩn Hóa Thứ Tự Ưu Tiên Mã Lỗi
- **Tệp sửa đổi**:
  - `backend/app/modules/knowledge/services/group_source_diff_service.py`
  - `backend/app/modules/knowledge/services/group_source_publish_service.py`
  - `backend/app/modules/knowledge/services/group_source_sync_service.py`
- **Triển khai helper chuẩn hóa**:
  ```python
  def populate_failed_items_from_diff(
      diff: dict[str, Any],
      items: list[DocumentSyncItemResult],
      failed_document_ids: set[str],
  ) -> None:
      conflict_doc_ids: set[str] = set()

      # 1. ƯU TIÊN CAO NHẤT: Conflict ownership luôn duyệt trước
      for doc, rev, existing_bnd in diff.get("conflict_docs", []):
          conflict_doc_ids.add(doc.id)
          failed_document_ids.add(doc.id)
          if not any(it.document_id == doc.id for it in items):
              items.append(
                  DocumentSyncItemResult(
                      document_id=doc.id,
                      binding_id=existing_bnd.id,
                      source_revision_id=rev.id,
                      status="failed",
                      error_code="DOCUMENT_BOUND_TO_ANOTHER_GROUP_SOURCE",
                      error_message=f"Tài liệu '{doc.title}' đã thuộc nguồn nhóm khác trong kho tri thức này.",
                  )
              )

      # 2. Lỗi revision chung (failed/cancelled): Chỉ áp dụng cho tài liệu KHÔNG thuộc conflict
      for itm in diff.get("items", []):
          if itm.category == "failed" and itm.document_id not in conflict_doc_ids:
              failed_document_ids.add(itm.document_id)
              if not any(it.document_id == itm.document_id for it in items):
                  items.append(
                      DocumentSyncItemResult(
                          document_id=itm.document_id,
                          source_revision_id=itm.revision_id,
                          status="failed",
                          error_code="DOCUMENT_REVISION_FAILED",
                          error_message=itm.reason,
                      )
                  )
  ```
- **Áp dụng đồng bộ tại 3 điểm mấu chốt**:
  1. `group_source_publish_service.py`: Luồng sau khi publish và re-evaluate diff.
  2. `group_source_sync_service.py` (Fast path): Khi nhóm không có ready documents hoặc toàn bộ tài liệu lỗi.
  3. `group_source_sync_service.py` (Post-sync re-evaluation): Khi hoàn tất sync và đánh giá lại diff tổng thể.
- **Invariant bảo đảm**:
  - Conflict ownership $\rightarrow$ `DOCUMENT_BOUND_TO_ANOTHER_GROUP_SOURCE`.
  - Revision failed $\rightarrow$ `DOCUMENT_REVISION_FAILED`.
  - Build staging failed $\rightarrow$ `failure_code` hoặc `STAGING_BUILD_FAILED`.
  - Promote failed $\rightarrow$ `PROMOTE_FAILED`.
  - Mỗi tài liệu xuất hiện tối đa 1 lần trong `items` và `failed_document_ids`.

---

## 3. Danh Sách Tệp Đã Sửa Đổi

1. `backend/app/modules/knowledge/services/group_source_diff_service.py`:
   - Bổ sung helper `populate_failed_items_from_diff` ưu tiên conflict ownership trước revision failed.
2. `backend/app/modules/knowledge/services/group_source_publish_service.py`:
   - Thay thế vòng lặp duyệt lỗi sau publish bằng helper `populate_failed_items_from_diff`.
3. `backend/app/modules/knowledge/services/group_source_sync_service.py`:
   - Thay thế vòng lặp lỗi ở Fast path và Post-sync re-evaluation bằng helper `populate_failed_items_from_diff`.
   - File sau tối ưu đạt chính xác **712 dòng**.
4. `backend/tests/test_knowledge_group_sources.py`:
   - Bổ sung 4 regression test cases kiểm thử chi tiết `error_code` cho conflict vs revision failed.
5. `frontend/src/features/knowledge/source-detail-page.tsx`:
   - Khai báo `shouldShowUpdatesBanner` và render banner "Có tài liệu cần đồng bộ" với CTA "Đồng bộ".
   - Ẩn nút trùng lặp ở `Changes Diff Breakdown Card` khi có banner hoạt động.
6. `frontend/src/features/knowledge/utils/retry-decision.test.ts`:
   - Mở rộng 10 test cases bao phủ trọn vẹn 7 trạng thái banner (`failed`, `review`, `updates`, `none`), độ ưu tiên thứ bậc và retry action.
7. `docs/nhat_ky/2026-10-10_phien_322_sua_sau_nguon_nhom_kho_tri_thuc.md`:
   - Hiệu chỉnh số liệu dòng thực tế của `group_source_sync_service.py` (712 dòng thay vì 484 dòng).

---

## 4. Kết Quả Kiểm Thử Thực Tế

### 4.1. Frontend Unit Tests & Build Gate
- **Lệnh chạy unit test**:
  ```powershell
  node --experimental-strip-types --import ./src/app/auth/test-loader.mjs --test src/features/knowledge/utils/retry-decision.test.ts
  ```
  - **Kết quả**: `pass 10, fail 0` (10/10 test cases đạt 100%).
  - Đã bao phủ:
    1. `failed + awaiting_publish` $\rightarrow$ `failed`.
    2. `review_required` không failed $\rightarrow$ `review`.
    3. `needs_build_count > 0` $\rightarrow$ `updates`.
    4. `updates_available` $\rightarrow$ `updates`.
    5. `ready` $\rightarrow$ `none`.
    6. `empty` $\rightarrow$ `none`.
    7. `pending` $\rightarrow$ `none`.
    8. Thứ bậc ưu tiên: `failed > review > updates > none`.
    9. Retry action: failed + staging $\rightarrow$ `publish`, không staging $\rightarrow$ `sync`.

- **Lệnh build bundle**:
  ```powershell
  npm run build
  ```
  - **Kết quả**: `✓ built in 3.89s` (0 lỗi TypeScript, 0 lỗi biên dịch, exit code 0).

### 4.2. Backend Ruff Linter & Targeted Pytest Suite
- **Lệnh kiểm tra Ruff**:
  ```powershell
  .\.venv\Scripts\python -m ruff check app/modules/knowledge tests/test_knowledge_group_sources.py
  ```
  - **Kết quả**: `All checks passed!` (0 lỗi linting, 0 cảnh báo).

- **Lệnh chạy Targeted Pytest**:
  ```powershell
  .\.venv\Scripts\python -m pytest -q tests/test_knowledge_group_sources.py tests/test_document_repository_workflow.py tests/test_rag.py tests/test_knowledge_publishing_v2.py
  ```
  - **Kết quả**: **89 passed, 1 skipped** (100% targeted tests đạt).
  - Bao gồm 4 ca kiểm thử bất biến mới:
    - Ca 1: Một conflict duy nhất $\rightarrow$ `failed_count == 1`, `error_code == "DOCUMENT_BOUND_TO_ANOTHER_GROUP_SOURCE"`.
    - Ca 2: Một revision failed thông thường $\rightarrow$ `error_code == "DOCUMENT_REVISION_FAILED"`.
    - Ca 3: Một conflict và một build failure ở 2 tài liệu $\rightarrow$ `failed_count == 2`, mỗi tài liệu xuất hiện đúng 1 lần, conflict giữ mã ownership, build failure giữ mã build tương ứng (`STAGING_BUILD_FAILED`).
    - Ca 4: Publish có 1 tài liệu thành công và 1 tài liệu conflict $\rightarrow$ conflict không bị biến thành `DOCUMENT_REVISION_FAILED`, `published_count == 1`, `failed_count == 1`, `res.status == "failed"`.

### 4.3. Kiểm Tra Git Diff
- **Lệnh chạy**:
  ```powershell
  git diff --check
  ```
  - **Kết quả**: Exit code 0, không có lỗi whitespace hay conflict marker nào.

---

## 5. Hiện Trạng Baseline & Các Lỗi Tồn Đọng Ngoài Phạm Vi

- **Phạm vi task**: Hoàn tất 100% 3 vấn đề của quy trình `Nhóm tài liệu → Nguồn Kho tri thức → Đồng bộ → Staging → Publish → Active RAG`.
- **Không có bất kỳ tệp nào trong `qnu-sso` bị chỉnh sửa**.
- **Không có migration CSDL mới hay thay đổi DB schema**.
- **Ghi nhận trung thực các lỗi baseline ngoài phạm vi**:
  - Khi chạy full backend test suite (`pytest -q`), các bài kiểm tra ngoài phạm vi (như kiểm tra phân quyền RBAC HTTP 403 do role `AI.Admin` và một số file khóa tạm của Windows) vẫn là baseline cũ tồn tại từ trước và không bị ảnh hưởng bởi thay đổi này.

---

## 6. Bài Học Kinh Nghiệm (Lessons Learned)

1. **Thứ tự duyệt trong Data Transformation có tính quyết định ngữ nghĩa**: Khi xử lý danh sách lỗi phân tầng (Hierarchical Error Resolution), lỗi chuyên biệt (Specific Errors như Conflict Ownership) bắt buộc phải được xử lý và đánh dấu trước lỗi tổng quát (Generic Errors như Revision Failed).
2. **Khử trùng UI Action là cốt lõi của UX tinh tế**: Việc xuất hiện 2 nút CTA cùng thực hiện một hành động (ở action banner và bảng chi tiết bên dưới) làm suy giảm tính định hướng của người dùng. Cần áp dụng quy tắc: khi đã có Action Banner chính ở đầu trang, các nút thao tác tương tự bên dưới phải ẩn đi hoặc nhường quyền ưu tiên cho banner.
3. **Trung thực số liệu tài liệu**: Tuyệt đối không phỏng đoán số dòng hay sao chép con số ước lượng. Mọi báo cáo kỹ thuật phải dựa trên lệnh đo đạc thực tế (`Measure-Object -Line` / `.Count`).
