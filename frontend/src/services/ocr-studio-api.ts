import type {
  DocumentBoundingBox,
  DocumentChunkItem,
  DocumentRegion,
  DocumentVerificationData,
} from "@/types/knowledge";
import type { StudioOCRDocument } from "@/types/studio-ocr";
import { BASE_URL } from "./http-client";
import { knowledgeApi } from "./knowledge-api";
import { MOCK_VERIFICATION_DOCUMENT } from "./verification-data";

export const ocrStudioApi = {
  /**
   * Lấy dữ liệu đối soát tài liệu bóc tách (Bounding Boxes, Regions, Pages, Markdown).
   * Phân biệt rõ ràng giữa tài liệu mẫu (doc_ts_2026) và các tài liệu người dùng tải lên thực tế.
   */
  async getStudioView(
    docId: string,
    refreshLayout = false,
  ): Promise<DocumentVerificationData> {
    const url = refreshLayout
      ? `${BASE_URL}/knowledge/documents/${docId}/studio-view?refresh_layout=true`
      : `${BASE_URL}/knowledge/documents/${docId}/studio-view`;
    const res = await fetch(url);
    if (!res.ok) {
      throw new Error(`Không tải được studio-view (HTTP ${res.status}).`);
    }
    const v = (await res.json()) as {
      document_id: string;
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
        bounding_boxes: DocumentBoundingBox[];
        regions: DocumentRegion[];
      }[];
    };
    const totalChars = v.pages.reduce(
      (sum, p) => sum + p.markdown_content.length,
      0,
    );
    const sizeBytes =
      typeof v.file_size_bytes === "number" ? v.file_size_bytes : 0;
    return {
      document_id: v.document_id,
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
        markdown_content: p.markdown_content,
        raw_text: p.raw_text,
        bounding_boxes: p.bounding_boxes || [],
        regions: p.regions || [],
      })),
    };
  },

  async getDocumentVerification(
    docId: string,
    refreshLayout = false,
  ): Promise<DocumentVerificationData> {
    // Legacy demo document keeps its hand-written studio fixture.
    if (docId === MOCK_VERIFICATION_DOCUMENT.document_id) {
      return Promise.resolve(MOCK_VERIFICATION_DOCUMENT);
    }
    // Real documents: prefer studio-view (markdown + real boxes + page images),
    // fall back to chunk mapping when the backend lacks stored geometry.
    try {
      return await this.getStudioView(docId, refreshLayout);
    } catch {
      // Fall through to chunk mapping below.
    }
    // Chunk mapping fallback (no invention — per AGENTS.md 8.7/8.9,
    // never fabricate pages, boxes or word counts).
    const detail = await knowledgeApi.getDocumentDetail(docId);
    const byPage = new Map<number, DocumentChunkItem[]>();
    for (const chunk of detail.chunks) {
      const pageNumber =
        chunk.page_number && chunk.page_number > 0 ? chunk.page_number : 1;
      const group = byPage.get(pageNumber) || [];
      group.push(chunk);
      byPage.set(pageNumber, group);
    }
    const pageNumbers = [...byPage.keys()].sort((a, b) => a - b);
    const totalChars = detail.chunks.reduce(
      (sum, c) => sum + c.content.length,
      0,
    );
    const engine =
      (detail.doc_metadata.ocr_method as string) ||
      detail.ocr_method ||
      "PyMuPdfParser";
    return {
      document_id: detail.id,
      collection_id: detail.collection_id,
      title: detail.title,
      filename: detail.filename,
      status: detail.status,
      index_status: detail.index_status,
      file_size_mb: Math.round((detail.file_size / 1048576) * 100) / 100,
      total_pages: Math.max(pageNumbers.length, 1),
      engine,
      total_chars: totalChars,
      estimated_chunks: detail.chunks.length,
      pages: (pageNumbers.length > 0 ? pageNumbers : [1]).map((pageNumber) => {
        const group = (byPage.get(pageNumber) || []).sort(
          (a, b) => a.chunk_index - b.chunk_index,
        );
        const markdown = group.map((c) => c.content).join("\n\n");
        return {
          page_number: pageNumber,
          word_count: markdown.trim() ? markdown.trim().split(/\s+/).length : 0,
          line_count: markdown ? markdown.split("\n").length : 0,
          image_url: undefined,
          markdown_content: markdown,
          raw_text: markdown,
          bounding_boxes: [],
          regions: [],
        };
      }),
    };
  },

  /**
   * Phê duyệt tài liệu: gửi bản sửa tay lên backend để nạp Vector DB thật.
   */
  async saveDocumentVerification(
    docId: string,
    payload: { pages: { page_number: number; markdown_content: string }[] },
  ): Promise<{
    success: boolean;
    vector_status: string;
    total_chunks: number;
  }> {
    // Legacy demo document keeps its in-memory fixture behavior.
    if (docId === MOCK_VERIFICATION_DOCUMENT.document_id) {
      for (const p of payload.pages) {
        const targetPage = MOCK_VERIFICATION_DOCUMENT.pages.find(
          (mp) => mp.page_number === p.page_number,
        );
        if (targetPage) {
          targetPage.markdown_content = p.markdown_content;
        }
      }
      return Promise.resolve({
        success: true,
        vector_status: "ready_for_indexing",
        total_chunks: MOCK_VERIFICATION_DOCUMENT.estimated_chunks,
      });
    }
    const result = await knowledgeApi.approveDocument(docId, payload.pages);
    return Promise.resolve({
      success: true,
      vector_status:
        result.indexed_chunks > 0 ? "indexed" : "approved_pending_index",
      total_chunks: result.total_chunks,
    });
  },

  /**
   * Bóc tách tức thì tệp scan trên Studio OCR Sandbox.
   */
  async parseStudioOcr(
    file: File | null,
    engineId?: string,
  ): Promise<StudioOCRDocument> {
    const formData = new FormData();
    if (file) {
      formData.append("file", file);
    }
    if (engineId) {
      formData.append("engine_id", engineId);
    }
    const res = await fetch(`${BASE_URL}/ocr/studio/parse`, {
      method: "POST",
      body: formData,
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(
        err.detail || `Lỗi bóc tách OCR Studio (HTTP ${res.status})`,
      );
    }
    return res.json();
  },

  /**
   * Lấy dữ liệu 14 trang tài liệu scan tuyển sinh mẫu để kiểm thử ngay lập tức.
   */
  async getStudioSampleDocument(): Promise<StudioOCRDocument> {
    const res = await fetch(`${BASE_URL}/ocr/studio/sample`);
    if (!res.ok) {
      throw new Error(`Không tải được tài liệu mẫu (HTTP ${res.status})`);
    }
    return res.json();
  },
};
