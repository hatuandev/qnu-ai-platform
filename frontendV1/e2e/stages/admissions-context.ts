import { readFileSync } from "node:fs";
import path from "node:path";
import { type Api, type Checkpoint, sha256 } from "./session";

export interface AdmissionCase {
  id: string;
  question: string;
  kind: "answerable" | "unanswerable";
  expected_numbers: number[];
  expected_patterns: string[];
  pages: number[];
  expected: string;
  rubric: string;
}
export const benchmark = JSON.parse(
  readFileSync(path.resolve("e2e/data/admissions-floor-2026.json"), "utf8"),
) as {
  version: string;
  source: { path: string; sha256: string; pages: number };
  label_status: string;
  cases: AdmissionCase[];
};
export const sourcePath = path.resolve("..", benchmark.source.path);

export function context(state: Checkpoint): Checkpoint {
  return { ...state, collection: state.admissions?.collection, folder: undefined };
}

export function checkSource() {
  if (sha256(readFileSync(sourcePath)) !== benchmark.source.sha256)
    throw new Error("BLOCKED: PDF đã đổi so với bộ câu hỏi; cần đối chiếu lại đáp án/hash.");
}

export async function modelTimeout(api: Api, state: Checkpoint) {
  if (!state.runtimeDefaults) throw new Error("BLOCKED: chạy navigation trước.");
  const provider = await api.get<{ timeout_seconds: number }>(
    `/modelops/providers/${state.runtimeDefaults.chat}`,
  );
  return (provider.timeout_seconds + 30) * 1000;
}

