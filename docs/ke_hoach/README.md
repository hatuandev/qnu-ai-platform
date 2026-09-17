# Chuyên Mục Kế Hoạch Phát Triển — QNU AI Platform

Thư mục này lưu trữ các tài liệu kế hoạch, lộ trình kỹ thuật và phân tích phương án phát triển cho từng cấu phần của dự án **QNU AI Platform**.

---

## 📌 Danh Mục Kế Hoạch

1. [**`01_ke_hoach_phat_trien_fe.md`**](./01_ke_hoach_phat_trien_fe.md):
   - **Tên kế hoạch**: Kế hoạch phát triển Frontend QNU AI Platform chuẩn Design System QLKTX.
   - **Mục tiêu**: Xây dựng lại Frontend bằng **Vite 8 + React 19 + TanStack Suite + Tailwind CSS v4 + Biome**, kế thừa 100% tokens màu OKLCH, khung vỏ `AdminShell` (Sidebar, Topbar, Breadcrumbs, CommandMenu) từ dự án `qnu-ktx`, và bổ sung bộ components chuyên trách AI (`ChatMessage`, `MessageScroller`, `Attachment`, `QuestionnaireCard`, `CitationSheet`, `DAGCanvas`).
   - **Trạng thái**: Đã phê duyệt, sẵn sàng thực thi.

2. [**`03_ke_hoach_dong_bo_taxonomy_loai_van_ban.md`**](./03_ke_hoach_dong_bo_taxonomy_loai_van_ban.md):
   - **Tên kế hoạch**: Chuẩn hóa và đồng bộ taxonomy loại văn bản từ `qnu-ai-core` sang `qnu-ai-platform`.
   - **Mục tiêu**: Đưa 37 loại văn bản QNU về một contract có mã chuẩn, lưu bền vững trong Platform và dùng chung cho Knowledge, RAG, Workflow, Drafting và Frontend.
   - **Trạng thái**: Đã triển khai nền tảng taxonomy v1; còn chờ Core contract versioned để sync HTTP.
