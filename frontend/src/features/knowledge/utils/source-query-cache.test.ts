import assert from "node:assert/strict";
import { test } from "node:test";
import { QueryClient } from "@tanstack/react-query";
import { refreshSourceQueries } from "./source-query-cache";

test("review refreshes inactive list and summary before returning to collection", async () => {
  const client = new QueryClient({
    defaultOptions: { queries: { staleTime: 30_000, retry: false } },
  });
  try {
    let requiresReview = true;
    const keys = [
      ["knowledge-source", "collection", "source"],
      ["knowledge-bindings", "collection"],
      ["collection-summary-metrics", "collection"],
      ["knowledge-vector-load", "collection"],
      ["collection-facts", "collection"],
      ["binding-index-revisions", "source"],
      ["ingestion-tasks", "collection"],
    ];
    for (const queryKey of keys) {
      await client.fetchQuery({
        queryKey,
        queryFn: async () => ({ requiresReview }),
      });
    }
    client.setQueryData(["knowledge-bindings", "other-collection"], {
      requiresReview: true,
    });
    requiresReview = false;

    await refreshSourceQueries(client, "collection", "source");

    for (const queryKey of keys) {
      assert.deepEqual(client.getQueryData(queryKey), {
        requiresReview: false,
      });
    }
    assert.deepEqual(
      client.getQueryData(["knowledge-bindings", "other-collection"]),
      { requiresReview: true },
    );
  } finally {
    client.clear();
  }
});
