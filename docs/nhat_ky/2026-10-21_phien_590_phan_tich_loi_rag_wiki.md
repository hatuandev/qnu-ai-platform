# Phiên 590 — Phân tích lỗi RAG sau tích hợp trang tri thức

Người dùng yêu cầu tìm nguyên nhân các lỗi còn lại và đánh giá cách sửa. Phạm vi
là chẩn đoán, chưa triển khai bản sửa ứng dụng. Đọc AGENTS, context, Git/diff,
skill qnu-rag-pipeline và qnu-rag-evaluation; đối chiếu artifact thật đã lưu.

24 gold spans của 9 câu lỗi khớp canonical, 23 unit đều có refs trong wiki.
P03/P13/P14 sai contract lượt reader thứ hai; P07/P11 bị YEAR_REQUIRED trước
retrieval; P09/P10 tái hiện ambiguous bị bọc thành lỗi integrity; P05 đã có
đoạn nguồn nhưng vòng audit sau phát sinh điều kiện e6.c3. Tái hiện thêm lỗi
tách danh sách năm thành clause mất chủ ngữ. P01 chưa xác định lỗi upstream:
log DomainException 502 không chứng minh actual HTTP 502, status gốc null.

Chạy helper offline `context590_diagnosis.py` từ root bằng Python backend.
Lượt đầu exit 1 do guard chặn socketpair nội bộ Windows; điều chỉnh riêng helper,
lượt hoàn chỉnh 12/12 probe PASS/exit 0. Network service bị chặn, 0 LLM/DB calls,
743 file app/test/đầu vào giữ SHA. Probe PASS là xác minh nguyên nhân, không
phải sản phẩm đã sửa. Full test/live benchmark/FE NOT RUN trong lượt này.

Thêm báo cáo, nhật ký, snapshot và các mục lục. Không sửa mã app/test, không
thay model/source/index, reindex/publish/restart/commit/push. Giữ toàn bộ thay
đổi chưa commit trước đó. Chưa làm ưu tiên 4–6.

[Báo cáo nguyên nhân và kế hoạch sửa](../bao_cao/context590/ROOT_CAUSE_AND_FIX_PLAN.md).
Đề nghị tiếp theo: trace → reader/routing → unknown/integrity → phạm vi năm →
condition closure → regression và frozen64 cùng nguồn/model. Chưa APPROVED.
