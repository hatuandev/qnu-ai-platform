# Context615 — Chặn gán nhầm ý nghĩa số liệu ở compiler

## Kết quả

Đã sửa lỗi **chấp nhận nhãn số liệu thiếu căn cứ**: số có trong nguồn không còn đủ để xác nhận tên chỉ số do model đặt. Regression trọng tâm đạt **19 PASS**, Ruff 6 tệp PASS. Thử thật chỉ tình huống 5.081, không chạy benchmark 64 câu hoặc compiler toàn bộ ba tài liệu.

Hai lượt thử cùng một câu hỏi đều không còn khẳng định 5.081 là tổng chỉ tiêu tuyển sinh. Tuy nhiên model vẫn thiếu binding nhãn nguồn, có scope không trích nguyên văn và header canonical cũ chưa xác định. **Kết quả thực tế vẫn chưa đạt đầy đủ, không APPROVED**. Không đổi các lỗi còn lại thành PASS chỉ vì đã ngăn kết luận sai.

## Nguyên nhân

Trong Context614, giá trị 5.081 có mặt trong bảng, cùng mô tả về thí sinh trúng tuyển đã nhập học. Compiler gán thành `Total admission quota`/`total_quota`; item review và section review cùng xác nhận nhầm. Kiểm tra cơ học khi ấy kiểm tra nguồn, scope và năm nhưng chưa buộc tên chỉ số/cột khớp vai trò của ô. Lỗi xảy ra trước retrieval chatbot; không có bằng chứng đây là thiếu context 32K hay lỗi truy xuất RAG.

## Thay đổi

- Thêm `compilation_metrics.py`: số liệu từ bảng cần hai scope có trích dẫn riêng `source_metric` và `source_column`; nhãn entity/attribute phải giữ nguyên các nhãn nguồn ấy. Giá trị phải khớp duy nhất một ô, đúng đường header của cột. Không dùng từ điển tên chỉ số hoặc vá riêng số 5.081.
- `metric_binding_targets` đưa context/cột ứng viên cùng proof ID ngay trong gói trích xuất; không nâng ứng viên header thành header đã xác nhận.
- Packet bị chặn khi thiếu binding, đổi tên chỉ số, trích dẫn sai bảng, sai cột, giá trị không có ô duy nhất hoặc header chưa rõ. Giữ nguyên verdict của model trong audit và ghi lỗi cơ học riêng; `supported` của model không vượt được các lỗi này.
- Section phải giữ nguyên nhãn và giá trị đã ràng buộc; phần kiểm tra semantic vẫn cần thiết, vì trùng literal không chứng minh toàn bộ diễn giải đúng.
- Policy mới `qnu-compilation-review/v4`, protocol `literal-table-metric-and-column/v1` tham gia configuration hash. Đọc lại bundle mới dựng lại metadata nguồn trước khi tính verdict. Bundle cũ vẫn đọc theo policy cũ, không sửa checkpoint hoặc giả kết quả review mới.

Phạm vi app: `compilation_runtime_schemas.py`, `compilation_engine.py`, `compilation_validation.py`, `compilation_modelops.py` và tệp mới `compilation_metrics.py`. Thêm `backend/tests/test_compilation_metrics_615.py`; giữ mọi sửa đổi Context608–614.

## Kiểm chứng

| Kiểm tra thực chạy | Kết quả | Exit |
|---|---|---:|
| Regression tái hiện trước sửa, 12 trường hợp đầu | 9 FAIL / 3 PASS, lỗi đều là chấp nhận nhãn/cột/scope sai hoặc bỏ nhãn khi tổng hợp | 1 |
| Regression cuối, chỉ module metric615 | 19 PASS / 0 FAIL, 5,68 giây | 0 |
| So exact test ID | 9 lỗi cũ chuyển PASS; 7 test bổ sung PASS; không mất ID | 0 |
| Ruff 5 app + 1 test | PASS | 0 |
| Tiền kiểm môi trường/corpus/model | DB/MinIO/Qdrant loopback, môi trường development; hash ba DOCX khớp; không đổi model mặc định | 0 |
| Replay riêng lỗi cũ 5.081 | Model cũ supported; guard mới phát hiện binding thiếu và chặn | 0 |
| Lượt thật đầu: trích xuất → review → tổng hợp → review | Hoàn thành 4 inference; không gọi 5.081 là chỉ tiêu; packet/section chưa đạt do binding/scope/header | 0 |
| Lượt thật sau khi làm rõ lựa chọn bằng chứng | 3 inference hoàn tất, harness dừng bởi assert cục bộ khi model đề xuất quan hệ; không có timeout/uncertain | 1 |
| Tiếp tục lượt sau bằng đúng 3 receipt đã hoàn tất | Không gửi lại 3 request; thêm đúng 1 inference review, tổng 4 của lượt này; packet/section vẫn chưa đạt | 0 |

Câu hỏi duy nhất: “Số 5.081 trong bảng Giới tính năm 2025 là số gì? Có phải tổng chỉ tiêu tuyển sinh không?” Đây là kiểm thử đường compiler bằng nguồn thật, **không phải chatbot serving E2E**. Tổng 8 inference mới, cùng `ollama/gpt-oss:120b`, thinking medium, đầu ra 8.192, 8/8 finish=stop, không fallback. Default `gh/gpt-6-luna` giữ nguyên. Ngân sách đầu vào/đầu ra vẫn kiểm trước gọi; một preflight vượt budget đã dừng trước inference, chỉ rút gọn hướng dẫn lặp, không cắt nguồn hoặc tăng cap.

Ở lượt cuối, model không tạo `source_metric`/`source_column`, đồng thời dựng scope “Giới tính năm 2025” không có trích đoạn nguyên văn tương ứng. Dù item/section review nói supported, server giữ `complete=false` với lỗi binding/scope/năm. Vì vậy chỉ nghiệm thu được **cơ chế chặn xác nhận sai**, chưa nghiệm thu khả năng model luôn tạo đúng binding hoặc hiểu đầy đủ số liệu này.

Unit test không dùng DB/provider: chặn kết nối DB/HTTP, Storage local và endpoint DB giả loopback cổng đóng. Có một lỗi fixture ban đầu vì chặn cả socket nội bộ của event loop Windows; đã sửa ranh giới fixture, không sửa assertion để test xanh. Test cuối kiểm cả compile runtime → bundle → đọc kiểm chứng lại bằng model giả; không gọi đó là live E2E.

Artifacts riêng trong `backend/storage/context615`: `baseline.xml`, `focused.xml`, `test-id-comparison.json`, `ruff.log`, các receipt/request/output và `target-final/result-private.json`. Không đưa corpus hay prompt riêng vào Git. Báo cáo full Context614 **3622 PASS / 18 FAIL nền / 17 SKIP** là lịch sử; full backend, 64 câu, compiler toàn tài liệu và FE **NOT RUN** theo yêu cầu chỉ kiểm tình huống nhầm.

## Dữ liệu và giới hạn

DB cấu hình local chỉ đọc đối chiếu metadata nghiệp vụ; inference đi qua ModelOps có bảo vệ và ghi usage/lease bình thường. Không tạo DB thử mới, không migration, không ghi nguồn/collection/index. Hash hàng nguồn, revision, binding, index, assistants và provider/default config trước/sau khớp; hash DOCX không đổi. Không truy cập hay ghi vector trong lượt này; không tuyên bố đã kiểm lại embedding.

Storage local riêng giữ receipt/evidence theo chính sách bảo vệ hiện có; không tắt bảo vệ hoặc xóa cưỡng bức. Không có dữ liệu thử được nạp vào kho nguồn/vector để cần gỡ. Chưa áp lại kết quả vào checkpoint614, chưa reparse, reindex, xuất bản, restart, commit hoặc push.
