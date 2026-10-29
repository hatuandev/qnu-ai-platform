// @vitest-environment jsdom
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, cleanup, renderHook } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, expect, test, vi } from "vitest";
import { useTestConnection } from "@/features/modelops/connections/api";

const state = vi.hoisted(() => ({ post: vi.fn() }));
vi.mock("@/app/api/v1", () => ({ v1Client: { post: state.post } }));
vi.mock("@/app/auth/v1", () => ({ useV1Auth: () => ({ sessionId: 99 }) }));
afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

function hook() {
  const cache = new QueryClient({
    defaultOptions: { mutations: { retry: false } },
  });
  const invalidate = vi.spyOn(cache, "invalidateQueries");
  const wrapper = ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={cache}>{children}</QueryClientProvider>
  );
  return {
    ...renderHook(() => useTestConnection("conn-review"), { wrapper }),
    invalidate,
  };
}

test("saved-key request preserves identity and allows configured server timeout", async () => {
  state.post.mockResolvedValue({ ok: true });
  const { result, invalidate } = hook();
  await act(() => result.current.mutateAsync({ key_id: "second-key" }));
  expect(state.post).toHaveBeenCalledWith(
    "/modelops/connections/conn-review/test",
    { key_id: "second-key" },
    { timeoutMs: 310_000 },
  );
  expect(invalidate).toHaveBeenCalledWith({ queryKey: ["v1", 99, "modelops"] });
});

test("failed saved-key request refreshes keys removed in another session", async () => {
  state.post.mockRejectedValue(new Error("Key no longer exists"));
  const { result, invalidate } = hook();
  await act(async () => {
    await expect(
      result.current.mutateAsync({ key_id: "removed-key" }),
    ).rejects.toThrow("Key no longer exists");
  });
  expect(state.post).toHaveBeenCalledTimes(1);
  expect(invalidate).toHaveBeenCalled();
});

test("temporary key test does not invalidate saved-key verification history", async () => {
  state.post.mockResolvedValue({ ok: true });
  const { result, invalidate } = hook();
  await act(() =>
    result.current.mutateAsync({ api_key: "synthetic-temporary" }),
  );
  expect(invalidate).not.toHaveBeenCalled();
});
