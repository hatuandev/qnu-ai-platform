import { Check, Copy } from "lucide-react";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import type { NodeManifest } from "@/services/api-client";

interface NodeManifestDialogProps {
  node: NodeManifest | null;
  onClose: () => void;
}

function formatSchema(schema: Record<string, unknown>): string {
  return JSON.stringify(schema, null, 2);
}

export function NodeManifestDialog({ node, onClose }: NodeManifestDialogProps) {
  const [isCopied, setIsCopied] = useState(false);

  if (!node) {
    return null;
  }

  const handleCopy = async () => {
    await navigator.clipboard.writeText(JSON.stringify(node, null, 2));
    setIsCopied(true);
    window.setTimeout(() => setIsCopied(false), 1800);
  };

  return (
    <Dialog open={Boolean(node)} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-h-[85vh] max-w-4xl overflow-y-auto">
        <DialogHeader className="pr-8">
          <div className="flex items-start justify-between gap-3">
            <div>
              <DialogTitle>{node.display_name}</DialogTitle>
              <DialogDescription className="mt-2">
                {node.type}@{node.version} · {node.category} · {node.status}
              </DialogDescription>
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={() => void handleCopy()}
            >
              {isCopied ? (
                <Check className="mr-1.5 size-3.5" />
              ) : (
                <Copy className="mr-1.5 size-3.5" />
              )}
              {isCopied ? "Đã sao chép" : "Sao chép JSON"}
            </Button>
          </div>
        </DialogHeader>
        <div className="grid gap-4 lg:grid-cols-3">
          <SchemaBlock title="Input schema" schema={node.input_schema} />
          <SchemaBlock title="Output schema" schema={node.output_schema} />
          <SchemaBlock title="Config schema" schema={node.config_schema} />
        </div>
      </DialogContent>
    </Dialog>
  );
}

interface SchemaBlockProps {
  title: string;
  schema: Record<string, unknown>;
}

function SchemaBlock({ title, schema }: SchemaBlockProps) {
  return (
    <section className="min-w-0 space-y-2">
      <h3 className="text-xs font-semibold text-foreground">{title}</h3>
      <pre className="max-h-80 overflow-auto rounded-lg border border-border bg-muted/40 p-3 text-[10px] leading-relaxed text-muted-foreground">
        {formatSchema(schema)}
      </pre>
    </section>
  );
}
