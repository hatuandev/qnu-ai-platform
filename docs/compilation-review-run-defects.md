# Lỗi chạy quy trình biên dịch và rà soát tự động — phân tích chi tiết

- Ngày phân tích: 2026-11-16
- Môi trường: dev trên Kiri (Postgres/Redis/Qdrant/MinIO trong Docker, API `:8002`, worker arq)
- Bộ dữ liệu: tài liệu PDF đã upload trong phiên E2E Kiri ngày 2026-11-16, collection `col_af3ea7d6d5fb`
- Nhà cung cấp model: `prv_5b58c60f8a22` (openai_compatible, `qwen3.8-27b-q4`), context 163.840, max output 32.768
- Phạm vi: hai lỗi chặn quy trình — (1) biên dịch dừng vì `compilation_draft_invalid`, (2) rà soát tự động không chạy được vì `compilation_review_segment_too_large`. Câu trả lời Q04/Q06/Q09 **ngoài phạm vi** theo yêu cầu tạm gác của người dùng.
- Trạng thái: cả hai lỗi đã được sửa và kiểm chứng ở tầng lập kế hoạch trên dữ liệu thật; **phiên chạy lại đầu-cuối (biên dịch mới + rà soát thật) CHƯA CHẠY** — cần khởi động lại API/worker dev và có duyệt riêng.

## 1. Tóm tắt nhanh

| # | Mã lỗi | Nơi phát sinh | Nguyên nhân gốc (một dòng) | Trạng thái |
|---|---|---|---|---|
| 1 | `compilation_draft_invalid` | Biên dịch, phần số 2 của run `cmp_bad6bec5f85b` | Hợp đồng bản nháp đặt trần cứng 100 trích dẫn/đoạn; model trả đoạn trích 129 ô của một bảng dài và bị từ chối dù nội dung đúng nguồn | Đã sửa, đã kiểm chứng bằng chính phản hồi đã lưu |
| 2 | `compilation_review_segment_too_large` | Chuẩn bị rà soát tự động | Một đoạn văn trích cả bảng 321 ô buộc mỗi lượt review mang theo toàn bộ bảng làm ngữ cảnh bắt buộc; cận trên đầu vào 156.320 > capacity 131.072; hệ thống từ chối cắt bằng chứng nên dừng | Đã sửa bằng cơ chế "chưa xác định tường minh"; kiểm chứng bằng replay dữ liệu thật |

## 2. Dòng thời gian sự cố (giờ UTC, đọc từ DB dev)

| Thời điểm | Sự kiện | Bằng chứng |
|---|---|---|
| 01:51:17 | Yêu cầu biên dịch lần 1, run `cmp_bad6bec5f85b`, 8 phần | `kb_compilation_runs.requested_at` |
| 01:54:59 | Run 1 thất bại `compilation_draft_invalid`; 2 phần xong, 1 phần lỗi (phần số 2, `cseg_4392c3119780`), 5 phần chưa chạy; đã tiêu 150.346 token | `status=failed`, `error_code`, `usage_tokens` |
| 01:57:58 → 02:01:52 | Chạy lại thành run `cmp_2b61941ad6e0`; 8/8 phần hoàn tất; tiêu 318.383 token | `status=completed` |
| ~02:04 (trước bước duyệt) | Yêu cầu "Rà soát tự động" trả 422 `compilation_review_segment_too_large`; **không có bản ghi review nào được tạo** | Không tồn tại dòng trong `kb_compilation_reviews` cho hai run trên |
| 02:05:22 | Duyệt có xác nhận bỏ qua rà soát (preview `pprev_3b3cc49af08f`), lý do đã lưu: "Rà soát tự động không chạy được vì một đơn vị nội dung vượt ngân sách model và hệ thống không cắt nộ…" | `kb_publication_previews.review_ack.mode=skipped` |
| 02:05:26 | Xuất bản (preview `pprev_193c18ff5c00`) — nội dung lên phục vụ **chưa qua rà soát tự động** | `kb_publication_previews` |

Hệ quả vận hành: một lần biên dịch lỗi làm mất toàn bộ công đã sinh (fail-fast theo phần lỗi), lần chạy lại tốn thêm 318.383 token; rà soát tự động không có kết quả nên bước duyệt phải dùng đường "bỏ qua có xác nhận".

## 3. Lỗi 1 — Biên dịch dừng vì `compilation_draft_invalid`

### 3.1. Triệu chứng

- Run `cmp_bad6bec5f85b` chạy 8 phần theo cơ chế biên dịch phân đoạn v2; phần số 2 (`cseg_4392c3119780`) nhận phản hồi của model rồi bị từ chối với `compilation_draft_invalid` (HTTP 502 ở API).
- Phần lỗi kéo theo: 5 phần còn lại không được chạy (fail-fast), run chuyển `failed`.
- Bản nháp gốc của phần lỗi vẫn được lưu nguyên vẹn ở artifact `raw_response` (19.944 byte phong bì provider, phần nội dung 16.853 ký tự).

### 3.2. Bằng chứng gốc

Phân tích artifact `raw_response` của phần lỗi (chỉ đọc cấu trúc, không in nội dung tài liệu):

- `finish_reason = stop` — model trả xong bình thường, không bị cắt.
- Nội dung là JSON hợp lệ: 5 mục, 11 đoạn.
- Một đoạn có **129 trích dẫn**; các đoạn khác 14, 13, 10, 10, …
- Hợp đồng cũ tại [schemas.py](../backendV1/qnu/domains/knowledge/compilation/schemas.py) khai báo `DraftParagraph.citations = Field(min_length=1, max_length=100)`.
- Pydantic ném `too_long` cho mảng 129 phần tử → `build_draft` bọc thành `compilation_draft_invalid`.

Đây **không phải model bịa nguồn**: đoạn văn trích nguyên một bảng dài theo từng dòng/ô, đúng chỉ dẫn "mỗi đoạn phải có citations là các ID đã cấp". Lỗi nằm ở trần đếm cứng của chính hệ thống.

### 3.3. Nguyên nhân gốc

Giới hạn `max_length=100` được đặt như một biện pháp phòng ngừa, nhưng số trích dẫn của một đoạn trung thành với bảng tỷ lệ thuận với kích thước bảng, không phải dấu hiệu bất thường. Bảng 321 ô → đoạn hợp lệ có thể vượt 100 trích dẫn bất kỳ lúc nào. Giới hạn này vô tình biến "trung thành với nguồn" thành lỗi hợp lệ.

### 3.4. Đã sửa

- Bỏ trần đếm: `citations` chỉ còn `min_length=1` ([schemas.py](../backendV1/qnu/domains/knowledge/compilation/schemas.py)).
- Giữ nguyên kiểm tra ngữ nghĩa: mọi trích dẫn phải thuộc đúng tập nguồn đã cấp cho đoạn (`validated_draft`, `parse_segment_draft`); trích dẫn lạ vẫn bị từ chối như cũ.
- JSON schema gửi cho model (structured output) sinh trực tiếp từ Pydantic model ([drafting.py](../backendV1/qnu/domains/knowledge/compilation/drafting.py), [segments.py](../backendV1/qnu/domains/knowledge/compilation/segments.py)) nên cũng không còn `maxItems` cho `citations`; không có đường thứ hai giữ trần cũ.

### 3.5. Kiểm chứng

- Đưa **chính phản hồi đã lưu** của phần lỗi qua schema hiện tại: **PASS** — 5 mục, 11 đoạn, đoạn nhiều nhất 129 trích dẫn được chấp nhận.
- Run chạy lại `cmp_2b61941ad6e0`: 8/8 phần hoàn tất (lần chạy này model trả bản nháp ngắn hơn nên không chạm trần cũ; xác nhận sửa nằm ở lần kiểm chứng raw response phía trên).
- Bộ kiểm thử lập kế hoạch review: 13/13 hàm PASS (chạy trực tiếp theo quy ước phiên, không dùng pytest).

## 4. Lỗi 2 — Rà soát tự động vỡ vì `compilation_review_segment_too_large`

### 4.1. Triệu chứng

- Yêu cầu rà soát tự động cho run `cmp_2b61941ad6e0` (đã biên dịch xong) bị từ chối ngay ở bước chuẩn bị với `compilation_review_segment_too_large` (422); không có dòng review nào được ghi.
- Người dùng buộc phải duyệt với xác nhận bỏ qua rà soát; nội dung được xuất bản mà không có báo cáo rà soát tự động.

### 4.2. Cơ chế gốc (vì sao không chỉ là "model yếu")

1. Rà soát tự động đánh giá **từng đơn vị**: từng ô bảng, từng đoạn văn. Với bảng, đơn vị là ô — không phải cả bảng.
2. Một đoạn văn trích **cả một bảng** (bảng `ocr_7199f52c20db:ev_p011_b001`, **321 ô**). Theo quy tắc hiện hành, các ô của bảng được đoạn dẫn phải có mặt trong lượt review làm **ngữ cảnh bắt buộc (chỉ đọc)** — để model có thể đối chiếu đoạn với đúng các ô. Không được cắt bớt vì như vậy là che bằng chứng.
3. Đo lường trên dữ liệu thật (chỉ đọc, từ material đã lưu):

   | Đoạn | Bảng | Ô | Payload bắt buộc | Cận trên đầu vào |
   |---|---|---|---|---|
   | `section:22:paragraph:1` | 1 bảng | 321 | 115.118 byte | 156.320 |
   | `section:23:paragraph:1` | 1 bảng | 321 | 115.226 byte | 156.417 |

4. Ngân sách khả dụng của provider: context 163.840 − output dành riêng 32.768 = **capacity 131.072**; trần lập kế hoạch an toàn là 85% = **111.411** (phần dư là headroom chống timeout prefill). Cận trên bảo thủ theo byte UTF-8 (không phải số token đo bằng tokenizer — hệ thống cố ý dùng cận trên để không bao giờ vượt vật lý) vượt cả capacity.
5. Bộ lập kế hoạch đã thử mọi cách chia hợp lệ: tách phần thành nhóm đoạn, đẩy ô đã sở hữu sang ngữ cảnh chỉ đọc — nhưng cái làm phần này to **chính là 321 ô bắt buộc**, không phải phần sở hữu. Khi nhóm đoạn là bất khả phân (một đoạn văn không thể tách) và vẫn quá ngân sách, lựa chọn duy nhất trung thực trước đây là **dừng và báo lỗi**.

### 4.3. Vì sao không thể "cứ cắt bớt bảng"

- Cắt bớt ô khỏi ngữ cảnh = model đánh giá đoạn mà không thấy phần bảng còn lại → kết luận sai hoặc giả "đã kiểm tra".
- Tách các ô sang phần nguồn khác nhưng bỏ đoạn khỏi tầm nhìn của phần đó = đoạn không còn được đối chiếu khi review các ô.
- Rơi ô/thay đổi nhóm hàng = phá bất biến "giữ nguyên hàng/ô, không cắt rời nguồn".
- Đánh dấu "đã đạt" khi chưa soát = báo cáo giả — bị cấm bởi bất biến trung thực.

### 4.4. Đã sửa — "chưa xác định tường minh" thay vì giả vờ

Cơ chế mới (chỉ kích hoạt đúng vào thế bí hợp lệ, không phải đường tắt chung):

1. **Phát hiện**: khi một nhóm đoạn bất khả phân vẫn vượt ngân sách sau mọi cách chia, và mọi đoạn trong nhóm đều trích các bảng nguyên khối vượt một lượt gọi, hệ thống tách riêng các đoạn đó thành một phần **không có nguồn sở hữu** ([parts.py](../backendV1/qnu/domains/knowledge/compilation/review/parts.py), `_limited_part`).
2. **Không gọi model**: phần này mang **đánh giá do server tự soạn**, trạng thái `uncertain`, `source_ids: []`, usage 0, giải thích cụ thể ("đoạn trích dẫn 1 bảng nguồn với 321 ô, vượt ngân sách ngữ cảnh của một yêu cầu review…") và hành động gợi ý ("Đối chiếu đoạn với bảng nguồn đã dẫn trước khi duyệt").
3. **Không mất ô nào**: toàn bộ 321 ô vẫn do các phần nguồn sở hữu và được rà soát đầy đủ; các phần đó vẫn gắn đoạn liên quan làm ngữ cảnh chỉ đọc để model đối chiếu ô với đoạn khi rà soát ô.
4. **Không tự động duyệt**: đánh giá `uncertain` chảy vào báo cáo như một phát hiện thật. Cổng xuất bản vẫn bắt xác nhận **từng phát hiện** (hoặc bỏ qua có lý do) — cơ chế này không miễn trừ bước duyệt.
5. **Tái lập chính xác**: danh sách `preassessed_drafts` được ghi vào `scope` của phần, nên chạy lại/khôi phục giữa chừng, manifest và merge đánh giá đều khớp từng byte; phần đánh giá server được đưa qua đúng bộ kiểm tra schema của báo cáo trước khi lưu ([execution.py](../backendV1/qnu/domains/knowledge/compilation/review/execution.py)).
6. **Giữ nguyên các chốt chặn cũ**: nhóm hàng bị chia một phần (không thể đánh giá trung thực) → vẫn báo lỗi; phần preassessed nếu vẫn vượt ngân sách → vẫn báo lỗi; capacity quá nhỏ cho mọi thứ → vẫn báo lỗi. Hai kiểm thử bảo vệ các hành vi này còn nguyên và PASS.

### 4.5. Kiểm chứng

- **Replay trên dữ liệu biên dịch thật** của run `cmp_2b61941ad6e0` (2.248 nguồn, 2.042 đơn vị bản nháp), capacity 131.072, output 32.768, reasoning tắt:

  | Tiêu chí | Kết quả |
  |---|---|
  | Tổng số phần | 43 |
  | Phủ nguồn | 2.248/2.248 |
  | Phủ đoạn bản nháp | 2.042/2.042 |
  | Phần "chưa xác định" | 2 (phần 15 và 17, đúng hai đoạn bảng 321 ô; ~6,8–6,9 nghìn đơn vị đầu vào mỗi phần) |
  | Phần lớn nhất | 122.211 ≤ 131.072 |
  | Lệch khi chạy lại từ `scope` đã lưu | 0 |

- **Bộ kiểm thử phần review**: 13/13 hàm PASS, trong đó có test mới dựng đúng kịch bản bảng 161+ ô và kiểm tra: phần preassessed chỉ sở hữu đoạn bị chặn, `status=uncertain`, `source_ids=[]`, giải thích nêu đúng số ô, scope tròn vẹn qua `rebuild_part`, đánh giá server qua được `validate_content`, phủ đủ và duy nhất mọi nguồn/đoạn, mọi ô bảng vẫn thuộc các phần nguồn ([test_compilation_review_parts_744.py](../backendV1/tests/unit/test_compilation_review_parts_744.py)).
- Ruff và import smoke trên các tệp sửa: PASS.

## 5. Các phương án khác đã cân nhắc và lý do không chọn

| Phương án | Lý do không chọn |
|---|---|
| Tăng capacity/cho phép một lượt gọi lớn hơn | Vượt ngân sách vật lý của model (context − output); prefill lớn còn dễ bị timeout giữa lượt |
| Cắt bớt ô/bảng khỏi ngữ cảnh review | Mất bằng chứng; kết luận "đã soát" sẽ sai sự thật |
| Chia ô sang phần khác, đoạn đứng riêng | Đoạn không còn thấy đủ bảng để đối chiếu; tách nhóm hàng làm sai ngữ nghĩa đánh giá |
| Buộc model coi đoạn này "đạt" | Báo cáo giả — vi phạm bất biến trung thực |
| Chia nhỏ đoạn văn thành nhiều đoạn ngắn để vừa ngân sách | Sửa nội dung bản nháp ở tầng review là thay đổi dữ liệu ngoài phạm vi review; cần thiết kế riêng ở tầng biên dịch nếu muốn |
| Preassessed `uncertain` (đã áp dụng) | Trung thực, không mất dữ liệu, buộc người duyệt xem xét; đổi lại một số đoạn phải đối chiếu thủ công |

## 6. Việc còn lại (chưa chạy — không phải PASS)

1. **Chạy lại đầu-cuối trên Kiri**: biên dịch mới + rà soát tự động thật, xác nhận không còn hai mã lỗi trên và báo cáo review có đúng 2 phát hiện `uncertain` cho hai đoạn bảng. Việc này cần **khởi động lại API và worker dev** — chờ duyệt.
2. Cập nhật nhật ký/PROJECT_CONTEXT/WORK_LOG và memory sau khi có kết quả chạy thật.
3. Q04/Q06/Q09: tạm gác theo yêu cầu, không nằm trong tài liệu này.

## 7. Phụ lục — vị trí mã liên quan

| Thành phần | Tệp |
|---|---|
| Hợp đồng bản nháp (bỏ trần trích dẫn) | [schemas.py](../backendV1/qnu/domains/knowledge/compilation/schemas.py) |
| Sinh schema structured cho model biên dịch | [drafting.py](../backendV1/qnu/domains/knowledge/compilation/drafting.py), [segments.py](../backendV1/qnu/domains/knowledge/compilation/segments.py) |
| Lập kế hoạch phần review, fallback preassessed | [parts.py](../backendV1/qnu/domains/knowledge/compilation/review/parts.py) |
| Thực thi phần review, nhánh preassessed | [execution.py](../backendV1/qnu/domains/knowledge/compilation/review/execution.py) |
| Cổng xuất bản (xác nhận từng phát hiện / bỏ qua có lý do) | [review_gate.py](../backendV1/qnu/domains/knowledge/publication/review_gate.py) |
| Kiểm thử phần review | [test_compilation_review_parts_744.py](../backendV1/tests/unit/test_compilation_review_parts_744.py) |
