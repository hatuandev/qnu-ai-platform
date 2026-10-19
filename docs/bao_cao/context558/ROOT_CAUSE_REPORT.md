# Context558 — Nguyên nhân và mục tiêu đã điều chỉnh

Mục tiêu cuối: upload DOCX/PDF → Markdown + Structured JSON → kiểm tra nội dung → sẵn sàng nạp vector. Semantic Review là phần nâng cao; tạo embeddings không đồng nghĩa xuất bản.

## Vì sao luồng cũ bị chặn

1. `prepare_standard_revision` luôn ép bản chuẩn sang warning, dù nội dung không có lỗi.
2. `get_structured_review_state` gộp lỗi nội dung, ô chưa rõ và proposal ngữ nghĩa vào cùng cờ chặn. ChunkSet, queue vector, publication và RAG cùng dùng cờ này.
3. UI yêu cầu chọn Chấp thuận rồi xác nhận lần nữa; proposal chưa có quyết định riêng vẫn chặn. Trước sửa đã tái hiện đúng thông báo SEMANTIC_CONTEXT_REVIEW_REQUIRED trên bản test, không POST duyệt nguồn thật.

Context557 thực tế đã là **changes_requested**, cùng proposal hash `543ddd61aa0b1527babe8c6adcb122c5cb2157f30d542c91d1de6fa5407207df`, khác trạng thái chờ duyệt trong báo cáo lịch sử. Không khôi phục hoặc duyệt thay quyết định này.

## Ba ô: không cùng nguyên nhân

| Vị trí | Raw | Đối chiếu | Kết luận |
|---|---|---|---|
| Bảng 5 / CT-05 / c02 | – | Chú giải K-05 và footnote 3; XML gốc khớp | Có căn cứ giải nghĩa: chưa đo do tạm ngừng; không phải 0 |
| Bảng 5 / CT-06 / c02 | / | Chú giải và footnote nói rõ chưa công bố nghĩa | Confirmed Source Unknown |
| Bảng 9 / trang_thai / c03 | / | Quy tắc của chính dòng yêu cầu chưa quy đổi; chú giải CT-06 có phạm vi riêng | Unverified Meaning; không mặc định đồng nhất với CT-06 |

Đã kiểm tra trực tiếp ba giá trị trong DOCX XML: không phải lỗi bóc tách ba ô. Luồng tự động giữ literal/blank/not_stated và giới hạn sử dụng; `literal_uninterpreted` không tuyên bố đã chứng minh nguồn không định nghĩa. Unknown không được đổi thành 0 hoặc tạo fact số chắc chắn.

## 18 issue và chất lượng nguồn là hai việc khác

Bộ fixture acceptance có thể kiểm chứng 18 issue của đúng gói đã đối soát, giữ A03 workflow/nhóm A/2027, A10 AM-0007, A11 c11 và A12 chuỗi có số 0 đầu. Sáu tham chiếu liên quan không biến thành not_applicable. Đây là kết quả máy, không phải 18 quyết định thủ công.

Bản Context557 còn cảnh báo độc lập về hàng gộp, header bảng, nội dung hình và định vị trang. Không coi đã giải quyết 18 issue là toàn bộ tài liệu đạt chất lượng. Không đổi trạng thái, tạo certificate tự động hoặc nạp vector cho nguồn thật trong phiên này.
