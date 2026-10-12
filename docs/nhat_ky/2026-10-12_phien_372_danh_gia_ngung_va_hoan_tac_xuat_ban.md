# Phiên #372 — Ngừng và hoàn tác xuất bản

- Ngày: 2026-10-12. Phạm vi: đọc code, không thao tác dữ liệu xuất bản.
- Skill qnu-rag-pipeline dùng để phân biệt Markdown, vector và chỉ mục phục vụ.
- Ảnh người dùng cho thấy 4 nguồn đang phục vụ chatbot; không đọc DB mới để xác minh lịch sử rollback.

## Hiện trạng và giới hạn

- `binding_service.detach_binding`: gỡ mềm, archive/deactivate revisions theo namespace generation, xóa active index pointer, tăng epoch. Giữ source revisions và tệp ở Repository. Trang binding detail cũ có Gỡ Khỏi Kho.
- Backend có rollback generation qua `generation_publish_service.publish_generation(rollback=True)`: chỉ nhận generation ready/retired, yêu cầu đủ chỉ mục cho mọi binding active hiện tại. Không phải snapshot bất biến của toàn bộ lần xuất bản lịch sử; danh sách nguồn thay đổi có thể làm rollback bị chặn.
- Frontend có hoàn tác revision ở binding-detail-page, nhưng `index_build_service.rollback_index_revision` activate/deactivate không truyền `qdrant_collection_name` của generation. Không bảo đảm tương thích cơ chế đa generation mới; chưa khuyên dùng trước khi sửa và kiểm thử.
- Không thấy nút/API ngừng xuất bản chuyên biệt cho toàn kho trong phạm vi đã rà.
- Xóa vĩnh viễn Knowledge-only không phải pause; mất artifact rollback của nguồn bị xóa, giữ tệp Repository.

## Đề xuất chưa triển khai

- Ngừng dùng/Bật lại từng nguồn, không xóa artifact.
- Thay văn bản hoặc sửa Markdown → xử lý bản mới → nạp vector → xuất bản; bản cũ còn phục vụ khi dựng bản mới, trừ khi chủ động ngừng vì sai nội dung.
- Hoàn tác theo lịch sử xuất bản có kiểm tra namespace/artifact/membership; trường hợp lần đầu không có bản trước phải ngừng thay vì rollback.
- Ngừng toàn kho loại dữ liệu khỏi RAG và invalidation cache theo epoch, không dùng dữ liệu thiếu căn cứ.

## Kiểm chứng

Chỉ đọc service/router/UI; chưa kiểm thử live rollback/pause/browser, chưa thay runtime, provider, qnu-sso hoặc dữ liệu. Không chạy Ruff/Pytest/Vite vì không sửa code. Cập nhật nhật ký, snapshot, context và mục lục; không đổi quy trình đang vận hành.
