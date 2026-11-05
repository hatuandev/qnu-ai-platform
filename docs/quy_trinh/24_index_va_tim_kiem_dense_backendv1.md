# 24 — Chỉ mục và tìm kiếm dense backendV1

Phạm vi: `backendV1/`, tiếp sau [duyệt/xuất bản](23_phien_ban_va_xuat_ban_backendv1.md).
Workspace là biên giới quyền của v1 theo ngoại lệ AGENTS; không thay cơ chế của `backend/`.

## Cập nhật Context878 — Tự phục vụ trợ lý sau phát hành

- Người dùng tiếp tục biên soạn, kiểm tra và Duyệt & Phát hành như trước. Chỉ bản đã
  phát hành hợp lệ mới được đưa vào tìm kiếm; bản nháp không tự phục vụ hội thoại.
- Commit phát hành/thu hồi đồng thời ghi ý định `kb_index_sync` trong PostgreSQL.
  API trả sớm, worker hiện có nhận việc nền; cron mỗi phút và lúc worker khởi động
  khôi phục ý định khi Redis mất kết nối. Nhiều thay đổi được gom theo collection,
  khóa quyền và khóa hàng ngăn delivery trùng tạo nhiều lượt embedding.
- Worker dùng default embedding được cấp qua ModelOps, giữ snapshot và kiểm lại
  quyền/nguồn/hash trước khi kích hoạt. Chỉ đổi active sau khi generation mới hoàn
  tất; lỗi giữ generation cũ, các cổng eligibility vẫn loại nội dung đã thu hồi.
  Provider/permission/configuration lỗi được báo rõ. `uncertain` không tự gửi lại.
- FE bỏ đường dẫn “Tìm kiếm thử & Chỉ mục” trong luồng thường và bỏ nút tạo index
  trên trang tài liệu/phiên bản. Sau phát hành hiển thị “Đang cập nhật cho trợ lý AI”
  rồi “Sẵn sàng cho trợ lý AI” khi đúng version/state/hash. Có kiểm tra lại trạng thái
  đọc lỗi và yêu cầu cập nhật mới có quyền, idempotency và audit nếu tác vụ thất bại.
  API/index/search cũ vẫn giữ cho runtime RAG, kiểm thử và liên kết tương thích.
- Dọn vector nền giữ active và một generation inactive gần nhất
  (`INDEX_RETAIN_INACTIVE=1`). Generation cũ hơn chỉ đủ điều kiện sau 24 giờ từ
  lúc bị thay (`INDEX_RETIRE_AFTER_SECONDS=86400`), đúng vector target và có active
  mới hơn. Kiểm lại dưới cùng khóa quyền với retrieval trước khi xóa namespace.
  Chỉ bỏ Qdrant và SQL vector staging; giữ nguồn, chunk text, cấu trúc, dẫn chứng,
  manifest, receipt và lịch sử. Lượt failed/uncertain và generation cũ không rõ
  thời điểm deactivation được giữ, không đoán hạn xóa.
- Migration mới `0014_publication_index_sync`. Với DB local đang chạy: dừng phiên
  dev, chạy `./make.ps1 v1-migrate`, rồi `./make.ps1 dev`; không clear/reset.
  Không tự reindex các tài liệu cũ chỉ vì mở trang. Bản cũ chưa có ý định sync có
  thể dùng “Thử cập nhật” trên trang tài liệu đã phát hành; phát hành mới tự chạy.
- Phạm vi đợt này là bước 1–2: tự động chỉ mục sau phát hành và vòng đời vector.
  Chưa tự trích metadata JSON, chưa đổi compiler nhanh/AI và chưa bỏ bước duyệt.

## Cập nhật Context880 — Metadata JSON và bộ lọc động

Sau biên soạn, hộp đăng ký đưa đề xuất metadata có trích đoạn nguồn lên trước.
Người dùng chọn từng đề xuất, có thể chỉnh giá trị và trích đoạn trong cùng dẫn
chứng hoặc bổ sung thuộc tính mới. Thuộc tính JSON giữ kiểu văn bản, số hoặc
logic; mã có số 0 ở đầu nên dùng văn bản. Server kiểm lại target, nguyên văn,
nguồn đã ghim, xung đột và idempotency trước khi tạo phiên bản. Đề xuất chưa chọn
không tự trở thành bộ lọc. Chỉnh metadata không sửa bản OCR hoặc bản nháp gốc.

- `GET .../collections/{collection_id}/search-facets` trả danh mục thuộc tính
  đã xác nhận của các bản đang phát hành, còn hợp lệ trong chỉ mục active.
  Endpoint chỉ đọc, có kiểm quyền workspace/collection và kiểm manifest/hash.
  Không có chỉ mục thì trả `ready=false`; lỗi đọc nguồn/hạ tầng vẫn là lỗi.
  Danh mục UI trả tối đa 50 trường, mỗi trường 50 giá trị và báo `truncated` nếu
  chưa hiển thị hết. Đây là giới hạn hiển thị, không xóa metadata đã lưu.
- Bộ lọc trợ lý, hội thoại và công cụ tìm thử thêm các trường từ danh mục thật,
  giữ lựa chọn đã lưu kể cả khi giá trị đó không còn trong danh mục hiện hành.
  Các trường năm/ngành/đợt cũ tiếp tục tương thích. Thuộc tính JSON gửi trong
  `metadata_filter.attributes`; các trường trong một bộ lọc phải cùng khớp trên
  một annotation, không ghép giá trị từ những hàng khác nhau.
- Trợ lý mới mặc định `scope_resolution=catalog`, `context_window=1`. Trợ lý và
  hội thoại đã lưu giữ chính sách cũ. Bộ nhận diện chỉ ánh xạ nhãn và giá trị
  thực sự có trong metadata đã xác nhận; mơ hồ/không nhận diện được giá trị đã
  nêu thì yêu cầu làm rõ. Không tự đoán thuộc tính từ tên tệp, không gọi thêm
  LLM cho bước lọc, không nới bộ lọc khi không có kết quả.
- Số `12`, chuỗi `"12"` và logic `true` giữ kiểu riêng; không chọn tùy tiện khi
  cùng cách viết có nhiều kiểu. `12` và `12.0` cùng là giá trị số JSON.
  Năm ban hành và năm dữ liệu vẫn tách vai trò. Tài liệu cũ chưa có metadata
  không bị gán một năm đoán từ câu hỏi hoặc từ tên tệp.
- Bộ lọc cố định của trợ lý, phạm vi từ lượt trước và lựa chọn bổ sung ở lượt
  hiện tại được gộp theo từng thuộc tính. Yêu cầu trái phạm vi cố định bị chặn.
  Scope được áp trước TopK ở cả dense và hybrid, cùng các cổng nguồn/xuất bản.
- Sau Duyệt & Phát hành, bước lập chỉ mục tự động của Context878 chạy nền.
  Người dùng chờ trạng thái “Sẵn sàng cho trợ lý AI”. Trang Tìm kiếm & Chỉ mục
  chỉ còn đường quản trị nâng cao cho người có quyền; không phải bước bắt buộc
  trong luồng sử dụng thông thường. Không tự backfill metadata tài liệu cũ.

Bước 5–6 giữ serialization của bộ lọc cũ và hash của yêu cầu đăng ký không có
chỉnh đề xuất. Không thêm migration mới ngoài `0014_publication_index_sync` của
bước 1–2. Nếu DB chưa áp migration này, dừng dev, chạy `./make.ps1 v1-migrate`
rồi `./make.ps1 dev`; không cần clear/reset dữ liệu để nhận thay đổi.

## Điều kiện đầu vào

Document có phiên bản đang xuất bản, receipt hợp lệ và nguồn/revision/hash còn
đúng. ModelOps có provider embedding đang hoạt động, credential mã hóa, grant
workspace, default hoặc provider được chọn, dimension/capacity và quota.
Qdrant/Redis/storage là cấu hình hạ tầng server, không lấy URL từ model hoặc body.

## Thứ tự nghiệp vụ

1. Editor/admin yêu cầu indexing bằng Idempotency-Key. Server chụp publication,
   chia đoạn và nhóm bảng giữ citation/ô/header/span/footnote từ snapshot gốc;
   lưu run/input/chunk và audit trước dispatch.
   Chỉ mục mới lấy tiêu đề nguồn có căn cứ cho đoạn và bảng của cả hai chế độ
   biên soạn. Nếu một đoạn tổng hợp nhiều mục, giữ tiêu đề biên soạn của đoạn.
   Với bảng sát ngân sách, giữ tiêu đề trong metadata để bảo toàn nhóm hàng.
   Chỉ mục v5 bỏ bản sao chữ trùng nguyên văn với các hàng của bảng đã bóc tách
   khi đoạn chỉ dẫn đúng bảng đó. Đoạn có metadata riêng, dẫn chứng khác hoặc
   nội dung bổ sung vẫn được lập chỉ mục theo đoạn.
   Kích thước đoạn mặc định tự tính theo model embedding được phép dùng. Không
   áp trần mặc định 3.000 byte; `INDEX_CHUNK_MAX_BYTES` chỉ dành cho cấu hình
   operator tường minh. Khi bật ngữ cảnh nguồn, tính đúng byte của tiêu đề,
   metadata và định nghĩa cho từng đoạn/nhóm hàng, không trừ dự phòng cố định.
   Tài liệu được chia đầy đủ với dẫn chứng; nhóm hàng không thể tách mà vẫn vượt
   khả năng model được báo lỗi rõ, không bỏ ô hoặc cắt mất nội dung.
2. Worker ARQ kiểm quyền/nguồn/model, reserve quota, gọi embedding theo batch.
   Raw response có hash, vector staging và usage receipt được giữ bền vững.
3. Ghi vào Qdrant generation riêng, xác nhận hoàn thành, kiểm lại snapshot,
   lưu manifest rồi kích hoạt. Generation mới lỗi giữ active generation cũ.
4. Người có quyền tìm trong collection và document scope tùy chọn. Chỉ tài liệu
   còn hợp lệ mới vào filter trước TopK; query dùng đúng model/config của index.
5. Sau embedding kiểm lại quyền/publication; đối chiếu hit với SQL/manifest,
   trả đoạn/bảng và citation revision/page/block. Thu hồi hoặc nguồn đổi loại
   nội dung; publication mới cần generation mới. Lỗi hạ tầng trả lỗi rõ.

Khi tạo câu trả lời từ bảng PDF có số thứ tự, RAG kiểm lại trên bản nguồn đã
ghim. Chỉ nối khi hai mảnh liền trang, nằm ở biên trang, cùng mép và số cột,
không có khối nội dung chen giữa, và số thứ tự chạy liên tục. Một hàng đầu
trang khuyết các ô định danh có thể tiếp nối hàng cuối trang trước nếu có
chứng cứ cấu trúc. Tìm thấy một nửa thì lấy nửa còn lại và hàng tiêu đề,
trong cùng phiên bản xuất bản, cùng phạm vi metadata và ngân sách hiện có.
Hai phần giữ dẫn chứng ô và trang riêng. Bảng chưa đủ căn cứ vẫn giữ từng mảnh.

Job mất delivery được reconcile; mất lease có fencing. Batch embedding chưa rõ
kết quả chuyển `uncertain`, không tự gọi lại. Batch đã lưu vector có thể upsert
lại cùng ID sau lỗi vector. Không tự xóa history/raw hoặc active generation.

## Kiểm chứng và bước sau

Live BGE-M3 trên server người dùng chỉ định đã qua ModelOps/ARQ/Qdrant/search
với dữ liệu mẫu: vector1024,2chunk, bảng150 và citation đúng, withdraw chặn kết quả
và không gọi embedding thêm. OCR/chat mẫu giả lập; chưa nghiệm thu chất lượng
corpus thật. Mã hiện tại là dense retrieval, chưa hybrid/rerank hoặc RAG answer.

Cần migration0009 và cấu hình ModelOps trong môi trường phục vụ trước khi vận hành;
phiên này chỉ áp DB thử. Không restart/deploy hoặc publish/index tài liệu thật.

[API/vận hành](../../backendV1/docs/dense-indexing.md) ·
[Báo cáo647](../bao_cao/context647/REVIEW.md).
