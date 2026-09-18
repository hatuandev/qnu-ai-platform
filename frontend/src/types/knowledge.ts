/** Types for Knowledge Collections, Documents, Chunks and Ingestion */

export interface KnowledgeCollection {
  id: string;
  name: string;
  code: string;
  description: string;
  document_count: number;
  chunk_count: number;
  chunking_strategy: "ClauseBasedChunker" | "SemanticChunker";
  ocr_profile: "PyMuPDF" | "Docling" | "EasyOCR";
  embedding_model?: string;
  status?: "ready" | "indexing" | "maintenance";
  updated_at: string;
}

export interface KnowledgeDocument {
  id: string;
  collection_id: string;
  collection_name: string;
  title: string;
  filename: string;
  file_size: number;
  page_count: number;
  chunk_count: number;
  status: "completed" | "processing" | "pending" | "failed" | "approved" | "archived";
  ocr_method: string;
  document_type?: string;
  document_type_code?: string;
  priority_level?: "core" | "high" | "normal";
  version?: string;
  created_at: string;
}

export interface IngestionTask {
  id: string;
  task_name: string;
  collection_id: string;
  collection_code: string;
  source_file: string;
  file_size_mb: number;
  worker_name: string;
  duration_seconds: number;
  category: "ingestion" | "ocr" | "reindex";
  progress_percent: number;
  status: "completed" | "processing" | "failed" | "cancelled";
  created_at: string;
  log_output?: string;
}

export interface DocumentBoundingBox {
  id: string;
  page_number: number;
  type: "text" | "table" | "stamp" | "header" | "title" | "signature" | "list";
  coordinates: { x: number; y: number; width: number; height: number }; // percentages 0-100
  label: string;
  confidence: number;
  content_snippet: string;
}

export interface DocumentRegion {
  id: string;
  page_number: number;
  title: string;
  type: "text" | "table" | "stamp" | "header" | "footer" | "title" | "signature" | "list";
  confidence: number;
  reading_order: number;
  details: string;
}

export interface ParsePreviewResult {
  file_name: string;
  file_type: string;
  file_size_bytes: number;
  raw_markdown: string;
  chunk_count: number;
  estimated_tokens: number;
  extracted_tables_count: number;
  ocr_method: string;
  preview_chunks: {
    index: number;
    token_count: number;
    section: string | null;
    preview: string;
  }[];
}

export interface DocumentChunkItem {
  id: string;
  document_id: string;
  chunk_index: number;
  content: string;
  token_count: number;
  section: string | null;
  page_number: number | null;
  metadata: Record<string, unknown>;
}

export interface KnowledgeDocumentDetail extends KnowledgeDocument {
  chunks: DocumentChunkItem[];
  doc_metadata: Record<string, unknown>;
}

export interface ApproveDocumentResult {
  document_id: string;
  status: string;
  total_chunks: number;
  indexed_chunks: number;
}

export interface DocumentVerificationData {
  document_id: string;
  collection_id: string;
  title: string;
  filename: string;
  file_size_mb: number;
  total_pages: number;
  engine: string;
  total_chars: number;
  estimated_chunks: number;
  pages: {
    page_number: number;
    word_count: number;
    line_count: number;
    image_url?: string;
    markdown_content: string;
    raw_text: string;
    bounding_boxes: DocumentBoundingBox[];
    regions: DocumentRegion[];
  }[];
}

export interface FactItem {
  id: string;
  collection_id: string;
  document_id: string;
  entity_name: string;
  entity_type: string;
  attribute_name: string;
  attribute_value: string;
  confidence: number;
  raw_data: Record<string, unknown>;
  created_at: string;
}

export interface FactListResponse {
  collection_id: string;
  total: number;
  facts: FactItem[];
}

export interface FactExcelImportResponse {
  collection_id: string;
  imported_count: number;
  document_id: string;
  message: string;
}
