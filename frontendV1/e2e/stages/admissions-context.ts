import { readFileSync } from "node:fs";
import path from "node:path";
import { type Api, type Checkpoint, sha256 } from "./session";

export interface BenchmarkDoc {
  key: string;
  path: string;
  sha256: string;
  /** 0 = chưa biết trước (DOCX); số trang thực lưu ở checkpoint sau extraction. */
  pages: number;
  format?: "pdf" | "docx";
  title: string;
  data_year: number;
}

export interface AdmissionCase {
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
  facts?: AdmissionFact[];
}

export interface AdmissionFact {
  document: string;
  pages: number[];
  data_year: number;
  locator: string;
  subject_patterns: string[];
  metric_patterns: string[];
  values: { value: number; kind: "integer" | "decimal" }[];
  support: "table" | "text";
  /** Offline native-PDF row/column audit; never sent to the model. */
  source_row_code?: string;
  source_value_column?: number;
}

export interface BenchmarkMultiDocs {
  version: string;
  documents: Record<string, BenchmarkDoc>;
  source: BenchmarkDoc; // Alias to floor2026 for compatibility
  label_status: string;
  cases: AdmissionCase[];
}

const rawBenchmark = JSON.parse(
  readFileSync(path.resolve("e2e/data/admissions-multi-docs.json"), "utf8"),
) as {
  version: string;
  documents: Record<string, BenchmarkDoc>;
  label_status: string;
  cases: AdmissionCase[];
};

export const benchmark: BenchmarkMultiDocs = {
  ...rawBenchmark,
  source: rawBenchmark.documents.floor2026,
};

export const docPaths: Record<string, string> = Object.fromEntries(
  Object.entries(benchmark.documents).map(([key, doc]) => [
    key,
    path.resolve("..", doc.path),
  ]),
);

export const sourcePath = docPaths.floor2026;

export function context(state: Checkpoint): Checkpoint {
  return {
    ...state,
    collection: state.admissions?.collection,
    folder: undefined,
  };
}

export function checkSource() {
  checkAllSources();
}

export function checkAllSources() {
  for (const [key, doc] of Object.entries(benchmark.documents)) {
    const fullPath = docPaths[key];
    const bytes = readFileSync(fullPath);
    const hash = sha256(bytes);
    if (hash !== doc.sha256) {
      throw new Error(
        `BLOCKED: nguồn ${key} (${doc.path}) đã đổi so với bộ câu hỏi: observed ${hash} != expected ${doc.sha256}.`,
      );
    }
  }
}

export async function modelTimeout(api: Api, state: Checkpoint) {
  if (!state.runtimeDefaults)
    throw new Error("BLOCKED: chạy navigation trước.");
  const provider = await api.get<{ timeout_seconds: number }>(
    `/modelops/providers/${state.runtimeDefaults.chat}`,
  );
  return (provider.timeout_seconds + 30) * 1000;
}
