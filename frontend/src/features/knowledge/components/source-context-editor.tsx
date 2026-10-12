import { useForm } from "@tanstack/react-form";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Pencil, Save } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";
import { z } from "zod";
import { Field } from "@/components/admin/field";
import { getFactContext } from "@/components/knowledge/fact-context";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { knowledgeApi } from "@/services/knowledge-api";
import type {
  SourceArtifact,
  SourceContextEditRequest,
} from "@/types/knowledge";

type Props = {
  collectionId: string;
  sourceId: string;
  revisionId: string;
  onSaved: (id: string) => void;
};
const optionalYear = z
  .string()
  .refine(
    (value) => !value || /^(19|20)\d{2}$/.test(value),
    "Năm phải có 4 chữ số hợp lệ.",
  );
const formSchema = z.object({
  date: z.string(),
  year: optionalYear,
  subjects: z.string(),
  factYear: optionalYear,
  method: z.string().max(255),
  unit: z.string().max(128),
  reason: z
    .string()
    .trim()
    .min(5, "Hãy ghi lý do hiệu đính (ít nhất 5 ký tự)."),
});

export function SourceContextEditor(props: Props) {
  const [isOpen, setIsOpen] = useState(false);
  const query = useQuery({
    queryKey: [
      "source-context-studio",
      props.collectionId,
      props.sourceId,
      props.revisionId,
    ],
    queryFn: () =>
      knowledgeApi.getSourceStudioView(
        props.collectionId,
        props.sourceId,
        props.revisionId,
      ),
    enabled: isOpen,
  });
  return (
    <Sheet open={isOpen} onOpenChange={setIsOpen}>
      <Button variant="outline" size="sm" onClick={() => setIsOpen(true)}>
        <Pencil className="size-3.5" />
        Ngữ cảnh
      </Button>
      <SheetContent className="flex w-full flex-col sm:max-w-xl">
        <SheetHeader>
          <SheetTitle>Hiệu đính ngữ cảnh</SheetTitle>
          <SheetDescription>
            Tạo bản dự thảo từ Markdown đã lưu, không OCR lại. Cần duyệt và
            nạp/xuất bản trước khi chatbot dùng bản mới.
          </SheetDescription>
        </SheetHeader>
        {query.isLoading ? (
          <p className="p-4 text-sm">Đang tải...</p>
        ) : query.isError ? (
          <p role="alert" className="p-4 text-sm text-destructive">
            {query.error.message}
          </p>
        ) : query.data?.structured_artifact ? (
          <ContextForm
            key={`${props.revisionId}-${query.data.structured_artifact.fact_set_hash}`}
            {...props}
            artifact={query.data.structured_artifact}
            onClose={() => setIsOpen(false)}
          />
        ) : (
          <p className="p-4 text-sm">
            Bản nguồn chưa có artifact để hiệu đính.
          </p>
        )}
      </SheetContent>
    </Sheet>
  );
}

function ContextForm({
  artifact,
  onClose,
  ...props
}: Props & { artifact: SourceArtifact; onClose: () => void }) {
  const queryClient = useQueryClient();
  const [factId, setFactId] = useState("none");
  const [search, setSearch] = useState("");
  const initial = {
    date: artifact.temporal_metadata?.issued_date.value ?? "",
    year: String(artifact.temporal_metadata?.issued_year.value ?? ""),
    subjects: artifact.temporal_metadata?.subject_years.values.join(", ") ?? "",
    factYear: "",
    method: "",
    unit: "",
    reason: "",
  };
  const mutation = useMutation({
    mutationFn: (payload: SourceContextEditRequest) =>
      knowledgeApi.editSourceContext(
        props.collectionId,
        props.sourceId,
        props.revisionId,
        payload,
      ),
    onSuccess: async (revision) => {
      await queryClient.invalidateQueries({
        queryKey: ["knowledge-source", props.collectionId, props.sourceId],
      });
      await queryClient.invalidateQueries({
        queryKey: ["source-context-studio", props.collectionId, props.sourceId],
      });
      props.onSaved(revision.id);
      onClose();
      toast.success(
        "Đã tạo bản mới chờ duyệt. Chỉ mục đang phục vụ được giữ nguyên.",
      );
    },
  });
  const form = useForm({
    defaultValues: initial,
    onSubmit: async ({ value }) => {
      const parsed = formSchema.safeParse(value);
      if (!parsed.success) {
        toast.error(parsed.error.issues[0]?.message);
        return;
      }
      const subjects = value.subjects
        .split(",")
        .map((year) => year.trim())
        .filter(Boolean);
      if (subjects.some((year) => !/^(19|20)\d{2}$/.test(year))) {
        toast.error("Năm chủ đề: nhập các năm cách nhau bằng dấu phẩy.");
        return;
      }
      const payload: SourceContextEditRequest = {
        expected_fact_set_hash: artifact.fact_set_hash,
        reason: value.reason.trim(),
      };
      if (value.date !== initial.date) payload.issued_date = value.date || null;
      if (value.year !== initial.year)
        payload.issued_year = value.year ? Number(value.year) : null;
      if (value.subjects !== initial.subjects)
        payload.subject_years = subjects.map(Number);
      if (factId !== "none")
        payload.facts = [
          {
            fact_id: factId,
            year: value.factYear ? Number(value.factYear) : null,
            method: value.method || null,
            unit: value.unit || null,
          },
        ];
      try {
        await mutation.mutateAsync(payload);
      } catch (error) {
        toast.error(
          error instanceof Error ? error.message : "Không lưu được ngữ cảnh.",
        );
      }
    },
  });
  const selected = artifact.facts.find((fact) => fact.id === factId);
  const options = artifact.facts
    .filter((fact) =>
      `${fact.entity_name} ${fact.attribute_name}`
        .toLocaleLowerCase("vi")
        .includes(search.toLocaleLowerCase("vi")),
    )
    .slice(0, 50);
  const fields = [
    { name: "date", label: "Ngày ban hành (YYYY-MM-DD)" },
    { name: "year", label: "Năm ban hành" },
    { name: "subjects", label: "Năm chủ đề" },
    { name: "reason", label: "Lý do đối chiếu / hiệu đính" },
  ] as const;
  return (
    <form
      onSubmit={(event) => {
        event.preventDefault();
        void form.handleSubmit();
      }}
      className="flex min-h-0 flex-1 flex-col gap-4 p-4"
    >
      <div className="min-h-0 flex-1 space-y-4 overflow-y-auto">
        <p className="text-xs text-muted-foreground">
          Không sửa trường nào thì thao tác này nâng artifact hiện tại thành bản
          mới chờ duyệt. Không cần upload lại. Với artifact cũ, hãy nâng và mở
          lại bản mới trước khi sửa fact.
        </p>
        {fields.map((item) => (
          <form.Field key={item.name} name={item.name}>
            {(field) => (
              <Field label={item.label} htmlFor={`context-${item.name}`}>
                <Input
                  id={`context-${item.name}`}
                  value={field.state.value}
                  onChange={(event) => field.handleChange(event.target.value)}
                />
              </Field>
            )}
          </form.Field>
        ))}
        <Field label="Tìm fact" htmlFor="context-search">
          <Input
            id="context-search"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Tên thực thể, thuộc tính..."
          />
        </Field>
        <Select
          value={factId}
          onValueChange={(id) => {
            setFactId(id);
            const fact = artifact.facts.find((item) => item.id === id);
            const context = fact ? getFactContext(fact.raw_data) : null;
            form.setFieldValue(
              "factYear",
              context && context.year !== "Chưa rõ" ? context.year : "",
            );
            form.setFieldValue(
              "method",
              context && context.method !== "Không ghi riêng"
                ? context.method
                : "",
            );
            const qualifiers = fact?.raw_data.qualifiers;
            form.setFieldValue(
              "unit",
              qualifiers &&
                typeof qualifiers === "object" &&
                "unit" in qualifiers &&
                typeof qualifiers.unit === "string"
                ? qualifiers.unit
                : "",
            );
          }}
        >
          <SelectTrigger aria-label="Chọn fact">
            <SelectValue placeholder="Chọn fact" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="none">Chỉ nâng/sửa metadata</SelectItem>
            {options.map((fact) => (
              <SelectItem key={fact.id} value={fact.id}>
                {fact.entity_name} · {fact.attribute_name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <p className="text-xs text-muted-foreground">
          Danh sách tối đa 50 kết quả; tìm để thu hẹp.
        </p>
        {selected && (
          <div className="space-y-3">
            <p className="text-xs">
              Giá trị nguồn: {selected.attribute_value} · Trang{" "}
              {String(selected.raw_data.page_number ?? "?")} ·{" "}
              {String(selected.raw_data.header_path ?? "")}
            </p>
            {(
              [
                { name: "factYear", label: "Năm áp dụng của fact" },
                { name: "method", label: "Phương thức" },
                { name: "unit", label: "Đơn vị" },
              ] as const
            ).map((item) => (
              <form.Field key={item.name} name={item.name}>
                {(field) => (
                  <Field label={item.label} htmlFor={`context-${item.name}`}>
                    <Input
                      id={`context-${item.name}`}
                      value={field.state.value}
                      onChange={(event) =>
                        field.handleChange(event.target.value)
                      }
                    />
                  </Field>
                )}
              </form.Field>
            ))}
          </div>
        )}
      </div>
      <div className="flex justify-end gap-2 border-t border-border pt-3">
        <Button
          type="button"
          variant="outline"
          onClick={onClose}
          disabled={mutation.isPending}
        >
          Đóng
        </Button>
        <Button type="submit" disabled={mutation.isPending}>
          <Save className="size-3.5" />
          {mutation.isPending ? "Đang lưu" : "Tạo bản duyệt"}
        </Button>
      </div>
    </form>
  );
}
