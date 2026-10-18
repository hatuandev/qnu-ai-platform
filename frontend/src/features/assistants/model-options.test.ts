import assert from "node:assert/strict";
import test from "node:test";
import type { AssistantEditForm } from "../../components/assistants/types.ts";
import type { AssistantLifecycleConfig } from "../../types/assistants.ts";
import type { ModelProvider } from "../../types/modelops.ts";
import {
  buildAssistantModelOptions,
  selectedModelValue,
} from "./model-options";
import { buildAssistantPolicyUpdate } from "./policy-update";

test("catalog separates roles and keeps duplicate aliases owned by different providers", () => {
  const providers = [
    {
      id: "ai",
      name: "AI server",
      is_active: true,
      models: ["opaque-encoder", "opaque-ranker"],
      model_specs: {
        "opaque-encoder": { type: "embedding" },
        "opaque-ranker": { type: "reranker" },
      },
    },
    { id: "a", name: "Gateway A", is_active: true, models: ["alias"] },
    { id: "b", name: "Gateway B", is_active: true, models: ["alias"] },
  ] as ModelProvider[];
  assert.equal(
    buildAssistantModelOptions(providers, "reranker")[0].providerId,
    "ai",
  );
  const chat = buildAssistantModelOptions(providers, "chat");
  assert.equal(chat.length, 2);
  assert.notEqual(chat[0].value, chat[1].value);
});

test("editing chat policy preserves reranker provider, model and zero threshold", () => {
  const current = {
    model_policy: {},
    knowledge_policy: {
      reranker_policy: {
        provider_id: "ai",
        model_name: "opaque-ranker",
        score_threshold: 0,
      },
    },
  } as AssistantLifecycleConfig;
  const form = {
    primary_model: "alias",
    fallback_model: "backup",
    temperature: 0.2,
    max_tokens: 1000,
    thinking_budget: 0,
    reranker_score_threshold: 0,
  } as AssistantEditForm;
  const update = buildAssistantPolicyUpdate(current, form, []);
  assert.equal(update.knowledge_policy.reranker_policy?.provider_id, "ai");
  assert.equal(
    update.knowledge_policy.reranker_policy?.model_name,
    "opaque-ranker",
  );
  assert.equal(update.knowledge_policy.reranker_policy?.score_threshold, 0);
});

test("saved alias remains visible even if provider catalog no longer lists it", () => {
  const options = buildAssistantModelOptions([], "chat", [
    { model: "new-alias", providerId: "proxy" },
  ]);
  assert.equal(options[0].model, "new-alias");
  assert.equal(
    selectedModelValue(options, "new-alias", "proxy"),
    options[0].value,
  );
});
test("declared capabilities keep embedding and reranking out of LLM choices", () => {
  const providers = [
    {
      id: "multi",
      name: "Multi-purpose provider",
      code: "multi",
      type: "custom",
      circuit_breaker_status: "CLOSED",
      latency_ms: 0,
      failure_rate: 0,
      is_active: true,
      models: ["opaque-a", "opaque-b", "opaque-c"],
      model_capabilities: {
        "opaque-a": { probe_role: "chat", vision: false, reasoning: false },
        "opaque-b": {
          probe_role: "embedding",
          vision: false,
          reasoning: false,
        },
        "opaque-c": { probe_role: "reranker", vision: false, reasoning: false },
      },
    },
  ] as ModelProvider[];
  assert.deepEqual(
    buildAssistantModelOptions(providers, "chat").map((m) => m.model),
    ["opaque-a"],
  );
  assert.deepEqual(
    buildAssistantModelOptions(providers, "reranker").map((m) => m.model),
    ["opaque-c"],
  );
});
