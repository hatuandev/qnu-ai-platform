# Kiểm thử 20 câu RAG và DAG sau khi thêm văn bản thuyết minh

## Kết luận

Tài liệu **QNU_TuyenSinh_2026_VanBanThuyetMinh** đã xuất bản và được truy xuất, trích dẫn thật. Đã hoàn thành 20 câu đại diện trên cả DAG và RAG, tổng 40 lượt. Không có HTTP lỗi hoặc quota chặn. **Chưa nghiệm thu chất lượng**: còn một đáp án RAG sai rõ ràng về phương thức, thiếu điều kiện quan trọng và những câu có nguồn nhưng bị từ chối.

Nên sửa lỗi ngữ nghĩa và truy xuất theo ngữ cảnh trước, chạy lại nhóm hồi quy rồi mới chạy toàn bộ 82. Không lấy 32 lượt `answered` làm tỷ lệ đúng.

## Phạm vi và dữ liệu

Lượt mới từ 10:34:01 đến 10:44:12 ngày 14/10/2026, UTC+7. Các câu giữ nguyên từ bộ 82, IDs: 1, 3, 5, 6, 9, 11, 13, 16, 19, 22, 25, 38, 48, 51, 62, 66, 75, 80, 81, 82. Đây là 20 câu đại diện, không phải 20 câu đầu.

- [Bộ 82 câu](./82_cau_hoi_chatbot_tuyen_sinh.md).
- [Kết quả đầy đủ gồm câu hỏi, đáp án, trích dẫn, quyết định, traces và usage](../../backend/storage/admissions_eval435_smoke20.json).
- [Đối soát kỹ thuật và thống kê](../../backend/storage/admissions_eval435_audit.json).

Expected answers chỉ dùng để đối chiếu cục bộ, không gửi vào yêu cầu/chatbot. Tài liệu tổng hợp được biên tập từ chính bộ hỏi đáp nên bài test này là kiểm thử truy xuất, bám nguồn và hồi quy, **không phải đánh giá độc lập khả năng tổng quát hóa**. Đáp án tham chiếu cũng không thay thế nguồn chính thức: câu 62 có công thức nội suy thật trong văn bản quy đổi nên không chấm sai chỉ vì FAQ khuyên dùng bảng chính thức.

Kho `col_admissions`, epoch 4, 20 nguồn; nguồn mới binding `bnd_9da34f16ef75`, revision `ks_rev_aae30aac628c`, index `idx_rev_ec8a7677282b`, canonical SHA-256 `78598a325c3e36879b0e0d6f341c6af965dbd31c9c1657f822b2084e01babefd`. Snapshot fingerprint `733f3faf2f247c16e3a2`. Tài liệu mới xuất hiện trong citations của 20/40 lượt.

Primary `ollama/gpt-oss:120b`, fallback `ollama/gemma4:31b`, cùng provider 9router đã cấu hình; temperature 0,2, max_tokens 5000. Reranker không đổi. Giữ quy tắc năm hiện tại và ưu tiên TB1906 cùng ngữ cảnh. Không sửa nguồn, model, cấu hình, quota, index hay publication trong lượt; chat tạo hội thoại, trace và usage thông thường.

## Số liệu vận hành

| Chỉ số | DAG | RAG trực tiếp |
| --- | --- | --- |
| Lượt | 20 | 20 |
| HTTP 200 | 20 | 20 |
| answered | 16 | 16 |
| insufficient_context | 4 | 4 |
| Trung vị thời gian | 15,23 giây | 11,37 giây |
| Trung bình thời gian | 17,03 giây | 13,43 giây |
| Cao nhất | 34,42 giây | 34,17 giây |

125 usage logs thành công: 123 GPT-OSS và 2 Gemma fallback (câu 9 và 22, RAG). Đã quan sát fallback thật, nhưng chưa phải bài thử chịu lỗi có kiểm soát. Tổng prompt+completion ghi nhận 939.393 tokens; chi phí theo usage logs 0,180357 USD, không phải xác nhận hóa đơn upstream.

34/34 quyết định supported/partial có claim bindings vượt kiểm tra digest, numeric/entity binding và tương ứng citations. 57/57 citations canonical khớp đoạn `source_markdown[start:end]`, hash đúng. Các kiểm tra này không chứng minh entailment, completeness hoặc ngữ cảnh nghiệp vụ; câu 16 là phản ví dụ rõ ràng. Cấu hình, publication và tập file runtime mà harness theo dõi không đổi. Không chạy Ragas hoặc test đủ 82.

## Đối soát từng câu

“Thiếu” là thiếu điều kiện/phạm vi ảnh hưởng đến cách hiểu, không phải chấm theo độ dài. “Không trả” là no-answer; có chỉ dẫn chung trong tài liệu mới nhưng context/verifier chưa trả được. Câu trả lời được đối chiếu với canonical đã xuất bản và quotes trong report, không phải xác minh pháp lý độc lập.

| Câu | DAG | RAG | Nhận xét nội dung |
| --- | --- | --- | --- |
| 1. Mã trường | Đúng DQN | Đúng DQN | Nguồn TB1906, ghi rõ 2026. |
| 3. Hotline | Đúng | Đúng | 1800.55.88.49 từ nguồn cập nhật, không dùng hotline cũ. |
| 5. Chỉ tiêu | Đúng 5.173 | Đúng 5.173 | Dùng số cập nhật, không trả 4.500 đầu mùa. |
| 6. Ngành/chương trình | Thiếu | Thiếu | Chỉ 53; DAG nói đầu mùa, RAG bỏ qualifier này. Cả hai thiếu phân biệt 56 mã xét tuyển ở thông báo sau. |
| 9. Phương thức | Đúng đầy đủ | Đúng đầy đủ | PT1–PT5/mã405 và tuyển thẳng/mã301 đều có; lỗi bỏ PT5 trước đây không xuất hiện ở lượt này. |
| 11. Ngành không học bạ | Không trả | Đúng | DAG chọn danh sách phương thức 2025; verifier loại vì không chứng minh 2026. Nguồn 2026 có câu trực tiếp về ngành đào tạo giáo viên. |
| 13. Sư phạm xét ĐGNL ĐHSP Hà Nội | Suy rộng/thiếu điều kiện | Không trả | Cả hai plan đặt target_institution=ĐHSP Hà Nội, exam_organizer=null thay vì QNU nhận điểm. DAG chỉ quote quy định PT4 chung để khẳng định ngành sư phạm, thiếu ngành phù hợp và ngoại lệ GDMN/GDTC. |
| 16. Chọn học bạ hay THPT | Nội dung chính đúng, bị partial | **Sai** | DAG xác nhận dùng PT1/PT2 nếu ngành cho phép, nhưng thêm footer cần đối soát. RAG gán PT3/ĐGNL cho điểm THPT và verifier vẫn cho qua. |
| 19. Ngưỡng nguồn học bạ | Đúng số, thiếu điều kiện | Đúng số, thiếu điều kiện | Nêu 15/30 nhưng không nói là tổng điểm thi THPT, đối tượng từ 2026, ngoại lệ và ngưỡng riêng của ngành. Dễ bị hiểu thành điểm học bạ. |
| 22. Đăng ký học bạ riêng | Đúng ý chính, thiếu bước bắt buộc | Đúng đầy đủ | DAG nói không cần cổng trường nhưng bỏ đăng ký nguyện vọng trên Cổng Bộ; RAG giữ cả hai ý. |
| 25. Tiếng Anh hệ số hai | Đúng | Đúng | Nguồn mới, đúng hai ngành và năm. |
| 38. Điều kiện sư phạm không dùng kết quả THPT xét tuyển | Không trả | Không trả | Tài liệu có mục PT4/học lực/18 điểm và ngoại lệ GDTC. Cần phân biệt điểm dùng xét tuyển với điểm THPT dùng kiểm tra điều kiện đầu vào. Không suy rộng một phương thức thành mọi phương thức. |
| 48. Ưu tiên khi điểm cao | Đúng công thức, thiếu ngưỡng | Không trả | DAG bỏ mốc áp dụng từ 22,5/30. RAG lỗi exact-quote: `Quote must match one unambiguous source span`. |
| 51. Lịch nguyện vọng | Đúng ngày, thiếu giờ chốt | Đúng đầy đủ | DAG bỏ 17 giờ ngày 14/07; RAG giữ 02/07–17:00 14/07/2026. RAG phân năm vào event_years, không phải lỗi mất năm. |
| 62. Công thức quy đổi | Có chứng cứ, thiếu hướng dẫn phạm vi | Không trả | DAG quote nội suy tuyến tính theo từng khoảng giữa hai mốc bách phân vị trong khung quy đổi 2026. Cần nói phải dùng đúng bảng/mốc/phương thức, không công thức tùy ý cho mọi trường hợp. RAG EVIDENCE_NOT_SUPPORTED. |
| 66. Điểm chuẩn 2025 đảm bảo đậu 2026? | Đúng | Đúng | Hai năm giữ nguyên; chỉ tham khảo, không khẳng định đậu. |
| 75. Nơi đăng ký bổ sung | Ý chính đúng, partial | Đúng theo phạm vi nguồn | Trực tuyến theo TB151; không bịa URL khi nguồn không có URL cụ thể. DAG còn đề xuất địa chỉ trường không liên quan rồi bị loại, dẫn footer partial dù ý chính đã trả. |
| 80. Học phí | Đúng mức dự kiến | Đúng mức dự kiến | Toàn khóa 83–97 triệu/112,3 triệu. RAG giữ 4/4,5 năm, DAG bỏ thời lượng. Cần nhắc mức thu thực tế theo thông báo tài chính khi tư vấn sâu. |
| 81. Học bổng | Đúng ý chính | Đúng, tách lịch sử | RAG không biến số liệu 2025 thành cam kết suất/giá trị 2026. Chưa thử yêu cầu tra cứu riêng số liệu 2025. |
| 82. Hỗ trợ sư phạm | Đúng số, thiếu điều kiện đầy đủ | Đúng số, thiếu điều kiện | 3.630.000/tháng và tối đa 10 tháng. DAG thêm đơn/cam kết; RAG bỏ cụm mỗi năm học, điều kiện hưởng và cam kết/bồi hoàn. Không trình bày như quyền tự động của mọi SV sư phạm. |

## Lỗi ưu tiên và phương án đề xuất

### 1. Verifier cho qua mệnh đề sai dù quote đúng

Câu 16 RAG có claim “PT3 ... đánh giá năng lực, phù hợp khi có điểm thi THPT”. Quote chỉ chứng minh PT3 dùng ĐGNL ĐHQG TP.HCM. Verifier giải thích sai rằng ĐGNL là “THPT exam” và gán entailed=true. Đây là lỗi ngữ nghĩa ở proposal/verification, **không phải trích dẫn giả hay chỉ riêng BM25**.

Đề xuất tách claim theo từng mệnh đề quan hệ: phương thức → loại kết quả → đơn vị tổ chức → điều kiện áp dụng. Kiểm chứng tất cả vế, không chỉ vế đầu; một vế không có chứng cứ phải loại hoặc sửa có giới hạn. Đánh giá verifier độc lập/cross-model nếu cần, nhưng không tự đổi model của người dùng hoặc hardcode PT1/PT3 vào runtime. Có thể dùng trường hợp 16 làm regression, không đưa đáp án benchmark vào prompt nghiệp vụ.

### 2. Nhầm trường đích với đơn vị tổ chức thi

Câu 13 plan cả hai luồng đặt ĐHSP Hà Nội là target_institution. RAG verifier vì vậy kiểm sai bài toán “ĐHSP Hà Nội tự xét tuyển”, thay vì QNU nhận điểm kỳ thi do ĐHSP Hà Nội tổ chức. Đề xuất giữ scope trường đích của assistant, tách vai trò đơn vị tổ chức từ quan hệ ngữ nghĩa; giữ nguyên ý định câu gốc qua rewrite/DAG.

### 3. Cửa sổ ngữ cảnh và độ đầy đủ

Câu 11 DAG context gồm sáu block phương thức 2025 và các đoạn ưu tiên nguồn 2026 trang 10, không có đoạn trực tiếp từ văn bản mới. Verifier từ chối dữ liệu 2025 là hành vi an toàn; lỗi là lựa chọn/đóng gói context không đưa được chứng cứ 2026 thích hợp. Đề xuất kiểm coverage theo entity/attribute/method/year trước khi pack; không để nhóm liệt kê sai năm hoặc ưu tiên nguồn không liên quan chiếm chỗ. Không dùng năm file/ban hành làm data_year cho mọi đoạn.

Câu 6/19/22/48/51/82 còn thiếu số liệu so sánh hoặc điều kiện. Đề xuất giữ qualifier cùng câu/đoạn cha và kiểm completeness của các ràng buộc đi kèm: ngưỡng áp dụng, đối tượng, loại điểm, giờ chốt, mỗi năm học, ngoại lệ. Giữ raw quote; không nới matching để che lỗi công thức câu 48. Bound theo span ID/offset đã có, có repair giới hạn cho format/layout nhưng không sửa dấu/toán tử một cách tùy tiện.

### 4. Phân biệt partial thật và claim thừa bị loại

Câu 16 DAG/75 DAG đã trả ý chính nhưng bị partial vì một claim thêm không được xác minh. Cần đánh giá lại coverage theo yêu cầu gốc sau khi loại claim thừa, không tự động coi mọi rejected claim là phần câu hỏi còn thiếu. Giữ no-answer khi dữ kiện cần thiết thực sự thiếu.

## Bước tiếp theo

Chưa sửa runtime trong phiên kiểm thử. Sau khi thống nhất, xử lý ưu tiên 1–3 và partial, kiểm thử lại cùng nhóm 20 cùng các diễn đạt khác, thêm câu hỏi riêng về dữ liệu 2025/historical và câu thực sự thiếu nguồn. Khi nhóm hồi quy đạt, chạy đủ 82 và chấm theo căn cứ, không ép 82/82 phải trả lời. Giữ bản xuất bản hiện tại; không cần reset DB.
