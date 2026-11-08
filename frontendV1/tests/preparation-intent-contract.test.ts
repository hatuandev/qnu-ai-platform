/**
 * Contract tests for the durable preparation intent flow (P3).
 *
 * Covers the wire contract (paths, method, idempotency header, body),
 * query-key isolation between lists/details, and the status/error helpers the
 * dialog and status bar rely on.
 */

import assert from "node:assert/strict";
import { test } from "vitest";
import { createV1Client } from "../src/app/api/v1/client.ts";
import { preparationPaths } from "../src/app/api/v1/endpoints.ts";
import { preparationKeys } from "../src/features/knowledge/preparation-queries.ts";
import {
  cancelPreparationIntent,
  createPreparationIntent,
  getPreparationIntent,
  listPreparationIntents,
} from "../src/features/knowledge/preparation-requests.ts";
import {
  formatPreparationError,
  isPreparationActive,
  preparationStatusLabel,
  preparationStatusVariant,
  shortHash,
} from "../src/features/knowledge/preparation-schemas.ts";
import type {
  PreparationIntent,
  PreparationRequestInput,
  PreparationStatus,
} from "../src/features/knowledge/preparation-types.ts";

const WORKSPACE = "ws-1";
const COLLECTION = "col-1";
const SOURCE = "src-1";
const INTENT = "intent-1";

function buildIntent(
  overrides: Partial<PreparationIntent> = {},
): PreparationIntent {
  return {
    id: INTENT,
    workspace_id: WORKSPACE,
    collection_id: COLLECTION,
    source_id: SOURCE,
    revision_id: "rev-2",
    revision_no: 3,
    revision_sha256: "a".repeat(64),
    mode: "source",
    status: "queued",
    topic: "Quy chế tuyển sinh",
    text_version: 0,
    text_version_id: null,
    text_canonical_sha256: null,
    provider_id: null,
    max_output_tokens: null,
    ocr_run_id: null,
    compilation_run_id: null,
    error_code: null,
    created_at: "2026-11-08T08:00:00Z",
    updated_at: "2026-11-08T08:00:00Z",
    started_at: null,
    finished_at: null,
    ...overrides,
  };
}

type RecordedCall = {
  url: string;
  method: string;
  headers: Headers;
  body: string | undefined;
};

function createMockFetch(handler: (call: RecordedCall) => Response) {
  const calls: RecordedCall[] = [];
  const fetchImpl = async (input: string, init?: RequestInit) => {
    const call: RecordedCall = {
      url: input,
      method: init?.method ?? "GET",
      headers: new Headers(init?.headers),
      body: typeof init?.body === "string" ? init.body : undefined,
    };
    calls.push(call);
    return handler(call);
  };
  return { calls, fetchImpl };
}

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

test("preparation paths pin the source-scoped create/list and collection-scoped detail", () => {
  assert.equal(
    preparationPaths.intents(WORKSPACE, COLLECTION, SOURCE),
    `/workspaces/${WORKSPACE}/collections/${COLLECTION}/sources/${SOURCE}/preparation-intents`,
  );
  assert.equal(
    preparationPaths.intent(WORKSPACE, COLLECTION, INTENT),
    `/workspaces/${WORKSPACE}/collections/${COLLECTION}/preparation-intents/${INTENT}`,
  );
  assert.equal(
    preparationPaths.cancel(WORKSPACE, COLLECTION, INTENT),
    `/workspaces/${WORKSPACE}/collections/${COLLECTION}/preparation-intents/${INTENT}/cancel`,
  );
});

test("create sends POST with the idempotency key and the server-pinned input", async () => {
  const { calls, fetchImpl } = createMockFetch(() =>
    jsonResponse(
      { intent: buildIntent(), created: true, dispatched: true },
      201,
    ),
  );
  const client = createV1Client({ fetchImpl, getToken: () => "token" });
  const input: PreparationRequestInput = {
    mode: "source",
    revision_id: "rev-2",
    ocr_run_id: "run-9",
    text_version: 4,
  };

  const result = await createPreparationIntent(
    client,
    WORKSPACE,
    COLLECTION,
    SOURCE,
    input,
    "idem-key-1",
  );

  assert.equal(result.created, true);
  assert.equal(result.intent.id, INTENT);
  assert.equal(calls.length, 1);
  const call = calls[0];
  assert.equal(call.method, "POST");
  assert.equal(
    call.url,
    `/platform/v1alpha1${preparationPaths.intents(WORKSPACE, COLLECTION, SOURCE)}`,
  );
  assert.equal(call.headers.get("Idempotency-Key"), "idem-key-1");
  assert.equal(call.headers.get("Authorization"), "Bearer token");
  assert.deepEqual(JSON.parse(call.body ?? "null"), input);
});

test("list is source-scoped GET with a bounded limit query", async () => {
  const { calls, fetchImpl } = createMockFetch(() =>
    jsonResponse([buildIntent()]),
  );
  const client = createV1Client({ fetchImpl, getToken: () => "token" });

  const items = await listPreparationIntents(
    client,
    WORKSPACE,
    COLLECTION,
    SOURCE,
  );
  await listPreparationIntents(client, WORKSPACE, COLLECTION, SOURCE, 5);

  assert.equal(items.length, 1);
  assert.equal(calls[0].method, "GET");
  assert.equal(
    calls[0].url,
    `/platform/v1alpha1${preparationPaths.intents(WORKSPACE, COLLECTION, SOURCE)}?limit=20`,
  );
  assert.equal(calls[0].headers.get("Idempotency-Key"), null);
  assert.equal(calls[1].url.endsWith("?limit=5"), true);
});

test("detail and cancel use the collection-level intent path", async () => {
  const { calls, fetchImpl } = createMockFetch((call) => {
    if (call.url.endsWith("/cancel")) {
      return jsonResponse(buildIntent({ status: "cancelled" }));
    }
    return jsonResponse(buildIntent({ status: "compiling" }));
  });
  const client = createV1Client({ fetchImpl, getToken: () => "token" });

  const detail = await getPreparationIntent(
    client,
    WORKSPACE,
    COLLECTION,
    INTENT,
  );
  const cancelled = await cancelPreparationIntent(
    client,
    WORKSPACE,
    COLLECTION,
    INTENT,
  );

  assert.equal(detail.status, "compiling");
  assert.equal(cancelled.status, "cancelled");
  assert.equal(calls[0].method, "GET");
  assert.equal(
    calls[0].url,
    `/platform/v1alpha1${preparationPaths.intent(WORKSPACE, COLLECTION, INTENT)}`,
  );
  assert.equal(calls[1].method, "POST");
  assert.equal(
    calls[1].url,
    `/platform/v1alpha1${preparationPaths.cancel(WORKSPACE, COLLECTION, INTENT)}`,
  );
  assert.deepEqual(JSON.parse(calls[1].body ?? "null"), {});
});

test("preparation keys isolate session, source, and page limit", () => {
  const list = preparationKeys.list(7, WORKSPACE, COLLECTION, SOURCE, 20);
  const sameList = preparationKeys.list(7, WORKSPACE, COLLECTION, SOURCE, 20);
  const otherLimit = preparationKeys.list(7, WORKSPACE, COLLECTION, SOURCE, 5);
  const otherSource = preparationKeys.list(
    7,
    WORKSPACE,
    COLLECTION,
    "src-2",
    20,
  );
  const otherSession = preparationKeys.list(
    8,
    WORKSPACE,
    COLLECTION,
    SOURCE,
    20,
  );
  const detail = preparationKeys.intent(7, WORKSPACE, COLLECTION, INTENT);

  assert.deepEqual(list, sameList);
  assert.notDeepEqual(list, otherLimit);
  assert.notDeepEqual(list, otherSource);
  assert.notDeepEqual(list, otherSession);
  assert.deepEqual(detail.slice(0, 3), ["v1", 7, "workspaces"]);
  assert.equal(detail.includes("sources"), false);
  assert.notDeepEqual(detail, list);
});

test("only queued, waiting_ocr, and compiling keep polling", () => {
  assert.equal(isPreparationActive(undefined), false);
  assert.equal(isPreparationActive(null), false);
  for (const status of ["queued", "waiting_ocr", "compiling"] as const) {
    assert.equal(isPreparationActive(buildIntent({ status })), true);
  }
  for (const status of ["ready", "failed", "uncertain", "cancelled"] as const) {
    assert.equal(isPreparationActive(buildIntent({ status })), false);
  }
});

test("status variants and labels stay semantic", () => {
  const expectations: Array<[PreparationStatus, string, string]> = [
    ["queued", "info", "Đã ghi nhận"],
    ["waiting_ocr", "info", "Đang đọc nội dung"],
    ["compiling", "info", "Đang tạo bản nháp"],
    ["ready", "success", "Bản nháp sẵn sàng"],
    ["failed", "destructive", "Chưa hoàn tất"],
    ["uncertain", "destructive", "Chưa rõ trạng thái"],
    ["cancelled", "outline", "Đã hủy"],
  ];
  for (const [status, variant, label] of expectations) {
    assert.equal(preparationStatusVariant(status), variant);
    assert.equal(preparationStatusLabel(status), label);
  }
});

test("known error codes map to actionable Vietnamese copy", () => {
  assert.match(
    formatPreparationError("preparation_source_changed"),
    /Tệp nguồn đã thay đổi/,
  );
  assert.match(
    formatPreparationError("preparation_text_version_not_ready"),
    /chưa sẵn sàng/,
  );
  assert.match(formatPreparationError("idempotency_conflict"), /khác nội dung/);
  assert.match(formatPreparationError("quota_exceeded"), /hết quota/);

  const unknown = formatPreparationError("something_else");
  assert.match(unknown, /Chuẩn bị nội dung chưa hoàn tất/);
  assert.equal(formatPreparationError(null), unknown);
  assert.equal(formatPreparationError(undefined), unknown);
});

test("shortHash never invents a hash", () => {
  assert.equal(shortHash("b".repeat(64)), "b".repeat(12));
  assert.equal(shortHash(null), "");
  assert.equal(shortHash(undefined), "");
});
