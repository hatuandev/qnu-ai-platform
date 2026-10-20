# Context568 — Đối chiếu64case Qwen/Luna

Cùng code/source/index/query/gold/rubric. Mọi lỗi runtime/schema vẫn FAIL; negative cần đúng lý do, không chỉ không bịa số. Trích dẫn phải khớp canonical nhưng không thay semantic correctness. Không sửa mã sau đọc response.

| ID | Nhóm | Qwen567 | Luna568 | Phân loại Luna |
|---|---|---|---|---|
| N01 | scalar | PASS | PASS | correct_cells |
| N02 | scalar | PASS | PASS | correct_cells |
| N03 | scalar | PASS | PASS | correct_cells |
| N04 | scalar | PASS | PASS | correct_cells |
| N05 | scalar | PASS | PASS | correct_cells |
| N06 | scalar | PASS | PASS | correct_cells |
| N07 | scalar | PASS | PASS | correct_cells |
| N08 | scalar | PASS | PASS | correct_cells |
| N09 | scalar | PASS | PASS | correct_cells |
| N10 | scalar | PASS | PASS | correct_cells |
| N11 | scalar | PASS | PASS | correct_cells |
| N12 | scalar | PASS | PASS | correct_cells |
| N13 | scalar | PASS | PASS | correct_cells |
| N14 | scalar | PASS | PASS | correct_cells |
| N15 | scalar | PASS | PASS | correct_cells |
| N16 | scalar | PASS | PASS | correct_cells |
| N17 | other_table | PASS | PASS | correct_source_answer |
| N18 | other_table | PASS | PASS | correct_source_answer |
| N19 | other_table | PASS | FAIL | false_negative |
| N20 | other_table | PASS | PASS | correct_source_answer |
| M01 | multi | PASS | PASS | correct_cells |
| M02 | multi | PASS | PASS | correct_cells |
| M03 | multi | PASS | PASS | correct_cells |
| M04 | multi | PASS | PASS | correct_cells |
| M05 | enumeration | PASS | FAIL | incomplete_enumeration |
| M06 | multi | PASS | PASS | correct_cells |
| F01 | followup | PASS | PASS | correct_cells |
| F02 | followup | PASS | PASS | correct_cells |
| F03 | followup | PASS | PASS | correct_cells |
| F04 | followup | PASS | PASS | correct_cells |
| F05 | followup | PASS | PASS | correct_cells |
| F06 | followup | PASS | PASS | correct_cells |
| F07 | followup | PASS | PASS | correct_cells |
| F08 | followup | PASS | PASS | correct_cells |
| P01 | prose | PASS | PASS | correct_source_answer |
| P02 | prose | PASS | PASS | correct_source_answer |
| P03 | prose | FAIL | PASS | correct_source_answer |
| P04 | prose | PASS | PASS | correct_source_answer |
| P05 | prose | PASS | PASS | correct_source_answer |
| P06 | prose | FAIL | FAIL | false_negative |
| P07 | prose | FAIL | FAIL | missing_essential_conditions |
| P08 | prose | FAIL | FAIL | false_negative |
| P09 | prose | PASS | PASS | correct_source_answer |
| P10 | prose | PASS | FAIL | false_negative |
| P11 | prose | FAIL | PASS | correct_source_answer |
| P12 | prose | PASS | PASS | correct_source_answer |
| P13 | prose | PASS | PASS | correct_source_answer |
| P14 | prose | PASS | PASS | correct_source_answer |
| P15 | prose | FAIL | PASS | correct_source_answer |
| P16 | prose | PASS | FAIL | false_negative |
| X01 | negative | PASS | PASS | correct_refusal |
| X02 | negative | PASS | PASS | correct_refusal |
| X03 | negative | PASS | PASS | correct_refusal |
| X04 | negative | PASS | PASS | correct_refusal |
| X05 | negative | FAIL | FAIL | incomplete_refusal_reason |
| X06 | negative | PASS | PASS | correct_refusal |
| X07 | negative | PASS | PASS | correct_refusal |
| X08 | negative | FAIL | FAIL | incomplete_refusal_reason |
| X09 | negative | FAIL | PASS | correct_refusal |
| X10 | negative | PASS | PASS | correct_refusal |
| S01 | social | PASS | PASS | correct_social |
| S02 | social | PASS | PASS | correct_social |
| S03 | social | PASS | PASS | correct_social |
| S04 | social | PASS | PASS | correct_social |

## Các ca Luna chưa đạt

- **N19**: Nguồn có giá trị0 thật và ý nghĩa giờ vượt mức nhómA năm2026, nhưng model từ chối và nói thiếu Bảng5.
- **M05**: Không liệt kê được12cặp mã/tên dù nguồn đủ; trả insufficient_context, không tính giữ an toàn là PASS.
- **P06**: Không trả được ngoại lệ E-A; model yêu cầu xác nhận bảng thuộc Phụ lụcII dù nguồn đầy đủ, còn lỗi scope/evidence context.
- **P07**: Đúng biên bản trực tuyến, hạn30ngày và không miễn an toàn nhưng thiếu điều kiện cơ sở tạm đóng, nhật ký và xác nhận giảng viên cùng kỳ; thiếu phạm vi không áp nhómA.
- **P08**: Nguồn có quy tắc giữ nguyên số0 đầu/dấu nối, nhưng hệ thống từ chối, không trả được câu có đáp án.
- **P10**: Từ chối và nói chưa có chú giải dấu gạch dù nguồn xác định CT-05 tạm ngừng đo theo quyết định; không phân biệt đủ với0 có chứng cứ CT-01.
- **P16**: Chưa trả được trạng thái thiếu biến theo nguồn, chỉ từ chối chung dù nguồn có đầy đủ điều kiện tính/xếp loại.
- **X05**: Không trả nhầm số SV thành lớp nhưng từ chối chung, chưa giải thích nguồn là SV và không có phép quy đổi sang lớp.
- **X08**: Không biến dự kiến thành nghiệm thu, nhưng từ chối chung chưa giải thích khác biệt giữa dữ liệu dự kiến và kết quả đã nghiệm thu2027.

## ID thay đổi

FAIL→PASS: P03, P11, P15, X09.

PASS→FAIL: N19, M05, P10, P16.

Không công bố corpus hoặc nội dung riêng trong report; mỗi verdict có source spans/frozen rubric và response evidence ignored. [Báo cáo chính](BENCHMARK_REPORT.md).
