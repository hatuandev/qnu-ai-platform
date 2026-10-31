# Phiên 746 — Compiler chia phần: projection gọn, reasoning có hợp đồng, chạy song song có giới hạn

## Bằng chứng hiện tại (quan sát, không phải giả định)

- PDF `docs/tai_lieu/tuyen_sinh/TB điểm sàn 26.pdf` (8 trang, nhiều bảng và ghi chú) từng lỗi `chat_output_truncated`: prompt33666, completion8192, `finish_reason=length`, content rỗng, toàn bộ allowance vào reasoning (đã ghi ở phiên745).
- Sau khi sửa phiên745 (planner v2), cùng tài liệu chia thành 15 phần; phần1 mất khoảng2 phút với input20126/output6352, phần2 khoảng2 phút với input24426/output6601. Đây là số đo trên lượt chạy thật của người dùng, dùng để đối chiếu chứ không phải trạng thái hiện tại của mã.
- Đọc mã và diff xác nhận bốn nguyên nhân: (a) planner v2 dùng 25% allowance output làm **proxy kích thước nguồn UTF-8**, nên chia rất nhỏ; (b) mỗi phần gửi lại `structure` toàn tài liệu và context toàn cục; (c) các phần chạy tuần tự trong một session; (d) adapter chưa từng gửi tham số reasoning nên model tự tiêu hết ngân sách output cho suy luận.

## Nguyên nhân và cách sửa

1. **Chia quá nhỏ** — planner v3 ước lượng **nội dung sẽ viết** (`tokens × 0.5 × 3` byte) thay vì kích thước nguồn, và đóng gói theo 70% capacity input. `finalize_plans` dựng lại từng phần bằng `input_tokens` thật, chỉ tách đôi nhóm vượt biên; không cắt nguồn, không hạ kiểm tra.
2. **Lặp context** — projection v3 chỉ gửi phần sở hữu + context có **vai trò tường minh** (`table_header`, `caption`, `section_heading`, `document_note`, `neighbour_note`), kèm outline gọn (số trang, hình dạng bảng, tiêu đề, đuôi ghi chú) thay cho census từng block. Liên kết bảng nhiều trang chỉ tạo khi header signature và trang kề thật sự khớp.
3. **Reasoning** — thêm hợp đồng khai báo ở ModelOps (`reasoning_policy_v1`) với cổng `verified`; chỉ áp dụng khi quản trị viên khai báo đúng tham số của endpoint. Không suy đoán theo tên model, không hardcode `enable_thinking`/`reasoning_effort`/`chat_template_kwargs`.
4. **Tuần tự** — scheduler bounded (`asyncio.Semaphore`, mặc định2, tối đa4) chỉ cho các phần **thực sự độc lập**; mỗi phần một session riêng, một writer cho bản partial, ghép theo `segment_index` chứ không theo thứ tự hoàn tất.
5. **Tiến độ** — progress API thêm `received`, `concurrency`, `active_segments`, `elapsed_seconds`, `planner_version`, thời lượng từng phần; E2E chỉ in khi trạng thái đổi và báo rõ phần nào đang chạy.

## Tương thích với lượt đang dở

- Projection v2 được **đóng băng byte** trong `compilation/segments_v2.py` + `projection.py` + `units.py`; test ghim `input_sha256` và prompt hash. Nhờ vậy run 15 phần đang dở vẫn dựng lại đúng request cũ.
- `plan_from_scope` thiếu `projection_version` ⇒ đọc là v2; phiên bản lạ bị từ chối 409 `compilation_segment_version_unsupported`. Phần v3 ghi `projection_version` vào scope/config/request_hash.
- Phần đã hoàn tất được tái sử dụng; phần đang `running` không có raw giữ `uncertain`, không gửi lại. Không sửa DB, checkpoint, artifact hay migration của lượt cũ.
- E2E: nếu lượt trước `failed` và `planner_version` khác `qnu.compiler.plan/v3`, chặng tạo run mới thay vì resume (khóa riêng `-floor-replan-v3-<run>`), giữ lịch sử trong `compilationHistory`. Lượt lập lại **không** đánh dấu `compilationRecoveryOf`, để không tiêu mất lượt phục hồi output duy nhất nếu lượt mới lại bị cắt.

## Kiểm chứng và giới hạn

- Chỉ đọc mã/diff/trạng thái; chạy `py_compile` + import và các script đo planner (không gọi model, không ghi DB).
- Tự kiểm tra phát hiện một lỗi thật trong validator chính sách reasoning: `tasks` bị đối chiếu như *tác vụ → mức* nên mọi chính sách có `tasks` đều bị từ chối. Đã sửa thành *mức → danh sách tác vụ*, cấm một tác vụ xuất hiện ở hai mức, cấm danh sách rỗng; thêm regression cho cả ba trường hợp.
- Số đo planner trên tài liệu 8 trang/105 hàng: **2 phần** ở output8192 (input lớn nhất 67821, ước lượng viết 12176/12288 byte) và **1 phần** ở output16384. Trước đây 15 phần. Đây là ước lượng của planner, chưa phải thời gian chạy thật.
- Test/build/lint/typecheck/E2E: **NOT RUN** theo yêu cầu hiện tại. Không restart serve, không migration, không reindex, không deploy, không push.
- Chưa đo tốc độ thật khi chạy song song; `max_num_seqs=8` của vLLM **không** được hiểu là nhanh gấp8 hay dành8 slot cho compiler. Chưa xác nhận endpoint Qwen/vLLM chấp nhận tham số tắt suy luận, nên mặc định vẫn là `server_default`.
- Rủi ro còn lại: reasoning có thể vẫn tiêu hết output nếu chính sách chưa `verified`; planner v3 vẫn là heuristic (không phải tokenizer thật); review POST vẫn chạy đồng bộ.

## Việc tiếp theo

Người dùng dừng cửa sổ serve bằng Ctrl+C, chạy lại `serve`, rồi `run admissions-compilation`. Chỉ khi PASS mới đi tiếp publication/chat. Không cleanup/init/upload/OCR lại.
