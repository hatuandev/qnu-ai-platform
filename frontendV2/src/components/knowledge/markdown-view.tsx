import { Check, Code2, Copy, Download, Eye, FileText } from "lucide-react";
import { useCallback, useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { downloadBlob } from "@/lib/download-blob";
import type { CitationInfo } from "@/lib/knowledge-studio-helpers";
import { cn } from "@/lib/utils";
import { MarkdownContent } from "./markdown-content";

interface MarkdownViewProps {
  content: string | null | undefined;
  isLoading?: boolean;
  isError?: boolean;
  artifact?: Blob;
  fileName?: string;
  sourceTitle?: string;
  lifecycleStatus?: string;
  citations: ReadonlyMap<string, CitationInfo>;
}

export function MarkdownView({
  content,
  isLoading,
  isError,
  artifact,
  fileName = "document.md",
  sourceTitle,
  lifecycleStatus,
  citations,
}: MarkdownViewProps) {
  const [subMode, setSubMode] = useState<"preview" | "raw">("preview");
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    if (!content) return;
    try {
      await navigator.clipboard.writeText(content);
      setCopied(true);
      toast.success("Đã sao chép nội dung Markdown!");
      setTimeout(() => setCopied(false), 2000);
    } catch {
      toast.error("Không thể sao chép vào bộ nhớ tạm.");
    }
  };

  const handleDownload = () => {
    if (artifact)
      downloadBlob(
        artifact,
        fileName.endsWith(".md") ? fileName : `${fileName}.md`,
      );
  };

  const renderCitationToken = useCallback(
    (part: string, tokenKey: string) => {
      const citation = citations.get(part.slice(1, -1));
      if (citation) {
        return (
          <span
            key={tokenKey}
            className="inline-flex items-center px-1.5 py-0.2 mx-0.5 text-[10px] font-mono font-medium rounded bg-primary/10 text-primary border border-primary/20 align-baseline cursor-default"
            title={citation.location ?? "Dẫn chứng trong tài liệu"}
          >
            [{citation.index}]
          </span>
        );
      }
      return null;
    },
    [citations],
  );

  if (isLoading) {
    return (
      <div className="py-24 flex flex-col items-center justify-center gap-2 text-xs text-muted-foreground">
        <span className="size-5 border-2 border-primary border-t-transparent rounded-full animate-spin" />
        <span>Đang nạp dữ liệu Markdown...</span>
      </div>
    );
  }

  if (isError || !content) {
    return (
      <div className="py-20 text-center text-xs text-muted-foreground space-y-2 border border-dashed rounded-xl bg-card/40">
        <FileText className="size-8 mx-auto text-muted-foreground/40" />
        <p
          className="font-medium text-foreground"
          role={isError ? "alert" : "status"}
        >
          {isError ? "Không tải được bản Markdown" : "Chưa có bản Markdown"}
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {/* Submode Toolbar */}
      <div className="flex items-center justify-between border-b border-border/60 pb-2.5">
        <div className="flex items-center gap-1 bg-muted/60 p-0.5 rounded-lg border border-border/70 text-xs">
          <button
            type="button"
            onClick={() => setSubMode("preview")}
            className={cn(
              "flex items-center gap-1.5 px-2.5 py-1 rounded-md transition-all cursor-pointer font-medium text-xs",
              subMode === "preview"
                ? "bg-card text-foreground shadow-2xs font-semibold"
                : "text-muted-foreground hover:text-foreground",
            )}
          >
            <Eye className="size-3.5" />
            <span>Xem trước</span>
          </button>
          <button
            type="button"
            onClick={() => setSubMode("raw")}
            className={cn(
              "flex items-center gap-1.5 px-2.5 py-1 rounded-md transition-all cursor-pointer font-medium text-xs",
              subMode === "raw"
                ? "bg-card text-foreground shadow-2xs font-semibold"
                : "text-muted-foreground hover:text-foreground",
            )}
          >
            <Code2 className="size-3.5" />
            <span>Mã nguồn</span>
          </button>
        </div>

        <div className="flex items-center gap-1.5">
          <Button
            variant="outline"
            size="sm"
            onClick={handleCopy}
            className="h-7 text-xs gap-1.5"
            title="Sao chép toàn bộ mã Markdown"
          >
            {copied ? (
              <Check className="size-3 text-emerald-600" />
            ) : (
              <Copy className="size-3" />
            )}
            <span>{copied ? "Đã chép" : "Sao chép"}</span>
          </Button>

          <Button
            variant="outline"
            size="sm"
            onClick={handleDownload}
            disabled={!artifact}
            className="h-7 text-xs gap-1.5"
            title="Tải tệp .md về máy"
          >
            <Download className="size-3" />
            <span>Tải .md</span>
          </Button>
        </div>
      </div>

      {/* Viewport: Preview vs Raw */}
      {subMode === "preview" ? (
        <article className="prose prose-sm dark:prose-invert max-w-none space-y-4 p-5 sm:p-7 rounded-xl border border-border/70 bg-card text-foreground leading-relaxed shadow-2xs">
          {lifecycleStatus && (
            <p className="text-xs text-muted-foreground">{lifecycleStatus}</p>
          )}
          {sourceTitle && (
            <div className="pb-3 border-b border-border/60 mb-4">
              <span className="text-[11px] font-semibold tracking-wider uppercase text-muted-foreground">
                Tài liệu trích xuất
              </span>
              <h2 className="text-base font-bold text-foreground mt-0.5">
                {sourceTitle}
              </h2>
            </div>
          )}

          <MarkdownContent
            content={content}
            renderToken={renderCitationToken}
          />
        </article>
      ) : (
        <div className="relative rounded-xl border border-border/70 bg-muted/20 overflow-hidden shadow-2xs">
          <pre className="p-4 sm:p-5 font-mono text-xs leading-relaxed whitespace-pre-wrap select-text text-foreground max-h-[600px] overflow-y-auto">
            {content}
          </pre>
        </div>
      )}
    </div>
  );
}
