import assert from "node:assert/strict";
import { readdirSync, readFileSync } from "node:fs";
import { join, sep } from "node:path";
import { test } from "vitest";
import {
  backendFetch,
  TemplateRequestError,
} from "../src/app/api/backend-fetch.ts";

const SRC_ROOT = new URL("../src", import.meta.url).pathname.replace(
  /^\/([A-Za-z]:)/,
  "$1",
);

function sourceFiles(directory = SRC_ROOT): string[] {
  const files: string[] = [];
  for (const entry of readdirSync(directory, { withFileTypes: true })) {
    const path = join(directory, entry.name);
    if (entry.isDirectory()) files.push(...sourceFiles(path));
    else if (/\.tsx?$/.test(entry.name) && !entry.name.endsWith(".gen.ts")) {
      files.push(path);
    }
  }
  return files;
}

function relative(path: string): string {
  const normalized = path.split(sep).join("/");
  const root = SRC_ROOT.split(sep).join("/");
  return normalized.startsWith(`${root}/`)
    ? normalized.slice(root.length + 1)
    : normalized;
}

/**
 * The only places allowed to speak to backendV1. Everything else is either a
 * KTX template screen (whose API is hard-blocked) or shared UI.
 */
const V1_DIRECTORIES = [
  "app/api/v1/",
  "app/auth/v1/",
  "features/workspaces/",
  "features/modelops/",
  "features/knowledge/",
  "features/inbox/",
  "features/assistants/",
  "features/answer-review/",
  "features/conversations/",
  "features/lifecycle/",
  "features/operations/",
  "features/evaluation/",
];
const V1_ROUTE_PREFIXES = [
  "routes/workspaces",
  "routes/modelops",
  "routes/providers",
  "routes/signin-oidc",
];

function isV1File(path: string): boolean {
  const file = relative(path);
  return (
    V1_DIRECTORIES.some((directory) => file.startsWith(directory)) ||
    V1_ROUTE_PREFIXES.some((prefix) => file.startsWith(prefix))
  );
}

const FETCH_CALL = /\bfetch\s*\(/;
const BACKEND_FETCH_IMPORT = /from\s+["'][^"']*backend-fetch["']/;
/**
 * Importing the *error type* is fine for shared UI; importing the HTTP client
 * is not. This pattern matches only the client symbols.
 */
const V1_CLIENT_IMPORT =
  /import\s*\{[\s\S]*?\b(v1Client|v1PublicClient|v1ApiBaseUrl)\b[\s\S]*?\}\s*from\s*["'][^"']*api\/v1/;
const V1_PREFIX_LITERAL = /platform\/v1alpha1/;
const PERSISTENCE_WRITE =
  /localStorage\.setItem|sessionStorage\.setItem|document\.cookie\s*=/;

/**
 * The v1 bearer token is never persisted. Exactly one non-secret key is
 * allowed: the dev auto-login suppression flag, a boolean written after an
 * explicit logout so the local bridge cannot silently sign the user back in.
 * Its value must stay the literal `"1"` — anything else fails the test below.
 */
const ALLOWED_STORAGE_KEYS = new Set(["qnu.dev-auto-login.suppressed"]);
const ALLOWED_STORAGE_VALUE = "1";

/** Resolves `const NAME = "literal"` so an indirection cannot hide a key. */
function literalConstants(source: string): Map<string, string> {
  const constants = new Map<string, string>();
  const pattern = /const\s+([A-Za-z0-9_$]+)\s*=\s*["'`]([^"'`]*)["'`]/g;
  for (const match of source.matchAll(pattern)) {
    constants.set(match[1], match[2]);
  }
  return constants;
}

function resolveLiteral(raw: string, constants: Map<string, string>): string {
  const value = raw.trim();
  const quoted = value.match(/^["'`]([\s\S]*)["'`]$/);
  if (quoted) return quoted[1];
  return constants.get(value) ?? value;
}

/** Every storage write in a file, as `key=value` pairs plus bare cookie writes. */
function persistenceWrites(source: string): string[] {
  const constants = literalConstants(source);
  const writes: string[] = [];
  if (/document\.cookie\s*=/.test(source)) writes.push("document.cookie");

  const pattern =
    /(?:local|session)Storage\.setItem\(\s*([\s\S]*?),\s*([\s\S]*?)\)/g;
  for (const match of source.matchAll(pattern)) {
    const key = resolveLiteral(match[1], constants);
    const value = resolveLiteral(match[2], constants);
    if (!ALLOWED_STORAGE_KEYS.has(key) || value !== ALLOWED_STORAGE_VALUE) {
      writes.push(`setItem(${key}=${value})`);
    }
  }
  return writes;
}

test("reference API reads, writes and file transfers never reach fetch", async () => {
  let networkCalls = 0;
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async () => {
    networkCalls += 1;
    throw new Error("Unexpected network access");
  };
  try {
    for (const method of ["GET", "POST", "PUT", "PATCH", "DELETE"]) {
      await assert.rejects(
        backendFetch("https://example.invalid/api/reference", { method }),
        TemplateRequestError,
      );
    }
    const file = new FormData();
    file.append("file", new Blob(["sample"]), "sample.txt");
    await assert.rejects(
      backendFetch("/api/upload", { method: "POST", body: file }),
      TemplateRequestError,
    );
    assert.equal(networkCalls, 0);
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test("only the v1 client is allowed to call fetch", () => {
  const offenders = sourceFiles()
    .filter((path) => FETCH_CALL.test(readFileSync(path, "utf8")))
    .map(relative)
    .filter((file) => file !== "app/api/v1/client.ts");

  assert.deepEqual(offenders, []);
});

test("KTX template code never imports the v1 client", () => {
  const offenders = sourceFiles()
    .filter((path) => !isV1File(path))
    .filter((path) => {
      const source = readFileSync(path, "utf8");
      return V1_CLIENT_IMPORT.test(source) || V1_PREFIX_LITERAL.test(source);
    })
    .map(relative);

  assert.deepEqual(offenders, []);
});

test("v1 code never reaches for the blocked KTX boundary", () => {
  const offenders = sourceFiles()
    .filter(isV1File)
    .filter((path) => BACKEND_FETCH_IMPORT.test(readFileSync(path, "utf8")))
    .map(relative);

  assert.deepEqual(offenders, []);
});

test("the v1 bearer token is never persisted by the client", () => {
  const offenders = sourceFiles()
    .filter(isV1File)
    .filter((path) => PERSISTENCE_WRITE.test(readFileSync(path, "utf8")))
    .flatMap((path) =>
      persistenceWrites(readFileSync(path, "utf8")).map(
        (write) => `${relative(path)} :: ${write}`,
      ),
    );

  assert.deepEqual(offenders, []);
});
