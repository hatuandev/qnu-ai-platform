import type {
  ApproveDocumentResult,
  AvailableRepositoryDocumentsResponse,
  BackfillReport,
  BackfillRequest,
  BindingChunksResponse,
  BuildStagingIndexRequest,
  CanaryPolicyResponse,
  CollectionDataProcessingConfig,
  CreateKnowledgeBindingsRequest,
  CreateKnowledgeBindingsResponse,
  FactExcelImportResponse,
  FactListResponse,
  GarbageCollectionReport,
  GarbageCollectionRequest,
  IndexActivationRequest,
  IndexActivationResponse,
  KnowledgeBinding,
  KnowledgeCollection,
  KnowledgeDocument,
  KnowledgeDocumentDetail,
  KnowledgeIndexRevision,
  KnowledgeReconciliationReport,
  LegacyAuditReport,
  ParsePreviewResult,
  ReconcileFixResponse,
  ReindexDocumentResponse,
  RollbackIndexRevisionRequest,
  ShadowRetrievalReport,
  ShadowRetrievalRequest,
  SystemDecommissioningAuditReport,
  SystemGarbageCollectionReport,
  SystemGarbageCollectionRequest,
  UpdateCanaryPolicyRequest,
} from "@/types/knowledge";
import { BASE_URL, getAuthHeaders } from "./http-client";

export const knowledgeApi = {
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
    const res = await fetch(`${BASE_URL}/knowledge/collections`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      throw new Error(`Tạo kho tri thức thất bại (HTTP ${res.status}).`);
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
};
