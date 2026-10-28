# Context696 — Bổ sung nguyên tắc thiết kế vào skill frontend

Người dùng đồng ý bổ sung các điểm phù hợp đã nhận xét từ `frontend-design`
của Anthropic vào skill đang có. Dùng `skill-creator`; không chạy lệnh cài
`npx skills add` hoặc tạo thêm skill trùng vai trò.

## Thay đổi

- `.agents/skills/qnu-frontend-architect/SKILL.md`: thêm thiết kế theo tác vụ
  OCR/Compiler/ModelOps, giữ nhận diện/component của đúng phiên bản frontend,
  dùng dữ liệu giúp ra quyết định và rà soát hình ảnh khi thực sự sửa UI.
- `C:/Users/AnhTuan/.codex/skills/admin-frontend-design/SKILL.md`: bổ sung cách
  nhóm nội dung, nhấn hành động chính, đặt nhãn nhất quán, lỗi/trống có hướng
  xử lý và tự rà soát. Đây là skill cá nhân ngoài Git repo; quy ước dự án được
  ưu tiên hơn hướng dẫn chung.
- Giữ nguyên tên, description, cách chọn skill và các phần hướng dẫn cũ.
  Viết lại nguyên tắc theo ngữ cảnh; có dẫn nguồn, không sao chép toàn skill.
  Sửa nhỏ không bắt buộc wireframe, đổi thương hiệu hoặc thêm vòng phê duyệt.

Nguồn đã đọc ở lượt trao đổi trước:
[SKILL.md chính thức](https://github.com/anthropics/skills/blob/main/skills/frontend-design/SKILL.md).

## Kiểm chứng

- PASS: `python -X utf8 C:/Users/AnhTuan/.codex/skills/.system/skill-creator/scripts/quick_validate.py <skill-folder>` cho cả hai skill, exit0.
- PASS: UTF-8 không BOM/LF, liên kết mới và diff có phạm vi.
- Rà soát hướng dẫn với ba tình huống: sửa lỗi nhỏ ở nút OCR; sắp xếp lại
  ModelOps; tạo màn duyệt Compiler. Kỳ vọng lần lượt là giữ phạm vi sửa lỗi,
  nhóm theo tác vụ trong design system, và ưu tiên bản nháp/nguồn/quyết định
  duyệt. Đây là rà soát chỉ dẫn, không phải thử nghiệm chất lượng UI thực tế.
- NOT RUN: build, pytest, browser hoặc benchmark; chỉ sửa skill/tài liệu theo
  bảng kiểm chứng chung, không chỉnh code hay cấu hình ứng dụng.

Đồng bộ nhật ký, snapshot và ba index; bảo toàn thay đổi chưa commit của các
phiên trước. Không commit/push hoặc thay đổi tiến trình đang chạy.
