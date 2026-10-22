# Phiên 591 — Sửa RAG/wiki và benchmark 64

Context591: sửa trace/reader/unknown/year/condition packing; cuối đủ64, 59/60 tri thức, positive49/50, negative10/10, social4/4; 85%PASS. CònFAIL F03. Focused257/Ruff21 PASS; full3123PASS/18FAILnền/17SKIP, 37mớiPASS, exactIDs/cause không đổi. 138/138citationsđúng, 124Luna usage/0fallback. Source/model/config/vector giữ, postcheckPASS, 2DBtestdọn/Storagegiữtheopolicy. Không reindex/publish/restart/commit/push.

Thực hiện từ 21 sang 22/10/2026. Dùng các skill clean-code, rag-pipeline,
rag-evaluation, backend và ModelOps; không điều phối agent khác. Giữ các thay
đổi Context587–590 chưa commit. Mã không đổi parser/FE trong lượt này.

Sửa theo nguyên nhân chung: action contract reader, tách mô tả unknown khỏi
consumer số liệu, vai trò năm/phạm vi câu hỏi, dependency và đóng gói nguyên
quy định, audit điều kiện vòng sau, trace provider trung thực. Không hạ gate.

Focused/full tests dùng PostgreSQL test riêng và Local Storage tạm, endpoint
ngoài bị cô lập. Live64 gọi candidate RAG staging cùng nguồn/model; không phải
published HTTP/browser E2E. Chấm exact ô/hàng và review rubric có response hash;
không dùng judge LLM. Các lượt gián đoạn/FAIL được giữ, không ghép vào lượt cuối.

Lệnh/cwd/exit code, exact18 lỗi nền, bảng đối chiếu64 ID, giới hạn và artifact
ở [báo cáo](../bao_cao/context591/IMPLEMENTATION_AND_VALIDATION.md).
Full vẫn FAIL. Không chuyển sang ưu tiên wiki4–6, không xuất bản dữ liệu.
