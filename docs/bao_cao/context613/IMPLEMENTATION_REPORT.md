# Context613 — Thay đổi triển khai

## Kết quả kỹ thuật

Compiler có thể tổng hợp bản lớn qua nhiều request và manifest, giữ hợp đồng cũ khi bản nhỏ còn vừa giới hạn. Ngân sách phân giải theo profile provider/model/endpoint; khi thiếu profile phải công bố cơ sở dự phòng chưa xác minh. Không thay model, source hoặc publication đang chạy.

## File và trách nhiệm

| Phạm vi | Thay đổi |
|---|---|
| [compilation_schemas.py](../../../backend/app/modules/knowledge/compilation_schemas.py) | Manifestv2 và nhóm có ID/hash/nguồn/thành viên; Draftv1 giữ nguyên |
| [compilation_runtime_schemas.py](../../../backend/app/modules/knowledge/compilation_runtime_schemas.py) | Check toàn cục, hợp đồng quan hệ liên nguồn, chính sách tài nguyên và nhãn cơ sở ngân sách |
| [compilation_manifest.py](../../../backend/app/modules/knowledge/services/compilation_manifest.py) | Inventory và capacity422, kiểm toàn vẹn/coverage nhóm |
| [compilation_engine.py](../../../backend/app/modules/knowledge/services/compilation_engine.py) | Tổng hợp từng nhóm, closure bằng chứng, ghép manifest và ledger, giữ checkpoint |
| [compilation_synthesis.py](../../../backend/app/modules/knowledge/services/compilation_synthesis.py) | Chia review thực theo dung lượng, giữ raw context và kiểm đủ ID/index |
| [compilation_cross_source.py](../../../backend/app/modules/knowledge/services/compilation_cross_source.py) | Chọn cặp ứng viên tổng quát, proposal/review/direction, budget CPU riêng, pending/NOT_RUN trung thực |
| [compilation_transport.py](../../../backend/app/modules/knowledge/services/compilation_transport.py) | Offered enums/opaque handles cho hợp đồng mới |
| [compilation_contracts.py](../../../backend/app/modules/knowledge/services/compilation_contracts.py) | Binding v1/v2 cùng các bất biến source/year/ID/proof và group hash |
| [compilation_validation.py](../../../backend/app/modules/knowledge/services/compilation_validation.py) | Đọc lại và tính lại kết quả check toàn cục/cross ledger |
| [compilation_service.py](../../../backend/app/modules/knowledge/services/compilation_service.py), [compilation_store.py](../../../backend/app/modules/knowledge/services/compilation_store.py) | Lỗi capacity xác định, receipt rõ stage, loại lineage bị chặn; không tự retry |
| [compilation_modelops.py](../../../backend/app/modules/knowledge/services/compilation_modelops.py) | Resolve profile, giao ngân sách fallback, provenance ngân sách và hash protocol/prompt |
| [wiki_schemas.py](../../../backend/app/modules/knowledge/wiki_schemas.py) | Không ép mọi model theo cap context32K/output8.192 |
| [ModelOps schemas](../../../backend/app/modules/modelops/schemas.py), [token_limits.py](../../../backend/app/modules/modelops/services/token_limits.py) | Profile endpoint-bound, validation/merge capability từng phần; explicit null để xóa |
| [inference_service.py](../../../backend/app/modules/modelops/services/inference_service.py), [provider_service.py](../../../backend/app/modules/modelops/services/provider_service.py) | Kiểm đầu ra trước key lease cho generate/stream; giữ profile khi form cũ cập nhật |

Tổng17appfiles trong phiên613; những thay đổi Context608–611 còn dirty trước đó được giữ. Test mới [test_compilation_groups_613.py](../../../backend/tests/test_compilation_groups_613.py); fixture ownedDB600 chỉ thêm prefix613, các kiểm tra host/owner/môi trường không bị bỏ.

## Tương thích và giới hạn

- Không migration DB, không sửa schema lưu nguồn hoặc parser. Registry/StorageDriver/ModelOps và quyền hiện có tiếp tục được dùng.
- V1 không bị nâng cap âm thầm; v2 là hợp đồng tổng khác với hợp đồng request nhỏ. Đọc lại vẫn kiểm source hash, binding và reviewer ledger.
- Quan hệ mới vẫn là proposal trong bundle `review_only/unpublished`. Có một verdict supported nhưng cờ temporal_roles=false vẫn không đủ kiểm chứng; không dùng riêng chữ supported để duyệt.
- Khi nguồn hoặc cấu hình đổi, checkpoint khác protocol/hash không tự được nhập. Harness thử nguồn cũ có provenance tái sử dụng riêng; chưa cung cấp tính năng migration production.
- Đợt này không thêm UI cấu hình token profile. API provider hiện có nhận trường mới; hướng dẫn quản trị nêu rõ fallback chưa xác minh.
- Việc khám phá liên nguồn hiện là các cặp có nhãn trùng/gần nhau được giới hạn tài nguyên; không khám phá đầy đủ mọi alias/khái niệm hoặc quan hệ giữa mọi cặp. Những liên kết không cùng request và chưa được kiểm không tự có hiệu lực.

Xem [thiết kế](DESIGN.md), [hướng dẫn model](MODEL_LIMITS_GUIDE.md) và [đối soát ứng viên](RECONCILIATION_REPORT.md). Kết quả kiểm chứng thực được báo riêng; thay đổi kiến trúc không tự chứng nhận nội dung nguồn hoặc chatbot serving.
