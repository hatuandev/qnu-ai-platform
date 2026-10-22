# Phiên596 — Phân tích điểm RAG giảm sau hoàn thiện ngữ cảnh

Người dùng yêu cầu tìm nguyên nhân. Chỉ phân tích, chưa được giao sửa ứng dụng.

Đọc PROJECT_CONTEXT, Git/diff, skill clean-code/RAG pipeline/evaluation, quy tắc
verification và workflow. Đối chiếu artifact591/595 với mã hiện tại.

Kết quả:59/60→51/60 là lịch sử hai lượt thật; F03 tăng, chín loss gồm5lỗi lease và
F08/P07/P12/P15. Năm retry tuần tự5/5 không ghép vào điểm64. Việc chạy synthetic
model đồng thời benchmark của Codex làm nhiễu phép đo; chưa chứng minh lease holder.
P07 đủ source/audit scope nhưng thiếu tiền đề công khai; pure-function replay chứng
minh required=false bỏ qua gap. P12 audit vẫn thiếu định nghĩa sau bổ sung; P15 chọn
đoạn thừa ngày kết thúc. Context IDs P12/P15 và mã fallback/audit giống591. F08 literal
guard nhạy hoa/thường/khoảng trắng; không có rejected rewrite thật để quy chắc nguyên nhân.

Nguồn/profile/query/rubric/index giống; snapshot chỉ đổi created_at.1.239code seals
giữ. Không kết luận mọi loss do595, không đổ cho parser/Qwen32K.

Thay đổi: báo cáoContext596, nhật ký/index/WORK_LOG/PROJECT_CONTEXT/snapshot; helper
offline trong validation và artifact chọn lọc trong Storage ignored. Không sửa app.

Lệnh thật tại repo root:
`backend/.venv/Scripts/python.exe -X utf8 .antigravity-bridge/validation/context596_analysis.py`.
Exit0, offline assertions đạt; không DB/LLM/network call. Đọc mã/seal và artifact
bổ sung bằng Python/PowerShell; không pytest/live mới. Full59518FAIL nền vẫn FAIL.

Đề xuất: benchmark tuần tự; chặn mất tiền đề P07; sửa span/body/context và phục hồi
điều kiện P12/P15; đối chiếu rewritten metric tương đương có kiểm soát; rồi nguyên64.
Chưa thực hiện app fix, reindex, publish, đổi model/config, restart, commit/push.
Storage cũ giữ theo policy.

[Báo cáo nguyên nhân](../bao_cao/context596/ROOT_CAUSE_ANALYSIS.md).
