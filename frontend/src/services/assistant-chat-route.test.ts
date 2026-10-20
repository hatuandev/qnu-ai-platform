import assert from "node:assert/strict";
import test from "node:test";
import {
  assistantChatUrl,
  ownedConversationSession,
} from "./assistant-chat-route";

test("ordinary chat retains the existing endpoint and never opts into debug", () => {
  assert.equal(
    assistantChatUrl("admissions"),
    "/platform/v1alpha1/assistants/admissions/chat",
  );
  assert.equal(
    assistantChatUrl("admissions", false),
    assistantChatUrl("admissions"),
  );
});
test("admin debug is explicit and assistant references remain one URL segment", () => {
  assert.equal(
    assistantChatUrl("admissions", true),
    "/platform/v1alpha1/assistants/admissions/chat?debug=true",
  );
  assert.equal(
    assistantChatUrl("a/b?debug=true"),
    "/platform/v1alpha1/assistants/a%2Fb%3Fdebug%3Dtrue/chat",
  );
});

test("thread switches restore only their own server session and legacy history starts fresh", () => {
  const a = {
    assistantCode: "one",
    runtimeSession: { conversationId: "a", conversationToken: "grant-a" },
  };
  const b = {
    assistantCode: "one",
    runtimeSession: { conversationId: "b", conversationToken: "grant-b" },
  };
  assert.equal(ownedConversationSession(a, "one")?.conversationId, "a");
  assert.equal(
    ownedConversationSession(b, "one")?.conversationToken,
    "grant-b",
  );
  assert.equal(ownedConversationSession(a, "two"), undefined);
  assert.equal(
    ownedConversationSession({ assistantCode: "one" }, "one"),
    undefined,
  );
  assert.equal(ownedConversationSession(null, "one"), undefined);
  const restored = JSON.parse(JSON.stringify(a));
  assert.deepEqual(ownedConversationSession(restored, "one"), a.runtimeSession);
});
