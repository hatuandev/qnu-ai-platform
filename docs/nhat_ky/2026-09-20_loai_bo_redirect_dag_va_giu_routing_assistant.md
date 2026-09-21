# Nhật Ký Làm Việc — 2026-09-20 (Phiên #168)
## Loại Bỏ Chuyển Hướng /workflows/* & Giữ Nguyên Không Gian URL /assistants/:id/workflow

### 1. Bối Cảnh & Vấn Đề
- Người dùng phản hồi:
  > *"ở chỗ DAG nó lại chuyển hướng đến http://localhost:3001/workflows/admissions-assistant?returnTo=/assistants/admissions tôi lại không thích điều này"*
- **Phân tích nguyên nhân**:
  - Ở phiên trước, khi tách DAG Canvas ra khỏi subtab bị chèn ép, hệ thống đã cài đặt một hook tự động `useEffect` trong `assistant-detail-page.tsx` chuyển tiếp URL sang `/workflows/admissions-assistant?returnTo=/assistants/admissions`.
  - Việc này làm người dùng cảm thấy bị đẩy ra khỏi phân hệ quản lý Trợ lý AI:
    - URL trên thanh địa chỉ xuất hiện query rườm rà `?returnTo=/assistants/admissions`.
    - Menu bên trái bị nhảy focus từ "Trợ lý AI" sang "Thư Viện Workflow" (nhóm Nâng cao).
    - Breadcrumb đổi thành "Hệ thống > Tổng Quan".
  - Mong muốn đúng đắn của người dùng: DAG Canvas cần một không gian hiển thị rộng rãi, nhưng **phải giữ nguyên ngữ cảnh của Trợ lý** tại URL sạch `/assistants/:id/workflow`.

---

### 2. Các Thay Đổi Kỹ Thuật (Key Changes)

1. **[`assistant-detail-page.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/pages/assistant-detail-page.tsx)**:
   - Xóa bỏ hoàn toàn hook `useEffect` tự động redirect sang `/workflows/...`.
   - Bổ sung early-return khi `subView === "workflow"`: trả về trực tiếp `DAGCanvasPage` với `initialWorkflowId={form?.workflow_id || item.workflow_id}`, `backPath={`/assistants/${item.code}`}`, `backLabel={`Trợ lý ${item.name}`}`.
   - Nhờ đó, trang DAG Canvas nhận toàn bộ không gian viewport (`h-[calc(100vh-4rem)]`), không bị chèn ép bởi form hay tab nào phía trên.
2. **[`assistant-header.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/components/assistants/assistant-header.tsx)**:
   - Nút `[Sơ đồ DAG Studio]` và mục trong Dropdown Menu điều hướng trực tiếp sang `/assistants/${assistantCode}/workflow`.
   - Xóa bỏ tham số `?returnTo=...`.
3. **[`assistant-tools-section.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/components/assistants/sections/assistant-tools-section.tsx)**:
   - Nút `Mở đồ thị DAG Studio` điều hướng sang `/assistants/${assistantCode}/workflow`.
4. **[`assistant-workspace-nav.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/components/assistants/assistant-workspace-nav.tsx)**:
   - Bổ sung tab `workflow` ("Sơ đồ DAG Studio", icon `Network`) vào thanh Workspace Nav, giúp người dùng dễ dàng chuyển qua lại giữa các tab cấu hình và DAG Studio.
5. **[`dag-canvas-page.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/pages/dag-canvas-page.tsx)**:
   - Hỗ trợ props `backPath`, `backLabel`, `initialWorkflowId`.
   - Nút mũi tên và nút text `[Quay lại Trợ lý ...]` điều hướng về đúng `backPath` (`/assistants/:id`).

---

### 3. Kết Quả Sau Khi Tối Ưu
- **Địa chỉ URL**: Luôn là `http://localhost:3001/assistants/admissions/workflow` (Sạch sẽ 100%, không còn `?returnTo=...`).
- **Sidebar**: Luôn giữ highlight ở mục **Trợ Lý AI** (không bị nhảy sang Thư Viện Workflow).
- **Breadcrumbs**: Luôn giữ **Xây Dựng AI > Trợ Lý AI**.
- **Không gian DAG Canvas**: Chiếm trọn chiều cao màn hình, rộng rãi, thao tác thêm node/chạy thử/lưu nháp trơn tru.
- **Quay lại**: Chỉ cần bấm `[Quay lại Trợ lý]` là quay về trang cấu hình `/assistants/admissions`.

---

### 4. Kết Quả Kiểm Thử (Verification)
- `npm run typecheck`: **0 lỗi** (`tsc --noEmit`).
- `npm run lint`: **0 lỗi** trên 167 files (Biome check).
- `npm run build`: **Thành công** trong 8.73s.
- `uv run ruff check .`: **0 lỗi**.
