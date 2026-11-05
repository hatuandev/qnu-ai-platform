# Liên kết, revision và đối chiếu Trang tri thức

> **TÀI LIỆU LỊCH SỬ — không phải hiện trạng V1.** Nội dung dưới đây mô tả hệ thống `backend/` + `frontend/` trước V1 (hai thư mục đã gỡ khỏi checkout) và chỉ dùng để truy vết. Bản đang chạy là [`backendV1/`](../../backendV1) + [`frontendV1/`](../../frontendV1); xem [bản đồ tài liệu](../README.md).

## Luồng phổ thông

Upload DOCX/PDF → chuẩn hóa → kiểm chất lượng → sẵn sàng nạp vector → phục vụ
theo publication và quyền hiện có. Trang tri thức hỗ trợ tìm nguồn, không thay
canonical Markdown/Structured JSON và không tạo một vòng duyệt mọi liên kết.

Mở **Nội dung → Trang tri thức → Xem trang**. Trang liên quan/backlinks giữ URL
nguồn và revision. Năm dữ liệu, ban hành, hiệu lực và sự kiện là các vai trò riêng.
Bấm **Xem nguồn** để đối chiếu nguyên văn, điều kiện, ngoại lệ và ký hiệu chưa rõ.
Tài liệu không có wiki vẫn dùng pipeline hiện hành.

## Quy tắc liên kết

- Projection `qnu-wiki-links/v1` có hash, collection và snapshot; chỉ dựng từ các
  bundle/index đang được phép phục vụ, không ghi sidecar vào index đóng băng.
- `source_reference` là dẫn về nguồn. `co_mention` xác nhận cùng chuỗi nguyên văn
  ở hai đầu, không xác nhận cùng thực thể hoặc quan hệ áp dụng/sửa đổi/thay thế.
- Tên/mã/năm khác nhau giữ riêng. Alias/same-entity chưa rõ là candidate và không
  đi vào context tự động như một fact đã duyệt. Không chuẩn hóa Unicode của mã.
- RAG lọc scope trước expand, mặc định depth1/node3/edge32, giữ ngân sách
  model/time/chars/context sẵn có. Candidate không được dùng để mở rộng.
- Cache request kiểm lại phạm vi phục vụ và nguồn. Mất quyền/pointer/epoch trả
  lỗi stale; thiếu một block do context budget thì bỏ cả section cache không đủ.
  Citation vẫn trỏ canonical, không lấy trang wiki làm bằng chứng chính thức.

## Cập nhật revision

Nguồn không đổi chỉ được reuse khi toàn fingerprint/policy/manifest tương thích
và bundle cũ hợp lệ. Trang mới được rebind source revision/page ID/render/hash,
ghi trace reuse, giữ bundle cũ. Nội dung đổi biên soạn riêng nguồn đó; không tái
biên soạn toàn collection. Chưa reuse từng packet khi canonical thay đổi.

Unique revision/config và khóa source giữ idempotency/concurrency. Build không
đổi active pointer. Job cũ không xuất bản thay revision mới. Remove/rollback
phải qua quy trình có quyền hiện có; map/cache lấy lại tập snapshot tương ứng.
Không dùng thời điểm upload/tên file làm bằng chứng mới nhất có hiệu lực.

## Đối chiếu nâng cao

Quyền `ai.knowledge.review` mới xem được đối chiếu chi tiết; quyền
`ai.knowledge.view` xem trang/map phổ thông. Server kiểm cả hai. Ba GET mới:

- `/knowledge/collections/{id}/knowledge-map`.
- `/knowledge/collections/{id}/knowledge-map/review`.
- `/knowledge/collections/{id}/sources/{binding}/revisions/{revision}/knowledge-pages/review`.

GET không gọi model hoặc ghi dữ liệu. Review phân biệt blocker toàn vẹn/quyền,
warning, source limitation, candidate, lỗi provider/hạ tầng và stale/not compiled.
Nguồn mất bảng/số/mã/provenance không được hạ mức để chạy tiếp. Unknown đã giữ
nguyên không tự thành lỗi parser hoặc giá trị0. Giá trị khác năm/đơn vị/điều kiện
không tự bị coi là mâu thuẫn. Kiểm cấu trúc không thay đối chiếu ngữ nghĩa có người
duyệt; cùng mã/tên chưa đủ chứng minh identity xuyên nguồn.

Chi tiết sử dụng: [hướng dẫn Context600](../bao_cao/context600/USER_GUIDE.md).
Kết quả chạy thật, mock và NOT RUN: [kiểm chứng](../bao_cao/context600/VALIDATION_REPORT.md).
Phiên600 không tái dựng kho vận hành, reindex, publish, restart hoặc deploy.

## Inventory nguồn dài và nền biên soạn (Context602)

Trang nguồn extractive có thể phân thành nhiều phần, tối đa512 sections/phần.
Metadata part/count/previous/next và continuation links giữ thứ tự nguồn;
source_reference dẫn tới phần đầu. Server kiểm toàn bộ inventory đủ unit nguồn,
không mất/lặp unit vì giới hạn một trang. Reuse theo revision mới phải rebind
cả chuỗi continuation; không thay bundle của index đóng băng.

Ký hiệu nguồn1–2 ký tự được giữ khi server trích đúng toàn unit và kiểm lại với
canonical; đây là literal nguyên văn, không phải giải thích hoặc fact. Generated
mode không được dùng ngoại lệ này. Điều kiện/ngoại lệ và unknown vẫn giữ các
kiểm tra hiện có.

DOCX chỉ được nối lại các engine fragments khi khớp một native paragraph đầy đủ
duy nhất cùng parent/level; raw fragments và hash/locator được lưu. Nguồn mơ hồ
giữ nguyên, không suy heading/role hoặc tự cập nhật revision đang phục vụ.

Hợp đồng biên soạn tương lai trong602 chỉ tạo proposal đã gắn source-set/proof,
trả review_only. Chưa có endpoint lưu/duyệt hoặc compiler tổng hợp xuyên nguồn.
Scope/temporal metadata chứng minh vai trò khác với điều kiện nghiệp vụ bắt
buộc trong câu trả lời; việc phân loại này cần kiểm chứng độc lập ở đợt sau,
không dùng binding cấu trúc làm phê duyệt ngữ nghĩa.

[Thiết kế và ranh giới](../bao_cao/context602/COMPILATION_DESIGN.md) ·
[Kết quả thực chạy](../bao_cao/context602/VALIDATION_REPORT.md).
