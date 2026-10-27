# Context612 — Nguyên nhân compiler chưa tổng hợp được

Ngày: 2026-10-23. Phạm vi: điều tra ngoại tuyến trên kết quả Context611 và mã hiện tại. Không sửa mã ứng dụng, gọi LLM, kết nối DB/MinIO/Qdrant, tạo revision, nạp vector hoặc xuất bản.

## Kết luận

**Lượt compiler thực bị chặn bởi giới hạn cấu trúc tổng hợp của ứng dụng, trước khi LLM được yêu cầu viết trang Markdown.** Ngoài lỗi đã phát sinh này, mô phỏng ngoại tuyến phát hiện thêm điểm chặn ngân sách ở chính hàm chia nhóm tổng hợp. Vì vậy chỉ tăng giới hạn số phần tử vẫn chưa đủ.

Đây là lỗi dung lượng và điều phối cần giải quyết trong compiler. Kết quả hiện tại chưa đủ căn cứ quy nguyên nhân cho khả năng tổng hợp của GPT-OSS, thiếu context của model hoặc parser DOCX làm mất nội dung.

## 1. Điểm dừng đã xảy ra trong lượt thực

Trong [compilation_engine.py](../../../backend/app/modules/knowledge/services/compilation_engine.py), dòng 436–440 ghép danh sách thực thể và assertion của mọi packet thành một đối tượng rồi gọi `CompilationDraft.model_validate(merged)`. Dòng 442 mới gọi `synthesis_batches`.

Trong [compilation_schemas.py](../../../backend/app/modules/knowledge/compilation_schemas.py), dòng 85–91 quy định một `CompilationDraft` tối đa 64 thực thể và 128 assertion. Sau trích xuất, tổng có 92 thực thể và 145 assertion. Tái hiện bằng dữ liệu đã lưu cho đúng hai lỗi `too_long`; tất cả phần tử riêng lẻ vẫn hợp lệ về schema.

Assertion ở đây là **dữ kiện có nguồn**, chưa phải liên kết giữa hai đối tượng. Lượt thực chưa đến `SynthesisDraft`, chưa tạo relations/sections cuối hoặc chạy Quality Gate cuối.

| Nguồn theo revision | Thực thể | Assertion | Thử riêng với hợp đồng tổng hiện tại |
|---|---:|---:|---|
| Nguồn 1, tài liệu mang tên 2024 | 70 | 103 | FAIL: 70 > 64 thực thể |
| Nguồn 2, tài liệu mang tên 2025 | 14 | 33 | Đạt giới hạn số lượng |
| Nguồn 3, tài liệu mang tên 2026 | 8 | 9 | Đạt giới hạn số lượng |
| Tổng | 92 | 145 | FAIL: vượt cả hai giới hạn |

Tên năm trong bảng chỉ nhận diện tài liệu; không dùng để gán năm dữ liệu cho từng assertion. Đạt giới hạn số lượng cũng không phải chứng nhận ngữ nghĩa.

**Nguyên nhân thiết kế:** compiler hỗ trợ nhiều packet, từng `PacketDraft` có giới hạn riêng 32/48, nhưng sản phẩm của toàn bộ packet vẫn phải vừa một draft tổng 64/128. Hai mươi hai đầu ra PacketDraft thành công, gồm cả trích bổ sung, cộng chính xác thành 92/145. Packet lớn nhất chỉ có 10 thực thể và 30 assertion: không có packet riêng nào cần vượt giới hạn mới tạo ra lỗi này.

Hàm chia nhóm có tồn tại nhưng nằm sau cổng kiểm tổng. Thêm nữa, dòng 471 và `bind_draft` còn dùng lại hợp đồng tổng khi ghép kết quả cuối. Chỉ chuyển vị trí chia nhóm sẽ để lại cùng vấn đề ở cuối luồng. Chỉ chia theo ba nguồn cũng chưa đủ vì nguồn 1 đã có 70 thực thể.

## 2. Điểm chặn tiếp theo được phát hiện ngoại tuyến

Thử trực tiếp hàm `synthesis_batches` với dữ liệu đã lưu, không đổi schema, không gọi model, cho lỗi `single_assertion_synthesis_budget`.

Tại dòng 151–152, planner dự phòng thêm **5.000 token cố định** ngoài 8.192 token đầu ra. Có bốn assertion mà chỉ một assertion cùng bằng chứng đã bị planner từ chối:

| Kiểm tra với trường hợp lớn nhất | Ngân sách dự phòng |
|---|---:|
| Request riêng, gồm đầu ra 8.192 | 20.839 / 24.000 |
| Cộng thêm dự phòng 5.000 của planner | 25.839 / 24.000 |

Cả 145 request tổng hợp đơn lẻ đều vừa ngân sách khi đo request ban đầu, chưa cộng dự phòng 5.000. Bốn request vượt vì phần dự phòng này; planner hiện không có phương án xử lý request đơn lẻ đó nên dừng. Các con số là **cận trên theo byte UTF-8 và framing do app tính**, không phải token đầu vào được provider đo.

Đây là điểm chặn kế tiếp có thể tái hiện, chưa phải lỗi đã xảy ra trong lượt compiler thực: lượt thực dừng sớm hơn ở mục 1. Không được tự bỏ dự phòng để tuyên bố hoàn tất. Thiết kế sửa cần đo riêng request tổng hợp, review và correction thực tế, giữ nguồn và chặn request nào thực sự không vừa.

## 3. Vì sao khó nhìn rõ nguyên nhân từ thông báo lỗi

`CompilationDraft.model_validate` phát sinh `ValidationError`. Nhánh xử lý trong [compilation_service.py](../../../backend/app/modules/knowledge/services/compilation_service.py), dòng 180–192, chuyển lỗi không phải `AppException` thành HTTP 502 / `KNOWLEDGE_COMPILATION_FAILED`. Biên nhận được ghi `uncertain` bởi `fail`.

Do đó lỗi dung lượng xác định bị hiển thị như một lỗi thực thi chung. Checkpoint vẫn giữ 91 đầu ra đạt contract và 5 lần từ chối JSON/schema có trạng thái xác định; việc đó không biến lỗi ghép thành vấn đề có thể giải quyết bằng retry model. Chạy tiếp cùng mã và dữ liệu sẽ lại gặp lỗi này.

## 4. Gộp trùng hoặc đổi model có giải quyết được không?

- Có 74 tên thực thể khác nhau trong 92 thực thể. Ngay cả gộp tất cả tên giống nhau vẫn vượt 64; phép gộp đó còn có thể sai nguồn/năm. Không dùng nó để sửa dữ liệu tự động.
- Có một thực thể không được assertion dùng đến. Bỏ riêng phần đó chỉ còn 91, không giải quyết giới hạn.
- Đối soát chính xác Context611 ghi 92 thực thể và 145 assertion khác nhau khi giữ nội dung, bằng chứng và đối tượng liên quan. Điều này không chứng minh không có trùng nghĩa; chưa đối soát ngữ nghĩa đầy đủ 145 assertion.
- Ba mươi hai assertion có trạng thái nguồn chưa xác định; đó không mặc định là lỗi. Có 116 assertion chưa có vai trò thời gian xác định, cần kiểm riêng phạm vi và bằng chứng, không lấy tên file lấp vào. Những điểm này chưa phải nguyên nhân của hai lỗi số lượng đã tái hiện.
- Đọc lại 96 biên nhận response lịch sử đều `finish_reason=stop`; không có call `SynthesisDraft`. Không có bằng chứng model đã thử viết trang tổng hợp rồi thất bại vì trần đầu ra.

## 5. Hướng sửa đề xuất

1. **Tách hợp đồng cho nhóm xử lý và manifest tổng.** Manifest chứa đầy đủ đối tượng và ánh xạ nguồn; tổng hợp theo nhóm phù hợp dung lượng, phạm vi và bằng chứng. Kiểm toàn cục vẫn bảo đảm ID, provenance, coverage, thời gian, điều kiện và ngoại lệ. Chạm cả điểm ghép đầu, ghép cuối và binding; không chỉ nới hai con số hoặc cắt bỏ dữ kiện.
2. **Sửa planner ngân sách tổng hợp.** Đo request thực cho từng giai đoạn và correction có giới hạn; phần dự phòng phải có phương án xử lý khi một đơn vị vẫn không vừa. Không cắt bằng chứng hoặc giả PASS.
3. **Báo lỗi dung lượng rõ ràng.** Trả giai đoạn, số lượng và giới hạn; phân biệt lỗi xác định với inference chưa rõ kết quả, tránh gợi ý retry tốn token.
4. **Đối soát 145 ứng viên đã lưu.** Xác định phần thực sự phục vụ topic, phần chỉ là ngữ cảnh và khả năng trùng nghĩa; giữ unknown đúng bằng chứng. Việc này phục vụ chất lượng, không phải lý do loại tùy ý để vừa cap.

Chưa triển khai sửa trong Context612. Chưa có cơ sở nói chỉ sửa hai điểm chặn thì toàn bộ nội dung sẽ được duyệt; synthesis, kiểm chiều quan hệ và Quality Gate cuối vẫn phải thực chạy khi triển khai.

## 6. Bằng chứng và kiểm chứng

Lệnh từ root: `backend/.venv/Scripts/python.exe .antigravity-bridge/validation/context612_diagnose.py`, exit code **0**. Mười hai kiểm tra chẩn đoán D01–D12 PASS theo kết quả mong đợi, bao gồm tái hiện compiler FAIL. Đây không phải 12 ca chứng minh compiler đã hoạt động.

Artifacts local, không đưa corpus vào Git: `backend/storage/context612/diagnosis.json`, `diagnosis-run.log`, `run-result.json`. Kiểm đủ biên 64/128, 65/128, 64/129; source hash và 381-proof snapshot khớp; xác nhận 22 đầu ra cộng đúng tổng; thử planner trực tiếp và đo đủ 145 request đơn lẻ. Harness chặn network, bỏ side effect của package export khi import các helper thật; không mock kết quả helpers. Không có network attempt trong lần kiểm chứng cuối.

Hash toàn bộ app Python, JSON Context611 và ba DOCX giữ nguyên trước/sau. Không cần tạo hoặc dọn DB thử vì không dùng DB. Storage cũ giữ nguyên theo chính sách bảo vệ. Không chạy full Pytest, benchmark, browser E2E hoặc inference mới: **NOT RUN**, phạm vi chỉ chẩn đoán và tài liệu. Full Context611 3586 PASS / 18 FAIL nền / 17 SKIP là kết quả lịch sử, không nâng thành PASS hiện tại.
