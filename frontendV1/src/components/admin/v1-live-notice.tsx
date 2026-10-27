import { Database, Info } from "lucide-react";
import { Alert, AlertDescription } from "@/components/ui/alert";

/**
 * Shown on `/workspaces` and `/modelops` only.
 *
 * These screens read and write real backendV1 data through a Bearer session, so
 * they must not carry the "Bản mẫu KTX" label used by the copied template.
 */
export function V1LiveNotice() {
  return (
    <Alert className="mb-6">
      <Info className="size-4" />
      <AlertDescription className="flex flex-wrap items-center gap-x-2 gap-y-1">
        <Database className="size-3.5 shrink-0" />
        <span>
          QNU AI v1alpha1 · dữ liệu thật từ backendV1 qua phiên Bearer của bạn.
          Các mục KTX còn lại trong menu vẫn là bản mẫu và API của chúng bị
          chặn.
        </span>
      </AlertDescription>
    </Alert>
  );
}
