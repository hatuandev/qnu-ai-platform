# Bản sạch và duyệt nội dung nguồn

> **TÀI LIỆU LỊCH SỬ — không phải hiện trạng V1.** Nội dung dưới đây mô tả hệ thống `backend/` + `frontend/` trước V1 (hai thư mục đã gỡ khỏi checkout) và chỉ dùng để truy vết. Bản đang chạy là [`backendV1/`](../../backendV1) + [`frontendV1/`](../../frontendV1); xem [bản đồ tài liệu](../README.md).

## Phạm vi phiên 510

Ba bước đầu của chuẩn hóa nguồn đã được triển khai trên ingestion/Studio hiện có:
chuẩn hóa giữ cấu trúc, đối chiếu bản sạch, kiểm tra toàn vẹn trước duyệt. Không
thay cấu hình retrieval/model, không tự nạp vector hoặc xuất bản.

## Cách sử dụng

1. Mở một nguồn trong Kho tri thức, chọn đúng revision và mở Studio.
2. Chọn **Đối chiếu**. Ảnh nguồn vẫn nằm bên cạnh. Text bóc tách ban đầu chỉ hiển
   thị khi revision thật sự đã lưu nó; bản cũ thiếu dữ liệu này được ghi rõ,
   không lấy Markdown đang sửa giả làm text gốc.
3. Chọn **Kiểm tra** để lấy đề xuất chuẩn hóa và báo cáo chỉ đọc. Xem toàn văn
   đề xuất trước khi chọn **Áp dụng đề xuất**. Thao tác áp dụng chỉ đổi nháp trên
   trình duyệt; chưa lưu DB, chưa duyệt và chưa nạp vector.
4. Đối chiếu trước–sau, các cảnh báo và bảng/công thức/chú thích với nguồn. Có thể
   bấm cảnh báo để đến trang và chọn dòng nếu xác minh được vị trí Markdown;
   cảnh báo toàn tài liệu/chưa ánh xạ không được gán bbox hoặc trang giả.
5. Nhập lý do hiệu đính và chọn **Lưu Markdown**. Server ghi actor từ session,
   lý do, thời gian, revision/hash gốc và hash bản mới. Bản sửa luôn chờ duyệt
   nếu không bị Quality Gate từ chối; không tự đổi active source/index.
6. Sau khi xem lại revision đã lưu, ghi chú đối chiếu và **Duyệt**. Với bản hiệu
   đính mới, server yêu cầu actor và ghi chú; client không tự cấp quyền duyệt.
   Nạp vector và xuất bản vẫn là các thao tác tách biệt theo luồng hiện có.

## Chuẩn hóa và kiểm tra

- `clean-content-v1` chuẩn hóa NFC, xuống dòng và khoảng trắng có kiểm soát;
  chỉ nối soft-wrap văn xuôi đủ rõ. Giữ nguyên danh sách lồng, code thụt lề/fence,
  dấu xuống dòng Markdown chủ ý, công thức, bảng, ảnh và chú thích.
- Không xóa dòng chỉ có số, không cắt ô thừa, không điền ô thiếu, không tự nối
  hàng/bảng chỉ vì giống số cột. Unknown vẫn unknown, ô trống khác số 0.
- Bản extraction và blocks/bbox gốc được giữ trong page manifest cho lần xử lý
  mới. Bản sửa giữ text extraction cũ, đánh dấu căn chỉnh layout stale.
- Chữ lặp ở mép trang chỉ là ứng viên header/footer; được đánh dấu nhưng không
  xóa. Thứ tự khối lặp được cảnh báo, không tự đoán lại thứ tự cột.
- Kiểm tra cấu trúc bảng/header, cột trống, header nhiều năm, encoding, đoạn ngắn,
  code/công thức chưa đóng, chú thích thiếu nội dung. Kết hợp các issues cấu trúc
  đã có trong source artifact, không thay thế toàn bộ Quality Gate.
- So với revision trước, ghi nhận khác biệt số/năm, phủ định, từ ngữ (có thể gồm
  đơn vị/điều kiện), phần bảng/công thức/chú thích bị giảm. Đây là heuristic và
  diff để người duyệt xem, không chứng minh mọi thay đổi ngữ nghĩa đã được phát hiện.
- Báo cáo luôn ghi `semantic_correctness=not_measured`; không dùng điểm heuristic
  làm chứng nhận OCR hay nội dung đúng. Không có model tự sửa hoặc tự phê duyệt.

## Contract và tương thích

- `POST .../sources/{source}/revisions/{revision}/clean-preview` dùng quyền
  `ai.knowledge.update`; body có `canonical_markdown` và tùy chọn
  `expected_canonical_hash`. Kết quả có revision, base hash, đề xuất và report.
  Service xác minh collection/binding/revision, không persist/gọi model.
- `PATCH .../content` thêm `change_reason` và `expected_canonical_hash`. Actor
  chỉ lấy từ session ở router; service từ chối thiếu actor/lý do. UI cũ hoặc
  client tự viết cần gửi lý do; thiếu sẽ nhận 422. Hash cũ sai nhận 409.
- Không cho tự thêm/đổi/mất số trang so với page manifest. Nguồn chưa có pagination
  đáng tin không được biến thành trang vật lý chỉ do client gửi marker.
- Không cần migration: dùng JSON metadata/page manifest hiện có. Phiên bản
  extraction tăng để lần bóc tách mới không tái dùng artifact của cleaner cũ.
- Các nguồn/index đang xuất bản không bị backfill/reindex hoặc tự chuyển revision.
  Không phục hồi text extraction cho revision cũ bằng suy đoán. Bóc tách lại nguồn
  thật, nhập sidecar của bản MD mẫu và nghiệm thu riêng cần yêu cầu khác.

## Chia đoạn và ghim phiên bản (bước 4–5, phiên 511)

- Sau duyệt, lần **Nạp vector** tiếp theo dùng `structure-chunks-v1`: giữ
  công thức/chú giải gần nhau cùng phạm vi, code fence, danh sách cha–con,
  hàng bảng/header/đơn vị và chú thích có liên kết. Footnote `[^id]` phải có
  định nghĩa duy nhất trong phạm vi. Không đoán nội dung chú giải còn thiếu.
- Preferred size của strategy không được cắt rời nhóm cấu trúc. Vượt hard
  `max_chars` sẽ báo cần kiểm tra cách chia; không xóa điều kiện để vừa ngân sách.
  Văn xuôi vẫn theo strategy, có kiểm tra không đổi/mất chữ so với nguồn.
- Tập chunks có seal `derived-bundle-v1`: source revision/hash, metadata,
  unit/context/facts/manifest/config cùng bản. Đổi annotation hoặc cleaner
  tạo key mới; re-embedding cùng tập hợp lệ không cần OCR lại.
- Luồng vận hành: **Duyệt → Nạp vector staging → Xem candidate → Xuất bản**.
  Không cần upload lại chỉ vì đổi chunker. Mã mới không tự reindex hoặc đổi
  index đang xuất bản; muốn áp dụng phải bảo đảm BE/worker nạp mã mới theo quy
  trình triển khai được phép, rồi chủ động dựng và kiểm tra staging.
- Xuất bản/rollback kiểm tra nguồn và artifact trước đổi serving pointer,
  kể cả sau remote I/O. Rollback từng nguồn trong cùng thế hệ giữ endpoint
  hiện có; đổi thế hệ dùng thao tác rollback thế hệ và chọn bản từng xuất bản.
  Bản staging chưa từng xuất bản không phải đích rollback.
- Bản sạch đang biên tập và index đang phục vụ là hai phiên bản độc lập.
  Rollback index không xóa bản sạch mới hoặc tự lùi draft. Points cũ của
  contract mới được giữ cho snapshot/rollback; GC xử lý retention riêng.
- Không migration/backfill. Index legacy tiếp tục tương thích, nhưng không
  được gán nhãn đã có seal mới. Thiếu lịch sử rollback hiện đại thì báo rõ.
- Hash là kiểm tra toàn vẹn dữ liệu đã lưu, không chứng nhận OCR chính xác,
  không thay việc đối chiếu nguồn và không tự xác nhận công thức đúng.

## Giới hạn nghiệm thu hiện tại

Unit/API handler và build không thay kiểm tra UI trong phiên đã đăng nhập hoặc
nghiệm thu OCR/PDF/DOCX trên dịch vụ thật. Chunker mới đã kiểm tra cấu trúc và
DB contract, chưa đo tác động chất lượng RAG sau tái lập chỉ mục. Diff UI là so cùng số dòng, không phải semantic
alignment. Thông tin vị trí thiếu được hiển thị trung thực.
