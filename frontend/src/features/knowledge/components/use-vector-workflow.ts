import { useQuery } from "@tanstack/react-query";
import { knowledgeApi } from "@/services/knowledge-api";

export function useVectorWorkflow(collectionId: string) {
  const sources = useQuery({
    queryKey: ["knowledge-bindings", collectionId],
    queryFn: () => knowledgeApi.getAllBindings(collectionId),
    refetchInterval: 5000,
  });
  const generations = useQuery({
    queryKey: ["knowledge-vector-generations", collectionId],
    queryFn: () => knowledgeApi.listVectorGenerations(collectionId),
    refetchInterval: 5000,
  });
  const state = useQuery({
    queryKey: ["knowledge-vector-load", collectionId],
    queryFn: () => knowledgeApi.getVectorLoadState(collectionId),
    refetchInterval: (query) =>
      query.state.data?.jobs.some((job) =>
        ["queued", "running"].includes(job.status),
      )
        ? 1500
        : 5000,
  });
  return { sources, generations, state };
}
