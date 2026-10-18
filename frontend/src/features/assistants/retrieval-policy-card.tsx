import { SlidersHorizontal } from "lucide-react";
import { Field } from "@/components/admin/field";
import type { AssistantEditForm } from "@/components/assistants/types";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  defaultRetrievalPolicy,
  type RetrievalPolicy,
  researchRetrievalPolicy,
  retrievalPolicySchema,
} from "./retrieval-policy";

const fields = [
  ["dense_top_k", "Ứng viên ngữ nghĩa", 100],
  ["lexical_top_k", "Ứng viên từ khóa", 100],
  ["fusion_top_k", "Sau hợp nhất RRF", 200],
  ["context_top_k", "Đoạn ngữ cảnh chính", 20],
  ["max_context_chars", "Ngân sách ký tự", 64000],
] as const;

export function RetrievalPolicyCard({
  form,
  onChange,
}: {
  form: AssistantEditForm;
  onChange: (updated: AssistantEditForm) => void;
}) {
  const policy = form.retrieval_policy ?? defaultRetrievalPolicy;
  const update = (patch: Partial<RetrievalPolicy>) =>
    onChange({ ...form, retrieval_policy: { ...policy, ...patch } });
  const validation = retrievalPolicySchema.safeParse(policy);
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-sm">
          <SlidersHorizontal className="size-4 text-primary" />
          Tìm kiếm &amp; ngữ cảnh
        </CardTitle>
        <CardDescription>
          Top K tính theo đoạn dữ liệu, không phải số tài liệu hoặc số token.
          Chỉ áp dụng sau khi lưu cấu hình.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <Field htmlFor="retrieval-profile" label="Chế độ">
          <Select
            value={policy.profile}
            onValueChange={(profile: RetrievalPolicy["profile"]) =>
              update({ profile })
            }
          >
            <SelectTrigger id="retrieval-profile">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="legacy">Hiện tại (đối chứng)</SelectItem>
              <SelectItem value="configured">Tùy chỉnh Top K</SelectItem>
            </SelectContent>
          </Select>
        </Field>
        {policy.profile === "legacy" ? (
          <p className="text-sm text-muted-foreground">
            Giữ luồng hiện tại: lấy 8/12 ứng viên mỗi nhánh theo ý định; số giữ
            sau xếp hạng dùng cấu hình reranker bên dưới. Nhánh evidence dùng
            ngân sách riêng nếu đã bật.
          </p>
        ) : (
          <>
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              {fields.map(([key, label, max]) => (
                <Field
                  key={key}
                  htmlFor={`retrieval-${key}`}
                  label={label}
                  hint={
                    key === "dense_top_k" || key === "lexical_top_k"
                      ? `Để trống dùng retrieval_limit (${form.retrieval_limit ?? 10}).`
                      : undefined
                  }
                >
                  <Input
                    id={`retrieval-${key}`}
                    type="number"
                    min={key === "max_context_chars" ? 1000 : 1}
                    max={max}
                    step={1}
                    value={policy[key] ?? ""}
                    onChange={(e) =>
                      update({
                        [key]:
                          e.target.value === "" &&
                          (key === "dense_top_k" || key === "lexical_top_k")
                            ? null
                            : Number(e.target.value),
                      })
                    }
                  />
                </Field>
              ))}
            </div>
            {!validation.success && (
              <p role="alert" className="text-sm text-destructive">
                {validation.error.issues
                  .map((issue) => issue.message)
                  .join(" ")}
              </p>
            )}
            <p className="text-sm text-muted-foreground">
              Facts, hàng bảng và ngữ cảnh phụ có thể bổ sung bằng chứng. Luồng
              liệt kê đầy đủ không bị cắt theo Top K; ngân sách ký tự không cho
              phép cắt ngang một đoạn chứng cứ.
            </p>
          </>
        )}
        <Button
          type="button"
          variant="outline"
          onClick={() =>
            onChange({
              ...form,
              retrieval_policy: { ...researchRetrievalPolicy },
            })
          }
        >
          Dùng mốc 30/30/30/5
        </Button>
        <p className="text-xs text-muted-foreground">
          Đây là mốc thử nghiệm từ bộ mã tham khảo, không phải cấu hình đã chứng
          minh tối ưu cho kho này. Chọn “Hiện tại” để quay về đối chứng.
        </p>
      </CardContent>
    </Card>
  );
}
