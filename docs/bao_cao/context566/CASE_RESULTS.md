# Context566 — Kết quả từng ca

Mỗi ID có đúng một kết quả của lượt TCP đã chốt. Câu hỏi, đáp án, exact source spans và response đầy đủ nằm trong artifact private; bảng này chỉ chứa kết quả/metadata. Nhãn cuối theo rubric nguồn, không dùng câu trả lời model làm gold.

| ID | Nhóm | Kết quả | Trạng thái API | ms | Citation | Căn cứ chấm |
|---|---|---|---|---:|---:|---|
| N01 | scalar | PASS | answered | 753.38 | 2 | Đủ ô nguồn, đúng tọa độ/giá trị/phạm vi và trích dẫn. |
| N02 | scalar | FAIL | insufficient_context | 428.22 | 0 | Nguồn có số ghi nhận đúng phạm vi; cách hỏi rõ ghi nhận nhưng bị METRIC_UNVERIFIED. |
| N03 | scalar | PASS | answered | 372.82 | 1 | Đủ ô nguồn, đúng tọa độ/giá trị/phạm vi và trích dẫn. |
| N04 | scalar | PASS | answered | 397.37 | 2 | Đủ ô nguồn, đúng tọa độ/giá trị/phạm vi và trích dẫn. |
| N05 | scalar | PASS | answered | 377.16 | 1 | Đủ ô nguồn, đúng tọa độ/giá trị/phạm vi và trích dẫn. |
| N06 | scalar | PASS | answered | 549.56 | 1 | Đủ ô nguồn, đúng tọa độ/giá trị/phạm vi và trích dẫn. |
| N07 | scalar | FAIL | insufficient_context | 352.47 | 0 | Nguồn có số ghi nhận đúng phạm vi; cách hỏi rõ ghi nhận nhưng bị METRIC_UNVERIFIED. |
| N08 | scalar | PASS | answered | 440.92 | 1 | Đủ ô nguồn, đúng tọa độ/giá trị/phạm vi và trích dẫn. |
| N09 | scalar | PASS | answered | 373.66 | 2 | Đủ ô nguồn, đúng tọa độ/giá trị/phạm vi và trích dẫn. |
| N10 | scalar | PASS | answered | 408.53 | 1 | Đủ ô nguồn, đúng tọa độ/giá trị/phạm vi và trích dẫn. |
| N11 | scalar | FAIL | insufficient_context | 6337.86 | 0 | Nguồn có đúng mã/hàng/cột; ROW_SELECTION_MISSING nói không tìm thấy mã hoặc cột mã. |
| N12 | scalar | PASS | answered | 388.12 | 1 | Đủ ô nguồn, đúng tọa độ/giá trị/phạm vi và trích dẫn. |
| N13 | scalar | PASS | answered | 393.21 | 1 | Đủ ô nguồn, đúng tọa độ/giá trị/phạm vi và trích dẫn. |
| N14 | scalar | PASS | answered | 2532.44 | 2 | Đủ ô nguồn, đúng tọa độ/giá trị/phạm vi và trích dẫn. |
| N15 | scalar | FAIL | insufficient_context | 2554.18 | 0 | Tên có đúng trong bảng nhưng request bị ràng vào mã ngành ngoài danh mục nguồn, nên không tìm được fact. |
| N16 | scalar | PASS | answered | 357.97 | 1 | Đủ ô nguồn, đúng tọa độ/giá trị/phạm vi và trích dẫn. |
| N17 | other_table | FAIL | insufficient_context | 2965.85 | 0 | Có đủ đoạn/hàng nguồn tương ứng nhưng ROW_METRIC_SCOPE_UNRESOLVED chặn câu trả lời. |
| N18 | other_table | FAIL | insufficient_context | 3018.03 | 0 | Có đủ đoạn/hàng nguồn tương ứng nhưng ROW_METRIC_SCOPE_UNRESOLVED chặn câu trả lời. |
| N19 | other_table | FAIL | insufficient_context | 3103.13 | 0 | Có đủ đoạn/hàng nguồn tương ứng nhưng ROW_METRIC_SCOPE_UNRESOLVED chặn câu trả lời. |
| N20 | other_table | PASS | answered | 2241.21 | 2 | Đúng đối tượng và trạng thái hàng CS-02; exact citation hỗ trợ cả hai ô. |
| M01 | multi | PASS | answered | 371.48 | 2 | Đủ ô nguồn, đúng tọa độ/giá trị/phạm vi và trích dẫn. |
| M02 | multi | PASS | answered | 526.46 | 3 | Đủ ô nguồn, đúng tọa độ/giá trị/phạm vi và trích dẫn. |
| M03 | multi | FAIL | insufficient_context | 376.68 | 0 | Nguồn có số ghi nhận đúng phạm vi; cách hỏi rõ ghi nhận nhưng bị METRIC_UNVERIFIED. |
| M04 | multi | FAIL | answered | 349.59 | 1 | Hỏi hai chỉ số nhưng chỉ trả chỉ tiêu; thiếu số ghi nhận của cùng mã/năm. |
| M05 | enumeration | FAIL | insufficient_context | 33920.39 | 0 | Không liệt kê được 12 cặp mã/tên dù gold đã ánh xạ đầy đủ; VISIBLE_ANSWER_NOT_SUPPORTED. |
| M06 | multi | FAIL | insufficient_context | 2597.15 | 0 | Dòng tổng và cột cần hỏi có trong nguồn nhưng bị NO_COMPATIBLE_FACT_EVIDENCE. |
| F01 | followup | PASS | answered | 362.41 | 2 | Đủ ô nguồn, đúng tọa độ/giá trị/phạm vi và trích dẫn. |
| F02 | followup | PASS | answered | 1987.98 | 1 | Đủ ô nguồn, đúng tọa độ/giá trị/phạm vi và trích dẫn. |
| F03 | followup | FAIL | answered | 2027.86 | 1 | Hỏi số SV ghi nhận nhưng trả số chỉ tiêu của lượt trước; trích dẫn đúng nguồn không sửa được sai đại lượng. |
| F04 | followup | FAIL | insufficient_context | 2500.63 | 0 | Đã có mã mới và ngữ cảnh năm/đại lượng từ người dùng nhưng hệ thống hỏi lại chủ đề/năm. |
| F05 | followup | FAIL | insufficient_context | 2402.83 | 0 | Lượt mở đầu hỏi tên chương trình/năm/chỉ tiêu rõ ràng, có hàng nguồn nhưng bị từ chối. |
| F06 | followup | FAIL | insufficient_context | 1159.38 | 0 | Chuỗi nối tiếp không hoàn thành; seed F05 đã thất bại. Không suy đây là các nguyên nhân độc lập đã cô lập. |
| F07 | followup | FAIL | insufficient_context | 2425.32 | 0 | Chuỗi nối tiếp không hoàn thành; seed F05 đã thất bại. Không suy đây là các nguyên nhân độc lập đã cô lập. |
| F08 | followup | FAIL | insufficient_context | 4433.79 | 0 | Chuỗi nối tiếp không hoàn thành; seed F05 đã thất bại. Không suy đây là các nguyên nhân độc lập đã cô lập. |
| P01 | prose | FAIL | insufficient_context | 8644.89 | 0 | Nguồn nói rõ tài liệu mô phỏng không có giá trị thực tế, nhưng bị NUMERIC_GROUNDING_FAILED. |
| P02 | prose | PASS | answered | 15076.64 | 3 | Đủ hai mốc năm học và phân biệt với năm dương lịch; các exact sentence spans hỗ trợ. |
| P03 | prose | PASS | answered | 18886.51 | 1 | Trả đúng thứ tự ba loại chứng cứ như câu hỏi yêu cầu; không nâng thẩm quyền bản tổng hợp. Rubric được xét theo ý nghĩa, không ép lặp mọi câu nguồn. |
| P04 | prose | PASS | answered | 8782.64 | 2 | Nêu đúng hồ sơ kèm riêng AM-0007 và loại AM-0070; citation đúng chú thích dòng. |
| P05 | prose | PASS | answered | 8438.69 | 3 | Nêu đúng Ước tính 2027 là dự kiến, không nghiệm thu và không lan sang Ghi nhận 2026. |
| P06 | prose | FAIL | insufficient_context | 20996.52 | 0 | Có đủ đoạn/hàng nguồn tương ứng nhưng ROW_METRIC_SCOPE_UNRESOLVED chặn câu trả lời. |
| P07 | prose | FAIL | insufficient_context | 29468.84 | 0 | Nguồn có đủ nội dung yêu cầu nhưng trả VISIBLE_ANSWER_NOT_SUPPORTED; không có câu trả lời để nghiệm thu. |
| P08 | prose | PASS | answered | 13959.40 | 4 | Câu trả lời giữ mã gốc/chuỗi, cấm đánh rơi số 0 và thay định danh; không cho phép phép đổi mã được hỏi. Dẫn footnote và Điều 1 tương đương, không chỉ gold hàng Bảng 9. |
| P09 | prose | PASS | answered | 7290.17 | 2 | Xác nhận ký hiệu chưa giải thích và phải giữ nguyên; không quy đổi 0. |
| P10 | prose | PASS | answered | 6856.56 | 1 | Trả đúng dấu ở CT-05 là chưa đo do tạm ngừng và khác 0; CT-01 bằng 0 đã là tiền đề câu hỏi, không bắt lặp lại tiền đề. |
| P11 | prose | FAIL | insufficient_context | 10936.74 | 0 | Nguồn có đủ nội dung yêu cầu nhưng trả VISIBLE_ANSWER_NOT_SUPPORTED; không có câu trả lời để nghiệm thu. |
| P12 | prose | PASS | answered | 45773.64 | 2 | Đủ công thức, ngưỡng chứng cứ, ba biến số xác thực và quy tắc thiếu biến không đặt 0; hai citation đúng exact spans. |
| P13 | prose | FAIL | insufficient_context | 34301.93 | 0 | Nguồn có đủ nội dung yêu cầu nhưng trả VISIBLE_ANSWER_NOT_SUPPORTED; không có câu trả lời để nghiệm thu. |
| P14 | prose | PASS | answered | 16226.79 | 1 | Đúng mỗi ghi chú thuộc bảng ngay trước, không áp chéo; exact câu nguồn hỗ trợ. |
| P15 | prose | PASS | answered | 36414.85 | 4 | Phân biệt đúng ngày ban hành và ngày bắt đầu áp dụng; có dư nội dung nhưng không sai dữ kiện. |
| P16 | prose | PASS | answered | 21391.87 | 5 | Đúng chưa đủ điều kiện tính, không kết luận Đạt/Cần khắc phục, không thay thiếu bằng 0; phần code minh họa được trích đúng nguồn. |
| X01 | negative | PASS | insufficient_context | 406.66 | 0 | Từ chối/làm rõ đúng phạm vi thiếu năm, mã, metric hoặc không có dữ liệu; không tạo số hay mượn nguồn khác. |
| X02 | negative | PASS | insufficient_context | 394.46 | 0 | Từ chối/làm rõ đúng phạm vi thiếu năm, mã, metric hoặc không có dữ liệu; không tạo số hay mượn nguồn khác. |
| X03 | negative | PASS | insufficient_context | 368.04 | 0 | Từ chối/làm rõ đúng phạm vi thiếu năm, mã, metric hoặc không có dữ liệu; không tạo số hay mượn nguồn khác. |
| X04 | negative | PASS | insufficient_context | 447.67 | 0 | Từ chối/làm rõ đúng phạm vi thiếu năm, mã, metric hoặc không có dữ liệu; không tạo số hay mượn nguồn khác. |
| X05 | negative | FAIL | answered | 394.88 | 1 | Người dùng hỏi theo lớp nhưng trả số SV mà không giải thích thiếu phép quy đổi; source citation đúng nhưng không đáp đúng đơn vị. |
| X06 | negative | PASS | insufficient_context | 386.97 | 0 | Từ chối/làm rõ đúng phạm vi thiếu năm, mã, metric hoặc không có dữ liệu; không tạo số hay mượn nguồn khác. |
| X07 | negative | FAIL | insufficient_context | 233.55 | 0 | Không bịa 0 nhưng hỏi lại chỉ tiêu/ghi nhận, không nhận ra nguồn đã xác nhận ký hiệu chưa định nghĩa; thiếu lời giải đúng về unknown. |
| X08 | negative | FAIL | insufficient_context | 4569.42 | 0 | Đúng là không có kết quả nghiệm thu 2027, nhưng thêm nhận định sai mã AM-0007 không khớp tên Khoa học dữ liệu; full-case không PASS. |
| X09 | negative | FAIL | insufficient_context | 16529.36 | 0 | Chặn được việc chốt số Q nhưng chỉ nói chưa đối chiếu chắc con số; thiếu kết luận không thể tính do A vắng theo rubric đã chốt. Safety abstention riêng đạt. |
| X10 | negative | PASS | insufficient_context | 2434.49 | 0 | Từ chối/làm rõ đúng phạm vi thiếu năm, mã, metric hoặc không có dữ liệu; không tạo số hay mượn nguồn khác. |
| S01 | social | PASS | answered | 127.11 | 0 | Đúng hội thoại/meta, status answered, không citation; trace router_model_calls=0, rag_invoked=false. |
| S02 | social | PASS | answered | 126.19 | 0 | Đúng hội thoại/meta, status answered, không citation; trace router_model_calls=0, rag_invoked=false. |
| S03 | social | PASS | answered | 125.95 | 0 | Đúng hội thoại/meta, status answered, không citation; trace router_model_calls=0, rag_invoked=false. |
| S04 | social | PASS | answered | 132.28 | 0 | Đúng hội thoại/meta, status answered, không citation; trace router_model_calls=0, rag_invoked=false. |

Tổng tri thức 34/60 PASS; 26 FAIL. Hội thoại riêng 4/4 PASS. 64/64 HTTP 200; không missing/duplicate ID.

Chấm định tính do Codex kiểm lại theo nguồn, chưa có human signoff. X07/X09 bị chấm thiếu lý do dù không tạo số; X08 có giải thích sai. Điểm an toàn từ chối đơn giản và điểm đầy đủ toàn câu được phân biệt trong [báo cáo chính](BENCHMARK_REPORT.md).

Không cộng hội thoại vào mẫu số 85%; không bỏ fail, thay gold hoặc chạy lại riêng câu thất bại để lấy đáp án khác.
