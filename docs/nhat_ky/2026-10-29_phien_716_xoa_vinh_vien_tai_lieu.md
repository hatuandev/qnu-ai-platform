# Phiên716 — Xóa vĩnh viễn tài liệu và bảo vệ bản phát hành

## Yêu cầu và phạm vi

- Người dùng không cần trang Tài nguyên; muốn xóa trực tiếp tệp tài liệu trong kho.
  Xác nhận thêm: tài liệu đang phát hành phải ngừng/thu hồi trước khi xóa.
- Diễn giải được thông báo: phải `withdraw` mọi bản biên soạn phụ thuộc còn
  `published`; tắt chatbot hoặc archive nguồn/văn bản không thay cho thu hồi.
- Ngoại lệ có phạm vi được ghi ADR005: `backendV1 source/delete` là xóa vĩnh viễn
  có xác nhận, không sửa bằng chứng âm thầm. Các loại delete khác vẫn xóa mềm.
- Giữ yêu cầu không chạy test từ phiên review trước. Không thao tác dữ liệu thật,
  gọi API/model, migrate, đổi env, restart, reindex, deploy hay Git commit/push.
  Git đã có commit đồng thời trong phiên; giữ nguyên, không reset thay đổi đó.

## Thay đổi

- `lifecycle/purge_graph.py`: đồ thị FK theo allowlist, truy ngược input/provenance
  Compiler và các hậu duệ edit; kiểm workspace, publication, phụ thuộc ngoài phạm
  vi và giới hạn 10.000 hàng. Chỉ xóa chat turn có `sources[].version_id` đúng,
  không dò từ khóa trong nội dung. Ghim PK, object key/hash; không lưu nội dung
  vào ledger. Giữ nguồn khác/phiên bản không phụ thuộc.
- `lifecycle/purge.py`, service/router/schemas: preview/accept/worker kiểm lại
  `published`, actor và target. Intent `pending` lưu bền vững trên biên nhận cũ,
  hủy tác vụ liên quan và chặn nguồn; chờ 1800 giây nếu còn worker chạy. Chỉ nhận
  output muộn trong các run đã ghim, không thêm lineage mới. Lỗi giữ pending,
  retry cùng action/key; chỉ completed sau khi dọn thành công. Kế hoạch nội bộ
  bị loại khỏi JSON response. API liệt kê yêu cầu chờ gắn actor và collection.
- Tái sử dụng worker/operations reconciler hiện có với `source_purge_job`;
  không thêm framework, migration hoặc dependency.
- Blob port/Local/S3: purge đúng key; S3 dọn version/delete marker, không tạo
  marker mới khi key đã mất. Kiểm hash, khóa cùng workspace và chặn object dùng
  chung. Xóa raw/ảnh OCR đã đăng ký, MD/JSON và artifact Compiler/review liên quan.
- Vector port/Qdrant: chỉ xóa đúng point của chunk liên quan, không xóa collection
  chung. Manifest dẫn xuất giữ phần input/chunk còn lại và chuỗi hash gốc để
  generation còn phục vụ và recovery không yêu cầu chunk đã purge; không gọi model.
- FE: xác nhận xóa vĩnh viễn trong kho/chi tiết tài liệu, không nhảy Tài nguyên.
  Dialog không mất khi row biến khỏi danh sách; có theo dõi/tiếp tục sau reload,
  scope theo session/workspace/kho, trạng thái chờ/lỗi trung thực. Hoàn tất làm
  mới danh sách hoặc về kho cha. Ẩn Tài nguyên; URL cũ chuyển sang biên nhận vận
  hành. Thành viên chỉ nhận biên nhận hội thoại của mình, không tải dữ liệu Ops.
- Cập nhật hướng dẫn vòng đời31/34, hướng dẫn chạy38, ADR005 và tài liệu backend.

## Regression đã viết, chưa chạy

- 9 unit: handler409 published, accept kiểm lại sau preview, lỗi storage/retry,
  scope key, ẩn private plan, raw muộn trong run ghim/chặn version mới, xóa đúng
  S3 version/marker và retry không tạo marker, kiểm lại quyền worker, reseal
  manifest không đụng chunk còn lại.
- 2 integration opt-in DB riêng: published vẫn chặn dù archive document;
  nguồn chưa phát hành lưu intent khi queue lỗi rồi purge vật lý, giữ nguồn khác,
  replay biên nhận và không restore. Dữ liệu synthetic, không dùng corpus thật.
- 2 FE: publication409 không submit/chuyển trang; thành viên chỉ xem receipt
  không tải trang vận hành. Điều chỉnh regression cũ về nút xóa và điều hướng;
  ca xóa nguồn mềm cũ chuyển sang archive hoặc delete collection đúng nghiệp vụ.
- Tất cả **NOT RUN** theo yêu cầu người dùng; chưa có bằng chứng runtime.

## Kiểm tra thực chạy

- Scoped Ruff check/format trên15 file BE: PASS; không lint/fix toàn repo.
- Scoped Biome check trên11 file FE: PASS; TypeScript `npm run typecheck`: PASS.
- Python AST15 file, UTF-8 không BOM/LF36 file thuộc phạm vi và `git diff --check`:
  PASS, exit0. Ruff/Biome/TypeScript cũng exit0. Không import app hoặc chạy
  Pytest/Vitest/build; không có số test PASS/FAIL vì toàn bộ test NOT RUN.

## Giới hạn và bước vận hành

- Xóa là không thể restore sau khi nhận; lỗi giữa chừng có thể đã dọn một phần.
  Không tuyên bố transaction phân tán/rollback tệp. Đổi quyền, target, lineage,
  object dùng chung, giới hạn đồ thị hoặc S3 Object Lock đều chặn hoàn tất.
- Platform admin muốn chạy job nền cần được phân giải quyền bền vững qua DB hoặc
  cầu dev-admin hiện có; không sao chép quyền JWT để qua kiểm tra khi worker chạy.
- Giữ audit/idempotency, hash/manifest lịch sử và các bundle backup đã tạo theo
  chính sách riêng. Orphan không có tham chiếu DB thuộc luồng cleanup riêng;
  đây không phải cam kết xóa backup hay toàn bộ bản sao ngoài hệ thống QNU.
- Cần dừng/chạy lại `v1-dev` để API/worker nạp mã; phiên này chưa restart.
  Sau khi người dùng cho phép kiểm chứng: chạy regression trong DB/storage/vector
  riêng, đặc biệt published race, worker đang inference, MinIO versioning, retry
  sau crash và kho có nhiều nguồn/index dùng chung. Chưa nghiệm thu runtime.
