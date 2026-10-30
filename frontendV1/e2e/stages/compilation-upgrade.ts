import type { Api, Publication, Run } from "./session";

export type CompilationDraft = {
  sections: { paragraphs: { text: string; citations: string[] }[] }[];
  validation?: { unread_source_blocks?: string };
};

export async function needsUnreadBlockUpgrade(
  api: Pick<Api, "get">,
  collectionBase: string,
  publication: Publication,
  draft: CompilationDraft,
  history: readonly Publication[] = [],
): Promise<boolean> {
  if (draft.validation?.unread_source_blocks === "retained") return false;
  const target = publication.review
    ? publication
    : [...history].reverse().find(
        (row) =>
          publication.document &&
          row.document === publication.document &&
          row.review,
      );
  if (!target?.review) return false;
  if (!publication.review) {
    const pending = await api.get<Run[]>(
      `${collectionBase}/compilation-runs/${publication.run}/reviews?limit=1`,
    );
    if (pending.length) return false;
  }
  const base = `${collectionBase}/compilation-runs/${target.run}/reviews/${target.review}`;
  const review = await api.get<Run>(base);
  if (review.status !== "completed") return false;
  const report = await api.get<{
    findings: {
      direction: string;
      sources: { text: string; requires_review?: boolean; kind: string }[];
    }[];
  }>(`${base}/report`);
  return report.findings.some(
    (finding) =>
      finding.direction === "source_to_draft" &&
      finding.sources.some(
        (source) =>
          source.requires_review &&
          source.kind !== "table_cell" &&
          !source.text.trim(),
      ),
  );
}
