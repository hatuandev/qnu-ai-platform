import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { createRequire } from "node:module";
import { test } from "node:test";
import { runInNewContext } from "node:vm";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import ts from "typescript";

const require = createRequire(import.meta.url);
function load(url, overrides, globals = {}) {
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
    ...globals,
  });
  return exports;
}
const response = {
  collection_id: "c",
  binding_id: "b",
  source_revision_id: "r",
  status: "ready",
  pages: [],
};
const client = (fetch) =>
  load(
    new URL("../../../services/knowledge-api.ts", import.meta.url),
    {
      "./http-client": {
        BASE_URL: "http://test",
        getAuthHeaders: () => ({ Authorization: "Bearer fixture" }),
      },
    },
    { fetch },
  ).knowledgeApi;

test("pages API retains auth and exact collection/binding/revision", async () => {
  const api = client(async (url, init) => {
    assert.equal(
      url,
      "http://test/knowledge/collections/c/sources/b/revisions/r/knowledge-pages",
    );
    assert.equal(init.headers.Authorization, "Bearer fixture");
    return { ok: true, json: async () => response };
  });
  assert.equal(
    (await api.getSourceKnowledgePages("c", "b", "r")).status,
    "ready",
  );
});

for (const field of ["collection_id", "binding_id", "source_revision_id"]) {
  test(`pages API rejects foreign ${field}`, async () => {
    const api = client(async () => ({
      ok: true,
      json: async () => ({ ...response, [field]: "other" }),
    }));
    await assert.rejects(
      api.getSourceKnowledgePages("c", "b", "r"),
      /không khớp/,
    );
  });
}

test("pages API exposes permission failure instead of fake empty pages", async () => {
  const api = client(async () => ({
    ok: false,
    json: async () => ({ detail: "Không có quyền xem." }),
  }));
  await assert.rejects(
    api.getSourceKnowledgePages("c", "b", "r"),
    /Không có quyền/,
  );
});

const container = ({ children }) => React.createElement("div", null, children);
const primitive = (names) =>
  Object.fromEntries(names.map((name) => [name, container]));
const { KnowledgeWikiContent } = load(
  new URL("./knowledge-wiki-panel.tsx", import.meta.url),
  {
    "@tanstack/react-query": {},
    "@/rbac/context": {},
    "@/services/knowledge-api": {},
    "react-markdown": ReactMarkdown,
    "remark-gfm": remarkGfm,
    "@/components/ui/accordion": primitive([
      "Accordion",
      "AccordionContent",
      "AccordionItem",
      "AccordionTrigger",
    ]),
    "@/components/ui/alert": primitive(["Alert", "AlertDescription"]),
    "@/components/ui/badge": primitive(["Badge"]),
    "@/components/ui/button": primitive(["Button"]),
    "@/components/ui/card": primitive([
      "Card",
      "CardContent",
      "CardHeader",
      "CardTitle",
    ]),
    "@/components/ui/sheet": primitive([
      "Sheet",
      "SheetContent",
      "SheetHeader",
      "SheetTitle",
      "SheetDescription",
    ]),
  },
);

test("rendered page keeps year and exceptions, hides metadata and external resources", () => {
  const data = {
    ...response,
    pages: [
      {
        id: "p",
        kind: "concept",
        title: "Phương thức 2025",
        references: [],
        markdown:
          "---\nbinding_id: private-machine-id\n---\n# Phương thức\n\nNăm dữ liệu: 2025\n\nNgoại lệ: chỉ áp dụng khi đủ điều kiện.\n\n![x](https://outside.invalid/image.png)\n<script>bad()</script>",
      },
    ],
  };
  const html = renderToStaticMarkup(
    React.createElement(KnowledgeWikiContent, { data }),
  );
  assert.match(html, /2025/);
  assert.match(html, /Ngoại lệ/);
  assert.doesNotMatch(html, /private-machine-id|<img|<script/);
});

test("unavailable generation displays limitation without claiming ready", () => {
  const html = renderToStaticMarkup(
    React.createElement(KnowledgeWikiContent, {
      data: { ...response, status: "unavailable" },
    }),
  );
  assert.match(html, /Chưa biên soạn được/);
  assert.doesNotMatch(html, /Sẵn sàng/);
});
