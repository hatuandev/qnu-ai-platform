import { readFileSync } from "node:fs";
import { expect, test } from "vitest";
import {
  configuredProfiles,
  type LiveProfile,
  profileForCapability,
} from "../e2e/stages/live-profile";
import {
  connectionEndpoint,
  connectionProtocol,
} from "../src/features/modelops/connections/presentation";

const profile = JSON.parse(
  readFileSync("../scripts/e2e_profiles/qnu-server.json", "utf8"),
) as LiveProfile;

test("OCR routes independently from chat selection and QNU discovery excludes OCR", () => {
  for (const chat of ["qnu", "router"] as const) {
    const target = profileForCapability(profile, chat, "ocr");
    expect(target.api_type).toBe("mineru");
    expect(target.models.ocr).toBe("mineru");
    expect(target.base_url.endsWith("/mineru")).toBe(true);
  }
  expect(profile.models.ocr).toBeUndefined();
  expect(Object.keys(profile.models)).toEqual(["chat", "embedding", "rerank"]);
  expect(configuredProfiles(profile)).toHaveLength(3);
  expect(JSON.stringify(profile)).not.toMatch(/nemotron|ocr_page_input/);
  expect(profileForCapability(profile, "qnu", "embedding").base_url).toBe(
    profile.base_url,
  );
  expect(profileForCapability(profile, "router", "chat").models.chat).toBe(
    "cx/gpt-6-luna",
  );
});

test("task URL handles optional /v1 while generic connections never imply chat", () => {
  for (const base_url of [
    "https://example.test/mineru/",
    "https://example.test/mineru/v1/",
  ])
    expect(connectionEndpoint({ base_url, api_type: "mineru" })).toBe(
      "https://example.test/mineru/v1/tasks",
    );
  expect(connectionProtocol({ api_type: "openai_compatible" })).toBe(
    "OpenAI Compatible",
  );
  expect(
    connectionEndpoint({
      base_url: "https://example.test/v1/",
      api_type: "openai_compatible",
    }),
  ).toBe("https://example.test/v1");
});
