# Phiên 446 — Review độc lập mã RAG và full 82 câu

Ngày: 14/10/2026 (Asia/Bangkok).

## Phạm vi

Theo yêu cầu review sau các phiên 444/445. Đọc diff runtime, regression mới, hai nhật ký và toàn bộ đáp án của bốn artifact `admissions_eval445_phase*.json`. Không sửa mã nghiệp vụ/test/runner, không gọi model, không chạy lại chat 82 câu, không đổi cấu hình, reset, reindex, publish hoặc tiếp tục backup. Chỉ bổ sung tài liệu review và đồng bộ bộ nhớ/mục lục.

Skill clean-code hướng dẫn giữ review có phạm vi và tái hiện hành vi; skill RAG hướng dẫn tách toàn vẹn trích dẫn khỏi độ đúng, đủ và phạm vi. Đã đọc thêm skill backend để đối chiếu exception/verification. Không tự dùng model/hotline minh họa trong skill thay cấu hình DB hoặc dữ liệu đã xuất bản.

## Kết quả xác minh độc lập

| Giai đoạn | Câu | supported | partial | conflict | missing | Trích đoạn canonical | Dòng fact |
|---|---:|---:|---:|---:|---:|---:|---:|
| 1 | 20 | 18 | 2 | 0 | 0 | 66 | 0 |
| 2 | 20 | 17 | 3 | 0 | 0 | 57 | 2 |
| 3 | 20 | 17 | 2 | 1 | 0 | 43 | 1 |
| 4 | 22 | 20 | 1 | 0 | 1 | 56 | 0 |
| Tổng | 82 | 72 | 8 | 1 | 1 | 222 | 3 |

- Đủ 82 ID duy nhất 1–82, không thiếu/nhân đôi; 82 HTTP 200, không execution DAG.
- Trung bình 20,779 giây, cao nhất 34,03 giây. Đây là quan sát của một lượt, không chứng minh SLA hay cải thiện hiệu năng do thuật toán.
- Chạy lại `scripts.verify_evidence_report` trên cả bốn artifact, đọc snapshot DB đã pin: **222 canonical citations + 3 reviewed facts khớp**, failures rỗng cả bốn lần. Tổng **225 citations**, không phải “225 spans + 3 facts” như nhật ký 445 ghi. Số liệu nhật ký 445 đếm dư ba trích đoạn; không sửa đè lịch sử.
- 88 regression có sẵn đạt: `test_evidence_quality_444`, `test_evidence_priorities_443`, `test_evidence_completeness_437`, `test_evidence_claims`. Chạy với basetemp riêng `storage/pytest446_review`, không đụng thư mục pytest bị khóa cũ.
- Ruff `app/modules/rag` và `tests/test_evidence_quality_444.py` đạt. Không chạy full suite/FE build trong review này. Số 1276 pass/11 baseline fail/15 skip là kết quả do phiên 445 ghi, không tuyên bố đã chạy lại độc lập ở 446.

### Đúng phiên bản kiểm thử

- Cả bốn giai đoạn có cùng code fingerprint `5188ed58a9644efaf0022634a0db2a4ba25ce6f78e8f02e3e8b99b6bf41a5c75`, cùng configuration fingerprint `d44d96c4f2a9646a212d33470690dd9da590d6293bbf665a149bfddb00043e1b`, publication `733f3faf2f247c16e3a2`, các cờ unchanged đều true.
- Mã hiện tại có fingerprint `1bd743e6f74358de143380f43d14506f7c4d8839f0ec9d835416014292d2df0f`.
- Tính hash giả định trong bộ nhớ, chỉ bỏ bản vá loại dòng dẫn kết thúc bằng `:` và hai dòng comment trong `formula_legend_gap`, cho hash trùng chính xác `5188...`. Không ghi/sửa file khi tính hash.
- Vì vậy **toàn bộ 82 câu là trước bản vá legend-intro cuối**, không phải full acceptance cho mã hiện tại. Không có bằng chứng trộn phiên bản giữa bốn giai đoạn. Probe Q62 sau vá được nhật ký nhắc nhưng không có artifact riêng trong các file 444/445 đã tìm thấy; regression hiện tại không thay thế acceptance thực tế có lưu kết quả.

## Findings cần xử lý trước khi chấp nhận bản vá

### F1 — P1: Numeric auto-retain có thể bỏ điều kiện thật và nâng incomplete thành complete

Vị trí: `evidence_audit.py:131–150`, `:168–169`, `:186–191`.

`_advisory_missing` chỉ so tập số và việc số có xuất hiện trong câu hỏi. Nó không chứng minh yêu cầu là ngoài ý định. Khi người dùng hỏi tổng bằng lời, claim chỉ nêu 53 và 28 riêng rẽ, audit báo “Missing total for 53 and 28 majors”, missing bị xóa và complete trở thành true. Câu hỏi đã yêu cầu tổng dù không chứa chữ số. Không kết luận trường hợp Q6 thật cần cộng; tình huống đối chứng chứng minh thuật toán tổng quát không phân biệt được hai ý định.

Tái hiện thứ hai: nguồn có “Điểm tối thiểu là 18.” và “Chỉ thí sinh thuộc nhóm A được áp dụng mức điểm 18.”; claim chỉ trích câu đầu, qualifier có retained_by rỗng. Auto-retain value_constraint lấy số 18 có sẵn làm chứng minh cho cả điều kiện “chỉ nhóm A”; kết quả complete=true, missing=[] mặc dù giới hạn nhóm đã bị bỏ. Atomic check câu đầu vẫn đúng nguồn, nên không kiểm tra được phần điều kiện không được đưa vào claim.

Ngoài ra return cuối không còn sử dụng `audit.complete`. Với audit.complete=false, missing=[], qualifier=[], một claim hợp lệ về một phương thức vẫn trả complete=true cho câu hỏi liệt kê toàn bộ. Mô hình có thể trả incomplete mà chưa mô tả missing; không được coi đó là chứng minh complete.

Hướng đề xuất: coverage/qualifier phải có liên kết quan hệ, phạm vi, đơn vị, phủ định và ý định, không chỉ tập số. Giữ kết luận incomplete hoặc kiểm chứng lại có giới hạn khi audit không nhất quán; chỉ loại yêu cầu ngoài câu hỏi khi có bằng chứng về ý định. Không hạ guard để tăng supported.

### F2 — P1: Công thức không thuộc dependency group gây AttributeError

Vị trí: `evidence_validation.py:70–73`.

Fallback của `groups.get` là `[references[0]]` (dict), nhưng vòng lặp truy cập `member.id`/`member.text` như EvidenceBlock. Tái hiện bằng tài liệu có tiêu đề “Formula:” không đánh số, đoạn `𝒀 = 𝑿 + 1` và một đoạn giải thích: `formula_legend_gap` ném `AttributeError: 'dict' object has no attribute 'id'`. Hàm được gọi trực tiếp từ verify_bound_answer nên lỗi có thể thoát thành lỗi máy chủ ở chat.

Regression hiện tại chỉ kiểm công thức dưới mục “3.”, nên không phủ trường hợp không có group. Thêm ca standalone và cấu trúc heading/LaTeX/ASCII; absence of group cần có hành vi typed, an toàn, không tự suy ra đủ legend.

### F3 — P2: Một URL chung bất kỳ làm mất gap của đường dẫn đăng ký riêng

Vị trí: `evidence_constraints.py:26–29`.

Chỉ cần ANY quote ở ANY claim có URL, hàm trả false trước khi đối chiếu đường dẫn có thuộc hành động/đợt/nguồn được hỏi không. Tái hiện: claim “Register using the link in notice 151/TB-HĐTS” báo gap=true; thêm claim “General information portal: https://example.org” báo gap=false dù vẫn thiếu link đăng ký.

Q75 thật được marked supported nhờ câu trỏ đường dẫn trong thông báo và câu hotline/cổng chung. URL không bị bịa, nhưng câu hỏi “Đăng ký xét bổ sung ở đâu?” vẫn chưa có locator đăng ký cụ thể và không nói rõ chưa biết link đó. Không đồng nhất tính đúng của cổng liên hệ với độ đầy đủ của đường dẫn đăng ký.

Hướng đề xuất: bind locator với tuple hành động/nguồn/đợt. Cổng chung có thể là hướng dẫn hỗ trợ đúng phạm vi, nhưng không tự xóa missing cho locator cụ thể. Không xây URL suy đoán.

### F4 — P2: Nối câu chưa bảo đảm liền kề trong cấu trúc gốc

Vị trí: `evidence_dependencies.py:150–161`.

Hàm lọc bỏ container và các block khác section trước khi xác định “khối kế tiếp”; chỉ kiểm following.start không nhỏ hơn previous.end, không kiểm gap hoặc vị trí cây gốc. Tái hiện bằng cùng source/section, một container giữa câu dở và đoạn chữ thường cách 1000 ký tự: vẫn trả đoạn xa là continuation. Chữ thường/dấu câu không chứng minh các đoạn thực sự tiếp nối.

Do `source_grounded_claims` tự đưa continuation vào public text, hiện tượng có thể làm câu trả lời thêm đoạn không liên quan mặc dù mỗi span đều đúng nguồn. Hướng đề xuất: xác định liền kề trước khi lọc, kiểm boundary gốc chỉ chứa khoảng trắng/page marker cho phép; không nhảy qua container/heading/list. Giữ nguyên raw spans.

## Đối soát chất lượng đáp án 82 câu

Đây là kiểm tra theo mã và dữ liệu cung cấp, không xác nhận tính pháp lý/chính xác chính sách với văn bản bên ngoài.

- **6/9/13/25**: lượt full82 tốt hơn lượt 443; 13 giữ “một số ngành phù hợp”, không suy rộng một hàng thành toàn nhóm; 25 không cụt như trước. 13 từng dao động ở 444 nên một lượt đúng chưa chứng minh ổn định.
- **26 supported nhưng chưa trả lời trực tiếp**: hỏi điểm chuẩn là tổng ba môn hay đã tính ưu tiên; đáp án chủ yếu đưa công thức giảm ưu tiên/thang điểm, chưa kết luận đúng ý hỏi. Không tính supported là quality-pass.
- **17/30/55/71**: có đoạn liên quan nhưng còn văn bản flyer/địa chỉ hoặc thông tin ngành/đợt khác không cần thiết. Có thể đúng nguồn mà trải nghiệm trả lời vẫn rối.
- **52 supported nhưng mất đầu câu**: có đoạn bắt đầu “Nhơn mà không đăng ký...”. Nối xuôi Q25 không xử lý khối bắt đầu giữa câu và không bảo đảm đơn vị được chọn là câu đầy đủ.
- **62**: công thức raw đang xuống dòng mất hình dạng phân số; có nhiều dòng định nghĩa biến trong answer nhưng gap trước vá intro vẫn báo thiếu. Không nên chỉ đổi status mà coi công thức này sử dụng được; phải kiểm biểu diễn công thức và dữ liệu mốc. Full82 chưa chạy với bản vá cuối.
- **75**: hỗ trợ liên hệ hữu ích nhưng còn thiếu đường dẫn cụ thể; xem F3.
- **74 missing không phải chứng minh corpus thiếu phương thức bổ sung**: Q73 cùng kho/cấu hình trích `ks_rev_aae30aac628c:15578:16015` có đủ bốn phương thức theo ngành. Selection Q74 không có block đó, lại có nhiều phương thức chung đợt đầu. Lỗi selection/coverage; corrective đã chạy một lần nhưng không lấy đúng đoạn. Giữ no-answer là an toàn, song phải sửa truy hồi thay vì yêu cầu người dùng bổ sung chính dữ liệu đã có.
- **37 partial**: QueryPlan có target_institution="Sư phạm", query prefixed “Sư phạm:” thay vì QNU. Q12 hỏi cùng chính sách ở QNU lại answered. Guard hàng-đơn chặn suy rộng là tốt, nhưng institution-role resolution/alias vẫn có lỗi, không phải mặc nhiên thiếu nguồn.
- **32 conflict**: đọc DB các đoạn được chọn cho thấy `6602:7081` nói IELTS quy đổi thay điểm trong tổ hợp xét tuyển; `7083:7561` nói không thay điểm thi khi xác định điều kiện/ngưỡng đầu vào; cập nhật `14373:14550` nói thay điểm trong tổ hợp PT1/PT2. Hai công dụng khác nhau không tự mâu thuẫn. Fail-closed tốt hơn đoán, nhưng nhật ký “conflict đúng chính sách” chưa đủ bằng chứng; cần phân biệt điểm xếp hạng với điều kiện đầu vào hoặc hỏi rõ công dụng. Artifact không lưu cặp claim/source-tuple mâu thuẫn cụ thể, nên không xác nhận mọi conflict là thật.
- **11/15/21/27/54/56 partial**: audit có nhiều yêu cầu nhắc lại/định nghĩa/mã hoặc proof năm. 21 và 27 đã có câu chính trả lời; cần đối chiếu điều kiện theo quan hệ và phạm vi. Không giải quyết bằng loại hết số/năm (F1). Với 54 có thể cân nhắc mốc hạn để tư vấn hữu ích, nhưng tách yêu cầu trả lời yes/no khỏi yêu cầu lịch đầy đủ.

## Kết luận và ưu tiên

Chưa chấp nhận kết luận “đã xử lý xong” cho patch 444/445. Có tiến bộ về độ bám nguồn và vận hành, nhưng hai P1 mới cần regression/fix trước, rồi F3/F4 và các câu 26/32/37/52/62/74/75. Không cần đổi model, nâng token hay thêm thuật toán lớn trước khi sửa các bất biến này.

Sau sửa: probe nhỏ có cả ca âm/diễn đạt lại/năm lịch sử; ghi artifact với cùng fingerprint mã cuối. Chỉ sau đó full82 cuối. Bổ sung câu giữ lại ngoài bộ FAQ đã dùng để xây văn bản thuyết minh; bộ82 hiện tại có nội dung nguồn tổng hợp từ chính FAQ nên không phải held-out benchmark độc lập. Chưa có điểm accuracy/TM-08 hoặc chứng minh độ ổn định nhiều lượt.

## Bài học

Khớp span/hash không chứng minh quan hệ hay độ đầy đủ; regression có thể đạt mà vẫn thiếu negative case quan trọng. Kiểm fingerprint toàn lượt và phân biệt trạng thái model audit với đánh giá người dùng. Tổng citation phải tách canonical/fact đúng mẫu đếm, không cộng fact hai lần.
