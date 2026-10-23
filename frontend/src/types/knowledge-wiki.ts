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
  temporal?: KnowledgeWikiTemporal[];
}

export interface KnowledgeWikiTemporal {
  role: "data" | "publication" | "effective" | "event";
  years: number[];
}

export interface KnowledgeWikiResponse {
  collection_id: string;
  binding_id: string;
  status: "ready" | "pending" | "not_requested" | "unavailable";
  source_revision_id: string;
  index_revision_id: string | null;
  failure_code: string | null;
  pages: KnowledgeWikiPage[];
  source_revision_no?: number;
  canonical_hash?: string;
}

export interface KnowledgeWikiNode {
  id: string;
  kind: "source" | "entity" | "concept";
  title: string;
  binding_id: string;
  source_revision_id: string;
  source_revision_no: number;
  source_title: string;
  temporal: KnowledgeWikiTemporal[];
}

export interface KnowledgeWikiLink {
  id: string;
  source: string;
  target: string;
  relation: string;
  status: "structural" | "candidate";
}

export interface KnowledgeWikiIssue {
  id: string;
  category:
    | "blocker"
    | "warning"
    | "source_limitation"
    | "candidate"
    | "provider_infrastructure"
    | "stale";
  code: string;
  message: string;
}

export interface KnowledgeWikiMap {
  collection_id: string;
  pages: KnowledgeWikiNode[];
  graph: {
    version: string;
    snapshot: string;
    sha256: string;
    links: KnowledgeWikiLink[];
    outgoing: Record<string, string[]>;
    backlinks: Record<string, string[]>;
  };
  issues: KnowledgeWikiIssue[];
}

export interface KnowledgeWikiReview {
  collection_id: string;
  binding_id: string;
  source_revision_id: string;
  issues: KnowledgeWikiIssue[];
}
