import { ApiError } from "@/app/api/client";
import type {
  AddGroupDocumentsRequest,
  AddGroupDocumentsResponse,
  AsyncUploadDocumentResponse,
  AttachDocumentsRequest,
  DocumentGroup,
  DocumentGroupCreateRequest,
  DocumentGroupListResponse,
  DocumentGroupUpdateRequest,
  DocumentRevision,
  DocumentRevisionListItem,
  DocumentStats,
  GroupDocumentsResponse,
  RepositoryDocument,
  RepositoryDocumentFilter,
  RepositoryDocumentListItem,
  RepositoryDocumentUpdate,
} from "@/types/documents";
import { BASE_URL, getAuthHeaders } from "./http-client";

export const documentsApi = {
  /**
   * Lấy danh sách tài liệu trong kho với các bộ lọc
   */
  async getDocuments(filter?: RepositoryDocumentFilter): Promise<{
    items: RepositoryDocumentListItem[];
    total: number;
    skip: number;
    limit: number;
  }> {
    const params = new URLSearchParams();
    if (filter?.search) params.set("search", filter.search);
    if (filter?.document_type_code)
      params.set("document_type_code", filter.document_type_code);
    if (filter?.file_type) params.set("file_type", filter.file_type);
    if (filter?.parse_status) params.set("parse_status", filter.parse_status);
    if (filter?.group_id) params.set("group_id", filter.group_id);
    if (filter?.exclude_group_id)
      params.set("exclude_group_id", filter.exclude_group_id);
    if (filter?.skip !== undefined) params.set("skip", String(filter.skip));
    if (filter?.limit !== undefined) params.set("limit", String(filter.limit));

    const res = await fetch(`${BASE_URL}/documents?${params.toString()}`, {
      headers: getAuthHeaders(),
    });
    if (!res.ok) {
      throw new Error(`Không thể tải danh sách tài liệu (HTTP ${res.status}).`);
    }
    return res.json();
  },

  /**
   * Lấy chi tiết tài liệu (kèm parsed_markdown và danh sách kho tri thức đã gắn)
   */
  async getDocument(id: string): Promise<RepositoryDocument> {
    const res = await fetch(`${BASE_URL}/documents/${id}`, {
      headers: getAuthHeaders(),
    });
    if (!res.ok) {
      throw new Error(
        `Không tìm thấy tài liệu ID '${id}' (HTTP ${res.status}).`,
      );
    }
    return res.json();
  },

  /**
   * Lấy số liệu thống kê tổng quan của Kho Tài Liệu
   */
  async getStats(): Promise<DocumentStats> {
    const res = await fetch(`${BASE_URL}/documents/stats`, {
      headers: getAuthHeaders(),
    });
    if (!res.ok) {
      throw new Error(
        `Không thể lấy thống kê kho tài liệu (HTTP ${res.status}).`,
      );
    }
    return res.json();
  },

  /**
   * Tiếp nhận tệp bất đồng bộ vào Kho Tài Liệu (Chuẩn V2 ADR-011)
   */
  async intakeDocument(
    file: File,
    meta?: {
      title?: string;
      document_number?: string;
      issuing_authority?: string;
      issued_date?: string;
      effective_date?: string;
      document_type_code?: string;
      ocr_engine?: string;
      group_id?: string;
      idempotency_key?: string;
    },
  ): Promise<AsyncUploadDocumentResponse> {
    const formData = new FormData();
    formData.append("file", file);
    if (meta?.title) formData.append("title", meta.title);
    if (meta?.document_number)
      formData.append("document_number", meta.document_number);
    if (meta?.issuing_authority)
      formData.append("issuing_authority", meta.issuing_authority);
    if (meta?.issued_date) formData.append("issued_date", meta.issued_date);
    if (meta?.effective_date)
      formData.append("effective_date", meta.effective_date);
    if (meta?.document_type_code)
      formData.append("document_type_code", meta.document_type_code);
    if (meta?.ocr_engine) formData.append("ocr_engine", meta.ocr_engine);
    if (meta?.group_id) formData.append("group_id", meta.group_id);

    const headers = getAuthHeaders();
    if (meta?.idempotency_key) {
      headers.set("Idempotency-Key", meta.idempotency_key);
    }

    const res = await fetch(`${BASE_URL}/documents/intake`, {
      method: "POST",
      headers,
      body: formData,
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(
        (err as { detail?: string; message?: string }).detail ||
          (err as { message?: string }).message ||
          `Tiếp nhận tài liệu thất bại (HTTP ${res.status}).`,
      );
    }
    return res.json();
  },

  /**
   * Tải tài liệu lên Kho Tài Liệu Tập Trung (Compatibility V1 — Deprecated: ưu tiên dùng intakeDocument)
   */
  async uploadDocument(
    file: File,
    meta?: {
      title?: string;
      document_number?: string;
      issuing_authority?: string;
      issued_date?: string;
      signer?: string;
      document_type_code?: string;
      auto_parse?: boolean;
      group_id?: string;
      idempotency_key?: string;
    },
  ): Promise<RepositoryDocument> {
    const formData = new FormData();
    formData.append("file", file);
    if (meta?.title) formData.append("title", meta.title);
    if (meta?.document_number)
      formData.append("document_number", meta.document_number);
    if (meta?.issuing_authority)
      formData.append("issuing_authority", meta.issuing_authority);
    if (meta?.issued_date) formData.append("issued_date", meta.issued_date);
    if (meta?.signer) formData.append("signer", meta.signer);
    if (meta?.document_type_code)
      formData.append("document_type_code", meta.document_type_code);
    if (meta?.auto_parse !== undefined)
      formData.append("auto_parse", String(meta.auto_parse));
    if (meta?.group_id) formData.append("group_id", meta.group_id);

    const headers = getAuthHeaders();
    if (meta?.idempotency_key) {
      headers.set("Idempotency-Key", meta.idempotency_key);
    }

    const res = await fetch(`${BASE_URL}/documents/upload`, {
      method: "POST",
      headers,
      body: formData,
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(
        (err as { detail?: string; message?: string }).detail ||
          (err as { message?: string }).message ||
          `Tải lên tài liệu thất bại (HTTP ${res.status}).`,
      );
    }
    return res.json();
  },

  /**
   * Cập nhật thông tin hành chính của tài liệu
   */
  async updateDocument(
    id: string,
    body: RepositoryDocumentUpdate,
  ): Promise<RepositoryDocument> {
    const res = await fetch(`${BASE_URL}/documents/${id}`, {
      method: "PATCH",
      headers: getAuthHeaders({ "Content-Type": "application/json" }),
      body: JSON.stringify(body),
    });
    if (!res.ok) {
      throw new Error(`Cập nhật tài liệu thất bại (HTTP ${res.status}).`);
    }
    return res.json();
  },

  /**
   * Xóa tài liệu khỏi kho tập trung
   */
  async deleteDocument(id: string): Promise<{ deleted: boolean; id: string }> {
    const res = await fetch(`${BASE_URL}/documents/${id}`, {
      method: "DELETE",
      headers: getAuthHeaders(),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(
        (err as { detail?: string }).detail ||
          `Không thể xóa tài liệu (HTTP ${res.status}).`,
      );
    }
    return res.json();
  },

  /**
   * Bóc tách lại văn bản (Reparse)
   */
  async reparseDocument(id: string): Promise<RepositoryDocument> {
    const res = await fetch(`${BASE_URL}/documents/${id}/reparse`, {
      method: "POST",
      headers: getAuthHeaders(),
    });
    if (!res.ok) {
      throw new Error(`Bóc tách lại tài liệu thất bại (HTTP ${res.status}).`);
    }
    return res.json();
  },

  /**
   * Trả về URL tải tệp gốc
   */
  getDownloadUrl(id: string): string {
    return `${BASE_URL}/documents/${id}/download`;
  },

  /**
   * Trả về URL xem trước ảnh trang PDF (nếu là PDF)
   */
  getPreviewPdfUrl(id: string, page = 1): string {
    return `${BASE_URL}/documents/${id}/preview-pdf?page=${page}`;
  },

  /**
   * Gắn danh sách tài liệu từ kho vào một Bộ Sưu Tập Tri Thức
   */
  async attachToCollection(
    collectionId: string,
    request: AttachDocumentsRequest,
  ): Promise<{
    message: string;
    attached_count: number;
    created_documents: Array<{
      id: string;
      title: string;
      chunk_count: number;
      status: string;
    }>;
  }> {
    const res = await fetch(
      `${BASE_URL}/knowledge/collections/${collectionId}/attach-repository-documents`,
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
          `Gắn tài liệu vào kho tri thức thất bại (HTTP ${res.status}).`,
      );
    }
    return res.json();
  },

  /**
   * Lấy danh sách toàn bộ các bản sửa đổi (Revisions) của tài liệu (ADR-011)
   */
  async getRevisions(documentId: string): Promise<DocumentRevisionListItem[]> {
    const res = await fetch(`${BASE_URL}/documents/${documentId}/revisions`, {
      headers: getAuthHeaders(),
    });
    if (!res.ok) {
      throw new Error(
        `Không thể lấy danh sách phiên bản tài liệu (HTTP ${res.status}).`,
      );
    }
    return res.json();
  },

  /**
   * Lấy chi tiết một bản sửa đổi tài liệu (Manifests, Provenance & Quality Gate)
   */
  async getRevision(
    documentId: string,
    revisionId: string,
  ): Promise<DocumentRevision> {
    const res = await fetch(
      `${BASE_URL}/documents/${documentId}/revisions/${revisionId}`,
      {
        headers: getAuthHeaders(),
      },
    );
    if (!res.ok) {
      throw new Error(
        `Không thể lấy chi tiết phiên bản tài liệu (HTTP ${res.status}).`,
      );
    }
    return res.json();
  },

  /**
   * Hiệu đính nội dung Markdown của revision trong giai đoạn thẩm định
   */
  async updateRevisionContent(
    documentId: string,
    revisionId: string,
    parsedMarkdown: string,
    expectedLockVersion: number,
    editReason?: string,
  ): Promise<DocumentRevision> {
    const res = await fetch(
      `${BASE_URL}/documents/${documentId}/revisions/${revisionId}/content`,
      {
        method: "PATCH",
        headers: getAuthHeaders({ "Content-Type": "application/json" }),
        body: JSON.stringify({
          canonical_markdown: parsedMarkdown,
          expected_lock_version: expectedLockVersion,
          notes: editReason,
        }),
      },
    );
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(
        (err as { detail?: string }).detail ||
          `Cập nhật nội dung phiên bản thất bại (HTTP ${res.status}).`,
      );
    }
    return res.json();
  },

  /**
   * Phê duyệt hoặc từ chối bản sửa đổi tài liệu (chuyển trạng thái ready)
   */
  async reviewRevision(
    documentId: string,
    revisionId: string,
    action: "approve" | "reject",
    expectedLockVersion: number,
    reviewNotes?: string,
  ): Promise<DocumentRevision> {
    const res = await fetch(
      `${BASE_URL}/documents/${documentId}/revisions/${revisionId}/review`,
      {
        method: "POST",
        headers: getAuthHeaders({ "Content-Type": "application/json" }),
        body: JSON.stringify({
          action,
          expected_lock_version: expectedLockVersion,
          notes: reviewNotes,
        }),
      },
    );
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(
        (err as { detail?: string }).detail ||
          `Thẩm định phiên bản thất bại (HTTP ${res.status}).`,
      );
    }
    return res.json();
  },

  /**
   * Thử lại quy trình bóc tách và thẩm định chất lượng cho revision
   */
  async retryRevision(
    documentId: string,
    revisionId: string,
    ocrEngine?: string,
  ): Promise<DocumentRevision> {
    const url = new URL(
      `${BASE_URL}/documents/${documentId}/revisions/${revisionId}/retry`,
    );
    if (ocrEngine) url.searchParams.set("ocr_engine", ocrEngine);

    const res = await fetch(url.toString(), {
      method: "POST",
      headers: getAuthHeaders(),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(
        (err as { detail?: string }).detail ||
          `Thử lại bóc tách thất bại (HTTP ${res.status}).`,
      );
    }
    return res.json();
  },

  // =========================================================================
  // Logical Document Groups APIs (Kho Tài Liệu)
  // =========================================================================

  /**
   * Lấy danh sách các kho tài liệu
   */
  async getGroups(params?: {
    search?: string;
    page?: number;
    page_size?: number;
  }): Promise<DocumentGroupListResponse> {
    const searchParams = new URLSearchParams();
    if (params?.search) searchParams.set("search", params.search);
    if (params?.page) searchParams.set("page", String(params.page));
    if (params?.page_size)
      searchParams.set("page_size", String(params.page_size));

    const res = await fetch(
      `${BASE_URL}/documents/groups?${searchParams.toString()}`,
      {
        headers: getAuthHeaders(),
      },
    );
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      const message =
        (err as { detail?: string }).detail ||
        "Không thể tải danh sách kho tài liệu.";
      throw new ApiError(res.status, message, err);
    }
    return res.json();
  },

  /**
   * Chi tiết kho tài liệu
   */
  async getGroup(groupId: string): Promise<DocumentGroup> {
    const res = await fetch(`${BASE_URL}/documents/groups/${groupId}`, {
      headers: getAuthHeaders(),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      const message =
        (err as { detail?: string }).detail ||
        `Không tìm thấy kho tài liệu '${groupId}'.`;
      throw new ApiError(res.status, message, err);
    }
    return res.json();
  },

  /**
   * Tạo kho tài liệu mới
   */
  async createGroup(data: DocumentGroupCreateRequest): Promise<DocumentGroup> {
    const res = await fetch(`${BASE_URL}/documents/groups`, {
      method: "POST",
      headers: {
        ...getAuthHeaders(),
        "Content-Type": "application/json",
      },
      body: JSON.stringify(data),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(
        (err as { detail?: string }).detail || "Tạo kho tài liệu thất bại.",
      );
    }
    return res.json();
  },

  /**
   * Cập nhật thông tin kho tài liệu
   */
  async updateGroup(
    groupId: string,
    data: DocumentGroupUpdateRequest,
  ): Promise<DocumentGroup> {
    const res = await fetch(`${BASE_URL}/documents/groups/${groupId}`, {
      method: "PATCH",
      headers: {
        ...getAuthHeaders(),
        "Content-Type": "application/json",
      },
      body: JSON.stringify(data),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(
        (err as { detail?: string }).detail ||
          "Cập nhật kho tài liệu thất bại.",
      );
    }
    return res.json();
  },

  /**
   * Xóa kho tài liệu
   */
  async deleteGroup(groupId: string): Promise<void> {
    const res = await fetch(`${BASE_URL}/documents/groups/${groupId}`, {
      method: "DELETE",
      headers: getAuthHeaders(),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(
        (err as { detail?: string }).detail || "Xóa kho tài liệu thất bại.",
      );
    }
  },

  /**
   * Lấy danh sách tài liệu trong kho tài liệu
   */
  async getGroupDocuments(
    groupId: string,
    params?: {
      search?: string;
      status?: string;
      page?: number;
      page_size?: number;
    },
  ): Promise<GroupDocumentsResponse> {
    const searchParams = new URLSearchParams();
    if (params?.search) searchParams.set("search", params.search);
    if (params?.status) searchParams.set("status", params.status);
    if (params?.page) searchParams.set("page", String(params.page));
    if (params?.page_size)
      searchParams.set("page_size", String(params.page_size));

    const res = await fetch(
      `${BASE_URL}/documents/groups/${groupId}/documents?${searchParams.toString()}`,
      {
        headers: getAuthHeaders(),
      },
    );
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      const message =
        (err as { detail?: string }).detail ||
        "Không thể tải danh sách tài liệu trong kho.";
      throw new ApiError(res.status, message, err);
    }
    return res.json();
  },

  /**
   * Thêm tài liệu vào kho tài liệu
   */
  async addDocumentsToGroup(
    groupId: string,
    data: AddGroupDocumentsRequest,
  ): Promise<AddGroupDocumentsResponse> {
    const res = await fetch(
      `${BASE_URL}/documents/groups/${groupId}/documents`,
      {
        method: "POST",
        headers: {
          ...getAuthHeaders(),
          "Content-Type": "application/json",
        },
        body: JSON.stringify(data),
      },
    );
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(
        (err as { detail?: string }).detail ||
          "Thêm tài liệu vào kho thất bại.",
      );
    }
    return res.json();
  },

  /**
   * Gỡ một tài liệu khỏi kho tài liệu
   */
  async removeDocumentFromGroup(
    groupId: string,
    documentId: string,
  ): Promise<void> {
    const res = await fetch(
      `${BASE_URL}/documents/groups/${groupId}/documents/${documentId}`,
      {
        method: "DELETE",
        headers: getAuthHeaders(),
      },
    );
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(
        (err as { detail?: string }).detail || "Gỡ tài liệu khỏi kho thất bại.",
      );
    }
  },
};
