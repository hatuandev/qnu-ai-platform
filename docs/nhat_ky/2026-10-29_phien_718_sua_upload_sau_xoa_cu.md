# Phiên718 — Upload báo trùng sau xóa mềm trên API cũ

## Yêu cầu và bằng chứng

- Người dùng gửi ảnh: kho không còn tài liệu, upload cùng tệp báo409 duplicate,
  phần theo dõi xóa báo không đọc được trạng thái; yêu cầu tìm nguyên nhân và sửa.
- Giữ yêu cầu không chạy test. Đọc mã, Git/diff và kiểm tra chỉ đọc để chẩn đoán;
  không tạo/xác nhận purge, sửa DB/tệp, gọi model, restart hoặc đổi cấu hình.
- GET OpenAPI của API V1 đang chạy trả200 nhưng không có endpoint
  `/lifecycle/source-deletions`: tiến trình đang dùng mã cũ, FE đã nạp mã mới.
- SELECT trong transaction PostgreSQL READ ONLY theo đúng workspace/collection
  của ảnh: action delete đã completed, result giữ originals, không có permanent;
  bản ghi nguồn còn và lifecycle state deleted. Đây là xóa mềm, không phải purge.
- Thử đọc với backendV1/.env bị InvalidPasswordError; chọn lại root .env theo
  mặc định thực tế của runner và đọc được. Không in hoặc sửa credential/env.
- Đọc đồ thị phụ thuộc bằng mã hiện tại trong transaction READ ONLY:48hàng,
  32tham chiếu object, không bị chặn bởi bản published. Chỉ nạp ORM và SELECT;
  không chạy lifespan, dispatch/job/model/storage/vector mutation. Số liệu này
  không phải bằng chứng đã xóa hoặc kiểm chứng runtime ghi dữ liệu.

## Nguyên nhân

V1-dev không hot-reload API/worker như FE. Mã purge mới đã có trong repository
nhưng tiến trình cũ vẫn đánh dấu deleted và giữ revision/tệp; query chống trùng
đúng khi tiếp tục tìm thấy checksum. FE gọi endpoint mới trên API cũ nhận404.
Ngoài ra chưa có lối xử lý tài liệu xóa mềm từ trước: nguồn không còn trong danh
sách và transition delete trên state deleted bị chặn.

## Thay đổi

- Backend thêm GET `/lifecycle/source-deletions/legacy` có DTO, phân trang và
  kiểm quyền admin/collection. Chỉ liệt kê nguồn đã deleted còn tồn tại, loại bỏ
  nguồn đang có action delete pending của bất kỳ actor nào. Không tự tạo action.
- Cho phép riêng source/delete trên state deleted để xem trước và xác nhận mới.
  Giữ guard pending, published, hash, quyền và worker hiện có; không đổi transition
  delete của collection/document/assistant và không cần restore làm nguồn hiện lại.
- Upload phân biệt nội dung đã có, xóa mềm cũ, purge pending và revision không đổi.
  Cả nhánh kiểm tra trước ghi và nhánh đua unique đều dùng cùng thông báo. Bỏ ID
  nội bộ trong detail; không bỏ uniqueness hoặc bỏ nguồn ẩn khỏi chống trùng.
- FE dùng path/request/type dùng chung. Tại kho có danh sách phẳng **Tài liệu đã
  xóa còn giữ tệp**, một menu ⋯/hàng với **Hoàn tất xóa**. Mở preview/confirmation
  mới; pending dùng lại đúng action đã nhận. Không tái sử dụng biên nhận soft-delete
  completed như một purge đã hoàn thành, không xóa ngầm khi upload hay GET danh sách.
- Endpoint404 không có mã lỗi nghiệp vụ hiển thị cần nạp API/worker mới; có nút
  Tải lại trạng thái, ngừng polling lỗi liên tục. Các lỗi nghiệp vụ404 khác không
  bị đánh đồng với phiên bản API. Giữ scoping theo session/workspace/kho và phân trang.
- Dialog chặn preview từ API chỉ biết xóa mềm; chỉ báo purge completed khi receipt
  có permanent=true, originals_retained=false và restore_available=false. Không
  đóng dialog/toast thành công vĩnh viễn chỉ vì API cũ trả status completed.
- Giữ diff FE717 đang có; không sửa sidebar/progress hoặc các trang người dùng đang vibe.
- Tài liệu vòng đời backend và quy trình31 có hướng dẫn xử lý dữ liệu legacy.

## Kiểm chứng

- Scoped Ruff trên7file BE: PASS, exit0; format có phạm vi.
- Scoped Biome trên7file FE, TypeScript và build FE: PASS, exit0 sau guard
  receipt/preview. Build còn cảnh báo native-config import thiếu extension và
  bundle lớn có sẵn, không sửa lan sang cấu hình/sidebar đang vibe.
- Python AST7file, UTF-8 không BOM/LF21file có phạm vi và diff-check: PASS.
-12regression viết nhưng **NOT RUN**:4unit về transition/duplicate;3integration
  DB riêng về inventory/confirmation/purge/reupload, quyền và published;5FE về
  legacy không tự xóa, pending receipt, server cũ404, preview mềm và proof completed.
- Không chạy Pytest/Vitest/E2E hoặc live inference. Không xác nhận purge thực tế.

## Bước tiếp theo

1. Người dùng dừng phiên v1-dev cũ rồi chạy lại `./make.ps1 v1-dev` để cả API và
   worker nạp bản sửa; chỉ refresh trình duyệt không đủ. Không cần migration.
2. Đóng hộp upload, tại kho chọn nguồn trong **Tài liệu đã xóa còn giữ tệp → ⋯ →
   Hoàn tất xóa**, xem trước/xác nhận và chờ completed rồi upload lại.
3. Nếu nguồn còn published phải withdraw trước; nếu worker/storage lỗi, giữ
   pending để tiếp tục cùng action. Không bỏ guard để cho upload chen vào.

Giới hạn: phiên này chưa restart runtime hoặc chuyển/xóa dữ liệu legacy thật.
Các thay đổi chỉ có hiệu lực sau khi API/worker nạp mã và người dùng xác nhận.
