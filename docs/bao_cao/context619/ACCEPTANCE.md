# Context619 — Nghiệm thu compiler trên ba DOCX 2024–2026

Ngày24/10/2026. **Kết quả: NOT APPROVED — chưa đạt nghiệm thu toàn compiler.**

Người dùng yêu cầu chốt nghiệm thu để tránh tiếp tục kéo dài. Đã chạy một lượt create hoàn chỉnh bằng service hiện có, không sửa mã ứng dụng hoặc chạy lại full regression. Không đưa đề xuất nguồn/chỉ mục đang phục vụ vào trạng thái approved.

## Phạm vi và bằng chứng

- Giữ ba DOCX2024–2026 và381canonicalproofs, snapshot `59eb474ad57dc88b943504a46bc9cce8c718a302072b309c5c87022bd7f6ef66`.
- Câu nghiệm thu: số5.081 trong bảng Giới tính năm2025 là gì, có phải tổng chỉ tiêu tuyển sinh không.
- GPT-OSS120B qua protected ModelOps, reasoning medium, context128000/outputcapacity64000 phân giải tự động. Default app vẫn gh/gpt-6-luna; không sửa cấu hình DB.
- Một lượt compiler: **39 inference**,0fallback, toàn bộ finish`stop`;2schema rejection được correction theo quy tắc hiện có; max32535input/6951output. Không có lỗi vượt context hoặc output bị cắt.
- Service đã thực hiện chọn bằng chứng, native column review, draft, semantic/coverage review và synthesis. Bị từ chối trong `finish → validate_result → validate_semantic_repair` trước lưu bundle cuối. Job fixture có receipt failed/uncertain theo service; không giả thành completed.

## Các blocker đã xác định

| Mục | Bằng chứng | Tác động |
|---|---|---|
| Sai vai trò năm | Assertion giữ `publication=2025` nhưng proof là heading báo cáo kết quả năm2025, không có ngày công bố. Blind truth review trả `contradicted`, temporal_roles=false. | Không được dùng năm báo cáo như bằng chứng năm công bố. |
| Chọn nhầm bảng có cùng giá trị | Assertion có hiệu lực lấy dòng tổng của bảng phân bố khác (`proof_983ed5da6f5202f0933736b9`). Không có assertion present/5.081 gắn dòng Tổng trong bảng Giới tính (`proof_65fdc58847517d4ab7247676`). Hai coverage classifier bất đồng vai trò của dòng đúng. | Chưa đáp ứng câu nghiệm thu; trùng số không chứng minh cùng bảng/phạm vi. |
| Guard kiểm biên nhận nhầm thông tin coverage | Lỗi `semantic_repair_rejected_candidate_effective`. Replay đối chiếu exact39request/output cho thấy active entity/assertions vẫn bằng initial bị lỗi; chỉ `review` và `coverage_reconciliation` khác sau bước reconciliation hợp lệ trong luồng. | So sánh toàn packet có thể chặn nhầm metadata của bước coverage sau repair. Không chứng minh candidate bị loại đã trở thành dữ liệu có hiệu lực. |

Synthesis review nói supported nhưng không xóa việc blind truth review thất bại. `machine_complete=false` khi tái dựng bằng đúng receipt. Ngay cả khi sửa guard lưu metadata, hai lỗi ngữ nghĩa trên vẫn chặn nghiệm thu; không nới guard rồi coi nội dung đã đúng.

## Đối soát độc lập, không gọi thêm model

Đã tái chạy thuật toán điều phối bằng **39 request/output đã ghi**, kiểm khớp contract, instruction và payload digest của từng bước, gồm hai rejection/correction. **0 inference mới**, không resend job uncertain. Đây là replay chẩn đoán, không phải service result đã lưu thành công hoặc E2E PASS.

Bundle replay được giữ qua LocalStorageDriver làm bằng chứng, không được chấp nhận vào registry/serving. Nó tái hiện đúng lỗi validation, machine_complete=false,1assertion/1section,0assertion đúng cho targetgender5.081. Artifact riêng ở `backend/storage/context619/compiler-live/independent-failure-review-private.json`; raw request/output và replay bundle trong Storage test, không đưa vào Git.

## Kiểm thử và bảo toàn

| Kiểm tra | Kết quả |
|---|---|
| Lượt compiler service end-to-end | **FAIL**, exit1, codeKNOWLEDGE_COMPILATION_INVALID/reasonsemantic_repair_rejected_candidate_effective |
| Replay exact39stage để phân tích | PASS cho tái hiện/chẩn đoán, exit0; không phải nghiệm thu compilerPASS |
| App code so hash trước/sau | PASS, không sửa ứng dụng trong Context619 |
| Nguồn/default/provider/domain seals | PASS, giữ sáu nhóm bảng shared |
| Full regression | Không chạy lại vì app không đổi. Kết quả618 gần nhất3759PASS/18FAIL nền/17SKIP, exactID/cause giữ; vẫn là suiteFAIL lịch sử618 |
| Benchmark64 | NOT RUN |
| Publish/index/serving | NOT RUN; không có hành động ghi vector hoặc publication |

DB/MinIO/Qdrant loopback đã xác minh trước thực thi. Source fixture/registry/Storage trong môi trường riêng; shared DB chỉ đọc domain/config và ghi ModelOpslease/usage vận hành đã được phép. Không migration/restart/source mutation.

Đã dọn database thử nghiệm619 theo nonce sở hữu sau xuất bằng chứng. Storage chứng cứ giữ chính sách bảo vệ; không bypass các thao tác xóa đã bị chặn. Các DB616 cũ giữ nguyên bàn giao trước. Không commit/push/reindex/publish/deploy.

Không tiếp tục mở thêm lượt LLM hoặc sửa code trong phiên nghiệm thu này. Báo cáo chốt phản ánh kết quả thực; phầnspan_id có kiểm chứng618, còn toàn compiler chưa được ghiAPPROVED.
