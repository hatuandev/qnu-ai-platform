# Phiên 849 — Tối ưu chuyển tab biên soạn

## Yêu cầu và nguyên nhân

Người dùng chấp thuận giữ các tab đã mở, hiển thị nội dung nặng theo nhu
cầu, dùng lại dữ liệu và tách việc chờ AI review khỏi chuyển tab.

Đo trước sửa trên tài liệu local: 23 mục, 80 đoạn, 8 bảng, 200 ô và 641
dẫn chứng; draft khoảng 696 KB, API khoảng 307 ms. Quay về draft mất
10.464 ms; browser ghi nhận hai long task khoảng 3,8–4 giây. Editor cũ
liệt kê mọi dẫn chứng tại từng đoạn, tạo 80 × 641 = 51.280 lựa chọn.
Radix Tabs mặc định tháo nội dung khi đổi tab nên editor bị hủy và dựng lại.
Auto-review đang chạy là công việc riêng, không phải trạng thái tải draft.

## Thay đổi trong frontendV1

- `compilation-detail-page.tsx`: khởi tạo tab ở lần mở đầu; force-mount tab
  đã ghé và ẩn tab không hoạt động. Session có key theo phiên đăng nhập,
  workspace, collection và run. Reset toàn bộ khi đổi scope; chỉ tải draft
  khi đã mở tab draft. Tiếp tục dùng các query key có scope hiện hành.
- `compilation-editor-tab.tsx`: giữ bản nháp và DOM input khi đổi tab.
  Cho qua điều hướng chỉ đổi search trong cùng pathname; rời trang/run khác
  và before-unload vẫn được bảo vệ khi chưa lưu. Preview và bộ chọn dẫn
  chứng không hiện lên trên tab khác khi editor bị ẩn.
- `compilation-citation-picker.tsx`: một dialog cho đoạn đang sửa, tìm kiếm
  và phân trang 20 lựa chọn. Không nhân toàn bộ index cho từng đoạn. Giữ
  nguyên ID trong bản nháp/payload và quy trình preview → xác nhận lưu.
- `compilation-draft-sections.tsx`: các mục mở theo nhu cầu, mặc định mục
  đầu mở; memo theo sections và callback ổn định. Nút dẫn chứng chuyển đúng
  ID gốc sang drawer, không hiển thị ID dài trong từng đoạn.
- `source-tables-view.tsx`: compiler dùng `deferContent`; chỉ dựng ma trận
  của bảng khi mở. Consumer khác vẫn mở sẵn theo mặc định. Giữ hàng, cột,
  rowSpan/colSpan và citation; header có wrap cho màn hình hẹp.
- `compilation-review-tab.tsx`: giữ polling trạng thái đang chạy theo hook
  hiện có; ẩn dialog tạo review nếu tab không hoạt động. Không tự tạo thêm
  review hay gọi lại model khi chuyển tab.
- `compilation-types.ts`, `citation-drawer.tsx`: canonical citation thật dùng
  trường `page`; hỗ trợ trường này cùng `page_number` trong bộ chọn và điều
  hướng về trang nguồn. Không suy trang từ tên file/ID.

Không đổi backend, nguồn, model, token, trạng thái xuất bản hoặc nội dung
biên soạn đã lưu. Giữ các thay đổi chưa commit từ phiên 848.

## Kiểm chứng

Từ `frontendV1`:

- Regression mới tại `tests/compilation-tabs-849.test.tsx` và
  `tests/compilation-reading-849.test.tsx`; bổ sung trường hợp dialog tab ẩn
  tại `tests/compilation-ui-671.test.tsx`. Bao phủ giữ input/nháp qua tab,
  reset khi đổi run/session, guard điều hướng, chọn dẫn chứng qua trang,
  payload giữ lựa chọn, lazy section/table, ô gộp và canonical page.
- Bản thử ban đầu 3 FAIL/1 PASS; một test dùng bare click không kích hoạt
  Radix Tab trong jsdom, đã chuyển sang sự kiện bàn phím Enter hợp lệ.
  Các regression sau sửa đạt; targeted 16/16 PASS trước batch canonical page.
- Gate cuối `npm exec -- vitest run --maxWorkers=2`: exit 0, 90 suite,
  756/756 PASS, 120,07 giây. Không tăng timeout hoặc bỏ assertion.
- Biome 11 file source/test: exit 0.
- `npm run build`: exit 0, gồm TypeScript; vẫn có cảnh báo chunk trên 500 KB
  ngoài phạm vi task.

Từ root, Chrome headless riêng, không dùng phiên trình duyệt của người dùng:

- `node tmp/verify-compilation-tabs-849.mjs`: exit 0. Giữ nguyên editor DOM
  và chữ sửa tạm qua draft/review/edit, sau đó hoàn nguyên chữ trong phiên
  trình duyệt kiểm tra; không gửi ghi dữ liệu. Mở thêm section, một bảng,
  drawer nguồn, bộ chọn dẫn chứng và trang thứ hai của danh sách.
- Sau batch cuối: các lần chuyển tab bình thường 164/131/247/217/233 ms
  (tính tới frame sau cập nhật). Lần quay về draft ngay sau đổi viewport từ
  mobile về desktop mất 1.259 ms; không tuyên bố mọi lần đều dưới 500 ms.
- Số node của draft lúc đầu giảm từ 2.531 xuống 397. Draft GET 1 lần;
  edit-context có 2 request lúc khởi tạo. Các số này không tăng trong vòng
  đổi tab sau khi editor sẵn sàng. Phép đo đầu từng FAIL vì giả định mọi
  request khởi tạo phải đúng 1; đã đổi kiểm chứng sang so sánh trước/sau
  vòng chuyển tab. Chưa quy nguyên nhân hai request khởi tạo.
- Desktop 1366×900 và dialog mobile 390×844: đã xem ảnh; dialog không tràn,
  20 checkbox mỗi trang, 0 page error, 0 write request. Artifact chỉ ở
  `tmp/compilation-tabs-849/`; không đưa nội dung tài liệu vào Git.
- `git diff --check`: exit 0.

## Giới hạn

Đây là đo trên một tài liệu và môi trường dev local, không phải benchmark
mọi kích thước máy/tệp. Lần tải dữ liệu đầu vẫn phụ thuộc API và mạng.
Không chạy backend suite hoặc inference vì không sửa contract/server/model;
không restart, reindex, publish, commit hoặc push.
