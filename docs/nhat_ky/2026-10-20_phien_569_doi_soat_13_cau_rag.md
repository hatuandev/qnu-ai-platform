# Phiên569 — Đối soát 13 câu RAG từng FAIL ở Qwen hoặc Luna

Ngày 20/10/2026. Người dùng giao bước 1: xác định nguyên nhân từng câu trước khi quyết định sửa pipeline hoặc bổ sung Hybrid Fact Extraction.

## Phạm vi thực hiện

Đọc source canonical, Facts, query/gold, labels, responses và diagnostics frozen của Context567 benchmark-3 và Context568. Xem mã thật và replay các hàm thuần trên dữ liệu đã lưu; không gọi model mới hoặc chạy lại benchmark. Báo cáo dùng số569 để giữ Context568 Luna-only.

## Kết quả

- Hợp hai tập FAIL có13IDs,5chung; xem26cặp,18FAIL/8PASS lịch sử. Không sửa nhãn hoặc điểm51/60 của hai lượt.
- Cùng272blocks/368Facts,33goldspans/30citations được kiểm theo offsets/hash/revision. Chưa có bằng chứng mất nội dung nguồn cần cho các ca này.
- P06 replay đúng11contextIDs cả hai lượt: nhóm Bảng1 chiếm nhóm đầu làm dừng packing, gold dù đã rerank bị bỏ. Gold-first oracle giữ K5/36.000 vẫn chứa2gold; đây chỉ là chẩn đoán, không ranking production.
- P07/P03 thiếu điều kiện; P07 citation đủ toàn đoạn nhưng internal audit cả hai vẫn chấp nhận. P15 có lỗi quan hệ sắp thứ tự dù ngày đúng.
- P08 cờbảngđãbật nhưng first-column matching không lấy hàng có mã/quy tắc ở cột sau; bác bỏ giả thuyết chỉ bật cờ. P10/N19 mất vế bảng sau ROW_SELECTION_MISSING.
- M05 code đọc được12cặp nguyên mã; schema payload không có caption/source context xác định Bảng1. Chưa có raw selector1/2 nên không gán duy nhất nguyên nhân model-call nào.
- P11 verifier đòi thêm chủ đề không hỏi; P16 ghép proof sai nhánh; X09 fallback có rule nhưng Qwen chưa chốt được completeness. X05/X08 guard đúng phạm vi, public refusal thiếu lý do đơn vị/vai trò.

## Lệnh và kiểm tra thực chạy

CWD repo root; Python `backend/.venv/Scripts/python.exe`.

1. `backend/storage/context569/collect.py`: cuối exit0,13IDs/26pairs/33spans/30citations; input/code hashes lưu. Lần đầu lỗi helper source_revision string/object, đã sửa helper; không app changes.
2. `backend/storage/context569/probes.py`: exit1,13PASS/3FAIL. Hai FAIL P08 bác bỏ giả thuyết cờ; một FAIL kiểm không có ý định I/O do import client Qdrant kiểm compatibility. Socket guard chặn trước kết nối; noLLM/noDB, warning giữ.
3. `backend/storage/context569/followup.py`: exit0,4PASS, thuầnstdlib. Xác nhận captiongap, giả thuyếtP08bịbác và code khớp manifest. Không ghi đè FAIL trước.
4. `backend/storage/context569/verify.py`: kiểm hashes, source citations, UTF8/LF, links/diff và đủIDs khi bàn giao; kết quả máy đọc tại `handoff-verification.json`.

Xem [validation đầy đủ](../bao_cao/context569/VALIDATION_REPORT.md) để phân biệt hypothesis probes với application regression. FullPytest/Ruff/FEbuild/livebenchmark/DBreadback NOT RUN. Full56718FAIL vẫn lịch sử, không báo fullPASS.

## File và dữ liệu

- [Báo cáo nguyên nhân](../bao_cao/context569/ROOT_CAUSE_REPORT.md).
- [Bảng đối soát đủ13câu](../bao_cao/context569/CASE_MATRIX.md).
- [Kiểm chứng và giới hạn](../bao_cao/context569/VALIDATION_REPORT.md).
- Cập nhật index/memory và snapshot569; giữ thay đổi Context568 trước task.
- Helper/private evidence trong Storage ignored, không đưa corpus hoặc prompt riêng vào báo cáo Git.
- Không sửa app/tests/config/model/source/Facts/vector/publication, không reindex/republish/restart/deploy/stage/commit/push. Không tạo dữ liệu DB cần cleanup hoặc đụng runtime cũ đã bị policy chặn.

## Bước sau

Chỉ mới hoàn tất đối soát. Ưu tiên kiểm đủ điều kiện và quan hệ đầu ra, sửa chọn/pack proof, caption/schema trace, kiểm chứng đúng phạm vi và lý do từ chối. Bước2 chưa thực hiện; chưa có kết quả cải thiện mới. Hybrid Fact Extraction là POC tiếp theo nếu chứng minh thêm giá trị.
