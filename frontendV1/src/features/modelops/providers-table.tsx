import { ArrowUpRight, Cpu } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  CapacityBadge,
  ProviderOperationalBudgetsSummary,
} from "@/features/modelops/capacity-badge";
import {
  CAPABILITY_LABELS,
  type Capability,
  PROVIDER_TYPE_LABELS,
  type Provider,
} from "@/features/modelops/types";
import { formatDateTimeValue } from "@/lib/date-utils";

export function ProvidersTable({
  providers,
  isLoading,
  onOpen,
}: {
  providers: Provider[];
  isLoading: boolean;
  onOpen: (provider: Provider) => void;
}) {
  if (isLoading) {
    return (
      <div className="grid gap-2 p-4">
        {[0, 1, 2, 3].map((row) => (
          <Skeleton key={row} className="h-11 w-full" />
        ))}
      </div>
    );
  }

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Provider</TableHead>
          <TableHead className="hidden md:table-cell">Model</TableHead>
          <TableHead className="hidden lg:table-cell">Capabilities</TableHead>
          <TableHead className="hidden xl:table-cell">Năng lực</TableHead>
          <TableHead className="w-[130px]">Trạng thái</TableHead>
          <TableHead className="hidden w-[170px] lg:table-cell">
            Cập nhật
          </TableHead>
          <TableHead className="w-[80px] text-right">
            <span className="sr-only">Hành động</span>
          </TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {providers.map((provider) => (
          <TableRow key={provider.id}>
            <TableCell>
              <div className="flex items-center gap-2">
                <span className="flex size-7 shrink-0 items-center justify-center rounded-md border bg-muted text-muted-foreground">
                  <Cpu className="size-3.5" />
                </span>
                <div className="min-w-0">
                  <p className="truncate text-sm font-medium">
                    {provider.name}
                  </p>
                  <p className="truncate font-mono text-[11px] text-muted-foreground">
                    {PROVIDER_TYPE_LABELS[provider.provider_type]} ·{" "}
                    {provider.base_url}
                  </p>
                </div>
              </div>
            </TableCell>
            <TableCell className="hidden font-mono text-xs md:table-cell">
              {provider.model_name}
            </TableCell>
            <TableCell className="hidden lg:table-cell">
              <div className="flex flex-wrap gap-1">
                {provider.capabilities.length === 0 ? (
                  <span className="text-xs text-muted-foreground">—</span>
                ) : (
                  provider.capabilities.map((capability) => (
                    <Badge
                      key={capability}
                      variant="outline"
                      className="text-[10px]"
                    >
                      {CAPABILITY_LABELS[capability as Capability] ??
                        capability}
                    </Badge>
                  ))
                )}
              </div>
            </TableCell>
            <TableCell className="hidden xl:table-cell">
              <div className="flex flex-col items-start gap-1">
                <CapacityBadge status={provider.capacity_status} />
                <ProviderOperationalBudgetsSummary
                  provider={provider}
                  compact
                />
              </div>
            </TableCell>
            <TableCell>
              {provider.is_active ? (
                <Badge variant="success">Đang bật</Badge>
              ) : (
                <Badge variant="secondary">Đang tắt</Badge>
              )}
            </TableCell>
            <TableCell className="hidden text-xs text-muted-foreground lg:table-cell">
              {formatDateTimeValue(provider.updated_at)}
            </TableCell>
            <TableCell className="text-right">
              <Button
                size="sm"
                variant="ghost"
                className="gap-1 text-xs"
                onClick={() => onOpen(provider)}
              >
                <span>Mở</span>
                <ArrowUpRight className="size-3.5" />
              </Button>
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
