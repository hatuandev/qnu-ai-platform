# ADR-006 — Phạm vi dữ liệu

**Quyết định:** một deployment dùng chung hạ tầng dữ liệu; đơn vị là biên giới
**quyền** (membership + role), không phải phân vùng vật lý. Truy vấn vẫn scope theo
collection đã được cấp quyền.

**Hệ quả:** không thêm filter tenant vào retrieval; kiểm quyền ở server trước khi gọi RAG.

## Làm rõ Context636

Chung hạ tầng không có nghĩa chung quyền. BackendV1 kiểm membership/role qua resolve_workspace_access cho workspace cụ thể; scope collection/model phải xuất phát từ quyền server. Cache, jobs và retrieval khi triển khai phải giữ đúng workspace đã được cấp. Ngoại lệ này chỉ v1; backend/ giữ nghiệp vụ một phạm vi dữ liệu chung.
