/**
 * P5.2 contract: the document page must describe prepared, published and
 * actually served versions from server fields, never from ordering or timestamps.
 */

import assert from "node:assert/strict";
import { test } from "vitest";
import { describeServingReferences } from "../src/features/knowledge/serving-references.tsx";

const versionOne = { id: "v1", version_no: 1, status: "published" as const };
const versionTwo = { id: "v2", version_no: 2, status: "approved" as const };

test("keeps prepared, published and serving references separate", () => {
  const references = describeServingReferences({
    prepared_version: versionTwo,
    published_version: versionOne,
    served_version: versionOne,
    readiness: { status: "ready" },
  });
  assert.ok(references);
  assert.equal(references.prepared.version?.id, "v2");
  assert.match(references.prepared.detail, /Đã duyệt/);
  assert.equal(references.published.version?.id, "v1");
  assert.equal(references.served.version?.id, "v1");
  assert.equal(references.warning, null);
});

test("warns when the published version is not confirmed as serving", () => {
  const references = describeServingReferences({
    prepared_version: null,
    published_version: versionTwo,
    served_version: null,
    readiness: { status: "outdated" },
  });
  assert.ok(references);
  assert.equal(references.prepared.version, null);
  assert.match(references.served.detail, /chưa khớp/);
  assert.match(references.warning ?? "", /chưa được xác nhận/);
});

test("names both versions when an older binding is still serving", () => {
  const references = describeServingReferences({
    prepared_version: null,
    published_version: { ...versionTwo, status: "published" },
    served_version: versionOne,
    readiness: { status: "ready" },
  });
  assert.ok(references);
  assert.match(references.warning ?? "", /v1/);
  assert.match(references.warning ?? "", /v2/);
});

test("does not claim a draft is waiting for a publish decision", () => {
  const references = describeServingReferences({
    prepared_version: { id: "v3", version_no: 3, status: "draft" },
    published_version: versionOne,
    served_version: versionOne,
    readiness: { status: "ready" },
  });
  assert.ok(references);
  assert.match(references.prepared.detail, /Bản nháp/);
  assert.match(references.prepared.detail, /chưa được duyệt/);
});

test("returns nothing until the server summary is available", () => {
  assert.equal(describeServingReferences(undefined), null);
});
