import { useId, useRef, useState } from "react";
import { v1Client } from "@/app/api/v1";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Label } from "@/components/ui/label";
import { searchCollection } from "@/features/knowledge/index-requests";
import type { SearchHit } from "@/features/knowledge/index-types";
import {
  hitTitle,
  SearchEvidenceSheet,
} from "@/features/knowledge/search-evidence";
import { useActionScope } from "@/features/lifecycle/action-scope";
import type { IndexManifest } from "./types";

export function GoldPicker({
  workspaceId,
  collectionId,
  query,
  manifest,
  manifestSha,
  selected,
  onChange,
  disabled,
  documentIds,
}: {
  workspaceId: string;
  collectionId: string;
  query: string;
  manifest: IndexManifest;
  manifestSha: string;
  selected: SearchHit[];
  onChange: (hits: SearchHit[]) => void;
  disabled: boolean;
  documentIds?: string[];
}) {
  const current = useActionScope();
  const fieldId = useId();
  const active = useRef(false);
  const [hits, setHits] = useState<SearchHit[] | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [inspecting, setInspecting] = useState<SearchHit | null>(null);
  const search = async () => {
    if (active.current || disabled || !query.trim()) return;
    active.current = true;
    setBusy(true);
    setError(null);
    setHits(null);
    try {
      const result = await searchCollection(
        v1Client,
        workspaceId,
        collectionId,
        {
          query,
          top_k: 50,
          mode: "hybrid",
          candidate_k: 50,
          rrf_k: 60,
          document_ids: documentIds?.length ? documentIds : null,
        },
      );
      if (!current()) return;
      const sealed = new Set(manifest.chunks.map((c) => c.id));
      if (
        result.index_run_id !== manifest.run_id ||
        result.trace.manifest_sha256 !== manifestSha ||
        result.hits.some(
          (hit) =>
            !sealed.has(hit.chunk_id) ||
            (documentIds?.length && !documentIds.includes(hit.document_id)),
        )
      )
        throw new Error(
          "Chỉ mục đã thay đổi hoặc kết quả khác snapshot. Hãy tải lại snapshot trước khi gán nhãn.",
        );
      setHits(result.hits);
    } catch (cause) {
      if (current())
        setError(
          cause instanceof Error
            ? cause.message
            : "Không tìm được đoạn để gán nhãn.",
        );
    } finally {
      active.current = false;
      if (current()) setBusy(false);
    }
  };
  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-2">
        <Button
          type="button"
          size="sm"
          variant="outline"
          disabled={disabled || busy || !query.trim()}
          onClick={() => void search()}
        >
          {busy ? "Đang tìm đoạn…" : "Tìm đoạn làm đáp án chuẩn"}
        </Button>
        <span className="text-xs text-muted-foreground">
          Đã chọn {selected.length}/100 đoạn
        </span>
      </div>
      <p className="text-xs text-muted-foreground">
        Tìm tối đa 50 đoạn mỗi lần. Kết quả gợi ý có thể bỏ sót; người gán nhãn
        cần đọc và kiểm tra độ đầy đủ. Không chọn đoạn nào sẽ được ghi là nhãn
        rỗng, không tính điểm chất lượng.
      </p>
      {error ? (
        <p role="alert" className="text-sm text-destructive">
          {error}
        </p>
      ) : null}
      {selected.length ? (
        <ul aria-label="Đáp án chuẩn đã chọn" className="space-y-2">
          {selected.map((hit) => (
            <li
              key={hit.chunk_id}
              className="flex flex-wrap items-center justify-between gap-2 rounded-lg border p-2"
            >
              <span className="text-sm min-w-0 break-words">
                {hitTitle(hit)} · {hit.text.slice(0, 100)}
              </span>
              <div className="flex gap-2">
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => setInspecting(hit)}
                >
                  Đọc
                </Button>
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  disabled={disabled}
                  onClick={() =>
                    onChange(
                      selected.filter((v) => v.chunk_id !== hit.chunk_id),
                    )
                  }
                >
                  Bỏ chọn
                </Button>
              </div>
            </li>
          ))}
        </ul>
      ) : null}
      {hits?.length === 0 ? (
        <p className="text-sm">Không tìm thấy đoạn phù hợp.</p>
      ) : null}
      {hits ? (
        <ul
          aria-label="Đoạn gợi ý"
          className="space-y-2 max-h-96 overflow-y-auto"
        >
          {hits.map((hit) => (
            <li key={hit.chunk_id} className="rounded-lg border p-3 space-y-2">
              <div className="flex items-start gap-2">
                <Checkbox
                  id={`${fieldId}-${hit.chunk_id}`}
                  checked={selected.some((v) => v.chunk_id === hit.chunk_id)}
                  disabled={
                    disabled ||
                    (selected.length >= 100 &&
                      !selected.some((v) => v.chunk_id === hit.chunk_id))
                  }
                  onCheckedChange={(checked) =>
                    onChange(
                      checked === true
                        ? [
                            ...selected.filter(
                              (v) => v.chunk_id !== hit.chunk_id,
                            ),
                            hit,
                          ]
                        : selected.filter((v) => v.chunk_id !== hit.chunk_id),
                    )
                  }
                />
                <Label
                  htmlFor={`${fieldId}-${hit.chunk_id}`}
                  className="text-sm leading-relaxed"
                >
                  {hitTitle(hit)}
                </Label>
              </div>
              <p className="text-sm line-clamp-4 whitespace-pre-wrap">
                {hit.text}
              </p>
              <Button
                type="button"
                size="sm"
                variant="outline"
                onClick={() => setInspecting(hit)}
              >
                Đọc đầy đủ và nguồn
              </Button>
            </li>
          ))}
        </ul>
      ) : null}
      {inspecting ? (
        <SearchEvidenceSheet
          key={inspecting.chunk_id}
          workspaceId={workspaceId}
          collectionId={collectionId}
          hit={inspecting}
          onClose={() => setInspecting(null)}
        />
      ) : null}
    </div>
  );
}
