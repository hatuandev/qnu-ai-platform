# Phiên 1013 — Câu hỏi luật: prompt v36 (Chặng 1) và quy tắc tập/phủ định (Chặng 2)

## Yêu cầu

- Người dùng hỏi trợ lý có trả lời đúng câu hỏi luật tuyển sinh (ví dụ: một tổ hợp
  điểm không nằm trong danh mục của ngành) hay không; sau đó yêu cầu đề xuất cách
  cải thiện chung cho mọi văn bản nạp vào kho, không chỉ một câu thử.
- Người dùng duyệt kế hoạch 4 chặng và giao **Chặng 1** (sửa prompt trả lời, không
  reindex); sau khi đo xong, giao **ghi nhật ký và làm tiếp Chặng 2** (ban đầu:
  chèn dòng bảng khớp tổ hợp làm bằng chứng, không reindex). Duyệt từng chặng,
  không mở rộng sang Chặng 3–4.
- Trong Chặng 2, đo đạc trên corpus cho thấy cơ chế chèn dòng bảng là **no-op**
  (mọi dòng khớp đã nằm trong rerank top và cell catalog); nhóm thực hiện thay
  bằng hai quy tắc prompt generic cùng mục tiêu, không reindex, và ghi rõ lý do
  trong phiên trước khi triển khai.

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
       suy ra ngoại lệ ngoài danh sách.
    2. Người hỏi không nêu tên đối tượng (ngành/đối tượng cụ thể) hoặc tên không
       có trong bằng chứng: trả lời quy tắc chung kèm dẫn chứng và nêu rõ cần tên
       để kết luận riêng; không tự chọn đối tượng thay thế.
    3. Số/điểm/điều kiện người hỏi tự nêu là tiền đề, không phải dữ kiện nguồn;
       không dùng làm căn cứ, không tự tính so sánh từ chúng; nếu nhắc thì ghi rõ
       là số của người hỏi.
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
- Còn mở sau Chặng 1: Q01 không lấy được đoạn quy đổi; Q02 chỉ liệt kê, không nói
  rõ "không nằm trong danh mục"; Q11 chỉ dẫn 2 dòng đúng nguyên chuỗi, bỏ các
  ngành có bộ tổ hợp hoán vị.
- Hai câu vẫn HTTP 409 `answer_scope_clarification_required` từ planner
  `qnu.catalog-scope/v6` — ngoài phạm vi prompt.

## Thay đổi Chặng 2

- **Đo đạc lật ngược thiết kế ban đầu.** Trên corpus đo, 15 chunk bảng của Mục 4
  nằm ở hạng rerank 0–16 cho cả Q01/Q02/Q11; `rerank_selected` = 8 mảnh bảng
  (ord 159–166) đã bao trùm mọi dòng khớp tổ hợp của cả ba câu. Chèn thêm dòng
  bảng theo đối tượng vì vậy là **no-op** — không thêm được chunk nào. Cơ chế đã
  duyệt không được xây để tránh dead code.
- Nguyên nhân thực của điểm thiếu: (a) Q11 là lỗi liệt kê tập của model — đủ bằng
  chứng 8 ngành khớp (271 ô đã trong catalog) nhưng v36 chỉ dẫn 2 dòng trùng
  chuỗi; (b) Q01/Q02/Q03 là khoảng suy luận — văn bản không có câu "không được
  dùng/chỉ được dùng/xét theo tổ hợp"; đoạn quy đổi ord 60 là quy định hoãn
  ("thông báo sau khi có kết quả thi"), nằm ở hạng 27 nên không vào evidence;
  (c) Q04 abstain đúng vì "Quản trị hàng không" không tồn tại trong kho.
- **`backendV1/qnu/domains/rag/answer/drafting.py`**
  - `PROMPT_VERSION` lên `qnu.rag.answer/v37` (dòng 16).
  - Hai quy tắc generic:
    1. Trong mục BẢNG (dòng 176): ô liệt kê nhiều thành phần là tập không thứ
       tự; đối chiếu từng dòng theo tập thành phần, quét mọi mảnh của cùng danh
       mục và liệt kê đủ mọi dòng khớp tập, không dừng ở dòng trùng chuỗi đầu
       tiên.
    2. Trong mục CÂU TRẢ LỜI (dòng 187): phương án được hỏi không có trong danh
       sách đã nêu cho đối tượng thì trả lời rõ rằng phương án không thuộc danh
       sách đó kèm dẫn ô/đoạn; không thay câu trả lời bằng việc chỉ liệt kê các
       phương án khác.
- Không đổi retrieval, `table_support.py`, schema, index hay nguồn dữ liệu.

## Phương pháp đo (Chặng 2)

- Cùng bộ 12 câu, cùng corpus/index/endpoint; v37 chạy 1 lượt/câu (12 lượt) và
  lặp **3 lần** cho 6 câu có kết quả thay đổi giữa các bản: Q02, Q03, Q05, Q08,
  Q10, Q11 (18 lượt). `trace.prompt_version` = `qnu.rag.answer/v37`.
- Ground truth Q11 lấy trực tiếp từ ô bảng trong run: đúng 8 ngành chứa tập
  {Toán, Văn, Địa} — Sư phạm Địa lý (ord 160 r8), Sư phạm Lịch sử-Địa lý
  (ord 162 r1), Việt Nam học (ord 163 r1), Công tác xã hội + Quản trị dịch vụ
  du lịch và lữ hành + Quản trị khách sạn + Quản lý TN&MT + Quản lý đất đai
  (ord 166 r1–r5). Ba ngành v35 từng liệt kê sai (Nông học, Giáo dục Thể chất,
  Quản lý nhà nước) không chứa đủ tập.
- Sau đo, 30 hội thoại kiểm thử v37 được lưu trữ qua lifecycle; không xóa vĩnh
  viễn.

## Kết quả đo (Chặng 2)

- **Q08 ổn định đúng (ca được lợi rõ nhất):** 3/3 lượt trả lời thẳng "không xét
  tuyển theo phương thức 2" và dẫn ô phương thức 1,4; khắc phục lượt v36 tự mâu
  thuẫn với chính dòng bằng chứng.
- **Q11 cải thiện một phần:** v36 2/8 (trùng chuỗi) → ba lượt liệt kê v37 đạt
  5/8, 6/8, 5/8; nhưng 2/3 lượt liệt kê thêm Nông học (không chứa tập) và một
  lượt trả nhầm kiểu (liệt kê 20 ngành, không gắn tổ hợp). Chưa đạt liệt kê đủ.
- **Q02 không đạt phủ định:** 2/3 lượt liệt kê nguyên hàng tổ hợp của Trí tuệ
  nhân tạo mà không nói "Toán, Văn, Địa không thuộc danh sách"; 1/3 abstain với
  lý do sai (cho rằng tài liệu không nêu phương thức học bạ dù cột phương thức
  ghi 1,2,3,4).
- **Q10 không đạt phủ định:** 1/3 chỉ nêu PT3 là thi đánh giá năng lực; 1/3 nêu
  IELTS áp dụng PT1–PT2 (ngụ ý đúng nhưng không trả lời thẳng); 1/3 abstain.
  0/3 nói rõ "không được dùng cho PT3".
- **Q03 dao động:** 1/3 trả lời đúng "Không được" kèm quy tắc chung; 2/3 abstain.
- **Q05:** 3/3 kết luận đúng "không thể xác nhận chắc chắn"; 1/3 vẫn tự so sánh
  29 điểm với điểm chuẩn (quy tắc tiền đề giữ 2/3).
- Q01/Q04/Q06/Q07/Q09/Q12 giữ nguyên hành vi (Q01 abstain — khoảng suy luận;
  Q04 abstain đúng; Q06/Q07 409 planner; Q09/Q12 đúng).
- **Kết luận:** v37 giữ được (không hồi quy hệ thống ngoài dao động nền), đóng
  ổn định một ca danh sách đóng (Q08) và cải thiện một phần Q11. Các câu phủ định
  và liệt kê đủ còn lại không sửa được bằng prompt trên corpus này — thuộc Chặng
  3 (metadata tổ hợp theo dòng, cần biên dịch lại và reindex) và Chặng 4 (hợp
  đồng tính eligibility phía BE), chỉ làm khi được duyệt riêng.

## Kiểm chứng

### Tĩnh

- Ruff `check` đạt trên `drafting.py` sau cả hai thay đổi v36 và v37.
- `ruff format --check` báo lỗi định dạng có sẵn tại `drafting.py` (list
  comprehension), không do thay đổi này tạo ra; giữ nguyên theo quy tắc sửa tối
  thiểu — ghi nhận FAIL nền, không sửa.

### Sống (PASS)

- 12 câu v35 + 12 câu v36 + 18 lượt lặp v36; 12 câu v37 + 18 lượt lặp v37 chạy
  thật trên API `:8002`; kết quả từng câu nêu ở mục trên.
- 42/42 hội thoại Chặng 1 và 30/30 hội thoại Chặng 2 lưu trữ thành công qua
  lifecycle (`completed`).

### NOT RUN

- pytest / full suite: không chạy theo quy ước phiên.
- Commit/push/deploy: không chạy.
- Chặng 3–4: chưa được duyệt.

## Rủi ro và bước sau

- Đo bằng một lượt có thể sai hướng vì dao động ~1/4 lượt; mọi kết luận chất
  lượng phải lặp tối thiểu 3 lần cho câu nghi ngờ.
- Trần của hướng prompt đã lộ rõ: quy tắc tập giúp Q11 bớt phụ thuộc khớp chuỗi
  nhưng model vẫn bỏ dòng và thêm dòng sai; quy tắc phủ định giúp Q08 nhưng không
  chuyển được sang Q02/Q10. Không nên vá tiếp bằng từ khóa hay câu thử.
- Chặng 3 (đưa tổ hợp vào `retrieval_metadata.attributes`) cần duyệt riêng vì
  phải biên dịch lại và reindex; Chặng 4 là hợp đồng trả lời dài hạn.
- Q06/Q07 vẫn 409 từ planner `qnu.catalog-scope/v6` — không thuộc phạm vi phiên.
