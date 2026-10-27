# Review lại và sửa FE sau Context668 — Context671

Ngày 2026-10-27. User yêu cầu review sau prompt FE, rồi sửa 7 nhóm lỗi Context669;
RAG tiếp tục tạm dừng. Đã sửa trực tiếp `frontendV1`.

## Kết quả

| Nhóm | Khi review lại | Kết quả sửa và kiểm chứng |
| --- | --- | --- |
| F1 — nhầm bản nháp Compiler | Còn | Form ghim session/workspace/collection/run; hash preview dùng context khởi tạo. Chặn preview muộn khi draft đổi, bỏ phản hồi khi form cũ đã đóng; có xác nhận rời nháp chưa lưu |
| F2 — tải Markdown/raw | Hai nút Compiler đã được Context668 sửa, nút báo cáo còn lỗi | Giữ hai sửa đã có, truyền client xác thực cho tải báo cáo; kiểm tra handler qua DOM và transport |
| F3 — chat hơn50lượt | Còn | Infinite history lấy cửa sổ mới nhất theo chiều tăng dần của API, tải/ghép phần cũ theo ID và giữ lượt mới. Form chat ghim session/conversation; lỗi tải lịch sử hiển thị rõ |
| F4 — mất focus khi gõ heading | Còn | ID cục bộ ổn định cho section/paragraph, không lấy nội dung đang sửa làm React key; loại ID UI khỏi payload gửi server |
| F5 — cache list không làm mới | Còn | Invalidate bằng prefix gắn đúng session/workspace/collection/run, áp dụng tạo Compiler, bản sửa và review; có test không ảnh hưởng scope khác |
| F6 — auto-review | Còn | Giữ notScheduled; chỉ xử lý đúng lỗi404; polling chờ intent có giới hạn, theo review_id dù list chưa cập nhật; làm mới list khi trạng thái đổi, có tải lại và trạng thái lỗi/loading |
| F7 — runner không nạp alias/TSX | Còn | Vitest dùng alias/React transform, giữ123test cũ và thêm11test. Không bỏ kiểm tra auth/session/secret để làm xanh |

**Một lỗi mới của phần xuất bản đã được sửa:** `ReviewGateFinding` trước đây đọc
category/description/location/suggestion, trong khi backend trả
direction/status/explanation/suggested_action/sources/draft_excerpts. Người duyệt
không thấy nội dung giải thích và trích đoạn. Đã dùng đúng contract và tái sử dụng
FindingCard để hiện phát hiện/nguồn/gợi ý; verdict dùng đúng giá trị backend.
Test có dữ liệu đúng shape từ backend đã FAIL trước sửa và PASS sau sửa.

## Phạm vi mã

- Chat: `src/features/conversations/chat-view.tsx`, `queries.ts`.
- Compiler: `src/features/knowledge/compilation-editor-tab.tsx`,
  `compilation-detail-page.tsx`, `compilation-review-tab.tsx`,
  `compilation-queries.ts`, `compilation-requests.ts`.
- Publication: `src/features/knowledge/publication-types.ts`,
  `review-gate-dialog.tsx`.
- Test/runtime dev: `vitest.config.ts`, package/lockfile, comment tsconfig và
  README;10test cũ chỉ đổi runner/import/format, riêng compilation thêm negative
  case404. Ba tệp test tương tác/hook mới có hậu tố671.
- Dependency mới chỉ phục vụ test: Vitest5, React Testing Library16 và jsdom26.
  Chọn jsdom26 tương thích Node>=22.12 của project; bản30 thử đầu cần Node mới hơn.
  Chưa đổi dependency runtime của ứng dụng theo yêu cầu nghiệp vụ.

## Kiểm chứng cuối

| Kiểm tra | Kết quả thực chạy |
| --- | --- |
| `npm test -- --reporter=json --outputFile=.../full-compatible.json`, cwd frontendV1 | **PASS**, exit0,134pass/0fail/0skip;123test cũ giữ đủ,11mới |
| `npm run build`, cwd frontendV1, với dependency cuối | **PASS**, exit0; Vite + TypeScript; cảnh báo chunk>500kB còn |
| `npm run typecheck` | **PASS**, exit0 sau sửa contract verdict |
| Biome25tệp thuộc phạm vi, không sửa thêm | **PASS**, exit0,0errors/0warnings |
| `npm run lint -- --reporter=json` toàn FE | **FAIL**, exit1:61errors/12warnings/6infos trên468tệp; các lỗi nằm ngoài25tệp sửa |
| `npm ls --depth=0` | **PASS**, exit0 |
| RAG source hashes so Context670 | Giữ nguyên11tệp đã ghi hash; không thay RAG |

Lint toàn bộ vẫn FAIL. Lỗi còn có ở mẫu KTX/shared components, hai tệp
`compiled-document-detail-page.tsx` và `compiled-version-detail-page.tsx`
(organizeImports), cùng ba artifact JSON cũ trong `frontendV1/storage/qa`.
Hai tệp publication và các tệp source báo lỗi giữ hash trước sửa. Không gọi lint
toàn FE PASS hoặc quy toàn bộ lỗi cho mã KTX.

## Bằng chứng trước/sau và giới hạn

- Lệnh npm test trước sửa:66pass/6tệp fail khởi chạy. Sau chuyển runner, toàn bộ
 123test cũ chạy đạt, xác nhận không chỉ chạy riêng các tệp mới.
- Các regression trước sửa tái hiện sai draft/hash, remount ô đang gõ, cache và
  auto-review. Chat60lượt và review gate có trích đoạn đều FAIL trước sửa.
- Lượt test UI đầu thiếu ResizeObserver; đã bổ sung môi trường giả lập của Radix.
  Một mock trả object mới liên tục làm effect test lặp; đã sửa mock thành dữ liệu
  ổn định, dừng đúng worker Vitest đã xác minh thuộc lượt thử rồi chạy lại. Không
  sửa assertion hoặc app để che lỗi của fixture.
- Negative404 làm lộ một fixture cũ chỉ có problem.type, không có code. Request
  hỗ trợ đúng hậu tố type khi code là http_404, vẫn từ chối404khác/503. Ca cũ và
  ca âm đều đạt sau sửa. Một lần gọi npm sai cwd đã sửa lại đúng frontendV1.
- Sau đổi jsdom sang bản tương thích engine project, đã chạy lại full134test và
  build, đều exit0. Lượt full134 trước đó giữ làm bằng chứng riêng.
- Test tương tác dùng React DOM/jsdom, handler/query thật và cổng dữ liệu tổng
  hợp; không phải nghiệm thu SSO hoặc FE→API→model thật. Test router blocker sử
  dụng cổng router giả lập; chưa kiểm nghiệm điều hướng/beforeunload trên trình
  duyệt có phiên QNU thật.
- Không bật backend/worker, chạy inference, thay cấu hình, migration, reindex,
  restart hoặc deploy. Không có process test của phiên còn chạy khi bàn giao.

Artifact thô ở `storage/artifacts/context671-fe-fixes` (Git ignore). Kết quả rút
gọn và hashes trong [verification.json](verification.json). Giữ báo cáo669/668
làm lịch sử; kết quả671 thay thế kết luận7nhóm lỗi đó ở snapshot hiện tại.
