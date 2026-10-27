# Rà soát backendV1 và quy trình ngược

Kết luận: **CHANGES REQUESTED**. Luồng lifecycle có phần lõi hoạt động, nhưng hai
API cập nhật hiện hữu chưa áp cùng quy tắc hủy lượt hỏi. Đây là review; chưa sửa
mã ứng dụng hoặc thay đổi hệ thống đang phục vụ.

## Hai lỗi cần sửa trước

1. **[P2] Tắt/bật trợ lý qua API cập nhật không hủy lượt đang chạy.**
   `PUT /workspaces/{id}/assistants/{id}` chỉ ghi `is_active`. Nếu tắt rồi bật
   trước khi model trả kết quả, checkpoint cuối thấy trợ lý đã bật và giữ nguyên
   revision, nên vẫn hoàn tất lượt hỏi cũ. Probe qua HTTP thực nhận `200`,
   `turn.status=completed`, có kết quả. Mong đợi thao tác dừng phải hủy bền vững
   lượt cũ; bật lại chỉ cho phép lượt mới. FrontendV1 hiện dùng chính API PUT này.
   [Chỗ ghi trạng thái](../../../backendV1/qnu/domains/assistants/service.py#L87),
   [client](../../../frontendV1/src/features/assistants/requests.ts#L77).
2. **[P2] Lưu trữ/mở lại hội thoại qua API cập nhật có cùng lỗ hổng.**
   `PUT /workspaces/{id}/conversations/{id}` chỉ ghi `status`, không hủy turn
   đang chạy. Archive rồi mở lại trước phản hồi model vẫn lưu câu trả lời cũ.
   Probe nhận cùng kết quả `200/completed/có kết quả`. Nút lưu trữ hiện dùng PUT.
   [Chỗ ghi trạng thái](../../../backendV1/qnu/domains/conversations/service.py#L83),
   [client](../../../frontendV1/src/features/conversations/requests.ts#L63).

Luồng lifecycle mới đã gọi hủy bền vững trước pause/archive, vì vậy bật lại không
thể phục hồi quyền của lượt đã hủy:
[effects](../../../backendV1/qnu/domains/lifecycle/effects.py#L50).
Cần gom các đường ghi trạng thái về cùng quy tắc nghiệp vụ, giữ quyền ở server,
transaction, audit và quyền sở hữu hội thoại; thêm hai regression vào suite.
Không chữa bằng cách chỉ giấu nút trên giao diện.

## Những phần đã kiểm tra đạt

Chạy lại hai file integration lifecycle: **23 PASS / 0 FAIL / 0 SKIP**.
Bao phủ xóa có thể khôi phục và giữ bytes gốc; chặn truy cập qua nguồn/kho đã ẩn;
preview gắn actor/hash/expiry và thao tác đồng thời; quyền restore; loại nguồn cũ
khỏi tìm kiếm/lịch sử chat; pause/resume qua lifecycle; hủy index/Compiler và
không nhận kết quả muộn; hủy auto-review; giữ publication/index cũ khi thay thế
chưa xong hoặc lỗi; dọn đúng generation, retry lỗi Qdrant; restore cần index lại.
Không coi kết quả đó là bằng chứng hai API PUT cũng có cùng hành vi.

## Phần còn thiếu hoặc cần quyết định sản phẩm

- `delete` hiện là thùng rác có thể khôi phục, giữ file gốc, raw OCR và lịch sử.
  Chưa có purge vĩnh viễn; nếu cần phải có retention, xem trước và xác nhận riêng.
- Dọn index cũ có thao tác thủ công, nhưng blob mồ côi/tệp tạm chưa có GC tổng quát.
  Chỉ nên dọn object đã chứng minh không còn được tham chiếu; giữ bằng chứng hợp lệ.
- Bản sao lưu là evidence archive; chưa có phục hồi toàn bộ DB/credential/Qdrant.
  Cần quy trình sao lưu hạ tầng và diễn tập restore trước vận hành chính thức.
- Compiler review có báo cáo nhưng chưa là điều kiện bắt buộc của approve/publish.
  Nếu muốn ngăn xuất bản khi còn lỗi ngữ nghĩa quan trọng, cần chính sách xử lý
  finding hoặc quyền bỏ qua có lý do, ghim đúng phiên bản/hash. Đây là cải tiến,
  không phải lỗi của hai probe. Xem
  [kiểm quyết định duyệt](../../../backendV1/qnu/domains/knowledge/publication/decisions.py#L220).
- Thay thế hiện từng document; nguồn dùng chung nhiều document được chặn an toàn
  bằng `replacement_shared_source`, chưa có thay thế theo nhóm nguyên tử.
  [Mã kiểm tra](../../../backendV1/qnu/domains/lifecycle/replacement.py#L115).

Ưu tiên: sửa hai đường cập nhật trạng thái; sau đó hoàn thiện dọn dữ liệu dẫn
xuất và phục hồi vận hành. Chính sách gate review làm khi chốt quy trình duyệt.
Không cần thêm framework để sửa các điểm này.

## Kiểm chứng và giới hạn

Cwd `backendV1`, Python `.venv/Scripts/python.exe`, hạ tầng PostgreSQL/Qdrant cục
bộ thật và model HTTP tổng hợp. Harness tạo DB riêng `qnu_v1_test_*`, chặn egress
ngoài loopback; không dùng tài liệu/credential AI thật.

- `-X utf8 storage/context661/run_tests.py tests/integration/test_lifecycle_659.py tests/integration/test_lifecycle_runtime_659.py -q`: exit 0, 23 PASS, 119,52 giây pytest.
- `-X utf8 storage/context661/run_tests.py storage/context663/test_api_stop_probes.py -p tests.integration.conftest -q`: lượt cuối exit 1, 2 FAIL, 26,56 giây pytest. Hai failure đều ở assertion kết quả thực `200/completed/có kết quả`.
- Lượt probe đầu: nhánh assistant lỗi dựng request vì dùng response có trường thừa;
  không tính là tái hiện lỗi ứng dụng. Đã lọc đúng trường request và chạy lại cả hai
  nhánh; không sửa hoặc nới assertion. Nhánh conversation đã tái hiện từ lượt đầu.
- Ba DB thử đã dọn, legacy sentinel/version giữ; quan sát lại không còn DB thử
  trong receipt và không còn collection vector v1. Chi tiết ở receipt.
- Full suite **NOT RUN trong review này**; 565 PASS ở Context662 là kết quả lịch sử.
  Không chạy AI thật, benchmark chất lượng, restore hạ tầng, migration hoặc restart.

[Probe tái hiện](lifecycle_api_probes.py) · [Receipt](verification.json) ·
[Hợp đồng lifecycle](../../../backendV1/docs/resource-lifecycle.md) ·
[Giới hạn backup](../../../backendV1/docs/operations.md).
