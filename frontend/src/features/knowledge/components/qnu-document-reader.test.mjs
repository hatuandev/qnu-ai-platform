import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { createRequire } from "node:module";
import { test } from "node:test";
import { runInNewContext } from "node:vm";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import remarkParse from "remark-parse";
import ts from "typescript";
import { unified } from "unified";

const require = createRequire(import.meta.url);
function load(url, overrides) {
  const output = ts.transpileModule(readFileSync(url, "utf8"), {
    compilerOptions: {
      module: ts.ModuleKind.CommonJS,
      jsx: ts.JsxEmit.ReactJSX,
    },
  }).outputText;
  const exports = {};
  runInNewContext(output, {
    exports,
    require: (name) => overrides[name] ?? require(name),
  });
  return exports;
}
const primitives = load(
  new URL("../../../components/ui/table.tsx", import.meta.url),
  { "@/lib/utils": { cn: (...values) => values.filter(Boolean).join(" ") } },
);
const { QnuDocumentReader } = load(
  new URL("./qnu-document-reader.tsx", import.meta.url),
  {
    "react-markdown": ReactMarkdown,
    "remark-gfm": remarkGfm,
    "@/components/ui/table": primitives,
  },
);
const fixture = (markdown) => ({
  title: "Fixture",
  blocks: [
    { id: "b", anchor: "qnu-b", type: "list", markdown, references: [] },
  ],
  notes: [],
});
const render = (document) =>
  renderToStaticMarkup(React.createElement(QnuDocumentReader, { document }));

test("actual Markdown AST keeps three levels and original alphabetic label", () => {
  const md = "7. Parent\n   - **a)** Child\n     - Condition\n8. Next";
  const tree = unified().use(remarkParse).use(remarkGfm).parse(md);
  assert.equal(tree.children[0].start, 7);
  const child = tree.children[0].children[0].children[1];
  assert.equal(child.type, "list");
  assert.equal(child.children[0].children[1].type, "list");
  const html = render(fixture(md));
  assert.match(html, /<ol start="7">/);
  assert.match(html, /<strong>a\)<\/strong>/);
});

test("notes have distinct IDs, readable paragraphs, and every return target exists", () => {
  const document = fixture("Source.");
  document.blocks[0].references = [
    { id: "qnu-ref", target_id: "qnu-note", label: "1" },
  ];
  document.notes = [
    {
      id: "n",
      anchor: "qnu-note",
      label: "1",
      markdown: "First.\n\nSecond.",
      anchors: document.blocks[0].references,
      unresolved: true,
    },
  ];
  const html = render(document);
  assert.match(html, /id="qnu-ref"/);
  assert.match(html, /href="#qnu-note"/);
  assert.match(html, /id="qnu-note"/);
  assert.match(html, /href="#qnu-ref"/);
  assert.doesNotMatch(html, /<pre>/);
  assert.match(html, /chưa xác định/);
});

test("source table renders multirow headers and spans without coercing source cells", () => {
  const document = fixture("");
  document.blocks[0].table = {
    headers: ["Code", "2034 / Count"],
    column_ids: ["c1", "c2"],
    rows: [["00028", "0"]],
    row_ids: ["r"],
    references: [],
    layout: {
      rows: 3,
      columns: 2,
      header_rows: 2,
      cells: [
        { text: "Code", row_start: 0, row_end: 2, col_start: 0, col_end: 1 },
        { text: "2034", row_start: 0, row_end: 1, col_start: 1, col_end: 2 },
        { text: "Count", row_start: 1, row_end: 2, col_start: 1, col_end: 2 },
        { text: "00028", row_start: 2, row_end: 3, col_start: 0, col_end: 1 },
        { text: "0", row_start: 2, row_end: 3, col_start: 1, col_end: 2 },
      ],
    },
  };
  const html = render(document);
  assert.match(html, /rowSpan="2"/i);
  assert.match(html, />00028<\/td>/);
  assert.match(html, />0<\/td>/);
});

test("untrusted source cannot load images or render active HTML", () => {
  const html = render(
    fixture(
      "![scan](https://external.invalid/scan.png)\n\n<script>alert(1)</script>\n\n[x](javascript:alert(1))",
    ),
  );
  assert.doesNotMatch(html, /<img|<script|href="javascript:/);
});

test("export footnote definitions parse as notes, never code", () => {
  const tree = unified()
    .use(remarkParse)
    .use(remarkGfm)
    .parse("Source[^qnu-note].\n\n[^qnu-note]: First.\n    \n    Second.");
  assert.equal(tree.children[1].type, "footnoteDefinition");
  assert.equal(tree.children[1].children.length, 2);
  assert.ok(
    tree.children[1].children.every((node) => node.type === "paragraph"),
  );
});

test("child item references create their return anchor inside the child", () => {
  const document = fixture(
    "7. Parent\n   - **a)** Child.[1](#qnu-note--ref--qnu-ref)",
  );
  document.blocks[0].embedded_references = [
    { id: "qnu-ref", target_id: "qnu-note", label: "1" },
  ];
  const html = render(document);
  assert.match(html, /Child\.<a id="qnu-ref" href="#qnu-note"/);
});

test("an empty reader reports the actual empty state", () => {
  assert.match(
    render({ title: "Empty", blocks: [], notes: [] }),
    /Chưa có nội dung/,
  );
});

test("explicit source numbering restart creates a separate ordered list", () => {
  const md =
    "7. First\n8. Second\n\n<!-- source-list-restart -->\n\n3. Restarted";
  const tree = unified().use(remarkParse).use(remarkGfm).parse(md);
  assert.deepEqual(
    tree.children.filter((n) => n.type === "list").map((n) => n.start),
    [7, 3],
  );
  assert.match(render(fixture(md)), /<ol start="3">/);
});
