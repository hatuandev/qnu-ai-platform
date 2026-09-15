import type React from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { cn } from "../../lib/utils";

export interface ChatBubbleProps {
  content: string;
  senderRole?: "user" | "assistant" | "system";
  isStreaming?: boolean;
  className?: string;
}

export const ChatBubble: React.FC<ChatBubbleProps> = ({
  content,
  senderRole = "assistant",
  isStreaming = false,
  className,
}) => {
  const isAssistant = senderRole === "assistant";
  const isThinking = isStreaming && !content;

  if (isThinking) {
    return (
      <div
        className={cn(
          "flex items-center gap-2 px-4 py-3 rounded-surface bg-muted/60 text-muted-foreground w-fit animate-pulse border border-border/60",
          className
        )}
      >
        <div className="flex items-center gap-1.5">
          <span className="h-2 w-2 rounded-full bg-primary/70 animate-bounce [animation-delay:-0.3s]" />
          <span className="h-2 w-2 rounded-full bg-primary/70 animate-bounce [animation-delay:-0.15s]" />
          <span className="h-2 w-2 rounded-full bg-primary/70 animate-bounce" />
        </div>
        <span className="text-xs font-medium text-foreground/70 ml-1">
          Trợ lý QNU đang đối chiếu tri thức & lập luận...
        </span>
      </div>
    );
  }

  if (senderRole === "user") {
    return (
      <div
        className={cn(
          "bg-primary text-primary-foreground px-4 py-2.5 rounded-surface rounded-br-micro shadow-xs max-w-2xl text-sm leading-relaxed whitespace-pre-wrap select-text",
          className
        )}
      >
        {content}
      </div>
    );
  }

  return (
    <div
      className={cn(
        "prose prose-sm dark:prose-invert max-w-none text-foreground leading-relaxed text-sm",
        "bg-card border border-border/80 rounded-surface p-4 shadow-xs",
        className
      )}
    >
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          table: ({ children }) => (
            <div className="my-3 overflow-x-auto rounded-control border border-border">
              <table className="min-w-full text-left text-xs divide-y divide-border">
                {children}
              </table>
            </div>
          ),
          thead: ({ children }) => (
            <thead className="bg-muted/80 text-foreground font-semibold">{children}</thead>
          ),
          th: ({ children }) => (
            <th className="px-3.5 py-2 text-xs font-semibold tracking-wider text-muted-foreground border-b border-border">
              {children}
            </th>
          ),
          td: ({ children }) => (
            <td className="px-3.5 py-2.5 text-xs text-foreground/90 border-t border-border/60">
              {children}
            </td>
          ),
          tr: ({ children }) => <tr className="hover:bg-muted/40 transition-colors">{children}</tr>,
          code: ({ className: codeClassName, children, ...props }) => {
            const isInline = !codeClassName;
            return isInline ? (
              <code
                className="rounded-micro bg-muted px-1.5 py-0.5 font-mono text-[13px] text-foreground font-medium border border-border/50"
                {...props}
              >
                {children}
              </code>
            ) : (
              <code
                className="block overflow-x-auto rounded-control bg-muted/90 p-3 font-mono text-xs text-foreground leading-normal border border-border/80"
                {...props}
              >
                {children}
              </code>
            );
          },
          blockquote: ({ children }) => (
            <blockquote className="border-l-4 border-primary bg-primary/5 px-3.5 py-2 rounded-r-control my-3 italic text-muted-foreground text-xs">
              {children}
            </blockquote>
          ),
          ul: ({ children }) => (
            <ul className="list-disc list-outside pl-5 my-2 space-y-1 text-foreground/90">
              {children}
            </ul>
          ),
          ol: ({ children }) => (
            <ol className="list-decimal list-outside pl-5 my-2 space-y-1 text-foreground/90">
              {children}
            </ol>
          ),
          li: ({ children }) => <li className="text-xs leading-relaxed">{children}</li>,
          p: ({ children }) => (
            <p className="my-2 leading-relaxed text-xs sm:text-sm">{children}</p>
          ),
          h1: ({ children }) => (
            <h1 className="text-base font-bold text-foreground mt-4 mb-2">{children}</h1>
          ),
          h2: ({ children }) => (
            <h2 className="text-sm font-bold text-foreground mt-3 mb-1.5 border-b border-border/40 pb-1">
              {children}
            </h2>
          ),
          h3: ({ children }) => (
            <h3 className="text-xs font-semibold text-primary mt-2.5 mb-1 uppercase tracking-wider">
              {children}
            </h3>
          ),
          a: ({ href, children }) => (
            <a
              href={href}
              target="_blank"
              rel="noopener noreferrer"
              className="text-primary underline underline-offset-2 hover:text-primary/80 font-medium"
            >
              {children}
            </a>
          ),
        }}
      >
        {content}
      </ReactMarkdown>

      {isStreaming && isAssistant && (
        <span className="inline-block w-1.5 h-4 ml-1 bg-primary animate-pulse align-middle" />
      )}
    </div>
  );
};
