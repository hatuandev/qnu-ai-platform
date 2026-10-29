// @vitest-environment jsdom
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, expect, test, vi } from "vitest";
import { clearAccessToken, setAccessToken } from "@/app/api/v1";
import { useProcessingRunsQuery } from "@/features/knowledge/ocr-queries";

vi.mock("@/app/auth/v1", () => ({ useV1Auth: () => ({ sessionId: 708 }) }));
afterEach(() => {
  cleanup();
  clearAccessToken();
  vi.unstubAllGlobals();
});

test("OCR history refreshes a queued item to its terminal status", async () => {
  setAccessToken("synthetic-708");
  let calls = 0;
  const fetch = vi.fn(async () => {
    calls++;
    return new Response(
      JSON.stringify({
        items: [{ id: "ocr", status: calls === 1 ? "queued" : "failed" }],
        meta: { page: 1, page_size: 10, total: 1 },
      }),
      { status: 200, headers: { "content-type": "application/json" } },
    );
  });
  vi.stubGlobal("fetch", fetch);
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  const hook = renderHook(
    () => useProcessingRunsQuery("w", "c", "s", "r", 1, 10),
    {
      wrapper: ({ children }: { children: ReactNode }) => (
        <QueryClientProvider client={client}>{children}</QueryClientProvider>
      ),
    },
  );
  try {
    await waitFor(() =>
      expect(hook.result.current.data?.items[0].status).toBe("queued"),
    );
    await waitFor(
      () => expect(hook.result.current.data?.items[0].status).toBe("failed"),
      { timeout: 4000 },
    );
    expect(calls).toBe(2);
  } finally {
    hook.unmount();
    client.clear();
  }
});
