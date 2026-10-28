// @vitest-environment jsdom
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, cleanup, renderHook } from "@testing-library/react";
import type { PropsWithChildren } from "react";
import { afterEach, expect, test, vi } from "vitest";
import {
  useCreateAppApiKeyMutation,
  useRotateAppApiKeyMutation,
} from "@/features/modelops/queries";

const { post } = vi.hoisted(() => ({ post: vi.fn() }));
vi.mock("@/app/api/v1", () => ({ v1Client: { post } }));
vi.mock("@/app/auth/v1", () => ({ useV1Auth: () => ({ sessionId: 42 }) }));
afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

test("create and rotate hand secret only to modal callback, not mutation cache", async () => {
  const secret = "qnu_live_syntheticOnlyInModal";
  post.mockResolvedValue({ id: "key_review", secret_key: secret });
  const cache = new QueryClient();
  const onSecret = vi.fn();
  const wrapper = ({ children }: PropsWithChildren) => (
    <QueryClientProvider client={cache}>{children}</QueryClientProvider>
  );
  const { result, unmount } = renderHook(
    () => ({
      create: useCreateAppApiKeyMutation("ws_review", onSecret),
      rotate: useRotateAppApiKeyMutation("ws_review", onSecret),
    }),
    { wrapper },
  );
  await act(async () => {
    await result.current.create.mutateAsync({
      name: "Review key",
      app_name: "Review app",
      allow_all_assistants: true,
    });
    await result.current.rotate.mutateAsync({ keyId: "key_review", input: {} });
  });
  expect(onSecret).toHaveBeenCalledTimes(2);
  expect(onSecret).toHaveBeenCalledWith({
    id: "key_review",
    secret_key: secret,
  });
  expect(result.current.create.data).toBeUndefined();
  expect(result.current.rotate.data).toBeUndefined();
  const states = cache
    .getMutationCache()
    .getAll()
    .map((mutation) => mutation.state);
  expect(JSON.stringify(states)).not.toContain(secret);
  unmount();
  cache.clear();
});
