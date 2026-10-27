# Context680 — Chức năng FE còn thiếu và API BE chưa nối

Phạm vi đối chiếu: `frontendV1` và `backendV1` đang phát triển, không coi các màn
KTX/legacy là tính năng QNU đã tích hợp. Chỉ đọc mã và ghi báo cáo; không sửa ứng
dụng, gọi model/DB, tạo backup/xóa dữ liệu, reindex, restart hay deploy.

## Kết luận

Luồng upload/revision → OCR/hậu OCR → Compiler/review → duyệt/xuất bản → index/
search/chat, cùng Workspaces/ModelOps/lifecycle/Operations, đều đã có giao diện.
Không còn một module nghiệp vụ lớn nào trong các nhóm đó hoàn toàn thiếu FE.
Tuy nhiên vẫn có API chưa có thao tác UI và các khả năng mới được nối một phần.

## BE có sẵn, FE chưa nối hoặc chưa khai thác đầy đủ

| ID | Chức năng | Bằng chứng hiện tại | Cần làm |
|---|---|---|---|
| F1 | Xem đầy đủ lịch sử và danh sách lớn | [Index API](../../../backendV1/qnu/domains/knowledge/index/router.py:71) có limit/offset, nhưng [FE index query](../../../frontendV1/src/features/knowledge/index-queries.ts:49) chỉ lấy20. [Compiled documents](../../../frontendV1/src/features/knowledge/compiled-documents-list.tsx:45) chọn20/50/100 nhưng offset luôn0; [version và publication history](../../../frontendV1/src/features/knowledge/compiled-document-detail-page.tsx:99) lấy100 đầu. Review list cũng chỉ50 đầu. | Thêm trang trước/sau hoặc tải thêm, URL state và empty/error thật. BE đã hỗ trợ offset cho các danh sách này. Riêng Compiler runs chỉ có limit≤100, cần bổ sung phân trang BE nếu muốn xem xa hơn100. |
| F2 | Chọn cụ thể tài liệu khi tìm kiếm/đánh giá | [SearchRequest](../../../backendV1/qnu/domains/knowledge/index/schemas.py:43) và [EvaluationQuery](../../../backendV1/qnu/domains/evaluation/schemas.py:10) có `document_ids`. [Search UI](../../../frontendV1/src/features/knowledge/index-panel.tsx:212) không gửi trường này; [evaluation](../../../frontendV1/src/features/evaluation/evaluation-form.tsx:124) luôn gửi null. | Bộ chọn tài liệu bằng tiêu đề, chỉ gửi ID đã chọn, giữ scope khi đổi snapshot. Không suy scope từ đoạn gold hoặc tự nới khi ít kết quả. |
| F3 | Mở lại kết quả kiểm tra chính tả sau tải lại trang | [BE GET checks/{check_id}](../../../backendV1/qnu/domains/ocr/review/router.py:138) có sẵn; [hook đọc check](../../../frontendV1/src/features/knowledge/ocr-queries.ts:525) chưa có caller UI. [Gợi ý hiện tại](../../../frontendV1/src/features/knowledge/ocr-text-review-panel.tsx:117) là state bộ nhớ và chỉ lấy từ phản hồi POST. | Ghim check ID trong URL, đọc lại đúng OCR run/text version/hash, hiển thị trạng thái thật. Việc áp dụng gợi ý vẫn cần đối chiếu span và người dùng lưu. Muốn danh sách mọi lần kiểm tra cần thêm BE list API; GET một check chưa phải lịch sử đầy đủ. |
| F4 | Thử hỏi đáp trực tiếp trong bộ sưu tập | [POST collection/answers](../../../backendV1/qnu/domains/rag/answer/router.py:19) đã được register; FE không có path/caller cho endpoint này. Chat hiện có đi qua conversation/turn, không phải endpoint answers độc lập. | Màn thử câu hỏi + câu trả lời/citations/verification ngay trong kho, dùng ModelOps và scope đã chọn; không phải tạo trợ lý/hội thoại chỉ để thử. Đây là tiện ích quản trị, không phải thiếu chức năng chat hiện tại. |
| F5 | Xem/tải phản hồi gốc của review Compiler | [BE review raw](../../../backendV1/qnu/domains/knowledge/compilation/review/router.py:135) và [request helper](../../../frontendV1/src/features/knowledge/compilation-requests.ts:248) đã có. Helper không có caller ngoài file khai báo; [review tab](../../../frontendV1/src/features/knowledge/compilation-review-tab.tsx:47) chỉ nối tải Markdown. | Thêm thao tác đọc/tải raw cho đối soát nâng cao; không cần đưa mã thô vào luồng sử dụng chính. Ưu tiên thấp. |
| F6 | Dashboard QNU riêng | [Navigation](../../../frontendV1/src/navigation/config.ts:89) gắn dashboard hiện tại là template; [route dashboard](../../../frontendV1/src/routes/dashboard.tsx:1) còn đi qua tính năng KTX. Operations đã có summary/usage/readiness theo workspace. | Dashboard QNU tái sử dụng dữ liệu hiện có. Số liệu tổng hợp xuyên workspace hoặc theo thời gian cần kiểm tra/bổ sung BE riêng; không lấy số liệu giả từ template. |

Phân trang ở màn evaluation mới679 đã có; không tính nó là thiếu. Hội thoại đã
có lịch sử/tải thêm; Operations jobs, backup và resources cũng đã có phân trang.
Hook không có caller chưa tự động là một tính năng thiếu: `useIndexRunQuery`
không được dùng nhưng GET index run đã được trang evaluation gọi trực tiếp;
các helper nội bộ như `isIndexRunActive` vẫn có caller trong cùng file.

## Chưa thể giải quyết chỉ bằng nối FE

| Khả năng | BE hiện tại | Việc còn thiếu |
|---|---|---|
| Quản lý lịch sử đánh giá RAG | [Evaluation router](../../../backendV1/qnu/domains/evaluation/router.py:14) chỉ có POST chạy. FE đã xuất JSON/CSV; báo cáo hiện ở trong phiên. | Lưu run/bộ nhãn, list/detail/so sánh kết quả ở BE rồi mới làm màn lịch sử. Nhập lại bộ câu hỏi từ JSON là phần có thể làm riêng ở FE, nhưng không thay được lưu server. |
| Chat streaming từng phần | [Conversation router](../../../backendV1/qnu/domains/conversations/router.py:67) trả TurnResponse; hiện không có SSE/stream route. | Bổ sung hợp đồng streaming, reconnect/cancel/error ở BE rồi FE hiển thị. Hiện chat có trạng thái đang xử lý/polling, không phải streaming token. |
| Feedback và chia sẻ/nhúng chatbot | Router đã đăng ký không có API feedback/share/public embed. Tên bảng legacy trong ownership không chứng minh có tính năng v1. | Cần thiết kế quyền, lưu trữ, API và UI tương ứng nếu sản phẩm cần. Không gọi đây là BE làm xong mà FE quên nối. |
| Khôi phục toàn hệ thống bằng giao diện | Có [CLI recovery](../../../backendV1/scripts/recovery_bundle.py) và recovery service; không có HTTP restore route. | Chưa có API/approval/job để điều khiển an toàn từ web. Gói evidence backup trên FE không phải nút restore toàn DB/storage/vector. |

Các mục trên là khả năng còn thiếu, không phải tất cả đều bắt buộc triển khai
ngay. RAG decomposition/structured retrieval cũng là hạng mục pipeline riêng;
không nên thêm công tắc FE khi BE chưa có hành vi tương ứng.

## Thứ tự nên làm tiếp

1. F1 và F2: tránh bị giới hạn bản ghi và cho người quản trị thử đúng phạm vi tài liệu.
2. F3: quay lại đúng kết quả chính tả đã chạy, tránh phải gọi model lại khi F5.
3. F4: thêm bàn thử hỏi đáp trực tiếp trong kho; có thể dùng lại UI câu trả lời/
   citation/verification hiện có. F5 có thể ghép thành thay đổi nhỏ trong đợt này.
4. F6 và quản lý lịch sử evaluation theo nhu cầu vận hành; phần lịch sử phải làm
   cả BE. Streaming/feedback/chia sẻ/restore web là các đợt sản phẩm riêng.

## Cách kiểm tra và giới hạn

- Đọc AGENTS, memory hiện hành, Git status, router/schema/service và request/hook/
  component/route thực tế. Nhiều tệp v1 là untracked nên Git diff rỗng không được
  dùng làm bằng chứng rằng ứng dụng không đổi.
- AST Python tìm128 thao tác HTTP trên các router trong `qnu`; đối chiếu với
  `qnu/api/routes.py` xác nhận các router được register. Đây là inventory tĩnh,
  không phải gọi128API hoặc kiểm chứng runtime.
- AST TypeScript đọc96 path helpers;123 thao tác BE có path trùng khai báo FE.
  Năm thao tác chưa có path khai báo là answers và4route hạ tầng (`/health/live`,
  `/health/ready`, `/health`, `/metrics`). Health/metrics không phải nghiệp vụ
  bắt buộc có nút UI; readiness của Operations đã có màn riêng.
- Matching path không chứng minh method/caller/UI. Đã đọc riêng caller chain để
  xác nhận raw review và GET spelling check chưa được giao diện sử dụng.
- Artifact `storage/artifacts/context680-fe-be-inventory` chứa inventory,
  candidate scan, path coverage và hash trước/sau. Không dùng kết quả quét tên
  hàm đơn thuần để coi helper nội bộ là lỗi.
- Không chạy build/test/live API/browser trong phiên chỉ kiểm kê này. Kết quả
  287test của679 là lịch sử, không được báo là đã chạy lại trong680.

[Nhật ký680](../../nhat_ky/2026-10-27_phien_680_kiem_ke_chuc_nang_fe_be.md).
