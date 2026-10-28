import { afterEach, expect, test, vi } from "vitest";
import { createV1Client } from "@/app/api/v1/client";

afterEach(() => vi.useRealTimers());

test("a diagnostic request can wait longer without changing the client default", async () => {
  vi.useFakeTimers();
  let aborted = false;
  const client = createV1Client({
    timeoutMs: 1000,
    fetchImpl: async (_url, options) => {
      await new Promise<void>((_resolve, reject) =>
        options?.signal?.addEventListener("abort", () => {
          aborted = true;
          reject(new DOMException("Timeout", "AbortError"));
        }),
      );
      return new Response("{}");
    },
  });
  const pending = client
    .post("/modelops/providers/p/probe", {}, { timeoutMs: 3000 })
    .catch((error) => error);
  await vi.advanceTimersByTimeAsync(1100);
  expect(aborted).toBe(false);
  await vi.advanceTimersByTimeAsync(2000);
  expect(aborted).toBe(true);
  expect(await pending).toBeInstanceOf(Error);
  aborted = false;
  const normal = client.get("/modelops/providers").catch((error) => error);
  await vi.advanceTimersByTimeAsync(1100);
  expect(aborted).toBe(true);
  await normal;
});
