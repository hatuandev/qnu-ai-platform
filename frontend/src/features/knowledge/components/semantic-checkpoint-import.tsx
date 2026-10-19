import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { extractErrorMessage } from "@/services/knowledge-api";

export function SemanticCheckpointImport({
  canImport,
  onImport,
}: {
  canImport: boolean;
  onImport: (checkpoint: unknown, comment: string) => Promise<void>;
}) {
  const [checkpoint, setCheckpoint] = useState<unknown>(null);
  const [comment, setComment] = useState("");
  const [error, setError] = useState("");
  const [isImporting, setIsImporting] = useState(false);
  return (
    <details className="space-y-3 rounded-lg border p-3">
      <summary>Nhập đề xuất từ checkpoint đã đối soát</summary>
      <p>
        Chọn đúng bản nháp trước khi nhập. Nhập chỉ tạo đề xuất chờ đối chiếu;
        mỗi quyết định vẫn cần bạn thực hiện.
      </p>
      {!canImport && (
        <p>Cần đăng nhập bằng tài khoản có quyền hiệu đính nguồn.</p>
      )}
      <Input
        type="file"
        accept=".json,application/json"
        aria-label="Gói đề xuất checkpoint"
        disabled={!canImport || isImporting}
        onChange={async (event) => {
          setCheckpoint(null);
          setError("");
          const file = event.target.files?.[0];
          if (!file) return;
          try {
            if (file.size > 8 * 1024 * 1024)
              throw new Error("Gói đề xuất vượt giới hạn 8 MiB.");
            const value: unknown = JSON.parse(await file.text());
            if (
              !value ||
              typeof value !== "object" ||
              !("contract" in value) ||
              value.contract !== "qnu-semantic-checkpoint-v1"
            ) {
              throw new Error(
                "Chọn file import-package.json của gói đã đối soát.",
              );
            }
            setCheckpoint(value);
          } catch (cause) {
            setError(extractErrorMessage(cause, "Không đọc được checkpoint."));
          }
        }}
      />
      <Textarea
        aria-label="Căn cứ nhập checkpoint"
        value={comment}
        disabled={!canImport || isImporting}
        placeholder="Ghi căn cứ chọn đúng nguồn và bản nháp"
        onChange={(event) => setComment(event.target.value)}
      />
      <Button
        type="button"
        variant="outline"
        disabled={
          !canImport || !checkpoint || comment.trim().length < 3 || isImporting
        }
        onClick={async () => {
          setIsImporting(true);
          setError("");
          try {
            await onImport(checkpoint, comment.trim());
            setCheckpoint(null);
            setComment("");
          } catch (cause) {
            setError(
              extractErrorMessage(
                cause,
                "Không nhập được đề xuất; hãy kiểm tra lại revision và quyền.",
              ),
            );
          } finally {
            setIsImporting(false);
          }
        }}
      >
        {isImporting
          ? "Đang kiểm chứng nguồn..."
          : "Kiểm chứng và tạo đề xuất chờ duyệt"}
      </Button>
      {error && (
        <p role="alert" className="text-destructive">
          {error}
        </p>
      )}
    </details>
  );
}
