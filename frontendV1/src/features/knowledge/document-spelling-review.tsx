import { useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { applySuggestionsToText, validateSuggestionSpan } from "./ocr-schemas";
import type { Suggestion } from "./ocr-types";
import type { SpellingPanelProps } from "./spelling-result-panel";

type Item = { id: string; page: number; suggestion: Suggestion };
type Decision = "applied" | "dismissed" | "edited";

export function DocumentSpellingReview({
  items,
  doc,
  draftChanges,
  canManage,
  onApply,
  onLocateUnit,
  onEdit,
  onSave,
}: Pick<
  SpellingPanelProps,
  "doc" | "draftChanges" | "canManage" | "onApply" | "onLocateUnit"
> & {
  items: Item[];
  onEdit: (id: string, text: string) => boolean;
  onSave: () => void;
}) {
  const [decisions, setDecisions] = useState<Record<string, Decision>>({});
  const [selected, setSelected] = useState<string>();
  const [filter, setFilter] = useState("pending");
  const [edit, setEdit] = useState<string | null>(null);
  const [blocked, setBlocked] = useState(false);
  const visible = items.filter(({ id }) =>
    filter === "applied"
      ? decisions[id] === "applied" || decisions[id] === "edited"
      : filter === "dismissed"
        ? decisions[id] === "dismissed"
        : !decisions[id],
  );
  const active = visible.find(({ id }) => id === selected) ?? visible[0];
  const locatedId = useRef<string | undefined>(undefined);
  useEffect(() => {
    if (!active || locatedId.current === active.id) return;
    locatedId.current = active.id;
    onLocateUnit?.({
      evidenceId: active.suggestion.evidence_id,
      page: active.page,
    });
  }, [active, onLocateUnit]);
  const unit = doc.units.find(
    (row) => row.evidence_id === active?.suggestion.evidence_id,
  );
  const text = unit ? (draftChanges.get(unit.evidence_id) ?? unit.text) : "";

  const select = (item?: Item) => {
    setSelected(item?.id);
    setEdit(null);
    setBlocked(false);
  };
  const decide = (item: Item, decision: Decision) => {
    setDecisions((previous) => ({ ...previous, [item.id]: decision }));
    const index = items.indexOf(item);
    select(
      [...items.slice(index + 1), ...items.slice(0, index)].find(
        ({ id }) => !decisions[id],
      ),
    );
  };
  const resolveActiveSpan = () => {
    if (!active || !unit) return;
    const suggestion = active.suggestion;
    const prior = items
      .filter(
        ({ id, suggestion: previous }) =>
          decisions[id] === "applied" &&
          previous.evidence_id === unit.evidence_id,
      )
      .map((item) => item.suggestion);
    const expected = applySuggestionsToText(unit.text, prior);
    if (
      expected.updatedText !== text ||
      prior.some(
        (previous) =>
          previous.start < suggestion.end && previous.end > suggestion.start,
      )
    ) {
      return;
    }
    const offset = prior
      .filter((previous) => previous.end <= suggestion.start)
      .reduce(
        (total, previous) =>
          total +
          Array.from(previous.replacement).length -
          (previous.end - previous.start),
        0,
      );
    const rebased = {
      ...suggestion,
      start: suggestion.start + offset,
      end: suggestion.end + offset,
    };
    return validateSuggestionSpan(text, rebased) ? rebased : undefined;
  };
  const span = filter === "pending" ? resolveActiveSpan() : undefined;
  const points = span ? Array.from(text) : [];
  const apply = () => {
    if (active && span && onApply(span)) decide(active, "applied");
    else setBlocked(true);
  };

  return (
    <section
      className="space-y-3"
      aria-label="Rà soát chính tả toàn bộ tài liệu"
    >
      <h3 className="text-sm font-semibold">
        Rà soát chính tả toàn bộ tài liệu
      </h3>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <label className="text-xs">
          Hiển thị{" "}
          <select
            className="rounded-md border bg-background p-1"
            value={filter}
            onChange={(event) => {
              setFilter(event.target.value);
              select();
            }}
          >
            <option value="pending">Chưa duyệt</option>
            <option value="applied">Đã áp dụng</option>
            <option value="dismissed">Đã bỏ qua</option>
          </select>
        </label>
        <Button
          size="sm"
          variant="outline"
          disabled={!canManage || !draftChanges.size}
          onClick={onSave}
        >
          Lưu thay đổi
        </Button>
      </div>
      <p className="text-xs text-muted-foreground" role="status">
        Đã duyệt {Object.keys(decisions).length}/{items.length} gợi ý
      </p>
      <div className="grid gap-3 xl:grid-cols-[minmax(8rem,1fr)_2fr]">
        <ul
          className="max-h-56 space-y-1 overflow-auto"
          aria-label="Danh sách gợi ý theo trang"
        >
          {visible.map((item) => (
            <li key={item.id}>
              <button
                type="button"
                aria-current={active?.id === item.id}
                className="block w-full rounded-md px-2 py-1.5 text-left text-xs hover:bg-muted aria-[current=true]:bg-muted"
                onClick={() => select(item)}
              >
                <span className="block text-muted-foreground">
                  Trang {item.page}
                </span>
                {item.suggestion.original} → {item.suggestion.replacement}
              </button>
            </li>
          ))}
        </ul>
        {active && unit ? (
          <div className="min-w-0 space-y-2 text-sm">
            <p className="text-xs text-muted-foreground">Trang {active.page}</p>
            <p className="break-words">
              <del className="text-destructive">
                {active.suggestion.original}
              </del>
              {" → "}
              <strong className="text-primary">
                {active.suggestion.replacement}
              </strong>
            </p>
            <p className="whitespace-pre-wrap break-words">
              {span ? (
                <>
                  {points.slice(0, span.start).join("")}
                  <mark className="rounded-sm bg-warning/30 font-semibold text-foreground underline decoration-warning underline-offset-2">
                    {points.slice(span.start, span.end).join("")}
                  </mark>
                  {points.slice(span.end).join("")}
                </>
              ) : (
                text
              )}
            </p>
            {blocked && (
              <p role="alert" className="text-xs text-destructive">
                Đoạn văn đã thay đổi. Hãy chỉnh tay hoặc bỏ qua.
              </p>
            )}
            {edit !== null && (
              <Textarea
                aria-label="Văn bản chỉnh tay"
                value={edit}
                onChange={(event) => setEdit(event.target.value)}
              />
            )}
            <div className="flex flex-wrap gap-2">
              <Button
                size="sm"
                variant="ghost"
                onClick={() =>
                  onLocateUnit?.({
                    evidenceId: unit.evidence_id,
                    page: active.page,
                    showImage: true,
                  })
                }
              >
                Đối chiếu ảnh
              </Button>
              {canManage && filter === "pending" && (
                <>
                  {edit === null ? (
                    <>
                      <Button size="sm" onClick={apply}>
                        Áp dụng
                      </Button>
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => setEdit(text)}
                      >
                        Chỉnh tay
                      </Button>
                    </>
                  ) : (
                    <>
                      <Button
                        size="sm"
                        disabled={edit === text}
                        onClick={() => {
                          if (onEdit(unit.evidence_id, edit))
                            decide(active, "edited");
                        }}
                      >
                        Lưu vào nháp
                      </Button>
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => setEdit(null)}
                      >
                        Hủy chỉnh tay
                      </Button>
                    </>
                  )}
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => decide(active, "dismissed")}
                  >
                    Bỏ qua
                  </Button>
                </>
              )}
            </div>
          </div>
        ) : (
          <p className="text-sm text-muted-foreground">
            Không có gợi ý trong mục này.
          </p>
        )}
      </div>
    </section>
  );
}
