import type {
  ProcessingRunResponse,
  SourceResponse,
  SourceServingState,
  SourceSummaryResponse,
} from "@/api/knowledge/types";

export type KnowledgeDisplayStatus = {
  label: string;
  variant: "default" | "secondary" | "destructive" | "outline";
  hint?: string;
  isReadyForAssistant: boolean;
  servingNote?: string;
};

/**
 * Maps real backend data into user-friendly lifecycle status.
 *
 * Invariants:
 * 1. "Sẵn sàng" ONLY when BE confirms actual serving version matches published.
 * 2. Preparation ready ONLY means the draft is ready for review/editing.
 * 3. Approved does NOT mean published.
 * 4. Published does NOT mean ready until indexed into RAG.
 * 5. When older version is still serving and new revision is preparing, display both.
 */
export function resolveSourceDisplayStatus(
  source: SourceResponse,
  summary?: SourceSummaryResponse | null,
): KnowledgeDisplayStatus {
  const serving: SourceServingState | undefined = summary?.serving;
  const prep = summary?.preparation;
  const processing: ProcessingRunResponse | undefined | null =
    source.processing || summary?.processing_runs?.[0];

  // 1. Check if older revision is actively served while a newer is preparing
  const isOlderServed =
    serving?.served_revision_no &&
    serving.served_revision_no > 0 &&
    source.serving_revision_no > 0;

  let servingNote: string | undefined;
  if (
    isOlderServed &&
    serving?.preparing_revision_no &&
    serving.preparing_revision_no > (serving.served_revision_no ?? 0)
  ) {
    servingNote = `v${serving.served_revision_no} đang phục vụ · v${serving.preparing_revision_no} đang chuẩn bị`;
  }

  // 2. Preparation intent status
  if (prep) {
    if (prep.status === "cancelled") {
      return {
        label: "Đã dừng xử lý",
        variant: "outline",
        hint: "Người dùng đã chủ động dừng lượt chuẩn bị.",
        isReadyForAssistant: false,
        servingNote,
      };
    }
    if (prep.status === "failed") {
      return {
        label: "Có lỗi chuẩn bị",
        variant: "destructive",
        hint: prep.error_code
          ? `Mã lỗi: ${prep.error_code}`
          : "Không thể hoàn tất chuẩn bị nội dung.",
        isReadyForAssistant: false,
        servingNote,
      };
    }
    if (prep.status === "uncertain") {
      return {
        label: "Chưa xác định",
        variant: "outline",
        hint: "Trạng thái không chắc chắn; có thể thử lại.",
        isReadyForAssistant: false,
        servingNote,
      };
    }
    if (
      prep.status === "queued" ||
      prep.status === "waiting_ocr" ||
      prep.status === "compiling"
    ) {
      return {
        label: "Đang chuẩn bị",
        variant: "secondary",
        hint: prep.step || "Đang đọc hiểu văn bản...",
        isReadyForAssistant: false,
        servingNote,
      };
    }
  }

  // 3. OCR Processing status
  if (processing) {
    if (processing.status === "running" || processing.status === "queued") {
      return {
        label: "Đang bóc tách",
        variant: "secondary",
        hint: "Đang trích xuất văn bản từ tệp gốc...",
        isReadyForAssistant: false,
        servingNote,
      };
    }
    if (processing.status === "failed") {
      return {
        label: "Cần kiểm tra",
        variant: "destructive",
        hint: processing.error_code
          ? `Lỗi bóc tách: ${processing.error_code}`
          : "Trích xuất thất bại.",
        isReadyForAssistant: false,
        servingNote,
      };
    }
  }

  // 4. Derivation & Serving checks from summary
  if (summary?.derivations && summary.derivations.length > 0) {
    const servingDerivation = summary.derivations.find((d) => d.is_serving);
    if (servingDerivation && servingDerivation.readiness?.status === "ready") {
      return {
        label: "Sẵn sàng",
        variant: "default",
        hint: "Đã phát hành và sẵn sàng cho Trợ lý AI hỏi đáp.",
        isReadyForAssistant: true,
        servingNote,
      };
    }

    const latestDerivation = summary.derivations[0];
    if (latestDerivation.version) {
      const vStatus = latestDerivation.version.status;
      if (vStatus === "published") {
        return {
          label: "Đang đưa vào hỏi đáp",
          variant: "secondary",
          hint: "Đã phát hành, đang đồng bộ chỉ mục tìm kiếm.",
          isReadyForAssistant: false,
          servingNote,
        };
      }
      if (vStatus === "approved") {
        return {
          label: "Đã duyệt",
          variant: "outline",
          hint: "Đã được phê duyệt, chờ quản trị viên phát hành.",
          isReadyForAssistant: false,
          servingNote,
        };
      }
    }

    if (processing?.status === "completed_with_warnings") {
      return {
        label: "Có cảnh báo ảnh",
        variant: "outline",
        hint: "Một số ảnh trong tệp chưa đọc được; phần văn bản còn lại vẫn dùng được. Cần đọc lại hoặc quản trị viên xác nhận trước khi xuất bản.",
        isReadyForAssistant: false,
        servingNote,
      };
    }

    if (
      latestDerivation.compilation_status === "completed" ||
      prep?.status === "ready"
    ) {
      return {
        label: "Bản nháp sẵn sàng",
        variant: "outline",
        hint: "Bản chuẩn bị đã sẵn sàng để xem và chỉnh sửa.",
        isReadyForAssistant: false,
        servingNote,
      };
    }
  }

  // 5. Fallback when no derivations exist yet
  if (processing?.status === "completed_with_warnings") {
    return {
      label: "Đã bóc tách, có cảnh báo",
      variant: "outline",
      hint: "Đã bóc tách nội dung thô nhưng còn ảnh chưa đọc được. Cần đọc lại hoặc quản trị viên xác nhận trước khi xuất bản.",
      isReadyForAssistant: false,
      servingNote,
    };
  }

  if (processing?.status === "completed") {
    return {
      label: "Đã bóc tách",
      variant: "secondary",
      hint: "Đã bóc tách nội dung thô, sẵn sàng để chuẩn bị bản biên soạn.",
      isReadyForAssistant: false,
      servingNote,
    };
  }

  if (source.status === "stored") {
    return {
      label: "Đã tải lên",
      variant: "secondary",
      hint: "Tệp đã lưu an toàn trong kho.",
      isReadyForAssistant: false,
      servingNote,
    };
  }

  return {
    label: source.status || "Chờ xử lý",
    variant: "secondary",
    isReadyForAssistant: false,
    servingNote,
  };
}
