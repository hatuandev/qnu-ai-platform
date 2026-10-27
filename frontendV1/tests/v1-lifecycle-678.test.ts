import { expect, test } from "vitest";
import { createV1Client } from "@/app/api/v1/client";
import type { CallerWorkspaceRole } from "@/app/auth/v1/permissions";
import { addRevision } from "@/features/knowledge/requests";
import {
  canLifecycleAction,
  canReadOperations,
} from "@/features/lifecycle/permissions";
import {
  acceptLifecycle,
  getLifecycleAction,
  listArchivedResources,
  previewLifecycle,
} from "@/features/lifecycle/requests";
import {
  acceptRecovery,
  getReadiness,
  listJobs,
  previewRecovery,
} from "@/features/operations/requests";
import { operationsSearchSchema } from "@/features/operations/search";

type Call = { url: string; method: string; headers: Headers; body: unknown };
function recorder() {
  const calls: Call[] = [];
  const client = createV1Client({
    prefix: "/platform/v1alpha1",
    fetchImpl: async (url, options) => {
      calls.push({
        url,
        method: options?.method ?? "GET",
        headers: new Headers(options?.headers),
        body:
          options?.body instanceof FormData
            ? options.body
            : options?.body
              ? JSON.parse(String(options.body))
              : undefined,
      });
      return new Response(JSON.stringify({ items: [], limit: 21, offset: 0 }), {
        headers: { "Content-Type": "application/json" },
      });
    },
  });
  return { calls, client };
}
test("lifecycle preview carries exact target and reason; accept and replay keep body/hash/key", async () => {
  const { client, calls } = recorder();
  const target = {
    kind: "document" as const,
    resource_id: "doc",
    action: "replace" as const,
    replacement_version_id: "version-new",
    reason: "Replace approved version",
  };
  await previewLifecycle(client, "workspace", target);
  const preview = { id: "preview-one", preview_sha256: "a".repeat(64) };
  await acceptLifecycle(client, "workspace", preview);
  await acceptLifecycle(client, "workspace", preview);
  expect(calls[0]).toMatchObject({
    url: "/platform/v1alpha1/workspaces/workspace/lifecycle/previews",
    method: "POST",
    body: target,
  });
  expect(calls[1].body).toEqual({
    preview_id: preview.id,
    preview_sha256: preview.preview_sha256,
  });
  expect(calls[2].body).toEqual(calls[1].body);
  expect(calls[1].headers.get("Idempotency-Key")).toBe("lifecycle:preview-one");
  expect(calls[2].headers.get("Idempotency-Key")).toBe(
    calls[1].headers.get("Idempotency-Key"),
  );
});
test("trash requests an extra row to detect the next page without inventing totals", async () => {
  const { client, calls } = recorder();
  await listArchivedResources(client, "workspace", 3);
  await getLifecycleAction(client, "workspace", "receipt");
  const url = new URL(calls[0].url, "http://synthetic.invalid");
  expect(url.searchParams.get("limit")).toBe("21");
  expect(url.searchParams.get("offset")).toBe("40");
  expect(calls[1].url).toBe(
    "/platform/v1alpha1/workspaces/workspace/lifecycle/actions/receipt",
  );
});
test.each([true, false, undefined])(
  "revision upload preserves staged=%s and omits title",
  async (staged) => {
    const { client, calls } = recorder();
    await addRevision(
      client,
      "w",
      "c",
      "s",
      new File(["%PDF-synthetic"], "synthetic.pdf", {
        type: "application/pdf",
      }),
      "upload-key",
      staged,
    );
    const body = calls[0].body as FormData;
    expect(body.get("staged")).toBe(
      staged === undefined ? null : String(staged),
    );
    expect(body.get("title")).toBeNull();
    expect(calls[0].headers.get("Idempotency-Key")).toBe("upload-key");
  },
);
test("operations filters/pagination remain server side; readiness is only GET", async () => {
  const { client, calls } = recorder();
  await listJobs(client, "w", {
    page: 3,
    pageSize: 50,
    kind: "ocr",
    status: "uncertain",
    collectionId: "c",
  });
  await getReadiness(client, "w");
  const url = new URL(calls[0].url, "http://synthetic.invalid");
  expect(Object.fromEntries(url.searchParams)).toEqual({
    limit: "50",
    offset: "100",
    kind: "ocr",
    status: "uncertain",
    collection_id: "c",
  });
  expect(calls[1]).toMatchObject({
    method: "GET",
    url: "/platform/v1alpha1/workspaces/w/operations/readiness",
    body: undefined,
  });
});
test("recovery uses the server preview hash and stable key rather than resending a job", async () => {
  const { client, calls } = recorder();
  await previewRecovery(client, "w", "index", "job", "Recover expired lease");
  await acceptRecovery(client, "w", {
    id: "operation-one",
    preview_sha256: "b".repeat(64),
  });
  expect(calls[0].url).toBe(
    "/platform/v1alpha1/workspaces/w/operations/jobs/index/job/recovery-preview",
  );
  expect(calls[1]).toMatchObject({
    method: "POST",
    url: "/platform/v1alpha1/workspaces/w/operations/actions",
    body: { preview_id: "operation-one", preview_sha256: "b".repeat(64) },
  });
  expect(calls[1].headers.get("Idempotency-Key")).toBe(
    "operations:operation-one",
  );
});
test("job cancellation retains the concrete executor kind in the lifecycle preview", async () => {
  const { client, calls } = recorder();
  await previewLifecycle(client, "w", {
    kind: "job",
    resource_id: "auto-review-job",
    job_kind: "auto_review",
    action: "cancel",
    reason: "Operator cancellation",
  });
  expect(calls[0].body).toEqual({
    kind: "job",
    resource_id: "auto-review-job",
    job_kind: "auto_review",
    action: "cancel",
    reason: "Operator cancellation",
  });
});
const admin: CallerWorkspaceRole = { kind: "member", role: "admin" };
const editor: CallerWorkspaceRole = { kind: "member", role: "editor" };
const member: CallerWorkspaceRole = { kind: "member", role: "member" };
const reviewer: CallerWorkspaceRole = { kind: "member", role: "reviewer" };
test("UI lifecycle permissions match editorial/admin/owner boundaries", () => {
  expect(canLifecycleAction(editor, "source", "archive")).toBe(true);
  expect(canLifecycleAction(editor, "source", "delete")).toBe(false);
  expect(
    canLifecycleAction(editor, "source", "restore", { deleted: true }),
  ).toBe(false);
  expect(canLifecycleAction(editor, "source", "restore")).toBe(true);
  expect(canLifecycleAction(editor, "assistant", "pause")).toBe(false);
  expect(canLifecycleAction(admin, "assistant", "pause")).toBe(true);
  expect(
    canLifecycleAction(member, "conversation", "delete", {
      ownedConversation: true,
    }),
  ).toBe(true);
  expect(
    canLifecycleAction({ kind: "platform-admin" }, "conversation", "delete"),
  ).toBe(false);
  expect(canLifecycleAction(reviewer, "job", "cancel")).toBe(false);
  expect(
    canLifecycleAction(member, "job", "cancel", {
      turn: true,
      ownedConversation: true,
    }),
  ).toBe(true);
});
test("reviewer reads operations, ordinary member cannot; unknown role never grants access", () => {
  expect(canReadOperations(reviewer)).toBe(true);
  expect(canReadOperations(editor)).toBe(true);
  expect(canReadOperations(member)).toBe(false);
  expect(canReadOperations({ kind: "unknown" })).toBe(false);
});
test("operations deep link retains job/receipt IDs and validates filter types", () => {
  expect(
    operationsSearchSchema.parse({
      page: "2",
      jobKind: "ocr",
      jobId: "job",
      lifecycleActionId: "life",
    }),
  ).toMatchObject({
    page: 2,
    pageSize: 20,
    jobKind: "ocr",
    jobId: "job",
    lifecycleActionId: "life",
  });
  expect(operationsSearchSchema.safeParse({ kind: "not-a-job" }).success).toBe(
    false,
  );
});
