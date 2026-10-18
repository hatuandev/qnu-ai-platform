import assert from "node:assert/strict";
import test from "node:test";
import { hasPendingModelPolicy } from "./model-policy-state";

const saved = {
  primary_model: "same-alias",
  preferred_provider_id: "internal",
  fallback_model: "fallback",
  fallback_provider_id: "secondary",
  temperature: 0.2,
  max_tokens: 8000,
  thinking_budget: 0,
};

test("saved policy has no pending change", () => {
  assert.equal(hasPendingModelPolicy({ ...saved }, saved), false);
});

test("changing provider for the same model is a pending change", () => {
  assert.equal(
    hasPendingModelPolicy({ ...saved, preferred_provider_id: "cloud" }, saved),
    true,
  );
});

test("fallback and generation changes remain pending until saved", () => {
  const draft = { ...saved, fallback_model: "new", max_tokens: 4000 };
  assert.equal(hasPendingModelPolicy(draft, saved), true);
  assert.equal(hasPendingModelPolicy(draft, draft), false);
});
