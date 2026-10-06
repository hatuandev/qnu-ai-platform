import { ChevronRight } from "lucide-react";
import type React from "react";
import { ProviderIcon } from "../../components/icons/provider-icon";
import { Badge } from "../../components/ui/badge";
import { Card } from "../../components/ui/card";
import type { ModelProvider } from "../../services/api-client";

export interface ProviderCardProps {
  provider: ModelProvider;
  onSelect: (providerId: string) => void;
}

export const ProviderCard: React.FC<ProviderCardProps> = ({
  provider,
  onSelect,
}) => {
  return (
    <Card
      onClick={() => onSelect(provider.id)}
      className="group p-4 transition-all flex items-center justify-between cursor-pointer hover:border-primary/70 hover:shadow-md hover:-translate-y-0.5 bg-card border border-border"
    >
      <div className="flex items-center gap-3.5 min-w-0">
        <div className="w-11 h-11 rounded-lg bg-muted/40 p-2 flex items-center justify-center shrink-0 group-hover:scale-105 transition-transform border border-border/50">
          <ProviderIcon code={provider.type || provider.code} size={30} />
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-1.5">
            <h3 className="font-bold text-sm text-foreground truncate group-hover:text-primary transition-colors">
              {provider.name}
            </h3>
            {!provider.is_active && (
              <Badge
                variant="outline"
                className="text-[10px] px-1.5 py-0 h-4 text-muted-foreground border-muted-foreground/30 font-mono shrink-0"
              >
                Tắt
              </Badge>
            )}
          </div>
          <div className="flex items-center gap-1.5 mt-0.5">
            <span className="text-[11px] font-mono text-muted-foreground uppercase">
              {provider.type}
            </span>
            {provider.models && provider.models.length > 0 && (
              <span className="text-[10px] text-muted-foreground/70 font-mono truncate">
                • {provider.models.length} model
                {provider.models.length > 1 ? "s" : ""}
              </span>
            )}
          </div>
        </div>
      </div>
      <ChevronRight className="h-4 w-4 text-muted-foreground/40 group-hover:text-primary group-hover:translate-x-0.5 transition-all shrink-0 ml-2" />
    </Card>
  );
};
