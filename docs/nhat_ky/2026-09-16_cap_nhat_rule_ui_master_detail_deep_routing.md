# Nhật Ký Làm Việc — Cập Nhật Quy Tắc UI/UX Frontend: Tư Duy UI Mở & Master-Detail Deep Routing
**Thời gian**: 2026-09-16 16:00 (UTC+7)  
**Tác giả**: AI Senior Full-Stack Architect & Enterprise AI Systems Specialist  
**Phiên làm việc**: #26  

---

## 1. Mục Tiêu Phiên Làm Việc
- Tiếp thu phản hồi thực tế của người dùng: Hiện tại nhiều trang bị gò bó trong 1 page duy nhất (ví dụ trang Kho Tri Thức có danh sách card nhưng bấm vào lại chỉ đổi tab hoặc hiển thị trên cùng một trang, không có trang chi tiết đàng hoàng).
- Cập nhật **Quy chuẩn UI/UX bắt buộc** cho toàn bộ AI Agents trong [`AGENTS.md`](file:///d:/DuAnPhanMem/qnu-ai-platform/AGENTS.md) và Skill [`qnu-frontend-architect`](file:///d:/DuAnPhanMem/qnu-ai-platform/.agents/skills/qnu-frontend-architect/SKILL.md).
- Xác lập mô hình kiến trúc **Master-Detail Deep Routing Pattern**: 1 Domain = List Page + Dedicated Detail Pages.

---

## 2. Thay Đổi Kỹ Thuật (Key Changes)

### 2.1. Cập Nhật [`AGENTS.md`](file:///d:/DuAnPhanMem/qnu-ai-platform/AGENTS.md) (Mục 4.5)
Bổ sung quy định bắt buộc:
- **Tư Duy UI Mở & Kiến Trúc Điều Hướng Sâu (Master-Detail Deep Routing Pattern)**:
  - Tuyệt đối không nhồi nhét "Monolithic Tabbed Page": Không gộp toàn bộ tính năng danh sách, chi tiết, chỉnh sửa chuyên sâu và wizard nạp tệp vào một file page duy nhất bằng các thẻ Tab gò bó hay Dialog chật hẹp.
  - Quy chuẩn 1 Domain = List Page + Dedicated Detail Pages:
    - *Trang Danh Sách (Master/List View)*: Tập trung vào tổng quan thực thể, bộ lọc tìm kiếm, chỉ số KPI và danh sách Card/Bảng tối giản, thoáng đãng.
    - *Trang Chi Tiết Độc Lập (Dedicated Detail View)*: Khi người dùng click vào bất kỳ Card/Hàng bảng nào, **BẮT BUỘC PHẢI chuyển hướng sang trang chi tiết riêng biệt** với URL phân cấp rõ ràng (`/:domain/:id`).
    - *Tách File Độc Lập*: Trang chi tiết phải là một component/file riêng (ví dụ `collection-detail-page.tsx`, `assistant-detail-page.tsx`), không viết chung thành khối nghìn dòng trong trang danh sách.
  - Tiêu chuẩn bắt buộc trên Trang Chi Tiết:
    - Thanh điều hướng quay lại & Breadcrumb (`ArrowLeft` + Breadcrumb phân cấp).
    - Header & Action Toolbar chuyên biệt.
    - Bố cục đa cột (2-3 cột sâu) không bị giới hạn không gian.
    - Deep Linking & URL State (F5 giữ nguyên ngữ cảnh).

### 2.2. Cập Nhật Skill [`.agents/skills/qnu-frontend-architect/SKILL.md`](file:///d:/DuAnPhanMem/qnu-ai-platform/.agents/skills/qnu-frontend-architect/SKILL.md) (Mục 5)
- Thêm Section 5 hoàn chỉnh:
  - 5.1 Tôn chỉ "Mở rộng không gian" thay vì "Gò bó một trang".
  - Chống Anti-pattern "Monolithic Tabbed Page".
  - Mô hình phân cấp 2 tầng (Master - Detail Separation).
  - Quy tắc tách tệp mã nguồn độc lập (`src/pages/collection-detail-page.tsx`, `src/pages/assistant-detail-page.tsx`, `src/pages/provider-detail-page.tsx`).
  - Hướng dẫn cấu hình query key phân cấp trong TanStack Query (`['knowledge', 'collections', collectionId]`).

---

## 3. Định Hướng Thực Thi Thực Tế Kế Tiếp
- Refactor trang **Kho Tri Thức (`/knowledge`)**:
  - Tách thành `knowledge-page.tsx` (danh sách bộ sưu tập + search/filter) và `collection-detail-page.tsx` (trang chi tiết độc lập khi click vào từng Collection, có route `/knowledge/collections/:id` hoặc `/knowledge/:id`, hiển thị tài liệu con, facts, chunks, and nạp tri thức).
- Áp dụng tương tự cho trang **Trợ Lý AI (`/assistants`)** và các trang khác.
