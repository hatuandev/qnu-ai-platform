# Kiểm thử lại 20 câu RAG/DAG sau khi khởi động BE và worker

## Phạm vi và nguyên tắc

- Thời điểm: 2026-10-14.
- Bộ kiểm thử: 20 câu đại diện `1,3,5,6,9,11,13,16,19,22,25,38,48,51,62,66,75,80,81,82`.
- Mỗi câu chạy trên hai tuyến `DAG` và `RAG`, tổng cộng 40 lượt.
- Nguồn và snapshot xuất bản giữ nguyên; không reset DB, không nạp vector, không xuất bản lại, không đổi model/config.
- Phiên này chỉ quan sát và ghi nhận vấn đề; không sửa code.
- Artifact: [admissions_eval438_smoke20.json](../../backend/storage/admissions_eval438_smoke20.json).

## Kết quả tổng quan

| Tuyến | HTTP 200 | Supported | Partial | Missing | Conflict | Lỗi vận chuyển |
|---|---:|---:|---:|---:|---:|---:|
| DAG | 20/20 | 4 | 11 | 5 | 0 | 0 |
| RAG | 19/20 | 3 | 12 | 3 | 1 | 1 (502) |

`supported` là trạng thái của `answer_decision`, không chỉ là HTTP 200. Nhiều lượt HTTP 200 nhưng bị hạ thành `partial` hoặc `missing` vì lớp kiểm chứng chưa xác nhận đủ các mệnh đề/điều kiện cần thiết.

### Độ trễ và ModelOps

| Tuyến | Nhanh nhất | Trung bình | P95 | Chậm nhất |
|---|---:|---:|---:|---:|
| DAG | 15,95 s | 33,37 s | 43,22 s | 46,72 s |
| RAG | 4,00 s | 27,17 s | 40,28 s | 49,17 s |

- 304 lượt gọi dùng `custom/gpt-oss:120b` thành công; 3 lượt fallback sang `custom/gemma4:31b` và cũng thành công.
- Không ghi nhận lỗi provider/timeout trong `served_models` của artifact.
- Lỗi RAG câu 38 xảy ra sau khi model đã phản hồi: HTTP 502 `EVIDENCE_TARGET_SCOPE_INVALID`, vì câu hỏi không nêu rõ vai trò trường đích; đây là lỗi scope validation của tuyến trực tiếp, không phải lỗi kết nối model.

## Vấn đề cần xử lý (chưa sửa trong phiên này)

### Mức cao — ảnh hưởng khả năng trả lời

1. **Câu 38, RAG bị chặn 502**: câu hỏi “các ngành sư phạm” không ghi rõ trường, trong khi tuyến `/rag/ask` đã có `assistant_code=admissions` và `collection_id`. Cần quyết định quy tắc suy ra trường đích từ trợ lý/kho hay tiếp tục yêu cầu người dùng nêu trường.
2. **Câu 80, cả DAG và RAG đều `missing`**: thông tin học phí số không được binding vào quote (`Numbers are not bound to their own quote`), dù bộ kỳ vọng có khoảng học phí toàn khóa và thời lượng 4/4,5 năm. Đây là lỗi liên kết số liệu–nguồn hoặc truy hồi khối bảng/đoạn chứa số.
3. **Câu 19, cả hai tuyến không trả được ngưỡng 15/30**: kiểm chứng báo `ATOMIC_PROOF_NOT_IN_ATTACHED_QUOTES`/`ATOMIC_COVERAGE_INCOMPLETE` hoặc quote không đơn nghĩa. Cần kiểm tra lại span nguồn cho điều kiện 3 môn và ngoại lệ.
4. **Câu 25, DAG `missing`, RAG `conflict`**: câu hỏi về hệ số 2 không được xác nhận thống nhất; cần đối soát nguồn 2025/2026 và binding phủ định “không nhân hệ số 2”.
5. **Câu 81, DAG `missing`, RAG `partial`**: mới trả được phần “không có cam kết 2026”, chưa giữ được dữ liệu học bổng lịch sử 2025 (19 đơn vị/226 suất/khoảng 1,57 tỷ) kèm nhãn “tham khảo”.
6. **Câu 82, DAG `missing`, RAG `partial`**: RAG giữ được 3.630.000 đồng/tháng và tối đa 10 tháng nhưng thiếu mức học phí tương ứng, đối tượng áp dụng và nghĩa vụ đơn/cam kết bồi hoàn; DAG không chứng minh được các mệnh đề chính.

### Mức trung bình — thiếu ý hoặc phân biệt năm chưa đủ rõ

7. **Câu 5**: DAG cộng thêm 456 chỉ tiêu xét tuyển bổ sung rồi yêu cầu tổng hợp, trong khi câu hỏi/kỳ vọng đang hỏi 5.173 chỉ tiêu đại học chính quy. Đây là vấn đề scope “chỉ tiêu chính quy” và “bổ sung”, không nên tự cộng nếu nguồn không khẳng định tổng.
8. **Câu 6**: cả hai tuyến giữ 53 đầu mùa và 28 bổ sung nhưng không chứng minh được quan hệ “56 mã xét tuyển/chương trình” hoặc 53+28 có trùng/không trùng. Cần trả lời rõ 53, 56 và 28 là các đơn vị đếm khác nhau.
9. **Câu 9**: chỉ trả được PT301/ xét tuyển thẳng; chưa liệt kê đủ PT1–PT5 (đặc biệt PT3, PT4, PT5) và mã/phạm vi tương ứng.
10. **Câu 11**: xác nhận chung “ngành đào tạo giáo viên không xét PT2” nhưng kiểm chứng yêu cầu danh sách ngành và PT5; cần tránh biến câu hỏi tổng quát thành yêu cầu liệt kê quá mức nếu nguồn không có danh sách đầy đủ.
11. **Câu 13**: DAG đạt `supported` nhưng chưa nêu ngoại lệ Giáo dục Mầm non/Giáo dục Thể chất dùng phương thức năng khiếu; RAG bị `partial` do quote qualifier. Cần giữ cả câu trả lời “có PT4” và ngoại lệ ngành.
12. **Câu 16**: nội dung trả lời chính phù hợp (“có thể dùng cả hai nếu ngành cho phép”), nhưng audit yêu cầu thêm bảng quy đổi, hạn đăng ký và danh sách ngành nên hạ `partial`. Đây là dấu hiệu coverage đang quá rộng so với intent câu hỏi.
13. **Câu 22**: RAG đạt `supported`; DAG thiếu qualifier “đợt 1”. Cần thống nhất cách gắn phạm vi thời gian mà không tạo false partial.
14. **Câu 48**: DAG đạt `supported`; RAG chỉ giữ công thức, bị thiếu ngưỡng 22,5/30 và phạm vi ưu tiên do binding số/qualifier không đồng nhất giữa hai tuyến.
15. **Câu 62**: cả hai `partial`; câu trả lời an toàn nhưng thiếu bảng bách phân vị/công thức chi tiết. Cần phân biệt rõ “không có công thức chung để tự tính” với “mô tả nội suy trong quy tắc chính thức”.
16. **Câu 66**: cả hai giữ được thông điệp “điểm 2025 chỉ tham khảo”, nhưng audit vẫn `partial` vì thiếu qualifier 2026/thang điểm khác nhau. Đây là lỗi completeness/quote, không phải nên suy diễn điểm chuẩn 2025 thành dự báo 2026.
17. **Câu 75**: DAG đạt `supported`; RAG bị `partial` vì yêu cầu URL cụ thể dù nguồn chỉ nói đường dẫn được công bố trong thông báo. Cần để mức thiếu URL phản ánh đúng nguồn, không tự bịa URL.

### Vấn đề xuyên suốt

- Candidate selection của một số câu 2026 vẫn kéo tài liệu 2025 vào (thấy rõ ở câu 1, 3, 5, 6, 11, 13, 25). Với câu 66, năm 2025 là chủ đích lịch sử; các câu còn lại cần lọc/giảm trọng số tài liệu cũ trước khi audit.
- Nhiều câu có quote đúng nhưng `binding_rejections` kiểu `QUALIFIER_QUOTE_INVALID`, `ATOMIC_SPAN_NOT_IN_CLAIM` hoặc “Numbers are not bound to their own quote”; điều này làm câu trả lời an toàn bị hạ `partial/missing`.
- Độ trễ P95 trên 40 giây ở cả hai tuyến; cần theo dõi riêng thời gian planning/retrieval/verification và số lần fallback trước khi chạy toàn bộ 82 câu.

## Trạng thái thay đổi

- `code_unchanged=True`.
- `configuration_unchanged=True`.
- `publication_unchanged=True`.
- Không có thao tác dữ liệu ngoài việc tạo artifact kiểm thử.

## Đề nghị cho vòng kế tiếp

1. Ưu tiên xử lý lỗi 502 scope câu 38 và binding số liệu câu 19/25/80/82.
2. Kiểm tra temporal filtering cho truy vấn 2026 nhưng vẫn giữ lịch sử có chủ đích như câu 66/81.
3. Chuẩn hóa tiêu chí `supported/partial` theo intent, tránh yêu cầu các ý ngoài câu hỏi làm false partial.
4. Chỉ sau khi các nhóm trên ổn định mới chạy toàn bộ 82 câu và tính Ragas.

## Đối soát nguyên nhân sâu hơn — phiên #439

Đọc lại `contexts`, `repair_history`, `semantic_audit` trong artifact #438 và mã xử lý hiện tại. Đối chiếu artifact #435 xác nhận publication fingerprint vẫn là `733f3faf2f247c16e3a2`, nguồn/revision không đổi. Các nhận xét dưới đây cụ thể hóa nguyên nhân; không chạy thêm model hoặc sửa runtime.

| Trường hợp | Bằng chứng đã quan sát | Điểm thất bại |
|---|---|---|
| 1: mã trường | Context chứa câu QNU dùng mã cơ sở đào tạo DQN | RAG audit không chấp nhận diễn đạt mã trường/mã cơ sở đào tạo; qualifier dùng source revision ID thay block ID. Dữ liệu đã được tìm thấy. |
| 3: hotline | DAG trả đúng 1800 55 88 49 từ thuyết minh | Bị partial do qualifier năm/tên trường không bind được, không phải thiếu số điện thoại. |
| 5: chỉ tiêu | Context có 5.173 chính quy, thay mức 4.500 | Audit/generation xử lý sai phạm vi: yêu cầu tổng hợp thêm 456 bổ sung hoặc bắt lặp lại qualifier dù đã có nguồn. |
| 6: ngành/chương trình | Context có nguyên đoạn phân biệt 53 đầu mùa và 56 mã cập nhật | Trả lời bỏ 56, đưa thêm 28 ngành bổ sung rồi audit đòi chứng minh tổng/không trùng. Lỗi sinh nội dung và xác định coverage. |
| 9: phương thức | #435 có đủ PT1–PT5 của TB cập nhật trong cùng publication; #438 chủ yếu có headings, mã301 và đoạn dùng nhiều phương thức | Lỗi lựa chọn/đóng gói context. Quote repair không thể bù danh sách không được đưa vào context. |
| 11/16/66 | Context và câu trả lời giữ được quy tắc nhóm ngành hoặc thông điệp chính | Audit đòi thêm danh sách ngành, bảng quy đổi/hạn đăng ký hoặc thang điểm ngoài yêu cầu chính; gây false partial. |
| 19: ngưỡng nguồn | RAG context có đủ PT2, đối tượng từ2026, tổng ba môn, 15/30 và ngoại lệ | Quote binding không khớp span; DAG có thêm lỗi atomic proof/coverage. Không thiếu điều kiện nguồn trong context. |
| 25: tiếng Anh | Context có chính sách 2025 nhân hệ số2 và câu2026 không nhân hệ số hai | Temporal scope chưa ngăn mâu thuẫn khác năm. DAG còn numeric binding; validator chữ số không hiểu số bằng chữ là hạn chế đáng kiểm tra, nhưng artifact không giữ raw proposal cuối nên chưa chứng minh đó là nguyên nhân duy nhất. |
| 38 | RAG model calls thành công, sau đó mã `EVIDENCE_TARGET_SCOPE_INVALID` | Model trả role basis/target quote không hợp lệ và backend trả502 ở bước scope. Không thể quy lỗi này cho dữ liệu hoặc yêu cầu người dùng tự nêu trường khi persona có trường đích. |
| 48/82 | Context có ngưỡng22,5 và đầy đủ hỗ trợ/cam kết/bồi hoàn | Sinh câu trả lời thiếu điều kiện thật, đồng thời audit cũng lỗi copied spans/qualifier references. Không nên chấm mọi partial là lỗi dữ liệu. |
| 80: học phí | Context có 83–97 triệu,112,3 triệu, toàn khóa, thời lượng bằng chữ, tính dự kiến | Numeric binding và atomic coverage chặn nội dung. Chưa có raw proposal cuối để xác định số nào gây numeric rejection. |
| 81: học bổng | Context ghi rõ có học bổng và số liệu lịch sử2025 kèm cảnh báo không cam kết2026/2027 | Atomic proof dùng quote ngoài trích dẫn gắn claim hoặc copy không nguyên văn; có dữ liệu nhưng bị loại. Số liệu lịch sử không bắt buộc cho câu hỏi chỉ hỏi có học bổng không. |
| 75: bổ sung | Đoạn nguồn chỉ nói đường dẫn ghi trongTB151, không chứaURL | Thiếu URL cụ thể là gap trong đoạn được chọn; vẫn có căn cứ trả nơi đăng ký. Chưa kết luận toàn bộ corpus không cóURL. |

### Hai chiều sai của kiểm chứng

- False negative: câu1/3/11/16/66 có ý chính được chứng minh nhưng báo thiếu/partial do qualifier tự mở rộng, sai block ID hoặc quote bị viết lại.
- False positive về completeness: câu22 RAG được `supported` nhưng bỏ bước đăng ký nguyện vọng bắt buộc trên Hệ thống Bộ; câu13 DAG `supported` nhưng thiếu giới hạn một số ngành và ngoại lệ năng khiếu. `supported` không thay thế chấm nội dung độc lập.
- `AUDIT_INSTRUCTION` hiện đã yêu cầu không tự cộng các đợt, không đòi mọi tên ngành và không thêm subquestions; artifact vẫn có các hành vi đó. Chỉ sửa prompt không đủ bảo đảm model tuân thủ.
- `audit_coverage` yêu cầu atomic spans phủ toàn bộ ký tự chữ/số của claim, `bind_quote` yêu cầu block ID và quote thật. Model tạo `...`, đổi chữ/Unicode hoặc dùng revision ID thì validator loại. Quy tắc an toàn có mục đích đúng, nhưng hợp đồng đầu ra model và cách xác nhận completeness chưa ổn định.

### Độ trễ nằm chủ yếu ở kiểm chứng

Trong các lượt có trường timing, verification trung bình khoảng19,81s DAG/19,26s RAG; retrieval khoảng1,84s/1,80s. Verification bao gồm audit và vòng repair. Đây là bằng chứng nên ưu tiên ổn định hợp đồng kiểm chứng, giảm repair vô ích trước khi tối ưu tốc độ BM25.

Các kết luận là từ nội dung canonical đã được ghi trong artifacts và mã xử lý, không phải xác minh pháp lý bên ngoài, không phải độ chính xác toàn bộ82 câu. Chưa có chứng cứ rằng các lỗi này chủ yếu do max_tokens5000 hoặc do upstream context window.
