import type {
  AttachDocumentsRequest,
  DocumentStats,
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
      throw new Error(`Không tìm thấy tài liệu ID '${id}' (HTTP ${res.status}).`);
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
      throw new Error(`Không thể lấy thống kê kho tài liệu (HTTP ${res.status}).`);
    }
    return res.json();
  },

  /**
   * Tải tài liệu lên Kho Tài Liệu Tập Trung (lưu MinIO + Pre-parsing)
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

    const res = await fetch(`${BASE_URL}/documents/upload`, {
      method: "POST",
      headers: getAuthHeaders(),
      body: formData,
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(
        (err as { detail?: string }).detail ||
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
};
