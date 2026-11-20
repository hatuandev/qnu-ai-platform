import assert from "node:assert/strict";
import test from "node:test";
import { parseMarkdownBlocks } from "./markdown-parser.ts";

test("parseMarkdownBlocks parses headings accurately", () => {
  const md = `# Heading 1
## Heading 2
### Heading 3
#### Heading 4`;

  const blocks = parseMarkdownBlocks(md);
  assert.equal(blocks.length, 4);
  assert.equal(blocks[0].type, "h1");
  assert.equal(blocks[0].content, "Heading 1");
  assert.equal(blocks[1].type, "h2");
  assert.equal(blocks[1].content, "Heading 2");
  assert.equal(blocks[2].type, "h3");
  assert.equal(blocks[2].content, "Heading 3");
  assert.equal(blocks[3].type, "h4");
  assert.equal(blocks[3].content, "Heading 4");
});

test("parseMarkdownBlocks parses markdown tables with separator rows", () => {
  const md = `| TT | Tiêu chí | Mức độ |
|---|---|---|
| 1.7 | Đào tạo trực tuyến | Mức 2 |
| 1.8 | Thư viện số | Mức 3 |`;

  const blocks = parseMarkdownBlocks(md);
  assert.equal(blocks.length, 1);
  assert.equal(blocks[0].type, "table");
  assert.ok(blocks[0].tableData);

  const { headers, rows } = blocks[0].tableData;
  assert.equal(headers.length, 3);
  assert.equal(headers[0].text, "TT");
  assert.equal(headers[1].text, "Tiêu chí");
  assert.equal(headers[2].text, "Mức độ");

  assert.equal(rows.length, 2);
  assert.equal(rows[0].cells.length, 3);
  assert.equal(rows[0].cells[0].text, "1.7");
  assert.equal(rows[0].cells[1].text, "Đào tạo trực tuyến");
  assert.equal(rows[0].cells[2].text, "Mức 2");

  assert.equal(rows[1].cells[0].text, "1.8");
  assert.equal(rows[1].cells[1].text, "Thư viện số");
  assert.equal(rows[1].cells[2].text, "Mức 3");
});

test("parseMarkdownBlocks parses lists and bullet points", () => {
  const md = `- Phân hệ LMS
- Phân hệ LCMS
1. Bước 1
2. Bước 2`;

  const blocks = parseMarkdownBlocks(md);
  assert.equal(blocks.length, 2);
  assert.equal(blocks[0].type, "ul");
  assert.equal(blocks[0].items?.length, 2);
  assert.equal(blocks[0].items?.[0].text, "Phân hệ LMS");
  assert.equal(blocks[0].items?.[1].text, "Phân hệ LCMS");

  assert.equal(blocks[1].type, "ol");
  assert.equal(blocks[1].items?.length, 2);
  assert.equal(blocks[1].items?.[0].text, "Bước 1");
  assert.equal(blocks[1].items?.[1].text, "Bước 2");
});

test("parseMarkdownBlocks handles mixed text, tables, quotes and paragraphs", () => {
  const md = `Dưới đây là bảng tổng hợp tiêu chí CĐS:

> Lưu ý: Dữ liệu tính theo năm 2022.

| Tiêu chí | Điểm tối đa |
|---|---|
| 2.4 | 10 |
| 2.5 | 15 |

Các đơn vị cần rà soát hoàn tất trước ngày 30/12/2026.`;

  const blocks = parseMarkdownBlocks(md);
  assert.equal(blocks.length, 4);
  assert.equal(blocks[0].type, "p");
  assert.equal(blocks[0].content, "Dưới đây là bảng tổng hợp tiêu chí CĐS:");

  assert.equal(blocks[1].type, "quote");
  assert.equal(blocks[1].content, "Lưu ý: Dữ liệu tính theo năm 2022.");

  assert.equal(blocks[2].type, "table");
  assert.equal(blocks[2].tableData?.headers.length, 2);
  assert.equal(blocks[2].tableData?.rows.length, 2);

  assert.equal(blocks[3].type, "p");
  assert.equal(
    blocks[3].content,
    "Các đơn vị cần rà soát hoàn tất trước ngày 30/12/2026.",
  );
});

test("parseMarkdownBlocks handles empty or null content safely", () => {
  assert.deepEqual(parseMarkdownBlocks(""), []);
  assert.deepEqual(parseMarkdownBlocks("   \n\n  "), []);
});
