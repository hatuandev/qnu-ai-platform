import type { DocumentVerificationData } from "@/types/knowledge";
import type { StudioOCRDocument } from "@/types/studio-ocr";

export function mapVerificationDataToStudioDoc(
  data: DocumentVerificationData,
): StudioOCRDocument {
  return {
    revisionId: data.revision_id,
    filename: data.filename,
    totalPages: data.total_pages,
    size: `${data.file_size_mb} MB`,
    provider: "OCR",
    model: data.engine,
    latencyMs: 0,
    status: data.status,
    indexStatus: data.index_status,
    pdfUrl: data.pdf_url,
    pages: data.pages.map((p) => ({
      pageNumber: p.page_number,
      title: `Trang ${p.page_number}`,
      isSigned: p.regions.some((r) => r.type === "signature"),
      hasTable: p.regions.some((r) => r.type === "table"),
      imageUrl: p.image_url || "",
      markdown: p.markdown_content,
      rawText: p.raw_text,
      dimensions: p.dimensions || { width: 0, height: 0 },
      wordCount: p.word_count,
      lineCount: p.line_count,
      regions: p.regions.flatMap((r) => {
        const box = p.bounding_boxes.find((b) => b.id === r.id);
        const coords = r.coordinates || box?.coordinates;
        if (!coords || coords.is_valid === false) return [];
        const pixel = coords.coordinate_system === "pixels";
        if (pixel && (!p.dimensions?.width || !p.dimensions?.height)) return [];
        const x = coords.left ?? coords.x;
        const y = coords.top ?? coords.y;
        if (x === undefined || y === undefined) return [];
        return [
          {
            id: r.id,
            type: r.type,
            label: r.title,
            text: r.details,
            left: pixel ? (x / (p.dimensions?.width || 1)) * 100 : x,
            top: pixel ? (y / (p.dimensions?.height || 1)) * 100 : y,
            width: pixel
              ? (coords.width / (p.dimensions?.width || 1)) * 100
              : coords.width,
            height: pixel
              ? (coords.height / (p.dimensions?.height || 1)) * 100
              : coords.height,
            readingOrder: r.reading_order,
            layoutConfidence: r.layout_confidence ?? null,
            textConfidence: r.text_confidence ?? null,
          },
        ];
      }),
    })),
  };
}
