import assert from "node:assert/strict";
import test from "node:test";
import type { CompilationDraftResponse } from "../api/compilation/types";
import type {
  SourcePreparationSummary,
  SourceResponse,
} from "../api/knowledge/types";
import {
  buildCitationMap,
  findViewedDerivation,
  parseCitationLocation,
  resolveStudioAction,
} from "./knowledge-studio-helpers.ts";

test("citation location comes from canonical metadata, never an evidence-key guess", () => {
  assert.equal(parseCitationLocation("ocr_test:ev_p012_b005"), undefined);
  assert.equal(
    parseCitationLocation({ page: 12, source_locator: { format: "pdf" } }),
    "Trang 12",
  );
  assert.equal(
    parseCitationLocation({ page: 1, source_locator: { format: "docx" } }),
    "Vị trí trong tài liệu Word",
  );
  assert.equal(
    parseCitationLocation({ pagination: "document", page: 1 }),
    "Vị trí trong tài liệu Word",
  );
  assert.equal(parseCitationLocation({ page: 0 }), undefined);
  assert.equal(parseCitationLocation(null), undefined);
});

test("buildCitationMap assigns sequential stable indices and deduplicates keys", () => {
  const mockDraft: CompilationDraftResponse = {
    title: "Tài liệu tuyển sinh 2026",
    sections: [
      {
        heading: "Thông tin chung",
        paragraphs: [
          {
            text: "Đoạn 1",
            citations: ["ev_p001_b001", "ev_p001_b002", "ev_p001_b001"], // Duplicate in same paragraph
          },
          {
            text: "Đoạn 2",
            citations: ["ev_p002_b001", "ev_p001_b002"], // Cross-paragraph repeated key
          },
        ],
      },
      {
        heading: "Phương thức xét tuyển",
        paragraphs: [
          {
            text: "Đoạn 3",
            citations: ["ev_p003_b001"],
          },
        ],
      },
    ],
    source_tables: [
      {
        citation: "ev_p004_b001",
        table: {
          rows: [
            [
              {
                text: "Chỉ tiêu",
                header: true,
                row_span: 1,
                col_span: 1,
              },
            ],
          ],
        },
      },
    ],
    unknowns: [],
    schema_version: "v1",
    compilation_run_id: "cmp_test",
    publication_status: "draft",
    requires_review: true,
    topic: "general",
    citations: {
      ev_p001_b001: {
        page: 1,
        source_id: "src_word",
        revision_id: "rev_word",
        source_locator: { format: "docx" },
      },
      ev_p004_b001: { page: 4, source_id: "src_pdf", revision_id: "rev_pdf" },
    },
    sources: [],
  };

  const map = buildCitationMap(mockDraft);

  // Total unique citations: 5
  assert.equal(map.size, 5);

  // Sequential order preserved
  assert.equal(map.get("ev_p001_b001")?.index, 1);
  assert.equal(map.get("ev_p001_b001")?.location, "Vị trí trong tài liệu Word");

  assert.equal(map.get("ev_p001_b002")?.index, 2);
  assert.equal(map.get("ev_p001_b002")?.location, undefined);

  assert.equal(map.get("ev_p002_b001")?.index, 3);
  assert.equal(map.get("ev_p002_b001")?.location, undefined);

  assert.equal(map.get("ev_p003_b001")?.index, 4);
  assert.equal(map.get("ev_p003_b001")?.location, undefined);

  // Table citation is continuation
  assert.equal(map.get("ev_p004_b001")?.index, 5);
  assert.equal(map.get("ev_p004_b001")?.location, "Trang 4");
});

test("resolveStudioAction handles lifecycle transitions cleanly", () => {
  const baseSource: SourceResponse = {
    id: "src_1",
    workspace_id: "ws_1",
    collection_id: "col_1",
    folder_id: null,
    title: "Quy chế đào tạo",
    status: "ready",
    revision_count: 1,
    current_revision_no: 1,
    serving_revision_no: 1,
    file_name: "quy_che.docx",
    content_type:
      "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    size_bytes: 50000,
    sha256: "abc",
    created_by: "user_1",
    created_at: "2026-11-10T00:00:00Z",
    updated_at: "2026-11-10T00:00:00Z",
  };

  // Case 1: Active editing
  const editingRes = resolveStudioAction({
    source: baseSource,
    hasDraft: true,
    isEditing: true,
  });
  assert.equal(editingRes.primaryAction, "save_edits");
  assert.equal(editingRes.canEdit, false);

  // Case 2: Actively running preparation
  const prepIntent: SourcePreparationSummary = {
    intent_id: "int_1",
    status: "compiling",
    step: "Đang đọc hiểu văn bản...",
  };
  const preparingRes = resolveStudioAction({
    source: baseSource,
    intentSummary: prepIntent,
    hasDraft: false,
    isEditing: false,
  });
  assert.equal(preparingRes.primaryAction, "cancel_prep");
  assert.equal(preparingRes.canEdit, false);

  // Case 3: No draft and not running
  const noDraftRes = resolveStudioAction({
    source: baseSource,
    hasDraft: false,
    isEditing: false,
  });
  assert.equal(noDraftRes.primaryAction, "prepare");
  assert.equal(noDraftRes.canEdit, false);

  // Case 4: Draft exists, unapproved
  const unapprovedRes = resolveStudioAction({
    source: baseSource,
    hasDraft: true,
    isEditing: false,
    currentDerivation: {
      compilation_run_id: "cmp_1",
      compilation_generation: 1,
      compilation_status: "completed",
      origin: "auto",
      ocr_run_id: "ocr_1",
      ocr_generation: 1,
      is_serving: false,
    },
  });
  assert.equal(unapprovedRes.primaryAction, "approve");
  assert.equal(unapprovedRes.canEdit, true);

  // Case 5: Approved, pending publication
  const approvedRes = resolveStudioAction({
    source: baseSource,
    hasDraft: true,
    isEditing: false,
    currentDerivation: {
      compilation_run_id: "cmp_1",
      compilation_generation: 1,
      compilation_status: "completed",
      origin: "auto",
      ocr_run_id: "ocr_1",
      ocr_generation: 1,
      version: {
        version_id: "ver_1",
        version_no: 1,
        state_version: 1,
        status: "approved",
        bundle_sha256: "sha1",
        document_id: "doc_1",
        document_title: "Quy chế đào tạo",
      },
      is_serving: false,
    },
  });
  assert.equal(approvedRes.primaryAction, "publish");
  assert.equal(approvedRes.canEdit, true);

  // Case 6: Published, syncing index
  const syncingRes = resolveStudioAction({
    source: baseSource,
    hasDraft: true,
    isEditing: false,
    currentDerivation: {
      compilation_run_id: "cmp_1",
      compilation_generation: 1,
      compilation_status: "completed",
      origin: "auto",
      ocr_run_id: "ocr_1",
      ocr_generation: 1,
      version: {
        version_id: "ver_1",
        version_no: 1,
        state_version: 1,
        status: "published",
        bundle_sha256: "sha1",
        document_id: "doc_1",
        document_title: "Quy chế đào tạo",
      },
      is_serving: false,
    },
  });
  assert.equal(syncingRes.primaryAction, "syncing");
  assert.equal(syncingRes.canEdit, true);

  // Case 7: Actively serving in RAG
  const servedRes = resolveStudioAction({
    source: baseSource,
    hasDraft: true,
    isEditing: false,
    currentDerivation: {
      compilation_run_id: "cmp_1",
      compilation_generation: 1,
      compilation_status: "completed",
      origin: "auto",
      ocr_run_id: "ocr_1",
      ocr_generation: 1,
      version: {
        version_id: "ver_1",
        version_no: 1,
        state_version: 1,
        status: "published",
        bundle_sha256: "sha1",
        document_id: "doc_1",
        document_title: "Quy chế đào tạo",
      },
      readiness: {
        status: "ready",
      },
      is_serving: true,
    },
  });
  assert.equal(servedRes.primaryAction, "served");
  assert.equal(servedRes.canEdit, true);
});

test("a newly edited run never inherits the old serving derivation", () => {
  const old = {
    compilation_run_id: "cmp_old",
    is_serving: true,
    readiness: { status: "ready" },
  } as import("../api/knowledge/types").SourceDerivation;
  assert.equal(findViewedDerivation([old], "cmp_child"), null);
  assert.equal(findViewedDerivation([old], "cmp_old"), old);
  const result = resolveStudioAction({
    hasDraft: true,
    isEditing: false,
    currentDerivation: findViewedDerivation([old], "cmp_child"),
  });
  assert.equal(result.primaryAction, "approve");
  assert.equal(result.displayStatus.label, "Bản nháp");
  assert.equal(result.displayStatus.isReadyForAssistant, false);
});
