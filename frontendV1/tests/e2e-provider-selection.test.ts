import { readFileSync } from "node:fs";
import { expect, test } from "vitest";
import {
  acceptsModelObservation,
  configuredProfiles,
  type LiveProfile,
  profileForCapability,
} from "../e2e/stages/live-profile";

const profile = JSON.parse(
  readFileSync(
    new URL("../../scripts/e2e_profiles/qnu-server.json", import.meta.url),
    "utf8",
  ),
) as LiveProfile;

test("9router is registered separately and only replaces the selected chat target", () => {
  expect(configuredProfiles(profile)).toHaveLength(3);
  const chat = profileForCapability(profile, "router", "chat");
  expect(chat.base_url).toBe("https://qnu-9router.duckdns.org/v1");
  expect(chat.models.chat).toBe("cx/gpt-6-luna");
  for (const capability of ["embedding", "rerank"] as const) {
    const target = profileForCapability(profile, "router", capability);
    expect(target.base_url).toBe(profile.base_url);
    expect(target.models[capability]).toBe(profile.models[capability]);
  }
  expect(profileForCapability(profile, "router", "ocr")).toBe(
    profile.additional_ocr_provider,
  );
  expect(profileForCapability(profile, "qnu", "ocr")).toBe(
    profile.additional_ocr_provider,
  );
  expect(profileForCapability(profile, "qnu", "chat").models.chat).toBe(
    profile.models.chat,
  );
});

test("selection cannot silently fall back and router capacity is not guessed", () => {
  expect(() => profileForCapability(profile, undefined, "chat")).toThrow(
    "chọn model",
  );
  const { additional_chat_provider: _router, ...legacy } = profile;
  expect(() => profileForCapability(legacy, "router", "chat")).toThrow(
    "thiếu cấu hình",
  );
  expect(profileForCapability(legacy, undefined, "chat")).toBe(legacy);
  expect(
    profile.additional_chat_provider?.model_runtime?.chat?.max_input_tokens,
  ).toBeUndefined();
});

test("gateway accepts only its explicitly declared upstream alias", () => {
  const target = profileForCapability(profile, "router", "chat");
  const requested = "cx/gpt-6-luna";
  expect(acceptsModelObservation(target, "chat", requested, "gpt-6-luna")).toBe(
    true,
  );
  expect(acceptsModelObservation(target, "chat", requested, requested)).toBe(
    true,
  );
  expect(
    acceptsModelObservation(target, "chat", requested, "gpt-oss:120b"),
  ).toBe(false);
  expect(
    acceptsModelObservation(target, "chat", "gpt-6-luna", "gpt-6-luna"),
  ).toBe(false);
});

test("aliases do not apply to another provider, capability or unconfigured model", () => {
  const requested = "cx/gpt-6-luna";
  const target = profileForCapability(profile, "router", "chat");
  expect(
    acceptsModelObservation(profile, "chat", requested, "gpt-6-luna"),
  ).toBe(false);
  expect(
    acceptsModelObservation(target, "embedding", requested, "gpt-6-luna"),
  ).toBe(false);
  const { observed_model_aliases: _aliases, ...withoutAliases } = target;
  expect(
    acceptsModelObservation(withoutAliases, "chat", requested, "gpt-6-luna"),
  ).toBe(false);
});

test("providers without aliases still require exact observations when present", () => {
  const requested = profile.models.chat;
  expect(acceptsModelObservation(profile, "chat", requested, requested)).toBe(
    true,
  );
  expect(acceptsModelObservation(profile, "chat", requested, null)).toBe(true);
  expect(
    acceptsModelObservation(profile, "chat", requested, "other-model"),
  ).toBe(false);
  expect(acceptsModelObservation(profile, "chat", "other-request", null)).toBe(
    false,
  );
});
