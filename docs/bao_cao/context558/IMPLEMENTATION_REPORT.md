# Context558 — Phạm vi triển khai

| Thành phần | Thay đổi |
|---|---|
| automatic_ingestion.py | Ba trạng thái nội dung, policy/version, proof chống stale, giới hạn raw và kiểm tra source/pair trước I/O tiếp theo |
| qnu_serving.py | Nhánh automatic opt-in của pipeline; giữ hành vi mặc định cũ cho caller cần review |
| source_ingestion_service.py | Upload/reparse DOCX/PDF dùng nhánh automatic; giữ các pointer và worker/post-ingestion hiện có |
| source_artifact.py | Certificate nội dung hợp lệ quyết định content readiness; proposal chưa duyệt vẫn giữ riêng |
| models.py / schemas.py | Property/DTO readonly ingestion_readiness; không thêm cột, không migration |
| vector_load_service.py / chunk_set_service.py / derived_bundle.py | Kiểm tra lại nguồn trước queue, materialize và publication validation |
| smart_approval.py / smart_approval_service.py / semantic_store.py | Smart Approval nâng cao, audit bulk + machine validation, snapshot v3 và backward compatibility |
| source-detail-page.tsx / ingestion-readiness-panel.tsx | Trạng thái, Xem Markdown, Nạp vector là luồng chính; đối chiếu nâng cao dành cho quyền quản trị |
| semantic-review-preview.tsx | Chứng cứ đầy đủ giữ trong Advanced Review, dùng nguồn chung theo unit thay vì lặp toàn đoạn |
| knowledge-api.ts / knowledge.ts | Contract có kiểu, gửi đúng hash/revision, giữ lỗi thật |

Không đổi model/provider/config chạy, không gọi lại 22 packet, không reparse/upload/index/publish nguồn thật. Không commit/push/deploy. Thay đổi Context557 chưa commit được giữ nguyên. Chỉ dữ liệu test riêng được ghi để nghiệm thu.

Thay đổi giao diện giữ chức năng hiệu đính, nhập checkpoint, đối chiếu, bỏ/yêu cầu sửa proposal, từ chối và duyệt thủ công trong phần nâng cao. Không có nút xác nhận lần hai cho cùng thao tác Smart Approval.
