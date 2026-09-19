# Nhật Ký Làm Việc — Phiên #105: Triển Khai Khắc Phục Lỗ Hổng Kỹ Thuật (Remediation Execution)
**Thời gian**: 2026-09-19 | **Mục tiêu**: Triển khai giải pháp khắc phục toàn diện 5 lỗ hổng kỹ thuật phát hiện từ đợt rà soát hệ thống kỹ năng #104.

---

## 1. Mục Tiêu & Bối Cảnh Phiên Làm Việc
Sau khi thực hiện rà soát chuyên sâu 7 bộ kỹ năng hệ thống ở Phiên #104, phiên #105 tập trung giải quyết triệt để 5 điểm nghẽn kỹ thuật:
1. **Khuyết thiếu Node Handler `tool.api_caller`**: Dù catalog và workflow khai báo `tool.api_caller`, registry chưa có handler tương ứng dẫn tới lỗi `Unknown node type: tool.api_caller` khi chạy DAG.
2. **Kích hoạt lại Loại văn bản & Bảo toàn trạng thái User Override**: API mới chỉ có `/deactivate` mà thiếu `/activate`; thao tác đồng bộ catalog đè mất trạng thái tắt chủ động của người dùng.
3. **Thư viện Node gán cứng (Static Node Catalog)**: `NodeCatalogDrawer` sử dụng hằng số tĩnh 8 nodes và ép kiểu lệch `workflowNodeType` khi thêm vào canvas.
4. **Trọng số Pháp lý RRF (Legal Priority Boosting)**: Thuật toán RRF chưa tích hợp trường `priority` (1-10) của 37 loại văn bản theo chuẩn ĐH Quy Nhơn.
5. **Định danh Loại văn bản ép fallback ngầm**: `detectDocumentTypeFromFilename` tự động ép về `thong_bao` khi không có từ khóa hoặc ngữ cảnh kho rõ ràng.

---

## 2. Chi Tiết Các Thay Đổi Mã Nguồn (Key Changes)

### 2.1. Backend
- [`backend/app/modules/workflows/nodes/api_caller_node.py`](../../backend/app/modules/workflows/nodes/api_caller_node.py):
  - Hiện thực `APICallerNodeHandler` kế thừa `BaseNodeHandler`.
  - Khai báo Manifest: loại `tool.api_caller`, phiên bản `1.0.0`, category `tool`, config schema đầy đủ `tool_id`, `input_mapping`.
  - Tích hợp gọi công cụ qua `tool_registry.execute_tool`, lưu kết quả vào `result.output["tool_result"]` và nạp vào `context.inputs["tool_result"]`.
- [`backend/app/modules/workflows/nodes/__init__.py`](../../backend/app/modules/workflows/nodes/__init__.py) & [`backend/app/modules/workflows/registry.py`](../../backend/app/modules/workflows/registry.py):
  - Đăng ký chính thức `APICallerNodeHandler` vào `WorkflowNodeRegistry`.
- [`backend/tests/test_workflows.py`](../../backend/tests/test_workflows.py):
  - Bổ sung 2 bài kiểm thử: `test_api_caller_node_handler_execution_success` và `test_api_caller_node_handler_unknown_tool_fails`.
- [`backend/app/modules/document_types/service.py`](../../backend/app/modules/document_types/service.py):
  - Bổ sung phương thức `activate_document_type(db, code)`.
  - Sửa `sync_from_catalog`: Giữ nguyên `is_active` của bản ghi hiện tại thay vì ghi đè bằng `True`, bảo toàn quyền cấu hình của cán bộ.
- [`backend/app/modules/document_types/router.py`](../../backend/app/modules/document_types/router.py):
  - Bổ sung endpoint `POST /{code}/activate`.
- [`backend/tests/test_document_types.py`](../../backend/tests/test_document_types.py):
  - Bổ sung bài kiểm thử `test_document_type_activate_deactivate_and_sync_override`.
- [`backend/app/modules/rag/fusion.py`](../../backend/app/modules/rag/fusion.py):
  - Áp dụng công thức Trọng số Pháp lý trong `reciprocal_rank_fusion`:
    $$RRF\_Score(d) = \text{base\_score} \times \left(1.0 + (\text{priority} - 5) \times 0.02\right)$$
  - Văn bản có `priority = 10` (Quy chế, Quyết định) được cộng $+10\%$ điểm tương quan, đảm bảo ưu tiên văn bản quy phạm pháp luật khi tương quan gần bằng nhau.
- [`backend/tests/test_rag.py`](../../backend/tests/test_rag.py):
  - Bổ sung kiểm thử `test_reciprocal_rank_fusion_legal_priority_boost`.

### 2.2. Frontend
- [`frontend/src/services/document-types-api.ts`](../../frontend/src/services/document-types-api.ts):
  - Bổ sung hàm `activateDocumentType(code: string)`.
- [`frontend/src/pages/document-type-detail-page.tsx`](../../frontend/src/pages/document-type-detail-page.tsx):
  - Tích hợp `activateMutation` và chuyển đổi linh hoạt nút `[Vô hiệu hóa]` / `[Kích hoạt lại]`.
- [`frontend/src/components/admin/node-catalog-drawer.tsx`](../../frontend/src/components/admin/node-catalog-drawer.tsx):
  - Tải động danh mục `NodeManifest` từ API `systemApi.getNodeCatalog()`.
  - Hiển thị đầy đủ số lượng nodes, phiên bản và huy hiệu trạng thái (Active / Experimental).
- [`frontend/src/pages/dag-canvas-page.tsx`](../../frontend/src/pages/dag-canvas-page.tsx):
  - Sửa hàm `nodeTypeForCatalogItem` ánh xạ chính xác `item.type` sang `workflowNodeType` và gán `workflowNodeVersion`, loại bỏ ép kiểu sai lệch.
- [`frontend/src/lib/file-inspector.ts`](../../frontend/src/lib/file-inspector.ts):
  - Xóa bỏ fallback mặc định `thong_bao` trong `detectDocumentTypeFromFilename`, trả về `undefined` khi không đủ căn cứ nhằm kích hoạt kiểm tra người dùng.
  - Mở rộng `getPriorityForDocumentType` hỗ trợ tham số `priorityScore` (1-10) động từ CSDL.
- [`frontend/src/pages/document-ingest-page.tsx`](../../frontend/src/pages/document-ingest-page.tsx):
  - Hiển thị badge độ ưu tiên pháp lý trực tiếp cạnh ô chọn Loại văn bản và cảnh báo màu hổ phách khi chưa chọn.

### 2.3. Quy Trình Hệ Thống
- [`docs/quy_trinh/03_hybrid_rag_truy_xuat.md`](../quy_trinh/03_hybrid_rag_truy_xuat.md): Cập nhật công thức Trọng số Pháp lý trong Bước 5 RRF.
- [`docs/quy_trinh/04_dieu_phoi_tro_ly_dag.md`](../quy_trinh/04_dieu_phoi_tro_ly_dag.md): Bổ sung Mục 10 về Thư viện Node Động và `APICallerNodeHandler`.

---

## 3. Kết Quả Kiểm Thử (Verification)
- **Frontend Quality**:
  - `npm run lint`: 130 files checked, **0 lỗi**.
  - `npm run typecheck`: **0 lỗi**.
  - `npm run build`: Đóng gói bundle thành công trong 7.03s (2545 modules).
- **Backend Quality**:
  - `uv run ruff check .`: **0 lỗi** (All checks passed).
  - `uv run --extra dev pytest`: **216/216 passed (100%)** trong 77.29s.
  - Tối ưu tính độc lập kiểm thử: cấu hình `STORAGE_DRIVER = local` trong `backend/tests/conftest.py` và mock `get_db` cho `test_api_usage_stats_endpoint` loại trừ hoàn toàn việc treo chờ MinIO hay DB offline.
