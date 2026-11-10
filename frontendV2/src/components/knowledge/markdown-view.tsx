import { Check, Code2, Copy, Download, Eye, FileText } from "lucide-react";
import { useMemo, useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface MarkdownViewProps {
  content: string | null | undefined;
  isLoading?: boolean;
  fileName?: string;
  sourceTitle?: string;
}

interface MarkdownBlock {
  id: string;
  type:
    | "h1"
    | "h2"
    | "h3"
    | "h4"
    | "p"
    | "ul"
    | "ol"
    | "table"
    | "quote"
    | "divider";
  content: string;
  items?: Array<{ id: string; text: string }>;
  tableData?: {
    headers: Array<{ id: string; text: string }>;
    rows: Array<{ id: string; cells: Array<{ id: string; text: string }> }>;
  };
}

export function MarkdownView({
  content,
  isLoading,
  fileName = "document.md",
  sourceTitle,
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
    if (!content) return;
    const blob = new Blob([content], { type: "text/markdown;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = fileName.endsWith(".md") ? fileName : `${fileName}.md`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    toast.success("Đã tải tệp Markdown về máy.");
  };

  // Render markdown lines into formatted blocks for preview
  const renderedBlocks = useMemo(() => {
    if (!content) return null;

    const lines = content.split("\n");
    const blocks: MarkdownBlock[] = [];

    let currentList: {
      type: "ul" | "ol";
      items: Array<{ id: string; text: string }>;
    } | null = null;
    let tableLines: string[] = [];

    const flushList = () => {
      if (currentList) {
        blocks.push({
          id: `list_${blocks.length}_${currentList.type}`,
          type: currentList.type,
          content: "",
          items: currentList.items,
        });
        currentList = null;
      }
    };

    const flushTable = () => {
      if (tableLines.length >= 2) {
        const parseRow = (line: string) =>
          line
            .replace(/^\|/, "")
            .replace(/\|$/, "")
            .split("|")
            .map((c) => c.trim());

        const rawHeaders = parseRow(tableLines[0]);
        const headers = rawHeaders.map((h, i) => ({
          id: `th_${i}_${h.slice(0, 8)}`,
          text: h,
        }));

        const rows: Array<{
          id: string;
          cells: Array<{ id: string; text: string }>;
        }> = [];

        for (let i = 2; i < tableLines.length; i++) {
          if (tableLines[i].includes("|")) {
            const rawCells = parseRow(tableLines[i]);
            rows.push({
              id: `tr_${i}`,
              cells: rawCells.map((c, cellIdx) => ({
                id: `td_${i}_${cellIdx}`,
                text: c,
              })),
            });
          }
        }

        blocks.push({
          id: `tbl_${blocks.length}`,
          type: "table",
          content: "",
          tableData: { headers, rows },
        });
      }
      tableLines = [];
    };

    for (let i = 0; i < lines.length; i++) {
      const line = lines[i].trimEnd();
      const trimmed = line.trim();

      // Check table row
      if (trimmed.startsWith("|") && trimmed.endsWith("|")) {
        flushList();
        tableLines.push(trimmed);
        continue;
      } else if (tableLines.length > 0) {
        flushTable();
      }

      if (!trimmed) {
        flushList();
        continue;
      }

      // Check headings
      if (trimmed.startsWith("# ")) {
        flushList();
        blocks.push({
          id: `h1_${blocks.length}`,
          type: "h1",
          content: trimmed.replace(/^#\s+/, ""),
        });
      } else if (trimmed.startsWith("## ")) {
        flushList();
        blocks.push({
          id: `h2_${blocks.length}`,
          type: "h2",
          content: trimmed.replace(/^##\s+/, ""),
        });
      } else if (trimmed.startsWith("### ")) {
        flushList();
        blocks.push({
          id: `h3_${blocks.length}`,
          type: "h3",
          content: trimmed.replace(/^###\s+/, ""),
        });
      } else if (trimmed.startsWith("#### ")) {
        flushList();
        blocks.push({
          id: `h4_${blocks.length}`,
          type: "h4",
          content: trimmed.replace(/^####\s+/, ""),
        });
      } else if (trimmed.startsWith("---") || trimmed.startsWith("***")) {
        flushList();
        blocks.push({
          id: `div_${blocks.length}`,
          type: "divider",
          content: "",
        });
      } else if (trimmed.startsWith("> ")) {
        flushList();
        blocks.push({
          id: `quote_${blocks.length}`,
          type: "quote",
          content: trimmed.replace(/^>\s+/, ""),
        });
      } else if (trimmed.startsWith("- ") || trimmed.startsWith("* ")) {
        const itemText = trimmed.replace(/^[-*]\s+/, "");
        if (currentList && currentList.type === "ul") {
          currentList.items.push({
            id: `ul_item_${currentList.items.length}`,
            text: itemText,
          });
        } else {
          flushList();
          currentList = {
            type: "ul",
            items: [{ id: "ul_item_0", text: itemText }],
          };
        }
      } else if (/^\d+\.\s+/.test(trimmed)) {
        const itemText = trimmed.replace(/^\d+\.\s+/, "");
        if (currentList && currentList.type === "ol") {
          currentList.items.push({
            id: `ol_item_${currentList.items.length}`,
            text: itemText,
          });
        } else {
          flushList();
          currentList = {
            type: "ol",
            items: [{ id: "ol_item_0", text: itemText }],
          };
        }
      } else {
        flushList();
        blocks.push({
          id: `p_${blocks.length}`,
          type: "p",
          content: trimmed,
        });
      }
    }

    flushList();
    flushTable();

    return blocks;
  }, [content]);

  // Clean inline citations and bold/code text
  const renderFormattedText = (text: string, prefix: string) => {
    const parts = text.split(/(\[[A-Za-z0-9_:-]+\])/g);
    let counter = 0;
    return parts.map((part) => {
      counter++;
      const tokenKey = `${prefix}_tok_${counter}`;
      if (part.startsWith("[") && part.endsWith("]") && part.length > 2) {
        const rawKey = part.slice(1, -1);
        return (
          <span
            key={tokenKey}
            className="inline-flex items-center px-1.5 py-0.2 mx-0.5 text-[10px] font-mono font-medium rounded bg-primary/10 text-primary border border-primary/20 align-baseline cursor-default"
            title={`Căn cứ truy vết: ${rawKey}`}
          >
            {rawKey}
          </span>
        );
      }
      return <span key={tokenKey}>{part}</span>;
    });
  };

  if (isLoading) {
    return (
      <div className="py-24 flex flex-col items-center justify-center gap-2 text-xs text-muted-foreground">
        <span className="size-5 border-2 border-primary border-t-transparent rounded-full animate-spin" />
        <span>Đang nạp dữ liệu Markdown...</span>
      </div>
    );
  }

  if (!content) {
    return (
      <div className="py-20 text-center text-xs text-muted-foreground space-y-2 border border-dashed rounded-xl bg-card/40">
        <FileText className="size-8 mx-auto text-muted-foreground/40" />
        <p className="font-medium text-foreground">Chưa có bản Markdown</p>
        <p>Bản Markdown sẽ được tự động kết xuất sau khi chuẩn bị nội dung.</p>
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

          {renderedBlocks?.map((block) => {
            switch (block.type) {
              case "h1":
                return (
                  <h1
                    key={block.id}
                    className="text-lg font-bold text-foreground pt-2 border-b border-border/50 pb-1.5"
                  >
                    {renderFormattedText(block.content, block.id)}
                  </h1>
                );
              case "h2":
                return (
                  <h2
                    key={block.id}
                    className="text-base font-semibold text-foreground pt-2 text-primary"
                  >
                    {renderFormattedText(block.content, block.id)}
                  </h2>
                );
              case "h3":
                return (
                  <h3
                    key={block.id}
                    className="text-sm font-semibold text-foreground pt-1.5"
                  >
                    {renderFormattedText(block.content, block.id)}
                  </h3>
                );
              case "h4":
                return (
                  <h4
                    key={block.id}
                    className="text-xs font-semibold text-muted-foreground pt-1 uppercase tracking-wider"
                  >
                    {renderFormattedText(block.content, block.id)}
                  </h4>
                );
              case "quote":
                return (
                  <blockquote
                    key={block.id}
                    className="border-l-3 border-primary/60 bg-muted/30 px-3.5 py-2 rounded-r text-xs italic text-foreground/90 my-2"
                  >
                    {renderFormattedText(block.content, block.id)}
                  </blockquote>
                );
              case "ul":
                return (
                  <ul
                    key={block.id}
                    className="list-disc pl-5 space-y-1 text-xs text-foreground/90"
                  >
                    {block.items?.map((item) => (
                      <li key={item.id}>
                        {renderFormattedText(item.text, item.id)}
                      </li>
                    ))}
                  </ul>
                );
              case "ol":
                return (
                  <ol
                    key={block.id}
                    className="list-decimal pl-5 space-y-1 text-xs text-foreground/90"
                  >
                    {block.items?.map((item) => (
                      <li key={item.id}>
                        {renderFormattedText(item.text, item.id)}
                      </li>
                    ))}
                  </ol>
                );
              case "table":
                return (
                  <div
                    key={block.id}
                    className="rounded-lg border border-border/70 overflow-x-auto shadow-2xs my-3 bg-background"
                  >
                    <table className="w-full text-xs text-left border-collapse">
                      {block.tableData?.headers && (
                        <thead>
                          <tr className="bg-muted/60 border-b border-border/60">
                            {block.tableData.headers.map((h) => (
                              <th
                                key={h.id}
                                className="p-2.5 font-semibold text-foreground border-r border-border/40 last:border-0"
                              >
                                {renderFormattedText(h.text, h.id)}
                              </th>
                            ))}
                          </tr>
                        </thead>
                      )}
                      <tbody>
                        {block.tableData?.rows.map((row) => (
                          <tr
                            key={row.id}
                            className="border-b border-border/40 last:border-0 hover:bg-muted/20"
                          >
                            {row.cells.map((cell) => (
                              <td
                                key={cell.id}
                                className="p-2.5 text-foreground/90 border-r border-border/40 last:border-0"
                              >
                                {renderFormattedText(cell.text, cell.id)}
                              </td>
                            ))}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                );
              case "divider":
                return <hr key={block.id} className="border-border/60 my-4" />;
              default:
                return (
                  <p
                    key={block.id}
                    className="text-xs leading-relaxed text-foreground/90 my-1.5"
                  >
                    {renderFormattedText(block.content, block.id)}
                  </p>
                );
            }
          })}
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
