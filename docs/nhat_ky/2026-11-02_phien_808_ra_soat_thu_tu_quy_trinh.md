# Phiên 808 — Rà soát thứ tự xử lý V1

## Phạm vi

Người dùng yêu cầu tìm các quy trình đang xử lý ngược. Chỉ review mã hiện tại, tái hiện cục bộ; không sửa ứng dụng, gọi model, thay DB, restart, reindex hay xuất bản. Giữ các thay đổi FE phiên 807 và backend chưa commit.

## Hai lỗi P2 đã tái hiện

1. **Lưu bản mới nhưng chuyển biên soạn vẫn dùng bản trước.** Trong `frontendV1/src/features/knowledge/source-detail-page.tsx`, `selectedVersion` quyết định query đọc văn bản. Khi chọn rõ v1 (đang là mới nhất), sửa và lưu thành v2, `handleConfirmSave` xóa nháp, thông báo thành công và refetch, nhưng không chuyển selection sang v2. Query vẫn đọc v1 và `CompilationDialog.initialRun.textVersion` vẫn là v1. Lỗi ở bước chuyển tiếp FE, chưa có bằng chứng compiler backend đọc sai snapshot đã được yêu cầu. Nên đồng bộ selection/cache với phiên bản server vừa trả trước khi cho phép biên soạn; giữ khả năng chủ động chọn lịch sử.
2. **Màn hình cha cập nhật làm đặt lại cấu hình biên soạn.** `compilation-dialog.tsx` có effect phụ thuộc object `initialRun`, xóa topic/model/output/review/key mỗi lần identity object đổi khi dialog mở. `SourceDetailPage` truyền object literal mới mỗi render. Tái hiện cùng run/version, nhập topic rồi rerender parent với object mới cùng giá trị: topic trở về rỗng. Nên chỉ khởi tạo khi mở phiên dialog hoặc khi danh tính nguồn thực sự đổi, không ghi đè form đang nhập.

## Các thứ tự đã đọc và chưa thấy đảo bước

- Upload lưu blob và commit hàng DB trước dispatch worker.
- Lưu sửa OCR kiểm version/hash, tạo MD/JSON dẫn xuất; compiler ghim text version cụ thể.
- Publication từ chối compiler chưa completed; quyết định duyệt/xuất bản kiểm preview, nguồn và hash. Bỏ AI review có biên nhận riêng, không tự bỏ approval.
- Index dựng vector/manifest rồi mới kích hoạt generation. Nhánh thay thế chuẩn bị index trước và đổi publication/source/index trong transaction chung; đây là chủ đích an toàn.
- Retrieval kiểm publication/scope trước TopK; rerank trước dựng evidence và generation. Không thấy nhánh trực tiếp lấy draft chưa xuất bản làm bằng chứng trong phạm vi đã đọc.

Hai quan sát chưa xếp là lỗi: `workflow/edits.py` chủ động bật auto-review khi nhận bản sửa compiler; RAG kiểm ngân sách chat đầy đủ sau khi có evidence, nên có thể đã tốn embedding/rerank trước khi phát hiện budget chat không đủ. Chưa thay chính sách các nhánh này.

## Kiểm chứng

Probe nằm trong `tmp/workflow-audit807/`, ngoài mã ứng dụng; có junction dependency tới `frontendV1/node_modules`. Không xóa thư mục/junction trong phiên này.

- `frontendV1/node_modules/.bin/vitest.cmd run --config tmp/workflow-audit807/vitest.config.mjs --reporter=verbose`, cwd root: exit 1. Probe lưu phiên bản FAIL đúng điều kiện mong đợi v2 nhưng nhận v1; probe dialog lúc đầu lỗi môi trường thiếu ResizeObserver.
- Bổ sung ResizeObserver giả trong probe, không sửa ứng dụng/expectation; chạy riêng `dialog.test.tsx` cùng config: exit 1, FAIL vì mong topic giữ nguyên nhưng nhận chuỗi rỗng. Đây là sửa môi trường test, không retry model hay làm xanh assertion.
- Kết quả: **2 lỗi tái hiện**, chưa sửa. Không báo PASS cho quy trình. Chưa chạy live E2E, full suite, build hoặc lint vì không thay mã ứng dụng.
- Probe SourceDetailPage dùng mock API/query có phân biệt phiên bản, mock Select và dialog đích để kiểm version bàn giao; chưa chứng minh thao tác DOM/browser thật hoặc compiler provider thật.

## Bước sau

Ưu tiên lỗi bàn giao phiên bản sau save, rồi lỗi reset dialog. Sau sửa cần regression hai tình huống và kiểm tra tuyến FE thực tế; không chạy lại OCR/compiler thật chỉ để xác nhận state FE.
