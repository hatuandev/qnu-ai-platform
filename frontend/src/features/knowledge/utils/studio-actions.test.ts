import assert from "node:assert/strict";
import { test } from "node:test";
import type { KnowledgeSourceRevisionResponse } from "@/types/knowledge";
import { saveStudioRevision } from "./studio-actions";

test("save and approve use the returned new revision, never the original ID", async () => {
  const reviewed: string[] = [];
  const id = await saveStudioRevision(
    {
      updateSourceRevisionContent: async () =>
        ({
          id: "new",
          status: "review_required",
        }) as KnowledgeSourceRevisionResponse,
      reviewSourceRevision: async (_c, _s, revision) => {
        reviewed.push(revision);
        return {
          id: revision,
          status: "ready",
        } as KnowledgeSourceRevisionResponse;
      },
    },
    "col",
    "source",
    { id: "old", status: "ready" },
    "edited",
    true,
  );
  assert.equal(id, "new");
  assert.deepEqual(reviewed, ["new"]);
});
test("save-only never approves a quality warning", async () => {
  let count = 0;
  await saveStudioRevision(
    {
      updateSourceRevisionContent: async () =>
        ({
          id: "new",
          status: "review_required",
        }) as KnowledgeSourceRevisionResponse,
      reviewSourceRevision: async () => {
        count++;
        throw new Error("unexpected");
      },
    },
    "col",
    "source",
    { id: "old", status: "ready" },
    "edited",
    false,
  );
  assert.equal(count, 0);
});
test("failed quality result cannot be approved", async () => {
  await assert.rejects(
    saveStudioRevision(
      {
        updateSourceRevisionContent: async () =>
          ({ id: "new", status: "failed" }) as KnowledgeSourceRevisionResponse,
        reviewSourceRevision: async () => {
          throw new Error("unexpected");
        },
      },
      "col",
      "source",
      { id: "old" },
      "edited",
      true,
    ),
    /Chỉ duyệt/,
  );
});
