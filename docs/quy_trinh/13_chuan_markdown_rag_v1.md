# QNU RAG Markdown Standard v1.0

> Chuẩn thống nhất: lõi Universal + quy tắc dữ liệu chọn lọc từ v1 + chỉ mục dẫn xuất.
> Chốt cấu trúc ngày 2026-10-17. Đây là đặc tả và mẫu để chuyển đổi tài liệu,
> **không phải tài liệu kiến thức để nạp nguyên file này vào RAG**.
> Parser của app hiện chưa hỗ trợ đầy đủ chuẩn này; tạo file không đồng nghĩa đã triển khai.
> Cập nhật phiên 522 (2026-10-17): đường nạp DOCX qua Docling đã sinh **artifact chuẩn
> dẫn xuất** (`*.qnu-rag-v1.md` + `*.qnu-doc-v1.json`) gắn source revision và có
> endpoint tải riêng. Phiên 525 (2026-10-18) bổ sung PDF native/scan/mixed thành
> artifact chuẩn song song. Phiên 526 nối chuẩn vào serving cho import/reparse mới
> và revision hiệu đính: cặp MD/JSON được đối soát rồi chiếu thành canonical + units,
> facts và context graph của pipeline hiện có. Không tự chuyển các revision cũ,
> không tự reindex hoặc xuất bản. Xem mục 11.2 về điều kiện áp dụng.

## 1. Phạm vi và cách dùng

Áp dụng cho văn bản hành chính, quy chế, kế hoạch, báo cáo, tài liệu tuyển sinh,
hướng dẫn kỹ thuật và tài liệu có bảng, danh sách, công thức hoặc hình. Các trường
nghiệp vụ chỉ bổ sung khi có trong nguồn; không ép mọi tài liệu theo mẫu tuyển sinh.

1. Giữ file gốc, raw extraction/OCR, bảng/ô, hình và thông tin bố cục hiện có.
2. Chép khung tại mục 3, điền từ nguồn và tạo các khối theo mục 4–6.
3. Ghi dữ liệu chuẩn hóa, vị trí nguồn, điều kiện và cờ chất lượng theo mục 7–8.
4. Chỉ mục tổng hợp tại mục 9 do app/script sinh riêng, không viết tay.
5. Kiểm tra mục 10 trước khi đề nghị duyệt. Duyệt, dựng index và xuất bản là ba bước riêng.

File tài liệu dùng UTF-8 không BOM, LF. Không để placeholder `{{...}}` trong bản
đề nghị xuất bản. Giữ tên, số mục và thứ tự nguồn; không chuyển tất cả tài liệu
thành một bộ chương cố định hoặc tóm tắt thay cho nguyên văn.

## 2. Ba lớp dữ liệu, không trộn vai trò

| Lớp | Nội dung | Vai trò |
| --- | --- | --- |
| Nguồn gốc | PDF/DOCX/XLSX/ảnh/nguồn khác; raw text/OCR, bố cục và hash | Đối chiếu và lưu vết |
| Canonical Markdown | Nội dung giữ cấu trúc; metadata và ánh xạ tới nguồn | Chứng cứ có kiểm soát sau khi được server duyệt |
| Dẫn xuất | Chunks, văn bản hỗ trợ tìm kiếm, giá trị chuẩn hóa, chỉ mục đếm/liệt kê | Hỗ trợ truy hồi/tính toán; không là nguồn độc lập |

Một dữ kiện chỉ có một bản canonical. Các bản trình bày/tóm tắt/rollup phải trỏ về
bản đó, không tạo thêm “nguồn” hoặc làm tăng số ngành, nhiệm vụ hay tài liệu.
Hash chứng minh toàn vẹn bytes, không chứng minh OCR hoặc nội dung đúng.

## 3. Khung tài liệu dùng lại

Chép phần trong code fence dưới đây thành file mới. `revision_id` là nhãn revision
trong gói trao đổi; server đối chiếu và cấp/mapping revision DB, không tin nhãn này
để ghi đè tài liệu đang có. `document_id` không phải quyền truy cập.

````markdown
---
schema_version: "qnu-rag-markdown/1.0"
is_template: true
document_id: "{{document_id}}"
revision_id: "{{revision_id}}"
title: "{{document_title_from_source}}"
language: "vi"
document_type: null
source:
  filename: "{{original_source_filename}}"
  uri: null
  sha256: null
  page_count: null
metadata: {}
review_status: "unreviewed"
---

# {{document_title_from_source}}

<!-- rag:block
id: "s001"
parent_id: null
type: section
source_locations:
  - page: null
    page_label: null
    locator: "{{section_locator}}"
section_path: ["{{section_title_from_source}}"]
context_refs: []
attributes: {}
quality_flags: []
-->
## {{section_title_from_source}}
<!-- /rag:block -->

<!-- rag:block
id: "p001"
parent_id: "s001"
type: text
source_locations:
  - page: null
    page_label: null
    locator: "{{paragraph_locator}}"
section_path: ["{{section_title_from_source}}"]
context_refs: []
attributes: {}
quality_flags: []
-->
{{complete_source_paragraph_with_conditions_and_exceptions}}
<!-- /rag:block -->
````

### Hợp đồng frontmatter

- Bắt buộc: `schema_version`, `is_template`, `document_id`, `revision_id`, `title`,
  `language`, `document_type`, `source`, `metadata`, `review_status`.
- `document_type`: chuỗi loại tài liệu nếu biết, không biết dùng YAML `null`;
  trường mở rộng nằm trong `metadata`, không tạo tùy tiện nhiều tên cho cùng một khóa.
- `source.sha256`: hash 64 ký tự hex của **file gốc được dẫn chiếu**, không phải hash
  của bản Markdown chuyển đổi. Server phải đọc bytes để đối chiếu. Chưa biết để `null`.
- Nếu Markdown chính là nguồn gốc, không nhúng hash tự tham chiếu của nó vào chính
  file: để `source.sha256: null`, server lưu hash bytes ở manifest ngoài file.
- `source.page_count`: số trang vật lý đã xác minh, không phân trang/chưa biết dùng
  `null`; không lấy số bảng, số heading hoặc số chunk làm số trang.
- `source.uri`: chỉ là tham chiếu; không tự tải URL, file path hay ảnh ngoài từ giá trị này.
- `metadata`: thông tin hành chính nếu có, ví dụ số hiệu/ngày ký/người ký; năm dữ liệu
  của từng bảng/ô vẫn ghi ở khối tương ứng, không suy từ frontmatter.
- `review_status`: `unreviewed | reviewed | needs_review`, chỉ là khai báo của gói;
  không đổi quyền hay trạng thái duyệt/xuất bản thực trong app.
- `is_template: true` phải bị chặn ở bước nhập kiến thức thực. Đổi thành `false`
  chỉ sau khi điền dữ liệu; giá trị `false` cũng không chứng minh tài liệu đã đúng.
- Phiên bản không hỗ trợ, sai kiểu, khóa trùng hoặc khóa lõi không biết phải báo rõ;
  không âm thầm bỏ metadata rồi nạp như văn bản thường.

## 4. Hợp đồng khối Universal

Chỉ dùng một cú pháp: comment mở `<!-- rag:block` chứa YAML, kết thúc metadata
bằng `-->`; tiếp theo là Markdown nội dung; đóng bằng `<!-- /rag:block -->`.

- Không lồng cặp mở/đóng, không để khối chưa đóng. Quan hệ lồng dùng `parent_id`.
- Metadata/hướng dẫn không phải nội dung chứng cứ và không embedding như văn bản.
- Khối là đơn vị chứng cứ, **không bắt buộc là một chunk embedding**.

| Trường | Quy tắc |
| --- | --- |
| `id` | Bắt buộc; chuỗi duy nhất trong một revision, không dùng một mã ngành làm ID cho mọi lần xuất hiện |
| `parent_id` | Bắt buộc; ID khối cha cùng revision hoặc `null`; không có chu trình |
| `type` | Bắt buộc; một loại trong bảng dưới |
| `source_locations` | Bắt buộc; danh sách vị trí thật, có thể rỗng khi chưa xác minh và phải có cờ |
| `source_label` | Tùy chọn; số Điều/Khoản/STT nguyên gốc, không phải ID kỹ thuật |
| `section_path` | Tùy chọn; tên/số các cấp nguồn, không ép độ sâu heading |
| `context_refs` | Tùy chọn; ID điều kiện/chú thích cùng revision cần đọc cùng, mặc định `[]` |
| `attributes` | Tùy chọn; trường có kiểu cho bảng, thời gian, nghiệp vụ; mặc định `{}` |
| `quality_flags` | Tùy chọn; cảnh báo có vị trí/phạm vi, mặc định `[]` |

| `type` | Dùng cho |
| --- | --- |
| `section` | Tiêu đề/phần dẫn của chương, điều, mục, phụ lục |
| `text` | Đoạn nguyên văn đầy đủ |
| `list` | Danh sách có thứ tự hoặc lồng nhau, giữ câu dẫn và ngoại lệ |
| `table` | Header, định nghĩa cột và bảng GFM nhỏ hoặc container của các record |
| `table_row` | Một dòng logic của bảng, liên kết với container và header |
| `note` | Chú thích/điều kiện thực sự có trong nguồn |
| `code` | Mã nguồn nguyên văn trong code fence |
| `formula` | Công thức kèm định nghĩa ký hiệu, đơn vị, điều kiện nguồn |
| `figure` | Hình/sơ đồ kèm tham chiếu tài nguyên và chú thích nguồn |
| `derived_index` | Chỉ mục do máy sinh theo mục 9; không phải trích nguyên văn |

Định danh nội bộ phải được ghim theo bộ `(document_id, revision_id, id)` và mapping
với binding/source revision của server. Bản sửa có thể giữ ID logic nhưng không
được dùng tham chiếu thiếu revision để trích lại bản cũ. ID trong file không tự trở
thành citation ID công khai của app.

### Vị trí nguồn

Mỗi location có `page`, `page_label`, `locator`; có thể thêm `bbox` và `bbox_space`
khi thực sự có tọa độ và hệ tọa độ xác định. `page` là trang vật lý 1-based;
`page_label` là nhãn in trên trang, có thể khác. Nguồn không phân trang dùng
`page: null`, `page_label: null` và locator mục/đoạn/ô/anchor.

Khối nối trang giữ một location cho mỗi vị trí, không gán cả khối vào trang đầu.
Sidecar/manifest giữ ánh xạ tới raw block/ô/span nếu có. Không bịa bbox, số trang
hoặc quote gốc khi chỉ có văn bản đã viết lại. Thiếu ánh xạ phải báo giới hạn;
metadata upload không tự xác nhận được tham chiếu nguồn.

### Điều kiện và liên kết

`context_refs` biểu diễn phụ thuộc chứng cứ, không phải chỉ dẫn cho model. Khi nạp
và đóng gói, phải lấy đủ điều kiện liên quan; vượt ngân sách thì chia ở ranh giới
hợp lệ hoặc báo chưa đủ context, không bỏ điều kiện. Quan hệ cha–con không mặc
định chứng minh mọi điều kiện cha áp dụng cho mọi con.

Liên kết sang tài liệu khác đặt trong `attributes.links`, mỗi mục gồm
`target: {document_id, revision_id, block_id}`, `relation` và
`basis: explicit | inferred`. Đích phải tồn tại, đúng collection/publication của
request. Liên kết inferred không là căn cứ gộp mã, mở scope hay xác nhận dữ kiện.

## 5. Bảng và bản ghi

Hai cách biểu diễn được phép cho **mỗi bảng**:

1. `attributes.representation: gfm`: giữ bảng Markdown, một dòng dữ liệu trên một
   dòng vật lý. Parser sinh record/ô nội bộ; không nhập thêm bản ghi lặp độc lập.
2. `attributes.representation: records`: container `table` định nghĩa các cột;
   từng `table_row` giữ đủ giá trị, không cần lặp cả bảng GFM.

Chọn theo độ dài ô, cấu trúc header và ngân sách, không cố định quy tắc 10 dòng/6 cột.
Không dùng cột kỹ thuật `Row ID` hay `PDF page` như một chỉ tiêu nghiệp vụ; đặt chúng
trong metadata. Khi xuất ra bảng cho người đọc có thể hiển thị, nhưng không tạo facts giả.

### Mẫu container và một dòng bảng

````markdown
<!-- rag:block
id: "t001"
parent_id: "s001"
type: table
source_locations: []
context_refs: []
attributes:
  representation: records
  columns:
    - id: "c01"
      header_path: ["{{entity_code_header}}"]
    - id: "c02"
      header_path: ["{{parent_header}}", "{{leaf_header}}"]
quality_flags:
  - code: "source_location_unverified"
    status: "unresolved"
    detail: "{{reason_the_table_location_is_not_verified}}"
-->
### {{original_table_title}}
<!-- /rag:block -->

<!-- rag:block
id: "r001"
parent_id: "t001"
type: table_row
source_label: "{{original_row_number}}"
source_locations: []
context_refs: ["n001"]
attributes:
  fields:
    c01:
      raw: "{{original_cell_value}}"
      state: present
      normalized: null
    c02:
      raw: ""
      state: blank
      normalized: null
  field_origins: {}
quality_flags:
  - code: "source_location_unverified"
    status: "unresolved"
    detail: "{{reason_the_row_location_is_not_verified}}"
-->
**{{entity_code_header}}:** {{original_cell_value}}

**{{parent_header}} / {{leaf_header}}:** [Ô trống trong nguồn]
<!-- /rag:block -->

<!-- rag:block
id: "n001"
parent_id: "t001"
type: note
source_locations: []
context_refs: []
quality_flags:
  - code: "source_location_unverified"
    status: "unresolved"
    detail: "{{reason_the_note_location_is_not_verified}}"
-->
{{original_condition_or_footnote_applicable_to_the_row}}
<!-- /rag:block -->
````

`attributes.fields` là ánh xạ `column_id -> {raw, state, normalized}`. Cột phải
tồn tại trong container; nội dung hiển thị và `raw` phải khớp, không là hai bản
viết tay khác nghĩa. Header nhiều tầng giữ đủ thứ tự cha/con, năm, đơn vị và vai trò.
Giá trị chuẩn hóa có thể là `{value, unit, operator, basis_quote}` khi cần; quote
phải truy về đúng ô/khối, không lấy từ tóm tắt.

`field_origins` dùng khóa column ID, giá trị có `block_id`, `column_id` và `basis`
(`merged_cell | explicit_reference`) để chỉ nguồn kế thừa đã xác minh. Mọi ô/khối
nguồn phải có thật; chưa xác định phạm vi ô gộp thì đặt cờ, không điền đoán.

Bảng nhiều năm: năm và loại đại lượng thuộc cột/ô, không áp năm của tiêu đề tài
liệu cho toàn bảng. Hai hệ quy đổi khác nhau phải có trường phân loại rõ hoặc
tách bảng; đặt IELTS và VSTEP cùng hàng không được biến thành điều kiện cần cả hai.

## 6. Nội dung không phải bảng

- Văn xuôi giữ nguyên Điều/Khoản/Điểm, phủ định, ngoại lệ và mốc thời gian.
  Danh sách đầy đủ không thay bằng dấu ba chấm. Header/footer không tự xóa nếu
  chưa xác minh là phần lặp không mang nội dung.
- `code` giữ ngôn ngữ và code fence; không đọc heading/comment bên trong thành
  cấu trúc của tài liệu. Marker `rag:block` literal trong code cũng không mở khối.
- `formula` giữ công thức, ký hiệu, miền áp dụng, đơn vị và ghi chú. Chép công thức
  không kích hoạt score rule hay cho LLM tự tính thay công cụ kiểm chứng.
- `figure` giữ ảnh/chú thích và nguồn tài nguyên. Diễn giải do AI sinh là dẫn xuất
  riêng, không phải lời nguyên bản của hình. Hình chưa đọc được phải có cờ thiếu.
- Khối dài có thể chia thành các khối con có nguồn riêng; không bỏ header, ngoại lệ
  hoặc phá công thức để đạt kích thước cố định. Không áp giới hạn 500 từ cho mọi nguồn.

## 7. Quy tắc dữ liệu chọn lọc từ v1

### Giá trị thiếu và chuẩn hóa

| Trạng thái `state` | Ý nghĩa |
| --- | --- |
| `present` | Có giá trị đọc được, kể cả số 0 |
| `blank` | Ô nguồn thực sự trống; `raw: ""`, không đổi thành 0 |
| `not_stated` | Nguồn nói rõ không nêu/chưa công bố, có quote hỗ trợ |
| `not_applicable` | Không áp dụng theo nội dung/chú giải nguồn |
| `unreadable` | Có nội dung nhưng chưa đọc được |
| `ambiguous` | Giá trị/ký hiệu/phạm vi chưa rõ nghĩa |

Dấu `-`, `/`, ký hiệu khác giữ trong `raw`; chỉ phân loại sau khi đọc chú giải.
“Không nêu ở ô này” không chứng minh toàn bộ văn bản/kho không có thông tin.
Trường không tồn tại khác với trường có ô trống: không tạo cột không có trong nguồn.

Nguyên văn giữ dấu số gốc; giá trị chuẩn hóa dùng số thập phân chính xác (không
floating-point để quyết định làm tròn tiền/điểm). Mã ngành, số hiệu, mã có số 0 đầu
là chuỗi. Phép `>`, `>=`, `<`, `<=`, `=`, `approx`, `range` phải giữ đúng chủ thể,
đơn vị, điều kiện và quote; không đổi “trên” thành “từ … trở lên”.

NFC và nối soft-wrap chỉ sửa biểu diễn. Hiệu đính chữ/số phải có lý do, vị trí,
giá trị trước–sau và revision mới; không âm thầm sửa lỗi có ngay trong nguồn.

### Thời gian

Trường mở rộng `attributes.temporal` có thể chứa `data_years`, `academic_year`,
`effective_from`, `effective_to`, `event_from`, `event_to`, `recurrence`, `basis_quote`.
Ngày ban hành lưu trong metadata hành chính. Mỗi mốc chuẩn hóa có
`{raw, value, precision}` với precision `day | month | year`; không đủ căn cứ thì
`value: null`. Năm học `2025-2026` không tự thành khoảng hiệu lực pháp lý.

`data_years` chỉ ghi khi có căn cứ của chính dữ kiện/header/điều kiện liên quan.
Không biết dùng `[]`; năm chỉ được nhắc tới không tự thành năm dữ liệu. Bảng nhiều
năm ghi temporal ở từng column/field khi khác nhau, không dùng một nhãn năm chung
để lọc tất cả ô. Hạn chót chưa biết hoặc sự kiện định kỳ không bị ép thành ngày cụ thể.

### Hồ sơ nghiệp vụ tùy chọn

Trường nghiệp vụ nằm trong `attributes.domain`, không thay lõi Universal:

- Tuyển sinh: mã/ngành/chương trình, phương thức, tổ hợp, loại điểm, năm dữ liệu.
- Kế hoạch: chủ thể, chủ trì/phối hợp/thực hiện, sản phẩm, thời hạn, chỉ tiêu.
- Quy chế: số Điều/Khoản/Điểm, đối tượng, điều kiện, ngoại lệ, hiệu lực có căn cứ.
- Kỹ thuật: ngôn ngữ, phiên bản sản phẩm, môi trường, tham số và điều kiện áp dụng.

Nhãn hiển thị ưu tiên header/nguyên văn; tên chuẩn hóa ghi riêng. Không tự đồng nhất
hai tên/mã khác nhau. Thuật ngữ/bí danh chỉ gợi ý vào glossary hiện có, không tự duyệt
hoặc ghi đè thuật ngữ trong app; truy hồi chỉ dùng mục được phép theo collection.

## 8. Cờ chất lượng, tóm tắt và quyền hạn

Cờ có tối thiểu `{code, status, detail}`, có thể thêm `field_id` và
`related_block_ids`. `status`: `unresolved | confirmed | resolved | rejected`;
đó là mô tả cảnh báo, không phải trạng thái xuất bản.

Nhóm cờ dùng chung: `source_location_unverified`, `source_hash_unverified`,
`ocr_uncertain`, `merged_cell_uncertain`, `page_break_row`, `code_mismatch`,
`name_variant`, `date_ambiguous`, `quantity_ambiguous`, `template_placeholder`,
`citation_irregular`, `missing_content`, `other`. `other` phải mô tả cụ thể.
Ô trống hợp lệ không tự là lỗi chặn xuất bản; mức ảnh hưởng phụ thuộc trường hợp.

Cờ gắn ngay khối/ô bị ảnh hưởng và phải đến bước kiểm chứng câu trả lời. Danh sách
QA tổng hợp nằm ngoài chứng cứ/vector chính, có thể do app hiển thị riêng. Không
nhúng câu lệnh “hãy bỏ qua/không index” rồi kỳ vọng LLM tự thực thi.

Tóm tắt không bắt buộc. Nếu có, giữ riêng ở dẫn xuất hỗ trợ tìm kiếm với liên kết
nguồn; không ghi đè nguyên văn và không tạo citation như trích nguồn. Số liệu xuất
hiện đủ trong tóm tắt chưa chứng minh đúng ngữ nghĩa hoặc quan hệ điều kiện.

Server tính/kiểm hash, xác minh actor/quyền và ghi audit duyệt. File không được tự
cấp quyền, chuyển `active`, publish, kích hoạt công cụ, chọn provider hay tạo tenant/
workspace. Metadata/tài liệu/OCR là dữ liệu không tin cậy; không thi hành instruction
hoặc tải tài nguyên ngoài chỉ vì tài liệu yêu cầu.

## 9. Chỉ mục dẫn xuất: liệt kê, đếm và tra cứu ngược

### Quy tắc bắt buộc

- App/script sinh từ một manifest đầu vào bất biến, đúng collection và tập revision
  được phép phục vụ. Đổi nguồn, trạng thái xuất bản hoặc quy tắc nhóm thì vô hiệu hóa
  và sinh lại; không dùng rollup cũ với nguồn mới.
- Tách artifact/file khỏi canonical nguồn. Nếu xuất MD, dùng `document_type:
  derived_index`, cùng schema và `type: derived_index`; không viết tay số tổng.
- Frontmatter file chỉ mục dùng `source.filename`, `source.uri`, `source.sha256`,
  `source.page_count` là `null`; các nguồn thật nằm trong `derivation.inputs`.
  Hash của artifact chỉ mục được server lưu ngoài file, không tự tham chiếu.
- Mỗi thành viên trỏ rõ `document_id`, `revision_id`, `block_id`; không chỉ ghi tên.
- Manifest có hash và revision của từng nguồn, phiên bản builder, quy tắc nhóm,
  thời điểm sinh, bộ lọc, đơn vị đếm, quy tắc trùng và độ đầy đủ.
- Chỉ ghim chỉ mục khi phù hợp ý định/phạm vi thực, không route chỉ bằng từ khóa.
  Không đặt ngưỡng “hơn 5 chỗ” hay phụ thuộc một giá trị Top K cố định.

### Các loại chỉ mục

| `index_kind` | Nội dung |
| --- | --- |
| `entity` | Các bản ghi liên quan thực thể; tách từng vai trò |
| `topic` | Các bản ghi theo chủ đề có căn cứ |
| `code` | Các lần xuất hiện của mã; không gộp hai mã chỉ vì gần giống |
| `timeline` | Mốc thời gian, giữ độ chính xác và mốc chưa rõ |
| `metrics` | Chỉ tiêu/đại lượng với chủ thể, phép so sánh, đơn vị và điều kiện |
| `inventory` | Thống kê số tài liệu/bảng/record trong phạm vi xác định |

### Mẫu manifest/khối chỉ mục do máy sinh

```yaml
id: "idx-entity-001"
parent_id: null
type: derived_index
source_locations: []
context_refs: []
attributes:
  derivation:
    builder_version: "{{builder_version}}"
    built_at: "{{ISO_8601_timestamp}}"
    input_manifest_hash: "{{hash_of_exact_input_manifest}}"
    inputs:
      - document_id: "{{source_document_id}}"
        revision_id: "{{source_revision_id}}"
        canonical_sha256: "{{verified_canonical_hash}}"
    index_kind: "entity"
    scope: {}
    count_unit: "source_record"
    deduplication: "exact_revision_block_ref"
    coverage: "partial"
    total: null
    returned_count: 0
    members: []
quality_flags: []
```

Đây là metadata trong `rag:block`; phần thân MD do renderer sinh từ `members`,
không phải lời nguồn. `scope` phải chứa bộ lọc thực và snapshot/collection phía
server; không lấy collection do model/file khai báo làm chứng minh quyền.

`members` là danh sách `{document_id, revision_id, block_id}`. Mỗi giá trị phụ thêm
trong rollup phải có tham chiếu ô/field nguồn. `returned_count` bằng số members
được xuất. Chỉ khi đã duyệt hết tập phù hợp mới ghi `coverage: complete` và
`total` chính xác; partial giữ `total: null`, nêu rõ chưa có tổng đầy đủ.
Khi phân trang/tách file phải có manifest tập đầy đủ, số phần và cursor/phạm vi;
không gọi số dòng của một trang là tổng toàn bộ.

Số bản ghi, số mã duy nhất, số ngành/chương trình, số tài liệu, số đoạn trích là
những đơn vị đếm khác nhau. Một ngành xuất hiện ở hai năm/hai tài liệu không tự
thành hai ngành, cũng không được gộp nếu khác chương trình/điều kiện. Đếm duy nhất
cần quy tắc nhận dạng đã kiểm chứng và ghi rõ trong manifest.

Chỉ mục là điểm vào để lấy đủ bản ghi và điều kiện ngoài giới hạn top-k. Nó không
thay cơ chế lấy tập đầy đủ có giới hạn/phân trang, không bỏ kiểm chứng vì đã có số
tổng. Citation câu trả lời trỏ về nguồn thành viên; phép tính hiển thị là dẫn xuất
kèm công thức/quy tắc đếm, không giả làm số in trong văn bản.

## 10. Bảng kiểm trước khi duyệt và xuất bản

- [ ] Schema/version/kiểu dữ liệu/YAML an toàn; không khóa trùng, template hay placeholder sót.
- [ ] Hash/trang/tài nguyên đối chiếu được với bytes nguồn thật; nguồn chưa xác minh có cờ.
- [ ] ID duy nhất theo revision, parent/context refs có thật; quan hệ cha–con không chu trình.
- [ ] Số mục, record, phần tử danh sách và các ô được kiểm tra độc lập so với nguồn.
- [ ] Header, năm, vai trò, đơn vị, phủ định, ngoại lệ, ô trống/0 và mã được giữ đúng.
- [ ] Mọi giá trị chuẩn hóa có nguyên văn và mapping; mọi mâu thuẫn còn mở được truyền tới verifier.
- [ ] Kiểm các ô gộp/nối trang/OCR nghi vấn bằng nguồn trực quan; không chỉ nhìn MD đẹp.
- [ ] Không tạo nguồn lặp từ summary, QA, glossary hoặc rollup; không trích summary như nguyên văn.
- [ ] Chunk/context đủ điều kiện trong ngân sách; vượt giới hạn không được cắt âm thầm.
- [ ] Chỉ mục dẫn xuất khớp input manifest, bộ lọc, đơn vị đếm, members và coverage.
- [ ] Actor/quyền/audit/approval do server xác minh; dựng staging không tự chuyển serving.
- [ ] So sánh hành vi bằng câu hỏi đại diện trên cùng snapshot; cấu trúc đạt không đồng nghĩa RAG đạt 90%.

## 11. Áp dụng cho app hiện tại

Đây là **chuẩn đã chốt về thiết kế**; phiên 522 đã triển khai đường sinh cho DOCX
thành artifact dẫn xuất, chưa là tuyên bố toàn bộ parser đang hỗ trợ chuẩn này.
Tái dùng source revision, raw artifact, unit/context graph, chunk cấu trúc,
derived bundle và lifecycle tại [quy trình bản sạch](./11_ban_sach_va_duyet_noi_dung.md).

Đã có từ phiên 522 (DOCX): parser/builder đọc DoclingDocument, validator frontmatter
và `rag:block`, mapping giữ nguồn/header/field/condition, artifact MD/JSON có hash
lưu content-addressed, endpoint tải có quyền. Còn lại khi mở rộng: dùng MD chuẩn
làm chứng cứ canonical/chunk/RAG và builder chỉ mục theo snapshot.
Giữ đường MD cũ, không tự nâng schema/backfill index đang phục vụ.
Không cần reset DB chỉ để chốt hay thử chuẩn. Migration nếu có phải được xác định
khi triển khai thực, không kết luận trước từ tài liệu thiết kế.

**Hợp đồng danh tính artifact** (phiên 523): một tệp `.qnu-rag-v1.md` chỉ là bản
chuẩn của đúng một revision, vì frontmatter của nó chứa `revision_id`. Khi revision
mới sinh ra do **hiệu đính nội dung** (sửa markdown, sửa ô bảng), tệp của bản cũ
không còn là bằng chứng: metadata phải mang
`status=unavailable` + `reason=superseded_revision_content`, giữ
`superseded_revision_id`/`superseded_sha256` để tham chiếu nhưng không còn `path`,
và không được dựng lại từ DOCX gốc rồi tuyên bố là nội dung đã hiệu đính. Khi
revision mới sinh ra do **dùng lại kết quả bóc tách bất biến** cùng nguồn (artifact
key ghim hash nguồn + parser profile + OCR config + version) thì được phép tái sử
dụng dữ liệu dẫn xuất, nhưng phải render lại dưới `revision_id` của chính revision
mới, không dán nhãn tệp cũ. Bộ phân giải và endpoint kiểm `revision_id` và
`document_id` khớp trước khi phục vụ (`QNU_MARKDOWN_REVISION_MISMATCH`), không chỉ
nhìn `status=ready`. Artifact lịch sử không ghi đè và không xóa.

Mapping trang của DOCX là trang của **bản PDF render xem trước**, được ánh xạ theo
từng đơn vị (dòng bảng, ghi chú, item danh sách). Trang do **toàn bộ khoảng khớp**
quyết định, không chỉ điểm bắt đầu: đơn vị nằm trọn trong một trang nhận một
`source_location`; đơn vị trải qua ranh giới trang nhận một `source_location` cho mỗi
trang render, vẫn giữ nguyên locator của nó; khoảng khớp có gap, chưa ghim hoặc vượt
ra ngoài vùng đã ghim thì giữ `page: null` kèm locator và cờ `page_unresolved`. Nội
dung lặp xuất hiện ở nhiều trang khác nhau vẫn là mơ hồ, và việc đọc tiến
(forward-only) không được hồi tố khớp cũ thành trang. `page_mapping.status` chỉ
`aligned` khi mọi đơn vị đã định vị chắc chắn; số đơn vị đa trang nhìn thấy qua
`stats.unit_states` (`matched`/`spanning`/`ambiguous`/`absent`/`out_of_order`).

**Bằng chứng header DOCX** (phiên 535): backend đọc `w:tblHeader` trong DOCX gốc
và chỉ gắn vai trò cho bảng Docling khi toàn bộ lưới nội dung khớp duy nhất.
Các hàng header liên tiếp từ đầu bảng giữ đầy đủ đường dẫn cột, kể cả nhãn số/năm.
Nhãn `column_header` do engine mặc định cho hàng đầu chỉ là đề xuất. Thiếu bằng
chứng hoặc bảng trùng nội dung không gắn nguồn duy nhất thì giữ mọi hàng trong
records, header chưa rõ và cờ đối soát. JSON giữ cả bằng chứng Word và cờ engine
gốc; không sửa chúng để làm đúng vai trò suy đoán. Bảng chỉ có header vẫn giữ
header paths và không tạo dòng dữ liệu giả.

**Hợp đồng xác minh dẫn xuất khi reuse** (phiên 524): `.qnu-doc-v1.json` của bản dùng
chung chỉ được dựng lại dưới danh tính revision mới sau khi checksum đã lưu đạt.
`structured_sha256` thiếu hoặc không đúng dạng hex 64 ký tự thì dừng ở
`status=unavailable` (`structured_checksum_missing`/`structured_checksum_invalid`)
**trước** khi đọc storage; SHA-256 tính trên đúng bytes trả về từ StorageDriver, lệch
thì `status=failed` + `reason=structured_checksum_mismatch` kèm `expected_sha256` và
`actual_sha256`, không parse, không render, không ghi tệp mới, không lấy hash vừa tính
thay cho checksum kỳ vọng, không sửa hoặc xóa artifact lịch sử.

Thử trước trên tài liệu tuyển sinh, quy chế và kế hoạch, gồm dữ liệu thiếu/mâu thuẫn,
bảng nhiều năm, liệt kê/đếm, nguồn không phân trang. Chỉ reindex/publish tài liệu
được chọn khi có yêu cầu; không tự nạp lại cả kho hoặc chạy benchmark 82 câu.

### 11.1. PDF native, scan và mixed — phiên 525

Đường snapshot `extract_source` sinh thêm `QnuStructuredDocument` từ cấu trúc PDF,
không bọc lại Markdown cũ. Tái dùng renderer/validator và endpoint tải MD/JSON của
DOCX. `source.page_count` và `source_locations.page` là trang vật lý PDF 1-based;
nhãn trang in giữ riêng. Bbox native là PyMuPDF unrotated points, bbox OCR là phần
trăm theo trang OCR; tọa độ ô không biết để null, không lấy bbox bảng giả làm bbox ô.

- `pdf_evidence.py`: lưu layout không giới hạn 60 block của UI, matrix/cell boxes
  trước ghép/làm sạch, header gốc, hình và vector geometry. Nguồn PDF gốc vẫn là
  snapshot bất biến. Không loại dòng/header khỏi bằng chứng gốc.
- `pdf_structure.py`: chọn theo vùng native/OCR; bản trùng khớp không thành nguồn
  thứ hai, bất đồng giữ alternative trong JSON và cờ `native_ocr_conflict`.
  Thứ tự đọc dùng XY-cut hình học; cấp heading/chú thích suy từ kiểu chữ có cờ duyệt.
- `pdf_tables.py`: đọc matrix native, raw HTML/GFM của **block bảng** OCR; giữ
  header nhiều tầng, merged-cell origins, raw/state/field_sources. Header thiếu
  giữ toàn bộ dòng thay vì ép dòng đầu làm header. Ký hiệu chưa rõ không thành 0.
  Khối chứa nhiều bảng HTML/nested HTML chưa hỗ trợ được giữ nguyên trong code fence
  với cờ cần kiểm tra, không âm thầm gộp các bảng.
- Bảng ở biên trang tương thích chỉ sinh `continuation_candidate` + cờ cần duyệt,
  chưa tự ghép, chưa kế thừa header khi chỉ có suy luận hình học. Chú thích chỉ có
  `context_refs` tự động khi ký hiệu tham chiếu rõ, duy nhất, cùng trang.
- `OCRExtractResponse.raw_evidence` là trường nội bộ (exclude + repr=False), giữ
  payload provider/pre-clean pages trước cleaner; API công khai không nhúng payload.
  OCR chọn lọc giữ bảng ánh xạ local → physical; OCR vùng đầu giữ crop và raw riêng.
- Lưu `.pdf-evidence-v1.json` content-addressed qua StorageDriver cùng MD và
  `.qnu-doc-v1.json`. Metadata artifact trỏ raw evidence bằng path/hash; dùng lại
  phải kiểm cả checksum JSON cấu trúc và raw sidecar trước khi render revision mới.
  Hiệu đính vẫn vô hiệu artifact cũ theo hợp đồng 523. Không cần migration.

`status=ready` chỉ nghĩa tệp đạt gate cấu trúc; không đồng nghĩa đã duyệt OCR.
`content_status=needs_review`/`unreviewed`, quality flags và raw alternatives được
giữ riêng. Builder/capture lỗi phải báo artifact failed và không xuất MD giả;
không phá Markdown cũ đang phục vụ. Pipeline RAG/chunk/index và provider policy
không thay đổi trong batch này. Kiểm chứng fixture không thay thế đối chiếu PDF
thật hoặc nghiệm thu OCR server. Các trường hợp layout khó có thể cần hiệu đính.

### 11.2. Bản chuẩn làm đầu vào RAG — phiên 526

- Import/reparse DOCX/PDF mới dùng `layout-v16-qnu-evidence` từ phiên535
  (thay fingerprint v15 cho lần bóc tách mới, không sửa revision cũ). Kiểm hai checksum,
  schema, binding/revision, hash nguồn và parity ngữ nghĩa MD↔JSON trước khi tạo
  serving projection `qnu-rag-projection/v1`. Thứ tự key JSON không ảnh hưởng parity;
  thứ tự khối, nội dung và metadata phải tương ứng. PDF raw sidecar được kiểm riêng.
- Canonical phục vụ là projection nội dung, **không** phải nguyên file có YAML/comment.
  Bảng records chuyển thành bảng có header đầy đủ và các row units chính xác;
  source locations, field state/origin/source giữ trong metadata, không đưa raw JSON
  vào embedding. Ô trống/ambiguous không thành số 0 hoặc fact số chắc chắn.
  GFM cũng sinh trạng thái ô nội bộ trong `tables.row_fields`; unresolved count
  và chặn duyệt dùng cùng quy tắc với records. Fact giữ `field_state`, vị trí và
  source row-unit ID; chỉ state `present` mới được giữ, không mặc định thiếu state
  thành present. Trạng thái đã có căn cứ của records vẫn được bảo toàn.
- `context_refs` và quan hệ cấu trúc giữ header/chú thích/cha danh sách; closure cùng
  revision được kiểm. Liên kết có hướng: chọn một ghi chú dùng chung không mở rộng
  ngược thành toàn bộ bảng. Context quá ngân sách phải báo thiếu/loại có lý do,
  không cắt mất điều kiện. Chỉ mục `table_rows` đếm thành viên theo bảng/input hash,
  không chứng minh số ngành duy nhất hoặc độ phủ toàn collection, không được embed.
- Artifact ready không cấp quyền duyệt. Nguồn chuẩn mới chờ duyệt; approve cần actor
  từ server và ghi chú đối chiếu. Tệp lỗi/missing không được duyệt để vượt về legacy.
  Ô còn `ambiguous`/`unreadable` phải được hiệu đính rõ trước: không cho phê duyệt
  toàn tài liệu để biến số OCR chưa chắc thành dữ kiện chính thức. Chưa hỗ trợ
  xuất bản riêng một phần bảng còn ô chưa xác minh trong batch này.
  Tạo chunk và publication kiểm lại cặp tệp. Standard projection hỏng phải báo
  `QNU_STANDARD_INVALID`, không dựng legacy preview rồi tiếp tục trả lời.
- Trang chi tiết nguồn hiển thị/hiệu đính QNU MD khi artifact ready. Gửi
  `content_format=qnu-rag-markdown/1.0`, base canonical hash và lý do. Server tạo revision
  mới, giữ source identity/locations/raw machine data; không cho sửa locator/field source
  để giả trích dẫn. Với records sửa `attributes.fields`; server dựng lại display body.
  Metadata review trong file không phải phê duyệt. Chỉnh ngữ cảnh giữ luồng review hiện có.
- Studio dùng trang unit đã có căn cứ, không gán mọi nội dung unpaged vào trang đầu.
  Khối chưa có trang duy nhất giữ `unmapped_markdown`, báo cho người duyệt xem toàn
  bản chuẩn. Hiệu đính nội dung chuẩn thực hiện ở chi tiết nguồn; Studio đối chiếu/duyệt.
  Native-table correction cũ không được ghi lên nguồn đã chuyển chuẩn.
- RAG giữ canonical table units ngay cả khi có reviewed facts, vì facts không bao phủ
  mọi ô/điều kiện. Enumeration loại bản biểu diễn trùng canonical/fact theo đầy đủ
  binding/index/source/hash/unit + code/name/combination/year; không gộp khác nguồn/năm.
  Follow-up tái sử dụng luồng kiểm snapshot/records hiện có. Không thêm lượt model.
- Revision cũ vẫn legacy rõ ràng; không chuyển dữ liệu đang xuất bản tại chỗ. Giữ
  manifest seals cũ khi thêm trường provenance. Chỉ mục mới có source/hash/manifest
  mới; publication epoch/snapshot hiện có tiếp tục cô lập cache. Không đổi Top K,
  embedding, model, provider hoặc giới hạn context trong batch này.

Trước dọn kho: chạy kiểm kê local từ `backend` bằng
`python -m scripts.standard_migration_inventory --collection col_admissions --save-report`.
Lệnh đọc DB bằng repeatable-read/read-only và lưu báo cáo riêng qua StorageDriver;
không xuất prompt/key, không reset/index/publish. Báo cáo **không** chứng nhận bản
sao lưu và **không** cấp quyền xóa. Người vận hành tạo/kiểm tra bản backup đầy đủ
trên UI và giữ mật khẩu; seed cấu hình không thay thế backup corpus/vector.

Batch 526 chưa dọn, chuyển 33 revision thật, reindex hay publish. Dọn sidecar mới,
đối chiếu bản backup và nạp bộ nguồn thật thuộc đợt sau; phải kiểm phạm vi trước xóa.

### 11.3. Vận hành chuyển kho — phiên 528

Người dùng đã chấp nhận bỏ full backup cho riêng đợt528. Không áp ngoại lệ đó cho
lần dọn khác. Chỉ `col_admissions` được pause/purge; giữ Repository, cấu hình và
audit tombstones. Purge liệt kê snapshot/preview/QNU MD/JSON/raw sidecar, kiểm toàn
bộ prefix trước external delete và giữ tệp còn được nguồn khác tham chiếu.

Operator có thể dùng `scripts.standard_migration_batch` để kiểm kê fingerprint,
purge đúng inventory với waiver tường minh, import/retry qua service và kiểm pair.
`dispatch=False` là tùy chọn Python nội bộ: job được gắn `operator`, xử lý trong
process có mã hiện tại và Redis lease; không bị reconciler phát sang worker cũ.
API bình thường vẫn enqueue. Nếu operator process gián đoạn, kiểm job/item thực tế
rồi retry đúng batch; không gọi thành công hoặc tự bỏ job đang chạy.

MD ready không phải quyền xuất bản. Chỉ revision được người dùng duyệt cụ thể mới
được review/vector/publish; script `publish_standard_revision` kiểm permission,
identity/pair và không nhận nguồn có issue/ô bất định trong workflow đơn giản này.
Header OCR mặc định trong extraction dùng PaddleOCR tường minh, không tự mở `auto`
cloud chain. Không đổi cấu hình ModelOps, embedding hay Top K khi chuyển kho.

Kết quả528:6pair hợp lệ, chỉ1DOCX đã xuất bản theo xác nhận user,5PDF vẫn chờ đối
soát. Không coi nạp thành công là bằng chứng OCR/chất lượng trả lời đã đạt.
