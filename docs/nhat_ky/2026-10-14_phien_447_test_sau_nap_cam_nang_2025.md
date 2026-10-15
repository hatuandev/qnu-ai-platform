# Phiên 447 — Kiểm tra dữ liệu và test sau nạp cẩm nang 2025

Ngày: 14/10/2026, Asia/Bangkok. Theo yêu cầu người dùng kiểm tra dữ liệu đã nạp và thử lại chatbot. Không sửa runtime, cấu hình, model/provider, quota, review hay publication; không reset/reindex/publish. Chỉ thêm harness kiểm thử và tài liệu. Backup vẫn tạm dừng.

## Phương pháp

Đọc skill RAG, chatbot và clean-code. Theo các skill, kiểm tra cả knowledge binding, chỉ mục thật, nguồn trích, năm, phạm vi và độ đầy đủ; không dùng supported làm accuracy. Giữ primary/fallback và reranker do DB ModelOps quản lý, không thay bằng model/hotline ví dụ trong skill.

Kiểm tra DB PostgreSQL, snapshot RAG và Qdrant bằng thao tác đọc. Test chat thật `/assistants/admissions/chat`, các cuộc hội thoại mới; không gửi đáp án kỳ vọng. Bộ 14 câu cũ dùng runner417 có sẵn; sáu câu mới dùng `backend/scripts/evaluate_camnang_447.py`. Đây không phải full82 hoặc TM-08.

## Dữ liệu đã nạp

- Assistant `admissions` liên kết `col_admissions`, tenant `tenant_qnu`.
- Snapshot `c53f1acbde1bacbed06b`, **21 nguồn**. So với 445 đã thêm cẩm nang, không so sánh hai lần chạy như cùng corpus.
- Nguồn đang xuất bản là **`Cam_Nang_Tuyen_Sinh_Dai_Hoc_2025_QNU.docx`**, title cùng tên, **53 trang**; không phải PDF117 trang đã review ở lượt trước.
- Source `ks_rev_09753d4edfaa`: ready, canonical129196 ký tự, hash `d9440eda31b9b4be3d6f87dda98b169daff9a54482e761af02eae0048b0bf3e3`.
- Binding `bnd_af2d17a6f0d9`: active. Index `idx_rev_c1837199e835`: active,1099chunks/1099point IDs, parity_passed=true.
- Đọc trực tiếp Qdrant theo index_revision_id và is_retrievable=true: **1099 points**, đúng expected. Hai payload mẫu ready/retrievable và đúng revision. Đây là kiểm tra số lượng/trạng thái, không claim đã rehash độc lập toàn bộ1099points.
- Không có ký tự thay thế U+FFFD trong canonical. Điều này không chứng minh bảng/ngữ nghĩa đã đúng.

### Những lỗi dữ liệu còn tồn tại

1. Structured artifact có2tables, nhưng table1 chỉ7rows; table2 có0rows và nhận dòng Giáo dục Thể chất làm header. Có `TABLE_HEADER_UNRESOLVED` và `TABLES_NOT_MATERIALIZED` cho các trang3–8. Phê duyệt Studio đã có, nhưng approval không tự sửa nội dung bảng.
2. Chỉ7facts tổ hợp môn được materialize. Dòng `Sư phạm Lịch sử`, mã7140218, có attribute_value chỉ **`(`**; phần tiếp nối nằm sau page marker trang2. Cần đối chiếu bảng gốc52dòng, không coi count1099vectors là bảng52ngành đã hoàn chỉnh.
3. Cả7facts có applicability_year=null. Trong1084blocks evidence của nguồn mới, không có verified data-year2025/2026. Header có mention2025/proposed; không đồng nhất unknown với sai, nhưng unknown không đủ để gán hàng vào2026.
4. Kiểm tra SourceUnits quanh Sư phạm Toán (9510–11600) và Kỹ thuật phần mềm (87285–89800): tiêu đề ngành, thời gian đào tạo và cơ hội việc làm đều thành paragraph, parent_id=null, heading_path=[]. Có tiêu đề tách thành `**` và `GIỚI THIỆU**` qua trang. Dữ liệu thân đoạn vẫn có, nhưng mất liên kết ngành–thuộc tính gây khó truy hồi.

## Artifact và tính bất biến

- `backend/storage/admissions_eval447_regression14.json`: 14 câu từ fixture82, routechat, ID5/6/9/13/17/21/25/26/32/37/52/62/74/75.
- `backend/storage/admissions_eval447_camnang6.json`: lần đầu thử sáu câu mới song song lượt14; **6HTTP503**, `ALL_PROVIDERS_UNAVAILABLE`, không có câu trả lời. Giữ artifact riêng, không trộn vào lượt20 cuối.
- `backend/storage/admissions_eval447_camnang6_sequential.json`: chạy lại sáu câu tuần tự sau khi lượt14 kết thúc; 6HTTP200. ID2001–2006.
- Lượt14 và lượt6 cuối cùng đều code_unchanged/configuration_unchanged/publication_unchanged=true, cùng snapshot và config fingerprint `d44d96c4f2a9646a212d33470690dd9da590d6293bbf665a149bfddb00043e1b`.
- Runtime417 fingerprint `1bd743e6f74358de143380f43d14506f7c4d8839f0ec9d835416014292d2df0f`, là mã sau legend-introfix, như review446. Harness6 dùng tập file hash riêng; không so trực tiếp hai code hash có danh sách file khác nhau.

## Kết quả lượt20 cuối

| Nhóm | HTTP200 | supported | partial | conflict | missing | Canonical citations | Facts |
|---|---:|---:|---:|---:|---:|---:|---:|
| 14 câu cũ | 14 | 10 | 3 | 1 | 0 | 41 | 1 |
| 6 câu mới tuần tự | 6 | 3 | 0 | 0 | 3 | 6 | 1 |
| Tổng | 20 | 13 | 3 | 1 | 3 | 47 | 2 |

20/20HTTP200 của lượt cuối **không bao gồm** sáu503banđầu. Trung bình24,43s, cao nhất36,89s; không là benchmark hiệu năng hay uptime. Không executionDAG.

Chạy `scripts.verify_evidence_report` trên hai artifact cuối, đọc DB và raw spans/hash/fact values: **47canonical +2facts =49citations**, failures=[] cả hai. Đối soát này không chứng minh dữ liệu fact đúng nguyên bản hoặc đúng năm; fact thiếu năm vẫn có thể khớp DB.

### Các câu mới

| ID | Câu hỏi | Kết quả máy | Đối soát |
|---|---|---|---|
| 2001 | Theo cẩm nang2025, Sư phạm Toán học học bao lâu và ra trường làm gì | missing | Có thời gian4năm và các nghề trong canonical, nhưng selection không lấy đúng đoạn; không phải thiếu nguồn |
| 2002 | Theo cẩm nang2025, Kỹ thuật phần mềm học bao lâu và cơ hội việc làm | missing | Có4,5năm/150tín chỉ và các nghề trong canonicalDOCX; selection lại nghiêng quy chế/quy định khác, không lấy thân mục35 |
| 2003 | Tổ hợp Sư phạm Lịch sử2025 | missing | Selection có fact chỉ`(`; verifier từ chối đúng thay vì bịa tổ hợp. Lỗi bóc tách bảng đã chứng minh |
| 2004 | Cẩm nang2025 xét học bạ lớp nào | supported | Trích đúng đoạn lớp12 và header2025 từ nguồn mới |
| 2005 | 2026 có chỉ dùng lớp12 như cẩm nang2025 không | supported | Trích nguồn2026: cả lớp10/11/12; không lấy lớp12của2025 làm quy tắc2026 trong lượt này |
| 2006 | Có thể dùng tổ hợp2025 khẳng định chắc tổ hợp2026 không | supported **nhưng chưa đạt** | Đưa fact tổ hợp Sư phạm Sinh học2025 không nhãn năm dưới header2026, rồi trả lời về điểm chuẩn/đậu chứ không về tổ hợp. Sai thuộc tính/độ phủ và trình bày thời gian |

### P1 từ review446 đã xuất hiện trong test thực tế

Q2006: QueryPlan years=[2026],document_years=[2025]. Fact của cẩm nang có temporal_scope unknown, không có data_year. Verifier đánh quote bảng relevant/scope_compatible=true, và xem lời cảnh báo về điểm chuẩn như trực tiếp trả lời câu hỏi tổ hợp.

SemanticAudit còn missing_constraints=`Không có bằng chứng tổ hợp môn 2026 để khẳng định tính chắc chắn`, nhưng finalmissing=[]/supported. Theo `_advisory_missing`, con số duy nhất2026 đã có trong claim khác và nằm trong tập năm; fresh rỗng nên bị bỏ. Đây là bằng chứng trực tiếp về lỗi lọc thiếu ý theo con số/năm, không chỉ unit-repro446. Không được báo ba câu2004/2005/2006 đều phân biệt năm thành công; chỉ2004/2005 đạt đối soát trong lượt này.

### Các câu cũ

- 5/6/9/13/17/25/37/52/74 được máy đánh supported. 17 dùng3năm của2026, không nhầm lớp12của2025.
- 37 có thêm policy nhóm không dùngPT3, không chỉ một hàng; 52 không cụt đầu như445; 74 lần này trích được đoạn phương thức bổ sung trong thuyếtminh. Có cải thiện trong một lượt, nhưng code không đổi; không quy kết toàn bộ cải thiện do nguồn mới.
- 13 trả thêm điều kiện từ thuyếtminh; cần đối soát các nhánh thay thế với thông báo gốc khi đánh giá chính sách đầy đủ. Không mặc định supported là đủ mọi điều kiện.
- 26 supported nhưng vẫn chủ yếu nói trần30điểm; chưa trả lời thẳng điểm chuẩn là tổng3môn hay đã gồm ưu tiên.
- 21 partial vì thiếu định nghĩaPT2/học bạ; 62partial: công thức rawvỡ hình phân số và thiếulegend; 75partial thiếulocator đăng ký cụ thể. Không chữa bằng cách hạ guard.
- 32conflict IELTS vẫn tồn tại; cần tách thay điểm xét tuyển với điều kiện/ngưỡng đầu vào như review446, chưa khẳng định conflict thật.

## Lỗi vận hành khi chạy đồng thời

Sáu câu mới lần đầu trả503trong0,19–0,23s khi lượt14vẫn chạy. Đọc DB: providerprimary/fallbackcùng9router có đúng1keyactive, quota_limit=null,last_error_code=null và lease_until đang có. Mã `InferenceService` gọi `acquire`, không xử lý acquired.busy riêng; lease trống bị coi no_available_credentials rồi503.

Chạy lại tuần tự6/6HTTP200, không đổiprovider/model/key. Bằng chứng phù hợp với tranh chấp leasekey, không chứng minh upstream9routerđãhỏng. Cần log correlation để khẳng định nguyên nhân từngrequest nếu sửa. Không resetlease, không thaykey hoặc thêmquota. Harness mới chỉ thêm khả năng dừng sau lỗiHTTP5xxcho các lượt tiếp theo; không xóa sáu lỗi đã ghi.

## Đề xuất tiếp theo — chưa triển khai

1. Ưu tiên P1 coverage/temporal: không xóa missing vì chỉ có năm; điều kiện đủ cần đúng entity/attribute/year/method/round và ý định. Fact chưa xác minh năm không được trình bày như dữ liệu2026.
2. Bảng qua trang: giữ header và tiếp nối hàng theo cấu trúc; phục hồi/dò đủ52rows, kiểm tra mã và tổ hợp, gắn năm theo bằng chứng. Duyệt lại revision sửa trước reindex/publish, không chỉnh lén revisionđãactive.
3. Khôi phục quan hệ tiêu đề ngành–đoạn con; đưa contextnhánh vào embedding/BM25và đóng gói phần thời gian/công việc theo cùngmajor. Không hardcode tênngành/từvựng; không cầnGraphRAGhayđổimodelđểvá lỗi này.
4. Keybusy phải chờ cógiới hạn hoặc báo busyđúngnguyên nhân, không trả tất cảproviderkhôngphản hồi khi mộtkeyđangđượcgiữ.
5. Sau sửa, test2001/2002/2003/2006 +21/26/32/62/75 và các caâm/paraphrase; rồi mới full82trênsnapshot/mã cuối.

## Tệp thay đổi và kiểm chứng

Thêm `backend/scripts/evaluate_camnang_447.py` (harnesskiểm thử, không runtime), ba artifactsJSON, nhật ký447 và cập nhật PROJECT_CONTEXT/README/WORK_LOG. Ruff harness đạt. Không chạy pytest/fullsuite/FEbuild vì không thay đổi mã app. Hai script verifier đã chạy thật, không dùng fallback/mockđểchứng minhvectorhaynguồn.

Kết luận: nạp/xuất bản/vector **đã thành công về kỹ thuật**, nhưng cẩm nang chưa phát huy tốt câu tư vấn ngành và vẫn có lỗi dữ liệu/thời gian. Chưa đạt độ sẵn sàng mở công khai, chưa có accuracy/TM-08 hoặc full82sau nguồn mới. Không yêu cầu người dùng nạp lại nguyên file như cách chữa tự động; phải sửa đúng bảng/cấu trúc/guard trước.
