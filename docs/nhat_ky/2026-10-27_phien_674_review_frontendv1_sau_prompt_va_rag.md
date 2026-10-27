# Context674 — Review FE sau prompt672 và RAG673

User chọn review FE trước RAG mục5–6. Chỉ review; không sửa ứng dụng, cấu hình,
key, migration, DB hoặc nguồn/index phục vụ. Dùng skill frontend/clean-code/admin
design; đọc hướng dẫn, memory và file thật. FE/BEv1 đều untracked nên snapshot hash
trước review dùng làm bằng chứng độc lập thay cho Git diff nền không tồn tại.

## Kết luận

**CHANGES REQUESTED**,4nhóm lỗi và3phần tích hợp mới:

- F1/P1: runAutoLogin nhận phản hồi muộn vẫn cài token, ghi đè phiên SSO mới,
  đăng xuất hoặc sau unmount.3probe trên provider/store thật tái hiện.
- F2/P2: đổi tab rà soát OCR → ảnh đối chiếu → trở lại làm mất draft do panel
  unmount.1probe với OcrTabContainer/Radix thật tái hiện mất văn bản vừa sửa.
- F3/P2: transport nuốt mọi404 (hoặc code not_found sai status), trang detail
  không hiện publishedQuery.isError nên503 cũng thành “chưa xuất bản”.4probe.
- F4/P2: BE trả turn cancelled khi dừng/lưu trữ; FE không có nhánh terminal
  tương ứng nên phần trả lời trống.1probe render shape cancelled tái hiện.
- G1: chưa UI rag_policy/metadata scope/index/search; BE giữ policy nếu PUT FE
  thiếu trường mới, không báo nhầm bug resetpolicy.
- G2: chưa UI đăng ký/xem/duyệt retrieval_metadata và hash acknowledgement;
  phiên bản có metadata từ API bị chặn duyệt đúng ở BE673 khi FE không gửi hash.
- G3: observe/unsupported không hiện cảnh báo/report;1probe. Enforce vẫn được BE
  chặn đáp án, nhưng FE chưa hiển thị reason/phạm vi/context/usage mới đầy đủ.

G1–G3 là khoảng trống cần nối sau BE673, không coi là tính năng prompt672 đã hứa
nhưng chưa làm. Ưu tiên sửa F1–F4, nối G1–G3, smoke đúng môi trường/dữ liệu được
phép rồi mới mục5–6. [Báo cáo và vị trí](../bao_cao/context674/REVIEW.md),
[verification/test IDs/hashes](../bao_cao/context674/verification.json).

## Kiểm chứng thực chạy

Cwd frontendV1, npm/dependency đã có, không cài thêm:

| Lệnh | Kết quả |
|---|---|
| npm test -- --reporter=json --outputFile=.../tests.json | PASS156/0FAIL/0SKIP,exit0 |
| npm run lint -- --reporter=json | PASS472tệp,0error/0warning/0info,exit0 |
| npm run build (Vite + tsc --noEmit) | PASS,exit0; chunk>500kB vẫn cảnh báo |
| npm test -- tests/dev-auto-login-bundle-672.test.ts --reporter=json ... | PASS6/0FAIL/0SKIP sau build,exit0 |
| npm exec -- vitest run --config storage/artifacts/context674-review/vitest.review.config.ts ... | FAIL10/PASS1control/0SKIP,exit1: chứng minh lỗi, không sửa assertion để xanh |
| So hash755file src/dev/tests/config FE và qnu BE trước/sau | PASS0file đổi/mất |

Probe dùng ports HTTP/query mô phỏng, component/helper/client thật và jsdom.
Không kết luận tương đương browser/liveSSO/API/model thật. Cổng3001/8002 chưa có
listener đầu phiên; không khởi động/restart dịch vụ phục vụ. Full upload→chat,
desktop/mobile/dark browser và SSO/key thật NOT RUN. BE652PASS Context673 là lịch
sử, không chạy lại backend cho review FE thuần. Không thay luồng nghiệp vụ nên
không cập nhật quy trình; chỉ tạo báo cáo/nhật ký/snapshot/index.

Artifact ignored: storage/artifacts/context674-fe-review và
frontendV1/storage/artifacts/context674-review. Probe OCR đầu chọn sai nhãn tab;
đã sửa fixture và chạy tới assertion mất draft, không còn fixture error ở lượt
cuối. Source src/dev/tests/config ứng dụng giữ nguyên, chỉ tạo probe ở storage.
