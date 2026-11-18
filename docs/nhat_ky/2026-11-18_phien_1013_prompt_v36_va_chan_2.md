# Phiên 1013 — Câu hỏi luật: prompt v36 (Chặng 1) và chèn dòng bảng theo tổ hợp (Chặng 2)

## Yêu cầu

- Người dùng hỏi trợ lý có trả lời đúng câu hỏi luật tuyển sinh (ví dụ: một tổ hợp
  điểm không nằm trong danh mục của ngành) hay không; sau đó yêu cầu đề xuất cách
  cải thiện chung cho mọi văn bản nạp vào kho, không chỉ một câu thử.
- Người dùng duyệt kế hoạch 4 chặng và giao **Chặng 1** (sửa prompt trả lời, không
  reindex); sau khi đo xong, giao **ghi nhật ký và làm tiếp Chặng 2** (chèn dòng
  bảng khớp tổ hợp làm bằng chứng, không reindex). Duyệt từng chặng, không mở
  rộng sang Chặng 3–4.

## Bối cảnh

- Corpus đo: kho "Tuyển sinh 2026" (`col_279e00e8f7fb`, workspace
  `ws_623614ba7fb8`), tài liệu "Thông tin TSĐH cập nhật.pdf", index run
  `idx_14a9742d982d` (180 chunk). Các đơn vị chỉ có `attributes` + `issued_year`,
  chưa có khóa ngành/tổ hợp trong metadata.
- Bộ câu hỏi đo 12 câu dạng luật: quy đổi tổ hợp, thay thế tổ hợp, tổ hợp của một
  ngành, điều kiện/ngưỡng, chứng chỉ ngoại ngữ, ưu tiên xét tuyển, lịch, và một
  câu liệt kê các ngành có đúng chuỗi tổ hợp.

## Thay đổi Chặng 1

- **`backendV1/qnu/domains/rag/answer/drafting.py`**
  - `PROMPT_VERSION` lên `qnu.rag.answer/v36` (dòng 16).
  - Ba quy tắc chung, mô tả hành vi:
    1. Kết luận từ danh sách đóng phải nêu rõ phạm vi danh sách đang dùng; không
       suy ra ngoại lệ ngoài danh sách (dòng 164).
    2. Người hỏi không nêu tên đối tượng (ngành/đối tượng cụ thể) hoặc tên không
       có trong bằng chứng: trả lời quy tắc chung kèm dẫn chứng và nêu rõ cần tên
       để kết luận riêng; không tự chọn đối tượng thay thế (dòng 165).
    3. Số/điểm/điều kiện người hỏi tự nêu là tiền đề, không phải dữ kiện nguồn;
       không dùng làm căn cứ, không tự tính so sánh từ chúng; nếu nhắc thì ghi rõ
       là số của người hỏi (dòng 185).
- Không đổi retrieval, schema, index hay dữ liệu nguồn ở Chặng 1.

## Phương pháp đo (Chặng 1)

- Baseline v35 và bản v36 chạy cùng corpus, cùng index run, cùng endpoint
  `:8002`; mỗi câu tạo hội thoại riêng, POST turn và poll tới khi xong; lưu JSON
  từng câu trong `%TEMP%`.
- 6 câu có kết quả đáng ngại ở lượt đơn được lặp **3 lần/câu** để tách nhiễu lấy
  mẫu khỏi hồi quy thật. Xác nhận `trace.prompt_version` = `qnu.rag.answer/v36`
  ở các lượt v36.
- Sau đo, 42 hội thoại kiểm thử (12 v35 + 12 v36 + 18 lặp) được lưu trữ qua
  lifecycle preview → accept; không xóa vĩnh viễn.

## Kết quả đo (Chặng 1)

- **Không hồi quy hệ thống.** Hai sai lệch đáng ngại ở lượt đơn đều là nhiễu lấy
  mẫu: câu hỏi tổ hợp của một ngành đạt 3/3 sau lặp; câu về ngành sư phạm 3/3
  đúng sau lặp (lượt đầu tự mâu thuẫn với chính dòng bằng chứng của nó).
- Độ dao động cùng một câu ≈ 1/4 lượt, khớp mức nền ~12%/lượt của lớp guard đã
  biết; không kết luận từ một lượt.
- Quy tắc tiền đề: 2/3 lượt lặp bỏ được so sánh số vô căn cứ (1/3 vẫn so sánh).
- Quy tắc đối tượng không tên: cho kết quả "nêu quy tắc chung + cần tên ngành",
  đúng ý định.
- Còn mở sau Chặng 1: câu quy đổi tổ hợp (Q01) không lấy được đoạn quy đổi dù
  run có 6 chunk chứa từ ngữ quy đổi (ord 59/60/73/94/167/168) — lỗi chọn bằng
  chứng, thuộc Chặng 2; câu thay thế tổ hợp (Q02) chỉ liệt kê, không nói rõ
  "không nằm trong danh mục"; câu liệt kê (Q11) chỉ dẫn 2 dòng đúng nguyên chuỗi,
  bỏ 4 ngành có bộ tổ hợp hoán vị — thiếu liệt kê đủ, thuộc Chặng 2.
- Hai câu vẫn HTTP 409 `answer_scope_clarification_required` từ planner
  `qnu.catalog-scope/v6` — ngoài phạm vi prompt, chưa sửa ở phiên này.

## Thay đổi Chặng 2

- (Đang triển khai trong cùng phiên — mục này cập nhật sau khi hoàn tất.)

## Kiểm chứng

### Tĩnh

- Ruff `check` đạt trên `drafting.py` sau thay đổi.
- `ruff format --check` báo lỗi định dạng có sẵn tại `drafting.py:76` (list
  comprehension), không do thay đổi này tạo ra; giữ nguyên theo quy tắc sửa tối
  thiểu — ghi nhận FAIL nền, không sửa.

### Sống (PASS)

- 12 câu v35 + 12 câu v36 + 18 lượt lặp chạy thật trên API `:8002`; kết quả
  từng câu nêu ở mục trên.
- 42/42 hội thoại kiểm thử lưu trữ thành công qua lifecycle (`completed`).

### NOT RUN

- pytest / full suite: không chạy theo quy ước phiên.
- Commit/push/deploy: không chạy.
- Chặng 3–4: chưa được duyệt.

## Rủi ro và bước sau

- Đo bằng một lượt có thể sai hướng vì dao động ~1/4 lượt; mọi kết luận chất
  lượng phải lặp tối thiểu 3 lần cho câu nghi ngờ.
- Chặng 2 chỉ chèn bằng chứng dòng bảng khớp tổ hợp; không đổi prompt, không
  reindex. Chặng 3 (đưa tổ hợp vào `retrieval_metadata.attributes`) cần duyệt
  riêng vì phải biên dịch lại và reindex.
