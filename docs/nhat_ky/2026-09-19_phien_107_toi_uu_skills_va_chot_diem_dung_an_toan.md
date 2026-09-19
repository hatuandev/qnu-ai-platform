# NHẬT KÝ LÀM VIỆC — PHIÊN #107

- **Thời gian**: 2026-09-19 14:30
- **Kỹ sư / Vai trò**: Senior Full-Stack Architect & Enterprise AI Systems Specialist
- **Mục tiêu phiên làm việc**: Thực thi Kế hoạch 05 Tối ưu hóa an toàn hệ thống 7 Skills QNU theo hướng bảo thủ:
  1. Giai đoạn 0: Khóa baseline kích thước và bảo toàn Quality Gates.
  2. Giai đoạn 1: Sửa đúng 5 điểm lệch kỹ thuật (10 liên kết `DeTaiAI`, Offline Seed Fallback trong LiveMode, cờ `--extra dev` trong pytest, scope của `ruff`, payload RAG Qdrant).
  3. Giai đoạn 2: Thu hẹp `description` của 6 skill domain và tắt implicit invocation cho `qnu-clean-code-architect` qua `openai.yaml`.
  4. Giai đoạn 3: Kiểm chứng định tuyến, kiểm thử toàn diện Quality Gates và chốt Điểm Dừng An Toàn (Safe Checkpoint).

---

## 1. Các Thay Đổi Kỹ Thuật (Key Changes)

### 1.1. Sửa Lỗi Sai Lệch Kỹ Thuật (Giai Đoạn 1)
- [`.agents/skills/qnu-rag-pipeline/SKILL.md`](.agents/skills/qnu-rag-pipeline/SKILL.md):
  - Thay thế toàn bộ 6 liên kết tuyệt đối `file:///d:/DuAnPhanMem/DeTaiAI/...` sang đường dẫn tương đối repository `backend/app/modules/rag/...`.
  - Cập nhật payload filter Qdrant thực tế: `collection_id`, `tenant_id`, `workspace_id`, `document_status == "ready"`, `is_retrievable == true`.
  - Bổ sung công thức RRF kết hợp Legal Priority Weighting: $\text{priority\_multiplier}(d) = 1.0 + (\text{priority} - 5) \times 0.02$.
- [`.agents/skills/qnu-knowledge-ingestion/SKILL.md`](.agents/skills/qnu-knowledge-ingestion/SKILL.md):
  - Thay thế 3 liên kết tuyệt đối `DeTaiAI` sang đường dẫn tương đối `backend/app/modules/knowledge/...`.
  - Chuẩn hóa lưu trữ tệp bền vững trước bóc tách.
- [`.agents/skills/qnu-modelops-resilience/SKILL.md`](.agents/skills/qnu-modelops-resilience/SKILL.md):
  - Thay thế liên kết `DeTaiAI` sang đường dẫn tương đối `backend/app/modules/modelops`.
- [`.agents/skills/qnu-frontend-architect/SKILL.md`](.agents/skills/qnu-frontend-architect/SKILL.md):
  - Chuẩn hóa Mục 6.2 phân định rõ **Demo / Sample Mode** vs **LiveMode (Chế độ sản xuất mặc định)**. Cấm Frontend âm thầm nạp số liệu mock bịa đặt khi Backend lỗi, tuân thủ nghiêm ngặt **Anti-Mock Rule** của `AGENTS.md`.
- [`.agents/skills/qnu-backend-architect/SKILL.md`](.agents/skills/qnu-backend-architect/SKILL.md):
  - Cập nhật lệnh kiểm thử chuẩn hóa có cờ `--extra dev`: `uv run --extra dev pytest -v`.
- [`.agents/skills/qnu-clean-code-architect/SKILL.md`](.agents/skills/qnu-clean-code-architect/SKILL.md):
  - Giới hạn phạm vi `uv run ruff check <tệp_hoặc_thư_mục_vừa_sửa> --fix`, tránh chạy `--fix` trên toàn repo gây sửa lan ngoài ý muốn.

### 1.2. Thu Hẹp Triggers & Quản Trị Invocation (Giai Đoạn 2)
- [`.agents/skills/qnu-clean-code-architect/agents/openai.yaml`](.agents/skills/qnu-clean-code-architect/agents/openai.yaml):
  - Tạo tệp cấu hình policy:
    ```yaml
    policy:
      allow_implicit_invocation: false
    ```
  - Chuyển skill `qnu-clean-code-architect` sang chế độ gọi tường minh (chỉ kích hoạt khi người dùng yêu cầu review kiến trúc chuyên sâu hoặc qua `$qnu-clean-code-architect`).
- **Thu hẹp `description` frontmatter của 6 domain skills**:
  - Gắn rõ ranh giới "Use this skill when..." và loại trừ "Do NOT use for..." nhằm loại bỏ hiện tượng kích hoạt chéo (cross-triggering) lãng phí token.

---

## 2. Kết Quả Đo Lường & Baseline

| Skill | Dòng Trước | Dòng Sau | Bytes Trước | Bytes Sau | Mô Tả Thay Đổi |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `qnu-backend-architect` | 65 | 63 | 4.391 | 4.347 | Sửa pytest `--extra dev`, thu hẹp trigger |
| `qnu-chatbot-builder` | 83 | 81 | 7.073 | 7.112 | Thu hẹp trigger |
| `qnu-clean-code-architect` | 168 | 166 | 9.878 | 10.069 | Thêm `openai.yaml`, giới hạn ruff scope, manual invocation |
| `qnu-frontend-architect` | 169 | 167 | 14.705 | 15.331 | Sửa Anti-Mock LiveMode, thu hẹp trigger |
| `qnu-knowledge-ingestion` | 53 | 52 | 3.999 | 3.995 | Sửa 3 links DeTaiAI, thu hẹp trigger |
| `qnu-modelops-resilience` | 43 | 42 | 2.729 | 2.719 | Sửa 1 link DeTaiAI, thu hẹp trigger |
| `qnu-rag-pipeline` | 56 | 55 | 4.292 | 4.425 | Sửa 6 links DeTaiAI, payload filter, RRF priority, thu hẹp trigger |
| **TỔNG CỘNG** | **637** | **626** | **47.067** | **48.000** | **0 lỗi Mojibake, 100% links hợp lệ** |

---

## 3. Kết Quả Kiểm Thử Toàn Diện (Verification)

1. **Frontend**:
   - `npm run lint`: Checked 130 files, **0 lỗi Biome**.
   - `npm run typecheck`: **0 lỗi TypeScript**.
   - `npm run build`: Thành công trong **7.90s** (`dist/index.html` và toàn bộ chunks).
2. **Backend**:
   - `uv run ruff check .`: **All checks passed (0 lỗi)**.
   - `uv run --extra dev pytest -v`: **216/216 tests passed (100%)**, 0 lỗi, 34 warnings.
3. **Mã hóa & Links**:
   - 100% file UTF-8 sạch, không BOM, 0 ký tự Mojibake/replacement.
   - 0 liên kết `DeTaiAI` còn sót lại.

---

## 4. Chốt Điểm Dừng An Toàn (Safe Checkpoint)

Hệ thống đã đạt trạng thái cân bằng tối ưu:
- Các sai lệch kỹ thuật và xung đột chính sách đã được triệt tiêu 100%.
- Cấu hình trigger đã được kiểm soát chặt chẽ, loại bỏ hoàn toàn việc nạp ngầm lãng phí token từ `qnu-clean-code-architect`.
- Toàn bộ test suite 216 tests và build frontend hoàn toàn trong sạch.
- **Quyết định dừng ở Giai đoạn 3**: Không vội vã tách tệp con sang progressive disclosure (Giai đoạn 4) nhằm bảo toàn tính toàn vẹn 100% của codebase và tránh gây đứt gãy trải nghiệm.
