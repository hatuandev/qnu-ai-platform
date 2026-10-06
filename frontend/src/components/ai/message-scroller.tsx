import { ArrowDown } from "lucide-react";
import type React from "react";
import { useCallback, useEffect, useRef, useState } from "react";
import { cn } from "../../lib/utils";
import { Button } from "../ui/button";

export interface MessageScrollerProps {
  children: React.ReactNode;
  isStreaming?: boolean;
  className?: string;
}

export const MessageScroller: React.FC<MessageScrollerProps> = ({
  children,
  isStreaming = false,
  className,
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const [isAtBottom, setIsAtBottom] = useState(true);
  const [hasNewMessages, setHasNewMessages] = useState(false);
  const userScrolledUpRef = useRef(false);

  const scrollToBottom = useCallback((smooth = true) => {
    if (!containerRef.current) return;
    const { scrollHeight, clientHeight } = containerRef.current;
    containerRef.current.scrollTo({
      top: scrollHeight - clientHeight,
      behavior: smooth ? "smooth" : "auto",
    });
    setIsAtBottom(true);
    setHasNewMessages(false);
    userScrolledUpRef.current = false;
  }, []);

  // Handle user scroll detection
  const handleScroll = useCallback(() => {
    if (!containerRef.current) return;
    const { scrollTop, scrollHeight, clientHeight } = containerRef.current;
    const distanceToBottom = scrollHeight - (scrollTop + clientHeight);

    if (distanceToBottom <= 40) {
      setIsAtBottom(true);
      setHasNewMessages(false);
      userScrolledUpRef.current = false;
    } else {
      setIsAtBottom(false);
      userScrolledUpRef.current = true;
    }
  }, []);

  // Auto-scroll when content mutations occur (streaming or new messages)
  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;

    const observer = new MutationObserver(() => {
      if (!userScrolledUpRef.current) {
        el.scrollTo({
          top: el.scrollHeight - el.clientHeight,
          behavior: "auto",
        });
      } else if (isStreaming) {
        setHasNewMessages(true);
      }
    });

    observer.observe(el, {
      childList: true,
      subtree: true,
      characterData: true,
    });

    return () => observer.disconnect();
  }, [isStreaming]);

  return (
    <div className="relative flex-1 min-h-0 flex flex-col">
      <div
        ref={containerRef}
        onScroll={handleScroll}
        className={cn(
          "flex-1 overflow-y-auto px-4 py-4 space-y-4 select-text overscroll-contain",
          className,
        )}
      >
        {children}
      </div>

      {/* Floating Scroll to bottom button */}
      {!isAtBottom && (
        <div className="absolute bottom-4 right-6 z-20 animate-in fade-in slide-in-from-bottom-2 duration-200">
          <Button
            size="sm"
            variant="outline"
            onClick={() => scrollToBottom(true)}
            className="shadow-md bg-card/90 backdrop-blur-xs border-primary/40 hover:bg-primary hover:text-primary-foreground text-xs gap-1.5 h-8 rounded-full px-3 transition-all"
          >
            <ArrowDown className="h-3.5 w-3.5" />
            <span>Xuống tin mới nhất</span>
            {hasNewMessages && (
              <span className="h-2 w-2 rounded-full bg-primary animate-ping ml-0.5" />
            )}
          </Button>
        </div>
      )}
    </div>
  );
};
