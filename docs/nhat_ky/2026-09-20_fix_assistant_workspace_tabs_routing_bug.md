# Nhật Ký Làm Việc — Sửa Lỗi Điều Hướng Tabs Trong Assistant Workspace (/assistants/:id/*)

- **Thời gian**: 2026-09-20 23:08 (UTC+7)
- **Kỹ sư / Agent**: AI Senior Full-Stack Architect & Enterprise AI Systems Specialist
- **Phiên số**: #65

---

## 1. Hiện Tượng & Phản Ánh Của Người Dùng

Khi người dùng mở trang chi tiết một Trợ lý AI (ví dụ: `http://localhost:3001/assistants/admissions`):
- Tab đầu tiên **"Thông tin & Tri thức"** (`/assistants/admissions`) hiển thị bình thường.
- Tuy nhiên, khi nhấp vào bất kỳ tab nào khác trong 7 tabs còn lại:
  - Tab `Mô hình & An toàn` (`/assistants/admissions/models`)
  - Tab `Quy trình & Công cụ` (`/assistants/admissions/tools`)
  - Tab `Thử nghiệm Chat` (`/assistants/admissions/playground`)
  - Tab `Đồ thị DAG` (`/assistants/admissions/workflow`)
  - Tab `Chất lượng TM-08` (`/assistants/admissions/quality`)
  - Tab `Lịch sử Chạy` (`/assistants/admissions/runs`)
  - Tab `Mã nhúng Kênh` (`/assistants/admissions/channels`)
- Màn hình lập tức bị vỡ và báo lỗi:
  > **Không tìm thấy Trợ lý AI**  
  > *Mã định danh hoặc bí danh “models” (hoặc “tools”, “playground”,...) không tồn tại trong hệ thống.*

---

## 2. Nguyên Nhân Gốc Rễ (Root Cause Analysis)

Trong [`frontend/src/pages/assistant-detail-page.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/pages/assistant-detail-page.tsx):
Hàm bóc tách mã định danh trợ lý từ URL được định nghĩa như sau:

```typescript
// ❌ Mã nguồn lỗi trước khi sửa:
function getReferenceFromPath(currentPath: string): string {
  return decodeURIComponent(currentPath.split("/").filter(Boolean).at(-1) ?? "");
}
```

- Cú pháp `.at(-1)` lấy phần tử **cuối cùng** của chuỗi URL sau khi tách dấu `/`:
  - Khi URL là `/assistants/admissions`: `parts` = `["assistants", "admissions"]` $\rightarrow$ `.at(-1)` là `"admissions"` (vô tình đúng).
  - Nhưng khi người dùng chuyển sang tab `models`, URL là `/assistants/admissions/models`: `parts` = `["assistants", "admissions", "models"]` $\rightarrow$ `.at(-1)` lấy nhầm chuỗi **`"models"`** làm mã trợ lý!
  - Trang chi tiết lập tức gọi API `GET /assistants/models`. Backend không tìm thấy trợ lý nào có code là `models` $\rightarrow$ trả lỗi HTTP 404 $\rightarrow$ UI rơi vào khối hiển thị EmptyState lỗi.
  - Tương tự cho toàn bộ các tab con khác (`tools`, `playground`, `workflow`, `channels`, `quality`, `runs`).

---

## 3. Giải Pháp Kỹ Thuật

1. **Chuẩn hóa hàm `getReferenceFromPath` trong `assistant-detail-page.tsx`**:
   Xác định vị trí phân đoạn `"assistants"` trong mảng đường dẫn và luôn trích xuất phần tử ngay sau nó (`parts[assistantsIndex + 1]`):
   ```typescript
   function getReferenceFromPath(currentPath: string): string {
     const parts = currentPath.split("/").filter(Boolean);
     const assistantsIndex = parts.indexOf("assistants");
     if (assistantsIndex !== -1 && parts[assistantsIndex + 1]) {
       return decodeURIComponent(parts[assistantsIndex + 1]);
     }
     return decodeURIComponent(parts.at(-1) ?? "");
   }
   ```
2. **Hỗ trợ Prop `assistantId` trực tiếp**:
   - Khai báo prop `assistantId?: string` trong `AssistantDetailPageProps`.
   - Trong [`frontend/src/App.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/App.tsx), truyền trực tiếp `assistantId={resolved.params.assistantId}` từ bộ giải mã tuyến đường `route-resolver.ts` vào `AssistantDetailPage`.
   - `reference` ưu tiên dùng `assistantId` được truyền vào, bảo đảm 100% chuẩn xác ở mọi cấp URL con.

---

## 4. Kết Quả Kiểm Thử (Verification)

- `npm run typecheck`: **0 lỗi** (TypeScript `tsc --noEmit` pass).
- `npm run lint`: **0 lỗi** (Biome check 167 files sạch sẽ).
- `npm run build`: **Thành công** (`vite build` đóng gói bundle thành công trong 9.86s).
