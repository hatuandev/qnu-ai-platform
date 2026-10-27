# ocr

Điều phối OCR qua ModelOps: revision, raw response, page/bbox/hash, canonical,
Markdown và manifest. ARQ run có lease/fence, quota và trace; API giữ bằng chứng gốc.

`review/` cung cấp text/ô đọc được, gợi ý chính tả và phiên bản sửa do người dùng
lưu. Hai artifact dẫn xuất được xác minh trước commit; OCR gốc bất biến.
Chưa có UI review hoặc binding bản sửa vào Compiler. Không tự publish/reindex.

Xem [contract](../../../docs/ocr-text-review.md) và
[ma trận tính năng](../../../docs/feature-port-matrix.md).
