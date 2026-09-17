# Nhật Ký Làm Việc — Khắc Phục Lỗi Xóa Tài Liệu Thất Bại HTTP 404 (Triệt Tiêu Mock Trap)

- **Thời gian thực hiện**: 2026-09-17 23:59 (UTC+7)
- **Phiên số**: #49
- **Kỹ sư phụ trách**: Senior Full-Stack Architect & Enterprise AI Systems Specialist

---

## 1. Bản Chất Lỗi
Người dùng phản ánh lỗi xuất hiện khi bấm "Xóa vĩnh viễn" tài liệu:
- Màn hình hiển thị modal: `Xóa tài liệu? Tài liệu "Thong tin tuyen sinh dai hoc 2026 Lan2 1 (1)" sẽ bị xóa vĩnh viễn khỏi kho...`
- Khi bấm xác nhận, xuất hiện thông báo lỗi màu đỏ: `(!) Xóa tài liệu thất bại (HTTP 404).`
- Console DevTools báo lỗi: `DELETE /platform/v1alpha1/knowledge/documents/doc_ts_2026 404 (Not Found)`.

---

## 2. Nguyên Nhân Kỹ Thuật (Root Cause)
1. Trong CSDL PostgreSQL hiện tại, bảng `knowledge_documents` đang **hoàn toàn rỗng (0 tài liệu)**.
2. Khi người dùng vào Kho Tri Thức Tuyển Sinh (`col_admissions`), Frontend gọi API `GET /knowledge/documents?collection_id=col_admissions`. Backend trả về thành công mã `200 OK` với danh sách rỗng `[]`.
3. Trong `apiClient.getDocuments`, điều kiện kiểm tra dữ liệu trước đây là:
   ```typescript
   if (Array.isArray(data) && data.length > 0) {
     return data.map(...);
   }
   // Khi data.length === 0, rơi vào fallback:
   return MOCK_DOCUMENTS.filter((d) => d.collection_id === collectionId);
   ```
   Do danh sách trả về rỗng (`data.length === 0`), Frontend đã tự động lấy dữ liệu mẫu ảo `doc_ts_2026` ("Thong tin tuyen sinh dai hoc 2026 Lan2 1 (1)") ra hiển thị lên bảng.
4. Khi người dùng bấm "Xóa vĩnh viễn", Frontend gửi `DELETE /knowledge/documents/doc_ts_2026`.
5. Backend tìm trong CSDL không thấy ID `doc_ts_2026` nên trả về lỗi chuẩn RFC 7807 `HTTP 404 Not Found`.

---

## 3. Giải Pháp Đã Triển Khai
- [`frontend/src/services/api-client.ts`](../../frontend/src/services/api-client.ts):
  - Sửa `getDocuments` và `getCollections`: Đổi `Array.isArray(data) && data.length > 0` thành `Array.isArray(data)`. Khi Backend trả về `[]`, Frontend trả về đúng mảng rỗng `[]` và hiển thị giao diện Empty State trung thực ("Chưa có tài liệu"), chấm dứt hoàn toàn tình trạng hiển thị tài liệu ảo.
  - Cập nhật `deleteDocument`: Coi mã `404` (tài liệu không còn tồn tại trên server) là thao tác thành công (idempotent delete), tự động dọn dẹp khỏi giao diện người dùng.

---

## 4. Kết Quả Kiểm Thử (Verification)
- `npm run lint`: Biome check 77 files, 0 errors.
- `npm run typecheck`: TypeScript 0 errors.
- `npm run build`: Vite build hoàn tất thành công trong 5.36s.
- `uv run ruff check .`: 0 errors.
- `uv run --extra dev pytest tests/test_knowledge.py -v`: 23/23 tests passed.
- `uv run --extra dev pytest -q`: 117/117 tests passed (100%).
