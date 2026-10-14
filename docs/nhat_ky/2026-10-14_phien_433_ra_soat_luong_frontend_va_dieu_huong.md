# Phiên 433 Rà soát luồng frontend và điều hướng

Ngày: 2026-10-14. Mục tiêu: rà giao diện, router, quy trình phía FE, các nút quay về và trường dùng chung. Phạm vi sửa tập trung Kho tài liệu, Kho tri thức, Studio, Trợ lý, Provider và các trang chi tiết còn dùng lịch sử trình duyệt. Không thay đổi backend hoặc dữ liệu phục vụ chatbot.

## Lỗi xác định và sửa

Breadcrumb chỉ khớp URL chính xác nên trang chi tiết rơi về Quản trị; sidebar cũng không nhận mục cha. Đã bổ sung metadata trang con trong navigation config, khớp ranh giới đoạn đường dẫn, chọn cha phù hợp và cho bấm breadcrumb bằng điều hướng SPA. Không sửa route tree sinh tự động hoặc đổi cấu trúc URL hiện hành.

Studio ghi quay về kho nhưng chỉ đóng chế độ Studio. Nút mới ghi đúng Chi tiết nguồn; từ đó về Kho, rồi danh sách Kho tri thức. Nhóm tài liệu quay về danh sách nhóm thay vì danh sách tệp. BackButton dùng chung đã áp dụng ở các header chính. Sáu nhóm trang chi tiết ký túc xá bỏ `window.history.back()`, chuyển tới danh sách xác định, hỗ trợ cả link mở trực tiếp; không sửa nghiệp vụ cư trú/tài chính.

Tab Kho tri thức, Trợ lý và nguồn tài liệu đọc/ghi URL qua TanStack Router. Chọn revision không còn tự sửa history ngoài router; giữ revision khi vào/ra Studio. Tab sai được xử lý về mặc định, revision không thuộc nguồn hiện lỗi riêng, không âm thầm thao tác trên một revision khác. Component nguồn/trợ lý remount khi ID thay đổi để không mang state của đối tượng trước sang đối tượng mới.

Lưu Markdown, hiệu đính và bóc tách lại dùng chung refreshSourceQueries; mở revision mới sau khi làm mới cache. Cache bổ sung facts, index revisions và tác vụ. Duyệt nguồn tiếp tục làm mới cả danh sách không còn được mount. Không tự publish hoặc duyệt khi chỉ lưu bản sửa.

Danh sách kho dùng counter legacy nên hiện 0/0, trong khi kho tuyển sinh thật có 19 nguồn và 227 chunks đang hoạt động. Đã đọc cùng API summary và query key của trang chi tiết, cache 30 giây; trạng thái chưa tải/lỗi hiển thị dấu — và lỗi có thể thử lại, không giả thành kho trống. Bỏ mô tả BGE-M3 cố định và phụ đề KPI dư thừa.

OptionSelect là composition của Select sẵn có, dùng chung ở embedding và primary/fallback chat, giữ nguyên giá trị định danh provider/model do caller quản lý. Field có render-prop cung cấp ID và liên kết aria cho hint/error/required; không tạo primitive hoặc thư viện UI mới. Helper max tokens phân biệt độ dài phản hồi với quota; bỏ cam kết tốc độ 1–2 giây và tên model suy luận cố định trong helper.

Trang model tràn ngang ở viewport 390px do grid implicit giữ min-content; thêm grid-cols-1 và cho nhãn model dài wrap. Khôi phục metadata tiếng Việt và tiêu đề QNU AI Platform; viewport không còn cấm người dùng phóng to.

## Kiểm thử

- Biome trên 32 tệp FE được sửa/tạo: đạt, không warning/error sau dọn import/biến thừa.
- Build cuối: exit 0, 5114 modules, Vite 4,16 giây và TypeScript đạt. Log tại `frontend-build433.log`.
- 12 test trọng tâm đạt: path boundary/breadcrumb, cache inactive/summary/facts/jobs, model options/provider identity và Studio save/approve/error. Bun trong sandbox lỗi quyền đọc tsconfig/dependencies; chạy lại cùng bộ ngoài sandbox đạt 12/12.
- Browser thật: người dùng đăng nhập tab Codex; tab facts giữ sau F5, Back về sources; Studio về chi tiết nguồn rồi đúng kho; tab model giữ sau F5/Back với GPT-OSS primary và Gemma fallback không đổi; revision sai bị chặn và nút Bản hiện tại phục hồi đúng nguồn.
- Mobile model: trước sửa scrollWidth 409 > viewport 390; sau sửa scrollWidth 375 <= 390. Desktop 1280 kiểm breadcrumb nguồn có Kho tri thức/Kho/Nguồn tài liệu. Override viewport được trả về mặc định.
- Danh sách kho sau tải hiển thị 19 nguồn và 227 chunks, khớp trang chi tiết; các kho trống thật hiển thị 0. Ảnh đối chiếu lưu ngoài repo tại thư mục visualizations của phiên.
- Không chạy backend pytest/Ruff hoặc quét full linter theo quy định FE-only. Không nghiệm thu lại tất cả trang ở dark mode hoặc tất cả nhánh mutation/permission.

## Tệp chính

Mới: `frontend/src/components/admin/back-button.tsx`, `option-select.tsx`, `navigation/utils.test.ts`.

Sửa: navigation config/utils, sidebar/breadcrumbs, Field, các header collection/assistant/provider, workspace nav/Studio; các route knowledge/source/assistant và page tương ứng; source-context editor/query cache; embedding/chat selectors; trang nhóm tài liệu; back navigation của assignments/applications/students/invoices/residences/residence-contracts; `frontend/index.html`. Biome chỉ định dạng phạm vi tệp đang sửa.

## Giới hạn và công việc tiếp theo

Đây là sửa luồng chính và nền dùng chung, không phải xác nhận mọi router/tính năng của toàn ứng dụng đã được kiểm thử end-to-end. Không bấm lưu cấu hình, duyệt, nạp vector, xuất bản, xóa hoặc reset trên dữ liệu thật. Backup vẫn tạm dừng; không khởi động lại BE/worker, không reindex kho.

Cần tiếp tục đối soát các đường liên kết phụ/legacy, lỗi và quyền ở từng phân hệ; cảnh báo rời màn hình khi có thay đổi chưa lưu; áp dụng component chung cho các form còn lại. Editor ngữ cảnh từng source unit của phiên 432 vẫn là phần API, chưa được xây UI trong phiên này. Dashboard còn các helper/thống kê cũ cần audit riêng; không suy ra tính đúng của chúng từ kiểm thử navigation. Nếu số kho lớn, cần API bulk summary để tránh request riêng từng kho; phiên này dùng API sẵn có và cache để thống nhất dữ liệu.

## Bài học

Back về trang cha là một hành động có đích rõ, khác Back của trình duyệt. Trạng thái tab/revision phải thuộc URL để điều hướng và F5 nhất quán. Counter của pipeline mới phải lấy cùng nguồn dữ liệu với trang chi tiết; unknown không được thay bằng số 0.
