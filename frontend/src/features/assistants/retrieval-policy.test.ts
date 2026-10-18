import assert from "node:assert/strict";
import test from "node:test";
import {
  defaultRetrievalPolicy,
  researchRetrievalPolicy,
  retrievalPolicySchema,
} from "./retrieval-policy";

test("legacy remains default; experiment is explicit", () => {
  assert.equal(defaultRetrievalPolicy.profile, "legacy");
  assert.equal(researchRetrievalPolicy.profile, "configured");
  assert.deepEqual(
    [
      researchRetrievalPolicy.dense_top_k,
      researchRetrievalPolicy.lexical_top_k,
      researchRetrievalPolicy.fusion_top_k,
      researchRetrievalPolicy.context_top_k,
    ],
    [30, 30, 30, 5],
  );
});
test("budgets reject NaN, fractions, oversize and context beyond fusion", () => {
  for (const patch of [
    { dense_top_k: Number.NaN },
    { lexical_top_k: 1.5 },
    { fusion_top_k: 201 },
    { context_top_k: 21 },
    { fusion_top_k: 3 },
    { max_context_chars: 999 },
  ]) {
    assert.equal(
      retrievalPolicySchema.safeParse({ ...researchRetrievalPolicy, ...patch })
        .success,
      false,
    );
  }
});
test("nullable branch budgets preserve legacy retrieval_limit fallback", () => {
  const parsed = retrievalPolicySchema.parse({
    ...researchRetrievalPolicy,
    dense_top_k: null,
    lexical_top_k: null,
  });
  assert.equal(parsed.dense_top_k, null);
});
