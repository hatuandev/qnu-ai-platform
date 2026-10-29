# AnythingLLM — Những phần nên học và áp dụng vào QNU V1

Ngày nghiên cứu: 2026-10-29. Phạm vi đối chiếu: `backendV1/` và `frontendV1/`.
AnythingLLM được ghim tại commit `0941fb03596862899f7df2bdeb022eb68d4216a7`, commit timestamp `2026-10-27T23:04:07Z`.
Đây là đánh giá thiết kế từ mã nguồn, không phải benchmark hoặc xác nhận chất lượng runtime.

## Kết luận

Giá trị gần nhất với QNU là cách tổ chức công việc: workspace rõ ràng, giao diện theo
quyền, quản lý tệp thuận tiện, nguồn dẫn đọc được và thiết lập có hướng dẫn. QNU đã có
nhiều nền tảng tương ứng. Nên cải thiện luồng hiện có trước khi bổ sung agent/MCP hoặc
một bộ định tuyến model thứ hai.

Ba ưu tiên: (1) điều hướng theo vai trò, (2) thư mục và xử lý tài liệu theo lô,
(3) hướng dẫn thiết lập phòng ban đến lần hỏi đáp đầu. Tiếp theo cải thiện citation
và phản hồi tiến trình. Connector, chatbot nhúng và agent là các nhánh mở rộng riêng.

## Phương pháp và giới hạn bằng chứng

- Đọc README chính thức; lấy GitHub commit + cây thư mục đệ quy, tree không bị cắt.
- Lưu36tệp nguồn chọn lọc cùng URL/hash vào artifact local bị Git bỏ qua; một đường dẫn
  embed dự đoán ban đầu404, đã tìm và đọc đúng `server/endpoints/embed/index.js`.
- Rà các phần liên quan đến navigation/RBAC, picker/upload, citation/chat, onboarding,
  model routing, đồng bộ nguồn, embed và tool approval. Không đọc toàn bộ repository.
- Đối chiếu source QNU thực tế, không dựa riêng vào memory/README. Ví dụ README hội
  thoại QNU còn ghi chưa có FE nhưng `chat-view.tsx`/`citation-sheet.tsx` đã tồn tại.
- QNU đang có thay đổi frontend chưa commit và tiếp tục có sửa đồng thời. Đây là ảnh
  chụp mã trong phiên, không phải đánh giá của một bản phát hành đã khóa. Không sửa
  các tệp ứng dụng hoặc dùng trạng thái test cũ để kết luận bản hiện tại đạt.
- Không cài/chạy AnythingLLM, không chạy build/test/benchmark QNU, không đọc DB/config
  bí mật, không gọi model hoặc gửi tài liệu QNU sang dịch vụ ngoài.

## 1. Sidebar theo vai trò và phân biệt quản trị hệ thống/phòng ban — ưu tiên cao

**AnythingLLM:** sidebar cấu hình có vai trò được phép cho từng mục; danh sách workspace
đi cùng thread và hành động vào cài đặt/tài liệu. Middleware server vẫn kiểm tra truy cập.
Nguồn: [SettingsSidebar](https://github.com/Mintplex-Labs/anything-llm/blob/0941fb03596862899f7df2bdeb022eb68d4216a7/frontend/src/components/SettingsSidebar/index.jsx#L216),
[ActiveWorkspaces](https://github.com/Mintplex-Labs/anything-llm/blob/0941fb03596862899f7df2bdeb022eb68d4216a7/frontend/src/components/Sidebar/ActiveWorkspaces/index.jsx#L135),
[validWorkspace](https://github.com/Mintplex-Labs/anything-llm/blob/0941fb03596862899f7df2bdeb022eb68d4216a7/server/utils/middleware/validWorkspace.js).

**QNU:** `frontendV1/src/layouts/workspace-sidebar.tsx` duyệt toàn bộ nhóm chức năng sau
khi xác thực; chưa lọc từng mục theo vai trò membership. `workspace-features.ts` đã là
catalog dùng chung; nên bổ sung khả năng hiển thị vào nguồn này, không tạo sidebar
riêng lặp lại cho từng người. Cần lấy capability đáng tin cậy từ server; khi membership
đổi/thu hồi phải làm mới khả năng thao tác. Ẩn menu chỉ hỗ trợ UX, không cấp quyền.

**Cách áp dụng:** user vào Trợ lý/Hội thoại/tra cứu; editor có thêm luồng tài liệu;
reviewer có nghiệp vụ duyệt; workspace admin có thành viên/cấu hình phòng/vận hành;
platform/model admin có khu cấu hình toàn cục. Mục chỉ được xem thì phân biệt với quyền sửa.

**Tiêu chí nghiệm thu:** kiểm từng vai trò + đăng xuất/đổi workspace/thu hồi membership;
menu đúng phạm vi, URL nhập trực tiếp vẫn bị server chặn. Quyền owner hội thoại vẫn giữ.

## 2. Quản lý thư mục, lựa chọn nhiều trang và hàng đợi upload — ưu tiên cao

**AnythingLLM:** picker nạp khung thư mục trước, lấy từng trang khi mở; giữ lựa chọn
trong trạng thái chung. Chọn cả thư mục có cơ chế chọn tất cả trừ những tệp bỏ chọn,
bao gồm tệp chưa tải lên màn hình. Upload có cấu trúc thư mục và trạng thái tệp bị từ chối.
Nguồn: [useDocumentPicker](https://github.com/Mintplex-Labs/anything-llm/blob/0941fb03596862899f7df2bdeb022eb68d4216a7/frontend/src/components/Modals/ManageWorkspace/Documents/hooks/useDocumentPicker.js#L6),
[useUploadQueue](https://github.com/Mintplex-Labs/anything-llm/blob/0941fb03596862899f7df2bdeb022eb68d4216a7/frontend/src/components/Modals/ManageWorkspace/Documents/hooks/useUploadQueue.js).

**QNU:** đã có kho, thư mục, upload và idempotency. Source upload dialog hiện xử lý một
`File`; thay đổi kho/thư mục đang tiếp diễn. Context703 ghi các lỗi cần sửa nhưng phiên
này không chạy lại để xác nhận chúng còn tái hiện. Không coi thêm tính năng là cách né
các lỗi identity/lifecycle/URL của luồng hiện tại.

**Cách áp dụng:** dùng một hàng đợi nhiều tệp, mỗi tệp có đích workspace/kho/thư mục,
khóa idempotency và trạng thái riêng. Tách rõ đã nhận tệp, OCR, biên soạn, xuất bản,
đánh chỉ mục; upload xong không đồng nghĩa đã dùng được cho hỏi đáp. Chỉ retry tệp lỗi.
Chọn cả thư mục cần preview danh sách/snapshot do server giải quyết, tránh âm thầm xử lý
100tệp đầu hoặc tải không giới hạn bằng một request `all`.

**Tiêu chí nghiệm thu:** hơn một trang tệp, lỗi một phần, đổi kho lúc upload, retry không
trùng, folder bị di chuyển/thu hồi và đường dẫn bất hợp lệ. Hiển thị tiến trình từ kết
quả thật, giữ hash và nguồn gốc tài liệu.

## 3. Hướng dẫn thiết lập và trạng thái sẵn sàng — ưu tiên cao

**AnythingLLM:** onboarding tách bước lựa chọn LLM, người dùng và cách xử lý dữ liệu.
Nguồn: [OnboardingSteps](https://github.com/Mintplex-Labs/anything-llm/blob/0941fb03596862899f7df2bdeb022eb68d4216a7/frontend/src/pages/OnboardingFlow/Steps/index.jsx#L11).

**QNU:** có API workspace/member, cấp provider/model, hạn mức, kho và trợ lý; các thao tác
phân bố ở nhiều trang. Nên nối chúng thành checklist theo vai trò, dùng API hiện có.
Chưa kết luận QNU không có bất kỳ hướng dẫn nào chỉ từ tên tệp; đề xuất ở đây là luồng
thiết lập hoàn chỉnh cho phòng ban.

**Cách áp dụng:** tạo/chọn phòng → thêm thành viên → admin nền tảng cấp model/hạn mức →
phòng tạo kho → upload/OCR/duyệt/xuất bản/index → tạo trợ lý → câu hỏi kiểm tra có nguồn.
Bước không đủ quyền hiện người phụ trách và lý do, không cho admin phòng nhập secret
provider để vượt cấp quyền. Mỗi trạng thái phải suy từ dữ liệu thật.

**Tiêu chí nghiệm thu:** phòng mới không có model hoặc kho vẫn hiểu việc cần làm; reload
không mất tiến độ; không tự gửi prompt/gọi model có chi phí khi chỉ mở checklist.

## 4. Đọc nguồn cạnh câu trả lời — ưu tiên kế tiếp

**AnythingLLM:** có SourcesSidebar desktop và modal mobile, mở từng nguồn và tập hợp
các chunk thành nhóm tài liệu. Nguồn: [SourcesSidebar](https://github.com/Mintplex-Labs/anything-llm/blob/0941fb03596862899f7df2bdeb022eb68d4216a7/frontend/src/components/WorkspaceChat/ChatContainer/SourcesSidebar/index.jsx),
[combineLikeSources](https://github.com/Mintplex-Labs/anything-llm/blob/0941fb03596862899f7df2bdeb022eb68d4216a7/frontend/src/components/WorkspaceChat/ChatContainer/ChatHistory/Citation/index.jsx#L111).

**QNU:** đã có `conversations/citation-sheet.tsx`, lọc evidence theo mệnh đề, cùng
`knowledge/citation-drawer.tsx`. Nên phát triển tiếp thành trả lời → mệnh đề → đoạn
nguồn → trang/bảng/ô/phiên bản, mở đúng tài liệu gốc và phần OCR liên quan. Hai bề mặt
có thể dùng chung cách trình bày mà vẫn giữ contract riêng.

**Điều chỉnh bắt buộc:** AnythingLLM ở hàm được đọc nhóm bằng `title`. Với QNU phải nhóm
bằng document/source revision + version/hash + phạm vi hợp lệ; cùng tên tài liệu không
chứng minh cùng nguồn. Điểm similarity không phải xác suất câu trả lời đúng. Nguồn đã
thu hồi phải được kiểm lại khi người dùng mở dẫn chứng.

## 5. Tiến trình hội thoại, streaming và dừng — cần thiết kế server

**AnythingLLM:** stream handler có đường streaming/non-streaming, lỗi truy xuất tách
khỏi thiếu bằng chứng, và nối tín hiệu ngắt kết nối tới connector.
Nguồn: [stream handler](https://github.com/Mintplex-Labs/anything-llm/blob/0941fb03596862899f7df2bdeb022eb68d4216a7/server/utils/chats/stream.js#L93).

**QNU:** `/conversations/.../turns` trả `TurnResponse`; FE đang dùng mutation/polling.
`rag/answer/service.py` parse câu trả lời, kiểm nguồn/cấu hình lại sau inference và có
bước verification. Có thể học event protocol, nhưng không chỉ thêm hiệu ứng gõ chữ.

**Cách áp dụng:** truyền các trạng thái xác thực/đang truy xuất/đang sinh/đang kiểm chứng
và final/error có ID lượt; chỉ công bố câu trả lời chính thức sau gate. Dừng phải đi
qua server, hủy call khi khả thi và đối soát usage; cancel ở browser không chứng minh
provider đã dừng. Mất mạng/kết nối lại không tạo thêm lượt hoặc tính phí hai lần.

## 6. Connector và phát hiện tài liệu thay đổi — mở rộng có giá trị

**AnythingLLM:** danh mục connector và `documentSyncQueue` có lịch kiểm lại cho website,
GitHub/GitLab/Gitea, Confluence... Nguồn: [documentSyncQueue](https://github.com/Mintplex-Labs/anything-llm/blob/0941fb03596862899f7df2bdeb022eb68d4216a7/server/models/documentSyncQueue.js#L65).

**QNU:** bổ sung connector vào đường ingestion/version hiện có. Chọn một nguồn công
khai do trường quản lý để làm thử sẽ có ích hơn tích hợp hàng loạt ngay. Khi nguồn đổi:
lấy bản mới → hash/revision mới → review → quyết định xuất bản; giữ bản đang phục vụ
đến khi bản thay thế hợp lệ. Không tự cập nhật nội dung đang truy xuất chỉ vì lịch sync.

**Tiêu chí nghiệm thu:** nguồn không đổi thì không tạo revision thừa; timeout không
bị báo là tài liệu rỗng; có nguồn URL, thời điểm lấy, hash, audit và quyền egress/credential.

## 7. Model routing có giải thích — ưu tiên sau, tận dụng ModelOps

**AnythingLLM:** router có thứ tự rule, fallback và cơ chế giữ model cho user/workspace/
thread trong một khoảng thời gian. Nguồn: [modelRouter](https://github.com/Mintplex-Labs/anything-llm/blob/0941fb03596862899f7df2bdeb022eb68d4216a7/server/models/modelRouter.js#L91),
[router service](https://github.com/Mintplex-Labs/anything-llm/blob/0941fb03596862899f7df2bdeb022eb68d4216a7/server/utils/router/index.js#L112).

**QNU:** đã có model grants, runtime resolution, quotas, fallback/key pool và routing
trace. Không cần dựng hệ thống provider/router mới. Có thể học màn giải thích vì sao
chọn model, dry-run policy và cấu hình tuyến theo tác vụ/capability, trước khi thử
phân loại ý định bằng một LLM khác.

Cache quyết định phải gắn revision chính sách và quyền hiện hành, không chỉ TTL.
Không đổi embedding của index đã ghim; không âm thầm thay model đã chọn hoặc né hạn mức.
Hiệu quả chi phí/latency phải đo trên cùng workload, chưa có số liệu trong phiên này.

## 8. Chatbot nhúng vào website của phòng — giai đoạn sau

**AnythingLLM:** endpoint embed và middleware riêng kiểm trạng thái bật/tắt, origin,
phiên và giới hạn sử dụng. Nguồn: [embed middleware](https://github.com/Mintplex-Labs/anything-llm/blob/0941fb03596862899f7df2bdeb022eb68d4216a7/server/utils/middleware/embedMiddleware.js#L31).

**QNU:** API ứng dụng đã có scope trợ lý rõ ràng, key lifecycle và rate limit trong
`integration/access.py`/`schemas.py`. Có thể xây widget trên contract này, nhưng secret
ứng dụng không được nhúng trong JavaScript công khai; cần gateway hoặc phiên công
khai giới hạn riêng, chỉ truy vấn nội dung được phép công bố. Origin chỉ hỗ trợ kiểm
soát truy cập trình duyệt, không thay thế xác thực/cấp quyền.

## 9. Tool approval/MCP — tham khảo dài hạn

**AnythingLLM:** có flow executor, endpoint MCP và thẻ yêu cầu phê duyệt tool kèm payload,
timeout. Nguồn: [ToolApprovalRequest](https://github.com/Mintplex-Labs/anything-llm/blob/0941fb03596862899f7df2bdeb022eb68d4216a7/frontend/src/components/WorkspaceChat/ChatContainer/ChatHistory/ToolApprovalRequest/index.jsx#L7),
[flow executor](https://github.com/Mintplex-Labs/anything-llm/blob/0941fb03596862899f7df2bdeb022eb68d4216a7/server/utils/agentFlows/executor.js).

**QNU:** `domains/tools` và `domains/workflows` hiện là khung ngoài MVP. Bắt đầu từ tool
chỉ đọc như tra cứu lịch/biểu mẫu công khai. Tool ghi phải có quyền server, preview,
phê duyệt gắn actor+workspace+payload hash+thời hạn, idempotency và audit. Học cách trình
bày payload và kết quả duyệt; không mặc định đưa tùy chọn cho phép vĩnh viễn vào nghiệp
vụ nhạy cảm. Phê duyệt frontend không tự chứng minh server đã thực thi đúng.

## Những phần nên giữ khác AnythingLLM

| Điểm đã thấy trong nguồn | Quyết định cho QNU |
|---|---|
| `Workspace.getWithUser` cho admin/manager đi qua nhánh đọc mọi workspace | Không ánh xạ manager thành admin phòng; giữ membership+role theo workspace ở V1 |
| Middleware có chế độ single-user bỏ qua role check | QNU tiếp tục bắt xác thực và quyền server; dev seed không mở chế độ bỏ quyền |
| Citation gộp theo title | Gộp theo identity/revision/hash, giữ phân biệt các tài liệu cùng tên |
| Stream có chat/query và đưa nguồn từ lịch sử vào context | QNU giữ chính sách trả lời dựa nguồn; nếu tái dùng evidence lịch sử phải kiểm quyền/publication/scope hiện hành |
| TextSplitter tổng quát với chunk size/overlap | Không thay extraction/bảng/ô/provenance và phân biệt năm của QNU bằng chia văn bản thuần |
| Model route dùng TTL/sticky state | Giữ revision/grants/quota/capability và index pinning hiện có |

Nguồn bổ sung: [Workspace.getWithUser](https://github.com/Mintplex-Labs/anything-llm/blob/0941fb03596862899f7df2bdeb022eb68d4216a7/server/models/workspace.js#L294),
[multiUserProtected](https://github.com/Mintplex-Labs/anything-llm/blob/0941fb03596862899f7df2bdeb022eb68d4216a7/server/utils/middleware/multiUserProtected.js#L65),
[chat context](https://github.com/Mintplex-Labs/anything-llm/blob/0941fb03596862899f7df2bdeb022eb68d4216a7/server/utils/chats/stream.js#L224),
[TextSplitter](https://github.com/Mintplex-Labs/anything-llm/blob/0941fb03596862899f7df2bdeb022eb68d4216a7/server/utils/TextSplitter/index.js).
Đây là khác biệt thiết kế quan sát trong phần mã được đọc, không phải kết luận kiểm toán
an toàn tổng thể của AnythingLLM.

**Lưu ý quyền riêng tư QNU:** `conversations/access.py::owned` kiểm owner ngay cả với
platform admin. Quyền quản trị workspace không mặc nhiên cho phép đọc hội thoại cá nhân
của thành viên. Thiết kế menu admin phải giữ đúng điều này.

## Thứ tự triển khai đề xuất

| Đợt | Kết quả bàn giao | Phạm vi cần làm |
|---|---|---|
| A | Menu theo quyền + checklist thiết lập cho CTSV | FE catalog/capability API nếu thiếu; không đổi mô hình quyền |
| B | Hoàn thiện folder/upload rồi thêm hàng đợi theo lô | FE+API scope/identity/lifecycle; preview và retry đúng từng tệp |
| C | Nguồn dẫn dễ kiểm tra + tiến trình hội thoại | Tái dùng citation UI; event/cancel API riêng nếu triển khai streaming |
| D | Một connector hoặc widget thử nghiệm | Chọn một nhu cầu cụ thể, không triển khai đồng thời toàn bộ tích hợp |
| E | Routing nâng cao và tools/MCP | Chỉ khi có workload/nhu cầu, kiểm quyền và chi phí đủ rõ |

Ưu tiên là đề xuất dựa trên độ sát nhu cầu hiện tại, không phải ước lượng công đã cam kết.
Các thay đổi kho/route đang làm và lỗi được ghi ở Context703 cần được đối chiếu lại bằng
build/test trước đợt B; phiên nghiên cứu này không xác nhận chúng đã sửa hoặc còn lỗi.

## Hồ sơ và kiểm chứng của phiên

- Manifest36tệp nguồn, revision/tree lưu tại `storage/artifacts/anythingllm-research/`
  (local, không đưa mã upstream vào Git). Không thực thi script upstream.
- Nguồn QNU đối chiếu: sidebar/catalog, workspace access, conversation access/router/UI,
  citation sheet/drawer, upload dialog, assistant schemas, RAG policy/answer service,
  integration access/schemas, README tools/workflows. Các file source được giữ nguyên
  bởi phiên này; đã quan sát sửa đồng thời ở knowledge-detail/stage-ocr nên không dùng
  hash toàn cây làm bằng chứng không có tác nhân khác sửa.
- Chỉ kiểm cấu trúc tài liệu, liên kết, UTF-8 không BOM/LF và diff có phạm vi.
- Test/build/benchmark/runtime/browser: **NOT RUN**. Chưa có kết luận RAG của repo nào
  chính xác hơn, nhanh hơn hoặc rẻ hơn. Muốn kết luận phải thử cùng corpus/snapshot,
  model, embedding, scope và benchmark đã kiểm nhãn.
- Nếu lấy mã upstream, xem [LICENSE](https://github.com/Mintplex-Labs/anything-llm/blob/0941fb03596862899f7df2bdeb022eb68d4216a7/LICENSE) và giữ thông báo bản quyền theo
  giấy phép áp dụng; chưa sao chép mã upstream vào ứng dụng QNU trong phiên này.
