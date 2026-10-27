# Phiên679 — Bốn đợt frontend còn thiếu

Người dùng xác nhận triển khai cả bốn đợt trong kế hoạch: backup, orphan cleanup,
search source inspection và retrieval evaluation. Đọc AGENTS, memory, skills FE/
clean code/admin design, mã API thật và Git trước khi thực hiện. Không cài Haystack,
Meilisearch hay sửa BE. Không chạy thao tác xóa/corpus/model thật.

Đã thêm màn sao lưu và dọn tệp dưới Operations với quyền admin, preview/ack,
receipt/retry cùng hash/key. Search có toàn văn/bảng/metadata/citation, kiểm
publication và liên kết chính xác về version/OCR. Evaluation là trang riêng của
collection, chọn active snapshot, gán nhãn bằng đoạn đọc được, human ack, so sánh
dense/hybrid/rerank và xuất JSON/CSV. Không dựng lịch sử BE không tồn tại.

Chỉ sửa FE theo phạm vi; route tree do plugin sinh. Giữ auth, ModelOps, BE và
chỉnh sửa sẵn có. Full287PASS giữ244ID cũ+43mới; trọng tâm43PASS, regression51PASS;
Biome542tệp0/0/0; typecheck/build PASS; probe67411PASS/6768PASS; bundle11PASS. Các
nhãn trạng thái cuối được kiểm lại UI/build/lint theo rủi ro. Lệnh/count/exits
và các lượt FAIL trong phát triển ghi trong report/verification, không bỏ test.

Đã kiểm 10 ảnh browser fixture với dữ liệu tổng hợp, desktop/390×844 sáng/tối,
sửa overflow tên tệp; thử tải JSON/CSV từ nút thật thành công. Tab đã đóng, viewport
đã reset và helper riêng đã dừng. Chưa live BE/SSO/model/worker/storage, chưa quality
benchmark hoặc toàn ma trận thiết bị. Không migrate/reindex/restart/deploy/push.

[Báo cáo](../bao_cao/context679/REPORT.md), [verification](../bao_cao/context679/verification.json),
[hướng dẫn35](../quy_trinh/35_frontend_sao_luu_don_tep_va_danh_gia_rag.md),
[snapshot](../memory/snapshots/2026-10-27_session_679.md).
