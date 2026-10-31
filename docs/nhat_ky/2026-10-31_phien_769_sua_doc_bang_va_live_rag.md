# Phiên 769 — Sửa cách đọc bảng và kiểm thử RAG thật

Ngày 2026-10-31. Yêu cầu: tìm nguyên nhân, sửa F06/F09/F15 rồi chạy đủ 19 câu với model thật, không retry để làm xanh kết quả. **Chưa hoàn tất mục tiêu chất lượng: bản cuối đạt 17/19, còn F09 và F12.**

## Chẩn đoán từ bằng chứng đầu tiên

- F06 thực tế hỏi Ngôn ngữ Anh/học bạ, đáp án nháp 19. Nhận định ban đầu trong trao đổi đã nhầm sang hàng khác; đã đối chiếu lại bộ câu hỏi, PDF và nguồn đã niêm phong. Hàng đúng nằm trong evidence, không phải PDF sai số. Rerank nhận JSON bảng có cell IDs, khóa lặp và chuỗi `\\n`; context có thể thiếu header.
- F09 có hàng Luật với giá trị22 ở cột học bạ nhưng từng bị abstain. Header nằm ở một chunk khác; kiểm citation chỉ chứng minh nguồn/ID, không chứng minh model chọn đúng cột.
- F15 có ngoại lệ ở hạng4, song model chọn đoạn chung ở hạng1–2. Nguồn đầy đủ; đây không phải vượt token hoặc thiếu capacity.
- Canonical native đánh dấu cả hàng header thật `header=false`. Chunker cũ chỉ lặp header khi có cờ, nên bảng bị chia rời header. Không sửa âm thầm canonical hoặc gán mọi bảng cùng schema chỉ vì số cột giống nhau.

## Thay đổi

1. `knowledge/index/presentation.py`: nhận đúng serialization bảng do chunker tạo, sinh bản đọc theo hàng, chuẩn hóa khoảng trắng cho rerank. Legacy/custom/unparsed giữ text gốc. Không đoán header hay mở rộng ô gộp trong bản đọc; raw structure, spans, cell IDs, notes và nguồn giữ nguyên. Rerank ghi presentation version vào trace và request digest.
2. `answer/projection.py` dùng cùng bản đọc khi tính byte và tạo prompt. `drafting.py` nâng v5→v6 cho đọc đúng hàng/cột, xem hết evidence, đối chiếu quy định chung/ngoại lệ. Không thêm ngành, điểm hoặc regex đáp án vào logic sản phẩm.
3. Sau đợt v6 vẫn thiếu header, thêm `table_context.py`/`table_support.py`: phụ thuộc đọc dẫn xuất từ snapshot native đã ghim. Chỉ nhận bảng parsed/không requires_review/không ô gộp; header ứng viên toàn chữ trước số thứ tự liên tục. Qua trang cần khớp đồng thời nguồn/binding, vị trí đầu-cuối trang, khung ngang, mép trang, số cột và số thứ tự kế tiếp. Không dùng riêng cột giống nhau hoặc ô trống để ghép. Cả chain và basis `native_numbered_table_boundary/v1` được ghi lại.
4. Context bổ sung tối đa4 chunk header/hàng cuối đã niêm phong, giữ toàn bộ primary; không vừa allowance thì ghi no_room. Hỗ trợ cùng input/version, tuân metadata và `_hits`/manifest. `validate_results` vẫn kiểm quyền, receipt, nguồn và index trước/sau inference. `header=false` gốc không bị đổi. Prompt v7 nhận mapping support evidence IDs. Không gán năm/đơn vị/phương thức theo liên kết.
5. Đây là heuristic giới hạn cho bảng native đánh số và layout đơn giản. Header chứa số, cấu trúc gộp/OCR, bảng không đánh số hoặc thiếu dấu hiệu giữ unresolved. Không tuyên bố giải được mọi bảng PDF.
6. Assistant admissions đổi byte budget qua API có revision fence: revision4/57344 → revision5/69632 → revision6/**81920**. Cận top20+4 chunks là71605 byte; input upper bound83564, cộng output4096 vẫn dưới context131072. Model/context/output/quota/candidate50/top20 không đổi. Byte evidence khác token thực đo.

Giữ nguyên nguồn, publication/index manifest, checkpoint, provider và toàn bộ dirty work trước phiên. Không restart serve, reindex, publish hoặc upload/OCR lại.

## Hai cohort model thật, giữ kết quả lỗi

Mỗi cohort mới tạo19 conversations/turns, mỗi câu một POST. Không recovery, không quay lại từng câu khi sai. Giữa hai cohort có sửa code và prompt; không gộp các câu PASS ở hai cohort thành kết quả19/19.

| Cohort | Phiên bản | Kết quả | Thời gian |
| --- | --- | --- | --- |
| admissions-once-769 | v6 | **16 PASS / 3 FAIL / 0 NOT_RUN**: F04/F06/F12 model_abstained | 246.609s |
| admissions-once-769-final | v7 + phụ thuộc bảng | **17 PASS / 2 FAIL / 0 NOT_RUN** | 295.797s |

Cohort cuối F06 và F15 đạt. F09 trả20 thay22, trích đúng hàng và header nhưng đọc sai cột; F12 vẫn model_abstained dù context đã cấp quan hệ nguồn. Không biết lý do nội bộ của model chỉ từ trạng thái abstain. Do đó chưa thể nói đã sửa xong cả ba câu, hoặc regression chất lượng đã đạt toàn bộ. Ba câu negative F17–F19 đạt.

Audit cuối:19 conversations riêng,19 turns completed (bao gồm câu sai/từ chối); embedding19/rerank19/chat19, tất cả attempt1/codeok. Cùng task inference hash, promptv7, cấu hình và index manifest trong cohort. Evidence max62511 byte, prompt max31756 token; tổng usage696149. Không lỗi token/context/quota hoặc unknown reservation mới. Quota10M giữ, used9426181/reserved123455, khả dụng450364. Không tự nâng quota hoặc giải phóng reservation lịch sử để chạy tiếp.

Kiểm thử gọi backend hiện tại qua HTTPX ASGI/lifespan với auth, ModelOps DB, Qdrant và provider thật; **không phải Playwright/UI**. Serve người dùng vẫn chưa được nạp lại. Nhãn vẫn `draft_agent_read_pdf_not_human_approved`; semantic review độc lập NOT_RUN.

## Kiểm chứng mã

- Focused ban đầu23PASS. Regression phụ thuộc bắt lỗi header và hàng cuối cùng table ref cùng chọn header:10PASS/1FAIL; sửa phân biệt role rồi focused33PASS. Sau guard đầu header/ô gộp, focused18PASS; Ruff13file PASS. Giữ log lỗi, không bỏ assertion.
- Full unit sau batch: **562PASS/1FAIL**,31.17s,exit1. Lỗi nền đúng ID `tests/unit/test_source_purge_716.py::test_accept_rechecks_publication_after_preview_before_preparing_purge`, invalid_identity tạiworkspaces/access.py39. Hai guard nhỏ cuối được kiểm lại focused18PASS; full gate vẫn FAIL, không gọi toàn repo PASS.
- API cô lập đầu:44PASS/1FAIL,355.34s, do assertion phiên bản còn v5 khi prompt đã v6. Cập nhật contract sang v7 và chạy lại batch45test gồm scope672/answers648/hybrid655: **45PASS**,387.45s,exit0. Database `qnu_v1_test_4a5fbffe5a324aad` và `qnu_v1_test_66c3b1c0b8af42ad` đãdrop; legacy sentinel preserved.
- Offline dựng context cho cả19 ranked lists của cohort v6 bằng nguồn thật rồi `validate_results`:19/19 không lỗi, evidence tối đa62511byte. Không gọi embedding/rerank/chat trong kiểm tra này.
- Không chạy FE build vì không sửa frontend. Kiểm UTF-8 không BOM/LF, local links và diff riêng.

## Artifacts và việc còn lại

Local ignored artifacts (không commit corpus/đáp án thô):

- [Cohort v6](../../tmp/admissions-once-769/admissions-answers.json), [audit v6](../../tmp/admissions-once-769/audit.json).
- [Cohort v7](../../tmp/admissions-once-769-final/admissions-answers.json), [audit v7](../../tmp/admissions-once-769-final/audit.json); cùng thư mục có manifest/dispatches ghi trước POST.
- Log integration và receipt ở `backendV1/storage/context636/` của hai DB riêng; kết quả cohort768 giữ nguyên.

Việc tiếp theo cần giải quyết là ràng buộc chọn ô với header/đại lượng và kiểm hỗ trợ ngữ nghĩa; v7 vẫn chỉ kiểm citation hợp lệ, chưa ngăn được câu trả lời trích đúng nguồn nhưng sai cột. F12 cần đối chiếu cách model dùng liên kết hàng thay vì nới luật ghép tùy tiện. Không sửa nhãn/expected, thêm từ khóa câu test hoặc retry đến khi PASS.
