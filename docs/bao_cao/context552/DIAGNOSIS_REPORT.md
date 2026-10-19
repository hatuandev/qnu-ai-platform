# Phiên552 — Chẩn đoán có nhãn nguồn

## Lần live551

Raw response/context551 đã được cleanup: **NOT_AVAILABLE**. Metadata còn lại tại context551 ghi table scope ambiguity và API unit mismatch; không thể suy chính xác từng selector/category/index/owner từ raw đã mất. Không tái tạo response gốc bằng ví dụ tổng hợp và không tuyên bố payload đã sửa là response live cũ.

## Tái hiện synthetic trước bản vá

File `backend/tests/test_semantic_selector_v2.py` dùng fixture có mã dạng chuỗi và câu có điều kiện/loại trừ đã biết độc lập với output pipeline. Lượt red đầu **29FAIL/2PASS**: câu nhiều mã bị từ chối; chọn vế phủ định không tạo scope issue; chưa có contract v2/parser/binder theo phiên bản. V1 sai/thiếu owner vẫn bị chặn trong các ca tương thích. Lượt `registry-red` thêm1FAIL chứng minh evidence chỉ có trong private registry, không được cấp trong packet, cần guard riêng.

Trong kiểm thử tích hợp sau patch v2 ban đầu, trường hợp cell meaning cùng limitation lộ lỗi kiểm hash sau mutation dẫn xuất. Ca này được giữ trong test B09 và sửa thứ tự verify/apply; không giả định model551 đã trả payload hỗn hợp đó. Một lỗi test replacement fixture cũng được sửa để dùng `proposal_base` đã xác minh; không bỏ guard replacement của ứng dụng.

## Bằng chứng mới

Live552 chỉ được ghi sau checkpoint mã/test. Mỗi lượt phải ghi source/revision/hash, context/call, contract/schema/policy hash, requested/effective mode, provider/model thực và raw response hash. Lỗi binding có category/index/owner/target ở diagnostic; không log toàn prompt hoặc corpus. Kết quả thực tế và đường dẫn bằng chứng ở [validation](VALIDATION_REPORT.md).
