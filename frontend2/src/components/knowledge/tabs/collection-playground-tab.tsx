import { Search } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import type { SandboxSearchResult } from "../types";

interface CollectionPlaygroundTabProps {
  sandboxQuery: string;
  setSandboxQuery: (query: string) => void;
  isSearchingSandbox: boolean;
  sandboxResults: SandboxSearchResult[] | null;
  onSandboxSearch: (e: React.FormEvent) => void;
}

export function CollectionPlaygroundTab({
  sandboxQuery,
  setSandboxQuery,
  isSearchingSandbox,
  sandboxResults,
  onSandboxSearch,
}: CollectionPlaygroundTabProps) {
  return (
    <div className="space-y-4">
      <Card className="p-5 border-border">
        <form onSubmit={onSandboxSearch} className="space-y-3">
          <label
            htmlFor="sandbox-query"
            className="text-xs font-semibold text-foreground block"
          >
            Truy vấn thử nghiệm (Hybrid RRF BGE-M3 + PostgreSQL FTS):
          </label>
          <div className="flex gap-2">
            <Input
              id="sandbox-query"
              value={sandboxQuery}
              onChange={(e) => setSandboxQuery(e.target.value)}
              placeholder="VD: Điểm chuẩn và phương thức xét tuyển ngành Quản lý giáo dục năm 2026..."
              className="h-9 text-xs"
            />
            <Button
              type="submit"
              disabled={isSearchingSandbox}
              className="h-9 text-xs gap-1.5 bg-primary text-primary-foreground shrink-0"
            >
              <Search className="size-3.5" />
              <span>{isSearchingSandbox ? "Đang tìm..." : "Truy vấn"}</span>
            </Button>
          </div>
        </form>

        {sandboxResults && (
          <div className="mt-5 space-y-3 pt-4 border-t border-border">
            <p className="text-xs font-semibold text-foreground">
              Kết quả truy xuất ({sandboxResults.length} Chunks phù hợp nhất):
            </p>
            {sandboxResults.map((res) => (
              <div
                key={res.id}
                className="p-3 bg-muted/20 border border-border rounded-lg space-y-1.5"
              >
                <div className="flex items-center justify-between text-xs">
                  <span className="font-semibold text-primary">
                    {res.clause}
                  </span>
                  <Badge variant="secondary" className="font-mono text-xs">
                    Điểm phù hợp: {res.score}
                  </Badge>
                </div>
                <p className="text-xs text-foreground leading-relaxed">
                  {res.text}
                </p>
                <p className="text-xs text-muted-foreground font-mono">
                  Phương pháp: {res.method}
                </p>
              </div>
            ))}
          </div>
        )}
      </Card>
    </div>
  );
}
