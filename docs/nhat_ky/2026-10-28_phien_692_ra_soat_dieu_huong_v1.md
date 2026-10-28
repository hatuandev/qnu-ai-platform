# Phiên 692 — Rà soát lại điều hướng V1

Người dùng báo sidebar/router vẫn chưa ổn và yêu cầu rà lại, điều chỉnh đầy đủ.
Đọc mã hiện tại, snapshot691, Git/diff và kiểm tra trình duyệt trên dịch vụ V1
đang chạy. Áp dụng skill frontend/clean-code và computer-use. Phạm vi là điều
hướng/giao diện V1; giữ thay đổi trước đó của người dùng.

## Phát hiện và sửa

- Chọn workspace trên màn chọn kho chưa cập nhật scope sidebar. Khi mở chức
  năng khác, người dùng phải chọn lại. Chuyển sang một nguồn cấu hình tại
  `src/navigation/workspace-features.ts`, được export qua config.ts; sidebar,
  picker, command menu và breadcrumb dùng chung. Bỏ module destinations cũ
  không còn caller, không duy trì hai danh mục.
- Scope workspace/kho theo URL và bộ nhớ phiên do shell giữ bằng React Context;
  đóng Sheet mobile không mất lựa chọn. Giữ kho khi chuyển trang trong cùng
  workspace; đổi workspace hoặc phiên không giữ kho cũ. URL chỉ là lựa chọn,
  không chứng minh quyền; API/query hiện có tiếp tục kiểm quyền server.
- Màn chọn tách khỏi file route, có loading/error/retry/trống/phân trang và
  nút tạo workspace/kho dùng dialog thật sẵn có, theo quyền. Workspace tạm
  dừng có lối quản lý trạng thái. Không tự chọn hay tạo dữ liệu.
- Active menu phân biệt tab kho, trang chi tiết và view vận hành; thêm lối
  Xuất bản tới tab documents. OCR chuyển `sourceAction=ocr` xuống các link
  nguồn và sau upload, mở tab OCR thay vì preview mặc định.
- Ctrl+K có menu QNU riêng cùng scope; header workspace đồng bộ nhãn. Bỏ các
  nút notification/quick-create mẫu và banner kỹ thuật KTX khỏi header V1.
  Đổi tiêu đề trình duyệt sang QNU AI Platform. Giữ nguồn template ngoài V1.
- Hướng dẫn chạy38 bổ sung cách chọn workspace/kho và dùng sidebar/Ctrl+K.

## Kiểm chứng đã chạy

Cwd `frontendV1`, trừ kiểm diff/hash/link ở gốc:

- Biome các file thay đổi: PASS, exit0; receipt
  `storage/artifacts/context692-biome-scoped-final.log`. Chạy nhầm từ gốc
  từng gặp lỗi config của Biome gốc; chạy lại bằng binary cục bộ/cwd V1 đạt,
  không sửa config để né lỗi.
- Test trọng tâm cuối: `npm exec -- vitest run tests/workspace-sidebar-689.test.tsx
  tests/sidebar-navigation-691.test.tsx tests/navigation-scope-692.test.tsx
  tests/feature-entry-692.test.tsx --maxWorkers=2`: **37PASS/0FAIL**, exit0.
  Test gồm router thật, chọn workspace/kho, error/retry, quyền tạo, workspace
  tạm dừng, session đổi, mount/unmount mobile và từng đích/tab/view.
- Full FE `npm run test -- --maxWorkers=2 --reporter=json
  --outputFile=../storage/artifacts/context692-fe-full.json`:
  **385PASS/0FAIL/0SKIP, 37files/45suites, exit0**. Chạy trước việc làm rõ đuôi import
  `.tsx` để Vite đang chạy bỏ cache đường dẫn `.ts`; sau đó chạy lại37test
  trọng tâm và build. Không lặp full suite cho thay đổi import tương đương.
- `npm run build` gồm TypeScript: PASS, exit0, receipt
  `storage/artifacts/context692-build-verified.log`. Còn cảnh báo chunk lớn.
- Thử đầu có lỗi TS optional target/props test cũ, label test cũ và một test
  session mock không kích hoạt consumer render; đã sửa nguyên nhân và fixture,
  không bỏ guard hoặc tăng timeout. Giữ receipt đầu để truy vết.
- Kiểm browser trên FE3001/API8002: chọn workspace cập nhật sidebar; các trang
  trợ lý/hội thoại/thành viên/hạn mức/nhật ký và ba view vận hành mở được; Ctrl+K
  chỉ danh mục QNU; biểu mẫu tạo kho mở rồi Hủy, không submit. Trên390×844,
  menu tự đóng sau chọn trang; mở lại sau chuyển ModelOps vẫn giữ workspace.
- Sau đổi file hook từ `.ts` sang `.tsx`, Vite dev từng giữ import `.ts` cũ
  khiến trang trắng khi reload. Sửa import rõ đuôi trên ba caller, kiểm reload
  trang mới thành công; console error trang mới rỗng. Không restart dịch vụ.
- Ảnh trong `storage/artifacts/context692-navigation-review/`:
  `desktop-selector-final.png`, `mobile-scope-final.png`;
  hash baseline trước task và danh sách file thay đổi cùng thư mục.

## Giới hạn và bàn giao

Workspace đang có trên máy chưa có kho. Browser chứng minh điều hướng/trống/
dialog; phần chọn kho có dữ liệu được kiểm bằng fixture router, chưa chạy
OCR/Compiler/LLM hay luồng tài liệu thật trong phiên này. Không tạo hoặc sửa
dữ liệu live, không sửa backend, credential, env, quyền, schema, cấu hình đang
chạy; không reindex/restart/deploy/commit/push. Không gọi backend suite vì
không đổi hành vi server. Khôi phục kích thước browser và đóng tab kiểm thử.

[Snapshot692](../memory/snapshots/2026-10-28_session_692.md).
