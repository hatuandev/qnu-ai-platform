import { useId } from "react";
import { Field, FieldLabel } from "@/components/admin/field";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useMetadataFacetsQuery } from "@/features/knowledge/index-queries";
import type { MetadataScalar } from "./types";

type Attributes = Record<string, MetadataScalar>;

export function MetadataFacetFields({
  workspaceId,
  collectionId,
  attributes,
  onChange,
  disabled,
}: {
  workspaceId: string;
  collectionId: string;
  attributes?: Attributes | null;
  onChange: (next: Attributes) => void;
  disabled?: boolean;
}) {
  const id = useId();
  const query = useMetadataFacetsQuery(workspaceId, collectionId);
  const selected = attributes ?? {};
  const catalog = new Map(Object.entries(query.data?.attributes ?? {}));
  for (const [key, value] of Object.entries(selected)) {
    const available = catalog.get(key) ?? [];
    if (!available.includes(value)) catalog.set(key, [...available, value]);
  }
  const fields = Array.from(catalog);
  if (!fields.length && !query.isError && !query.isPending) return null;

  return (
    <div className="col-span-full space-y-2">
      {query.isError && (
        <p role="status" className="text-xs text-muted-foreground">
          Chưa tải được thuộc tính đã xác nhận.
        </p>
      )}
      {query.isPending && (
        <p role="status" className="text-xs text-muted-foreground">
          Đang tải thuộc tính đã xác nhận…
        </p>
      )}
      {query.data?.truncated && (
        <p className="text-xs text-muted-foreground">
          Đang hiển thị một phần danh mục thuộc tính.
        </p>
      )}
      {fields.length > 0 && (
        <div className="grid gap-3 sm:grid-cols-2">
          {fields.map(([key, values], index) => (
            <Field key={key}>
              <FieldLabel htmlFor={`${id}-${index}`}>{key}</FieldLabel>
              <Select
                value={
                  Object.hasOwn(selected, key)
                    ? JSON.stringify(selected[key])
                    : "all"
                }
                disabled={
                  disabled ||
                  (Object.keys(selected).length >= 20 &&
                    !Object.hasOwn(selected, key))
                }
                onValueChange={(option) => {
                  const value = values.find(
                    (entry) => JSON.stringify(entry) === option,
                  );
                  if (value !== undefined) {
                    onChange({ ...selected, [key]: value });
                  } else {
                    onChange(
                      Object.fromEntries(
                        Object.entries(selected).filter(
                          ([label]) => label !== key,
                        ),
                      ),
                    );
                  }
                }}
              >
                <SelectTrigger id={`${id}-${index}`} className="w-full text-xs">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Không giới hạn</SelectItem>
                  {values.map((value) => (
                    <SelectItem
                      key={JSON.stringify(value)}
                      value={JSON.stringify(value)}
                    >
                      {String(value)}
                      {values.some(
                        (other) =>
                          typeof other !== typeof value &&
                          String(other) === String(value),
                      )
                        ? typeof value === "string"
                          ? " (văn bản)"
                          : " (số/logic)"
                        : ""}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </Field>
          ))}
        </div>
      )}
    </div>
  );
}
