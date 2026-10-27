# Xác nhận review trước duyệt/xuất bản — backendV1

Với phiên bản có retrieval_metadata, review_ack còn cần
retrieval_metadata_sha256 đúng giá trị GET version trả về. Đây là xác nhận của
người duyệt đã xem metadata bất biến; báo cáo Compiler vẫn ghim Compiler bundle
gốc. [Chi tiết metadata và hash đăng ký](rag-policies.md).

Workspace là biên quyền của v1. Người có vai trò admin/reviewer duyệt; admin
xuất bản. Model chỉ sinh nhận xét, không được tự cấp quyền hoặc phê duyệt.

Tiền tố `V` là đường dẫn tới một phiên bản compiled document:
`/platform/v1alpha1/workspaces/{ws}/collections/{collection}/compiled-documents/{document}/versions/{version}`.

1. Chờ review tự động hoàn tất hoặc tạo review thủ công của đúng Compiler run.
2. `GET V/review-gate` trả review mới nhất của đúng input/draft/bundle, hash nguyên
   bytes báo cáo và findings với `finding_id` do server tạo. API có quyền và no-store.
3. Người duyệt đọc báo cáo, đối chiếu nguồn. Mỗi finding phải được giải trình bằng
   `accepted_risk` hoặc `not_an_issue`, kèm lý do ít nhất 10 ký tự. Nếu sửa nội dung,
   lưu bản sửa thành run/phiên bản mới rồi review lại; không tự khai “đã sửa” trên
   cùng hash bản cũ. Báo cáo không có finding vẫn cần xác nhận đã đọc.
4. Gửi `POST V/decision-preview` như ví dụ dưới, rồi chấp nhận qua API decisions
   hiện hữu với preview ID/hash và Idempotency-Key.
5. Server kiểm lại quyền, hash nguồn/bản nháp, review mới nhất và toàn bộ finding
   khi commit. Xuất bản/thay thế kiểm lại biên nhận duyệt đã ghim review.

```json
{
  "action": "approve",
  "reason": "Đã đối chiếu bản biên soạn với nguồn",
  "review_ack": {
    "review_id": "<review_id>",
    "report_sha256": "<sha256 báo cáo từ server>",
    "confirmed_reviewed": true,
    "resolutions": [
      {
        "finding_id": "<finding_id từ server>",
        "decision": "not_an_issue",
        "reason": "Giải thích cụ thể sau khi đối chiếu nguồn"
      }
    ]
  }
}
```

Không có review hoàn tất trả `publication_review_required`; review/hash đổi trả
`publication_review_stale`; thiếu/thừa/trùng finding trả
`publication_review_unresolved`. Thiếu/hỏng artifact là lỗi hạ tầng/toàn vẹn,
không đổi thành “không có vấn đề”. Review mới xuất hiện sau preview cần xem lại.
Nếu đã approved rồi có review mới, thu hồi và duyệt lại trước khi publish.

Preview lưu `review_ack` và đưa vào hash; decision lưu lại trong `after` cùng
actor, reason và bundle. Không sửa báo cáo model hoặc tự chuyển finding sang
đã sửa. Không tự thu hồi bản đang phục vụ chỉ vì một model review mới xuất hiện.

Đây là xác nhận có truy vết, không chứng minh người duyệt hay model luôn đúng.
Chất lượng ngữ nghĩa cần nghiệm thu riêng. Kiểm thử dùng nhận xét và xác nhận
tổng hợp; lượt thử PDF thật được duyệt thử trong DB riêng theo phạm vi chạy toàn
luồng người dùng đã cho phép, không dùng làm phê duyệt nội dung phục vụ.
