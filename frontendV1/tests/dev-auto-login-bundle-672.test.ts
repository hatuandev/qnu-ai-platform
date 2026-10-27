/**
 * Guard: the local auto-login bridge is a Node-side dev-server feature.
 *
 * These tests fail if a future change makes the bridge (or its access key)
 * reachable from the browser bundle. They check the source graph first — that
 * part never needs a build — and then, when `dist/` exists, the real output.
 */
import { existsSync, readdirSync, readFileSync, statSync } from "node:fs";
import { join, relative } from "node:path";
import { describe, expect, test } from "vitest";

const projectRoot = process.cwd();
const srcDir = join(projectRoot, "src");
const devDir = join(projectRoot, "dev");
const distDir = join(projectRoot, "dist");

/** Server-only identifiers: none of them may appear in browser output. */
const SERVER_ONLY_MARKERS = [
  "createDevAutoLoginHandler",
  "devAutoLoginPlugin",
  "sec-fetch-site",
  "QNU_DEV_ACCESS_KEY=",
  "DEV_AUTO_LOGIN_ENV_KEY",
];

function listFiles(dir: string, extensionPattern: RegExp): string[] {
  const found: string[] = [];
  for (const entry of readdirSync(dir, { withFileTypes: true })) {
    const full = join(dir, entry.name);
    if (entry.isDirectory()) {
      found.push(...listFiles(full, extensionPattern));
    } else if (extensionPattern.test(entry.name)) {
      found.push(full);
    }
  }
  return found;
}

function readTextFiles(dir: string): { path: string; text: string }[] {
  if (!existsSync(dir)) return [];
  return listFiles(dir, /\.(js|css|html|json|svg|txt)$/).map((path) => ({
    path,
    text: readFileSync(path, "utf8"),
  }));
}

describe("dev auto-login bridge stays out of the browser bundle", () => {
  test("no file under src/ imports the dev-server bridge module", () => {
    const offenders: string[] = [];

    for (const file of listFiles(srcDir, /\.(ts|tsx)$/)) {
      const source = readFileSync(file, "utf8");
      // Only real import/require statements count; a doc comment may mention the path.
      const importsBridge =
        /(?:^|\n)\s*(?:import|export)[\s\S]{0,200}?from\s+["'][^"']*\/dev\/dev-auto-login["']/.test(
          source,
        ) ||
        /import\s*\(\s*["'][^"']*\/dev\/dev-auto-login["']\s*\)/.test(source) ||
        /require\s*\(\s*["'][^"']*\/dev\/dev-auto-login["']\s*\)/.test(source);
      if (importsBridge) offenders.push(relative(projectRoot, file));
    }

    expect(offenders).toEqual([]);
  });

  test("the bridge is exported only for the Vite dev server", () => {
    const bridgeSource = readFileSync(
      join(devDir, "dev-auto-login.ts"),
      "utf8",
    );
    expect(bridgeSource).toContain('apply: "serve"');

    const viteConfig = readFileSync(
      join(projectRoot, "vite.config.ts"),
      "utf8",
    );
    // The plugin may only be mounted behind the dev-server guard, never unconditionally.
    expect(viteConfig).toMatch(
      /\.\.\.\(isDevServer\s*\?\s*\[devAutoLoginPlugin\(autoLoginConfig\)\]\s*:\s*\[\]\)/,
    );
    expect(viteConfig).toMatch(/const isDevServer\s*=\s*command === "serve"/);
  });

  test("the browser client never sends or stores the access key", () => {
    const clientSource = readFileSync(
      join(srcDir, "app/auth/v1/dev-auto-login.ts"),
      "utf8",
    );

    // The request body must be empty: the key lives in the dev server process.
    expect(clientSource).not.toMatch(/body\s*:/);
    expect(clientSource).not.toMatch(/access_key/);
    expect(clientSource).not.toMatch(/localStorage/);
    // Session storage may only hold the non-secret suppression boolean.
    expect(clientSource).toContain("qnu.dev-auto-login.suppressed");
  });
});

describe.runIf(existsSync(distDir))(
  "built output carries no bridge secret",
  () => {
    const builtFiles = readTextFiles(distDir);

    test("dist/ contains assets to scan", () => {
      expect(builtFiles.length).toBeGreaterThan(0);
      expect(statSync(distDir).isDirectory()).toBe(true);
    });

    test("no server-only bridge marker appears in dist/", () => {
      const offenders = SERVER_ONLY_MARKERS.flatMap((marker) =>
        builtFiles
          .filter((file) => file.text.includes(marker))
          .map((file) => `${relative(projectRoot, file.path)} :: ${marker}`),
      );

      expect(offenders).toEqual([]);
    });

    test("the access key is never inlined as a value in dist/", () => {
      // `QNU_DEV_AUTO_LOGIN=true` is a documented public boolean that appears in
      // user-facing hints, so only the secret variable is checked here.
      const assignmentLeaks = builtFiles.flatMap((file) =>
        (file.text.match(/QNU_DEV_ACCESS_KEY\s*=\s*[^\s"'`]+/g) ?? []).map(
          (match) => `${relative(projectRoot, file.path)} :: ${match}`,
        ),
      );

      expect(assignmentLeaks).toEqual([]);
    });
  },
);
