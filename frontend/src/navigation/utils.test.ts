import assert from "node:assert/strict";
import { test } from "node:test";
import { getBreadcrumbs, isItemActive } from "./utils";

test("sidebar matches descendants only at a segment boundary", () => {
  const item = {
    id: "knowledge",
    title: "Knowledge",
    to: "/knowledge" as const,
  };
  assert.equal(isItemActive(item, "/knowledge"), true);
  assert.equal(
    isItemActive(item, "/knowledge/collection/sources/source"),
    true,
  );
  assert.equal(isItemActive(item, "/knowledge-other"), false);
  assert.equal(
    isItemActive({ id: "portal", title: "Portal", to: "/" }, "/knowledge"),
    false,
  );
});

test("source breadcrumb points to its collection", () => {
  const items = getBreadcrumbs("/knowledge/collection/sources/source");
  assert.equal(items[0].to, "/knowledge");
  assert.deepEqual(items[1], { label: "Kho", to: "/knowledge/collection" });
  assert.equal(items[2].label, "Nguồn tài liệu");
});

test("group detail has a group-list parent", () => {
  const items = getBreadcrumbs("/documents/groups/group");
  assert.equal(items[1].to, "/documents/groups");
  assert.equal(items[2].label, "Nhóm tài liệu");
});

test("provider and assistant details do not fall back to generic admin", () => {
  assert.equal(getBreadcrumbs("/models/provider")[0].to, "/models");
  assert.equal(getBreadcrumbs("/models/provider").at(-1)?.label, "Provider");
  assert.equal(
    getBreadcrumbs("/assistants/admissions").at(-1)?.label,
    "Cấu hình trợ lý",
  );
});
