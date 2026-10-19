# Context553 — đối soát ngữ nghĩa Context552

Trạng thái khảo sát: checkpoint offline, chưa có phê duyệt ứng dụng. Không coi JSON/schema/binding PASS là xác nhận ngữ nghĩa. Mọi phân loại dưới đây là phân tích của agent, không phải quyết định của người dùng.

Đã kiểm 14 SHA-256 trong manifest và envelope/input hash trước sửa. Original proposal: `80308912eba6ceecfcec7283e7ebedef225fe756000eb57c14602b0b58bbcfc3`. Source `offline544/draft544`, MD `cf52345162c89e025def74b988d1b3e2bb160e761776365cf113d40573ed2d7c`, structured `d687fe7c4950ec44663cb84e11eb4e5e20ba4b62586422fdcb3bab03d49c147f`.

## Bốn annotation

| Annotation/source | Scope hiện tại | Scope nguồn hỗ trợ / phủ định | Reference / hành động |
|---|---|---|---|
| qnu:l006 | Toàn bảng t001, cả ba khoản | Khoản 1: đơn vị chung và c10–c12 dự kiến; khoản 2: chỉ sáu dòng nhóm A, hồ sơ thiết bị 2027, không sửa chỉ tiêu/2025/B; khoản 3: riêng AM-0007, loại AM-0070; ngoại lệ thực tập riêng nhóm B | Cần tách assertions nguyên văn, có binding/span riêng, không chia lại source vật lý. Bổ sung l014/l015 và khoản 3 l012. Không suy rằng gia hạn thiết bị là thuộc tính số SV. |
| qnu:p049 | Toàn bảng t001 | Ngày chốt 2025/2026 và dự kiến 2027 riêng theo nhóm cột; quy tắc tính tỷ lệ cùng năm là chung | Tách các mệnh đề ngày theo c04–c06/c07–c09/c10–c12, giữ toàn câu tỷ lệ. Không dùng ngày lập 18/10/2026 làm năm dữ liệu. |
| qnu:p050 | r003 | r003 có mã chuỗi AM-0007; r004 AM-0070 bị loại trừ nguyên văn | Đủ căn cứ trình xác nhận scope, chưa scope_confirmed. Giữ toàn câu và footnote mã. |
| qnu:p051 | c11 | Header nguồn: c10=2027/Quy mô/Chỉ tiêu (SV), c11=2027/Dự kiến/Ước tính (SV), c12=2027/Ước đạt/Tỷ lệ (%). Mệnh đề “Ước tính” chỉ c11; phần “ba cột” là context về nhóm năm, không đủ để đồng nhất ba đại lượng | Giữ đầy đủ cả hai câu, riêng c11; quan hệ cả nhóm 2027 dự kiến được khoản 1 l006 và mốc p049 hỗ trợ độc lập. c05/c08 Ghi nhận 2025/2026 bị loại. Đủ căn cứ trình người dùng xem cách tách; không tự mở rộng c11. |

## Tám issue gốc (ID giữ nguyên trong checkpoint đối soát)

| Issue / ID | Evidence / liên quan assertion | Phân loại / bước tiếp |
|---|---|---|
| 1 ctxissue:caaaec699ea13848e145573699939a54240f13984efbc7b77767fd164ec32a6d | p050, r003/r004, mã đọc từ raw fields | Đủ căn cứ trình xác nhận riêng scope r003; chưa ghi quyết định. |
| 2 ctxissue:7796dfd6b7e8ef92fea6bf823a8618825a249295d3404d17d8716d9d6b4ff3fb | p051 và toàn header t001, l006.1/p049 | Đủ căn cứ trình đối chiếu c11 và quan hệ năm độc lập, không mở rộng đại lượng. |
| 3 ctxissue:020f5d0bffea6fabb4605e5fb4c53ccd72fb7320a3cf354dd477b5b81000a21e | s030 + toàn bộ hậu duệ Điều 15, gồm l012/p084/s031 | Heading không đủ; đã tìm được body. Liên quan sử dụng dữ liệu trong đánh giá và ngoại lệ B; cần context/revised proposal, không not_applicable. |
| 4 ctxissue:081d95e2e836c4aad52bfa72977575c1e7c732c094cffc52c9d42cc4c9fb26c4 | l012: điều kiện tính, cấm đổi năm, thực tập thiếu chữ ký | Liên quan assertion ngoại lệ B và cách dùng chỉ tiêu; giữ phủ định và tham chiếu II, không tự áp điểm Q vào giá trị Bảng1. |
| 5 ctxissue:d62e3952982928c38fa242bf17a7cf867f7ffdceb5f4599915d9260884e65530 | p084 đầy đủ, gồm năm, unknown, mã, nhóm A/B | Có liên quan nhiều assertion; cung cấp nguyên đơn vị cho reviewer, không đưa cả đoạn thành điều kiện chung cho mọi ô. |
| 6 ctxissue:8e49ed2d0da6280c39ddd1f068fe53c891bed6999eb732e92cd8214758ec9c11 | p090 mở Phụ lục II; l014/l015 là nội dung thực tế | Có liên quan A/B; bổ sung hai bộ điều kiện tách biệt, không xác nhận không liên quan. |
| 7 ctxissue:54652f308c332f02a379469f0d2ee9fc8f62a858dbc4ac98fb0d8adc515d9bda | s036 + l015, p092 và bảng ngoại lệ | Body II.2 có đủ điều kiện và hậu quả sau 30 ngày; liên quan nhóm B, loại nhóm A; cần giữ context. |
| 8 ctxissue:891a560adef9b2010117727e0188690b2d36c25c0dda4d594ebe58456cd9920d | docx_footnote_2: 0012/00027/AM-0007 là chuỗi | Liên quan định danh c02 các dòng r001/r002/r003. Không đổi sang int, không coi 0012=0120 hay AM-0007=AM-0070. |

## Quyết định kỹ thuật trước khi sửa

Tái sử dụng NoteScope và EvidenceBinding: thêm chế độ assertion nội bộ có phiên bản, trích đoạn có tọa độ canonical, phạm vi đích và các reference binding. Selector v1/v2 giữ wire schema cũ; annotation/snapshot cũ tiếp tục replay theo chế độ cũ. Quan hệ mới dẫn tới đơn vị dẫn xuất chứa đúng span, không dẫn cả mixed source unit vào mọi dòng. Full source vẫn có trong bản đối soát để người duyệt kiểm phủ định. Stage bổ sung issue riêng cho mỗi assertion; giữ tám issue gốc. ContextBuilder mở nội dung hậu duệ heading với ngân sách, không chỉ tiêu đề và không gọi lại toàn tài liệu. Không dùng từ điển ngữ nghĩa hoặc LLM viết lại nguồn.

Các issue deferred liên quan vẫn mở; bản đối soát mới không thể áp dụng bằng cách bấm đồng ý chung. Đường xử lý thực tế là changes_requested/phân tích lại có source-bound evidence trước khi người có quyền quyết định trên đúng revision/hash. Không nhập file offline thành approval.
