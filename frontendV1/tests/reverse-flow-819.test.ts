import { QueryClient } from "@tanstack/react-query";
import { expect, test, vi } from "vitest";
import { matchesPublishedIndex } from "@/features/knowledge/index-readiness";
import type {
  IndexReadiness,
  IndexRun,
} from "@/features/knowledge/index-types";
import { useCommitDecisionMutation } from "@/features/knowledge/publication-queries";
import type { PublishedResponse } from "@/features/knowledge/publication-types";

const ports = vi.hoisted(() => ({ client: null as QueryClient | null }));
vi.mock("@/app/auth/v1", () => ({ useV1Auth: () => ({ sessionId: 7 }) }));
vi.mock("@tanstack/react-query", async (original) => ({
  ...(await original<typeof import("@tanstack/react-query")>()),
  useQueryClient: () => ports.client,
  useMutation: (options: unknown) => options,
}));
const active = {
  id: "idx",
  status: "completed",
  is_active: true,
  requested_at: "2026-11-02T10:00:00Z",
} as IndexRun;
const published = {
  version: { id: "v2", state_version: 3, bundle_sha256: "hash" },
  decision: { id: "dec2", created_at: "2026-11-02T10:01:00Z" },
} as PublishedResponse;
const binding: IndexReadiness = {
  status: "ready",
  index_run_id: "idx",
  generation: 2,
  version_id: "v2",
  version_state: 3,
  bundle_sha256: "hash",
  publication_decision_id: "dec2",
};

test("replacement prepared before publication is ready by its exact binding", () => {
  expect(matchesPublishedIndex(binding, published, active)).toBe(true);
});
test.each([
  { index_run_id: "previous" },
  { version_id: "v1" },
  { version_state: 1 },
  { bundle_sha256: "other" },
  { publication_decision_id: "old" },
  { status: "outdated" as const },
])(
  "mismatched or unavailable binding cannot announce readiness: %j",
  (change) => {
    expect(
      matchesPublishedIndex({ ...binding, ...change }, published, active),
    ).toBe(false);
  },
);
test("missing read or inactive generation remains unconfirmed", () => {
  expect(matchesPublishedIndex(undefined, published, active)).toBe(false);
  expect(
    matchesPublishedIndex(binding, published, { ...active, is_active: false }),
  ).toBe(false);
});
test("decision commit invalidates chat history/turn and readiness only in current session/workspace", () => {
  const client = new QueryClient();
  ports.client = client;
  const history = [
    "v1",
    7,
    "workspaces",
    "ws",
    "conversations",
    "detail",
    "cnv",
    "history",
  ];
  const turn = [
    "v1",
    7,
    "workspaces",
    "ws",
    "conversations",
    "detail",
    "cnv",
    "turns",
    "item",
    "turn",
  ];
  const otherWorkspace = ["v1", 7, "workspaces", "other", "conversations"];
  const otherSession = ["v1", 8, "workspaces", "ws", "conversations"];
  const readiness = ["v1", 7, "indexing", "ws", "col", "readiness"];
  for (const key of [history, turn, otherWorkspace, otherSession, readiness])
    client.setQueryData(key, {});
  const mutation = useCommitDecisionMutation(
    "ws",
    "col",
    "doc",
    "v2",
  ) as unknown as { onSuccess: () => void };
  try {
    mutation.onSuccess();
    for (const key of [history, turn, readiness])
      expect(client.getQueryState(key)?.isInvalidated).toBe(true);
    for (const key of [otherWorkspace, otherSession])
      expect(client.getQueryState(key)?.isInvalidated).toBe(false);
  } finally {
    client.clear();
  }
});
