# NHẬT KÝ LÀM VIỆC — PHIÊN #114
# Ngày: 2026-09-19 | Triển Khai Giai Đoạn 4: Node Catalog Contract, DAG Schema Validation & Approval Inbox Vận Hành

---

## 1. Mục Tiêu Phiên Làm Việc
Khắc phục triệt để các khoảng hở kết nối thuộc Giai đoạn 4 theo tài liệu [docs/nhan_xet_khoang_ho_ket_noi_toan_app_2026-09-19.md](../nhan_xet_khoang_ho_ket_noi_toan_app_2026-09-19.md):
- **P1-07**: Biến Node Catalog thành runtime contract có Schema Validation phía backend; loại bỏ catalog tĩnh lỗi thời trên frontend.
- **P1-08**: Xóa nhãn tĩnh và gán cứng tham số trên Canvas Inspector; đồng bộ hai chiều (Two-Way Binding) giữa Tab Trực Quan và Tab JSON Schema; lưu cấu hình thực tế vào `workflowConfig`.
- **P2-08**: Bổ sung bảng tiếp nhận và nút phê duyệt checkpoint Human-in-the-loop (HITL) trực tiếp tại trang `/runs` mà không cần mở In-Canvas Test Runner.

---

## 2. Chi Tiết Các Thay Đổi Kỹ Thuật (Key Changes)

### 2.1. Backend Compiler & Node Catalog Validation (P1-07)
- **`backend/app/modules/node_catalog/service.py`**:
  - Bổ sung phương thức đồng bộ `get_manifests_map()` nạp toàn bộ 13 NodeManifests từ `configs/nodes/*.json` thành từ điển tra cứu nhanh theo `node_type` cho `WorkflowCompiler`.
- **`backend/app/modules/workflows/compiler.py`**:
  - Thêm bảng ánh xạ Canonical Aliases (`_CANONICAL_TYPE_ALIASES`) hỗ trợ phân giải các alias lịch sử (`input.chat` -> `chat_input`, `core.knowledge.answer` -> `knowledge_retrieval`, `core.drafting.compose` -> `compose`,...).
  - Xây dựng hàm `_validate_node_config_schema(node_id, node_type, config, config_schema)`:
    - Kiểm tra các trường bắt buộc (`required`): Báo lỗi `workflow_node_config_missing_required` nếu thiếu.
    - Kiểm tra kiểu dữ liệu: `string`, `integer`, `number`, `boolean`, `array`, `object`. Báo lỗi `workflow_node_config_type_mismatch`.
    - Kiểm tra tập giá trị `enum`: Đối soát với danh mục cho phép, hỗ trợ chuỗi tách bằng dấu phẩy như `"docx,pdf"`. Báo lỗi `workflow_node_config_invalid_enum`.
    - Kiểm tra vòng đời manifest: Cảnh báo nếu manifest `deprecated`, chặn xuất bản nếu manifest `inactive` (`workflow_node_manifest_inactive`).
- **`backend/tests/test_workflows.py`**:
  - Bổ sung 4 test cases mới:
    1. `test_compiler_validates_node_config_schema_missing_required_field`: Kiểm tra bắt lỗi thiếu trường bắt buộc.
    2. `test_compiler_validates_node_config_schema_success`: Kiểm tra biên dịch thành công khi đủ cấu hình schema.
    3. `test_compiler_validates_node_config_type_mismatch_and_enum`: Kiểm tra bắt lỗi sai kiểu dữ liệu và sai giá trị enum.
    4. `test_workflow_approval_api_endpoints`: Kiểm tra danh sách checkpoint chờ duyệt (`GET /approvals`) và quyết định phê duyệt (`POST /executions/.../approvals/.../decision`).
  - Toàn bộ **24/24 tests trong `test_workflows.py` đã passed 100%**.

### 2.2. Frontend Schema-Driven Property Inspector Two-Way Binding (P1-08)
- **`frontend/src/components/admin/property-inspector.tsx`**:
  - Viết lại toàn diện Property Inspector hỗ trợ đồng bộ hai chiều (Two-Way Binding) giữa **Tab Trực Quan (Visual Form)** và **Tab Mã Nguồn (JSON Schema)**.
  - Xóa bỏ toàn bộ nhãn tĩnh gán cứng (`Top K 8`, `RRF k=60`).
  - Xây dựng các form controls chuyên biệt tương tác với cấu hình thực tế:
    - **Knowledge Answer (RAG)**: Search Mode (`hybrid`, `vector_dense`, `keyword_lexical`), Top-K Chunks (1-20), Minimum RRF Score, Fact Layer Threshold, Target Collection.
    - **API Caller (Tool)**: Target Tool ID, Timeout (ms), Max Retry Attempts.
    - **Condition Route**: Default Branch, Danh sách Routing Conditions theo regex/keyword.
    - **Drafting / LLM**: Max Tokens, Temperature, Strict Markdown.
    - **Human Approval**: Reviewer Role, Approval Prompt Message.
    - **Citation Guard**: Minimum Citation Score, Fallback Mode.
    - **Output Chat / Terminal**: Response Format, Output Template.
  - Lưu trữ trực tiếp vào `node.data.workflowConfig` và gọi `onUpdateNodeConfig`.

### 2.3. Frontend Node Catalog Drawer & Default Config (P1-07)
- **`frontend/src/components/admin/node-catalog-drawer.tsx`**:
  - Chuẩn hóa danh mục `CATALOG_NODE_ITEMS` fallback khớp 13 manifest chính thức của platform.
  - Viết helper `extractDefaultConfig(schema)` tự động trích xuất các giá trị mặc định từ `config_schema`.
- **`frontend/src/pages/dag-canvas-page.tsx`**:
  - Trong `handleAddNodeFromCatalog`, khởi tạo `workflowConfig` bằng `defaultConfig` trích xuất từ manifest thay vì `{}` rỗng, ngăn ngừa tình trạng node mới thiếu trường gây lỗi compiler.

### 2.4. Approval Inbox Vận Hành Trực Tiếp Tại `/runs` (P2-08)
- **`frontend/src/types/workflows.ts`**:
  - Khai báo interface `WorkflowApproval` gồm `id`, `execution_id`, `checkpoint_id`, `node_id`, `description`, `status`, `decided_by`, `decision_reason`, `created_at`.
- **`frontend/src/services/workflows-api.ts` & `frontend/src/services/workflow-runs-api.ts`**:
  - Thêm `getPendingApprovals()` (`GET /workflows/approvals`).
  - Thêm `decideApproval(executionId, approvalId, payload)` (`POST /workflows/executions/{executionId}/approvals/{approvalId}/decision`).
- **`frontend/src/pages/runs-page.tsx`**:
  - Tích hợp `useQuery` gọi `apiClient.getPendingApprovals()` với `refetchInterval: 8000` (polling nền mỗi 8 giây).
  - Bổ sung section **Hộp Thư Phê Duyệt Tác Vụ (HITL Approval Inbox)**: hiển thị danh sách checkpoint đang chờ duyệt, mã Run ID, Node ID, thông điệp kiểm duyệt, cùng cặp nút hành động nhanh **[Phê duyệt]** và **[Từ chối]**.
  - Bổ sung modal **Approval Decision Dialog**: cán bộ nhập họ tên/chức danh (`decided_by`) và ý kiến/căn cứ chuyên môn (`decision_reason`).
  - Bổ sung nút shortcut **[Duyệt ngay]** trên các hàng bảng có trạng thái `paused_for_approval`.

### 2.5. Đồng Bộ Tài Liệu Quy Trình Hệ Thống
- **`docs/quy_trinh/04_dieu_phoi_tro_ly_dag.md`**:
  - Thêm **Mục 12**: Đặc tả chi tiết Cơ chế Kiểm định Cấu hình Node theo JSON Schema tại thời điểm biên dịch, Đồng bộ thuộc tính hai chiều trên Canvas, và Quy trình vận hành Hộp thư phê duyệt HITL tại `/runs`.

---

## 3. Kết Quả Kiểm Thử Nghiệm Thu

| Bộ Kiểm Thử | Lệnh Thực Thi | Kết Quả |
| :--- | :--- | :--- |
| **Backend Lint** | `uv run ruff check .` | **All checks passed! (0 lỗi)** |
| **Backend Tests** | `uv run --extra dev pytest -v` | **228/228 passed (100%)** trong 47.93s (+4 tests mới) |
| **Frontend Lint** | `npm run lint` | **130 files checked, 0 lỗi** |
| **Frontend Types** | `npm run typecheck` | **tsc --noEmit: 0 lỗi** |
| **Frontend Bundle**| `npm run build` | **Thành công trong 7.41s** (2545 modules, 0 warnings) |
| **Zero Mojibake** | `python scripts/check_mojibake.py` | **286/286 files sạch UTF-8 100%** |

---

## 4. Kết Luận & Hướng Đi Tiếp Theo
- Giai đoạn 4 đã hoàn thành 100% mục tiêu:
  - Compiler Backend xác thực nghiêm ngặt JSON schema của từng node, chống rủi ro cấu hình sai lệch gây lỗi lúc chạy.
  - Property Inspector trên Canvas hoạt động động 100%, đồng bộ mượt mà giữa Visual UI và JSON schema.
  - Approval Inbox trên `/runs` giúp cán bộ vận hành dễ dàng phê duyệt hoặc từ chối các chốt chặn HITL mà không cần mở Canvas Studio.
- Sẵn sàng chuyển sang **Giai đoạn 5: Chuẩn Hóa Vòng Đời Tri Thức, Indexing & OCR Studio Hợp Nhất**.
