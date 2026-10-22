# Phiên594 — Giữ đúng phạm vi và điều kiện hội thoại

Context594: sửa P1 coverage đối tượng/nguồn và bảo toàn điều kiện/ngoại lệ. Focused290/Ruff4 PASS;56regression mới PASS. Full3195PASS/18FAILnền/17SKIP, exactIDs/cause khớp592, không lỗi mới/thiếu. Live8/8,citations8/8,6Luna/0fallback; synthetic routing3/4,C04FAIL do metric không giữ literal, hỏi lại an toàn, chưa chứng minh riêng hoa/thường. Full64/FE NOT RUN. Hai DBtest dọn, Storage giữ theo policy; nguồn/model/vector/publication và code ngoài scope giữ. Chưa mục3–6/wiki4–6/reindex/publish/restart/commit/push.

Yêu cầu: chỉ sửa mục1–2 từ review593 trước khi mở rộng liên kết.

Phương pháp: proof đầy đủ cho tên/nguồn, giữ nguyên predicate và toán tử, bỏ/thay điều kiện theo lệnh literal, chặn bypass legacy/year shortcut. Không sửa/parser/index/source/model/Quality Gate.

Ranh giới kiểm chứng: baseline đỏ15FAIL/7PASS; mở rộng đỏ6FAIL/50PASS; cuối290focusedPASS, fullFAIL18 nền, exact56newPASS. Kết quả live4synthetic3PASS/1FAIL được giữ, không đổi nhãn để đạt xanh. Model thật chưa bảo đảm thao tác bỏ lọc dù regression nhánh đó đạt.

Lệnh, test IDs/cause, các lượt trung gian, file thay đổi, an toàn môi trường và giới hạn nằm trong [báo cáo](../bao_cao/context594/IMPLEMENTATION_AND_VALIDATION.md).

Không stage/commit/push/deploy/reindex/publish/restart. Hai database test dọn theo nonce, Storage test còn do chính sách; không bypass. Bước tiếp theo cần tách khỏi task này: mục3–6 và độ ổn định literal của router nếu được giao.
