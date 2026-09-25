# Quy Chuẩn Giao Diện UI & Nút Chuyển Đổi View Mode (UI Standards)

Tài liệu quy chuẩn giao diện Frontend cho toàn bộ AI Agents khi phát triển và bảo trì nền tảng `qnu-ai-platform`.

---

## 1. Nút Chuyển Đổi Chế Độ Xem (View Mode Switcher / Grid-Table Toggle)

### 1.1. Nguyên Tắc Bắt Buộc
- **100% Tái Sử Dụng `<ViewModeToggle />`**:
  Mọi màn hình danh sách có tính năng chuyển đổi chế độ xem giữa Thẻ Lưới (Grid) và Bảng/Danh Sách (Table/List) (ví dụ: `/document-types`, `/knowledge`, `/capabilities/nodes`, `/assistants`, v.v.) **BẮT BUỘC PHẢI SỬ DỤNG** component dùng chung:
  ```tsx
  import { ViewModeToggle } from "@/components/ui/view-mode-toggle";
  
  // Sử dụng:
  <ViewModeToggle value={viewMode} onChange={setViewMode} />
  ```
- **Tuyệt Đối CẤM Tự Chế Style Khi Vibe Coding**:
  - Nghiêm cấm tự viết thẻ HTML thô hoặc các nút `<Button>` tùy biến lẻ tẻ (nút chữ "Thẻ / Bảng", hay nút `variant="default"` màu đen/nền đậm, hoặc `rounded-sm` làm lệch lạc thẩm mỹ).
  - Không tự gõ inline `<div><Button>...</Button></div>`.

### 1.2. Chuẩn Thiết Kế Vàng (Lấy Chuẩn Từ `/document-types`)
- **Container Khung Bao**:
  `flex items-center gap-1 border border-border rounded-md p-0.5 bg-muted/30 shrink-0`
- **Nút Con (Sub-buttons)**:
  - Khi Active (đang chọn): `variant="secondary"` (nền sáng tinh tế, ăn khớp Dark & Light mode).
  - Khi Inactive: `variant="ghost"`.
  - Kích thước: `size="sm"` `className="h-7 w-7 p-0"`.
- **Icons**:
  - Thẻ lưới (Grid): `<LayoutGrid className="size-3.5" />` từ `lucide-react`.
  - Danh sách bảng (Table/List): `<List className="size-3.5" />` từ `lucide-react`.
- **Tooltips & Accessibility**:
  - `title="Xem dạng thẻ lưới"` cho nút Grid.
  - `title="Xem dạng danh sách bảng"` cho nút Table/List.
- **Hỗ Trợ Type**:
  - Hỗ trợ cả 2 chuẩn state: `"grid" | "table"` hoặc `"grid" | "list"`.
