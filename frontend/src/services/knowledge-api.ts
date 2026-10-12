import type {
  ActivateVectorGenerationResponse,
  ApproveDocumentResult,
  AttachDocumentGroupRequest,
  AttachDocumentGroupResponse,
  AttachGroupSourceRequest,
  AvailableRepositoryDocumentsResponse,
  BackfillReport,
  BackfillRequest,
  BindingChunksResponse,
  BuildStagingIndexRequest,
  BuildVectorGenerationRequest,
  BuildVectorGenerationResponse,
  CanaryPolicyResponse,
  CandidateGroupListResponse,
  CandidateListResponse,
  CollectionDataProcessingConfig,
  CollectionSummaryMetrics,
  CreateKnowledgeBindingsRequest,
  CreateKnowledgeBindingsResponse,
  CreateVectorGenerationRequest,
  DetachGroupSourceResponse,
  DocumentVerificationData,
  FactExcelImportResponse,
  FactListResponse,
  GarbageCollectionReport,
  GarbageCollectionRequest,
  IndexActivationRequest,
  IndexActivationResponse,
  KnowledgeBinding,
  KnowledgeChunkSetResponse,
  KnowledgeCollection,
  KnowledgeDocument,
  KnowledgeDocumentDetail,
  KnowledgeGroupSource,
  KnowledgeImportBatchCreateRequest,
  KnowledgeImportBatchResponse,
  KnowledgeIndexRevision,
  KnowledgeReconciliationReport,
  KnowledgeSourceDetailResponse,
  KnowledgeSourceRevisionResponse,
  KnowledgeVectorGenerationResponse,
  LegacyAuditReport,
  ParsePreviewResult,
  PreviewDocumentGroupResponse,
  PreviewGroupSourceDiffResponse,
  PublishGroupSourceResponse,
  ReconcileFixResponse,
  ReindexDocumentResponse,
  RollbackIndexRevisionRequest,
  ShadowRetrievalReport,
  ShadowRetrievalRequest,
  SyncGroupSourceRequest,
  SyncGroupSourceResponse,
  SystemDecommissioningAuditReport,
  SystemGarbageCollectionReport,
  SystemGarbageCollectionRequest,
  UpdateCanaryPolicyRequest,
  VectorLoadItem,
  VectorLoadJob,
  VectorLoadState,
} from "@/types/knowledge";
import { BASE_URL, getAuthHeaders } from "./http-client";

/**
 * Chuẩn hóa đọc lỗi RFC 7807 (ưu tiên detail -> message -> title -> fallback)
 */
export function extractErrorMessage(err: unknown, fallback: string): string {
  if (typeof err === "string" && err.trim()) return err;
  if (err && typeof err === "object") {
    const e = err as Record<string, unknown>;
    if (typeof e.detail === "string" && e.detail.trim()) return e.detail;
    if (typeof e.message === "string" && e.message.trim()) return e.message;
    if (typeof e.title === "string" && e.title.trim()) return e.title;
  }
  return fallback;
}

export interface KnowledgePurgeJob {
  id: string;
  status: "queued" | "running" | "completed" | "failed" | "cancelled";
  error: string | null;
}

export const knowledgeApi = {
  async getAllBindings(collectionId: string): Promise<KnowledgeBinding[]> {
    const items: KnowledgeBinding[] = [];
    let page = 1;
    while (true) {
      const batch = await knowledgeApi.getBindings(
        collectionId,
        undefined,
        page,
        100,
      );
      items.push(...batch);
      if (batch.length < 100) return items;
      page += 1;
    }
  },

  async getVectorLoadState(collectionId: string): Promise<VectorLoadState> {
    const res = await fetch(
      `${BASE_URL}/knowledge/collections/${collectionId}/vector-load`,
      { headers: getAuthHeaders() },
    );
    if (!res.ok) throw new Error("Không tải được trạng thái nạp vector.");
    return res.json();
  },

  async loadSourceVectors(
    collectionId: string,
    generationId: string,
    items: VectorLoadItem[],
  ): Promise<VectorLoadJob[]> {
    const res = await fetch(
      `${BASE_URL}/knowledge/collections/${collectionId}/vector-load`,
      {
        method: "POST",
        headers: getAuthHeaders({ "Content-Type": "application/json" }),
        body: JSON.stringify({ generation_id: generationId, items }),
      },
    );
    if (!res.ok)
      throw new Error(
        extractErrorMessage(
          await res.json().catch(() => ({})),
          "Không xếp hàng nạp vector được.",
        ),
      );
    return res.json();
  },
  async purgeSource(bindingId: string): Promise<KnowledgePurgeJob> {
    const res = await fetch(
      `${BASE_URL}/knowledge/bindings/${bindingId}/purge`,
      {
        method: "DELETE",
        headers: getAuthHeaders(),
      },
    );
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(
        err.detail || `Không xóa được nguồn (HTTP ${res.status}).`,
      );
    }
    return res.json();
  },

  async getSourcePurgeJob(
    bindingId: string,
    jobId: string,
  ): Promise<KnowledgePurgeJob> {
    const res = await fetch(
      `${BASE_URL}/knowledge/bindings/${bindingId}/purge/jobs/${jobId}`,
      {
        headers: getAuthHeaders(),
      },
    );
    if (!res.ok)
      throw new Error(`Không đọc được tiến trình xóa (HTTP ${res.status}).`);
    return res.json();
  },
  async getCollections(): Promise<KnowledgeCollection[]> {
    const res = await fetch(`${BASE_URL}/knowledge/collections`);
    if (!res.ok) {
      throw new Error(
        `Không tải được danh sách kho tri thức (HTTP ${res.status}).`,
      );
    }
    const data = await res.json();
    if (!Array.isArray(data)) {
      return [];
    }
    return data.map((item, idx) => {
      const d = item as Record<string, unknown>;
      const code =
        (d.code as string) || (d.module_code as string) || `col_${idx + 1}`;
      return {
        id: (d.id as string) || `col_${idx + 1}`,
        name: (d.name as string) || "Kho Tri Thức",
        code,
        description: (d.description as string) || "",
        document_count:
          typeof d.document_count === "number" ? d.document_count : 0,
        chunk_count: typeof d.chunk_count === "number" ? d.chunk_count : 0,
        chunking_strategy:
          (d.chunking_strategy as KnowledgeCollection["chunking_strategy"]) ||
          (code.includes("regulation") || code.includes("draft")
            ? "ClauseBasedChunker"
            : "SemanticChunker"),
        ocr_profile:
          (d.ocr_profile as KnowledgeCollection["ocr_profile"]) ||
          (code.includes("regulation") || code.includes("library")
            ? "PyMuPDF"
            : "Mistral"),
        data_processing: ((d.collection_metadata as Record<string, unknown>)
          ?.data_processing ||
          (d.metadata as Record<string, unknown>)?.data_processing ||
          d.data_processing) as KnowledgeCollection["data_processing"],
        embedding_model:
          ((
            ((d.collection_metadata as Record<string, unknown>)
              ?.data_processing ||
              (d.metadata as Record<string, unknown>)?.data_processing ||
              d.data_processing) as Record<string, unknown>
          )?.embedding_model as string) ||
          (d.embedding_model as string) ||
          "bge-m3:latest",
        updated_at:
          typeof d.updated_at === "string"
            ? d.updated_at
            : new Date().toISOString(),
      };
    });
  },

  async getCollection(collectionId: string): Promise<KnowledgeCollection> {
    const res = await fetch(
      `${BASE_URL}/knowledge/collections/${collectionId}`,
    );
    if (res.ok) {
      const item = await res.json();
      const meta = item.metadata || item.collection_metadata || {};
      const dp = (meta.data_processing || item.data_processing) as
        | Record<string, unknown>
        | undefined;
      return {
        ...item,
        data_processing: dp as KnowledgeCollection["data_processing"],
        embedding_model:
          (dp?.embedding_model as string) ||
          item.embedding_model ||
          "bge-m3:latest",
      };
    }
    const all = await this.getCollections();
    const found = all.find(
      (c) => c.id === collectionId || c.code === collectionId,
    );
    if (found) return found;
    throw new Error(
      `Không tìm thấy kho tri thức '${collectionId}' (HTTP ${res.status}).`,
    );
  },

  async createCollection(payload: {
    name: string;
    code?: string;
    description?: string;
    ocr_profile?: string;
    chunking_strategy?: string;
    data_processing?: CollectionDataProcessingConfig;
  }): Promise<KnowledgeCollection> {
    const moduleCode =
      payload.code?.trim() ||
      payload.name
        .toLowerCase()
        .replace(/[^a-z0-9_]/g, "_")
        .slice(0, 32) ||
      "admissions";
    const bodyPayload = {
      name: payload.name,
      description: payload.description,
      module_code: moduleCode,
      metadata: {
        ocr_profile: payload.ocr_profile,
        chunking_strategy: payload.chunking_strategy,
      },
      data_processing: payload.data_processing,
    };
    const res = await fetch(`${BASE_URL}/knowledge/collections`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...getAuthHeaders() },
      body: JSON.stringify(bodyPayload),
    });
    if (!res.ok) {
      const errData = await res.json().catch(() => null);
      const detail = errData?.detail || errData?.message;
      throw new Error(
        detail
          ? `Tạo kho tri thức thất bại: ${typeof detail === "string" ? detail : JSON.stringify(detail)}`
          : `Tạo kho tri thức thất bại (HTTP ${res.status}).`,
      );
    }
    return await res.json();
  },

  async updateCollection(
    collectionId: string,
    payload: {
      name?: string;
      description?: string;
      data_processing?: CollectionDataProcessingConfig;
    },
  ): Promise<void> {
    let res: Response;
    try {
      res = await fetch(`${BASE_URL}/knowledge/collections/${collectionId}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
    } catch {
      throw new Error(
        "Không kết nối được máy chủ Backend (kiểm tra service port 8001).",
      );
    }
    if (!res.ok) {
      throw new Error(`Cập nhật kho tri thức thất bại (HTTP ${res.status}).`);
    }
  },

  async deleteCollection(collectionId: string): Promise<void> {
    const res = await fetch(
      `${BASE_URL}/knowledge/collections/${collectionId}`,
      {
        method: "DELETE",
      },
    );
    if (!res.ok && res.status !== 204 && res.status !== 404) {
      throw new Error(`Xóa kho tri thức thất bại (HTTP ${res.status}).`);
    }
  },

  async reindexCollection(
    collectionId: string,
  ): Promise<{ job_id: string; status: string }> {
    let res: Response;
    try {
      res = await fetch(
        `${BASE_URL}/knowledge/collections/${collectionId}/reindex`,
        {
          method: "POST",
        },
      );
    } catch {
      throw new Error(
        "Không kết nối được máy chủ Backend (kiểm tra service port 8001).",
      );
    }
    if (!res.ok) {
      throw new Error(`Tạo job reindex thất bại (HTTP ${res.status}).`);
    }
    return (await res.json()) as { job_id: string; status: string };
  },

  async testCollection(
    collectionId: string,
    query: string,
    topK = 5,
  ): Promise<
    {
      chunk_id: string;
      document_id: string;
      content: string;
      score: number;
      section: string | null;
      page_number: number | null;
    }[]
  > {
    let res: Response;
    try {
      const params = new URLSearchParams({ query, top_k: String(topK) });
      res = await fetch(
        `${BASE_URL}/knowledge/collections/${collectionId}/test?${params.toString()}`,
        { method: "POST" },
      );
    } catch {
      throw new Error(
        "Không kết nối được máy chủ Backend (kiểm tra service port 8001).",
      );
    }
    if (!res.ok) {
      throw new Error(`Truy vấn thử thất bại (HTTP ${res.status}).`);
    }
    const data = (await res.json()) as {
      items: {
        chunk_id: string;
        document_id: string;
        content: string;
        score: number;
        section: string | null;
        page_number: number | null;
      }[];
    };
    return data.items || [];
  },

  async getDocuments(
    collectionId?: string,
    documentTypeCode?: string,
  ): Promise<KnowledgeDocument[]> {
    const params = new URLSearchParams();
    if (collectionId) {
      params.set("collection_id", collectionId);
    }
    if (documentTypeCode) {
      params.set("document_type_code", documentTypeCode);
    }
    const query = params.toString();
    const url = query
      ? `${BASE_URL}/knowledge/documents?${query}`
      : `${BASE_URL}/knowledge/documents`;
    const res = await fetch(url);
    if (!res.ok) {
      throw new Error(
        `Không tải được danh sách tài liệu (HTTP ${res.status}).`,
      );
    }
    const data = await res.json();
    if (!Array.isArray(data)) {
      return [];
    }
    return data.map((item, idx) => {
      const d = item as Record<string, unknown>;
      const fn =
        (d.filename as string) ||
        (d.file_name as string) ||
        `document_${idx + 1}.pdf`;
      const fs =
        typeof d.file_size === "number"
          ? d.file_size
          : typeof d.file_size_bytes === "number"
            ? d.file_size_bytes
            : 0;
      return {
        id: (d.id as string) || `doc_${idx + 1}`,
        collection_id: (d.collection_id as string) || collectionId || "",
        collection_name: (d.collection_name as string) || "Kho Tri Thức",
        title: (d.title as string) || fn,
        filename: fn,
        file_size: fs,
        page_count: typeof d.page_count === "number" ? d.page_count : 0,
        chunk_count: typeof d.chunk_count === "number" ? d.chunk_count : 0,
        status: ((d.status as string) || "completed") as
          | "completed"
          | "processing"
          | "pending"
          | "failed"
          | "approved"
          | "archived",
        index_status:
          (d.index_status as
            | "pending"
            | "indexing"
            | "indexed"
            | "index_failed") || "pending",
        index_error: (d.index_error as string | null) || null,
        ocr_method: (d.ocr_method as string) || "ModelOps OCR API",
        document_type_code: (d.document_type_code as string) || undefined,
        document_type: (d.document_type_code as string) || undefined,
        created_at:
          typeof d.created_at === "string"
            ? d.created_at
            : new Date().toISOString(),
      };
    });
  },

  async uploadDocument(
    collectionId: string,
    file: File,
    title?: string,
    ocrEngine?: string,
    documentTypeCode?: string,
    autoApprove?: boolean,
  ): Promise<KnowledgeDocument> {
    const formData = new FormData();
    formData.append("file", file);
    if (title) {
      formData.append("title", title);
    }
    if (ocrEngine) {
      formData.append("ocr_engine", ocrEngine);
    }
    if (documentTypeCode) {
      formData.append("document_type_code", documentTypeCode);
    }
    if (autoApprove) {
      formData.append("auto_approve", "true");
    }
    let res: Response;
    try {
      res = await fetch(
        `${BASE_URL}/knowledge/collections/${collectionId}/upload`,
        {
          method: "POST",
          body: formData,
        },
      );
    } catch {
      throw new Error(
        "Không kết nối được máy chủ Backend (kiểm tra service port 8001).",
      );
    }
    if (!res.ok) {
      let errorMsg = `Tải lên thất bại (HTTP ${res.status}). Vui lòng thử lại.`;
      try {
        const errorData = await res.json();
        if (res.status === 409 || errorData?.code === "entity_already_exists") {
          errorMsg =
            errorData?.detail ||
            errorData?.message ||
            `Tệp '${file.name}' đã tồn tại trong kho tri thức này (Trùng lặp tệp).`;
        } else if (errorData?.detail) {
          errorMsg = errorData.detail;
        } else if (errorData?.message) {
          errorMsg = errorData.message;
        } else if (errorData?.title) {
          errorMsg = errorData.title;
        }
      } catch {
        if (res.status === 409) {
          errorMsg = `Tệp '${file.name}' đã tồn tại trong kho tri thức này (Trùng lặp tệp).`;
        }
      }
      throw new Error(errorMsg);
    }
    const d = (await res.json()) as Record<string, unknown>;
    const fn = (d.filename as string) || (d.file_name as string) || file.name;
    const newDoc: KnowledgeDocument = {
      id: d.id as string,
      collection_id: (d.collection_id as string) || collectionId,
      collection_name: "Kho Tri Thức",
      title: (d.title as string) || fn,
      filename: fn,
      file_size:
        typeof d.file_size_bytes === "number" ? d.file_size_bytes : file.size,
      page_count: 1,
      chunk_count: 0,
      status: (d.status as KnowledgeDocument["status"]) || "pending",
      ocr_method: (d.ocr_method as string) || "PyMuPdfParser",
      document_type_code: (d.document_type_code as string) || undefined,
      document_type: (d.document_type_code as string) || undefined,
      created_at: new Date().toISOString().replace("T", " ").substring(0, 16),
    };
    return newDoc;
  },

  async parsePreviewDocument(
    collectionId: string,
    file: File,
    strategy = "semantic",
    ocrEngine?: string,
  ): Promise<ParsePreviewResult> {
    const formData = new FormData();
    formData.append("file", file);
    const params = new URLSearchParams({ strategy });
    if (ocrEngine) {
      params.append("ocr_engine", ocrEngine);
    }
    const res = await fetch(
      `${BASE_URL}/knowledge/collections/${collectionId}/parse-preview?${params.toString()}`,
      { method: "POST", body: formData },
    );
    if (!res.ok) {
      throw new Error(`Bóc tách xem trước thất bại (HTTP ${res.status}).`);
    }
    return (await res.json()) as ParsePreviewResult;
  },

  async getDocumentDetail(
    documentId: string,
  ): Promise<KnowledgeDocumentDetail> {
    const res = await fetch(`${BASE_URL}/knowledge/documents/${documentId}`);
    if (!res.ok) {
      throw new Error(`Không tải được tài liệu (HTTP ${res.status}).`);
    }
    const d = (await res.json()) as Record<string, unknown>;
    const chunks = (d.chunks as Record<string, unknown>[] | undefined) || [];
    return {
      id: d.id as string,
      collection_id: d.collection_id as string,
      collection_name: "Kho Tri Thức",
      title: d.title as string,
      filename: (d.file_name as string) || "",
      file_size: (d.file_size_bytes as number) || 0,
      page_count: 1,
      chunk_count: chunks.length,
      status: (d.status as KnowledgeDocument["status"]) || "pending",
      ocr_method: (d.ocr_method as string) || "PyMuPdfParser",
      document_type_code: (d.document_type_code as string) || undefined,
      document_type: (d.document_type_code as string) || undefined,
      created_at: (d.created_at as string) || "",
      chunks: chunks.map((c) => ({
        id: c.id as string,
        document_id: c.document_id as string,
        chunk_index: (c.chunk_index as number) || 0,
        content: (c.content as string) || "",
        token_count: (c.token_count as number) || 0,
        section: (c.section as string) || null,
        page_number: typeof c.page_number === "number" ? c.page_number : null,
        metadata: (c.metadata as Record<string, unknown>) || {},
      })),
      doc_metadata: (d.doc_metadata as Record<string, unknown>) || {},
    };
  },

  async approveDocument(
    documentId: string,
    pages?: { page_number: number; markdown_content: string }[],
  ): Promise<ApproveDocumentResult> {
    const res = await fetch(
      `${BASE_URL}/knowledge/documents/${documentId}/approve`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ pages: pages || null }),
      },
    );
    if (!res.ok) {
      throw new Error(`Phê duyệt tài liệu thất bại (HTTP ${res.status}).`);
    }
    return (await res.json()) as ApproveDocumentResult;
  },

  async batchApproveDocuments(documentIds: string[]): Promise<{
    approved: string[];
    failed: { document_id: string; error: string }[];
    indexed_chunks: number;
  }> {
    let res: Response;
    try {
      res = await fetch(`${BASE_URL}/knowledge/documents/batch-approve`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ document_ids: documentIds }),
      });
    } catch {
      throw new Error(
        "Không kết nối được máy chủ Backend (kiểm tra service port 8001).",
      );
    }
    if (!res.ok) {
      throw new Error(`Phê duyệt hàng loạt thất bại (HTTP ${res.status}).`);
    }
    return (await res.json()) as {
      approved: string[];
      failed: { document_id: string; error: string }[];
      indexed_chunks: number;
    };
  },

  async downloadDocument(documentId: string, filename: string): Promise<void> {
    let res: Response;
    try {
      res = await fetch(
        `${BASE_URL}/knowledge/documents/${documentId}/download`,
      );
    } catch {
      throw new Error(
        "Không kết nối được máy chủ Backend (kiểm tra service port 8001).",
      );
    }
    if (!res.ok) {
      throw new Error(`Tải tệp gốc thất bại (HTTP ${res.status}).`);
    }
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    link.click();
    URL.revokeObjectURL(url);
  },

  async deleteDocument(documentId: string): Promise<void> {
    let res: Response;
    try {
      res = await fetch(`${BASE_URL}/knowledge/documents/${documentId}`, {
        method: "DELETE",
      });
    } catch {
      throw new Error(
        "Không kết nối được máy chủ Backend (kiểm tra service port 8001).",
      );
    }
    if (res.status === 204 || res.status === 404 || res.ok) {
      return;
    }
    if (res.status === 500) {
      const text = await res.text().catch(() => "");
      if (
        !text ||
        text.includes("ECONNREFUSED") ||
        text.includes("proxy error")
      ) {
        throw new Error(
          "Không kết nối được máy chủ Backend (Port 8001 đang tắt). Vui lòng khởi động backend bằng lệnh 'make be' hoặc 'make dev'.",
        );
      }
      throw new Error(
        `Xóa tài liệu thất bại (HTTP 500): ${text.slice(0, 100)}`,
      );
    }
    throw new Error(`Xóa tài liệu thất bại (HTTP ${res.status}).`);
  },

  async getCollectionFacts(
    collectionId: string,
    limit = 500,
    offset = 0,
  ): Promise<FactListResponse> {
    const res = await fetch(
      `${BASE_URL}/knowledge/collections/${collectionId}/facts?limit=${limit}&offset=${offset}`,
    );
    if (!res.ok) {
      throw new Error(`Tải danh sách facts thất bại (HTTP ${res.status}).`);
    }
    return (await res.json()) as FactListResponse;
  },

  async importFactsExcel(
    collectionId: string,
    file: File,
  ): Promise<FactExcelImportResponse> {
    const formData = new FormData();
    formData.append("file", file);
    const res = await fetch(
      `${BASE_URL}/knowledge/collections/${collectionId}/facts/import-excel`,
      {
        method: "POST",
        body: formData,
      },
    );
    if (!res.ok) {
      throw new Error(`Nạp bảng biểu số liệu thất bại (HTTP ${res.status}).`);
    }
    return (await res.json()) as FactExcelImportResponse;
  },

  async reindexDocument(documentId: string): Promise<ReindexDocumentResponse> {
    const res = await fetch(
      `${BASE_URL}/knowledge/documents/${documentId}/reindex`,
      {
        method: "POST",
      },
    );
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "Lỗi kết nối" }));
      throw new Error(
        err.detail || `Lập chỉ mục lại thất bại (HTTP ${res.status}).`,
      );
    }
    return (await res.json()) as ReindexDocumentResponse;
  },

  async reconcileCollection(
    collectionId: string,
  ): Promise<KnowledgeReconciliationReport> {
    const res = await fetch(
      `${BASE_URL}/knowledge/collections/${collectionId}/reconcile`,
    );
    if (!res.ok) {
      throw new Error(`Đối soát kho tri thức thất bại (HTTP ${res.status}).`);
    }
    return (await res.json()) as KnowledgeReconciliationReport;
  },

  async fixReconciliation(collectionId: string): Promise<ReconcileFixResponse> {
    const res = await fetch(
      `${BASE_URL}/knowledge/collections/${collectionId}/reconcile-fix`,
      {
        method: "POST",
      },
    );
    if (!res.ok) {
      throw new Error(`Đồng bộ sửa lỗi chỉ mục thất bại (HTTP ${res.status}).`);
    }
    return (await res.json()) as ReconcileFixResponse;
  },

  async getReconciliationReport(
    collectionId: string,
  ): Promise<KnowledgeReconciliationReport> {
    return this.reconcileCollection(collectionId);
  },

  getDocumentDownloadUrl(documentId: string): string {
    return `${BASE_URL}/knowledge/documents/${documentId}/download`;
  },

  // ==============================================================================
  // Knowledge Publishing V2 Methods (ADR-011)
  // ==============================================================================

  /**
   * Lấy danh sách tài liệu từ kho trung tâm có thể liên kết vào bộ sưu tập
   */
  async getAvailableDocuments(
    collectionId: string,
    search?: string,
    page = 1,
    pageSize = 20,
  ): Promise<AvailableRepositoryDocumentsResponse> {
    const params = new URLSearchParams({
      page: String(page),
      page_size: String(pageSize),
    });
    if (search) params.set("search", search);

    const res = await fetch(
      `${BASE_URL}/knowledge/collections/${collectionId}/available-documents?${params.toString()}`,
      {
        headers: getAuthHeaders(),
      },
    );
    if (!res.ok) {
      throw new Error(
        `Không thể lấy danh sách tài liệu kho sẵn sàng (HTTP ${res.status}).`,
      );
    }
    return res.json();
  },

  /**
   * Tạo liên kết tri thức từ kho tài liệu trung tâm (Knowledge Bindings)
   */
  async createBindings(
    collectionId: string,
    request: CreateKnowledgeBindingsRequest,
  ): Promise<CreateKnowledgeBindingsResponse> {
    const res = await fetch(
      `${BASE_URL}/knowledge/collections/${collectionId}/bindings`,
      {
        method: "POST",
        headers: getAuthHeaders({ "Content-Type": "application/json" }),
        body: JSON.stringify(request),
      },
    );
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(
        (err as { detail?: string }).detail ||
          `Tạo liên kết tài liệu thất bại (HTTP ${res.status}).`,
      );
    }
    return res.json();
  },

  /**
   * Lấy danh sách các liên kết tài liệu (Knowledge Bindings) trong bộ sưu tập
   */
  async getBindings(
    collectionId: string,
    status?: string,
    page = 1,
    pageSize = 50,
  ): Promise<KnowledgeBinding[]> {
    const params = new URLSearchParams({
      page: String(page),
      page_size: String(pageSize),
    });
    if (status) params.set("status", status);

    const res = await fetch(
      `${BASE_URL}/knowledge/collections/${collectionId}/bindings?${params.toString()}`,
      {
        headers: getAuthHeaders(),
      },
    );
    if (!res.ok) {
      throw new Error(
        `Không thể tải danh sách liên kết tri thức (HTTP ${res.status}).`,
      );
    }
    return res.json();
  },

  /**
   * Lấy chi tiết một liên kết tài liệu tri thức
   */
  async getBinding(bindingId: string): Promise<KnowledgeBinding> {
    const res = await fetch(`${BASE_URL}/knowledge/bindings/${bindingId}`, {
      headers: getAuthHeaders(),
    });
    if (!res.ok) {
      throw new Error(
        `Không tìm thấy liên kết tri thức ID '${bindingId}' (HTTP ${res.status}).`,
      );
    }
    return res.json();
  },

  /**
   * Hủy liên kết tài liệu khỏi bộ sưu tập tri thức
   */
  async pauseSource(bindingId: string): Promise<KnowledgeBinding> {
    const res = await fetch(
      `${BASE_URL}/knowledge/bindings/${bindingId}/pause`,
      {
        method: "POST",
        headers: getAuthHeaders(),
      },
    );
    if (!res.ok) {
      const err: unknown = await res.json().catch(() => ({}));
      throw new Error(extractErrorMessage(err, "Không ngừng dùng được nguồn."));
    }
    return res.json();
  },

  async detachBinding(bindingId: string): Promise<KnowledgeBinding> {
    const res = await fetch(`${BASE_URL}/knowledge/bindings/${bindingId}`, {
      method: "DELETE",
      headers: getAuthHeaders(),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(
        (err as { detail?: string }).detail ||
          `Hủy liên kết tài liệu thất bại (HTTP ${res.status}).`,
      );
    }
    return res.json();
  },

  /**
   * Xây dựng chỉ mục staging và kiểm tra Parity Gate cho một binding
   */
  async buildStagingIndex(
    bindingId: string,
    request: BuildStagingIndexRequest = {},
  ): Promise<KnowledgeIndexRevision> {
    const res = await fetch(
      `${BASE_URL}/knowledge/bindings/${bindingId}/build-index`,
      {
        method: "POST",
        headers: getAuthHeaders({ "Content-Type": "application/json" }),
        body: JSON.stringify(request),
      },
    );
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(
        (err as { detail?: string }).detail ||
          `Dựng chỉ mục staging thất bại (HTTP ${res.status}).`,
      );
    }
    return res.json();
  },

  /**
   * Kích hoạt nguyên tử (Atomic Pointer Swap) index revision cho một binding
   */
  async promoteIndexRevision(
    bindingId: string,
    request: IndexActivationRequest,
  ): Promise<IndexActivationResponse> {
    const res = await fetch(
      `${BASE_URL}/knowledge/bindings/${bindingId}/promote`,
      {
        method: "POST",
        headers: getAuthHeaders({ "Content-Type": "application/json" }),
        body: JSON.stringify(request),
      },
    );
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(
        (err as { detail?: string }).detail ||
          `Kích hoạt chỉ mục thất bại (HTTP ${res.status}).`,
      );
    }
    return res.json();
  },

  /**
   * Lấy lịch sử các phiên bản chỉ mục (Index Revisions) của binding
   */
  async getIndexRevisions(
    bindingId: string,
  ): Promise<KnowledgeIndexRevision[]> {
    const res = await fetch(
      `${BASE_URL}/knowledge/bindings/${bindingId}/revisions`,
      {
        headers: getAuthHeaders(),
      },
    );
    if (!res.ok) {
      throw new Error(`Không thể lấy lịch sử chỉ mục (HTTP ${res.status}).`);
    }
    return res.json();
  },

  /**
   * Chạy dọn dẹp các Index Revision cũ không còn sử dụng (Artifact GC với Rollback Protection)
   */
  async runGarbageCollection(
    collectionId: string,
    request?: GarbageCollectionRequest,
  ): Promise<GarbageCollectionReport> {
    const res = await fetch(
      `${BASE_URL}/knowledge/collections/${collectionId}/gc`,
      {
        method: "POST",
        headers: getAuthHeaders({ "Content-Type": "application/json" }),
        body: JSON.stringify(request || {}),
      },
    );
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(
        (err as { detail?: string }).detail ||
          `Dọn dẹp chỉ mục thất bại (HTTP ${res.status}).`,
      );
    }
    return res.json();
  },

  /**
   * Hoàn tác tức thì (Instant Zero-Reindex Rollback) về index revision trước đó
   */
  async rollbackIndexRevision(
    bindingId: string,
    request: RollbackIndexRevisionRequest,
  ): Promise<IndexActivationResponse> {
    const res = await fetch(
      `${BASE_URL}/knowledge/bindings/${bindingId}/rollback`,
      {
        method: "POST",
        headers: getAuthHeaders({ "Content-Type": "application/json" }),
        body: JSON.stringify(request),
      },
    );
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(
        (err as { detail?: string }).detail ||
          `Hoàn tác chỉ mục thất bại (HTTP ${res.status}).`,
      );
    }
    return res.json();
  },

  /**
   * Lấy danh sách các chunk phân đoạn của một binding hoặc revision cụ thể (Chunk Inspector)
   */
  async getBindingChunks(
    bindingId: string,
    indexRevisionId?: string,
    page = 1,
    pageSize = 50,
  ): Promise<BindingChunksResponse> {
    const params = new URLSearchParams({
      page: String(page),
      page_size: String(pageSize),
    });
    if (indexRevisionId) {
      params.set("index_revision_id", indexRevisionId);
    }

    const res = await fetch(
      `${BASE_URL}/knowledge/bindings/${bindingId}/chunks?${params.toString()}`,
      {
        headers: getAuthHeaders(),
      },
    );
    if (!res.ok) {
      throw new Error(`Không thể lấy danh sách chunks (HTTP ${res.status}).`);
    }
    return res.json();
  },

  /**
   * Kiểm kê và phân loại dữ liệu legacy của collection (active-parity-ok / needs-rebuild / pending-intake)
   */
  async auditCollectionCanary(
    collectionId: string,
  ): Promise<LegacyAuditReport> {
    const res = await fetch(
      `${BASE_URL}/knowledge/collections/${collectionId}/canary/audit`,
      {
        method: "POST",
        headers: getAuthHeaders(),
      },
    );
    if (!res.ok) {
      throw new Error(`Kiểm kê Parity thất bại (HTTP ${res.status}).`);
    }
    return res.json();
  },

  /**
   * Chạy backfill an toàn (idempotent) chuyển đổi collection legacy sang chuẩn V2
   */
  async backfillCollectionCanary(
    collectionId: string,
    payload: BackfillRequest = {},
  ): Promise<BackfillReport> {
    const res = await fetch(
      `${BASE_URL}/knowledge/collections/${collectionId}/canary/backfill`,
      {
        method: "POST",
        headers: {
          ...getAuthHeaders(),
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
      },
    );
    if (!res.ok) {
      throw new Error(`Di trú Backfill thất bại (HTTP ${res.status}).`);
    }
    return res.json();
  },

  /**
   * Chạy shadow retrieval đối soát song song V1 Legacy và V2 Snapshot Isolation
   */
  async runShadowRetrievalTest(
    collectionId: string,
    payload: ShadowRetrievalRequest,
  ): Promise<ShadowRetrievalReport> {
    const res = await fetch(
      `${BASE_URL}/knowledge/collections/${collectionId}/canary/shadow-test`,
      {
        method: "POST",
        headers: {
          ...getAuthHeaders(),
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
      },
    );
    if (!res.ok) {
      throw new Error(`Chạy Shadow Retrieval thất bại (HTTP ${res.status}).`);
    }
    return res.json();
  },

  /**
   * Lấy cấu hình Canary serving mode và chính sách lưu trữ (retention) của kho
   */
  async getCanaryPolicy(collectionId: string): Promise<CanaryPolicyResponse> {
    const res = await fetch(
      `${BASE_URL}/knowledge/collections/${collectionId}/canary/policy`,
      {
        headers: getAuthHeaders(),
      },
    );
    if (!res.ok) {
      throw new Error(`Lấy chính sách Canary thất bại (HTTP ${res.status}).`);
    }
    return res.json();
  },

  /**
   * Cập nhật chính sách Canary serving mode và retention revisions
   */
  async updateCanaryPolicy(
    collectionId: string,
    payload: UpdateCanaryPolicyRequest,
  ): Promise<CanaryPolicyResponse> {
    const res = await fetch(
      `${BASE_URL}/knowledge/collections/${collectionId}/canary/policy`,
      {
        method: "PUT",
        headers: {
          ...getAuthHeaders(),
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
      },
    );
    if (!res.ok) {
      throw new Error(
        `Cập nhật chính sách Canary thất bại (HTTP ${res.status}).`,
      );
    }
    return res.json();
  },

  /**
   * Chạy dọn dẹp Artifact Garbage Collection trên toàn bộ hệ thống
   */
  async runSystemWideGarbageCollection(
    payload?: SystemGarbageCollectionRequest,
  ): Promise<SystemGarbageCollectionReport> {
    const res = await fetch(`${BASE_URL}/knowledge/gc/system-wide`, {
      method: "POST",
      headers: {
        ...getAuthHeaders(),
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload || {}),
    });
    if (!res.ok) {
      throw new Error(
        `Thực thi Garbage Collection toàn hệ thống thất bại (HTTP ${res.status}).`,
      );
    }
    return res.json();
  },

  /**
   * Lấy báo cáo kiểm kê di trú V2 và mức độ sẵn sàng decommission legacy toàn trường
   */
  async getSystemDecommissioningAudit(): Promise<SystemDecommissioningAuditReport> {
    const res = await fetch(`${BASE_URL}/knowledge/decommissioning/audit`, {
      headers: getAuthHeaders(),
    });
    if (!res.ok) {
      throw new Error(
        `Lấy báo cáo kiểm kê chuyển đổi thất bại (HTTP ${res.status}).`,
      );
    }
    return res.json();
  },

  /**
   * Xem trước phân tích nhóm tài liệu trước khi đưa vào kho tri thức (Read-only)
   */
  async previewDocumentGroup(
    collectionId: string,
    groupId: string,
  ): Promise<PreviewDocumentGroupResponse> {
    const res = await fetch(
      `${BASE_URL}/knowledge/collections/${collectionId}/preview-document-group`,
      {
        method: "POST",
        headers: {
          ...getAuthHeaders(),
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ group_id: groupId }),
      },
    );
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(
        (err as { detail?: string }).detail ||
          (err as { message?: string }).message ||
          `Xem trước nhóm tài liệu thất bại (HTTP ${res.status}).`,
      );
    }
    return res.json();
  },

  /**
   * Đưa nhóm tài liệu vào kho tri thức (Snapshot thủ công)
   */
  async attachDocumentGroup(
    collectionId: string,
    payload: AttachDocumentGroupRequest,
  ): Promise<AttachDocumentGroupResponse> {
    const res = await fetch(
      `${BASE_URL}/knowledge/collections/${collectionId}/attach-document-group`,
      {
        method: "POST",
        headers: {
          ...getAuthHeaders(),
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
      },
    );
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(
        (err as { detail?: string }).detail ||
          (err as { message?: string }).message ||
          `Đưa nhóm vào kho tri thức thất bại (HTTP ${res.status}).`,
      );
    }
    return res.json();
  },
  /**
   * Lấy danh sách nguồn nhóm tài liệu của Kho Tri Thức
   */
  async getGroupSources(collectionId: string): Promise<KnowledgeGroupSource[]> {
    const res = await fetch(
      `${BASE_URL}/knowledge/collections/${collectionId}/sources`,
      {
        headers: getAuthHeaders(),
      },
    );
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(
        extractErrorMessage(err, `Lỗi tải nguồn nhóm (HTTP ${res.status}).`),
      );
    }
    return res.json();
  },

  /**
   * Xem trước một nhóm tài liệu trước khi thêm làm nguồn
   */
  async previewAttachGroup(
    collectionId: string,
    groupId: string,
  ): Promise<PreviewGroupSourceDiffResponse> {
    const res = await fetch(
      `${BASE_URL}/knowledge/collections/${collectionId}/sources/preview-attach`,
      {
        method: "POST",
        headers: {
          ...getAuthHeaders(),
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ group_id: groupId }),
      },
    );
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(
        extractErrorMessage(
          err,
          `Xem trước nguồn nhóm thất bại (HTTP ${res.status}).`,
        ),
      );
    }
    return res.json();
  },

  /**
   * Thêm một nhóm tài liệu làm nguồn lâu dài
   */
  async attachGroupSource(
    collectionId: string,
    payload: AttachGroupSourceRequest,
  ): Promise<KnowledgeGroupSource> {
    const res = await fetch(
      `${BASE_URL}/knowledge/collections/${collectionId}/sources`,
      {
        method: "POST",
        headers: {
          ...getAuthHeaders(),
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
      },
    );
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(
        extractErrorMessage(
          err,
          `Thêm nguồn nhóm thất bại (HTTP ${res.status}).`,
        ),
      );
    }
    return res.json();
  },

  /**
   * Xem trước thay đổi của một nguồn nhóm đã liên kết
   */
  async previewSourceSync(
    collectionId: string,
    sourceId: string,
  ): Promise<PreviewGroupSourceDiffResponse> {
    const res = await fetch(
      `${BASE_URL}/knowledge/collections/${collectionId}/sources/${sourceId}/preview`,
      { headers: getAuthHeaders() },
    );
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(
        extractErrorMessage(
          err,
          `Xem trước đồng bộ thất bại (HTTP ${res.status}).`,
        ),
      );
    }
    return res.json();
  },

  /**
   * Đồng bộ nguồn nhóm tài liệu
   */
  async syncGroupSource(
    collectionId: string,
    sourceId: string,
    payload?: SyncGroupSourceRequest,
  ): Promise<SyncGroupSourceResponse> {
    const res = await fetch(
      `${BASE_URL}/knowledge/collections/${collectionId}/sources/${sourceId}/sync`,
      {
        method: "POST",
        headers: {
          ...getAuthHeaders(),
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload || {}),
      },
    );
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(
        extractErrorMessage(
          err,
          `Đồng bộ nguồn nhóm thất bại (HTTP ${res.status}).`,
        ),
      );
    }
    return res.json();
  },

  /**
   * Xuất bản chỉ mục staging của nguồn nhóm
   */
  async publishGroupSource(
    collectionId: string,
    sourceId: string,
  ): Promise<PublishGroupSourceResponse> {
    const res = await fetch(
      `${BASE_URL}/knowledge/collections/${collectionId}/sources/${sourceId}/publish`,
      {
        method: "POST",
        headers: getAuthHeaders(),
      },
    );
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(
        extractErrorMessage(
          err,
          `Xuất bản nguồn nhóm thất bại (HTTP ${res.status}).`,
        ),
      );
    }
    return res.json();
  },

  /**
   * Gỡ nguồn nhóm tài liệu khỏi Kho Tri Thức
   */
  async detachGroupSource(
    collectionId: string,
    sourceId: string,
    detachBindings: boolean = true,
  ): Promise<DetachGroupSourceResponse> {
    const res = await fetch(
      `${BASE_URL}/knowledge/collections/${collectionId}/sources/${sourceId}?detach_bindings=${detachBindings}`,
      {
        method: "DELETE",
        headers: getAuthHeaders(),
      },
    );
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(
        extractErrorMessage(
          err,
          `Gỡ nguồn nhóm thất bại (HTTP ${res.status}).`,
        ),
      );
    }
    return res.json();
  },

  /**
   * Lấy số liệu đo lường tổng hợp và trạng thái nghiệp vụ thật của Kho Tri Thức
   */
  async getCollectionSummaryMetrics(
    collectionId: string,
  ): Promise<CollectionSummaryMetrics> {
    const res = await fetch(
      `${BASE_URL}/knowledge/collections/${collectionId}/summary-metrics`,
      { headers: getAuthHeaders() },
    );
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(
        extractErrorMessage(err, `Lỗi tải số liệu kho (HTTP ${res.status}).`),
      );
    }
    return res.json();
  },

  // ==============================================================================
  // V3 Candidate Groups & Documents (ADR-012)
  // ==============================================================================

  async getCandidateGroups(
    collectionId: string,
  ): Promise<CandidateGroupListResponse> {
    const res = await fetch(
      `${BASE_URL}/knowledge/collections/${collectionId}/candidate-groups`,
      {
        headers: getAuthHeaders(),
      },
    );
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(
        extractErrorMessage(err, `Lỗi tải nhóm ứng viên (HTTP ${res.status}).`),
      );
    }
    return res.json();
  },

  async getCandidateDocuments(
    collectionId: string,
    params: {
      group_id?: string;
      vector_generation_id?: string;
      source_status?: string;
      search?: string;
      limit?: number;
      offset?: number;
    } = {},
  ): Promise<CandidateListResponse> {
    const sp = new URLSearchParams();
    if (params.group_id) sp.set("group_id", params.group_id);
    if (params.vector_generation_id)
      sp.set("vector_generation_id", params.vector_generation_id);
    if (params.source_status) sp.set("source_status", params.source_status);
    if (params.search) sp.set("search", params.search);
    if (params.limit) sp.set("limit", String(params.limit));
    if (params.offset) sp.set("offset", String(params.offset));

    const qs = sp.toString() ? `?${sp.toString()}` : "";
    const res = await fetch(
      `${BASE_URL}/knowledge/collections/${collectionId}/candidate-documents${qs}`,
      {
        headers: getAuthHeaders(),
      },
    );
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(
        extractErrorMessage(
          err,
          `Lỗi tải tài liệu ứng viên (HTTP ${res.status}).`,
        ),
      );
    }
    return res.json();
  },

  // ==============================================================================
  // V3 Snapshot Import Batches (ADR-012)
  // ==============================================================================

  async createImportBatch(
    collectionId: string,
    payload: KnowledgeImportBatchCreateRequest,
    idempotencyKey?: string,
  ): Promise<KnowledgeImportBatchResponse> {
    const headers = new Headers(getAuthHeaders());
    headers.set("Content-Type", "application/json");
    if (idempotencyKey) {
      headers.set("Idempotency-Key", idempotencyKey);
    }

    const res = await fetch(
      `${BASE_URL}/knowledge/collections/${collectionId}/imports`,
      {
        method: "POST",
        headers,
        body: JSON.stringify(payload),
      },
    );
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(
        extractErrorMessage(
          err,
          `Tạo đợt nạp tài liệu thất bại (HTTP ${res.status}).`,
        ),
      );
    }
    return res.json();
  },

  async getImportBatch(
    collectionId: string,
    batchId: string,
  ): Promise<KnowledgeImportBatchResponse> {
    const res = await fetch(
      `${BASE_URL}/knowledge/collections/${collectionId}/imports/${batchId}`,
      {
        headers: getAuthHeaders(),
      },
    );
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(
        extractErrorMessage(err, `Lỗi tải đợt nạp (HTTP ${res.status}).`),
      );
    }
    return res.json();
  },

  async retryFailedImportItems(
    collectionId: string,
    batchId: string,
  ): Promise<KnowledgeImportBatchResponse> {
    const res = await fetch(
      `${BASE_URL}/knowledge/collections/${collectionId}/imports/${batchId}/retry-failed`,
      {
        method: "POST",
        headers: getAuthHeaders(),
      },
    );
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(
        extractErrorMessage(
          err,
          `Thử lại đợt nạp thất bại (HTTP ${res.status}).`,
        ),
      );
    }
    return res.json();
  },

  async cancelImportBatch(
    collectionId: string,
    batchId: string,
  ): Promise<KnowledgeImportBatchResponse> {
    const res = await fetch(
      `${BASE_URL}/knowledge/collections/${collectionId}/imports/${batchId}/cancel`,
      {
        method: "POST",
        headers: getAuthHeaders(),
      },
    );
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(
        extractErrorMessage(err, `Hủy đợt nạp thất bại (HTTP ${res.status}).`),
      );
    }
    return res.json();
  },

  // ==============================================================================
  // V3 Knowledge Source Lifecycle & Human Review (ADR-012)
  // ==============================================================================

  async getKnowledgeSource(
    collectionId: string,
    sourceId: string,
  ): Promise<KnowledgeSourceDetailResponse> {
    const res = await fetch(
      `${BASE_URL}/knowledge/collections/${collectionId}/sources/${sourceId}`,
      {
        headers: getAuthHeaders(),
      },
    );
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(
        extractErrorMessage(
          err,
          `Lỗi tải nguồn tri thức (HTTP ${res.status}).`,
        ),
      );
    }
    return res.json();
  },

  async listSourceRevisions(
    collectionId: string,
    sourceId: string,
  ): Promise<KnowledgeSourceRevisionResponse[]> {
    const res = await fetch(
      `${BASE_URL}/knowledge/collections/${collectionId}/sources/${sourceId}/revisions`,
      {
        headers: getAuthHeaders(),
      },
    );
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(
        extractErrorMessage(
          err,
          `Lỗi tải danh sách bản sửa đổi (HTTP ${res.status}).`,
        ),
      );
    }
    return res.json();
  },

  async updateSourceRevisionContent(
    collectionId: string,
    sourceId: string,
    revisionId: string,
    markdown: string,
  ): Promise<KnowledgeSourceRevisionResponse> {
    const res = await fetch(
      `${BASE_URL}/knowledge/collections/${collectionId}/sources/${sourceId}/revisions/${revisionId}/content`,
      {
        method: "PATCH",
        headers: {
          ...getAuthHeaders(),
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ canonical_markdown: markdown }),
      },
    );
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(
        extractErrorMessage(
          err,
          `Lỗi hiệu đính nội dung (HTTP ${res.status}).`,
        ),
      );
    }
    return res.json();
  },

  async reviewSourceRevision(
    collectionId: string,
    sourceId: string,
    revisionId: string,
    decision: "approved" | "rejected",
    comment?: string,
  ): Promise<KnowledgeSourceRevisionResponse> {
    const res = await fetch(
      `${BASE_URL}/knowledge/collections/${collectionId}/sources/${sourceId}/revisions/${revisionId}/review`,
      {
        method: "POST",
        headers: {
          ...getAuthHeaders(),
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ decision, comment }),
      },
    );
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(
        extractErrorMessage(
          err,
          `Lỗi phê duyệt bản sửa đổi (HTTP ${res.status}).`,
        ),
      );
    }
    return res.json();
  },

  async previewVectorGeneration(
    collectionId: string,
    generationId: string,
    question: string,
  ): Promise<{
    status: string;
    answer: string;
    citations: {
      title: string;
      page_number?: number | null;
      quote?: string | null;
    }[];
  }> {
    const response = await fetch(
      `${BASE_URL}/knowledge/collections/${collectionId}/vector-generations/${generationId}/preview`,
      {
        method: "POST",
        headers: { ...getAuthHeaders(), "Content-Type": "application/json" },
        body: JSON.stringify({ question }),
      },
    );
    if (!response.ok)
      throw new Error(
        extractErrorMessage(
          await response.json().catch(() => ({})),
          "Không kiểm tra được chỉ mục dự thảo.",
        ),
      );
    return response.json();
  },

  async getSourceStudioView(
    collectionId: string,
    sourceId: string,
    revisionId?: string,
  ): Promise<DocumentVerificationData> {
    const url = revisionId
      ? `${BASE_URL}/knowledge/collections/${collectionId}/sources/${sourceId}/studio?revision_id=${revisionId}`
      : `${BASE_URL}/knowledge/collections/${collectionId}/sources/${sourceId}/studio`;
    const res = await fetch(url, { headers: getAuthHeaders() });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(
        extractErrorMessage(
          err,
          `Không tải được dữ liệu bóc tách Studio (HTTP ${res.status}).`,
        ),
      );
    }
    const v = (await res.json()) as {
      citation_metadata?: DocumentVerificationData["citation_metadata"];
      structured_artifact?: DocumentVerificationData["structured_artifact"];
      layout_text_alignment?: string;
      document_id: string;
      revision_id?: string;
      collection_id: string;
      title: string;
      filename: string;
      engine: string;
      status?: string;
      index_status?: string;
      total_pages: number;
      file_size_bytes?: number;
      total_chunks?: number;
      pages: {
        page_number: number;
        markdown_content: string;
        raw_text: string;
        word_count: number;
        line_count: number;
        image_url: string | null;
        dimensions?: { width: number; height: number };
        has_tables?: boolean;
        bounding_boxes: DocumentVerificationData["pages"][number]["bounding_boxes"];
        regions: DocumentVerificationData["pages"][number]["regions"];
      }[];
    };
    const totalChars = v.pages.reduce(
      (sum, p) => sum + (p.markdown_content ? p.markdown_content.length : 0),
      0,
    );
    const sizeBytes =
      typeof v.file_size_bytes === "number" ? v.file_size_bytes : 0;
    return {
      document_id: v.document_id,
      citation_metadata: v.citation_metadata,
      structured_artifact: v.structured_artifact,
      layout_text_alignment: v.layout_text_alignment,
      revision_id: v.revision_id,
      collection_id: v.collection_id,
      title: v.title,
      filename: v.filename,
      status: v.status,
      index_status: v.index_status,
      file_size_mb: Math.round((sizeBytes / 1048576) * 100) / 100,
      total_pages: v.total_pages,
      engine: v.engine,
      total_chars: totalChars,
      estimated_chunks: typeof v.total_chunks === "number" ? v.total_chunks : 0,
      pages: v.pages.map((p) => ({
        page_number: p.page_number,
        word_count: p.word_count,
        line_count: p.line_count,
        image_url: p.image_url || undefined,
        dimensions: p.dimensions,
        has_tables: p.has_tables,
        markdown_content: p.markdown_content,
        raw_text: p.raw_text,
        bounding_boxes: p.bounding_boxes || [],
        regions: p.regions || [],
      })),
    };
  },

  async reparseSource(
    collectionId: string,
    sourceId: string,
    payload: { parser_profile: string; ocr_engine?: string },
  ): Promise<KnowledgeSourceRevisionResponse> {
    const res = await fetch(
      `${BASE_URL}/knowledge/collections/${collectionId}/sources/${sourceId}/reparse`,
      {
        method: "POST",
        headers: {
          ...getAuthHeaders(),
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
      },
    );
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(
        extractErrorMessage(
          err,
          `Bóc tách lại nguồn tài liệu thất bại (HTTP ${res.status}).`,
        ),
      );
    }
    return res.json();
  },

  // ==============================================================================
  // V3 Vector Generations & Multi-Vector Spaces (ADR-012)
  // ==============================================================================

  async listVectorGenerations(
    collectionId: string,
  ): Promise<KnowledgeVectorGenerationResponse[]> {
    const res = await fetch(
      `${BASE_URL}/knowledge/collections/${collectionId}/vector-generations`,
      {
        headers: getAuthHeaders(),
      },
    );
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(
        extractErrorMessage(err, `Lỗi tải thế hệ vector (HTTP ${res.status}).`),
      );
    }
    return res.json();
  },

  async createVectorGeneration(
    collectionId: string,
    payload: CreateVectorGenerationRequest,
  ): Promise<KnowledgeVectorGenerationResponse> {
    const res = await fetch(
      `${BASE_URL}/knowledge/collections/${collectionId}/vector-generations`,
      {
        method: "POST",
        headers: {
          ...getAuthHeaders(),
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
      },
    );
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(
        extractErrorMessage(
          err,
          `Tạo thế hệ vector thất bại (HTTP ${res.status}).`,
        ),
      );
    }
    return res.json();
  },

  async buildVectorGeneration(
    collectionId: string,
    generationId: string,
    payload: BuildVectorGenerationRequest = {},
  ): Promise<BuildVectorGenerationResponse> {
    const res = await fetch(
      `${BASE_URL}/knowledge/collections/${collectionId}/vector-generations/${generationId}/build`,
      {
        method: "POST",
        headers: {
          ...getAuthHeaders(),
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
      },
    );
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(
        extractErrorMessage(
          err,
          `Lập chỉ mục thế hệ vector thất bại (HTTP ${res.status}).`,
        ),
      );
    }
    return res.json();
  },

  async activateVectorGeneration(
    collectionId: string,
    generationId: string,
  ): Promise<ActivateVectorGenerationResponse> {
    const res = await fetch(
      `${BASE_URL}/knowledge/collections/${collectionId}/vector-generations/${generationId}/activate`,
      {
        method: "POST",
        headers: getAuthHeaders(),
      },
    );
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(
        extractErrorMessage(
          err,
          `Kích hoạt thế hệ vector thất bại (HTTP ${res.status}).`,
        ),
      );
    }
    return res.json();
  },

  async rollbackVectorGeneration(
    collectionId: string,
    generationId: string,
  ): Promise<ActivateVectorGenerationResponse> {
    const res = await fetch(
      `${BASE_URL}/knowledge/collections/${collectionId}/vector-generations/${generationId}/rollback`,
      { method: "POST", headers: getAuthHeaders() },
    );
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(extractErrorMessage(err, "Khôi phục chỉ mục thất bại."));
    }
    return res.json();
  },

  async listSourceChunkSets(
    collectionId: string,
    sourceId: string,
  ): Promise<KnowledgeChunkSetResponse[]> {
    const res = await fetch(
      `${BASE_URL}/knowledge/collections/${collectionId}/sources/${sourceId}/chunk-sets`,
      {
        headers: getAuthHeaders(),
      },
    );
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(
        extractErrorMessage(
          err,
          `Lỗi tải danh sách tập đoạn cắt (HTTP ${res.status}).`,
        ),
      );
    }
    return res.json();
  },
};
