import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { createRequire } from "node:module";
import { test } from "node:test";
import { runInNewContext } from "node:vm";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
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
const map = {
  collection_id: "c",
  issues: [],
  pages: [
    {
      id: "own",
      binding_id: "b",
      source_revision_id: "r",
      title: "Viện",
      source_title: "Nguồn A",
      source_revision_no: 1,
      temporal: [],
    },
    {
      id: "other",
      binding_id: "b2",
      source_revision_id: "r2",
      title: "Viện",
      source_title: "Nguồn B",
      source_revision_no: 2,
      temporal: [{ role: "data", years: [2025] }],
    },
    {
      id: "candidate",
      binding_id: "b3",
      source_revision_id: "r3",
      title: "Tên gần giống",
      temporal: [],
    },
    {
      id: "old",
      binding_id: "b",
      source_revision_id: "old",
      title: "Cũ",
      temporal: [],
    },
  ],
  graph: {
    links: [
      {
        id: "e",
        source: "other",
        target: "own",
        status: "structural",
        relation: "co_mention",
      },
      {
        id: "a",
        source: "own",
        target: "candidate",
        status: "candidate",
        relation: "alias",
      },
    ],
  },
};
const container = ({ children }) => React.createElement("div", null, children);
const primitives = Object.fromEntries(
  ["Alert", "AlertDescription", "Badge", "Button"].map((name) => [
    name,
    container,
  ]),
);
const ui = {
  "@/components/ui/alert": primitives,
  "@/components/ui/badge": primitives,
  "@/components/ui/button": primitives,
  "@/services/knowledge-api": {
    extractErrorMessage: (_e, fallback) => fallback,
  },
};
const navigation = (query = () => ({}), state = false) =>
  load(new URL("./knowledge-wiki-navigation.tsx", import.meta.url), {
    ...ui,
    "@tanstack/react-query": { useQuery: query },
    react: { ...React, useState: () => [state, () => {}] },
  });

test("related links include backlinks and exclude candidates and old revision", () => {
  const { relatedWikiPages } = navigation();
  assert.equal(
    JSON.stringify(relatedWikiPages(map, "b", "r").map((p) => p.id)),
    '["other"]',
  );
  assert.equal(relatedWikiPages(map, "b", "newer").length, 0);
});

test("related source link pins revision and shows data-year and source separately", () => {
  const { WikiRelatedLinks } = navigation();
  const html = renderToStaticMarkup(
    React.createElement(WikiRelatedLinks, {
      data: map,
      bindingId: "b",
      revisionId: "r",
    }),
  );
  assert.match(html, /\/knowledge\/c\/sources\/b2\?revision=r2#wiki-other/);
  assert.match(html, /Dữ liệu: 2025/);
  assert.match(html, /Nguồn B/);
  assert.doesNotMatch(html, /Tên gần giống/);
});

test("no review permission keeps advanced queries disabled even with cached data", () => {
  const calls = [];
  const { KnowledgeWikiNavigation } = navigation((options) => {
    calls.push(options);
    return { data: map };
  }, true);
  const html = renderToStaticMarkup(
    React.createElement(KnowledgeWikiNavigation, {
      collectionId: "c",
      sourceId: "b",
      revisionId: "r",
      canReview: false,
    }),
  );
  assert.ok(
    calls
      .filter((c) => c.queryKey[0].includes("review"))
      .every((c) => c.enabled === false),
  );
  assert.doesNotMatch(html, /Đối chiếu nâng cao/);
});

test("read error stays visible instead of claiming an empty valid map", () => {
  const { KnowledgeWikiNavigation } = navigation(() => ({
    isError: true,
    error: new Error("denied"),
  }));
  const html = renderToStaticMarkup(
    React.createElement(KnowledgeWikiNavigation, {
      collectionId: "c",
      sourceId: "b",
      revisionId: "r",
      canReview: false,
    }),
  );
  assert.match(html, /Không đọc được trang liên quan/);
  assert.doesNotMatch(html, /Chưa có trang liên quan/);
});

const api = (fetch) =>
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

test("map and review use authenticated GET with exact source scope", async () => {
  const client = api(async (url, init) => {
    assert.equal(init.headers.Authorization, "Bearer fixture");
    assert.ok(!init.method || init.method === "GET");
    if (url.endsWith("knowledge-map/review"))
      return { ok: true, json: async () => map };
    assert.equal(
      url,
      "http://test/knowledge/collections/c/sources/b/revisions/r/knowledge-pages/review",
    );
    return {
      ok: true,
      json: async () => ({
        collection_id: "c",
        binding_id: "b",
        source_revision_id: "r",
        issues: [],
      }),
    };
  });
  assert.equal((await client.getKnowledgeMap("c", true)).collection_id, "c");
  assert.equal(
    (await client.getSourceKnowledgeReview("c", "b", "r")).source_revision_id,
    "r",
  );
});

test("foreign collection and revision responses cannot enter the UI", async () => {
  const client = api(async () => ({
    ok: true,
    json: async () => ({
      collection_id: "other",
      binding_id: "b",
      source_revision_id: "other",
    }),
  }));
  await assert.rejects(client.getKnowledgeMap("c"), /không khớp/);
  await assert.rejects(
    client.getSourceKnowledgeReview("c", "b", "r"),
    /không khớp/,
  );
});

test("403 review error is not converted to empty success", async () => {
  const client = api(async () => ({
    ok: false,
    json: async () => ({ detail: "Không có quyền" }),
  }));
  await assert.rejects(client.getKnowledgeMap("c", true), /Không có quyền/);
});
