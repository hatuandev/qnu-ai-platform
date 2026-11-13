# Kiểm thử PDF thật — TB điểm sàn 26

> **TÀI LIỆU LỊCH SỬ (từ 2026-11-13):** frontendV1, `test-v1-e2e.ps1` và bộ `scripts/v1_e2e_*` đã được gỡ khỏi repo. Các lệnh dưới đây không còn chạy được; giữ để truy vết.

## Kết quả mới phiên789 — F14/MX-05

Promptv13 hỗ trợ thứ tự đọc/citation cho đoạn liên tiếp cùng snapshot và kết hợp văn bản với ô bảng; schema chỉ cho statements dẫn văn bản. Không cần recompile/reindex để nạp thay đổi RAG này, chỉ serve phải dùng backend hiện tại.

Cohortv13 gửi9câu đúng một lượt/câu: **8 PASS/1 UNCERTAIN**, F14/MX-05 PASS. I25-04 bị ngắt tiến trình API/test trước khi ghi kết quả, không gửi lại để làm xanh. Sau khôi phục chỉ chạy sáu ID chưa dispatch với fingerprint cũ; báo cáo vẫn exit1. Đây không phải9/9PASS, không trộn các kết quả v11/v12. Khi tiến trình mất, `server.json=true` và DBturn=running chưa chứng minh model vẫn xử lý; kiểm port/process và đối soát trước khi chạy tiếp. Không tự xóa lock hoặc gửi lại uncertain turn chỉ vì lâu. Xem [nhật ký789](../nhat_ky/2026-11-01_phien_789_dieu_kien_va_tra_loi_hon_hop.md).

## Chạy riêng chín câu lỗi, không retry — phiên788

Sau khi publication/index của phiên hiện tại đã PASS và serve đã nạp backend hiện tại, chạy từ root:

```powershell
.\backendV1\.venv\Scripts\python.exe -X utf8 scripts/run_admissions_retest.py --headed
```

Runner chỉ dành cho F13/F14/I25-04/I25-05/BC24-05/BC24-08/MX-02/MX-05/MX-10 của snapshot tuyển sinh hiện tại. Tạo thư mục cohort mới, không đổi checkpoint cũ; một POST turn/câu, không gửi lại khi kết quả chưa rõ. Drift/uncertain/hạ tầng dừng chặng, có FAIL thì exit1. Runtime cần answer off, output16384/context98304byte, provider không retry/fallback; runner kiểm trước khi gửi. Thiếu publication/binding/capacity/quota thì BLOCKED, không tự thay cấu hình.

Mỗi lần gọi lệnh là một thí nghiệm mới có chi phí; không chạy liên tục để chọn kết quả đẹp. Khi lỗi, đọc report trong thư mục được in ra. Không cleanup/init/upload/recompile/reindex chỉ để chạy nhóm câu này.

Kiểm chứng phiên788: **7 PASS/2 FAIL**,0 NOT_RUN/UNCERTAIN,177.7s; F14/MX-05 còn model_abstained dù căn cứ vào context. Audit9chat attempt1, không retry, không lỗi schema/output truncation trong cohort này. Kết quả không thay full53 cũ. Xem [nhật ký788](../nhat_ky/2026-11-01_phien_788_sua_rag_va_retest9.md).

## Ngân sách trả lời mới — phiên785

Theo yêu cầu người dùng, Qwen hiện được cấu hình task `answer` tắt suy luận (`enable_thinking=false`), giữ compiler off. Assistant tuyển sinh hiện tại dùng output tối đa model công bố **16384 token**, context **131072**, ngân sách evidence **98304 byte** và overhead dự toán **16384**. Output là trần; model hoàn tất sớm trả kết quả ngay.

Helper tạo assistant E2E mới lấy output tối đa đã khai báo trong ModelOps, không còn cap4096. Capacity thiếu/chưa đủ chỗ input, overhead và output vẫn BLOCKED; không tự tăng capacity hoặc quota. Cận byte không thay tokenizer; guard toàn payload của ModelOps vẫn kiểm trước dispatch.

Probe cấu hình ngắn PASS; **chưa chạy lại benchmark16/53 câu**. Cấu hình khác cohort cũ nên lần đánh giá tiếp theo phải tạo cohort mới và ghim fingerprint mới; giữ nguyên kết quả/histories cũ. Không cleanup/index lại chỉ vì thay output. Các kết quả/cấu hình4096 ghi ở phần lịch sử bên dưới phản ánh thời điểm cũ. Xem [nhật ký785](../nhat_ky/2026-11-01_phien_785_tat_thinking_answer_output_max.md).

## Xuất bản nhanh sau compiler, không gọi review — phiên779

Luồng mặc định vẫn là compiler → review → duyệt → xuất bản → lập chỉ mục → hỏi đáp. Có thêm lựa chọn chủ động compiler → duyệt bỏ qua review → xuất bản → lập chỉ mục → hỏi đáp. Bỏ qua review không tự cấp quyền, không bỏ xác nhận duyệt/xuất bản và không chứng nhận chất lượng nội dung.

Trong giao diện chi tiết phiên bản đã biên soạn, mở menu `⋯` → **Duyệt nhanh, bỏ qua review**. Tích xác nhận, nhập lý do ít nhất 10 ký tự, xem trước và xác nhận duyệt. Sau đó dùng **Xuất bản** như thường lệ. Phiên bản hiển thị **Chưa qua review**; quyết định lưu người thực hiện, lý do và hash đúng phiên bản. Nút duyệt có review vẫn giữ nguyên.

Trong E2E, sau khi `admissions-draft` PASS, chạy:

```powershell
.\test-v1-e2e.ps1 run admissions-publication --headed --skip-review
.\test-v1-e2e.ps1 run admissions-chat --headed
```

Chỉ `admissions-publication` nhận `--skip-review`. Không đánh dấu `admissions-compilation` PASS thay cho review; checkpoint xuất bản lưu `review_mode=skipped`, báo cáo hỏi đáp ghi `compilation_review=SKIPPED_BY_USER`. Chat chỉ được mở sau publication/index PASS thực tế. Không truyền cờ này thì vẫn cần review đầy đủ.

Backend kiểm tra quyền, compiler hoàn tất, bundle/phiên bản/metadata nguồn, preview hash, idempotency và xác nhận duyệt/xuất bản như trước. Không tạo review hoặc finding giả. Khi máy vừa bật lại, dùng phiên cũ và bật serve theo hướng dẫn; không cleanup/init hoặc upload/OCR lại chỉ để bỏ qua review.

Kiểm chứng phiên779: xuất bản nhanh ba PDF/28 trang và lập chỉ mục 179 đoạn PASS (30 giây tổng chặng). Kiểm tra API/PostgreSQL cô lập 33 PASS; 6 unit kiểm ràng buộc bỏ qua review PASS; 38 kiểm tra frontend liên quan và 4 script PASS. Lượt model thật FAIL sau 5.8 phút: 12 PASS, F13/F14 FAIL, 39 NOT_RUN, không retry. Xem [nhật ký779](../nhat_ky/2026-11-01_phien_779_xuat_ban_nhanh.md); publication PASS không đồng nghĩa hỏi đáp PASS.

## Chạy riêng compiler, tạm chưa review — phiên778

Sau khi khởi động máy, giữ phiên hiện có nếu chưa cleanup. Bật Docker và các container của phiên, rồi chạy `serve` nếu API/worker/frontend chưa hoạt động. Không cần init, upload hay OCR lại khi các chặng đó đã PASS.

Để chỉ biên soạn bản nháp của ba tài liệu, bỏ qua review trong lượt kiểm tra:

```powershell
.\test-v1-e2e.ps1 run admissions-draft --headed
```

`admissions-draft` vẫn kiểm tra quota tháng hiện tại, hash nguồn, số trang, version/hash OCR và citation của draft; request `auto_review=false`. PASS của chặng này chỉ chứng minh compiler hoàn tất, không thay thế `admissions-compilation` (compiler + review). Publication/chat mặc định cần review; lựa chọn bỏ qua review phải dùng cờ tường minh của phiên779 ở trên. Khi cần review, chạy `admissions-compilation` bình thường để dùng lại các draft đã hoàn tất.

Nếu máy tắt khi job đang chạy, chờ hệ thống đối soát: lượt bị gián đoạn giữ trạng thái `uncertain`, không gửi lại các phần đang dở. Sau khi xác nhận nguyên nhân, dùng `--recover` chủ đích để tạo lượt mới và giữ lịch sử. Lượt `quota_not_configured` chỉ được thay khi đúng provider, chưa review/publish và mọi part còn pending/attempt_count=0; không tự retry lỗi model. Kiểm tra quota của đúng tháng: hạn mức tháng trước không tự áp sang tháng mới. Chặng draft chỉ đọc quota, không tự tăng/reset.

Theo xác nhận trong phiên778, provider Qwen đang dùng đã có ModelOps reasoning off riêng task `compiler` (probe JSON thành công, không reasoning). Cấu hình gắn với provider trong DB của phiên; cleanup/init mới không tự sao chép chính sách này. Review vẫn là lựa chọn mặc định trước xuất bản.

Kiểm chứng phiên778: cả ba tài liệu đã compiler PASS (17/17 phần, khoảng5.1phút); raw17lượt đều reasoning0,không có review. Đây chỉ là kiểm chứng tạo draft, không thay kiểm tra chất lượng/publish/RAG. Giữ phiên hiện tại; chạy `admissions-compilation` khi muốn thực hiện review.

## Sửa hợp đồng compiler → hỏi đáp — phiên777

Request compiler phải dùng `topic`, `ocr_run_ids`, `text_versions`, `provider_id`; `source_id`/`revision_id` không phải trường được nhận. Runner kiểm tra đủ cả ba nguồn/hash/trang OCR trước lượt model đầu, ghim version/hash văn bản canonical qua API text-review, bật structured output và tắt auto_review vì chặng gọi review riêng.

Compiler và review hoàn tất mới đọc report; report phải đúng review đã lưu. Trước khi tạo tài liệu, cả ba review phải hoàn tất và không có finding. Gate duyệt phải khớp review đã kiểm tra; preview/commit giữ hash và idempotency. Khi POST phục hồi lỗi, không tăng lịch sử để đổi khóa sang lượt khác. Index trước chat phải completed/active, đúng embedding và đúng tập ba document/version/receipt/bundle.

Test mới `admissions-pipeline-777.test.ts` chạy runner bằng adapter kiểm thử, thu request từ compiler, review, publication, index, assistant create/update và conversation single/all. `scripts/check_v1_e2e_contracts.py` kiểm chúng bằng chính APIRoute/Pydantic backend, bao gồm method/path/body/header/query; không gọi handler/DB/model. Đây là kiểm tra hợp đồng, không thay kết quả E2E với model thật.

Với lỗi422 trước đây, request bị chặn trước khi tạo compilation. Giữ phiên và các kết quả upload/OCR; không cleanup/init hay thêm `--recover` chỉ vì lỗi payload này. Chạy lại từng chặng, dừng khi có lỗi:

```powershell
.\test-v1-e2e.ps1 run admissions-compilation --headed
.\test-v1-e2e.ps1 run admissions-publication --headed
.\test-v1-e2e.ps1 run admissions-chat --headed
```

Kiểm chứng phiên777:88case liênquanPASS, TypeScript/build/Biome/RuffPASS. Fullfrontend560PASS/33FAIL ở9fileUI/fixture, chưa xanh toàn bộ; model thật chưa chạy ở lượt rà này.

Bản sửa chỉ nằm trong runner/test, không cần restart backend/serve. Không bỏ finding hoặc tự tạo lượt hỏi mới để làm xanh kết quả. Chất lượng model thật vẫn cần đánh giá riêng qua53câu.


## Ngân sách được duyệt — phiên776

Người dùng đã yêu cầu ngân sách tháng **20.000.000 token** cho profile E2E QNU. `test_monthly_token_limit` và validator ở `live-defaults.ts` đã đồng bộ mức này; vẫn chỉ chấp nhận số nguyên dương trong trần hữu hạn. Đây là quota tháng của workspace thử, không phải context/output của một request.

Sau khi provider-setup và các chặng model đã PASS, chạy lại:

```powershell
.\test-v1-e2e.ps1 run navigation --headed
```

Navigation áp dụng mức khai báo cho đúng workspace E2E theo cơ chế hiện có; không reset usage/reserved. Không cần cleanup/init, nhập lại key hoặc restart serve chỉ vì sửa profile/test. Các chặng admissions vẫn chỉ kiểm quota, không tự tăng nếu thiếu. Phiên776 chỉ kiểm thử cấu hình cục bộ; chưa chạy lại navigation/live.

## Hiện hành — benchmark 3 PDF, phiên775

Bộ `admissions-multi-docs-v2-775` gồm 53 câu trên 3 PDF/28 trang. Giữ nguyên toàn bộ câu và nhãn F01–F19 từ bộ 2026 ban đầu. Các nhãn đa tài liệu được sửa theo PDF gốc: Sư phạm Tin học và Sư phạm Tiếng Anh THPT 2026 đều 20; CNTT (An toàn, an ninh mạng) 15 tại trang vật lý 5. Học phí kỹ sư ở info2025 trang 10; nữ nhập học ở report2024 trang 2. Trang báo cáo có số in lặp lại: citation dùng **trang vật lý PDF**, không dùng số in ở chân/đầu trang.

Mỗi fact có nguồn, năm, trang, chủ thể, metric và kiểu số. Chấm câu có đáp án đòi đúng publication/version/revision/hash; dữ kiện bảng cần proof của ô được chọn cùng nhãn dòng/header, giá trị ở đúng trang. Không chỉ dò số trong toàn câu. Regex và proof là kiểm tra quy tắc; nhãn vẫn draft, đánh giá ngữ nghĩa độc lập `NOT_RUN`.

Chặng chat khai báo rõ output 4096, history 0, top20/candidate50 và context byte theo capacity đã xác nhận. Dự phòng prompt 16384 byte; context evidence tối đa 128000 byte và phải nằm trong input/context sau khi trừ output. Đây là **dự toán**, không thay phép đo payload cuối gồm prompt/schema/catalog của ModelOps. Report ghi kích thước bundle, capacity plan, dự toán cặp query/chunk rerank và quota; nếu trần bị vượt, giữ lỗi để điều chỉnh có chủ đích, không tự cắt nguồn hay nâng quota. Chặng upload chỉ đọc quota; đã bỏ tự tăng lên 20M. Trước chat, quota khả dụng phải đủ dự toán trong report; chỉnh hạn mức trong ModelOps khi đã kiểm tra, không xóa usage/reservation.

Index manifest phải khớp cả 3 phiên bản và quyết định xuất bản đang dùng. Cố định benchmark/index/assistant/provider bằng fingerprint trước chấm, rồi khóa prompt/config trace từ kết quả đầu; đổi cấu hình giữa lượt bị chặn. Scope single thiếu binding hoặc hội thoại cũ sai scope đều BLOCKED, không chuyển sang cả kho.

Mỗi câu một dispatch, không retry khi sai đáp án hoặc gặp lỗi. Dấu dispatch được lưu **trước** POST để timeout/HTTP lỗi cũng có vết. Câu sai nội dung vẫn tiếp tục các câu độc lập; lỗi hạ tầng/quota/capacity dừng và để phần còn lại NOT_RUN. Kết thúc vẫn FAIL nếu có câu lỗi/chưa chạy. Replay/resume không được tính thành PASS lần đầu.

Phiên `93faa11f0caf` hiện ở `provider-setup BLOCKED` do chưa nhập key. **Không cleanup/init lại.** Chạy trong PowerShell tương tác tại root repo:

```powershell
.\test-v1-e2e.ps1 run provider-setup --headed
```

Sau khi nhập key ẩn và chặng trên PASS, chạy lần lượt, dừng nếu chặng có lỗi:

```powershell
.\test-v1-e2e.ps1 run model-discovery --headed
.\test-v1-e2e.ps1 run model-chat --headed
.\test-v1-e2e.ps1 run model-embedding --headed
.\test-v1-e2e.ps1 run model-rerank --headed
.\test-v1-e2e.ps1 run model-ocr --headed
.\test-v1-e2e.ps1 run navigation --headed
.\test-v1-e2e.ps1 run admissions-upload --headed
.\test-v1-e2e.ps1 run admissions-extraction --headed
.\test-v1-e2e.ps1 run admissions-compilation --headed
.\test-v1-e2e.ps1 run admissions-publication --headed
.\test-v1-e2e.ps1 run admissions-chat --headed
```

Kiểm chứng775: 49 regression liên quan PASS; kiểm PDF gốc 3 file/28 trang/55 fact checks PASS; E2E TypeScript, build, scoped Biome/Ruff PASS. Full frontend Vitest **539 PASS/33 FAIL** ở 9 file UI/fixture, không thuộc các file ứng dụng sửa trong lượt này; chưa có baseline tái hiện riêng để khẳng định toàn bộ là lỗi nền. Live 53 câu **NOT_RUN** vì thiếu key, không dùng unit PASS để báo RAG đã đạt.

Các mục bên dưới là lịch sử vận hành các bộ/cohort trước, không thay trạng thái hiện hành này.


## Kết quả mới nhất và giới hạn (phiên769)

Trợ lý hiện tại revision6 có budget **81920 byte** cho top20 và tối đa4chunk phụ thuộc bảng. Promptv7/rerank đọc bảng rõ hàng, giữ ô và provenance; nhánh context native chỉ nối khi có các dấu hiệu cấu trúc cùng snapshot. Không sửa dữ liệu đã xuất bản hoặc index. Context model128K/output4096 giữ.

Hai cohort model thật được giữ riêng: v6 đạt16/19, sau sửa context v7 đạt **17/19** trong295.797s; F09 sai cột và F12 từ chối. F06/F15 đạt bản cuối nhưng chưa thể nghiệm thu cả19. Mỗi câu một lần/cohort, không retry từng câu hoặc cộng các PASS từ nhiều đợt. [Nhật ký769](../nhat_ky/2026-10-31_phien_769_sua_doc_bang_va_live_rag.md).

Đây là testAPI backend hiện tại, chưa phải PlaywrightPASS. Serve cũ chưa được tự restart; nếu chạyCLI cần mởlạiserve để nạp mã. Không cleanup/init chỉ để nạp mã. Không tự tăngquota hoặc xóareservationunknown; cuốiđợt còn450364tokenkhảdụng, ít hơn696149tokenđãdùngởđợtnày.

## Ngân sách context và kết quả một lượt (phiên768)

Trên trợ lý admissions hiện tại, đã lưu `context_max_bytes = 57344` qua API (revision4). Con số này là **byte evidence**, không phải token: cận của 20 chunks lớn nhất trong chỉ mục 46 chunks là 51391 byte, thêm dự phòng rồi làm tròn. Context Qwen131072/output4096, candidate50/top20 giữ nguyên. Phiên mới hoặc tài liệu/model khác phải tính lại, không sao chép ngân sách hoặc tăng quota mặc định để bỏ lỗi.

Đợt API mới đủ 19 câu, mỗi câu một lần, đạt **16/19** trong 228.297s: F06/F09 bị từ chối, F15 sai số liệu ngoại lệ. Audit xác nhận không retry và không lỗi token/context/quota. [Chi tiết phiên768](../nhat_ky/2026-10-31_phien_768_context_budget_va_live_19_cau.md). Chưa chạy lại Playwright/UI trong đợt này; nhãn vẫn draft, cần duyệt độc lập. Không coi đợt này là admissions-chat PASS hoặc ghi đè checkpoint.

Serve cũ không được tự restart. Trước khi tự chạy CLI với mã mới, dừng serve cũ rồi mở lại ` .\test-v1-e2e.ps1 serve `; giữ phiên/index đã có, không cleanup/init chỉ vì đổi byte budget. Khi nghiệm thu một đợt mới, giữ báo cáo đầu và không hỏi lại câu sai để chuyển kết quả thành PASS.

Compiler/review đã có nhánh chia phần và checkpoint: xem [triển khai, migration và cách chạy tiếp](V1_COMPILER_TAI_LIEU_LON.md). Restart serve để nạp mã và migration trước khi chạy lại compilation; chưa có kết quả nghiệm thu cho nhánh này.

## Chạy tiếp sau lỗi output ở compilation

### Qwen: giảm suy luận và chờ phản hồi hoàn tất (phiên760)

Trong ModelOps → model Qwen → Dự phòng & Phục hồi, bật **Chờ model xử lý xong** nếu không muốn giới hạn thời gian sinh phản hồi. Tùy chọn này áp dụng cho model được chọn, không đổi model khác; thời hạn kết nối/ghi HTTP, hàng đợi và ngân sách tổng của job vẫn giữ. Không dùng số timeout rất lớn để giả lập vô hạn.

Phiên thử `1da945adac7c` đã lưu tùy chọn này cho Qwen. Probe tổng hợp qua gateway xác nhận `chat_template_kwargs.enable_thinking=false` trả JSON đúng và không có reasoning; ModelOps đã lưu reasoning off cho `compiler`/`compiler_review`. Không suy khả năng này cho model hoặc server khác chưa kiểm tra. Cleanup/init sẽ tạo ModelOps mới; không coi cấu hình phiên cũ tự chuyển sang phiên mới.

Với lượt `uncertain` do timeout, không đổi trạng thái để gửi lại cùng request. Sau khi nạp mã mới, có thể chủ động tạo lượt mới từ OCR đã xong bằng:

```powershell
.\test-v1-e2e.ps1 run admissions-compilation --headed --recover
```

Lượt lỗi/partial cũ được giữ trong lịch sử. Đây là lượt inference mới, không phải chứng minh provider chưa xử lý request bị timeout. Không cleanup/init hoặc upload/OCR lại. Tùy chọn chờ ở QNU không thay timeout Nginx/router/server AI ở máy khác.

Lượt lỗi đã dùng hết8192token cho suy luận, chưa có JSON. Đã sửa planner chia theo ngân sách đầu ra, phân định owned/context và bật JSON Schema. Lần chạy lại chặng được phép tạo một recovery riêng theo giới hạn output ModelOps, giữ lịch sử lượt lỗi; mặc định compiler8192 không đổi. Không tự chạy model lại khi đang uncertain.

Tại cửa sổ serve nhấn Ctrl+C rồi chạy ` .\test-v1-e2e.ps1 serve ` để nạp mã mới. Ở cửa sổ thứ hai:

```powershell
.\test-v1-e2e.ps1 run admissions-compilation --headed
```

Không cleanup/init, upload hoặc OCR lại. Chỉ sau PASS mới chạy admissions-publication và admissions-chat. Nếu recovery vẫn lỗi thì giữ trạng thái để xem nguyên nhân, không thử lặp đến khi xanh. Các thay đổi này chưa chạy nghiệm thu.

## Phạm vi

Upload nguyên file `docs/tai_lieu/tuyen_sinh/TB điểm sàn 26.pdf` (8 trang), bóc tách, biên soạn, review độc lập, phê duyệt/xuất bản/lập chỉ mục, rồi hỏi 19 câu. Có kho và trợ lý riêng, dùng bốn model đã cấu hình qua ModelOps; không trộn dữ liệu giả của bộ test 14 chặng vào kho này.

[Bộ câu hỏi, đáp án và số trang](../kiem_thu/V1_CAU_HOI_TB_DIEM_SAN_26.md). Dữ liệu máy đọc: `frontendV1/e2e/data/admissions-floor-2026.json`. Nhãn hiện là draft từ việc đọc PDF; cần người duyệt độc lập nếu dùng làm benchmark chính thức.

## Chuẩn bị phiên mới

Phiên trước đã chạy lifecycle nên cần phiên mới. Tại cửa sổ serve cũ nhấn Ctrl+C; không xóa phiên khác hoặc chỉnh checkpoint thủ công. Cleanup dưới đây chỉ dọn phiên E2E đang chọn, gồm DB/khóa/provider của phiên đó; giữ báo cáo.

PowerShell thứ nhất, tại thư mục repo:

```powershell
.\test-v1-e2e.ps1 cleanup
.\test-v1-e2e.ps1 init --mode live
.\test-v1-e2e.ps1 serve
```

Chờ dòng sẵn sàng và giữ cửa sổ này mở. PowerShell thứ hai: chạy từng lệnh, PASS mới chuyển bước tiếp; provider-setup có thể yêu cầu nhập lại khóa tại nơi nhập ẩn như quy trình cũ.

```powershell
.\test-v1-e2e.ps1 run provider-setup --headed
.\test-v1-e2e.ps1 run model-discovery --headed
.\test-v1-e2e.ps1 run model-chat --headed
.\test-v1-e2e.ps1 run model-embedding --headed
.\test-v1-e2e.ps1 run model-rerank --headed
.\test-v1-e2e.ps1 run model-ocr --headed
.\test-v1-e2e.ps1 run navigation --headed
```

Không chạy nhóm `upload/extraction/compilation/publication/chat/lifecycle` dữ liệu giả trong kịch bản này. Chạy nhóm mới:

```powershell
.\test-v1-e2e.ps1 run admissions-upload --headed
.\test-v1-e2e.ps1 run admissions-extraction --headed
.\test-v1-e2e.ps1 run admissions-compilation --headed
.\test-v1-e2e.ps1 run admissions-publication --headed
.\test-v1-e2e.ps1 run admissions-chat --headed
```

## Điều kiện đạt và khi dừng

Từ phiên767, ngân sách JSON evidence được kiểm cả khi không lấy đoạn lân cận
(`context_window=0`). Nếu gặp `answer_context_budget_exceeded`, kiểm tra ngân sách
ngữ cảnh của trợ lý: top_k lớn có thể vượt mặc định16000byte. Cần chọn ngân sách
hợp lệ cho cấu hình retrieval đang dùng hoặc giảm top_k; không bỏ kiểm tra/cắt
nguồn/tự tăng capacity model để làm test xanh. Phiên767 không tự sửa cấu hình trợ
lý đang phục vụ. Trace mới có `inference_configuration_hash` và `reasoning` để
phân biệt hợp đồng suy luận; report cũ giữ nguyên.

- Upload: đúng hash PDF đã chốt; tải lại bytes nguồn vẫn giữ nguyên. Thay file sẽ BLOCKED để soạn/đối chiếu lại nhãn.
- Extraction: đủ 8 trang, kết quả sẵn sàng. Không tự sửa văn bản hay điền điểm từ đáp án test vào OCR.
- Compilation: dùng toàn bộ tài liệu, giữ bảng/ngành/phương thức/chú ý/ngoại lệ; review chỉ đạt khi không còn finding. Giữ ngân sách biên soạn hiện tại, output review theo capacity.
- Publication: preview và quyết định theo API có kiểm tra quyền; review gate không có finding; phiên bản published và chỉ mục active. Không tự xác nhận bỏ qua lỗi.
- Chat: mỗi câu một hội thoại để không nhận gợi ý từ câu trước; không đưa expected answer vào prompt. Câu có đáp án phải có số/điều kiện đã chọn và citation đúng phiên bản, hash nguồn, revision và trang; statement chỉ trỏ evidence hợp lệ. Câu ngoài dữ liệu phải trả insufficient_evidence.

PDF 8 trang nhiều ô bảng có thể làm review chạm giới hạn context/output hoặc timeout của model. Khi đó chặng phải FAIL/BLOCKED thật, không tự tăng capacity, cắt nguồn, bỏ nhận xét hay xuất bản tiếp. Gửi log của chặng lỗi để phân tích ngân sách/khả năng xử lý. Thời hạn stage là trần, không phải thời gian bắt buộc phải chờ.

Nếu đã FAIL, giữ phiên và chạy lại đúng chặng sau khi xử lý nguyên nhân. Lượt gửi có idempotency, không tạo lượt mới để thử đến khi xanh. Nếu POST đã trả lỗi model, cùng khóa sẽ giữ lỗi/lượt cũ; cần quyết định xử lý cụ thể thay vì tự retry. Không tự xóa dữ liệu hay purge sau kịch bản; có thể mở kho/trợ lý để thử thêm câu hỏi bằng tay.

## Báo cáo

Mỗi chặng có HTML/JSON tại đường dẫn runner in ra. Chặng chat thêm `admissions-answers.json`: từng ID, câu trả lời/tham chiếu, PASS/FAIL/NOT_RUN, tổng expected/passed/failed/not_run. Từ phiên775: tiếp tục sau lỗi nội dung độc lập; chỉ dừng khi lỗi hạ tầng/quota/capacity, các câu còn lại NOT_RUN.

Từ prompt `qnu.rag.answer/v4`, report chat phân biệt `origin=fresh/replayed/resumed`, `fresh_results`, `replayed`, `resumed` và `first_attempt_passed`. Kết quả lấy từ checkpoint không tính là đạt lần đầu; `inference_ms` của replay/resume là null, `client_elapsed_ms` chỉ là thời gian thao tác client. Report giữ `prompt_versions` và `configuration_hashes` để thấy khi đang trộn kết quả cũ/mới. Không dùng tổng PASS tích lũy làm tỷ lệ đúng của một lượt gọi mới. Lượt failed/uncertain không tự gửi lại hoặc đổi khóa; lỗi đọc trạng thái phải được xử lý trước.

Kiểm chứng phiên764 trên cùng index: API19câu mới, không retry, đạt18/19;F15model_abstained. Đây chưa phải nghiệm thu toàn bộ chat. Không cleanup/init hay xuất bản lại để xóa kết quả lỗi.

Phiên765 giữ relevance khi dựng evidence và nâng promptv5 cho quy định chung/ngoại lệ có scope. F15 được kiểm lại đúng một lần và đạt; F14 và3câu negative cũng đạt. Đây là5case với hợp đồngv5, không cộng với18case cũ để báo19/19 cùng cấu hình. Report giữ vết prompt/config và không retry câu sai để làm xanh.

PASS chỉ là các kiểm tra tự động đã khai báo, không chứng minh mọi câu diễn giải đúng toàn bộ quan hệ và/hoặc hay OCR chính xác tuyệt đối. Đọc thêm rubric từng câu, đặc biệt F11–F16. `semantic_review=NOT_RUN` giữ nguyên đến khi có đánh giá thực. Không dùng kết quả chưa chạy để báo PASS.

## Hợp đồng đọc ô từ phiên770

Từ772: promptv9, projectionv1. Khi có lookup hợp lệ, BE chỉ xuất dữ liệu ô đã
chọn và ghi số statements tự do bị loại trong `trace.grounding.projection`.
Không có lookup mà tự chép số từ bảng vẫn bị chặn; ID/citation ngoài scope vẫn
lỗi. Một câu trả lời dạng trích ô không tự chứng minh đủ các điều kiện ở đoạn
văn khác. F09 đã PASS ở một lượt mới sau sửa (20.672s), không retry. Đủ19câu với
promptv9 chưa chạy; không cộng PASS từ cohort khác.

Ở phiên770, backend dùng promptv8 và catalog ôv2. Trợ lý chọn định danh ô; backend lấy
nguyên giá trị/header/chủ thể từ nguồn và ghi trace `grounding.cell_proofs`.
`answer_cell_selection_required` là lỗi model chưa tuân hợp đồng chọn ô, không
phải lỗi hết token và không phải không có dữ liệu. Giữ lượt lỗi; không tự chạy
lại với khóa mới. `answer_context_budget_exceeded` vẫn là lỗi dung lượng evidence;
budget nay gồm cả catalog và quan hệ đọc, không chỉ các chunk.

Với phiên còn publication/index hợp lệ, không cần cleanup/init/upload/compile lại.
Để tiến trình đang mở nạp mã mới: Ctrl+C ở cửa sổ `serve`, chạy lại
`.\test-v1-e2e.ps1 serve`, chờ sẵn sàng rồi thực hiện lượt đánh giá có chủ đích.
Không tự reset checkpoint hoặc coi kết quả replay là đánh giá mới. Chỉ mục mới
sẽ có quality report v3; không cần reindex chỉ để dùng catalog đọc ô trên index cũ.

Kiểm chứng770 hiện chỉ có3câu API mới, mỗi câu một POST: F09FAIL, F12/F17PASS,
không gộp với kết quả769. Đủ19câu trên hợp đồng mới **NOT_RUN**; quota còn hạn chế,
không tự nâng hạn mức. Nhãn gold hiện còn draft và semantic review vẫn NOT_RUN.
