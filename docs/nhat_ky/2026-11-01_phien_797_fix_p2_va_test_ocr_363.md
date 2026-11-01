# Phiên 797 — Sửa ba P2 và thử PDF scan Quy chế 363

## Phạm vi được giao

- Sửa ba P2 từ review796; giữ các thay đổi người dùng795.
- Bổ sung kiểm thử OCR PDF `Quy chế tuyển sinh đại học 2026 - 363.pdf` và sửa lỗi OCR liên quan.
- Người dùng xác nhận alias `nemotron-parse` đang phục vụ Nemotron-3.5-Parse; chưa kiểm độc lập revision weights.
- Người dùng cho phép AI tự áp dụng và lưu sửa chính tả trong lượt thử này, rồi tiếp tục; không đổi quy trình UI hoặc tự bật chế độ sửa tự động lâu dài.

Không cleanup/init, không thay bộ 53 câu, publication hoặc index đang dùng. Nguồn thử nằm trong collection riêng của phiên `93faa11f0caf`. Các lượt lỗi và raw phản hồi được giữ.

## Thay đổi

1. ModelOps FE: xóa pending clear patch sau lỗi, đóng/mở lại và đổi provider; không gửi tên nháp cũ. Dòng OCR upper bound đọc provenance từ trường cha `ocr_page_input`.
2. Regression795 sửa về hợp đồng BE thật, thêm ca lỗi/lifecycle/provenance. Thêm `test:modelops:typecheck` để kiểm kiểu fixture này, thay vì chỉ dựa Vitest transpile.
3. Chặng riêng `admissions-scan-ocr`, hash nguồn, 32 trang scan, nhãn chữ tại 7 trang và bảng trang31–32; raw/canonical/manifest/Markdown được lưu, không tự retry. Có lựa chọn rõ ràng `--ocr-dpi`, lưu thế hệ thử riêng.
4. OCR parser `nemotron-tabular/v2` đọc wrapper `mbox/text/textrm`, giữ ô rỗng. Khai báo cột sai chỉ đối soát khi nhiều hàng không span có cùng số ô tường minh; cảnh báo `column_spec_reconciled`, giữ raw. Không bỏ ô rỗng thừa khi không có vertical merge. Run v1 vẫn ghim parser v1 ở cả parse và assemble.
5. API nhận tùy chọn `render_dpi`72–300; config/fingerprint, generation, quyền và ngân sách vẫn do server kiểm. Default144 không đổi; thử176 trong biên ảnh đã khai báo1664×2048.
6. Chính tả: ModelOps thêm tác vụ `ocr_review` trong cơ chế reasoning khai báo sẵn; không tự nhận tham số theo tên model. `qnu.ocr.spelling/v3` gửi JSON Schema, enum evidence ID, căn vị trí theo literal anchor; giữ chặn mơ hồ/overlap/khác số/ngoài scope. Raw vẫn lưu trước validation; đề xuất chưa ghi văn bản.
7. Executor thử cục bộ chỉ dùng các API kiểm tra/lưu sẵn có. Gợi ý hợp lệ được lưu theo version/hash và khóa duy nhất. Phản hồi lỗi được giữ; tận dụng raw xác định được vị trí, không gọi lại model để lấy PASS. JSON rỗng trang27 không coi là không có lỗi; giữ nguyên và ghi unresolved.

## Kết quả đo

Nguồn: 32 trang, 17.505.065 byte, không trang nào có native text.
SHA256 `59444d277a5e904808537ce70544c1fc83c0bf0a2f2653b78af362af59d5cccc`.

| Lượt | Kỹ thuật | Chữ mẫu | Bảng đúng số cột |
|---|---|---|---|
|144 DPI, parser v1|32/32 hoàn tất,85,876s|10/16|0/2|
|176 DPI, parser v2|32/32 hoàn tất,108,470s|14/16|1/2|
|Sau lưu chính tả version27|Raw/hash/evidence/hình học/số giữ nguyên|15/16|1/2|

Đây là mẫu đối chiếu ảnh, không phải CER/WER hoặc độ chính xác toàn tài liệu. Bảng trang32 model sinh10cột, ảnh có8; giữ cảnh báo, không tự xóa ô. Tiêu đề `PHỤ LỰC IV` chưa được AI sửa đúng. Không nghiệm thu chất lượng toàn PDF là PASS.

Ban đầu checker bảng dùng điều kiện tối thiểu8cột nên lọt bảng10cột. Đã sửa so sánh chính xác theo ảnh và thêm negative test; tính lại báo cáo offline từ cùng canonical, không chạy lại inference để đổi kết quả.

Lượt chính tả đầu dùng server-default reasoning, hết16384 output (`chat_output_truncated`). Sau tắt reasoning cho task, model trả JSON nhưng đếm sai offset Unicode (`ocr_spelling_invalid`); sửa literal anchoring. Giữ hai lượt lỗi, dùng raw lượt thứ hai cho trang1. Các trang chưa chạy được xử lý một lần. Trang27 trả `{}` trước khi bổ sung Schema; giữ lỗi, không gửi lại.

Đã áp dụng170 gợi ý vào115 đoạn/ô, lưu27 phiên bản;40 đề xuất bị loại, trang27 chưa có kết luận. Đối chiếu toàn bộ canonical trước/sau: mọi chuỗi số, geometry, cell/span, identity và evidence mapping giữ nguyên; thêm metadata `text_review`. Bản gốc trong storage không đổi.

Compiler hoàn tất8/8phần,259,219s,attempt1 từng phần, chạy song song2.
Ghim bản sửa version27/hash `35a43a367df4c037b03c98802228379c6024583f9981ca8bf328251602db1091`;
run `cmp_51223c447c59`. Kết quả31mục/124đoạn/644citation/20unknowns;
schema và citation membership PASS, unread blocks retained; semantic faithfulness
`not_evaluated`. Kiểm mọi citation thuộc OCR run đã chọn, lưu JSON/Markdown thật từ API.

## Kiểm chứng mã

- Frontend: full Vitest663PASS/0FAIL,73 suites; build gồm TypeScriptPASS; typecheck E2E và fixture ModelOpsPASS; Biome11filesPASS,3files checker cuốiPASS.
- Backend: full Pytest676PASS/**1FAIL**/75SKIP. Exact lỗi nền: `test_source_purge_716.py::test_accept_rechecks_publication_after_preview_before_preparing_purge` (actor fixture401, kỳ vọng409), không sửa trong phạm vi này.
- API HTTP/PostgreSQL riêng:42PASS sau sửa anchoring;28PASS cuối cho OCR density/text-review/JSONSchema. DB test duy nhất mỗi lượt được drop, remaining0. Mock chỉ chứng minh contract, không chứng minh chất lượng model.
- Unit reasoning17PASS; anchor + reasoning28PASS; OCR layout/config30PASS; script runner18PASS; Ruff scopedPASS; diff whitespacePASS.
- Các lượt giữa chừng từng lỗi import `_table_grid` khi sửa parser; đã khôi phục helper validator và kiểm lại full suite/API. Các log lỗi giữ trong tmp, không coi lượt lỗi là PASS.

Lệnh/log tại `tmp/ocr797/`, `tmp/ocr797-api.log`, `tmp/ocr797-schema-api.log`. Chặng OCR thật có hai report trong `tmp/v1-e2e/93faa11f0caf/runs/`: `admissions-scan-ocr-1793536268729836600` và `admissions-scan-ocr-1793537721917978800`. So sánh cùng raw ở `comparison.json`; sửa chính tả/assessment/integrity/receipt/compiler ở `tmp/ocr797/correction-anchored/`.

## Bàn giao

Nguồn riêng đã OCR, sửa/lưu chính tả và compiler xong; chưa xuất bản/index/RAG nguồn
này, chưa duyệt nội dung. Còn chất lượng tiêu đề/bảng và các gợi ý unresolved như
trên, không tuyên bố toàn bộ PDF đạt hoặc compiler đúng ngữ nghĩa hoàn toàn.

Đã khôi phục chính sách reasoning ban đầu qua ModelOps API, GET đối chiếu bằng policy
trước thử; `ocr_review` không bị bật tắt tự động lâu dài. Giữ các task compiler/answer
trước đó. Serve thử hiện tại parentPID29560, API64624/FE64625, backend source hash
`b6c0175e197d82d012ad2dfadd3039b4f36d86d6bd3e8884ac1c37ae3341550a`.
Giữ phiên93faa11f0caf, corpus/index53câu và uncertain789. Không commit/push/deploy.
Hướng dẫn chạy: [OCR Quy chế363](../quy_trinh/V1_TEST_OCR_QUY_CHE_363.md).
