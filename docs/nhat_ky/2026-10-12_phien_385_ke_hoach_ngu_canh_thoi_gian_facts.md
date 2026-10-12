# Phiên 385 Kế hoạch ngữ cảnh thời gian trong Facts

Ngày12/10/2026. Người dùng yêu cầu viết lại kế hoạch sau khi chốt năm/phương thức/ngữ cảnh từng số liệu lưu cùng fact; ngày/năm ban hành ở metadata nguồn. Chỉ lập kế hoạch, không triển khai ứng dụng.

## Nội dung

Tạo Kế hoạch14 gồm14mục: định nghĩa thời gian/nơi lưu, ứng viên ngày ban hành và filename hints, evidence/conflict/precision, header tree/spans/bảng nối trang/văn xuôi, typed fact context/migration nullable, common answerability/claim gate/SSE, rewrite/cache/UI,6hạng mục phụ thuộc, rollout giữserving vàtestmatrix.

Ví dụ2023/2024 từ ảnh: Quản lý Giáo dục7140114 điểmTHPT15/22,5, học bạ18/18; chỉ tiêu50/47, nhập học27/50. Không gán năm văn bản cho sốliệu hoặc phương thức của cột điểm cho chỉtiêu. IELTSidentitythuầnsố cần được hỗtrợ, không dùngôcóchữđầutiên cho mọi bảng.

Skills ingestion/RAG sử dụng để giữ invariants/provenance, parse-once và published snapshot. Skill write-page hướng dẫn rõ tiêu đề/phân biệt evidence/đề xuất và tôn trọng đích repository docs; không tạo Page cloud.

## Tệp thay đổi

- docs/ke_hoach/14_ke_hoach_ngu_canh_thoi_gian_facts_va_rag_dag.md và README.
- docs/nhat_ky/2026-10-12_phien_385_ke_hoach_ngu_canh_thoi_gian_facts.md và README.
- docs/memory/PROJECT_CONTEXT.md, snapshot385 và docs/WORK_LOG.md.

## Kiểm chứng và bàn giao

Đọc lại outline và quy tắc: ban hành/chủ đề/applicability khác nhau; năm filename chỉứngviên; thiếuDBfactkhôngđồngnghĩathiếudữliệutrongtài liệu; missingkhôngsuyratrườngchưacôngbố; cache/SSEkhôngbypassguard. Kếhoạch làđềxuấtkhôngbáođãimplement.

Không sửa runtime, gọi LLM, ghi DB, khởi động lại worker, migration, reset, reparse, publish hoặc qnu-sso. Không chạy pytest/build vì chỉ thay tài liệu. Đã kiểm tra outline, UTF-8 nghiêm ngặt không có ký tự thay thế, các liên kết tương đối tới tệp tồn tại và git diff --check đạt. Không dùng các kiểm tra tài liệu này làm bằng chứng tính năng đã triển khai.
