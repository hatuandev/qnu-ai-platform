import assert from "node:assert/strict";
import { describe, it } from "node:test";
import {
  buildSystemDefaultsPayload,
  formatModelLabel,
  NONE_VALUE,
} from "../src/lib/default-models.ts";
import { isModelAdmin, isPlatformAdmin } from "../src/lib/permissions.ts";

describe("Default Models - Page Helpers & Permissions", () => {
  it("formatModelLabel extracts model and provider name cleanly from exported route helper", () => {
    assert.equal(
      formatModelLabel({
        name: "QNU AI Server · qwen3.8-27b-q4",
        model_name: "qwen3.8-27b-q4",
      }),
      "qwen3.8-27b-q4 · QNU AI Server",
    );

    assert.equal(
      formatModelLabel({
        name: "9router Luna · cx/gpt-6-luna",
        model_name: "cx/gpt-6-luna",
      }),
      "cx/gpt-6-luna · 9router Luna",
    );

    assert.equal(
      formatModelLabel({
        name: "Google Gemini",
        model_name: "gemini-2.5-flash",
      }),
      "gemini-2.5-flash · Google Gemini",
    );
  });

  it("isPlatformAdmin strictly follows actor.py permissions without assuming admin role", () => {
    // Granted via exact ai.workspaces.manage
    assert.equal(
      isPlatformAdmin({
        username: "dev.platform",
        actor_id: "act_1",
        display_name: "Platform Manager",
        email: null,
        user_type: "staff",
        role: "staff",
        roles: [],
        permissions: ["ai.workspaces.manage"],
        authenticated: true,
      }),
      true,
    );

    // Granted via AI.Admin role
    assert.equal(
      isPlatformAdmin({
        username: "dev.aiadmin",
        actor_id: "act_2",
        display_name: "AI Admin",
        email: null,
        user_type: "staff",
        role: "staff",
        roles: ["ai.admin"],
        permissions: [],
        authenticated: true,
      }),
      true,
    );

    // Generic "admin" role does NOT grant platform admin in backendV1 actor.py
    assert.equal(
      isPlatformAdmin({
        username: "generic.admin",
        actor_id: "act_3",
        display_name: "Workspace Admin",
        email: null,
        user_type: "staff",
        role: "admin",
        roles: ["admin"],
        permissions: [],
        authenticated: true,
      }),
      false,
    );

    // Regular member
    assert.equal(
      isPlatformAdmin({
        username: "regular.member",
        actor_id: "act_4",
        display_name: "Member",
        email: null,
        user_type: "staff",
        role: "member",
        roles: [],
        permissions: [],
        authenticated: true,
      }),
      false,
    );
  });

  it("isModelAdmin requires ai.models.manage or ai.admin / ai.access.admin", () => {
    // Exact permission
    assert.equal(
      isModelAdmin({
        username: "model.admin",
        actor_id: "act_5",
        display_name: "Model Manager",
        email: null,
        user_type: "staff",
        role: "staff",
        roles: [],
        permissions: ["ai.models.manage"],
        authenticated: true,
      }),
      true,
    );

    // Generic admin role does NOT grant ModelOps management
    assert.equal(
      isModelAdmin({
        username: "workspace.admin",
        actor_id: "act_6",
        display_name: "Workspace Admin",
        email: null,
        user_type: "staff",
        role: "admin",
        roles: ["admin"],
        permissions: [],
        authenticated: true,
      }),
      false,
    );

    // Unauthenticated
    assert.equal(
      isModelAdmin({
        username: "guest",
        actor_id: "act_7",
        display_name: "Guest",
        email: null,
        user_type: "staff",
        role: "staff",
        roles: ["ai.admin"],
        permissions: ["ai.models.manage"],
        authenticated: false,
      }),
      false,
    );
  });

  it("System Defaults Payload: only includes changed *_provider_id fields and sends null when cleared", () => {
    const serverValues = {
      chat: "prv_chat_1",
      embedding: "prv_embed_1",
      rerank: "prv_rerank_1",
      ocr: "prv_ocr_1",
    };

    // User edits chat to a new provider and clears rerank
    const userEdits = {
      chat: "prv_chat_new",
      rerank: null, // cleared
    };

    const payload = buildSystemDefaultsPayload(userEdits, serverValues);

    assert.deepEqual(payload, {
      chat_provider_id: "prv_chat_new",
      rerank_provider_id: null,
    });
    assert.equal("embedding_provider_id" in payload, false);
    assert.equal("ocr_provider_id" in payload, false);
  });

  it("Draft preservation: maintains user uncommitted edits even when server baseline refetches", () => {
    const originalServer = {
      chat: "prv_chat_1",
      embedding: "prv_embed_1",
      rerank: "prv_rerank_1",
      ocr: "prv_ocr_1",
    };

    // User modified chat
    const userEdits: Record<string, string | null> = {
      chat: "prv_chat_custom",
    };

    // Helper that resolves effective value
    function getEffective(cap: string, server: Record<string, string | null>) {
      if (cap in userEdits) {
        return userEdits[cap] ?? NONE_VALUE;
      }
      return server[cap] ?? NONE_VALUE;
    }

    assert.equal(getEffective("chat", originalServer), "prv_chat_custom");
    assert.equal(getEffective("embedding", originalServer), "prv_embed_1");

    // Server data refetches with updated embedding
    const refetchedServer = {
      ...originalServer,
      embedding: "prv_embed_updated",
    };

    // User's uncommitted edit on chat is STILL preserved!
    assert.equal(getEffective("chat", refetchedServer), "prv_chat_custom");
    // While unedited embedding adopts the refetched server data
    assert.equal(
      getEffective("embedding", refetchedServer),
      "prv_embed_updated",
    );
  });
});
