# Context571 — Cấu trúc tài liệu và bản Markdown dễ đọc

Ngày 20/10/2026. Triển khai năm hạng mục trong prompt đã được người dùng chấp thuận, cùng các tiêu chí bổ sung về mapping từng mục, note identity, vai trò các bản Markdown và version. Không chuyển đổi nguồn đang xuất bản hoặc chạy benchmark bước 3.

## Kết quả trước/sau

| Hạng mục | Trước | Sau, đã kiểm chứng |
| --- | --- | --- |
| A. PDF cùng cỡ chữ | Mẫu native 42 khối, 0 section; mục đánh số bị nhận là list | Giữ 42 khối, có 5 section, parent/section_path và căn cứ suy luận. Raw glyph stream, vị trí và bytes nguồn giữ nguyên. |
| B. DOCX nhiều cấp | `a)` bị Markdown nhập vào đoạn của cha; glyph bullet nguồn bị làm phẳng | Parser thực tế nhận đủ 53 list items, ba cấp; marker và locator nguồn theo từng item. Test đánh số tự động giữ `7.`, `a)`, `•`, `b)`, `8.`, bắt đầu lại `3.` qua bảng và page break. |
| C. Note | Ba raw footnote bắt đầu bằng tab, bị hiểu là code khi render thẳng | Bản đọc có ba footnote definition, link đi–về và raw body không đổi; page unknown vẫn unknown. Note trùng chữ không gộp, nhiều tham chiếu giữ ID riêng. |
| D. Bảng | Gói chuẩn tốt cho máy nhưng khó đối chiếu trực quan | Cả 10 bảng của DOCX dựng được layout từ ô nguồn. UI giữ header nhiều tầng, rowspan/colspan; `.md` độc lập dùng header path đầy đủ và chú dẫn tọa độ ô gộp. |
| E. Bản đọc | Người dùng nhìn bản chuẩn nhiều metadata | Ba chế độ Bản dễ đọc / Gói chuẩn / Bản phục vụ RAG. Bản đọc mới 61.760 bytes; gói chuẩn 276.238 bytes do thêm mapping item. Không đưa metadata này vào RAG. |

Ví dụ định dạng với fixture độc lập:

```markdown
7. Mục cha
   - **a)** Điểm con
     - Điều kiện
8. Mục tiếp theo

<!-- source-list-restart -->

3. Danh sách bắt đầu lại
```

Nhãn `a)` và glyph nguồn nằm trong dữ liệu cấu trúc. Biểu diễn dẫn xuất dùng cú pháp CommonMark mà parser hiện tại hiểu được. Với note, `	Nội dung` ở raw vẫn giữ; bản đọc dùng định nghĩa `[^id]: Nội dung` và link tham chiếu. Không sửa code block thật chỉ vì có thụt đầu dòng.

## Phương pháp và phạm vi mã

- [pdf_headings.py](../../../backend/app/modules/knowledge/parsers/pdf_headings.py), [pdf_structure.py](../../../backend/app/modules/knowledge/parsers/pdf_structure.py): dùng glyph đậm, khoảng cách, đánh số và body cùng cột/trang kế tiếp. Phân biệt số riêng, đoạn liệt kê thường, vùng lặp đầu/cuối trang; tín hiệu chưa đủ giữ unresolved. OCR không có căn cứ cấp mục tiếp tục giữ cảnh báo; không gọi OCR mới.
- [docx_numbering.py](../../../backend/app/modules/knowledge/parsers/docx_numbering.py), [docling_structure.py](../../../backend/app/modules/knowledge/parsers/docling_structure.py), [docx_evidence.py](../../../backend/app/modules/knowledge/parsers/docx_evidence.py): đọc numPr/style/abstractNum/level/startOverride; lưu item ID, level, marker, parent, numbering recipe, source locator và locations. Match cùng nội dung theo thứ tự chỉ khi inventory nguồn và engine có cùng số lần xuất hiện. Không gán nguồn từ một occurrence tùy ý.
- [qnu_reader.py](../../../backend/app/modules/knowledge/normalization/qnu_reader.py): dẫn xuất xác định cho đọc/xuất; không mutate model. Chỉ dùng source layout nếu grid/raw fields khớp toàn bộ; layout lệch dùng grid canonical. Note thiếu đích hoặc cấu trúc phức tạp còn giới hạn, không bịa phần thiếu. Bản `.md` là bản đọc, không sao chép bố cục trang.
- [source_reader.py](../../../backend/app/modules/knowledge/services/source_reader.py), [router.py](../../../backend/app/modules/knowledge/router.py): mở rộng endpoint tải hiện tại bằng `reader/reader-json`, kiểm quyền xem và collection/binding/revision hiện có trước khi đọc cặp chuẩn; giữ hash/parity. Read only, không inference, lưu artifact hay ghi DB.
- [qnu-document-reader.tsx](../../../frontend/src/features/knowledge/components/qnu-document-reader.tsx), [qnu-standard-editor.tsx](../../../frontend/src/features/knowledge/components/qnu-standard-editor.tsx): tái dùng Table/Tabs/Button, trạng thái tải/lỗi/trống, nhãn rõ chức năng. Source HTML không thực thi và ảnh ngoài không tự tải. Hiệu đính vẫn ở tab Gói chuẩn và kiểm quyền hiện có.
- API client, menu tải và [ocr-inspector.tsx](../../../frontend/src/components/knowledge/ocr/ocr-inspector.tsx): chọn bản tải, bảo toàn `ol.start`. Không thay primitives hoặc route/deep link.

Schema chuẩn vẫn v1.0 và bảng vẫn `gfm/records`. Extraction mới là `layout-v22-document-structure`, PDF builder `pdf-evidence-structure/v2`, list structure `docx-lists/v1`, reader `qnu-reader/v1`. Không viết lại revision cũ. Xem [quy trình 11.12](../../quy_trinh/13_chuan_markdown_rag_v1.md#1112-cấu-trúc-nguồn-và-bản-dành-cho-người-đọc--phiên571).

## Giới hạn và việc áp dụng

Không nhận diện được mọi heading thiếu tín hiệu chỉ bằng các heuristic này. Typography suy luận không phải xác nhận ngữ nghĩa. OOXML có thể có numbering format không hỗ trợ; metadata giữ trạng thái unresolved thay vì chứng nhận marker đã đúng. Nội dung nhiều đoạn trong item đã kiểm qua line break, bảng xen và chuyển trang; tài liệu có các continuation paragraph không được engine nhận là item vẫn giữ nguyên paragraph, không tự gán scope từ khoảng cách.

Note phức tạp có bảng/hình chưa được tái dựng hết bố cục; giữ raw source/locator/cảnh báo. Bản đọc không là một kho kiến thức độc lập. Gói chuẩn và canonical projection giữ hợp đồng hiện tại; các artifact có hash vẫn bất biến. Việc chỉ render bản đọc từ revision cũ không sửa danh sách/heading đã trích sai trong revision đó.

Để nguồn thật nhận cải thiện A/B, cần tạo revision mới rồi kiểm MD/JSON, projection, Quality Gate và citation trước nạp vector/xuất bản theo phạm vi được phép. Phiên này không làm các thao tác đó. Benchmark 64 câu bước 3 phải giữ nguồn đã xuất bản nếu muốn đo riêng RAG bước 2; phép thử dùng revision parser mới cần báo riêng.

[Kiểm chứng và lỗi nền](VALIDATION_REPORT.md). Không commit/push, restart, deploy, đổi provider/model, reindex hoặc publish. Không sửa 68 file RAG hiện có hoặc 14 frozen benchmark input files.
