import { describe, expect, it } from "vitest";
import {
  TARGET_RETEST9_IDS,
  assertRunnerCompletion,
  buildCohortConfigFingerprint,
  checkConfigDrift,
  resolveDocumentBinding,
  type Retest9Report,
} from "../e2e/stages/retest9-core";

describe("Retest9 Runner Integrity Tests (Offline)", () => {
  // Test 1: Scope single thiếu binding phải bị chặn (BLOCKED), tuyệt đối không mở thành all
  describe("1. Scope binding fail-closed", () => {
    it("ném lỗi BLOCKED khi scope single nhưng thiếu target_doc", () => {
      expect(() => {
        resolveDocumentBinding({
          id: "F13",
          scope: "single",
          target_doc: undefined as any,
        });
      }).toThrow(/BLOCKED: Case F13 có scope 'single' nhưng thiếu target_doc/);
    });

    it("ném lỗi BLOCKED khi scenarioDocuments không có binding cho target_doc", () => {
      const scenarioDocs = {
        floor2026: { key: "floor2026" }, // không có publication.document
      };
      expect(() => {
        resolveDocumentBinding(
          { id: "F13", scope: "single", target_doc: "floor2026" },
          scenarioDocs as any,
        );
      }).toThrow(/BLOCKED: Không tìm thấy document binding cho target_doc 'floor2026'/);
    });

    it("trả về mảng 1 phần tử khi scope single có binding hợp lệ", () => {
      const scenarioDocs = {
        floor2026: {
          key: "floor2026",
          publication: { document: "cdoc_123" },
        },
      };
      const binding = resolveDocumentBinding(
        { id: "F13", scope: "single", target_doc: "floor2026" },
        scenarioDocs as any,
      );
      expect(binding).toEqual(["cdoc_123"]);
    });

    it("trả về undefined cho scope all", () => {
      const binding = resolveDocumentBinding({
        id: "MX-02",
        scope: "all",
        target_doc: "all",
      });
      expect(binding).toBeUndefined();
    });
  });

  // Test 2: Idempotency và danh tính 9 câu
  describe("2. Danh tính và cấu trúc 9 câu mục tiêu", () => {
    it("đảm bảo danh sách TARGET_RETEST9_IDS gồm đúng 9 ID duy nhất", () => {
      expect(TARGET_RETEST9_IDS).toHaveLength(9);
      const unique = new Set(TARGET_RETEST9_IDS);
      expect(unique.size).toBe(9);
      expect(TARGET_RETEST9_IDS).toEqual([
        "F13",
        "F14",
        "I25-04",
        "I25-05",
        "BC24-05",
        "BC24-08",
        "MX-02",
        "MX-05",
        "MX-10",
      ]);
    });
  });

  // Test 3: Cấu hình đổi giữa chừng (drift) bị chặn
  describe("3. Khóa cấu hình và kiểm soát Drift", () => {
    const baseConfig = {
      benchmarkVersion: "v2-775",
      benchmarkHash: "bench_hash_1",
      indexId: "idx_123",
      indexManifestHash: "manifest_hash_1",
      assistant: {
        id: "ast_1",
        revision: 2,
        max_output_tokens: 16384,
        context_max_bytes: 98304,
      },
      provider: {
        id: "prv_chat",
        model: "qwen3.8-27b-q4",
        reasoningPolicy: { tasks: { off: ["compiler", "answer"] } },
      },
      rerank: {
        id: "prv_rerank",
        model: "bge-reranker-v2-m3",
      },
    };

    it("tạo hash ổn định cho cùng cấu hình", () => {
      const h1 = buildCohortConfigFingerprint(baseConfig);
      const h2 = buildCohortConfigFingerprint(baseConfig);
      expect(h1).toBe(h2);
      expect(() => checkConfigDrift(h1, h2)).not.toThrow();
    });

    it("ném lỗi DRIFT_DETECTED khi bất kỳ thuộc tính nào thay đổi", () => {
      const h1 = buildCohortConfigFingerprint(baseConfig);

      // Assistant revision đổi
      const h2 = buildCohortConfigFingerprint({
        ...baseConfig,
        assistant: { ...baseConfig.assistant, revision: 3 },
      });
      expect(h1).not.toBe(h2);
      expect(() => checkConfigDrift(h1, h2)).toThrow(/DRIFT_DETECTED/);

      // Reasoning policy đổi
      const h3 = buildCohortConfigFingerprint({
        ...baseConfig,
        provider: {
          ...baseConfig.provider,
          reasoningPolicy: { tasks: { off: ["compiler"] } }, // mất answer off
        },
      });
      expect(h1).not.toBe(h3);
      expect(() => checkConfigDrift(h1, h3)).toThrow(/DRIFT_DETECTED/);

      // Max output tokens đổi
      const h4 = buildCohortConfigFingerprint({
        ...baseConfig,
        assistant: { ...baseConfig.assistant, max_output_tokens: 4096 },
      });
      expect(h1).not.toBe(h4);
      expect(() => checkConfigDrift(h1, h4)).toThrow(/DRIFT_DETECTED/);
    });
  });

  // Test 4: Report có failure hoặc not_run phải khiến runner assert thất bại (exit nonzero)
  describe("4. Runner assertion và báo lỗi trung thực", () => {
    function mockReport(overrides?: Partial<Retest9Report>): Retest9Report {
      return {
        benchmark_version: "v2-775",
        cohort_id: "retest9-test",
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        expected: 9,
        dispatched: 9,
        passed: 9,
        failed: 0,
        not_run: 0,
        uncertain: 0,
        halted: null,
        config_fingerprint: "hash_123",
        records: TARGET_RETEST9_IDS.map((id) => ({
          id,
          group: "test",
          scope: "single",
          target_doc: "doc",
          question: "Q",
          status: "PASS",
          dispatched: true,
          client_elapsed_ms: 1000,
          inference_ms: 800,
          tokens: { prompt_tokens: 100, completion_tokens: 50, total_tokens: 150 },
          response: {},
        })),
        ...overrides,
      };
    }

    it("pass assertion khi toàn bộ 9 câu đều PASS và không bị halted", () => {
      const rep = mockReport();
      expect(() => assertRunnerCompletion(rep)).not.toThrow();
    });

    it("ném lỗi RUNNER_HALTED khi cohort bị halt do hạ tầng/drift", () => {
      const rep = mockReport({
        halted: "Quota exceeded",
      });
      expect(() => assertRunnerCompletion(rep)).toThrow(/RUNNER_HALTED: Cohort bị dừng do lỗi hạ tầng\/drift: Quota exceeded/);
    });

    it("ném lỗi RUNNER_INCOMPLETE khi có câu bị FAIL (khắc phục false-green P1)", () => {
      const records = mockReport().records;
      records[0] = {
        ...records[0],
        status: "FAIL",
        error_code: "chat_output_truncated",
        error: "HTTP 422: chat_output_truncated",
      };
      const rep = mockReport({
        records,
        passed: 8,
        failed: 1,
      });
      expect(() => assertRunnerCompletion(rep)).toThrow(/RUNNER_INCOMPLETE: Có 1\/9 câu chưa đạt tiêu chuẩn PASS: F13:FAIL\[chat_output_truncated\]/);
    });

    it("ném lỗi RUNNER_FAILURE khi thiếu câu hỏi hoặc trùng lặp", () => {
      const records = mockReport().records.slice(0, 8); // Chỉ có 8 câu
      const rep = mockReport({ records, expected: 9, passed: 8 });
      expect(() => assertRunnerCompletion(rep)).toThrow(/RUNNER_FAILURE: Số lượng records không khớp 9/);
    });

    it("ném lỗi RUNNER_FAILURE khi có ID lạ", () => {
      const records = mockReport().records;
      records[0] = { ...records[0], id: "UNKNOWN-99" };
      const rep = mockReport({ records });
      expect(() => assertRunnerCompletion(rep)).toThrow(/RUNNER_FAILURE: Gặp ID không thuộc phạm vi retest9: 'UNKNOWN-99'/);
    });
  });
});
