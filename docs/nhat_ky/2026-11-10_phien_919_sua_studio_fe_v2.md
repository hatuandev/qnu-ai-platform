# Phiên 919 — Sửa Studio FE V2 và thu gọn giao diện

Ngày: 2026-11-10. Phạm vi: bốn lỗi sau lần rà Studio và giao diện chi tiết; không đổi backend, nguồn tài liệu, RAG hay DB ứng dụng.

## Lỗi và thay đổi

1. Viewer Word không mount target ở trạng thái ban đầu nên chờ vô hạn. Giữ target luôn mount, render vào staging riêng để kết quả cũ không ghi đè blob mới, dùng đúng class docx-preview-content-wrapper/section.docx-preview-content và đo kích thước thật. Fit bằng scale, không reflow văn bản Word. Hiện lỗi render và phục hồi khi đổi blob.
2. Hộp phát hành bắt đầu đăng ký lại dù phiên bản đã duyệt. Truyền đúng version của run đang xem, đọc chi tiết version, tiếp tục bước draft/approved/published và chỉ báo sẵn sàng khi served_version trùng. Run sửa mới đăng ký version vào document cũ; khóa/body đăng ký ổn định. Khi mất phản hồi commit, chỉ thao tác chủ động của người dùng mới replay cùng preview/body/key; preview hết hạn/stale phải xác nhận lại và tạo khóa mới. Bỏ xác nhận review_skip âm thầm; người duyệt chọn tường minh, nhập lý do, hoặc đối chiếu từng finding theo review_ack. Gắn metadata hash, capability server. Sửa DTO summary/registration-version và điều kiện polling theo published_version thực của BE.
3. Không fallback sang derivations[0] khi run con vừa chỉnh sửa chưa có trong summary. Nhãn bản đang xem tách khỏi bản cũ đang phục vụ.
4. Citation không suy trang/khối từ mã evidence. Dùng canonical page/source_locator; Word logical document không hiện trang vật lý. Tệp nguồn chỉ gắn khi source/revision khớp, mã kỹ thuật thu trong phần đối chiếu.

UI: một toolbar Word, một badge trạng thái; tiêu đề trình bày bỏ underscore nhưng không ghi sửa dữ liệu; tránh lặp tiêu đề paper; giảm thứ bậc nhãn nhóm nguồn. Menu mobile dùng Sheet có nhãn truy cập được, giữ sidebar desktop và đóng menu sau điều hướng. Hành động theo capabilities/actions server.

## Tệp chính

- frontendV2/src/components/knowledge/{docx-viewer,citation-badge,publication-dialog}.tsx
- frontendV2/src/lib/knowledge-studio-helpers.ts và .test.ts
- frontendV2/src/routes/knowledge.$sourceId.tsx
- frontendV2/src/api/documents/{types,requests,queries}.ts; api/knowledge/types.ts
- frontendV2/src/layouts/{app-shell,app-sidebar,app-topbar,app-breadcrumb}.tsx
- frontendV2/tests/studio-browser.mjs

## Kiểm chứng thực chạy

Từ frontendV2:

- `node --test --experimental-strip-types src/lib/knowledge-studio-helpers.test.ts tests/studio-browser.mjs`: **PASS, 13 passed, 0 failed, 0 skipped**, exit 0. Gồm 4 helper + 9 ca Chromium với Vite cô lập và API giả lập: DOCX hai trang, scale không reflow, đổi blob, lỗi/khôi phục, duyệt/phát hành đúng version, idempotency khi mất phản hồi, explicit skip, giải trình findings, quyền, run mismatch, preview hết hạn và desktop/mobile.
- `npm run build`: **PASS**, Vite + tsc --noEmit, exit 0 (lượt cuối sau khi sửa kiểu committedStatus).
- Biome trên 15 tệp sửa: **PASS**, 0 lỗi/cảnh báo, exit 0.
- `git diff --check`: **PASS**, exit 0 sau ghi memory; các tệp kiểm UTF-8 không BOM/LF.
- Ảnh mock desktop1440x960/mobile390x844 tại tmp/studio-919/ đã mở xem. Mobile trước sửa bị sidebar chiếm 256px; sau sửa đọc được toàn chiều rộng và mở/đóng điều hướng đạt.

Các lỗi ở harness ban đầu (DOCX fixture thiếu relationship; locator không phân biệt article Word và article nội dung; hai nút đóng accessible) đã sửa fixture/selector đúng cấu trúc, không bỏ assertion. Kiểm 13 ca cuối không retry tự động để đạt kết quả.

## Giới hạn

Không chạy model thật, OCR/compiler, publish/reindex, migration, reset, restart hoặc push; không thay dữ liệu đang mở của người dùng. API giả lập chứng minh hành vi FE, không nghiệm thu lượt phát hành live. Full backend/full E2E live NOT RUN; giữ các lỗi nền backend/F13 từ phiên cũ. Browser harness dùng Playwright đã cài trong frontendV1, không cài dependency mới.
