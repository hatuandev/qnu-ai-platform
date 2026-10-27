import { Badge } from "@/components/ui/badge";
import {
  DEFAULT_RAG_POLICY,
  describeMetadataFilter,
  hasMetadataFilter,
  isDefaultRagPolicy,
  type RagPolicy,
  RETRIEVAL_MODE_LABEL,
  VERIFICATION_MODE_LABEL,
} from "./types";

/**
 * Read-only summary of an assistant's stored RAG policy.
 *
 * A missing policy is shown as the backend default (dense, no context window,
 * verification off) rather than as "unset", because that is how the backend
 * behaves for snapshots created before Context673.
 */
export function RagPolicySummary({ policy }: { policy?: RagPolicy | null }) {
  const value = policy ?? DEFAULT_RAG_POLICY;
  const isDefault = isDefaultRagPolicy(value);

  return (
    <div className="space-y-2.5 text-xs">
      <div className="flex items-center justify-between gap-2">
        <span className="text-muted-foreground">Chế độ truy xuất</span>
        <div className="flex items-center gap-1.5">
          <Badge variant="secondary" className="font-mono text-[11px]">
            {value.retrieval_mode}
          </Badge>
          <span className="text-foreground">
            {RETRIEVAL_MODE_LABEL[value.retrieval_mode]}
          </span>
        </div>
      </div>

      {value.retrieval_mode !== "dense" ? (
        <div className="flex items-center justify-between gap-2">
          <span className="text-muted-foreground">Ứng viên / hằng số RRF</span>
          <span className="font-mono text-foreground">
            {value.candidate_k} / {value.rrf_k}
          </span>
        </div>
      ) : null}

      {value.retrieval_mode === "hybrid_rerank" ? (
        <div className="flex items-center justify-between gap-2">
          <span className="text-muted-foreground">Provider rerank</span>
          <span className="font-mono text-foreground truncate max-w-[60%]">
            {value.rerank_provider_id ?? "không dùng"}
          </span>
        </div>
      ) : null}

      <div className="flex items-center justify-between gap-2">
        <span className="text-muted-foreground">Cửa sổ ngữ cảnh</span>
        <span className="font-mono text-foreground">
          {value.context_window} chunk · {value.context_max_bytes} byte
        </span>
      </div>

      <div className="flex items-center justify-between gap-2">
        <span className="text-muted-foreground">Kiểm chứng</span>
        <div className="flex items-center gap-1.5">
          <Badge
            variant={value.verification_mode === "off" ? "outline" : "warning"}
            className="text-[11px]"
          >
            {value.verification_mode}
          </Badge>
          <span className="text-foreground">
            {VERIFICATION_MODE_LABEL[value.verification_mode]}
          </span>
        </div>
      </div>

      {value.verification_mode !== "off" ? (
        <div className="flex items-center justify-between gap-2">
          <span className="text-muted-foreground">Judge / ngân sách</span>
          <span className="font-mono text-foreground truncate max-w-[60%]">
            {value.verification_provider_id ?? "model chat mặc định"} ·{" "}
            {value.verification_max_output_tokens} token
          </span>
        </div>
      ) : null}

      <div className="flex items-start justify-between gap-2 border-t pt-2">
        <span className="text-muted-foreground">Phạm vi metadata</span>
        <span className="text-right text-foreground">
          {hasMetadataFilter(value.metadata_filter)
            ? describeMetadataFilter(value.metadata_filter)
            : "Không giới hạn"}
        </span>
      </div>

      <p className="pt-1 text-[11px] leading-relaxed text-muted-foreground">
        {isDefault
          ? "Đang dùng cấu hình mặc định tương thích backend (dense, không mở rộng ngữ cảnh, không kiểm chứng)."
          : "Policy được ghim vào snapshot hội thoại. Thay cấu hình chỉ áp dụng cho hội thoại mới; hội thoại đang chạy giữ snapshot cũ."}
      </p>
    </div>
  );
}
