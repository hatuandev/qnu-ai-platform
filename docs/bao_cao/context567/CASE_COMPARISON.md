# Context567 — Đối chiếu đủ 64 benchmark IDs

Giữ nguyên gold/rubric. `cells` chỉ PASS khi khớp từng tọa độ, giá trị, nhãn phạm vi và citation. Prose cần đủ mọi tiêu chí và không có substantive extras. Negative cần đúng lý do theo nguồn; không đủ nếu chỉ từ chối chung chung. HTTP/schema/timeout là FAIL. Social chấm riêng.

| ID | Nhóm | Context566 | Run1 | Run2 | Cuối Run3 | Phân loại cuối |
|---|---|---|---|---|---|---|
| N01 | scalar | PASS | PASS | PASS | PASS | correct_cells |
| N02 | scalar | FAIL | PASS | PASS | PASS | correct_cells |
| N03 | scalar | PASS | PASS | PASS | PASS | correct_cells |
| N04 | scalar | PASS | PASS | PASS | PASS | correct_cells |
| N05 | scalar | PASS | PASS | PASS | PASS | correct_cells |
| N06 | scalar | PASS | PASS | PASS | PASS | correct_cells |
| N07 | scalar | FAIL | PASS | PASS | PASS | correct_cells |
| N08 | scalar | PASS | PASS | PASS | PASS | correct_cells |
| N09 | scalar | PASS | PASS | PASS | PASS | correct_cells |
| N10 | scalar | PASS | PASS | PASS | PASS | correct_cells |
| N11 | scalar | FAIL | PASS | PASS | PASS | correct_cells |
| N12 | scalar | PASS | PASS | PASS | PASS | correct_cells |
| N13 | scalar | PASS | PASS | PASS | PASS | correct_cells |
| N14 | scalar | PASS | PASS | PASS | PASS | correct_cells |
| N15 | scalar | FAIL | PASS | PASS | PASS | correct_cells |
| N16 | scalar | PASS | PASS | PASS | PASS | correct_cells |
| N17 | other_table | FAIL | PASS | PASS | PASS | correct_source_answer |
| N18 | other_table | FAIL | PASS | PASS | PASS | correct_source_answer |
| N19 | other_table | FAIL | PASS | PASS | PASS | correct_source_answer |
| N20 | other_table | PASS | PASS | PASS | PASS | correct_source_answer |
| M01 | multi | PASS | PASS | PASS | PASS | correct_cells |
| M02 | multi | PASS | PASS | PASS | PASS | correct_cells |
| M03 | multi | FAIL | PASS | PASS | PASS | correct_cells |
| M04 | multi | FAIL | PASS | PASS | PASS | correct_cells |
| M05 | enumeration | FAIL | PASS | PASS | PASS | correct_source_answer |
| M06 | multi | FAIL | PASS | PASS | PASS | correct_cells |
| F01 | followup | PASS | PASS | PASS | PASS | correct_cells |
| F02 | followup | PASS | PASS | PASS | PASS | correct_cells |
| F03 | followup | FAIL | PASS | PASS | PASS | correct_cells |
| F04 | followup | FAIL | PASS | PASS | PASS | correct_cells |
| F05 | followup | FAIL | PASS | PASS | PASS | correct_cells |
| F06 | followup | FAIL | PASS | PASS | PASS | correct_cells |
| F07 | followup | FAIL | PASS | PASS | PASS | correct_cells |
| F08 | followup | FAIL | PASS | PASS | PASS | correct_cells |
| P01 | prose | FAIL | PASS | PASS | PASS | correct_source_answer |
| P02 | prose | PASS | PASS | PASS | PASS | correct_source_answer |
| P03 | prose | PASS | FAIL | FAIL | FAIL | missing_essential_qualifier |
| P04 | prose | PASS | PASS | PASS | PASS | correct_source_answer |
| P05 | prose | PASS | PASS | PASS | PASS | correct_source_answer |
| P06 | prose | FAIL | PASS | PASS | FAIL | false_negative |
| P07 | prose | FAIL | FAIL | FAIL | FAIL | missing_essential_conditions |
| P08 | prose | PASS | PASS | PASS | FAIL | false_negative |
| P09 | prose | PASS | PASS | PASS | PASS | correct_source_answer |
| P10 | prose | PASS | PASS | PASS | PASS | correct_source_answer |
| P11 | prose | FAIL | FAIL | PASS | FAIL | false_negative |
| P12 | prose | PASS | PASS | PASS | PASS | correct_source_answer |
| P13 | prose | FAIL | PASS | PASS | PASS | correct_source_answer |
| P14 | prose | PASS | FAIL | FAIL | PASS | correct_source_answer |
| P15 | prose | PASS | PASS | FAIL | FAIL | contradictory_extra |
| P16 | prose | PASS | FAIL | FAIL | PASS | correct_source_answer |
| X01 | negative | PASS | PASS | PASS | PASS | correct_refusal |
| X02 | negative | PASS | PASS | PASS | PASS | correct_refusal |
| X03 | negative | PASS | PASS | PASS | PASS | correct_refusal |
| X04 | negative | PASS | PASS | PASS | PASS | correct_refusal |
| X05 | negative | FAIL | FAIL | FAIL | FAIL | incomplete_refusal_reason |
| X06 | negative | PASS | PASS | PASS | PASS | correct_refusal |
| X07 | negative | FAIL | FAIL | PASS | PASS | correct_refusal |
| X08 | negative | FAIL | FAIL | FAIL | FAIL | incomplete_refusal_reason |
| X09 | negative | FAIL | FAIL | FAIL | FAIL | incomplete_source_answer |
| X10 | negative | PASS | PASS | PASS | PASS | correct_refusal |
| S01 | social | PASS | PASS | PASS | PASS | correct_social |
| S02 | social | PASS | PASS | PASS | PASS | correct_social |
| S03 | social | PASS | PASS | PASS | PASS | correct_social |
| S04 | social | PASS | PASS | PASS | PASS | correct_social |

## Ca còn FAIL

- **P03**: Đúng thứ tự ba chứng cứ nhưng thiếu giới hạn bản tổng hợp không được vượt chứng cứ gốc; citation hợp lệ chưa đủ.
- **P06**: Nguồn có đủ ngoại lệ nhưng fallback ưu tiên đoạn nhóm chung; dependency group đó chiếm budget và loại đoạn ngoại lệ cụ thể, nên trả insufficient_context.
- **P07**: Nêu phương án, hạn và không miễn an toàn, nhưng bỏ điều kiện vì cơ sở tạm đóng, nhật ký và xác nhận cùng kỳ; thiếu ngoại lệ không áp nhóm A.
- **P08**: Nguồn có quy tắc giữ mã nguyên văn nhưng fallback không tạo được bound claim, nên từ chối quá mức.
- **P11**: Đã tìm đủ hai hàng ngưỡng khác nhau nhưng audit bác sai và yêu cầu thêm chủ đề không được hỏi; chưa trả được câu có đáp án.
- **P15**: Hai mốc chính đúng nhưng tự tuyên bố sắp tăng dần trong khi thứ tự ngày sai; không chấp nhận phần bổ sung mâu thuẫn theo rubric gốc.
- **X05**: Không trả sai số SV theo lớp, nhưng chưa nói rõ nguồn dùng đơn vị SV và chưa có căn cứ quy đổi. Từ chối chung chưa đủ rubric gốc.
- **X08**: Không dùng số dự kiến làm nghiệm thu, nhưng chưa giải thích nguồn chỉ có dữ liệu dự kiến cho năm được hỏi; từ chối chung chưa đủ rubric gốc.
- **X09**: Vẫn chỉ báo chưa đối chiếu chắc các con số, chưa giải thích vì thiếu A nên chưa đủ điều kiện tính; không bịa Q.

## Đối chiếu ID thay đổi

FAIL→PASS: N02, N07, N11, N15, N17, N18, N19, M03, M04, M05, M06, F03, F04, F05, F06, F07, F08, P01, P13, X07.

PASS→FAIL: P03, P08, P15.

Không đưa câu hỏi, response/corpus hay prompt riêng vào Git; exact private proof records ở `backend/storage/context567/benchmark-*/`, hash bộ frozen được ghi trong [báo cáo chính](BENCHMARK_REPORT.md).
