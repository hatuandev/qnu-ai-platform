import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { createRequire } from "node:module";
import { test } from "node:test";
import { runInNewContext } from "node:vm";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import ts from "typescript";

const require = createRequire(import.meta.url);
function loadSource(url, overrides = {}) {
  const source = ts.transpileModule(readFileSync(url, "utf8"), {
    compilerOptions: {
      module: ts.ModuleKind.CommonJS,
      jsx: ts.JsxEmit.ReactJSX,
    },
  }).outputText;
  const exports = {};
  const context = {
    exports,
    require: (name) => overrides[name] ?? require(name),
    fetch: (...args) => globalThis.fetch(...args),
  };
  runInNewContext(source, context, { filename: url.pathname });
  return exports;
}
const { SemanticReviewPreview } = loadSource(
  new URL("./semantic-review-preview.tsx", import.meta.url),
);
const proposal = {
  status: "proposed",
  annotations: {
    notes: [
      {
        note_unit_id: "note",
        table_id: "table",
        scope: "column",
        row_unit_ids: [],
        column_ids: ["col"],
        evidence_quote: "Only this column <script>bad()</script>",
      },
    ],
    cells: [
      {
        row_unit_id: "row",
        column_id: "col",
        raw: "Not announced",
        state: "not_stated",
        evidence_quote: "Not announced",
      },
    ],
  },
};
const artifact = {
  semantic_annotations: proposal,
  tables: [
    {
      id: "table",
      columns: [{ id: "col", header_path: ["Quota", "2027"] }],
      row_unit_ids: ["row"],
      rows: [["0012", "Example program"]],
    },
  ],
};

test("review renders real source coordinates and escaped exact quotes", () => {
  const html = renderToStaticMarkup(
    React.createElement(SemanticReviewPreview, { artifact }),
  );
  assert.match(html, /Quota \/ 2027/);
  assert.match(html, /0012/);
  assert.match(html, /Nguồn chưa nêu/);
  assert.match(html, /&lt;script&gt;/);
  assert.doesNotMatch(html, /<script>/);
});

test("applied, unavailable or absent proposals do not masquerade as pending preview", () => {
  for (const status of ["verified", "empty", "unavailable", "rejected"]) {
    const value = {
      ...artifact,
      semantic_annotations: { ...proposal, status },
    };
    assert.equal(
      renderToStaticMarkup(
        React.createElement(SemanticReviewPreview, { artifact: value }),
      ),
      "",
    );
  }
});

const { knowledgeApi } = loadSource(
  new URL("../../../services/knowledge-api.ts", import.meta.url),
  {
    "./http-client": {
      BASE_URL: "/test",
      getAuthHeaders: (extra) =>
        new Headers({ Authorization: "Bearer test", ...extra }),
    },
  },
);

test("semantic actions send authenticated POST and exact reviewed hash to selected revision", async () => {
  const calls = [];
  const original = globalThis.fetch;
  globalThis.fetch = async (url, init) => {
    calls.push({ url, init });
    return new Response(
      JSON.stringify({ id: "draft", status: "review_required" }),
    );
  };
  try {
    await knowledgeApi.generateSemanticProposals(
      "collection",
      "source",
      "draft",
    );
    await knowledgeApi.reviewSemanticProposals(
      "collection",
      "source",
      "draft",
      "a".repeat(64),
      "Checked source",
    );
    await knowledgeApi.reviewSourceRevision(
      "collection",
      "source",
      "draft",
      "approved",
      "Checked source",
      "a".repeat(64),
    );
    assert.match(calls[0].url, /draft\/semantic-proposals$/);
    assert.match(calls[1].url, /draft\/semantic-review$/);
    for (const { init } of calls) {
      assert.equal(init.method, "POST");
      assert.equal(init.headers.get("Authorization"), "Bearer test");
    }
    for (const { init } of calls.slice(1)) {
      assert.equal(
        JSON.parse(init.body).expected_semantic_proposal_hash,
        "a".repeat(64),
      );
      assert.equal(init.headers.get("Content-Type"), "application/json");
    }
  } finally {
    globalThis.fetch = original;
  }
});

test("backend stale-review failure stays a failure", async () => {
  const original = globalThis.fetch;
  globalThis.fetch = async () =>
    new Response(JSON.stringify({ detail: "Source has changed" }), {
      status: 409,
    });
  try {
    await assert.rejects(
      knowledgeApi.reviewSemanticProposals("c", "s", "r", "old", "Checked"),
      /Source has changed/,
    );
  } finally {
    globalThis.fetch = original;
  }
});
