# Phiên653 — Sơ đồ quy trình backendV1

User yêu cầu tổng hợp quy trình bằng sơ đồ. Dùng skill diagram-design với marker
qnu-teal đã có; không sửa profile/skill. Đối chiếu memory và các contract/mã OCR,
text review, Compiler/review, publication/index, answer và conversation.

Tạo HTML tĩnh có3SVG1280×720,8node mỗi hình: tổng quan; hậuOCR/Compiler; hỏi đáp.
Xuất baPNG@2 và baSVG độc lập, kèm bản Markdown có links nguồn. Nét đứt chỉ bản
sửa hậuOCR chưa nối Compiler; reviewCompiler là API riêng, không auto worker hoặc
cổng bắt buộc publication. Không biến việc giữ nguyên OCR gốc thành sửa đè nguồn.

Kiểm tra self_check skill PASS, browser headless desktop/mobile390px, đo chữ không
tràn và label không đè node. Geist/InstrumentSerif tải được, có fallback khi offline.
Playwright bundled thiếu chromium riêng nên dùng browser đã cài, không cài mới.
PNG được mở xem trực quan trước bàn giao. Artifact không có JavaScript hoặc API
nghiệp vụ. Không chạy pytest ứng dụng vì chỉ thay tài liệu/sơ đồ.

Files chính: `docs/diagrams/quy-trinh-qnu-backendv1-2026-10-26.*` và các bản
`-tong-quan`, `-hau-ocr-compiler`, `-hoi-dap`. Script/render QA ignored ở
`backendV1/storage/context653/`. Không đổi app/ModelOps/DB/runtime hoặc restart/Git.

[Sơ đồ và nguồn](../diagrams/quy-trinh-qnu-backendv1-2026-10-26.md).
