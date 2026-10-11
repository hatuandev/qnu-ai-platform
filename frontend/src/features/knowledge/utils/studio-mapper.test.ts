import assert from "node:assert/strict";
import { describe, test } from "node:test";
import type { DocumentVerificationData } from "@/types/knowledge";
import { mapVerificationDataToStudioDoc } from "./studio-mapper";

function fixture(): DocumentVerificationData {
  return {
    document_id: "source",
    revision_id: "revision",
    collection_id: "col",
    title: "Test",
    filename: "test.pdf",
    file_size_mb: 1,
    total_pages: 1,
    engine: "ocr",
    total_chars: 4,
    estimated_chunks: 0,
    pages: [
      {
        page_number: 1,
        word_count: 1,
        line_count: 1,
        markdown_content: "Test",
        raw_text: "Test",
        dimensions: { width: 1200, height: 1600 },
        bounding_boxes: [
          {
            id: "box",
            page_number: 1,
            type: "text",
            label: "Text",
            confidence: 0,
            coordinates: {
              left: 20,
              top: 35,
              width: 45,
              height: 6,
              coordinate_system: "normalized_percent",
            },
            content_snippet: "Test",
          },
        ],
        regions: [
          {
            id: "box",
            page_number: 1,
            title: "Region",
            type: "text",
            confidence: 0,
            reading_order: 0,
            details: "Full contents",
            layout_confidence: null,
            text_confidence: null,
          },
        ],
      },
    ],
  };
}
describe("Studio preserves backend layout", () => {
  test("left/top percentages and full region content are not rewritten", () => {
    const doc = mapVerificationDataToStudioDoc(fixture());
    assert.equal(doc.revisionId, "revision");
    assert.deepEqual(doc.pages[0].regions[0], {
      id: "box",
      type: "text",
      label: "Region",
      left: 20,
      top: 35,
      width: 45,
      height: 6,
      text: "Full contents",
      readingOrder: 0,
      layoutConfidence: null,
      textConfidence: null,
    });
  });
  test("pixel coordinates below 100 still use actual dimensions", () => {
    const data = fixture();
    data.pages[0].bounding_boxes[0].coordinates = {
      left: 60,
      top: 80,
      width: 120,
      height: 160,
      coordinate_system: "pixels",
    };
    const { left, top, width, height } =
      mapVerificationDataToStudioDoc(data).pages[0].regions[0];
    assert.deepEqual(
      { left, top, width, height },
      { left: 5, top: 5, width: 10, height: 10 },
    );
  });
  test("invalid coordinates do not produce invented boxes", () => {
    const data = fixture();
    data.pages[0].bounding_boxes[0].coordinates.is_valid = false;
    assert.equal(
      mapVerificationDataToStudioDoc(data).pages[0].regions.length,
      0,
    );
  });
});
