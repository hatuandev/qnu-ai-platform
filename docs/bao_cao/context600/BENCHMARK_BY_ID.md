# Context600 — Đối chiếu đủ64 ID

Baseline và lượt cuối cùng questions/criteria/gold, source/canonical/index/vector, model/profile/timeout và quy tắc history. Social4 câu ngoài mẫu số60. Không thay điểm lượt chính bằng retry. Không đưa raw câu hỏi, đáp án hoặc corpus vào Git.

- Baseline:58/60; cuối:59/60. Positive48/50→49/50, negative10/10→10/10, social4/4→4/4.
- Gains:P10,P15. Loss:P07 (thiếu điều kiện nguồn). Không chứng minh causal gain/loss riêng do graph bằng phép đo này.
- Citation khớp canonical135/135→152/152;0runtime ở cả hai. Citation hợp lệ không chứng minh đáp án đầy đủ.

| ID | Baseline | Cuối | Đổi | Citation trước→sau | ms trước→sau | Nhận xét lượt cuối |
|---|---|---|---|---|---|---|
| N01 | PASS | PASS | unchanged | 1→1 | 527.39→533.00 | Đủ ô nguồn, đúng tọa độ/giá trị/phạm vi và trích dẫn. |
| N02 | PASS | PASS | unchanged | 1→1 | 500.68→492.82 | Đủ ô nguồn, đúng tọa độ/giá trị/phạm vi và trích dẫn. |
| N03 | PASS | PASS | unchanged | 1→1 | 381.25→361.26 | Đủ ô nguồn, đúng tọa độ/giá trị/phạm vi và trích dẫn. |
| N04 | PASS | PASS | unchanged | 1→1 | 358.15→351.17 | Đủ ô nguồn, đúng tọa độ/giá trị/phạm vi và trích dẫn. |
| N05 | PASS | PASS | unchanged | 1→1 | 514.02→503.64 | Đủ ô nguồn, đúng tọa độ/giá trị/phạm vi và trích dẫn. |
| N06 | PASS | PASS | unchanged | 1→1 | 396.81→379.25 | Đủ ô nguồn, đúng tọa độ/giá trị/phạm vi và trích dẫn. |
| N07 | PASS | PASS | unchanged | 1→1 | 488.40→508.83 | Đủ ô nguồn, đúng tọa độ/giá trị/phạm vi và trích dẫn. |
| N08 | PASS | PASS | unchanged | 1→1 | 443.56→355.20 | Đủ ô nguồn, đúng tọa độ/giá trị/phạm vi và trích dẫn. |
| N09 | PASS | PASS | unchanged | 1→1 | 500.17→501.91 | Đủ ô nguồn, đúng tọa độ/giá trị/phạm vi và trích dẫn. |
| N10 | PASS | PASS | unchanged | 1→1 | 363.01→357.19 | Đủ ô nguồn, đúng tọa độ/giá trị/phạm vi và trích dẫn. |
| N11 | PASS | PASS | unchanged | 1→1 | 516.54→516.73 | Đủ ô nguồn, đúng tọa độ/giá trị/phạm vi và trích dẫn. |
| N12 | PASS | PASS | unchanged | 1→1 | 358.72→408.56 | Đủ ô nguồn, đúng tọa độ/giá trị/phạm vi và trích dẫn. |
| N13 | PASS | PASS | unchanged | 1→1 | 588.76→524.63 | Đủ ô nguồn, đúng tọa độ/giá trị/phạm vi và trích dẫn. |
| N14 | PASS | PASS | unchanged | 1→1 | 446.90→372.83 | Đủ ô nguồn, đúng tọa độ/giá trị/phạm vi và trích dẫn. |
| N15 | PASS | PASS | unchanged | 1→1 | 360.76→347.55 | Đủ ô nguồn, đúng tọa độ/giá trị/phạm vi và trích dẫn. |
| N16 | PASS | PASS | unchanged | 1→1 | 389.05→353.13 | Đủ ô nguồn, đúng tọa độ/giá trị/phạm vi và trích dẫn. |
| N17 | PASS | PASS | unchanged | 3→3 | 12868.25→13929.66 | Đúng P.ĐT và hạn 30/11/2026 từ hàng NV-01. |
| N18 | PASS | PASS | unchanged | 3→4 | 9906.43→13246.29 | Giữ nguyên điều kiện Theo đủ điều kiện Phụ lục II cho NV-28, không kết luận chỉ có hồ sơ là đạt. |
| N19 | PASS | PASS | unchanged | 3→3 | 10875.53→9601.26 | Giá trị 0 thật của CT-01 gắn số giờ vượt mức nhóm A năm2026 có chứng cứ. |
| N20 | PASS | PASS | unchanged | 3→3 | 7678.15→10008.87 | Đúng CS-02 Thiết bị mô phỏng và trạng thái Cần làm rõ, không áp chéo bảng. |
| M01 | PASS | PASS | unchanged | 2→2 | 559.02→395.80 | Đủ ô nguồn, đúng tọa độ/giá trị/phạm vi và trích dẫn. |
| M02 | PASS | PASS | unchanged | 2→2 | 514.53→567.99 | Đủ ô nguồn, đúng tọa độ/giá trị/phạm vi và trích dẫn. |
| M03 | PASS | PASS | unchanged | 2→2 | 362.83→356.86 | Đủ ô nguồn, đúng tọa độ/giá trị/phạm vi và trích dẫn. |
| M04 | PASS | PASS | unchanged | 2→2 | 505.92→541.50 | Đủ ô nguồn, đúng tọa độ/giá trị/phạm vi và trích dẫn. |
| M05 | PASS | PASS | unchanged | 12→12 | 6782.75→4183.45 | Đủ đúng12 cặp mã/tên theo gold rows nguồn; giữ số0 và dấu nối, không đưa dòng tổng vào tập. |
| M06 | PASS | PASS | unchanged | 1→1 | 537.99→596.68 | Đủ ô nguồn, đúng tọa độ/giá trị/phạm vi và trích dẫn. |
| F01 | PASS | PASS | unchanged | 1→1 | 391.11→355.26 | Đủ ô nguồn, đúng tọa độ/giá trị/phạm vi và trích dẫn. |
| F02 | PASS | PASS | unchanged | 1→1 | 449.84→374.47 | Đủ ô nguồn, đúng tọa độ/giá trị/phạm vi và trích dẫn. |
| F03 | PASS | PASS | unchanged | 1→1 | 5021.77→6057.34 | Đủ ô nguồn, đúng tọa độ/giá trị/phạm vi và trích dẫn. |
| F04 | PASS | PASS | unchanged | 1→1 | 4918.61→5063.80 | Đủ ô nguồn, đúng tọa độ/giá trị/phạm vi và trích dẫn. |
| F05 | PASS | PASS | unchanged | 1→1 | 573.09→521.26 | Đủ ô nguồn, đúng tọa độ/giá trị/phạm vi và trích dẫn. |
| F06 | PASS | PASS | unchanged | 1→1 | 358.55→373.47 | Đủ ô nguồn, đúng tọa độ/giá trị/phạm vi và trích dẫn. |
| F07 | PASS | PASS | unchanged | 1→1 | 5277.75→5919.06 | Đủ ô nguồn, đúng tọa độ/giá trị/phạm vi và trích dẫn. |
| F08 | PASS | PASS | unchanged | 1→1 | 11819.23→4138.36 | Đủ ô nguồn, đúng tọa độ/giá trị/phạm vi và trích dẫn. |
| P01 | PASS | PASS | unchanged | 3→4 | 39628.79→28139.99 | Nguồn ghi tài liệu mô phỏng phục vụ kiểm thử, không có giá trị áp dụng thực tế; không tạo tuyên bố quyền/nghĩa vụ thật. |
| P02 | PASS | PASS | unchanged | 3→4 | 25215.02→26018.75 | Đúng năm học01/09/2026–31/08/2027 và phân biệt rõ với năm dương lịch2026/2027. |
| P03 | PASS | PASS | unchanged | 4→4 | 41074.63→46040.86 | Đủ ba mức ưu tiên đúng thứ tự: dữ liệu khóa có chữ ký, biên bản có số lưu, tổng hợp được xác thực và không vượt chứng cứ gốc. |
| P04 | PASS | PASS | unchanged | 4→4 | 22021.56→22420.65 | Đúng sổ xác nhận sử dụng phòng máy phân tích dữ liệu; chỉ AM-0007, loại rõ AM-0070. |
| P05 | PASS | PASS | unchanged | 7→6 | 43091.86→21684.26 | Nêu2027 Ước tính chỉ lập kế hoạch, không nghiệm thu; không áp cột Ghi nhận2025/2026. |
| P06 | PASS | PASS | unchanged | 7→7 | 55413.68→59953.27 | Đủ nhóm A/kế hoạch2027,15 ngày, thông báo và quyết định; không đổi chỉ tiêu SV/nhómB, giữ ngoại lệ. |
| P07 | PASS | FAIL | loss | 6→4 | 64511.55→53374.97 | Thiếu tiền đề: cơ sở tiếp nhận tạm đóng, nhật ký thực tập và xác nhận giảng viên cùng kỳ; giữ thời hạn/ngoại lệ nhưng chưa đủ điều kiện áp dụng. |
| P08 | PASS | PASS | unchanged | 4→6 | 60951.20→40038.12 | Giữ mã dạng chuỗi, số0đầu và dấu nối; không đồng nhất mã gần nhau. Có đoạn nguồn thừa/lặp nhưng không đổi định danh hoặc ý nghĩa bảo toàn mã. |
| P09 | PASS | PASS | unchanged | 6→5 | 28451.59→35344.61 | Giữ / củaCT-06 chưa được định nghĩa/unknown, không tự diễn giải hoặc đổi0. |
| P10 | FAIL | PASS | gain | 0→4 | 54284.78→25798.55 | Phân biệt dấu chưa đo CT-05 do AM/TN-02 với số0 có chứng cứ CT-01; không coi cùng nghĩa. |
| P11 | PASS | PASS | unchanged | 3→5 | 58288.06→43509.24 | Giữ >15giờ/người cho giảng viên có hợp đồng và >=15giờ/khoa cho khoa; không trộn toán tử/chủ thể/đơn vị. |
| P12 | PASS | PASS | unchanged | 4→8 | 39920.64→43785.08 | Đúng Q=.45A+.35B+.20C, >=80% chứng cứ đủ điều kiện vàABC đều số xác thực; thiếu ghi chưa đủ điều kiện, không đặt0; đủ các định nghĩa nguồn. |
| P13 | PASS | PASS | unchanged | 6→6 | 72546.30→50530.37 | Đủ thứ tự Khoa/Viện đến Phòng Đào tạo đến Hội đồng; đường phản hồi là hiệu chỉnh theo biên bản. |
| P14 | PASS | PASS | unchanged | 3→4 | 37598.69→41725.51 | Mỗi ghi chú chỉ thuộc bảng ngay trước; không suy CS-02 sang TT-02, giữ quyết định riêng. |
| P15 | FAIL | PASS | gain | 0→6 | 50631.94→41324.52 | Đúng ngày ban hành18/10/2026 và bắt đầu áp dụng01/11/2026; không đồng nhất hai mốc. |
| P16 | PASS | PASS | unchanged | 8→8 | 77866.67→68563.84 | Thiếu biến ghi Chưa đủ điều kiện tính, không gán0 và không kết luận Đạt/Cần khắc phục. |
| X01 | PASS | PASS | unchanged | 0→0 | 675.70→621.02 | Từ chối năm2099, không lấy năm khác. |
| X02 | PASS | PASS | unchanged | 0→0 | 374.11→353.95 | Không có đúng mã; không lấy mã gần giống. |
| X03 | PASS | PASS | unchanged | 0→0 | 538.31→527.69 | Không tự đồng nhấtAM-07 vớiAM-0007 hoặcAM-0070. |
| X04 | PASS | PASS | unchanged | 0→0 | 360.14→366.11 | Yêu cầu xác định đại lượng, không chọn một số ngẫu nhiên. |
| X05 | PASS | PASS | unchanged | 0→0 | 540.59→597.04 | Giữ đơn vịSV và từ chối đổi thành lớp khi không có căn cứ. |
| X06 | PASS | PASS | unchanged | 0→0 | 366.95→398.19 | Yêu cầu năm trước khi chọn số. |
| X07 | PASS | PASS | unchanged | 6→6 | 18254.09→18184.19 | Giữ ký hiệu/ chưa định nghĩa, không đổi0 hoặc suy số giờ. |
| X08 | PASS | PASS | unchanged | 0→0 | 566.95→400.53 | Không coi sốước tính2027 là số đã nghiệm thu. |
| X09 | PASS | PASS | unchanged | 4→3 | 25811.16→25291.79 | ThiếuA chưa đủ điều kiện tínhQ; không bịaQ hoặc gánA=0. |
| X10 | PASS | PASS | unchanged | 0→0 | 6386.75→6802.01 | Từ chối điểm chuẩn ngoài nguồn. |
| S01 | PASS | PASS | unchanged | 0→0 | 2.41→2.91 | Đáp lời chào đúng loại hội thoại. |
| S02 | PASS | PASS | unchanged | 0→0 | 2.77→3.07 | Đáp lời cảm ơn đúng loại hội thoại. |
| S03 | PASS | PASS | unchanged | 0→0 | 2.42→2.53 | Nêu phạm vi hỗ trợ theo persona hiện hành. |
| S04 | PASS | PASS | unchanged | 0→0 | 2.68→2.25 | Đáp lời tạm biệt đúng loại hội thoại. |

Giới hạn nhãn: draft source-rubric do Codex đối chiếu actual response và hash; không phải human holdout. Exact cell/quote/span checks chạy offline; không gọi judge model. Raw responses, adjudications và seals giữ trong artifact local được ignore.
