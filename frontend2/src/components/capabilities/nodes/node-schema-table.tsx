import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

interface NodeSchemaTableProps {
  schema: Record<string, unknown> | undefined;
  emptyMessage?: string;
}

interface SchemaPropertyItem {
  name: string;
  type: string;
  required: boolean;
  description: string;
  defaultValue?: string;
  enumValues?: string[];
}

export function NodeSchemaTable({
  schema,
  emptyMessage = "Không có trường dữ liệu nào được định nghĩa trong schema này.",
}: NodeSchemaTableProps) {
  if (!schema || typeof schema !== "object") {
    return (
      <div className="rounded-lg border border-dashed border-border/80 p-6 text-center text-xs text-muted-foreground">
        {emptyMessage}
      </div>
    );
  }

  const properties = (schema.properties || {}) as Record<
    string,
    Record<string, unknown>
  >;
  const requiredFields = Array.isArray(schema.required)
    ? (schema.required as string[])
    : [];

  const items: SchemaPropertyItem[] = Object.entries(properties).map(
    ([name, def]) => {
      const typeStr =
        typeof def.type === "string"
          ? def.type
          : Array.isArray(def.type)
            ? def.type.join(" | ")
            : typeof def.$ref === "string"
              ? def.$ref.split("/").pop() || "object"
              : "any";

      const isRequired = requiredFields.includes(name);
      const description =
        typeof def.description === "string" ? def.description : "—";
      const defaultValue =
        def.default !== undefined ? JSON.stringify(def.default) : undefined;
      const enumValues = Array.isArray(def.enum)
        ? (def.enum as string[])
        : undefined;

      return {
        name,
        type: typeStr,
        required: isRequired,
        description,
        defaultValue,
        enumValues,
      };
    },
  );

  if (items.length === 0) {
    return (
      <div className="rounded-lg border border-dashed border-border/80 p-6 text-center text-xs text-muted-foreground">
        {emptyMessage}
      </div>
    );
  }

  return (
    <div className="space-y-2.5">
      {/* Mobile Card View (< sm) */}
      <div className="space-y-2 sm:hidden">
        {items.map((item) => (
          <div
            key={item.name}
            className="p-3 rounded-lg border border-border/70 bg-card/60 space-y-2 text-xs"
          >
            <div className="flex items-start justify-between gap-2">
              <span className="font-mono font-semibold text-foreground text-xs break-all">
                {item.name}
              </span>
              <div className="flex items-center gap-1.5 shrink-0">
                <Badge
                  variant="outline"
                  className="font-mono text-[10px] px-1.5 py-0 text-muted-foreground"
                >
                  {item.type}
                </Badge>
                {item.required ? (
                  <span className="inline-flex items-center px-1.5 py-0.5 rounded-xs text-[10px] font-medium bg-destructive/10 text-destructive">
                    Bắt buộc
                  </span>
                ) : (
                  <span className="text-[10px] text-muted-foreground">
                    Tùy chọn
                  </span>
                )}
              </div>
            </div>

            {item.defaultValue !== undefined && (
              <div className="text-[11px] text-muted-foreground flex items-center gap-1.5">
                <span>Mặc định:</span>
                <code className="font-mono bg-muted/60 px-1 py-0.5 rounded-xs text-foreground">
                  {item.defaultValue}
                </code>
              </div>
            )}

            <div className="text-[11px] text-muted-foreground leading-relaxed pt-1 border-t border-border/40">
              {item.description}
            </div>

            {item.enumValues && (
              <div className="flex flex-wrap gap-1 items-center pt-0.5">
                <span className="text-[10px] text-muted-foreground">
                  Giá trị:
                </span>
                {item.enumValues.map((val) => (
                  <code
                    key={val}
                    className="text-[10px] font-mono bg-muted/80 px-1 py-0.5 rounded-xs"
                  >
                    {val}
                  </code>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Desktop / Tablet Table View (>= sm) */}
      <div className="hidden sm:block rounded-lg border border-border/70 overflow-hidden">
        <div className="w-full overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow className="bg-muted/40 hover:bg-muted/40 text-xs">
                <TableHead className="w-[180px] font-semibold text-foreground">
                  Tên trường (Field)
                </TableHead>
                <TableHead className="w-[120px] font-semibold text-foreground">
                  Kiểu (Type)
                </TableHead>
                <TableHead className="w-[100px] font-semibold text-foreground text-center">
                  Bắt buộc
                </TableHead>
                <TableHead className="w-[140px] font-semibold text-foreground">
                  Mặc định
                </TableHead>
                <TableHead className="font-semibold text-foreground">
                  Mô tả chức năng
                </TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {items.map((item) => (
                <TableRow key={item.name} className="text-xs hover:bg-muted/30">
                  <TableCell className="font-mono font-medium text-foreground py-2.5">
                    <div className="flex items-center gap-1.5">
                      <span>{item.name}</span>
                    </div>
                  </TableCell>
                  <TableCell className="py-2.5">
                    <Badge
                      variant="outline"
                      className="font-mono text-[10px] px-1.5 py-0 text-muted-foreground"
                    >
                      {item.type}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-center py-2.5">
                    {item.required ? (
                      <span className="inline-flex items-center px-1.5 py-0.5 rounded-xs text-[10px] font-medium bg-destructive/10 text-destructive">
                        Bắt buộc
                      </span>
                    ) : (
                      <span className="text-[11px] text-muted-foreground">
                        Tùy chọn
                      </span>
                    )}
                  </TableCell>
                  <TableCell className="py-2.5">
                    {item.defaultValue !== undefined ? (
                      <code className="text-[11px] font-mono bg-muted/60 px-1 py-0.5 rounded-xs text-foreground">
                        {item.defaultValue}
                      </code>
                    ) : (
                      <span className="text-muted-foreground">—</span>
                    )}
                  </TableCell>
                  <TableCell className="text-muted-foreground py-2.5 leading-relaxed">
                    <div>{item.description}</div>
                    {item.enumValues && (
                      <div className="mt-1 flex flex-wrap gap-1 items-center">
                        <span className="text-[10px] text-muted-foreground">
                          Giá trị:
                        </span>
                        {item.enumValues.map((val) => (
                          <code
                            key={val}
                            className="text-[10px] font-mono bg-muted/80 px-1 py-0.2 rounded-xs"
                          >
                            {val}
                          </code>
                        ))}
                      </div>
                    )}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      </div>
    </div>
  );
}
