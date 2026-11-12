# Phiên 930 — Sửa ngõ cụt trang rà soát sau khi lưu và thêm soát lại theo phiên bản

## Phạm vi và nguyên nhân

Tiếp nối phát hiện của phiên 929: sau khi lưu text version 1 cho nguồn
`src_c0321a0193f9`, route rà soát theo `textVersion=1` không còn nội dung để làm
việc. Version 1 chưa có kết quả soát, còn 13 gợi ý chờ duyệt và 2 gợi ý "Cần dò"
của version 0 không còn đường truy cập; giao diện không cho biết đang xem bản nào,
không có nút soát lại và không có cách quay về kết quả cũ. "Bỏ qua" vẫn chỉ là
quyết định cục bộ của phiên UI.

Người dùng đã duyệt kế hoạch P0/P1: thêm ngữ cảnh phiên bản, trạng thái rỗng có
hành động, chế độ chỉ đọc cho bản lịch sử; thêm endpoint soát lại theo phiên bản
và luồng lưu có xác nhận, giữ người dùng ở trang rà soát sau khi lưu.

Không reset/seed/reindex, không sửa `0020_reverse_flow`, không đổi dữ liệu hay lượt
cũ. F13 (chất lượng RAG) nằm ngoài phạm vi.

## Thay đổi

### Backend

- Thêm `POST /text-review/checks/rerun` (202) nhận `{version, retry}`:
  - Kiểm quyền ghi và version phải tồn tại (404 nếu không).
  - Nếu đã có lượt kiểm tra cho version: lượt `running`/`completed`/`cancelled`
    hoặc `retry=false` trả nguyên trạng thái, không xếp hàng lần nữa.
  - `retry=true` chỉ xếp hàng mới khi lượt gần nhất `failed`/`uncertain`; lượt cũ
    được giữ nguyên và worker tạo lượt cha mới với `trace.retry_of`.
  - Job id `qnu:v1:spelling:{run_id}:{version}` (thêm `:retry:{check_id}` khi thử
    lại) để lặp request không sinh job trùng.
  - Hàng đợi chưa cấu hình trả 503 `spelling_queue_unavailable`; lỗi gửi job trả
    503 `spelling_rerun_failed`.
- Bổ sung 5 ca integration: xếp hàng + replay, lượt đã xong là trạng thái cuối,
  retry lượt lỗi, quyền ghi/version không tồn tại, hàng đợi không khả dụng.

### Frontend V2

- Trang rà soát tải danh sách lượt kiểm tra của mọi version (poll 5 giây) thay vì
  chỉ version hiện tại, và lọc theo version của văn bản đang xem.
- Header hiển thị `Bản vN`; bản cũ hơn bản hiện hành có nhãn `· lịch sử`, banner
  cảnh báo và chế độ chỉ đọc: ẩn nút lưu, vô hiệu hóa Áp dụng/Bỏ qua/Sửa tay/Hoàn
  tác, chỉ giữ "Về bản hiện hành".
- Trạng thái rỗng có hành động thay vì ngõ cụt: "Soát bản vN" mở hộp thoại xác
  nhận chi phí token; "Xem kết quả bản vM" mở bản đã có kết quả; bản lịch sử chỉ
  mời quay về bản hiện hành.
- Hộp thoại lưu có ba lựa chọn: Tiếp tục sửa, Chỉ lưu (giữ hành vi cũ: lưu, gửi
  chuẩn bị nội dung rồi về chi tiết nguồn), và Lưu và soát lại (lưu, xếp hàng soát
  lại, ở lại trang rà soát bản mới).
- Sau khi lưu, trang giữ banner xác nhận (`savedVersion`) và trạng thái chờ soát
  (`recheck`) để không báo sai "chưa có kết quả" trong lúc worker chưa tạo lượt.
- Dải trạng thái ở trang chi tiết đọc mọi version: khi bản hiện hành chưa soát,
  hiển thị "Bản vN chưa soát · kết quả bản vM: X vị trí" kèm liên kết "Xem bản vM"
  và "Soát bản mới", không còn dẫn tới trang rỗng.
- Thêm helper `spellingChecksForVersion`, `latestSpellingCheckVersion` và API client
  `rerunTextReview`/`useRerunTextReviewMutation`.

## Kiểm chứng

- Backend, DB cô lập:
  `uv run --env-file ../.env python -m scripts.test_database tests/integration/test_ocr_text_review_651.py -q -p no:cacheprovider`
  → **31 ca PASS**, 2 cảnh báo, 111,58 giây; DB test đã dọn, `pytest_exit: 0`.
- Ruff format/check trên router, schema và test đã sửa: PASS.
- Biome `check --write` trên 6 tệp frontend đã sửa: PASS (1 tệp được format).
- `npm run typecheck` (`tsc --noEmit`): PASS.
- Trình duyệt (Vite 3002, API 8002 đang chạy nền):
  - Đúng URL người dùng gửi (`textVersion=1`): hiển thị `Bản v1`, trạng thái rỗng
    "Bản v1 chưa có kết quả soát chính tả", "Kết quả gần nhất thuộc bản v0", 396
    đoạn, hai nút "Soát bản v1" và "Xem kết quả bản v0".
  - "Xem kết quả bản v0": nhãn `Bản v0 · lịch sử`, banner chỉ đọc, 15 chờ duyệt +
    2 cần dò, toàn bộ nút quyết định bị vô hiệu hóa; quay lại bản hiện hành được.
  - "Soát bản v1": hộp thoại nêu rõ 396 đoạn và chi phí token; bấm Hủy, không tạo
    job hay lượt soát mới.
  - Hộp thoại lưu trên nguồn `src_a07e29184b04` (version hiện hành có kết quả):
    áp dụng 1 gợi ý cục bộ rồi mở hộp thoại, thấy đúng "1 vị trí ... bản v1" và
    ba lựa chọn; bấm "Tiếp tục sửa", không ghi dữ liệu.
  - Trang chi tiết `src_c0321a0193f9`: dải trạng thái "Bản v1 chưa soát · kết quả
    bản v0: 17 vị trí" với liên kết "Xem bản v0" và "Soát bản mới".
- Không tạo text version, preparation intent, lượt soát hay bản xuất bản mới
  trong phiên này; quyết định áp dụng thử đã bị bỏ khi rời trang.
- Full Pytest cô lập: **NOT RUN**. Baseline lịch sử **FAIL 4/1627** của phiên 928
  giữ riêng, không chạy lại để làm xanh.

## Giới hạn và bước sau

- "Bỏ qua" vẫn chưa lưu server (P2 chưa làm); hộp thoại lưu đã ghi rõ điều này.
- Version 1 của nguồn test vẫn chưa được soát; người dùng có thể tự bấm "Soát bản
  v1" và chịu chi phí token.
- `savedVersion`/`recheck` còn trên URL sau khi tải lại cho tới khi bấm "Đóng";
  không ảnh hưởng dữ liệu.
- Backend vẫn từ chối lưu bản lịch sử (yêu cầu version/hash mới nhất); giao diện
  chặn từ trước để không tạo 409 khó hiểu.
- E2E trên dữ liệu dev, không phải benchmark chất lượng OCR/chính tả.
- Working tree chưa commit; không push/deploy.
