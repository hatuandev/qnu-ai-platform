import { z } from "zod";

const integerBudget = (min: number, max: number) =>
  z
    .number({ error: "Cần nhập số hợp lệ." })
    .int("Cần nhập số nguyên.")
    .min(min, `Giá trị tối thiểu là ${min}.`)
    .max(max, `Giá trị tối đa là ${max}.`);

export const retrievalPolicySchema = z
  .object({
    profile: z.enum(["legacy", "configured"]),
    dense_top_k: integerBudget(1, 100).nullable().optional(),
    lexical_top_k: integerBudget(1, 100).nullable().optional(),
    fusion_top_k: integerBudget(1, 200),
    context_top_k: integerBudget(1, 20),
    max_context_chars: integerBudget(1000, 64000),
  })
  .strict()
  .refine((p) => p.context_top_k <= p.fusion_top_k, {
    message: "Số đoạn ngữ cảnh không được lớn hơn số ứng viên hợp nhất.",
    path: ["context_top_k"],
  });

export type RetrievalPolicy = z.infer<typeof retrievalPolicySchema>;

export const defaultRetrievalPolicy: RetrievalPolicy = {
  profile: "legacy",
  dense_top_k: null,
  lexical_top_k: null,
  fusion_top_k: 30,
  context_top_k: 5,
  max_context_chars: 36000,
};

export const researchRetrievalPolicy: RetrievalPolicy = {
  ...defaultRetrievalPolicy,
  profile: "configured",
  dense_top_k: 30,
  lexical_top_k: 30,
};
