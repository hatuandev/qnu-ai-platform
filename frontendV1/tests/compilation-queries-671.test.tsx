// @vitest-environment jsdom
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, cleanup, renderHook, waitFor } from "@testing-library/react";
import type { PropsWithChildren } from "react";
import { afterEach, expect, test, vi } from "vitest";
import {
  compilationKeys,
  useAutoReviewQuery,
  useCreateCompilationMutation,
  useCreateReviewMutation,
} from "../src/features/knowledge/compilation-queries";

const ports = vi.hoisted(() => ({
  create: vi.fn(),
  review: vi.fn(),
  auto: vi.fn(),
}));
vi.mock("@/app/auth/v1", () => ({ useV1Auth: () => ({ sessionId: 1 }) }));
vi.mock(
  "@/features/knowledge/compilation-requests",
  async (importOriginal) => ({
    ...(await importOriginal<
      typeof import("../src/features/knowledge/compilation-requests")
    >()),
    createCompilationRun: ports.create,
    createCompilationReview: ports.review,
    getAutoReviewStatus: ports.auto,
  }),
);
function setup() {
  const client = new QueryClient({
    defaultOptions: {
      queries: { retry: false, staleTime: Infinity },
      mutations: { retry: false },
    },
  });
  const wrapper = ({ children }: PropsWithChildren) => (
    <QueryClientProvider client={client}>{children}</QueryClientProvider>
  );
  return { client, wrapper };
}
afterEach(() => {
  cleanup();
  vi.useRealTimers();
});

test("F5: creating a compilation invalidates all page sizes in the same scope only", async () => {
  const { client, wrapper } = setup();
  const keys = [20, 50].map((limit) =>
    compilationKeys.runs("w", "c", limit, 1),
  );
  keys.forEach((key) => {
    client.setQueryData(key, []);
  });
  const other = compilationKeys.runs("w", "other", 20, 1);
  client.setQueryData(other, []);
  const otherSession = compilationKeys.runs("w", "c", 20, 2);
  client.setQueryData(otherSession, []);
  ports.create.mockResolvedValue({ run: { id: "new" } });
  const hook = renderHook(() => useCreateCompilationMutation("w", "c"), {
    wrapper,
  });
  await act(() =>
    hook.result.current.mutateAsync({
      input: { topic: "topic", ocr_run_ids: ["ocr"] },
      idempotencyKey: "same-intent-key",
    }),
  );
  keys.forEach((key) => {
    expect(client.getQueryState(key)?.isInvalidated).toBe(true);
  });
  expect(client.getQueryState(other)?.isInvalidated).toBe(false);
  expect(client.getQueryState(otherSession)?.isInvalidated).toBe(false);
  client.clear();
});

test("F6: polling an absent auto-review stops after the bounded scheduling window", async () => {
  const { client, wrapper } = setup();
  ports.auto.mockResolvedValue({
    notScheduled: true,
    status: "none",
    review_id: null,
  });
  const hook = renderHook(() => useAutoReviewQuery("w", "c", "run"), {
    wrapper,
  });
  await waitFor(() =>
    expect(hook.result.current.data?.notScheduled).toBe(true),
  );
  vi.useFakeTimers();
  // Refetch starts the polling interval under fake time.
  await act(() => hook.result.current.refetch());
  for (let i = 0; i < 12; i += 1)
    await act(() => vi.advanceTimersByTimeAsync(3000));
  expect(ports.auto.mock.calls.length).toBeLessThanOrEqual(10);
  hook.unmount();
  client.clear();
});

test("F5: creating a review invalidates every pagination of that run", async () => {
  const { client, wrapper } = setup();
  const key = compilationKeys.reviews("w", "c", "run", 50, 0, 1);
  client.setQueryData(key, []);
  ports.review.mockResolvedValue({ id: "r" });
  const hook = renderHook(() => useCreateReviewMutation("w", "c", "run"), {
    wrapper,
  });
  await act(() =>
    hook.result.current.mutateAsync({
      input: {},
      idempotencyKey: "review-intent-key",
    }),
  );
  expect(client.getQueryState(key)?.isInvalidated).toBe(true);
  client.clear();
});

test("F6: notScheduled is retained and a late automatic review refreshes the list", async () => {
  const { client, wrapper } = setup();
  const key = compilationKeys.reviews("w", "c", "run", 50, 0, 1);
  client.setQueryData(key, []);
  ports.auto
    .mockResolvedValueOnce({
      notScheduled: true,
      status: "none",
      review_id: null,
    })
    .mockResolvedValue({ status: "completed", review_id: "r" });
  const hook = renderHook(() => useAutoReviewQuery("w", "c", "run"), {
    wrapper,
  });
  await waitFor(() =>
    expect(hook.result.current.data?.notScheduled).toBe(true),
  );
  await act(() => hook.result.current.refetch());
  await waitFor(() =>
    expect(client.getQueryState(key)?.isInvalidated).toBe(true),
  );
  client.clear();
});
