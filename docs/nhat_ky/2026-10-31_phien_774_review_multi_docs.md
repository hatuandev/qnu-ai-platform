# Phiên774 — Review độc lập bộ E2E đa tài liệu773

User yêu cầu xem bản triển khai sau chạy prompt có ổn không. Chỉ review và chạy
kiểm tra cục bộ; không sửa app/test chính, không nhập key/modelcall, không
cleanup/init/restart/publish/reindex hoặc nâng quota. Giữ dirtydiff trước phiên.

Đọc AGENTS/frontendV1AGENTS,Context773, skill RAGevaluation/benchmarkcontract và
clean code; đối chiếu source/runner hiện tại. Bộ53case có thật, checkpoint theo
tài liệu và combinedIndex đã thêm, nhưng chưa đủ điều kiện nghiệm thu.

## Phát hiện

1. **P1 — Gold bị đổi và có nhãn sai so với PDF.** Multi-docs không giữ nguyên
   F01–F19: nhiều ID đổi câu/đại lượng, trong đó F09 không còn là case Luật từng
   sửa, F12 không còn case nối trang. F10 mới gán Luật15,trang3/dòng28; F12 mới
   gán ĐGNL600,trang3. Đọc và render PDF gốc xác nhận Luật ở trang4/dòng32 với
   dãy20/22/750/20. Sư phạm Toán/Lịch sử ở trang2, header học bạ là dấu gạch ở
   những hàng đã kiểm, không phải24/22 trong nhãn mới. Không lấy gold cũ làm
   chân lý: bằng chứng đã đối chiếu trực tiếp PDF; cần khôi phục regression cũ
   và rà lại mọi gold mới theo trang/ô nguồn trước live.
2. **P1 — Assistant mới mất budget đã giải quyết ở768–772.** POST chỉ đặt
   top20/candidate50/rerank, không context_max_bytes; backend default16000byte.
   Phiên cũ dùng81920 và từng có envelope68699byte cho F09. Sau cleanup mọi
   assistant mới quay về16K; cần đo/bố trí budget cho3nguồn qua ModelOps trước
   dispatch, không chỉ nâng quota. Chưa chạy live nên không khẳng định tất cả
   query chắc chắn lỗi; thiếu cấu hình/preflight là lỗi hiện hữu.
3. **P1 — Checker đa nguồn có thể PASS dù không có căn cứ cho cả hai facts.**
   checkAnswer chỉ kiểm số tồn tại và mọi hash thuộc danh sách3nguồn, một page
   bất kỳ đúng. Không có mapping fact→document/page/row/column/year/version.
   Probe thực MX01 với2số50/15 nhưng chỉcitationreport2024/wrongrevision vẫnPASS.
   Đây không phải semantic judge hay kiểm đủ hai nguồn. Không tuyên bố53case
   chứng minh scope/năm đúng từ checker này.
4. **P2 — Scope single thiếu binding mở ra cả kho.** Nếu documents[target] chưa
   có published ID, document_idsundefined vẫn gửi createconversation. Probe
   actualaskAdmissionQuestion xác nhận khôngBLOCKED và bỏ scope. Phải fail closed
   trước POST và kiểm scope khi dùng checkpoint cũ, không fallback all.
5. **P2 — Parse hàng nghìn thành thập phân gây falseFAIL.** Regex/replacecomma
   hiện coi300.000→300,4.681→4.681. I25-07 đòi300000 nên một câu trả lời đúng
   theo cách ghi trong nguồn vẫnFAIL; BC24-01/MX04 tương tự4681. Cần parser số
   theo ngữ cảnh/đơn vị hoặc facts chuẩn hóa, không replace mọi dấu chấm vì có
   tỷ lệ/chiều cao thật là số thập phân. Probe Node dùng đúngregex đã tái hiện.
6. **P2 — Chat vẫn fail-fast.** catch cuối mỗi case throwerror, thoát vòng53case
   ngay câu đầuFAIL; câu độc lập sau đó NOT_RUN trái yêu cầu chạy đủ khi có thể.
   Cần phân biệt lỗi case với lỗi hạ tầng/quota và tổng hợpFAIL cuối stage,
   tuyệt đối không retry. Origin của error cũng chưa ghi vì chỉ nhận khi hàm
   ask trả thành công; failedfresh không được theo dõi đầy đủ.
7. **P2 — Tự nâng quota20M thiếu dự toán/phê duyệt phạm vi.** Upload/chat gọi
   ensureSessionQuota20M, helperPUT khi hạn hiện có nhỏ hơn20M, không chỉ phiên
   chưaconfigured. Không có dự toán28trang/compiler/review/53request và không
   kiểm đủ số còn trước live. Đây là đường nâng hạn tự động, trái prompt trước;
   chưa xảy ra trong phiên mới vì provider-setup đangBLOCKED.

Thêm giới hạn: ensureAssistant catchget/put thànhnull nên nuốt lỗi cấu hình;
combinedindex chỉ kiểm active/nonempty/provider, không đối chiếu inputs đủ3version.
Nhãn mới chưa có source locator/quote/fact map cấu trúc, vẫn draft; unit773 chủ
yếu kiểm shape/count/hash, không chứng minh chốngscope hoặc gold đúng.

## Kiểm chứng thực chạy

- CWDfrontendV1: `npx vitest run tests/admissions-multi-docs-773.test.ts tests/admissions-replay-764.test.ts`
  **14PASS**,exit0 (6+8),646ms. Không lặp lại claim22 từ ảnh.
- `npm run test:e2e:typecheck`:PASS,exit0.
-3probe Vitest trên actualexportask/question runner với fakeAPI: tái hiện
  scopeundefined/falsePASSđa nguồn/budgetundefined,3/3reproduction,exit0.
  Đây là xác nhận3hành vi sai, không là qualitygatePASS. File probe tạm đã chuyển
  sang ignored`tmp/review774/review-774.probe.test.ts`, không thay app/testchính.
- Node numericprobe đúngregex:300.000→300;4.681/4.826→4.681/4.826;62,7→62.7.
- PDFread/render trang4 xác nhận hàngLuật; artifactignoredtmp/review774/floor-page4.png.
- `test-v1-e2e.ps1 status`:phiên93faa11f0caf/live,provider-setupBLOCKED,modelstages
  vànavigationNOT_RUN,admissionscheckpointchưacó. Không có bằng chứng đãupload/
  OCR/compiler/publish/chat53case trên modelthật. Chờ key là đúng điểm dừng,
  không cần cleanup/init lần nữa.
- GitdiffcheckPASS. Build/fullbackend/liveNOT_RUN; không sửa ứng dụng nên không
  thêm modelcall hoặc lặp gate rộng không liên quan.

Khuyến nghị sửa các lỗi trên trước khi đánh giá53câu. Review chưa sửa logic,
khôngnớigold hoặc xoá dữ liệu. Báo cáo773 giữ nguyên làm lịch sử, review774 là
kết luận đối chiếu mới.
