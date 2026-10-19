# Context553 — chờ người dùng đối chiếu

**WAITING_FOR_REVIEW**, chưa phải E2E PASS. Đây là bản đối soát offline; chưa có pending revision trong UI thật.

- Original proposal hash: `80308912eba6ceecfcec7283e7ebedef225fe756000eb57c14602b0b58bbcfc3`.
- Revised proposal hash cuối: `33d9cdae6fc80547aa6243ea7ac11d94b9fa5e9b765398ba569a9905870f3fc2`.
- Nguồn giữ nguyên `offline544/draft544`, input hash `0cced34a5a3b7b356bd4ce63df80e49749ec41e3686860b27809c8ed2549dcd9`.
- Bản sửa do agent đối soát nguyên văn từ checkpoint, không phải response ModelOps mới. Không gọi lại tài liệu/22 packet.

Mở [bản đọc đủ 12 assertion và tám issue](../../../backend/storage/context553-review-final/REVIEW.md), [proposal](../../../backend/storage/context553-review-final/proposal.json) hoặc [context bổ sung nguyên văn](../../../backend/storage/context553-review-final/review-context.json). [Bản gốc](../../../backend/storage/context552-checkpoint-06689f8f17dc/REVIEW.md) được giữ nguyên; các bản trung gian cũng được giữ để audit, không phải bản đang đề nghị duyệt.

## Nội dung cần xem

- Năm assertion từ l006: quy định chung, nhóm cột 2027, thiết bị nhóm A trong 2027, AM-0007 và ngoại lệ nhóm B. Mỗi quan hệ có span/đích riêng; không áp cả ba khoản cho mọi dòng.
- Bốn assertion p049: ba mốc thời gian theo đúng nhóm cột, một quy tắc tỷ lệ cùng năm. Ngày lập không thay năm dữ liệu.
- p050: r003 AM-0007, không phải r004 AM-0070.
- p051: c11 Ước tính; c10 Chỉ tiêu và c12 Tỷ lệ ước đạt có vai trò riêng. Quan hệ dự kiến chung cho 2027 nằm trong assertion khác; c05/c08 Ghi nhận bị loại.
- Footnote mã: c02 ở r001/r002/r003, giữ chuỗi 0012/00027/AM-0007.

## Tám issue gốc

| Issue | Căn cứ đã đối chiếu | Hành động phù hợp sau khi người dùng đọc |
|---|---|---|
| 1, p050 | Mã raw r003/r004, toàn câu gồm phủ định | Xác nhận scope riêng r003 hoặc yêu cầu sửa. Chưa ghi scope_confirmed. |
| 2, p051 | Header nhiều tầng c10/c11/c12 và c05/c08, toàn văn note, quan hệ năm độc lập | Đối chiếu và xác nhận riêng c11 hoặc yêu cầu sửa. |
| 3, s030 | Toàn Điều15 gồm các mục con, l012 và p084 | Tham chiếu liên quan: xác nhận đã đọc nội dung/giới hạn và các assertion liên quan; không chọn “không liên quan”. |
| 4, l012 | Điều kiện tính, cấm đổi năm, hồ sơ thực tập thiếu chữ ký và ngoại lệ | Xác nhận đã đối chiếu tham chiếu liên quan hoặc yêu cầu sửa. |
| 5, p084 | Toàn đoạn về chủ thể/năm/unknown/mã/A/B | Đọc nguyên văn, xem từng assertion được liên kết; không áp cả đoạn như một điều kiện chung. |
| 6, p090 | Dẫn nhập II và toàn điều kiện II.1/II.2 | Xác nhận hai ngoại lệ tách biệt, giữ điều kiện cần. |
| 7, s036 | Body II.2/l015, giới hạn 30 ngày, hậu quả quá hạn, loại nhóm A/an toàn | Xác nhận tham chiếu liên quan đến assertion nhóm B. |
| 8, footnote_2 | Giữ mã có 0 đầu | Xác nhận tham chiếu liên quan đến định danh, không chuyển mã sang số. |

Tất cả tám ID thực có trong proposal/bản đọc; không thay bằng ID tự tạo. Mười scope issue mới bảo vệ các assertion bổ sung. **18 issue vẫn mở**, không có quyết định duyệt tự động. Phân tích của agent không thay người có quyền.

Đã tìm được nội dung các heading/reference và source bindings cần cho đối soát này; không còn thiếu body Điều15/II.2. Phạm vi phân tích là Bảng1, chưa phải xác nhận toàn tài liệu. Điều cần tiếp theo là quyết định thực tế trên exact source/revision/hash và đường nạp pending revision hợp lệ. Không nhận file offline hoặc một câu đồng ý chung làm toàn bộ quyết định ứng dụng.

Khi thực hiện qua ứng dụng: actor phải có quyền server, nguồn phải là draft đúng revision/hash, mỗi issue có bằng chứng và lý do riêng. Giao diện cũ được mở rộng để hiện assertion/reference và hành động `related_context_reviewed`; chưa đưa checkpoint này vào UI thật. Chỉ sau quyết định hợp lệ mới kiểm apply/persist/rebuild/retrieval thật.

**Chưa áp dụng, chưa xuất bản, chưa reindex dữ liệu thật.** Không commit/push/deploy/migrate production. Các actor TEST trong kiểm thử không duyệt nguồn này.

Kiểm chứng cuối: focused261/FE18/Ruff13/Biome3/build PASS; full vẫn FAIL18/2398PASS/17SKIP, exact18ID/cause nền, 23 case thêm PASS, không regression mới. Database test đã dọn. Thư mục runtime test `backend/storage/context548-runtime-eba155eff9ff` còn tồn tại vì kiểm duyệt tự động chặn xóa với “blocked by policy”; cleanup Storage chưa hoàn tất. Không ảnh hưởng tính nguyên vẹn checkpoint, không coi đây là cleanup PASS.
