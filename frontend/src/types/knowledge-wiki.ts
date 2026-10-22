export interface KnowledgeWikiReference {
  unit_id: string;
  page_number: number | null;
  quote: string;
}

export interface KnowledgeWikiPage {
  id: string;
  kind: "source" | "entity" | "concept";
  title: string;
  markdown: string;
  references: KnowledgeWikiReference[];
}

export interface KnowledgeWikiResponse {
  collection_id: string;
  binding_id: string;
  status: "ready" | "pending" | "not_requested" | "unavailable";
  source_revision_id: string;
  index_revision_id: string | null;
  failure_code: string | null;
  pages: KnowledgeWikiPage[];
}
