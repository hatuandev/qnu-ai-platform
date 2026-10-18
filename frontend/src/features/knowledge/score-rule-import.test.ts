import assert from "node:assert/strict";
import { test } from "node:test";
import { parseRuleImport } from "./score-rule-import";

test("exported review stamps never turn an import into an approved rule", () => {
  const source = {
    id: "rule-1",
    status: "verified",
    reviewed_by: "forged",
    reviewed_at: "2026-01-01",
    year: 2026,
  };
  const [draft] = parseRuleImport(JSON.stringify([source]));
  assert.deepEqual(draft, { id: "rule-1", year: 2026 });
  assert.equal(source.reviewed_by, "forged");
});

test("supports one definition and managed-record exports", () => {
  assert.deepEqual(parseRuleImport('{"id":"one"}'), [{ id: "one" }]);
  assert.deepEqual(
    parseRuleImport('{"status":"active","definition":{"id":"one"}}'),
    [{ id: "one" }],
  );
});

test("rejects invalid JSON, non-records, empty and oversized batches", () => {
  for (const input of [
    "not json",
    "null",
    "42",
    "[]",
    '["x"]',
    JSON.stringify(Array(26).fill({ id: "x" })),
  ]) {
    assert.throws(() => parseRuleImport(input));
  }
});
