/** Types for Central Document Repository (Kho Tài Liệu Tập Trung) */

export interface AttachedCollectionInfo {
  collection_id: string;
  collection_name: string;
  document_id: string;
  index_status: string;
  created_at: string;
}

export interface RepositoryDocumentListItem {
  id: string;
  title: string;
  file_name: string;
  file_type: string;
  file_size_bytes: number;
  file_hash: string;
  document_type_code?: string | null;
  document_type_name?: string | null;
  document_number?: string | null;
  issuing_authority?: string | null;
  issued_date?: string | null;
  effective_date?: string | null;
  signer?: string | null;
  parse_status: "pending" | "parsing" | "parsed" | "failed";
  ocr_engine?: string | null;
  attached_collections_count: number;
  created_at: string;
  updated_at: string;
}

export interface RepositoryDocument extends RepositoryDocumentListItem {
  storage_path: string;
  parsed_markdown?: string | null;
  doc_metadata: {
    page_count?: number;
    table_count?: number;
    preview_pages?: string[];
    sections_count?: number;
    parse_error?: string | null;
    [key: string]: unknown;
  };
  is_active: boolean;
  attached_collections: AttachedCollectionInfo[];
}

export interface DocumentStats {
  total_documents: number;
  parsed_documents: number;
  pending_documents: number;
  failed_documents: number;
  total_size_bytes: number;
  document_types_count: number;
  attached_usages_count: number;
}

export interface RepositoryDocumentFilter {
  search?: string;
  document_type_code?: string;
  file_type?: string;
  parse_status?: string;
  skip?: number;
  limit?: number;
}

export interface RepositoryDocumentUpdate {
  title?: string;
  document_type_code?: string;
  document_number?: string;
  issuing_authority?: string;
  issued_date?: string;
  effective_date?: string;
  doc_metadata?: Record<string, unknown>;
}

export interface AttachDocumentsRequest {
  document_ids: string[];
  chunk_strategy?: string;
  auto_approve?: boolean;
}
