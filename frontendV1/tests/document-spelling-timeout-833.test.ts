import { expect, test, vi } from "vitest";
import { createV1Client } from "@/app/api/v1/client";
import { createDetectCheck } from "@/features/knowledge/ocr-requests";

test("spelling awaits the backend beyond the ordinary client deadline", async () => {
  vi.useFakeTimers();
  try {
    let signal: AbortSignal | null | undefined;
    let respond!: (response: Response) => void;
    const client = createV1Client({
      fetchImpl: async (_input, init) => {
        signal = init?.signal;
        return new Promise<Response>((resolve) => {
          respond = resolve;
        });
      },
    });
    const result = createDetectCheck(
      client,
      "ws",
      "col",
      "src",
      "rev",
      "run",
      {
        expected_version: 1,
        expected_sha256: "hash",
        evidence_ids: ["ev"],
        provider_id: null,
        max_output_tokens: 4096,
      },
      "test-check",
    );
    await vi.advanceTimersByTimeAsync(31_000);
    expect(signal?.aborted).toBe(false);
    respond(Response.json({ code: "chat_output_truncated" }, { status: 422 }));
    await expect(result).rejects.toMatchObject({
      code: "chat_output_truncated",
      status: 422,
    });
  } finally {
    vi.useRealTimers();
  }
});
