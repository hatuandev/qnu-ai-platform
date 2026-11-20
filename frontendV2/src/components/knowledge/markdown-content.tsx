import type React from "react";
import { useMemo } from "react";
import { type MarkdownBlock, parseMarkdownBlocks } from "@/lib/markdown-parser";
import { cn } from "@/lib/utils";

export type { MarkdownBlock };
export { parseMarkdownBlocks };

/**
 * Tokenizes and renders inline Markdown (bold, code, italic, citations).
 */
export function renderInlineMarkdown(
  text: string,
  prefix: string,
  renderToken?: (token: string, key: string) => React.ReactNode,
): React.ReactNode {
  if (!text) return null;

  // Matches bold (**...** or __...__), inline code (`...`), italic (*...*), or citation tokens ([...])
  const pattern =
    /(\*\*[^*]+\*\*|__[^_]+__|`[^`]+`|\*[^*]+\*|\[[A-Za-z0-9_:-]+\])/g;
  const parts = text.split(pattern);

  let counter = 0;
  return parts.map((part) => {
    counter++;
    const tokenKey = `${prefix}_tok_${counter}`;

    if (!part) return null;

    // Bold **text** or __text__
    if (
      (part.startsWith("**") && part.endsWith("**") && part.length > 4) ||
      (part.startsWith("__") && part.endsWith("__") && part.length > 4)
    ) {
      const inner = part.slice(2, -2);
      return (
        <strong key={tokenKey} className="font-semibold text-foreground">
          {inner}
        </strong>
      );
    }

    // Inline code `code`
    if (part.startsWith("`") && part.endsWith("`") && part.length > 2) {
      const inner = part.slice(1, -1);
      return (
        <code
          key={tokenKey}
          className="rounded bg-muted/80 px-1 py-0.5 font-mono text-[11px] font-medium text-foreground border border-border/40"
        >
          {inner}
        </code>
      );
    }

    // Italic *text*
    if (part.startsWith("*") && part.endsWith("*") && part.length > 2) {
      const inner = part.slice(1, -1);
      return (
        <em key={tokenKey} className="italic text-foreground/90">
          {inner}
        </em>
      );
    }

    // Citation or custom token [token]
    if (part.startsWith("[") && part.endsWith("]")) {
      if (renderToken) {
        const rendered = renderToken(part, tokenKey);
        if (rendered !== null && rendered !== undefined) {
          return rendered;
        }
      }
    }

    return <span key={tokenKey}>{part}</span>;
  });
}

export interface MarkdownContentProps {
  content: string | null | undefined;
  className?: string;
  compact?: boolean;
  suffix?: React.ReactNode;
  renderToken?: (token: string, key: string) => React.ReactNode;
}

/**
 * Reusable Markdown Content Renderer.
 * Accurately parses and formats headings, lists, tables, quotes, bold, and code.
 * Seamlessly accepts a `suffix` (e.g. CitationBadges) attached to the end of the content.
 */
export function MarkdownContent({
  content,
  className,
  compact = false,
  suffix,
  renderToken,
}: MarkdownContentProps) {
  const blocks = useMemo(() => parseMarkdownBlocks(content ?? ""), [content]);

  if (blocks.length === 0) {
    if (suffix) {
      return (
        <div
          className={cn("text-sm leading-relaxed text-foreground", className)}
        >
          {suffix}
        </div>
      );
    }
    return null;
  }

  return (
    <div className={cn("space-y-2 select-text", className)}>
      {blocks.map((block, blockIndex) => {
        const isLastBlock = blockIndex === blocks.length - 1;

        switch (block.type) {
          case "h1":
            return (
              <h1
                key={block.id}
                className={cn(
                  "font-bold text-foreground border-b border-border/50",
                  compact ? "text-sm pt-1 pb-0.5" : "text-lg pt-2 pb-1.5",
                )}
              >
                {renderInlineMarkdown(block.content, block.id, renderToken)}
                {isLastBlock && suffix}
              </h1>
            );

          case "h2":
            return (
              <h2
                key={block.id}
                className={cn(
                  "font-semibold text-primary",
                  compact ? "text-xs sm:text-sm pt-1" : "text-base pt-2",
                )}
              >
                {renderInlineMarkdown(block.content, block.id, renderToken)}
                {isLastBlock && suffix}
              </h2>
            );

          case "h3":
            return (
              <h3
                key={block.id}
                className={cn(
                  "font-semibold text-foreground",
                  compact ? "text-sm pt-1" : "text-sm pt-1.5",
                )}
              >
                {renderInlineMarkdown(block.content, block.id, renderToken)}
                {isLastBlock && suffix}
              </h3>
            );

          case "h4":
            return (
              <h4
                key={block.id}
                className="text-xs font-semibold text-muted-foreground uppercase tracking-wider pt-0.5"
              >
                {renderInlineMarkdown(block.content, block.id, renderToken)}
                {isLastBlock && suffix}
              </h4>
            );

          case "quote":
            return (
              <blockquote
                key={block.id}
                className="border-l-2 border-primary/60 bg-muted/20 px-3 py-1.5 rounded-r text-sm italic text-foreground/90 my-1.5 leading-relaxed"
              >
                {renderInlineMarkdown(block.content, block.id, renderToken)}
                {isLastBlock && suffix}
              </blockquote>
            );

          case "ul":
            return (
              <ul
                key={block.id}
                className="list-disc pl-5 space-y-1 text-sm text-foreground/90 my-1.5 leading-relaxed"
              >
                {block.items?.map((item, itemIdx) => {
                  const isLastItem =
                    isLastBlock && itemIdx === (block.items?.length ?? 1) - 1;
                  return (
                    <li key={item.id} className="leading-relaxed">
                      {renderInlineMarkdown(item.text, item.id, renderToken)}
                      {isLastItem && suffix}
                    </li>
                  );
                })}
              </ul>
            );

          case "ol":
            return (
              <ol
                key={block.id}
                className="list-decimal pl-5 space-y-1 text-sm text-foreground/90 my-1.5 leading-relaxed"
              >
                {block.items?.map((item, itemIdx) => {
                  const isLastItem =
                    isLastBlock && itemIdx === (block.items?.length ?? 1) - 1;
                  return (
                    <li key={item.id} className="leading-relaxed">
                      {renderInlineMarkdown(item.text, item.id, renderToken)}
                      {isLastItem && suffix}
                    </li>
                  );
                })}
              </ol>
            );

          case "table":
            return (
              <div key={block.id} className="space-y-1.5 my-2">
                <div className="rounded-lg border border-border/70 overflow-x-auto shadow-2xs bg-card/60">
                  <table className="w-full text-xs text-left border-collapse">
                    {block.tableData?.headers && (
                      <thead className="bg-muted/60 border-b border-border/60">
                        <tr>
                          {block.tableData.headers.map((h) => (
                            <th
                              key={h.id}
                              className="px-2.5 py-1.5 font-semibold text-foreground border-r border-border/40 last:border-0 whitespace-nowrap"
                            >
                              {renderInlineMarkdown(h.text, h.id, renderToken)}
                            </th>
                          ))}
                        </tr>
                      </thead>
                    )}
                    <tbody>
                      {block.tableData?.rows.map((row) => (
                        <tr
                          key={row.id}
                          className="border-b border-border/40 last:border-0 hover:bg-muted/20 transition-colors"
                        >
                          {row.cells.map((cell) => (
                            <td
                              key={cell.id}
                              className="px-2.5 py-1.5 text-foreground/90 border-r border-border/40 last:border-0 leading-relaxed align-top"
                            >
                              {renderInlineMarkdown(
                                cell.text,
                                cell.id,
                                renderToken,
                              )}
                            </td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                {isLastBlock && suffix && (
                  <div className="flex flex-wrap items-center gap-1 pt-0.5">
                    {suffix}
                  </div>
                )}
              </div>
            );

          case "divider":
            return <hr key={block.id} className="border-border/60 my-2.5" />;

          default:
            return (
              <p
                key={block.id}
                className="text-sm leading-relaxed text-foreground/90 my-1 whitespace-pre-wrap"
              >
                {renderInlineMarkdown(block.content, block.id, renderToken)}
                {isLastBlock && suffix}
              </p>
            );
        }
      })}
    </div>
  );
}
