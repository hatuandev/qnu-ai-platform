import { Link } from "@tanstack/react-router";
import { AlertTriangle, ArrowRight, Layers } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import type { IndexReadiness } from "./index-types";
import type { VersionResponse } from "./publication-types";

type VersionRef = Pick<VersionResponse, "id" | "version_no" | "status">;

type ServingSummary = {
  prepared_version: VersionRef | null;
  published_version: VersionRef | null;
  served_version: VersionRef | null;
  readiness: Pick<IndexReadiness, "status">;
};

export type ServingReference = {
  version: VersionRef | null;
  detail: string;
};

export type ServingReferences = {
  prepared: ServingReference;
  published: ServingReference;
  served: ServingReference;
  warning: string | null;
};

export function describeServingReferences(
  summary: ServingSummary | undefined,
): ServingReferences | null {
  if (!summary) return null;
  const { prepared_version: prepared } = summary;
  const { published_version: published } = summary;
  const { served_version: served } = summary;

  const servedDetail = served
    ? "Chỉ mục hoạt động đang khớp đúng phiên bản này."
    : summary.readiness.status === "outdated"
      ? "Chỉ mục chưa khớp bản xuất bản hiện tại."
      : summary.readiness.status === "not_indexed"
        ? "Chưa có chỉ mục hoạt động."
        : summary.readiness.status === "unavailable"
          ? "Không xác minh được chỉ mục cho tài liệu này."
          : "Không xác định được phiên bản đang phục vụ.";

  let warning: string | null = null;
  if (published && served && served.id !== published.id) {
    warning = `Trợ lý AI đang phục vụ bản v${served.version_no}; bản xuất bản v${published.version_no} chưa được đưa vào chỉ mục.`;
  } else if (published && !served) {
    warning =
      "Bản xuất bản chưa được xác nhận là bản đang phục vụ. Trợ lý AI có thể tạm ngừng trả lời từ tài liệu này cho đến khi chỉ mục cập nhật.";
  }

  return {
    prepared: {
      version: prepared,
      detail: prepared
        ? prepared.status === "approved"
          ? "Đã duyệt · chờ xuất bản."
          : "Bản nháp · chưa được duyệt để xuất bản."
        : "Không có bản nháp hoặc bản đã duyệt đang chờ.",
    },
    published: {
      version: published,
      detail: published
        ? "Phiên bản theo quyết định xuất bản hiện tại."
        : "Tài liệu chưa có phiên bản xuất bản.",
    },
    served: { version: served, detail: servedDetail },
    warning,
  };
}

function ReferenceItem({
  label,
  reference,
  workspaceId,
  collectionId,
  documentId,
}: {
  label: string;
  reference: ServingReference;
  workspaceId: string;
  collectionId: string;
  documentId: string;
}) {
  return (
    <div className="space-y-1.5 rounded-lg border border-border/60 bg-muted/10 p-3">
      <span className="text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
        {label}
      </span>
      <div className="flex min-h-6 flex-wrap items-center gap-2">
        {reference.version ? (
          <>
            <Badge variant="outline" className="font-mono text-xs">
              v{reference.version.version_no}
            </Badge>
            <Link
              to="/workspaces/$workspaceId/collections/$collectionId/documents/$documentId/versions/$versionId"
              params={{
                workspaceId,
                collectionId,
                documentId,
                versionId: reference.version.id,
              }}
              className="inline-flex items-center gap-1 text-[11px] text-primary hover:underline"
            >
              <span>Mở</span>
              <ArrowRight className="size-3" />
            </Link>
          </>
        ) : (
          <span className="text-xs text-muted-foreground">Chưa có</span>
        )}
      </div>
      <p className="text-[11px] leading-relaxed text-muted-foreground">
        {reference.detail}
      </p>
    </div>
  );
}

export function ServingReferencesCard({
  summary,
  workspaceId,
  collectionId,
  documentId,
}: {
  summary: ServingSummary | undefined;
  workspaceId: string;
  collectionId: string;
  documentId: string;
}) {
  const references = describeServingReferences(summary);
  if (!references) return null;
  return (
    <Card className="rounded-xl shadow-2xs">
      <CardContent className="space-y-3 p-4">
        <div className="flex items-center gap-2">
          <Layers className="size-4 text-primary" />
          <h2 className="text-sm font-semibold">Tham chiếu phục vụ</h2>
        </div>
        <div className="grid gap-3 sm:grid-cols-3">
          <ReferenceItem
            label="Bản chuẩn bị"
            reference={references.prepared}
            workspaceId={workspaceId}
            collectionId={collectionId}
            documentId={documentId}
          />
          <ReferenceItem
            label="Bản đã xuất bản"
            reference={references.published}
            workspaceId={workspaceId}
            collectionId={collectionId}
            documentId={documentId}
          />
          <ReferenceItem
            label="Bản đang phục vụ"
            reference={references.served}
            workspaceId={workspaceId}
            collectionId={collectionId}
            documentId={documentId}
          />
        </div>
        {references.warning ? (
          <p
            role="status"
            className="flex items-start gap-1.5 rounded-md border border-warning/40 bg-warning/10 px-2.5 py-2 text-[11px] leading-relaxed text-foreground"
          >
            <AlertTriangle className="mt-0.5 size-3.5 shrink-0 text-warning" />
            <span>{references.warning}</span>
          </p>
        ) : null}
      </CardContent>
    </Card>
  );
}
