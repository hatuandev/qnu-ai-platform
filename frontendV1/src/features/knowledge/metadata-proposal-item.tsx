import { MoreHorizontal } from "lucide-react";
import { useId } from "react";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import type { MetadataScalar, MetadataValues } from "@/features/rag/types";
import {
  describeAnnotationTarget,
  describeMetadataValues,
} from "@/features/rag/types";
import type { CompilerMetadataProposal } from "./compilation-types";

export type ProposalEditDraft = { value: string; quote: string };

export function proposalValue(values: MetadataValues) {
  const custom = Object.entries(values.attributes ?? {})[0];
  const [field, original] = custom ??
    Object.entries(values).find(([, value]) => value != null) ?? ["", ""];
  return {
    field,
    original: original as MetadataScalar,
    custom: Boolean(custom),
  };
}

export function MetadataProposalItem({
  proposal,
  selected,
  edit,
  disabled,
  onSelected,
  onEdit,
}: {
  proposal: CompilerMetadataProposal;
  selected: boolean;
  edit?: ProposalEditDraft;
  disabled?: boolean;
  onSelected: (selected: boolean) => void;
  onEdit: (edit: ProposalEditDraft | undefined) => void;
}) {
  const id = useId();
  const { annotation, origin, source } = proposal;
  const page = source.page_number ?? source.page;
  const { original } = proposalValue(annotation.values);
  const quote = annotation.evidence[0]?.quote ?? "";
  return (
    <li className="flex items-start gap-2 py-2">
      <Checkbox
        id={id}
        checked={selected}
        disabled={disabled}
        onCheckedChange={(checked) => onSelected(checked === true)}
      />
      <div className="min-w-0 flex-1 space-y-1">
        <Label htmlFor={id}>{describeMetadataValues(annotation.values)}</Label>
        <p className="text-xs text-muted-foreground">
          {describeAnnotationTarget(annotation.target).split(" của bảng ")[0]} ·{" "}
          {source.filename}
          {page ? ` · Trang ${page}` : ""} ·{" "}
          {origin === "model" ? "AI đề xuất" : "Nhận diện từ nguồn"}
        </p>
        <blockquote className="whitespace-pre-wrap break-words border-l-2 pl-2 text-xs">
          {quote}
        </blockquote>
        {selected && edit && (
          <div className="space-y-2 pt-1">
            <div className="space-y-1">
              <Label htmlFor={`${id}-value`}>Giá trị đã đối chiếu</Label>
              <Input
                id={`${id}-value`}
                value={edit.value}
                disabled={disabled}
                onChange={(event) =>
                  onEdit({ ...edit, value: event.target.value })
                }
              />
            </div>
            <div className="space-y-1">
              <Label htmlFor={`${id}-quote`}>
                Trích đoạn nguyên văn từ cùng dẫn chứng
              </Label>
              <Textarea
                id={`${id}-quote`}
                value={edit.quote}
                maxLength={2000}
                disabled={disabled}
                onChange={(event) =>
                  onEdit({ ...edit, quote: event.target.value })
                }
              />
            </div>
          </div>
        )}
      </div>
      {selected && annotation.evidence.length === 1 && (
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button
              type="button"
              variant="ghost"
              size="icon"
              className="size-7"
              disabled={disabled}
              aria-label="Thao tác đề xuất"
            >
              <MoreHorizontal className="size-4" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuItem
              onSelect={() => onEdit({ value: String(original), quote })}
            >
              Chỉnh giá trị
            </DropdownMenuItem>
            {edit && (
              <DropdownMenuItem onSelect={() => onEdit(undefined)}>
                Dùng lại đề xuất gốc
              </DropdownMenuItem>
            )}
          </DropdownMenuContent>
        </DropdownMenu>
      )}
    </li>
  );
}
