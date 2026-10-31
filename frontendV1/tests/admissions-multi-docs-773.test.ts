import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";

const benchmark = JSON.parse(
  readFileSync(path.resolve("e2e/data/admissions-multi-docs.json"), "utf8"),
) as {
  version: string;
  documents: Record<
    string,
    {
      key: string;
      path: string;
      sha256: string;
      pages: number;
      title: string;
      data_year: number;
    }
  >;
  label_status: string;
  cases: {
    id: string;
    group: string;
    scope: "single" | "all";
    target_doc: string;
    question: string;
    kind: "answerable" | "unanswerable";
    expected_numbers: number[];
    expected_patterns: string[];
    pages: number[];
    expected: string;
    rubric: string;
  }[];
};

describe("Admissions Multi-Document Benchmark & Scope Contract (Session 773)", () => {
  it("verifies 3 documents metadata, sha256 and page counts", () => {
    expect(Object.keys(benchmark.documents)).toEqual([
      "floor2026",
      "info2025",
      "report2024",
    ]);

    const docA = benchmark.documents.floor2026;
    expect(docA.pages).toBe(8);
    expect(docA.sha256).toBe(
      "236ab3573d6d683a760ed227512022d6c21a03ba5c147c32d4ed7b042f7c6d45",
    );

    const docB = benchmark.documents.info2025;
    expect(docB.pages).toBe(13);
    expect(docB.sha256).toBe(
      "f427bb580ad0b2bea89b847a8ce31ffeb8611ea67fd1ba069fd7521ab7327b6b",
    );

    const docC = benchmark.documents.report2024;
    expect(docC.pages).toBe(7);
    expect(docC.sha256).toBe(
      "92353949628629e6dc63c5eed9aad587fd8e9a9db7c6d9814e2718a39ad6d96f",
    );

    const totalPages = Object.values(benchmark.documents).reduce(
      (sum, d) => sum + d.pages,
      0,
    );
    expect(totalPages).toBe(28);
  });

  it("ensures physical PDF files match expected sha256 bytes", () => {
    for (const [key, doc] of Object.entries(benchmark.documents)) {
      const fullPath = path.resolve("..", doc.path);
      const bytes = readFileSync(fullPath);
      const hash = createHash("sha256").update(bytes).digest("hex");
      expect(hash, `PDF hash mismatch for ${key}`).toBe(doc.sha256);
    }
  });

  it("verifies exactly 53 test cases partitioned across 4 distinct groups", () => {
    expect(benchmark.cases).toHaveLength(53);

    const groupCounts: Record<string, number> = {};
    for (const c of benchmark.cases) {
      groupCounts[c.group] = (groupCounts[c.group] || 0) + 1;
    }

    expect(groupCounts.floor2026).toBe(19); // F01 - F19
    expect(groupCounts.info2025).toBe(12); // I25-01 - I25-12
    expect(groupCounts.report2024).toBe(12); // BC24-01 - BC24-12
    expect(groupCounts.cross_document).toBe(10); // MX-01 - MX-10
  });

  it("checks answerable vs unanswerable distribution and boundary cases", () => {
    const unanswerables = benchmark.cases.filter(
      (c) => c.kind === "unanswerable",
    );
    // F17, F18, F19 (3) + I25-11, I25-12 (2) + BC24-11, BC24-12 (2) + MX-06, MX-07, MX-08 (3) = 10 cases
    expect(unanswerables).toHaveLength(10);

    for (const u of unanswerables) {
      expect(u.expected_numbers).toHaveLength(0);
      expect(u.pages).toHaveLength(0);
    }

    const answerables = benchmark.cases.filter((c) => c.kind === "answerable");
    expect(answerables).toHaveLength(43);
  });

  it("ensures gold answers and rubrics are NOT embedded in questions", () => {
    for (const item of benchmark.cases) {
      expect(item.question).not.toContain(item.rubric);
      expect(item.question.length).toBeGreaterThan(15);
      expect(item.id).toMatch(/^(F\d{2}|I25-\d{2}|BC24-\d{2}|MX-\d{2})$/);
    }
  });

  it("ensures unique case IDs and non-colliding idempotency keys", () => {
    const ids = new Set<string>();
    const runId = "test93faa11f";
    const keys = new Set<string>();

    for (const item of benchmark.cases) {
      expect(ids.has(item.id)).toBe(false);
      ids.add(item.id);

      const idempotencyKey = `${runId}-adm-${benchmark.version}-${item.id}`;
      expect(keys.has(idempotencyKey)).toBe(false);
      keys.add(idempotencyKey);
    }
    expect(ids.size).toBe(53);
    expect(keys.size).toBe(53);
  });
});
