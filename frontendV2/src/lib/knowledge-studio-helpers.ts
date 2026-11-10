import type { CompilationDraftResponse } from "../api/compilation/types";
import type {
  SourceDerivation,
  SourcePreparationSummary,
  SourceResponse,
  SourceSummaryResponse,
} from "../api/knowledge/types";
import {
  type KnowledgeDisplayStatus,
  resolveSourceDisplayStatus,
} from "./knowledge-status.ts";

export type CitationInfo = {
  index: number;
  rawKey: string;
  location?: string;
  sourceId?: string;
  revisionId?: string;
};

/** Use canonical locators; evidence keys are opaque and do not prove pagination. */
function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === "object"
    ? (value as Record<string, unknown>)
    : {};
}

export function parseCitationLocation(value: unknown): string | undefined {
  const citation = asRecord(value);
  const locator = asRecord(citation.source_locator);
  if (locator.format === "docx" || citation.pagination === "document") {
    return "Vị trí trong tài liệu Word";
  }
  const page = citation.page;
  return typeof page === "number" && Number.isInteger(page) && page > 0
    ? `Trang ${page}`
    : undefined;
}

export function findViewedDerivation(
  derivations: SourceDerivation[] | undefined,
  runId: string | null | undefined,
): SourceDerivation | null {
  return derivations?.find((item) => item.compilation_run_id === runId) ?? null;
}

export function displayDocumentTitle(title: string): string {
  return title.replace(/_/g, " ").replace(/\s+/g, " ").trim();
}

/**
 * Builds a deterministic sequential mapping from raw citation keys to 1-based citation numbers.
 * The order is determined by first appearance in draft sections and then source tables.
 */
export function buildCitationMap(
  draft?: CompilationDraftResponse | null,
): Map<string, CitationInfo> {
  const map = new Map<string, CitationInfo>();
  if (!draft) return map;

  let counter = 1;

  for (const section of draft.sections || []) {
    for (const p of section.paragraphs || []) {
      for (const cit of p.citations || []) {
        if (cit && !map.has(cit)) {
          map.set(cit, {
            index: counter++,
            rawKey: cit,
            location: parseCitationLocation(draft.citations?.[cit]),
            sourceId: asRecord(draft.citations?.[cit]).source_id as
              | string
              | undefined,
            revisionId: asRecord(draft.citations?.[cit]).revision_id as
              | string
              | undefined,
          });
        }
      }
    }
  }

  for (const tbl of draft.source_tables || []) {
    if (tbl.citation && !map.has(tbl.citation)) {
      map.set(tbl.citation, {
        index: counter++,
        rawKey: tbl.citation,
        location: parseCitationLocation(draft.citations?.[tbl.citation]),
        sourceId: asRecord(draft.citations?.[tbl.citation]).source_id as
          | string
          | undefined,
        revisionId: asRecord(draft.citations?.[tbl.citation]).revision_id as
          | string
          | undefined,
      });
    }
  }

  return map;
}

export type StudioPrimaryActionType =
  | "prepare" // Chuẩn bị nội dung
  | "cancel_prep" // Dừng xử lý
  | "save_edits" // Lưu thay đổi
  | "approve" // Duyệt
  | "publish" // Phát hành
  | "syncing" // Đang đồng bộ chỉ mục
  | "served"; // Sẵn sàng phục vụ

export type StudioActionState = {
  primaryAction: StudioPrimaryActionType;
  canEdit: boolean;
  displayStatus: KnowledgeDisplayStatus;
};

/**
 * Determines the single primary action and edit availability for the currently viewed document/derivation.
 * Invariants:
 * 1. Prioritize active edit mode first.
 * 2. If actively preparing, allow cancel if permitted.
 * 3. Distinguish between the currently viewed derivation and general source serving state.
 * 4. If the viewed derivation is already serving and ready, do NOT prompt to re-approve the same version.
 */
export function resolveStudioAction({
  source,
  summary,
  intentSummary,
  hasDraft,
  isEditing,
  currentDerivation,
}: {
  source?: SourceResponse | null;
  summary?: SourceSummaryResponse | null;
  intentSummary?: SourcePreparationSummary | null;
  hasDraft: boolean;
  isEditing: boolean;
  currentDerivation?: SourceDerivation | null;
}): StudioActionState {
  let displayStatus: KnowledgeDisplayStatus = source
    ? resolveSourceDisplayStatus(source, summary)
    : {
        label: "Đang tải",
        variant: "secondary",
        isReadyForAssistant: false,
      };

  if (hasDraft) {
    const ready =
      currentDerivation?.is_serving &&
      currentDerivation.readiness?.status === "ready";
    const status = currentDerivation?.version?.status;
    displayStatus = {
      label: ready
        ? "Sẵn sàng phục vụ"
        : status === "published"
          ? "Đã phát hành"
          : status === "approved"
            ? "Đã duyệt"
            : "Bản nháp",
      variant: ready ? "default" : "secondary",
      isReadyForAssistant: Boolean(ready),
      servingNote:
        !ready && summary?.serving?.served_version_id
          ? "Bản trước vẫn đang phục vụ"
          : undefined,
    };
  }

  // 1. In edit mode -> primary action is Save
  if (isEditing) {
    return {
      primaryAction: "save_edits",
      canEdit: false,
      displayStatus,
    };
  }

  // 2. Preparation is actively running
  const isPreparing =
    intentSummary?.status === "queued" ||
    intentSummary?.status === "waiting_ocr" ||
    intentSummary?.status === "compiling";

  if (isPreparing) {
    return {
      primaryAction: "cancel_prep",
      canEdit: false,
      displayStatus,
    };
  }

  // 3. No draft and not running -> trigger preparation
  if (!hasDraft) {
    return {
      primaryAction: "prepare",
      canEdit: false,
      displayStatus,
    };
  }

  // 4. Draft exists -> determine derivation state
  if (currentDerivation) {
    // 4A. Actively serving and ready in RAG
    if (
      currentDerivation.is_serving &&
      currentDerivation.readiness?.status === "ready"
    ) {
      return {
        primaryAction: "served",
        canEdit: true,
        displayStatus,
      };
    }

    // 4B. Published but still syncing index
    if (currentDerivation.version?.status === "published") {
      return {
        primaryAction: "syncing",
        canEdit: true,
        displayStatus,
      };
    }

    // 4C. Approved, ready for publication
    if (currentDerivation.version?.status === "approved") {
      return {
        primaryAction: "publish",
        canEdit: true,
        displayStatus,
      };
    }
  }

  // 4D. Default draft ready for approval & editing
  return {
    primaryAction: "approve",
    canEdit: true,
    displayStatus,
  };
}
