# Phiên831 — Kiểm tra chính tả toàn tài liệu

## Yêu cầu và phạm vi

User muốn nút Kiểm tra chính tả kiểm toàn tài liệu, báo lỗi nếu có. Sửa frontendV1;
giữ API, quyền ModelOps, bước đối chiếu/áp dụng nháp/lưu phiên bản. Không tự sửa
OCR gốc, đổi cấu hình model/quota, compiler, publish hay reindex.

## Thực hiện

- Main button trên SourceDetailPage và OcrTextReviewPanel mặc định chọn toàn bộ
  đơn vị có chữ. Vẫn có chọn trang/đoạn thủ công.
- `ocr-spelling-batch.ts`: chia theo trang, tối đa20unit/8.000ký tự, giữ unit dài
  nguyên vẹn; không cắt ở100unit. Gọi tuần tự API hiện hành, không retry. Mỗi nhóm
  có idempotency riêng, ghim cùng version/hash/source_version và lựa chọn provider.
  Không diễn giải heuristic ký tự là lượng token.
- `use-document-spelling.ts`: chặn gửi trùng; dừng sau nhóm hiện tại; không gửi
  nhóm mới/cài kết quả cũ khi đổi scope/session/unmount. Cảnh báo trước đóng tab.
- `document-spelling-report.tsx`: tiến độ thật, gợi ý, withheld, trang lỗi, nhóm
  chưa chạy; export JSON trạng thái/checkID/count, không text/key. Giữ kết quả
  thành công; lỗi quyền/quota/model/source hoặc uncertain dừng nhóm chưa gửi.
- Gợi ý dùng từng DetectionResponse thật; giữ validate span/version/hash và thao
  tác áp dụng vào nháp của SpellingResultPanel. Không tạo checkID tổng hợp giả.
- Thông báo model_not_configured dùng tên chức năng chung thay vì khẳng định OCR
  cho mọi trường hợp; báo cáo spelling nêu rõ cần Chat khi gặp mã này.
- Bổ sung quy trình27 về thao tác toàn tài liệu và giới hạn điều phối trình duyệt.

## Kiểm chứng đã chạy

Từ frontendV1, binary đã cài; không live inference:

1. Focused Vitest3file: lần đầu26PASS/2FAIL vì hai ca chọn trang cũ giả định main
   button luôn chọn trang1. Sửa thao tác test để chọn trang1 rõ ràng, giữ assertion
   riêng; thêm ca mainbutton toàn tài liệu và lỗi từng trang. Focused30PASS/exit0.
2. Thêm test scope/stop/duplicate/unmount/session; full `npm exec -- vitest run`:
   **723PASS/83file,0FAIL, exit0**,72,26s. Bao gồm planner>100unit, mất mạng, version
   mismatch, quota, uncertain, không retry, báo lỗi từng trang và không tự save.
3. `npm run build`: **PASS/exit0**, Vite+TypeScript; cảnh báo chunk>500KB vẫn có.
4. Biome11file sửa/thêm: **PASS/exit0**. Một lần --write gặp Windows mapped-file
   lock trên test806; chạy lại đúng file đạt rồi check toàn phạm vi đạt.
5. Playwright đọc app thật desktop1365/mobile390: trên tài liệu32trang, mặc định
   chọn **474đoạn/ô có chữ**, không overflow ngang dialog,0pageerrors, không gửi
   request model. Mở/đóng dialog, không click Bắt đầu; ảnh/report ở tmp/spelling831*.
6. `git diff --check`: PASS ở thời điểm kiểm; kiểm UTF-8/LF sau ghi memory.

Log: tmp/spelling831-full-fe.log, spelling831-build.log, spelling831-tests.log,
spelling831-browser.json và ảnh dialog. Đây là artifact local, không corpus Git.

## Giới hạn và bước sau

NOT RUN: live AI cohort toàn32trang, chất lượng gợi ý model thật, backendfull vì
không đổi server. Mock test chứng minh điều phối, không chứng minh model sửa đúng.
Giữ màn hình mở; điều phối không tự tiếp tục sau refresh/đóng tab. Check riêng
backend vẫn lưu, báo cáo aggregate thuộc phiên màn hình hiện tại và tải được JSON.
Không retry để làm xanh, không restart/push. Các thay đổi830 trước task được giữ.

Người dùng tải lại trang → Kiểm tra chính tả → Toàn bộ tài liệu → Bắt đầu. Xem
báo cáo lỗi và đối chiếu từng gợi ý trước áp dụng/lưu; kiểm xong không tự biên soạn.
