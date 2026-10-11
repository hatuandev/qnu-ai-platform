# NHẬT KÝ PHIÊN LÀM VIỆC SỐ 326

**Ngày thực hiện**: 2026-10-10  
**Kỹ sư thực hiện**: Senior Full-Stack Architect & Enterprise AI Systems Specialist  
**Mục tiêu chính**: Khắc phục lỗi bấm **Thêm nguồn** trong chi tiết Kho tri thức nhưng URL đổi mà màn hình vẫn giữ nguyên trang chi tiết bộ sưu tập.

---

## 1. Hiện tượng và nguyên nhân gốc

- Sau khi migrate, reset CSDL và chạy môi trường dev, luồng tải tệp vào Kho tài liệu hoạt động bình thường.
- Tại `/knowledge/:collectionId`, bấm **Thêm nguồn** điều hướng đúng sang URL `/knowledge/:collectionId/add-documents`, nhưng giao diện vẫn hiển thị `CollectionDetailPage`.
- Ba route chuyên sâu được đặt tên theo dạng route con của `knowledge.$collectionId.tsx`:
  - `knowledge.$collectionId.add-documents.tsx`
  - `knowledge.$collectionId.documents.$bindingId.tsx`
  - `knowledge.$collectionId.sources.$sourceId.tsx`
- TanStack Router vì vậy gắn chúng làm con của route `/$collectionId`. Route cha đang render trực tiếp `CollectionDetailPage` và không có `Outlet`, nên component trang con không bao giờ xuất hiện dù URL đã khớp.

## 2. Giải pháp đã áp dụng

Chuyển ba route chuyên sâu sang quy ước **non-nested route** của TanStack Router bằng dấu gạch dưới ở cuối tham số cha:

- `knowledge.$collectionId_.add-documents.tsx`
- `knowledge.$collectionId_.documents.$bindingId.tsx`
- `knowledge.$collectionId_.sources.$sourceId.tsx`

URL công khai không thay đổi. Cây route sinh tự động xác nhận cả ba trang nay có `KnowledgeRoute` làm route cha trực tiếp, thay vì bị lồng dưới `KnowledgeCollectionIdRoute`:

- `/knowledge/$collectionId/add-documents`
- `/knowledge/$collectionId/documents/$bindingId`
- `/knowledge/$collectionId/sources/$sourceId`

Giải pháp đồng thời sửa cả ba luồng master-detail: **Thêm nguồn**, **Chi tiết nguồn**, và **Chi tiết tài liệu liên kết**.

## 3. Tệp thay đổi

- `frontend/src/routes/knowledge.$collectionId_.add-documents.tsx`
- `frontend/src/routes/knowledge.$collectionId_.documents.$bindingId.tsx`
- `frontend/src/routes/knowledge.$collectionId_.sources.$sourceId.tsx`
- `frontend/src/routeTree.gen.ts` được TanStack Router tái sinh trong bước build.
- Bộ nhớ và nhật ký dự án được đồng bộ theo AGENTS.md.

## 4. Kiểm thử và xác minh

- `npm run build` tại `frontend`: **thành công**, TypeScript không lỗi, Vite build thành công với 5.077 modules trong 6,07 giây.
- Kiểm tra `routeTree.gen.ts`: cả ba route chuyên sâu có `getParentRoute: () => KnowledgeRoute`, trong khi URL công khai được giữ nguyên.
- Thử mở trang qua trình duyệt kiểm tra tách biệt bị chuyển về `/sign-in` do không dùng chung phiên đăng nhập của trình duyệt người dùng; không coi đây là lỗi của route.
- Không chạy backend test vì đây là thay đổi thuần frontend routing, tuân thủ Fast-Path Frontend Verification.

## 5. Bài học và quyết định kiến trúc

- Với TanStack Router file-based routing, trang chi tiết độc lập không được đặt làm con của một route cha chỉ render page và không có `Outlet`.
- Dấu gạch dưới `_$param_` được dùng để phá quan hệ layout nesting nhưng vẫn giữ nguyên cấu trúc URL sâu, phù hợp Master-Detail Deep Routing của dự án.
- Khi thêm route chuyên sâu mới dưới Kho tri thức, cần kiểm tra cả URL lẫn `parentRoute` trong cây route sinh tự động để tránh lỗi “URL đổi nhưng trang không đổi”.
