# Chuyên Mục Kế Hoạch Phát Triển — QNU AI Platform

Thư mục này lưu trữ các tài liệu kế hoạch, lộ trình kỹ thuật và phân tích phương án phát triển cho từng cấu phần của dự án **QNU AI Platform**.

---

## 📌 Danh Mục Kế Hoạch

1. [**`01_ke_hoach_phat_trien_fe.md`**](./01_ke_hoach_phat_trien_fe.md):
   - **Tên kế hoạch**: Kế hoạch phát triển Frontend QNU AI Platform chuẩn Design System QLKTX.
   - **Mục tiêu**: Xây dựng lại Frontend bằng **Vite 8 + React 19 + TanStack Suite + Tailwind CSS v4 + Biome**, kế thừa 100% tokens màu OKLCH, khung vỏ `AdminShell` (Sidebar, Topbar, Breadcrumbs, CommandMenu) từ dự án `qnu-ktx`, và bổ sung bộ components chuyên trách AI (`ChatMessage`, `MessageScroller`, `Attachment`, `QuestionnaireCard`, `CitationSheet`, `DAGCanvas`).
   - **Trạng thái**: Đã phê duyệt, sẵn sàng thực thi.

2. [**`03_ke_hoach_dong_bo_taxonomy_loai_van_ban.md`**](./03_ke_hoach_dong_bo_taxonomy_loai_van_ban.md):
   - **Tên kế hoạch**: Chuẩn hóa và đồng bộ taxonomy loại văn bản từ `qnu-ai-core` sang `qnu-ai-platform`.
   - **Mục tiêu**: Đưa 37 loại văn bản QNU về một contract có mã chuẩn, lưu bền vững trong Platform và dùng chung cho Knowledge, RAG, Workflow, Drafting và Frontend.
   - **Trạng thái**: Đã triển khai nền tảng taxonomy v1; còn chờ Core contract versioned để sync HTTP.

3. [**`05_ke_hoach_toi_uu_skills_an_toan.md`**](./05_ke_hoach_toi_uu_skills_an_toan.md):
   - **Tên kế hoạch**: Tối ưu hệ thống Skills an toàn, không giảm chất lượng code.
   - **Mục tiêu**: Giảm skill bị kích hoạt thừa nhưng giữ nguyên toàn bộ quality gate và cấu trúc dự án.
   - **Trạng thái**: Sẵn sàng triển khai; chưa sửa các skill.

4. [**`06_ke_hoach_tai_cau_truc_chuc_nang_va_dieu_huong.md`**](./06_ke_hoach_tai_cau_truc_chuc_nang_va_dieu_huong.md):
   - **Tên kế hoạch**: Tái cấu trúc chức năng và điều hướng QNU AI Platform theo Assistant Workspace và Knowledge Workspace.
   - **Mục tiêu**: Giảm sidebar, gộp trải nghiệm đúng hành trình người dùng nhưng giữ độc lập các domain Backend, versioning và runtime.
   - **Trạng thái**: Bản kế hoạch, chờ phê duyệt triển khai.

5. [**`07_ke_hoach_cai_thien_toan_dien_sau_code_review.md`**](./07_ke_hoach_cai_thien_toan_dien_sau_code_review.md):
   - **Tên kế hoạch**: Cải thiện toàn diện QNU AI Platform sau code review.
   - **Mục tiêu**: Đưa dự án từ Internal Beta mạnh lên Production Candidate qua 10 đợt ưu tiên Security, Truthful Runtime, Database Integrity, RAG, ModelOps, Workflow, Evaluation, Testing, Observability và Deployment.
   - **Trạng thái**: Bản kế hoạch đề xuất; ưu tiên bắt đầu từ baseline xanh, secret/auth boundary và loại fake-success trong LiveMode.

6. [**`08_huong_dan_cai_thien_code_tang_diem_danh_gia.md`**](./08_huong_dan_cai_thien_code_tang_diem_danh_gia.md):
   - **Tên tài liệu**: Hướng dẫn cải thiện code QNU AI Platform để đạt Production Candidate.
   - **Mục tiêu**: Chuyển Kế hoạch 07 thành hướng dẫn triển khai có thứ tự, nguyên tắc code, acceptance criteria, failure tests, Definition of Done và ma trận bằng chứng để nâng mức đánh giá từ khoảng 6,5/10 lên 8,5+/10.
   - **Trạng thái**: Hướng dẫn thực thi; ưu tiên ba phiên đầu là Schema Truth, RAG Data Truth và Secret/Trusted Approval.

7. [**`09_danh_gia_sau_vibe_coding_va_huong_dan_cai_thien.md`**](./09_danh_gia_sau_vibe_coding_va_huong_dan_cai_thien.md):
   - **Tên tài liệu**: Đánh giá sau vibe coding và hướng dẫn cải thiện tiếp.
   - **Mục tiêu**: Kiểm chứng việc triển khai Kế hoạch 08 bằng code, test, migration và dữ liệu live; chỉ ra khoảng cách giữa unit test và runtime, đồng thời lập lộ trình P0/P1 để đạt Production Candidate thật.
   - **Trạng thái**: Đánh giá độc lập hoàn tất; điểm hiện tại đề xuất 7,1/10, ưu tiên sửa reconciliation, RAG live data, worker payload v1 và ModelOps fake-success.
