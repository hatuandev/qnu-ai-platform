import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { v1Client } from "../v1-client";

export type SpellingDefaults = {
  ocr: boolean;
  pdf_text: boolean;
  word_text: boolean;
  total_passes: number;
};

const path = "/settings/spelling";
const key = ["spelling-defaults"] as const;

export function useSpellingDefaults() {
  const client = useQueryClient();
  const query = useQuery({
    queryKey: key,
    queryFn: ({ signal }) => v1Client.get<SpellingDefaults>(path, { signal }),
  });
  const update = useMutation({
    mutationFn: (policy: SpellingDefaults) =>
      v1Client.put<SpellingDefaults>(path, policy),
    onSuccess: (policy) => client.setQueryData(key, policy),
  });
  return { query, update };
}
