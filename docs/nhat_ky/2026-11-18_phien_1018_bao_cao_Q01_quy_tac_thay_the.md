# Phiên 1018 — Báo cáo Q01: câu hỏi quy tắc thay thế tổ hợp

- Ngày: 2026-11-18
- Workstream: chất lượng trả lời câu hỏi luật/tổ hợp trên corpus "Thông tin TSĐH cập nhật.pdf" (kho "Tuyển sinh 2026", ws_623614ba7fb8)
- Phạm vi báo cáo: vấn đề gặp phải, việc đã làm, việc còn mở để Q01 đạt kết quả tốt
- Trạng thái chung: đã đo sau Chặng B; Q11 có hồi quy đã xác định cơ chế, chờ duyệt cách sửa; chưa commit/deploy; pytest/full suite, Kiri 12Q NOT RUN

## 1. Câu hỏi và chuẩn đúng

Q01 (nguyên văn): "Em đạt 15 điểm ở tổ hợp Toán, Văn, Địa nhưng chỉ đạt 13 điểm ở tổ hợp Toán, Lý, Hóa. Em có thể dùng kết quả 15 điểm của tổ hợp thứ nhất để đủ điều kiện xét học bạ vào ngành sử dụng tổ hợp thứ hai không?"

Chuẩn đúng đã chốt với người dùng:

1. Kết luận phủ định dứt khoát: **không được dùng thay**, trong phạm vi danh mục Mục 4.
2. Căn cứ phải trích được: danh sách tổ hợp đóng theo ngành (Mục 4) và/hoặc câu quy tắc quy đổi ở Mục 3 ("thông báo sau khi có kết quả thi tốt nghiệp THPT 2026").
3. Số liệu người dùng nêu (15/13) là tiền đề, không phải bằng chứng; model không được tự tính so sánh.
4. Thiếu căn cứ thì nói rõ phạm vi thiếu, không bịa, không trả lời "có".

## 2. Các vấn đề gặp phải (theo công đoạn)

### P1 — Gốc dữ liệu: câu quy tắc bị cắt rời ngay từ biên dịch

MinerU/OCR xuất mỗi dòng thị giác thành một block; câu quy tắc quy đổi ở trang 2 là 3 block liên tiếp (ev_p002_b016/b017/b018). Compiler biến mỗi block thành một đoạn nháp rồi mỗi đoạn thành một chunk, nên **không chunk đơn lẻ nào chứa trọn câu**; hệ quả là trước Chặng B không có chunk nào chứa "quy đổi"/"chuyển đổi" mà retrieval có thể trích cho Q01. Đây là lỗi quy trình, không phải lỗi prompt.

### P2 — Truy xuất/chọn bằng chứng

Với câu hỏi kiểu này, top-8 sau rerank toàn là mảnh bảng Mục 4 (ord 159–170); mảnh quy tắc chỉ ở hạng 31 (Chặng A) và 24 (Chặng A2), không lọt cửa sổ. Chặng A (ghép mảnh câu lúc đọc cho rerank, `qnu.evidence-reading/v3`) cải thiện điểm nhưng không đưa được mảnh quy tắc vào top-8, nên Q01 vẫn chỉ trả lời được nhờ bảng.

### P3 — Cổng gọi lại (appeal) bị chặn sai

Trước Chặng C, Q01 thường rơi vào `insufficient_evidence` dù bằng chứng bảng đủ để kết luận phạm vi: `plan_ready` trong `coverage.py` đếm cả nhóm `kind="continuation"` (nhóm tùy chọn nối header bảng, vốn đã bị các nhánh khác bỏ qua), nên appeal không được phép chạy.

### P4 — Hợp đồng trả lời của prompt

Ba lỗi hành vi đã gặp và đã sửa dần bằng luật generic (không từ điển, không từ khóa test):

- Trả lời bằng cách liệt kê tổ hợp khác thay vì nói rõ "phương án được hỏi không nằm trong danh sách" (v37).
- Tự tính so sánh từ số người dùng nêu ("29 > 26.5") như thể là bằng chứng (v36).
- Với câu hỏi thay thế phương án, kết luận bị đẩy sang "chờ quy đổi" thay vì kết luận danh mục trước (v39).

### P5 — Hợp đồng dữ liệu bảng

Cột tổ hợp chứa nhiều tổ hợp trong một ô, thứ tự không cố định (tập không thứ tự); đối chiếu chuỗi thô gây âm tính/ dương tính giả. Đã xử lý bằng luật khớp tập (v37), metadata tổ hợp từng dòng + lọc thuộc tính (Chặng 3: rules v11, `catalog-scope/v8`), và facts tính sẵn cho câu liệt kê (Chặng 4: `qnu.rag.closed-set/v1`).

### P6 — Thao tác dữ liệu/phát hành

Bản biên dịch mới bị cổng review chặn 409 `publication_review_required` nếu chưa có phiên rà soát hoàn tất. Đã đi đúng hợp đồng: duyệt bằng `review_skip` (mode skipped, lý do, đúng version/bundle), rồi publish; index tự đồng bộ qua `mark_pending` + `wake`.

### P7 — Chặng B gây hồi quy kỹ thuật ở Q11

Sau khi gộp dòng, cả 8 mảnh bảng Mục 4 lọt ngân sách bằng chứng nên đều "selectable". `closed_set.computed_facts` được thiết kế chỉ tính từ mảnh **không** selectable, nên bỏ qua toàn bộ (trace: `status: no_tables`, `skipped_selectable: 8`), mất đường liệt kê tất định đã đóng ở Chặng 4.

## 3. Những gì đã làm

### 3.1 Thay đổi mã (đều generic, không hard-code dữ liệu test)

| Thay đổi | Tệp | Phiên bản/ghi chú |
|---|---|---|
| Luật prompt câu hỏi luật | `backendV1/qnu/domains/rag/answer/drafting.py` | v36 → v37 → v38 → **v39** (đang chạy) |
| Metadata tổ hợp từng dòng + lọc thuộc tính | `metadata.py`, `supplement.py`, `query_scope.py` | rules **v11**, catalog-scope **v8** |
| Facts tính sẵn cho liệt kê/khớp danh mục | `backendV1/qnu/domains/rag/answer/closed_set.py`, `packing.py` | **closed-set/v1**; chỉ tính từ mảnh bảng đóng gói không selectable |
| Ghép mảnh câu cho rerank | `backendV1/qnu/domains/knowledge/index/search.py` | evidence-reading **v3**; không đổi dữ liệu |
| Mở cổng appeal cho Q01 | `backendV1/qnu/domains/rag/answer/coverage.py` | `plan_ready` bỏ qua nhóm continuation tùy chọn |
| **Chặng B — gộp dòng ở biên dịch** | `backendV1/qnu/domains/knowledge/compilation/line_wrap.py`, gọi tại `source_first.py:30` | gộp block cùng trang khi dòng chưa kết thúc câu, sát lề phải, cách dòng nhỏ, thụt đầu dòng khớp; tôn trọng vùng bị chặn và trần đoạn nháp |

### 3.2 Thao tác dữ liệu (có duyệt, không đổi nguồn gốc)

- Biên dịch lại: 172 → **111 đoạn nháp**; index **184 → 119 chunk**.
- Đăng ký/duyệt/xuất bản: run `cmp_ef09317f450b`, version **cver_269963ffa24b** (version_no 3), thay cver_7dbc92d84d05; quyết định `pdec_16cab1a03865` (approve, review_skip) và `pdec_209cc6cc89b8` (publish).
- Reindex: **idx_0944fa66af55**, generation 3, 119 chunk; search-readiness revision 4, ready.
- Kiểm chứng ở tầng index: đoạn quy tắc 165 ký tự, 3 dẫn chứng, tìm lại **hạng 1, điểm 0.9904** (trước B không tồn tại chunk chứa trọn câu).

### 3.3 Đo lường (prompt v39, index gen 3)

Q01 ×10, cùng một câu hỏi, 10 hội thoại riêng:

| Chỉ số | Trước B (v39 + sửa appeal) | Sau B |
|---|---|---|
| Trả lời ngay lượt đầu | 0/3 | **8/10** |
| Phải dùng appeal | 2/3 | 2/10 |
| Abstain | 1/4 | **0/10** |
| Lỗi/502 | 0 | 0 |
| Phủ định dứt khoát + dẫn chứng | 3/4 | 6/10 (thêm câu Q01 trong bộ 12 bị rào → 6/11) |

Chấm chi tiết 10 lượt: 6 lượt nói rõ "không thể dùng… thay thế" kèm dẫn chứng; 2 lượt (7, 8) nêu đúng "không thuộc danh sách" nhưng kết luận rào "chưa có căn cứ để khẳng định"; 2 lượt (2, 9) chỉ nêu "chờ quy tắc quy đổi", không kết luận. Không lượt nào khẳng định "có thể dùng".

Bộ 12 câu (một lượt mỗi câu, tiếng Việt, có chấm tay):

| Câu | Kết quả | Ghi chú |
|---|---|---|
| Q01 | Rào | nêu quy định "chưa có quy định cho phép" nhưng kết luận phụ thuộc quy đổi |
| Q02 | Ngầm (chưa đạt chuẩn tường minh) | chỉ liệt kê tổ hợp/method của ngành; baseline Chặng 4 là 4/4 phủ định tường minh; n=1 |
| Q03 | Đạt | phủ định có phạm vi danh mục + quy tắc hoãn |
| Q04 | Đạt (abstain đúng) | ngành không có trong nguồn |
| Q05 | Đạt | nêu 26.5/25.85 nhưng không khẳng định đỗ vô căn cứ |
| Q06 | Đạt (abstain đúng) | điểm sàn 2026 không có trong nguồn |
| Q07 | Đạt | nêu quy tắc hoãn + "chưa cung cấp công thức/hệ số" |
| Q08 | Đạt | loại PT2 tường minh, kèm ô phương thức 1,4 |
| Q09 | Đạt | loại PT3 tường minh; PT4 = ĐGNL Sư phạm Hà Nội |
| Q10 | Đạt (lần này tường minh) | IELTS chỉ PT1/PT2, không áp dụng PT3 |
| Q11 | **Hồi quy** | chỉ 2/8 ngành đúng (QT du lịch, QT khách sạn); không có dương tính giả |
| Q12 | Đạt (đối chứng) | hotline 1800.55.88.49 |

Ghi chú: Q06/Q07 lần này không còn 409 như các ledger trước; chưa chứng minh nhân quả riêng của B.

### 3.4 Vệ sinh

- 58 hội thoại đo (12 + 46, gồm các probe Q01 còn sót từ các đợt A/A2/B) đã được lưu trữ qua lifecycle.
- Artifact đo nằm ngoài repo tại `%TEMP%`: `qnu_q01_repeat_bmerge.json`, `qnu_rules_eval_bmerge.json` (không chứa token/bí mật).
- Code chưa commit; không đổi `.env`; không đụng tệp nguồn/thuật toán cấm.

## 4. Vấn đề chưa xử lý được (để Q01 đạt kết quả tốt)

1. **Kết luận phủ định chưa ổn định (ưu tiên 1).** Tỷ lệ phủ định dứt khoát 6/11; 3/11 chỉ "rào" bằng "chưa có căn cứ", 2/11 chỉ nêu chờ quy đổi. Đây là phần còn lại phía model sau khi bằng chứng đã đủ (mọi lượt đều trích được E9). Cần đo lặp cỡ 10 lượt sau khi xử lý mục 2; nếu vẫn thấp, hướng generic là mở rộng facts cho trường hợp **không nêu ngành**: xác định tổ hợp được hỏi không thuộc bất kỳ dòng nào có mặt trong danh mục (phạm vi catalogue) và buộc narrate kết luận âm — cần duyệt vì sửa `closed_set`/`drafting`.
2. **Q11 hồi quy do gate selectable của closed-set (ưu tiên 1).** Đề xuất tối thiểu (task #425, chờ duyệt): bỏ điều kiện loại bảng selectable khỏi `computed_facts` tại `packing.py:56-63` để facts tính từ mọi mảnh bảng đã đóng gói; cập nhật `tests/unit/test_closed_set_facts_1015.py:75` theo hợp đồng mới; đo Q11 ×3 rồi mới chốt. Rủi ro thấp: dẫn chứng của facts vẫn là ô có thật trong bảng đã hiển thị.
3. **Q02 mới có 1 lượt ngầm.** Baseline Chặng 4 là 4/4 tường minh; theo luật "lặp 3× trước khi kết luận hồi quy", cần đo Q02 ×3 cùng đợt với mục 2 (facts membership dự kiến phát khi bỏ gate).
4. **Nhánh nhiều kho bỏ qua ghép mảnh câu.** `multi.py::search_collections` không dùng stitch của Chặng A; nếu trợ lý gán nhiều kho, Q01 quay lại thiếu mảnh quy tắc trong rerank. Cần áp cùng cơ chế khi đo/ sửa nhánh nhiều kho.
5. **Dao động một lượt ở Q03/Q05/Q10.** Đã từng gặp 1–3 lượt sai trong các đợt trước; lượt này đều đạt nhưng mẫu 1. Muốn tuyên bố ổn định phải đo lặp, không sửa prompt theo một lượt.
6. **Phạm vi kiểm chứng chưa chạy.** pytest/full backend suite, Kiri 12Q, kiểm thử UI hiển thị, commit/deploy: **NOT RUN** — không tính là PASS.
7. **409 theo năm/planner (cũ).** Từng xuất hiện ở Q06/Q07 trong ledger trước; lần này không tái hiện. Giữ theo dõi, chưa đóng.

## 5. Thứ tự đề xuất

1. Duyệt và làm #425 (bỏ gate selectable + cập nhật test hợp đồng) → đo Q11 ×3, Q02 ×3 trên cùng index gen 3.
2. Đo Q01 ×10 lại sau #425 để chốt tỷ lệ phủ định dứt khoát; chỉ khi vẫn thấp mới cân nhắc mở rộng facts catalogue-wide (mục 4.1) — cần duyệt riêng.
3. Áp stitch cho nhánh nhiều kho (mục 4.4) khi cần chạy kịch bản nhiều kho.
4. Sau khi chốt: viết nhật ký/snapshot/memory và dọn hội thoại đo (task #424).

## 6. Bằng chứng tham chiếu

- Gộp dòng: `backendV1/qnu/domains/knowledge/compilation/line_wrap.py`; gọi tại `source_first.py:30`.
- Facts đóng: `backendV1/qnu/domains/rag/answer/closed_set.py:38` (`_fragments` loại trừ `exclude_evidence_ids`), `packing.py:56-63`.
- Prompt/ answer: `backendV1/qnu/domains/rag/answer/drafting.py` (v39).
- Trace Q01 sau B: `prompt_version = qnu.rag.answer/v39`; E9 = `ich_a6bcc625e49d` (đoạn quy tắc gộp, hạng 1, 0.9904).
- Trace Q11: `computed = {status: no_tables, tables: 0, skipped_selectable: 8}` — cơ chế hồi quy.
- Version/index: `cver_269963ffa24b` (run `cmp_ef09317f450b`), `idx_0944fa66af55` gen 3, readiness revision 4.
