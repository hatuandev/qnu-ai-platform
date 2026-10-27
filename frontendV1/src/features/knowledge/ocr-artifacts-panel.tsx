import {
  Check,
  Code,
  Copy,
  FileCheck,
  FileCode,
  FileText,
  Layers,
  Loader2,
  ShieldCheck,
} from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";
import { ApiProblemError, v1Client } from "@/app/api/v1";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  useRunEvidenceQuery,
  useRunManifestQuery,
} from "@/features/knowledge/ocr-queries";
import {
  readRunDocumentBlob,
  readRunMarkdownBlob,
} from "@/features/knowledge/ocr-requests";
import { formatOcrError } from "@/features/knowledge/ocr-schemas";
import type { ProcessingRunResponse } from "@/features/knowledge/ocr-types";

export function OcrArtifactsPanel({
  workspaceId,
  collectionId,
  sourceId,
  revisionId,
  run,
}: {
  workspaceId: string;
  collectionId: string;
  sourceId: string;
  revisionId: string;
  run: ProcessingRunResponse;
}) {
  const [activeTab, setActiveTab] = useState<string>("manifest");
  const [downloadingType, setDownloadingType] = useState<"doc" | "md" | null>(
    null,
  );
  const [copiedKey, setCopiedKey] = useState<string | null>(null);

  const manifestQuery = useRunManifestQuery(
    workspaceId,
    collectionId,
    sourceId,
    revisionId,
    run.id,
    { enabled: activeTab === "manifest" },
  );

  const evidenceQuery = useRunEvidenceQuery(
    workspaceId,
    collectionId,
    sourceId,
    revisionId,
    run.id,
    { enabled: activeTab === "evidence" },
  );

  const handleCopyText = async (text: string, key: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopiedKey(key);
      toast.success("Đã sao chép vào bộ nhớ tạm.");
      setTimeout(() => setCopiedKey(null), 2000);
    } catch {
      toast.error("Không thể sao chép.");
    }
  };

  const handleDownloadFile = async (type: "doc" | "md") => {
    setDownloadingType(type);
    try {
      const res =
        type === "doc"
          ? await readRunDocumentBlob(
              v1Client,
              workspaceId,
              collectionId,
              sourceId,
              revisionId,
              run.id,
            )
          : await readRunMarkdownBlob(
              v1Client,
              workspaceId,
              collectionId,
              sourceId,
              revisionId,
              run.id,
            );

      const downloadUrl = URL.createObjectURL(res.blob);
      const a = document.createElement("a");
      a.href = downloadUrl;
      a.download =
        res.fileName ||
        `run_${run.id}_${type === "doc" ? "canonical.json" : "ocr.md"}`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      setTimeout(() => URL.revokeObjectURL(downloadUrl), 5000);
      toast.success(
        `Đã tải ${type === "doc" ? "Canonical JSON" : "Markdown dẫn xuất"}.`,
      );
    } catch (error: unknown) {
      if (error instanceof ApiProblemError) {
        toast.error(formatOcrError(error.code, error.message));
      } else {
        toast.error("Không thể tải tệp artifact.");
      }
    } finally {
      setDownloadingType(null);
    }
  };

  return (
    <div className="space-y-4">
      {/* Overview Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 text-xs">
        <Card className="rounded-xl shadow-2xs">
          <CardContent className="p-3 space-y-1">
            <span className="text-muted-foreground">Config Fingerprint</span>
            <div className="flex items-center justify-between font-mono font-medium">
              <span className="truncate" title={run.config_fingerprint}>
                {run.config_fingerprint.slice(0, 16)}...
              </span>
              <Button
                variant="ghost"
                size="sm"
                className="size-6 p-0"
                onClick={() => handleCopyText(run.config_fingerprint, "fp")}
              >
                {copiedKey === "fp" ? (
                  <Check className="size-3 text-success" />
                ) : (
                  <Copy className="size-3" />
                )}
              </Button>
            </div>
          </CardContent>
        </Card>

        <Card className="rounded-xl shadow-2xs">
          <CardContent className="p-3 space-y-1">
            <span className="text-muted-foreground">Thế hệ xử lý</span>
            <div className="font-semibold text-foreground text-sm">
              Generation #{run.generation}
            </div>
          </CardContent>
        </Card>

        <Card className="rounded-xl shadow-2xs">
          <CardContent className="p-3 space-y-1">
            <span className="text-muted-foreground">Tổng số trang</span>
            <div className="font-semibold text-foreground text-sm">
              {run.pages_total !== null
                ? `${run.pages_total} trang`
                : "Chờ xác định"}
            </div>
          </CardContent>
        </Card>

        <Card className="rounded-xl shadow-2xs">
          <CardContent className="p-3 space-y-1">
            <span className="text-muted-foreground">Tải tệp gốc OCR</span>
            <div className="flex items-center gap-1.5 pt-0.5">
              <Button
                size="sm"
                variant="outline"
                className="h-6 text-[11px] px-2 gap-1"
                disabled={downloadingType === "doc"}
                onClick={() => void handleDownloadFile("doc")}
              >
                {downloadingType === "doc" ? (
                  <Loader2 className="size-2.5 animate-spin" />
                ) : (
                  <FileCode className="size-2.5 text-primary" />
                )}
                <span>JSON</span>
              </Button>
              <Button
                size="sm"
                variant="outline"
                className="h-6 text-[11px] px-2 gap-1"
                disabled={downloadingType === "md"}
                onClick={() => void handleDownloadFile("md")}
              >
                {downloadingType === "md" ? (
                  <Loader2 className="size-2.5 animate-spin" />
                ) : (
                  <FileText className="size-2.5 text-primary" />
                )}
                <span>Markdown</span>
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Tabs for Manifest & Evidence */}
      <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
        <TabsList className="h-9">
          <TabsTrigger value="manifest" className="text-xs gap-1.5">
            <ShieldCheck className="size-3.5 text-primary" />
            <span>Manifest kỹ thuật</span>
          </TabsTrigger>
          <TabsTrigger value="evidence" className="text-xs gap-1.5">
            <Layers className="size-3.5 text-primary" />
            <span>Snapshot bằng chứng (Compiler)</span>
          </TabsTrigger>
        </TabsList>

        {/* Manifest Content */}
        <TabsContent value="manifest" className="mt-3">
          <Card className="rounded-xl shadow-2xs">
            <CardHeader className="p-4 border-b bg-muted/20 flex flex-row items-center justify-between">
              <CardTitle className="text-xs font-semibold flex items-center gap-1.5">
                <FileCheck className="size-4 text-primary" />
                <span>Manifest: hash, PyMuPDF, kiểm tra toàn vẹn</span>
              </CardTitle>
              {manifestQuery.data ? (
                <Button
                  size="sm"
                  variant="ghost"
                  className="h-7 text-xs gap-1"
                  onClick={() =>
                    handleCopyText(
                      JSON.stringify(manifestQuery.data, null, 2),
                      "manifest_json",
                    )
                  }
                >
                  <Copy className="size-3" />
                  <span>Sao chép JSON</span>
                </Button>
              ) : null}
            </CardHeader>
            <CardContent className="p-4">
              {manifestQuery.isLoading ? (
                <Skeleton className="h-48 w-full" />
              ) : manifestQuery.isError ? (
                <p className="text-xs text-destructive">
                  Không đọc được manifest của lượt xử lý này.
                </p>
              ) : manifestQuery.data ? (
                <pre className="p-3 rounded-lg border bg-muted/10 font-mono text-[11px] overflow-auto max-h-[500px] leading-relaxed whitespace-pre-wrap">
                  {JSON.stringify(manifestQuery.data, null, 2)}
                </pre>
              ) : null}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Evidence Snapshot Content */}
        <TabsContent value="evidence" className="mt-3">
          <Card className="rounded-xl shadow-2xs">
            <CardHeader className="p-4 border-b bg-muted/20 flex flex-row items-center justify-between">
              <CardTitle className="text-xs font-semibold flex items-center gap-1.5">
                <Code className="size-4 text-primary" />
                <span>
                  Evidence Snapshot: ghim revision + generation + hash
                </span>
              </CardTitle>
              {evidenceQuery.data ? (
                <Button
                  size="sm"
                  variant="ghost"
                  className="h-7 text-xs gap-1"
                  onClick={() =>
                    handleCopyText(
                      JSON.stringify(evidenceQuery.data, null, 2),
                      "evidence_json",
                    )
                  }
                >
                  <Copy className="size-3" />
                  <span>Sao chép JSON</span>
                </Button>
              ) : null}
            </CardHeader>
            <CardContent className="p-4">
              {evidenceQuery.isLoading ? (
                <Skeleton className="h-48 w-full" />
              ) : evidenceQuery.isError ? (
                <p className="text-xs text-destructive">
                  Không đọc được snapshot bằng chứng của lượt xử lý này.
                </p>
              ) : evidenceQuery.data ? (
                <pre className="p-3 rounded-lg border bg-muted/10 font-mono text-[11px] overflow-auto max-h-[500px] leading-relaxed whitespace-pre-wrap">
                  {JSON.stringify(evidenceQuery.data, null, 2)}
                </pre>
              ) : null}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
