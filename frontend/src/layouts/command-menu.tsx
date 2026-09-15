import { useTheme } from "@/components/theme-provider";
import { Dialog, DialogContent, DialogTitle } from "@/components/ui/dialog";
import { Kbd } from "@/components/ui/kbd";
import { cn } from "@/lib/utils";
import { NAVIGATION_CONFIG } from "@/navigation/config";
import { ExternalLink, Moon, Search, Sun, X } from "lucide-react";
import * as React from "react";

interface CommandMenuProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSelectRoute: (path: string) => void;
}

export function CommandMenu({ open, onOpenChange, onSelectRoute }: CommandMenuProps) {
  const [query, setQuery] = React.useState("");
  const [selectedIndex, setSelectedIndex] = React.useState(0);
  const { setTheme, resolvedTheme } = useTheme();

  // Flatten all searchable items
  const allItems = React.useMemo(() => {
    const navItems = NAVIGATION_CONFIG.flatMap((section) =>
      section.items.map((item) => ({
        id: item.id,
        title: item.title,
        description: item.description,
        path: item.path,
        icon: item.icon,
        category: section.title,
      }))
    );

    const actionItems = [
      {
        id: "action-theme",
        title: `Chuyển sang giao diện ${resolvedTheme === "dark" ? "Sáng" : "Tối"}`,
        description: "Thay đổi giao diện màu hệ thống",
        path: "#theme",
        icon: resolvedTheme === "dark" ? Sun : Moon,
        category: "Thao Tác Nhanh",
      },
      {
        id: "action-swagger",
        title: "Mở Tài Liệu Swagger API Docs",
        description: "Kiểm thử các REST endpoints của Backend port 8001",
        path: "http://localhost:8001/docs",
        icon: ExternalLink,
        category: "Thao Tác Nhanh",
      },
    ];

    return [...navItems, ...actionItems];
  }, [resolvedTheme]);

  // Filter items based on query
  const filteredItems = React.useMemo(() => {
    if (!query.trim()) return allItems;
    const lower = query.toLowerCase();
    return allItems.filter(
      (item) =>
        item.title.toLowerCase().includes(lower) ||
        item.description?.toLowerCase().includes(lower) ||
        item.category.toLowerCase().includes(lower)
    );
  }, [query, allItems]);

  // Handle global shortcut Ctrl+K / Cmd+K
  React.useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === "k") {
        e.preventDefault();
        onOpenChange(!open);
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [open, onOpenChange]);

  const handleSelectItem = (item: (typeof allItems)[0]) => {
    if (item.path === "#theme") {
      setTheme(resolvedTheme === "dark" ? "light" : "dark");
      onOpenChange(false);
      return;
    }
    if (item.path.startsWith("http")) {
      window.open(item.path, "_blank");
      onOpenChange(false);
      return;
    }
    onSelectRoute(item.path);
    onOpenChange(false);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setSelectedIndex((prev) => (prev < filteredItems.length - 1 ? prev + 1 : 0));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setSelectedIndex((prev) => (prev > 0 ? prev - 1 : filteredItems.length - 1));
    } else if (e.key === "Enter") {
      e.preventDefault();
      if (filteredItems[selectedIndex]) {
        handleSelectItem(filteredItems[selectedIndex]);
      }
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="overflow-hidden p-0 max-w-xl top-[30%]">
        <DialogTitle className="sr-only">Hộp Thoại Tìm Kiếm Toàn Năng</DialogTitle>
        {/* Search Header */}
        <div className="flex items-center border-b border-border px-3.5 py-2.5">
          <Search className="size-4 shrink-0 text-muted-foreground mr-2.5" />
          <input
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
              setSelectedIndex(0);
            }}
            onKeyDown={handleKeyDown}
            placeholder="Tìm kiếm màn hình, chức năng hoặc trợ lý AI (Ctrl + K)..."
            className="flex-1 bg-transparent text-sm outline-none placeholder:text-muted-foreground"
          />
          {query && (
            <button
              type="button"
              onClick={() => {
                setQuery("");
                setSelectedIndex(0);
              }}
              className="rounded p-0.5 text-muted-foreground hover:text-foreground mr-1"
            >
              <X className="size-3.5" />
            </button>
          )}
          <Kbd>Esc</Kbd>
        </div>

        {/* Results List */}
        <div className="max-h-[320px] overflow-y-auto p-1.5 space-y-1">
          {filteredItems.length === 0 ? (
            <div className="py-8 text-center text-xs text-muted-foreground">
              Không tìm thấy kết quả phù hợp cho &quot;{query}&quot;
            </div>
          ) : (
            filteredItems.map((item, index) => {
              const Icon = item.icon;
              const isSelected = index === selectedIndex;
              return (
                <button
                  type="button"
                  key={item.id}
                  onClick={() => handleSelectItem(item)}
                  onMouseEnter={() => setSelectedIndex(index)}
                  className={cn(
                    "flex w-full items-center gap-3 rounded-md px-3 py-2 text-left text-xs transition-colors",
                    isSelected
                      ? "bg-primary/10 text-primary font-medium"
                      : "text-foreground hover:bg-muted"
                  )}
                >
                  <div
                    className={cn(
                      "flex size-7 items-center justify-center rounded-md shrink-0",
                      isSelected
                        ? "bg-primary text-primary-foreground"
                        : "bg-muted text-muted-foreground"
                    )}
                  >
                    <Icon className="size-3.5" />
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <span className="font-semibold truncate">{item.title}</span>
                      <span className="text-[10px] text-muted-foreground font-normal">
                        ({item.category})
                      </span>
                    </div>
                    {item.description && (
                      <p className="text-[11px] text-muted-foreground truncate">
                        {item.description}
                      </p>
                    )}
                  </div>
                  {isSelected && (
                    <span className="text-[10px] text-primary font-mono shrink-0">Enter ↵</span>
                  )}
                </button>
              );
            })
          )}
        </div>

        {/* Command Footer */}
        <div className="flex items-center justify-between border-t border-border bg-muted/30 px-3.5 py-2 text-[11px] text-muted-foreground">
          <div className="flex items-center gap-2">
            <span>Di chuyển:</span>
            <Kbd>↑</Kbd>
            <Kbd>↓</Kbd>
            <span>Chọn:</span>
            <Kbd>↵</Kbd>
          </div>
          <div>
            <span>Đóng:</span> <Kbd>Esc</Kbd>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
