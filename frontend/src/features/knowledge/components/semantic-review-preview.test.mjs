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
  {
    "@/components/ui/button": {
      Button: ({ children, ...props }) =>
        React.createElement("button", { type: "button", ...props }, children),
    },
    "@/components/ui/textarea": {
      Textarea: (props) => React.createElement("textarea", props),
    },
  },
);
const { SemanticCheckpointImport } = loadSource(
  new URL("./semantic-checkpoint-import.tsx", import.meta.url),
  {
    "@/components/ui/button": {
      Button: ({ children, ...props }) =>
        React.createElement("button", { type: "button", ...props }, children),
    },
    "@/components/ui/input": {
      Input: (props) => React.createElement("input", props),
    },
    "@/components/ui/textarea": {
      Textarea: (props) => React.createElement("textarea", props),
    },
    "@/services/knowledge-api": {
      extractErrorMessage: (error, fallback) => error?.message ?? fallback,
    },
  },
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

test("related reference uses its own action and shows the full appendix body", () => {
  const value = structuredClone(artifact);
  const binding = {
    source_unit_id: "appendix",
    evidence_id: "ev:body",
    start: 0,
    end: 35,
  };
  value.semantic_annotations.context_review = {
    scope: "selected_tables",
    unresolved: [],
    contract: "qnu-context-review-v2",
    issues: [
      {
        issue_id: "original-issue",
        kind: "deferred_reference",
        target: { table_ids: ["table"] },
        unit_ids: ["heading"],
        reason: "Read the appendix",
        review_evidence: [
          {
            evidence_binding: { ...binding, source_unit_id: "heading" },
            evidence_quote: "### Appendix",
          },
        ],
      },
    ],
    reference_assessments: [
      {
        issue_id: "original-issue",
        relevance: "related",
        assertion_ids: ["assertion:test"],
        reason: "Only group B; excludes group A",
        evidence: [
          {
            evidence_binding: binding,
            evidence_quote: "Only B; valid thirty days; never A.",
          },
        ],
      },
    ],
  };
  const html = renderToStaticMarkup(
    React.createElement(SemanticReviewPreview, {
      artifact: value,
      onDecision() {},
    }),
  );
  assert.match(html, /Only B; valid thirty days; never A/);
  assert.match(html, /Xác nhận đã đối chiếu tham chiếu liên quan/);
  assert.doesNotMatch(html, /Xác nhận tham chiếu không chi phối đích này/);
});

test("a lone heading cannot offer a decision and reference spans use Unicode code points", () => {
  const value = structuredClone(artifact);
  value.semantic_annotations.context_review = {
    scope: "selected_tables",
    unresolved: [],
    issues: [
      {
        issue_id: "heading-only",
        kind: "deferred_reference",
        target: {},
        unit_ids: ["heading"],
        reason: "Need body",
        review_evidence: [
          {
            evidence_binding: { evidence_id: "ev:heading" },
            evidence_quote: "### Only a heading",
          },
        ],
      },
    ],
  };
  const binding = {
    evidence_id: "ev:unicode",
    source_unit_id: "appendix",
    start: 2,
    end: 9,
    text_sha256: "a".repeat(64),
  };
  value.semantic_annotations.annotations.notes[0].related_evidence = [binding];
  value.retrieval_units = {
    units: [{ id: "appendix", text: "😀 Điều kiện khác" }],
  };
  const html = renderToStaticMarkup(
    React.createElement(SemanticReviewPreview, {
      artifact: value,
      onDecision() {},
    }),
  );
  assert.doesNotMatch(html, /Xác nhận tham chiếu không chi phối đích này/);
  assert.match(html, /Tham chiếu và điều kiện đi kèm/);
  assert.match(html, />Điều ki<|>Điều kiệ</);
});

test("scope confirmation shows exact string row codes and full exclusion separately", () => {
  const value = structuredClone(artifact);
  value.tables[0].row_unit_ids.push("excluded-row");
  value.tables[0].rows.push(["00027", "Excluded program"]);
  value.semantic_annotations.context_review = {
    contract: "qnu-context-review-v2",
    scope: "selected_tables",
    unresolved: [],
    issues: [
      {
        issue_id: "ctxissue:row",
        kind: "scope_confirmation_required",
        reason: "Check exact row and exclusions",
        unit_ids: ["note"],
        target: { table_id: "table", row_unit_ids: ["row"], column_ids: [] },
        review_evidence: [
          {
            evidence_binding: {
              evidence_id: "ev:full",
              source_unit_id: "note",
            },
            evidence_quote: "Only 0012 applies; 00027 is excluded.",
          },
        ],
      },
    ],
  };
  const html = renderToStaticMarkup(
    React.createElement(SemanticReviewPreview, {
      artifact: value,
      onDecision() {},
    }),
  );
  const targets = html.match(/Dòng cần xác nhận: ([^<]+)/)?.[1];
  assert.match(targets, /0012/);
  assert.doesNotMatch(targets, /00027/);
  assert.match(html, /Only 0012 applies; 00027 is excluded/);
  assert.match(html, /Xác nhận đúng tập dòng\/cột này/);
});

for (const status of [
  "proposed",
  "empty",
  "rejected",
  "changes_requested",
  "verified",
]) {
  test(`context issue survives ${status} preview without calling it a clean empty result`, () => {
    const value = structuredClone(artifact);
    value.semantic_annotations.status = status;
    value.semantic_annotations.context_review = {
      coverage_complete: true,
      scope: "document",
      unresolved: [
        { unit_ids: ["qnu:missing"], reason: "Missing <mandatory> condition" },
      ],
      semantic_support: "human_review_required",
    };
    value.source_policy = {
      mode: "strict",
      semantic_unknown_count: 0,
      acknowledged_limit_count: 0,
      unfinished_count: 0,
      context_blocker_count: 1,
      publication_enabled: false,
    };
    const html = renderToStaticMarkup(
      React.createElement(SemanticReviewPreview, { artifact: value }),
    );
    assert.match(html, /qnu:missing/);
    assert.match(html, /Missing &lt;mandatory&gt; condition/);
    assert.match(html, /1 vấn đề còn chặn/);
    if (status !== "proposed")
      assert.doesNotMatch(html, /Đề xuất từ model cần bạn đối chiếu/);
  });
}

test("specific issue intent sends coordinates, source binding and reason without client actor", async () => {
  const original = globalThis.fetch;
  let sent;
  globalThis.fetch = async (_url, init) => {
    sent = JSON.parse(init.body);
    return new Response(JSON.stringify({ id: "draft" }));
  };
  const decision = {
    issue_id: "ctxissue:TEST",
    action: "scope_confirmed",
    target: { column_ids: ["c4", "c7"] },
    evidence_quote: "Full original condition",
    evidence_binding: { source_unit_id: "qnu:g", start: 0, end: 23 },
    reason: "Checked complete condition and columns",
  };
  try {
    await knowledgeApi.reviewSemanticProposals(
      "c",
      "s",
      "r",
      "b".repeat(64),
      "Specific review",
      "approved",
      "strict",
      [decision],
    );
    assert.deepEqual(sent.context_decisions, [decision]);
    assert.equal(sent.context_decisions[0].actor_id, undefined);
  } finally {
    globalThis.fetch = original;
  }
});

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

test("related reference intent preserves supporting evidence and exact proposal hash", async () => {
  const original = globalThis.fetch;
  let sent;
  globalThis.fetch = async (_url, init) => {
    sent = JSON.parse(init.body);
    return new Response(JSON.stringify({ id: "draft" }));
  };
  const decision = {
    issue_id: "original-issue",
    target: { table_ids: ["table"] },
    action: "related_context_reviewed",
    evidence_binding: { source_unit_id: "heading" },
    evidence_quote: "### Appendix",
    reason: "Read complete body and exclusion",
    supporting_evidence: [{ source_unit_id: "body", evidence_id: "ev:body" }],
  };
  try {
    await knowledgeApi.reviewSemanticProposals(
      "c",
      "s",
      "r",
      "a".repeat(64),
      "Review reference",
      "approved",
      "strict",
      [decision],
    );
    assert.deepEqual(sent.context_decisions, [decision]);
    assert.equal(sent.expected_semantic_proposal_hash, "a".repeat(64));
    assert.equal(sent.context_decisions[0].actor_id, undefined);
  } finally {
    globalThis.fetch = original;
  }
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

test("twelve labeled relations and eighteen separate issues show workflow and reference roles", () => {
  const value = structuredClone(artifact);
  const assertions = Object.fromEntries(
    Array.from({ length: 12 }, (_, i) => [
      `a${i}`,
      `A${String(i + 1).padStart(2, "0")}`,
    ]),
  );
  value.semantic_annotations.proposal_hash = "current-hash";
  value.semantic_annotations.annotations.notes = Array.from(
    { length: 12 },
    (_, i) => ({
      ...proposal.annotations.notes[0],
      evidence_quote: `Rule ${i}`,
      ...(i === 2
        ? {
            context_kind: "workflow",
            context_label: "Hồ sơ thiết bị nhóm A / 2027",
            scope: "group",
            column_ids: [],
            row_unit_ids: ["row"],
          }
        : {}),
    }),
  );
  value.semantic_annotations.context_review = {
    scope: "selected_tables",
    contract: "qnu-context-review-v2",
    unresolved: [],
    assertion_ids: Object.keys(assertions),
    display_labels: { assertions, issues: {} },
    issues: [],
    reference_assessments: [],
  };
  for (let i = 0; i < 18; i++) {
    value.semantic_annotations.context_review.display_labels.issues[
      `issue${i}`
    ] =
      i < 8
        ? `O${String(i + 1).padStart(2, "0")}`
        : `S${String(i - 7).padStart(2, "0")}`;
    value.semantic_annotations.context_review.issues.push({
      issue_id: `issue${i}`,
      kind: "scope_confirmation_required",
      unit_ids: ["note"],
      target: { table_id: "table" },
      reason: `Need review ${i}`,
      review_evidence: [],
    });
  }
  value.semantic_annotations.context_review.reference_assessments.push({
    issue_id: "issue4",
    relevance: "related",
    evidence: [],
    reason: "Typed references",
    assertion_ids: ["a2", "a3", "a8"],
    links: [
      {
        assertion_id: "a2",
        role: "direct",
        reason: "Equipment condition",
        evidence: [],
      },
      {
        assertion_id: "a3",
        role: "protective",
        reason: "Keep identity",
        evidence: [],
      },
      {
        assertion_id: "a8",
        role: "conditional",
        reason: "No automatic Q input",
        condition: "Only if source proves this assessment link",
        evidence: [],
      },
    ],
  });
  const html = renderToStaticMarkup(
    React.createElement(SemanticReviewPreview, { artifact: value }),
  );
  for (const label of Object.values(assertions))
    assert.match(html, new RegExp(`${label} ·`));
  assert.match(html, /Vấn đề gốc và tham chiếu \(8\)/);
  assert.match(html, /Xác nhận phạm vi của từng quan hệ \(10\)/);
  assert.equal((html.match(/Chờ quyết định có xác thực/g) ?? []).length, 18);
  assert.match(html, /Hồ sơ thiết bị nhóm A \/ 2027/);
  assert.match(html, /không trực tiếp sửa dữ liệu số/);
  assert.match(html, /Trực tiếp \(direct\)/);
  assert.match(html, /Bảo vệ \(protective\)/);
  assert.match(html, /Có điều kiện \(conditional\)/);
  assert.match(html, /Only if source proves/);
  assert.match(html, /current-hash/);
  assert.doesNotMatch(html, /<button/);
});

test("checkpoint import without authenticated permission offers no enabled action or approval", () => {
  const html = renderToStaticMarkup(
    React.createElement(SemanticCheckpointImport, {
      canImport: false,
      onImport: async () => {
        throw new Error("must not run");
      },
    }),
  );
  assert.match(html, /Cần đăng nhập/);
  assert.match(html, /<button[^>]*disabled/);
  assert.match(html, /<input[^>]*disabled/);
  assert.doesNotMatch(html, /Đã duyệt|Đã áp dụng/);
});

test("import uses authenticated API and expected current hash; stale remains failure", async () => {
  const original = globalThis.fetch;
  const calls = [];
  globalThis.fetch = async (url, init) => {
    calls.push({ url, init });
    return new Response(
      JSON.stringify({ id: "draft", status: "review_required" }),
    );
  };
  try {
    await knowledgeApi.importSemanticCheckpoint(
      "c",
      "s",
      "draft",
      { contract: "qnu-semantic-checkpoint-v1" },
      "Checked source",
      "old-hash",
    );
    assert.match(calls[0].url, /draft\/semantic-checkpoint$/);
    assert.equal(calls[0].init.headers.get("Authorization"), "Bearer test");
    assert.deepEqual(JSON.parse(calls[0].init.body), {
      checkpoint: { contract: "qnu-semantic-checkpoint-v1" },
      comment: "Checked source",
      expected_semantic_proposal_hash: "old-hash",
    });
    globalThis.fetch = async () =>
      new Response(JSON.stringify({ detail: "Proposal stale" }), {
        status: 409,
      });
    await assert.rejects(
      knowledgeApi.importSemanticCheckpoint("c", "s", "draft", {}, "Checked"),
      /Proposal stale/,
    );
  } finally {
    globalThis.fetch = original;
  }
});
