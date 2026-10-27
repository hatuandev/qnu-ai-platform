# 23 — Phiên bản, duyệt và xuất bản bản biên soạn backendV1

```text
Compiler completed
→ đăng ký document_key + phiên bản draft (ghim run/hash/provenance)
→ người có quyền xem draft và tạo preview approve
→ xác nhận đúng preview → approved
→ admin preview publish → xác nhận → published
→ phiên bản mới published thì bản cũ superseded
→ admin có thể withdraw; phục hồi bản cũ cần approve + publish mới
```

Workspace là biên giới quyền **chỉ trong v1**. Trạng thái xử lý Compiler và trạng
thái publication là hai hợp đồng riêng. Chỉ API đọc bản đang xuất bản được dùng
làm đầu vào cho indexing về sau; draft/history không tự đi vào RAG.

Nguồn/revision/hash và quyết định phải khớp; thiếu hoặc đổi nguồn thì báo lỗi.
Thu hồi không xóa bằng chứng. Quyết định có preview, actor/quyền được kiểm lại,
idempotency và audit; LLM không tự duyệt hoặc xuất bản.

Định nghĩa trạng thái và quyền do QNU thiết kế, tham khảo cách tổ chức nguồn và
citation của Kotaemon; không tuyên bố Kotaemon có đúng vòng đời này.

[API, dữ liệu và vận hành](../../backendV1/docs/compiled-publication.md) ·
[Báo cáo646](../bao_cao/context646/REVIEW.md).
