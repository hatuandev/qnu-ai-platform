// @vitest-environment jsdom
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, cleanup, renderHook } from "@testing-library/react";
import type { PropsWithChildren } from "react";
import { afterEach, expect, test, vi } from "vitest";
import {
  ocrQueryKeys,
  useSaveTextReviewMutation,
} from "@/features/knowledge/ocr-queries";
import type { ReviewDocument } from "@/features/knowledge/ocr-types";

const ports = vi.hoisted(() => ({ save: vi.fn() }));
vi.mock("@/app/auth/v1", () => ({ useV1Auth: () => ({ sessionId: 1 }) }));
vi.mock("@/features/knowledge/ocr-requests", async (original) => ({
  ...(await original<typeof import("@/features/knowledge/ocr-requests")>()),
  saveTextReview: ports.save,
}));
afterEach(cleanup);

test("save seeds the returned snapshot before selecting it and preserves history/other scopes", async () => {
  const client = new QueryClient({
    defaultOptions: { mutations: { retry: false } },
  });
  const key = (version: number | null, source = "src", session = 1) =>
    ocrQueryKeys.review(session, "ws", "col", source, "rev", "run", version);
  const previous: ReviewDocument = {
    run_id: "run",
    version: 1,
    version_id: "v1",
    canonical_sha256: "a".repeat(64),
    original_sha256: "a".repeat(64),
    markdown_sha256: "b".repeat(64),
    saved_at: null,
    units: [],
  };
  const saved = {
    ...previous,
    version: 2,
    version_id: "v2",
    canonical_sha256: "c".repeat(64),
  };
  for (const k of [key(1), key(null), key(null, "other"), key(null, "src", 2)])
    client.setQueryData(k, previous);
  ports.save.mockResolvedValue(saved);
  const wrapper = ({ children }: PropsWithChildren) => (
    <QueryClientProvider client={client}>{children}</QueryClientProvider>
  );
  const hook = renderHook(
    () => useSaveTextReviewMutation("ws", "col", "src", "rev", "run"),
    { wrapper },
  );
  await act(() =>
    hook.result.current.mutateAsync({
      body: {
        expected_version: 1,
        expected_sha256: previous.canonical_sha256,
        changes: [],
      },
      idempotencyKey: "intent",
    }),
  );
  expect(client.getQueryData(key(2))).toEqual(saved);
  expect(client.getQueryData(key(null))).toEqual(saved);
  expect(client.getQueryData(key(1))).toEqual(previous);
  expect(client.getQueryData(key(null, "other"))).toEqual(previous);
  expect(client.getQueryData(key(null, "src", 2))).toEqual(previous);
  client.clear();
});
