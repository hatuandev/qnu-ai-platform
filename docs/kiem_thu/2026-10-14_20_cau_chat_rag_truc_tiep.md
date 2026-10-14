# Kiểm thử 20 câu — Chat RAG trực tiếp (#441)

## Phạm vi và cách đo

Giữ nguyên primary/fallback/reranker, kho đã xuất bản và bộ câu hỏi. Request chỉ gửi câu hỏi độc lập, không gửi đáp án chuẩn. Artifact cuối: `backend/storage/admissions_eval441_acceptance20.json`; runtime, assistant configuration và publication fingerprint đều không thay đổi trong lượt này. Publication: `733f3faf2f247c16e3a2`, epoch4,20sources. Không reset, upload, reindex hoặc publish.

20/20 HTTP200, không tạo execution_id workflow. Quyết định nội bộ:17supported,2partial,1missing. Đây **không phải tỷ lệ đúng 85% hoặc điểm Ragas**. Đối soát DB:31/31citations canonical khớp raw span và canonical hash, không có reviewed-fact citation trong lượt này. Hash đúng chỉ chứng minh liên kết nguồn, không chứng minh relevance/completeness.

Latency trung bình29,65s (min16,64s,max66,02s). Usage thật ghi105lượt primary gpt-oss:120b và7lượt fallback gemma4:31b thành công. Nhiều bước có repair; bỏ DAG không loại bỏ latency network/LLM. Không tự thay model/provider/timeout để làm đẹp kết quả.

## Ghi nhận từng câu

| ID | Nội dung | Quyết định | Ghi nhận khi đọc câu trả lời |
| --- | --- | --- | --- |
| 1 | Mã trường | supported | DQN, giữ đúng thuật ngữ nguồn “mã cơ sở đào tạo”; không còn từ chối vì nhãn khác |
| 3 | Hotline | supported | 1800.55.88.49 từ nguồn, không dùng hotline gán cứng |
| 5 | Tổng chỉ tiêu2026 | partial | Có5.173 đúng nguồn nhưng báo thiếu “năm2026” dù header/nguồn đã có năm; false partial cần sửa qualifier numeric |
| 6 | Số ngành/chương trình | supported | Giữ53đầu mùa và56mã/ngành/chương trình ở thông báo sau, phân biệt phạm vi, không cộng thành tổng giả |
| 9 | Phương thức xét tuyển | supported | ĐủPT1–PT5 với đặc tính/mã và tuyển thẳng301; section expansion lấy được đoạn liệt kê trước đây bị bỏ |
| 11 | Ngành không xét học bạ | supported | Chính sách nhóm đào tạo giáo viên không dùngPT2; không đòi tên mọi ngành ngoài câu hỏi |
| 13 | Sư phạm dùngĐGNLĐHSPHN | partial | CóPT4/402B nhưng đoạn được chọn chưa giữ chính sách nhóm giáo viên; nguồn thuyết minh có chính sách “một số ngành…phù hợp”; cần cải thiện selection/coverage, không kết luận toàn kho thiếu dữ liệu |
| 16 | Có học bạ và điểmTHPT | supported | Có thể dùng cả hai nếu ngành chấp nhận/đủ điều kiện; không còn diễn giảiPT5 thành thiTHPTđơn thuần |
| 19 | Ngưỡng nguồn học bạ | supported | Đủtổng3môn thi/tổ hợp hoặcToán+Văn+mônkhác,15/30,áp dụng từ2026 và ngoại lệ; không chỉ xuất con số15 |
| 22 | Đăng ký học bạ riêng | supported | Không riêng cổngTrường đợt1, nhưng vẫn bắt buộc nguyện vọng hệ thốngBộ; điều kiện không bị mất |
| 25 | Hệ sốTiếngAnh2026 | supported | Không nhân hệ sốhai; không xem chính sách khác năm là conflict2026 |
| 38 | Điều kiện sư phạm không dùngthiTHPT | missing | Không còn502role proof, nhưng vẫn không tìm đủ ngữ cảnh phương thức. Cần đối soát retrieval/scope; chưa xác nhận thiếu trong toàncorpus |
| 48 | Ưu tiên khi điểm cao | supported | Đủ22,5/30,công thức đúngglyph và giảm dần; còn lặp một câu khi model chọn cả paragraph và sentence con |
| 51 | Lịchnguyện vọng | supported | 02/07–17h00ngày14/07/2026; giữthời giantrong ngày, có thêmđoạn lịchcủaBộ |
| 62 | QuyđổiĐGNL | supported | Nội suytuyến tính theo khoảng bách phânvị và dùngbảng/quy tắccôngbố; không tự suy ra sốđiểm cụ thể |
| 66 | Dùngđiểmchuẩn2025 cho2026 | supported | Dữliệulịch sử đểtham khảo, khôngcamkếttrúng tuyển; giữnăm2025/2026 |
| 75 | Đăngkýbổsung ởđâu | supported | HệthốngtuyểnsinhTrường theoTB151; chưa cungcấpURLcụthể vì đoạn chọn chỉnóiđườngdẫn trongTB, không đoánlink |
| 80 | Họcphítoànkhóa | supported | Cửnhân4năm83–97triệu,kỹsư4nămrưỡi112,3triệu; dựkiếnđầu mùa khácmức thu chínhthức |
| 81 | Cơ hộihọcbổng | supported | Cóquỹkhuyếnkhích/tàitrợ;19đơnvị/226suất/1,57tỷghi rõ2025lịch sử, khônghứa2026/2027 |
| 82 | Hỗtrợsưphạm | supported | Họcphí+3.630.000đ/tháng,tốiđa10tháng/năm,camkếtvàbồihoàn theođiềukiện; phíkhác vẫnđóng |

## Lượt chẩn đoán trước đó không dùng làm nghiệm thu cuối

- `admissions_eval441_probe7.json`:6HTTP200/1timeout; có thay đổi runtime khi chạy, chỉ dùng điều tra.
- `admissions_eval441_chat20.json`:19HTTP200/1scope502;15supported nhưng có lỗi thiếu qualifier/quan hệ trong câu16/19/22. Không gọi15supported là15câu đúng.
- `admissions_eval441_final20.json`:4HTTP200/16ALL_PROVIDERS_UNAVAILABLE; cấu hình/publication/code giữ nguyên. Các503là provider failures, không phải No-Answer do thiếu tài liệu.
- `admissions_eval441_verified20.json`:đã dừng sau6câu để bổ sung expansion theo heading. Không là completed benchmark.

GET9router có timeout trong khi healthBE200. Người dùng xác nhận9router đang chạy và mạng quốc tế thấp. Không reset circuit/key/model tự động ngoài cơ chế đang có của ModelOps. Lượt acceptance cuối đã chạy xong sau phục hồi kết nối.

## Còn lại trước full82

1. **Câu5 — False partial của qualifier**: audit chọn đoạn tổng chỉ tiêu có nhiều số ngày/văn bản để chứng minh riêng “năm2026”; numeric guard đang yêu cầu mọi số của quote đó xuất hiện trong public text. Cần tách numeric atoms của điều kiện thực sự khỏi con số nền của đoạn, vẫn fail closed với giờ/ngưỡng/đơn vị bắt buộc. Không bỏ numeric guard toàn bộ.
2. **Câu13/38 — Retrieval/scope coverage**: câu13 có nguồn chính sách nhóm nhưng context/chọn chứng cứ chưa đủ;38 chưa xác nhận thiếu trong corpus. Cần bounded retrieval repair theo missing applicability tuple, không tạo đáp án từ whitelist domain.
3. **Formatting**: extractive answer bảo toàn nghĩa nhưng có lặpparagraph/sentence con hoặc giữsố thứtự gốc; có thể deduplicate theo cùngsource và span containment, không paraphrase lại điều kiện đã verify.
4. **Hiệu năng và đánh giá**: mạng chậm/kết nối model nhiều bước còn ảnh hưởng latency; chưa chạy82/TM-08. Tách lỗi provider/contract/retrieval/coverage khỏi thiếu dữ liệu thật trong kết quả82.

## Kiểm thử mã

Focus110pass; Ruff pass; Biome6files + Vite/TypeScript build pass. Full1253cases:1227pass/11baselinefail/15skip. Không tuyên bố toànsuite xanh. Chi tiết thay đổi và4bài repo tham khảo tại [nhật ký #441](../nhat_ky/2026-10-14_phien_441_chat_rag_truc_tiep_va_doi_soat_chung_cu.md).
