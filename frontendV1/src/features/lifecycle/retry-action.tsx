import { useQueryClient } from "@tanstack/react-query";
import { useRef, useState } from "react";
import { v1Client } from "@/app/api/v1";
import { useV1Auth } from "@/app/auth/v1";
import { Button } from "@/components/ui/button";
import { useActionScope } from "./action-scope";
import { acceptLifecycle } from "./requests";
import type { LifecycleAction } from "./types";

/** Replays an already accepted receipt; never creates a new preview/approval. */
export function RetryLifecycleAction({
  workspaceId,
  action,
}: {
  workspaceId: string;
  action: LifecycleAction;
}) {
  const { sessionId } = useV1Auth();
  const client = useQueryClient();
  const current = useActionScope();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const active = useRef(false);
  const retry = async () => {
    if (active.current || action.status !== "pending" || !action.accepted_at)
      return;
    active.current = true;
    setBusy(true);
    setError(null);
    try {
      const result = await acceptLifecycle(v1Client, workspaceId, action);
      if (!current()) return;
      await client.cancelQueries({
        queryKey: ["v1", sessionId, "lifecycle-action", workspaceId, action.id],
      });
      if (!current()) return;
      client.setQueryData(
        ["v1", sessionId, "lifecycle-action", workspaceId, action.id],
        result,
      );
      void client.invalidateQueries({ queryKey: ["v1", sessionId] });
    } catch (cause) {
      if (current())
        setError(
          cause instanceof Error
            ? cause.message
            : "Chưa xác định được kết quả thao tác.",
        );
    } finally {
      active.current = false;
      if (current()) setBusy(false);
    }
  };
  return (
    <div className="space-y-2">
      <Button
        size="sm"
        variant="outline"
        disabled={busy}
        onClick={() => void retry()}
      >
        {busy ? "Đang tiếp tục…" : "Tiếp tục thao tác đã xác nhận"}
      </Button>
      {error ? (
        <p role="alert" className="text-sm text-destructive">
          {error}
        </p>
      ) : null}
    </div>
  );
}
