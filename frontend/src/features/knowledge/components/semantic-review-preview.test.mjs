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

test("bound review shows exact source coordinates, reason and unresolved scope safely", () => {
  const value = structuredClone(artifact);
  value.semantic_annotations.annotations.notes[0].reason =
    "Inspect <script>unsafe</script> scope";
  value.semantic_annotations.annotations.notes[0].evidence_binding = {
    source_unit_id: "qnu:source",
    coordinate_space: "unit_codepoints",
    start: 2,
    end: 18,
    text_sha256: "a".repeat(64),
  };
  value.semantic_annotations.context_review = {
    coverage_complete: true,
    scope: "selected_tables",
    unresolved: [
      { unit_ids: ["qnu:missing"], reason: "Needs <source> condition" },
    ],
  };
  value.retrieval_units = {
    units: [{ id: "qnu:source", text: "Full note; exclude 2025 <source>" }],
  };
  const html = renderToStaticMarkup(
    React.createElement(SemanticReviewPreview, { artifact: value }),
  );
  assert.match(html, /qnu:source/);
  assert.match(html, /Full note; exclude 2025 &lt;source&gt;/);
  assert.match(html, /\[2, 18\)/);
  assert.match(html, /aaaaaaaaaaaa/);
  assert.match(html, /các bảng được chọn/);
  assert.match(html, /qnu:missing/);
  assert.match(html, /Needs &lt;source&gt; condition/);
  assert.match(html, /Inspect &lt;script&gt;unsafe&lt;\/script&gt; scope/);
  assert.doesNotMatch(html, /<script>/);
});

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

test("limit preview keeps raw, displays examination scope and never claims resolved", () => {
  const value = structuredClone(artifact);
  value.semantic_annotations.annotations.limitations = [
    {
      row_unit_id: "row",
      column_id: "col",
      raw: "/",
      basis: "human_examined_scope",
      evidence_unit_id: "note",
      evidence_quote: "No published definition in this scope",
      examined_unit_ids: ["row", "note"],
    },
  ];
  value.retrieval_units = {
    units: [
      { id: "row", text: "Original / cell" },
      { id: "note", text: "Exact source scope" },
    ],
  };
  const html = renderToStaticMarkup(
    React.createElement(SemanticReviewPreview, { artifact: value }),
  );
  assert.match(html, /Giới hạn nguồn cần xác nhận riêng/);
  assert.match(html, /Original \/ cell/);
  assert.match(html, /Exact source scope/);
  assert.match(html, /không quy về 0/);
  assert.match(html, /xuất bản vẫn bị chặn/);
});

test("acknowledged limit summary still reports semantic unknowns", () => {
  const value = {
    ...artifact,
    semantic_annotations: { ...proposal, status: "verified" },
    source_policy: {
      mode: "acknowledged_limits",
      semantic_unknown_count: 2,
      acknowledged_limit_count: 1,
      unfinished_count: 1,
      policy_blocker_count: 1,
      publication_enabled: false,
    },
  };
  const html = renderToStaticMarkup(
    React.createElement(SemanticReviewPreview, { artifact: value }),
  );
  assert.match(html, /Còn 2 ô chưa rõ nghĩa/);
  assert.match(html, /đã xác nhận 1 giới hạn nguồn/);
  assert.match(html, /Xuất bản có giới hạn chưa được bật/);
});

test("acknowledgment and further-check actions send distinct decisions with exact hash", async () => {
  const calls = [];
  const original = globalThis.fetch;
  globalThis.fetch = async (_url, init) => {
    calls.push(JSON.parse(init.body));
    return new Response(
      JSON.stringify({ id: "draft", status: "review_required" }),
    );
  };
  try {
    await knowledgeApi.reviewSemanticProposals(
      "c",
      "s",
      "r",
      "b".repeat(64),
      "Examined scope",
      "acknowledged_limits",
      "acknowledged_limits",
    );
    await knowledgeApi.reviewSemanticProposals(
      "c",
      "s",
      "r",
      "b".repeat(64),
      "Need more evidence",
      "changes_requested",
    );
    assert.equal(calls[0].decision, "acknowledged_limits");
    assert.equal(calls[0].policy_mode, "acknowledged_limits");
    assert.equal(calls[1].decision, "changes_requested");
    assert.equal(calls[1].policy_mode, "strict");
    assert.ok(
      calls.every(
        (value) => value.expected_semantic_proposal_hash === "b".repeat(64),
      ),
    );
  } finally {
    globalThis.fetch = original;
  }
});
