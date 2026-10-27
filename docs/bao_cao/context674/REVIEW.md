# Context674 — Review frontendV1 sau prompt672 và RAG673

Ngày 2026-10-27. Kết luận: **CHANGES REQUESTED**. User yêu cầu review FE trước
khi triển khai RAG mục5–6. Chỉ review, không sửa ứng dụng hoặc cấu hình đang chạy.

## Các lỗi cần sửa

### F1 — P1: phản hồi tự đăng nhập muộn ghi đè phiên mới hoặc phiên đã đăng xuất

Vị trí: [provider.tsx:116](../../../frontendV1/src/app/auth/v1/provider.tsx#L116).
runAutoLogin cài token ngay khi promise hoàn tất, không kiểm lại session hiện tại,
trạng thái logout, attempt generation hoặc provider còn mounted hay không.

Đã tái hiện bằng chính V1AuthProvider và token store, trì hoãn fetch của bridge:

- Trong lúc chờ bridge, cài phiên mô phỏng callback SSO thành công. Phản hồi dev
  đến muộn thay phiên đó bằng token dev. AppProviders bọc cả route signin-oidc nên
  đây là đường có thể xảy ra ở local khi vừa mở callback, không chỉ khi bấm login tay.
- Gọi signOut khi bridge đang chờ, rồi cho bridge hoàn tất: token lại xuất hiện,
  dù suppression đã bật. Kiểm tra trước khi bắt đầu request không chặn phản hồi cũ.
- Unmount provider trước khi bridge hoàn tất: token cũ vẫn được ghi vào store global.

Ba probe đều FAIL đúng assertion về token. Không gọi SSO thật hoặc dùng credential
thật trong probe. Tác động chỉ thuộc chế độ dev có bridge đang chờ; chưa có bằng
chứng bypass production. Cần dùng attempt/session generation và hủy/bỏ kết quả
muộn khi logout, có phiên khác, unmount hoặc chuyển luồng auth; vẫn giữ /auth/me.

### F2 — P2: mất bản nháp hậu OCR khi mở tab đối chiếu ảnh

Vị trí: [ocr-tab-container.tsx:282](../../../frontendV1/src/features/knowledge/ocr-tab-container.tsx#L282),
handleSubTabChange tại dòng134; draft nằm trong OcrTextReviewPanel dòng86.

Tái hiện với OcrTabContainer và Radix Tabs thật: Chỉnh sửa → Áp dụng vào nháp →
Đối chiếu ảnh & Văn bản → Rà soát & Sửa bản dẫn xuất. Đoạn vừa sửa biến mất, quay
về OCR gốc. TabsContent unmount panel; state nháp chỉ thuộc panel và không có chặn
đổi tab/xác nhận hủy nháp. Điều này cản trở chính luồng người dùng sửa chữ rồi xem
ảnh để đối chiếu trước khi lưu. Probe DOM FAIL sau khi trở lại tab.

Cần lưu draft ở lớp sống xuyên tab hoặc giữ panel mounted đúng scope, kèm xác nhận
khi rời nguồn/run/revision/session. Không chỉ forceMount toàn bộ mà bỏ khóa phạm vi.

### F3 — P2: lỗi tải publication bị biến thành trạng thái “chưa xuất bản”

Vị trí transport: [publication-requests.ts:243](../../../frontendV1/src/features/knowledge/publication-requests.ts#L243).
Điều kiện `status===404 || code===published_compilation_not_found` trả null cho
mọi404, gồm tài liệu không tồn tại hoặc resource_unavailable, và cả503 mang mã
not_found. Ba probe bằng V1Client thật + Response tổng hợp đều FAIL vì promise
resolve null thay vì báo lỗi. Control đúng404/published_compilation_not_found PASS.

Vị trí UI: [compiled-document-detail-page.tsx:225](../../../frontendV1/src/features/knowledge/compiled-document-detail-page.tsx#L225).
Trang chỉ phân nhánh loading/data; không có nhánh publishedQuery.isError. Ngay cả
503/storage_unavailable mà transport giữ đúng cũng hiện “Tài liệu chưa có phiên
bản nào đang xuất bản”. Probe DOM dùng hook trả503 tái hiện đúng thông báo sai.

Cần chỉ coi đúng404+mã thiếu publication là rỗng; lỗi khác phải giữ và UI cần lỗi/
thử lại, không khuyên người vận hành xuất bản lại trong khi chưa đọc được trạng thái.

### F4 — P2: lượt chat đã bị hủy có phần trả lời trống

Vị trí: [chat-message-item.tsx:29](../../../frontendV1/src/features/conversations/chat-message-item.tsx#L29),
TurnStatus trong types.ts chỉ có running/completed/failed/uncertain.

BE lifecycle trả status=cancelled, error_code=operation_cancelled khi dừng trợ lý
hoặc lưu trữ hội thoại trong lúc trả lời. FE không có nhánh cancelled, nên chỉ hiện
tiêu đề “Trợ lý AI”, không có nội dung hay thông báo. Polling dừng khi status khác
running, nên cũng không tự trở lại spinner. Probe render đúng shape này FAIL vì
không có thông báo hủy. Cần kiểu và UI terminal state tương ứng, không gợi ý resend
cùng key như một lỗi mới (BE bảo toàn idempotency của lượt đã hủy).

## Khoảng trống tích hợp với RAG mới

Đây là phần chưa được làm sau Context673, tách khỏi lỗi của prompt672:

| ID | Khoảng trống | Tác động và chỗ cần nối |
|---|---|---|
| G1 | Form trợ lý/API client chưa có rag_policy; chưa có điều khiển index/search | Không chọn hybrid/rerank, scope, window/judge từ FE; chưa hoàn tất luồng xuất bản → index → chat trên UI. Assistant types/form và endpoint FE chưa có các trường/đường này. **BE giữ policy cũ khi PUT thiếu rag_policy**, không kết luận FE đang làm mất policy |
| G2 | Version/registration/review gate chưa có retrieval_metadata và hash acknowledgement | Phiên bản có metadata được đăng ký qua API không hiện metadata để người duyệt xem, payload review_ack không gửi retrieval_metadata_sha256, BE673 trả409 publication_metadata_review_required. Phiên bản không metadata vẫn theo contract cũ |
| G3 | Chat chưa hiển thị trace.verification/context/scope và reason kiểm chứng mới | Observe/unsupported vẫn hiển thị câu trả lời như bình thường, không có cảnh báo hay báo cáo cho người đọc. Enforce không phát hành answer được BE giữ đúng, nhưng FE chỉ có thông báo thiếu căn cứ chung. Probe observe/unsupported FAIL vì không có cảnh báo. Cần nối trước khi bật observe/enforce cho người dùng; không bỏ guard ở BE |

Không tìm thấy các trường rag_policy/retrieval_mode/metadata_filter/verification
trong feature FE tương ứng ở thời điểm review. Không coi việc TypeScript hiện đạt
là chứng minh contract mới đã được nối: client trả generic type, extra JSON vẫn tồn tại
nhưng component không đọc/hiển thị. Không khẳng định đã thử G1/G2 qua API serving thật.

## Kiểm chứng thực chạy

| Kiểm tra | Kết quả |
|---|---|
| npm test, suite ứng dụng hiện có | PASS156/0FAIL/0SKIP, exit0 |
| npm run lint -- --reporter=json | PASS472tệp,0error/0warning/0info, exit0 |
| npm run build (Vite và tsc --noEmit) | PASS, exit0; còn cảnh báo chunk>500kB |
| Probe review độc lập | FAIL10, PASS1 control,0skip; xác nhận F1–F4 và G3 |
| So755hash trước/sau gồm FE source/dev/tests/config và BE qnu | PASS,0file bị đổi/mất |
| Markdown/JSON, local links, UTF-8 không BOM/LF | Theo [verification.json](verification.json) |
| Browser desktop/mobile/dark, key thật/SSO thật, API serving/model thật, full upload→chat | NOT RUN |

Probe dùng component/helper/transport thật với ports được mô phỏng và DOM jsdom.
Không gọi provider AI, không sửa key, cấu hình, DB, migration hay nguồn/index đang
phục vụ; cổng3001/8002 không có listener khi kiểm tra đầu phiên. Không coi jsdom là
nghiệm thu giao diện trình duyệt hay SSO/network thật. BE652PASS của Context673 là
bằng chứng lịch sử, không chạy lại backend cho task review FE này.

Artifact ở `storage/artifacts/context674-fe-review` và
`frontendV1/storage/artifacts/context674-review` (Git ignored), gồm JSON kết quả,
snapshot hash và probe tests/config riêng. Bộ156test không bị sửa để tạo failure.
Một lần dựng probe OCR chọn sai tên tab; đã sửa đúng nhãn rồi tái hiện tới assertion
mất draft. Kết quả cuối không có lỗi fixture chưa xử lý.

## Thứ tự xử lý đề xuất

Sửa F1 trước, sau đó F2–F4. Giữ các sửa Context671/672 và kiểm tra không hồi quy.
Nối G1–G3 bằng contract BE673, rồi chạy smoke có môi trường/dữ liệu được phép.
Chưa ưu tiên query decomposition hoặc engine truy vấn bảng/tính toán mục5–6.
