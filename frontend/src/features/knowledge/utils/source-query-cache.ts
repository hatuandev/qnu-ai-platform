import type { QueryClient } from "@tanstack/react-query";

export async function refreshSourceQueries(
  client: QueryClient,
  collectionId: string,
  sourceId: string,
) {
  const queryKeys = [
    ["knowledge-source", collectionId, sourceId],
    ["knowledge-source-chunk-sets", collectionId, sourceId],
    ["knowledge-binding", sourceId],
    ["source-context-studio", collectionId, sourceId],
    ["knowledge-bindings", collectionId],
    ["knowledge-collection", collectionId],
    ["collection-summary-metrics", collectionId],
    ["knowledge-vector-load", collectionId],
    ["collection-facts", collectionId],
    ["binding-index-revisions", sourceId],
    ["ingestion-tasks", collectionId],
  ];
  await Promise.all(
    queryKeys.map((queryKey) =>
      client.invalidateQueries({ queryKey, refetchType: "all" }),
    ),
  );
}
