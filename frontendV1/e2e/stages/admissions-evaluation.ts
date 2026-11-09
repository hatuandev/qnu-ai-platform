import type {
  AdmissionCase,
  AdmissionFact,
  BenchmarkDoc,
} from "./admissions-context";
import type { Checkpoint } from "./session";

export interface Answer {
  status: "answered" | "insufficient_evidence";
  reason?: string;
  answer: string | null;
  index_run_id: string;
  statements: { text: string; evidence_ids: string[] }[];
  sources: {
    evidence_id: string;
    document_id: string;
    version_id: string;
    publication_decision_id: string;
    text: string;
    source_passages?: { citation: string; text: string; position?: string }[];
    structure?: {
      source_table_citation?: string;
      rows?: { evidence_id: string; text: string }[][];
    } | null;
    citations: Record<
      string,
      { page: number; source_sha256: string; revision_id: string }
    >;
  }[];
  trace: {
    prompt_version?: string;
    configuration_hash?: string;
    stage_ms?: Record<string, number>;
    provider_id?: string;
    retrieval: { mode?: string; rerank_provider?: { provider_id: string } };
    grounding?: {
      cell_proofs?: {
        cell_id: string;
        evidence_ids: string[];
        source_cells: string[];
      }[];
    };
    prompt_tokens?: number | null;
    completion_tokens?: number | null;
    total_tokens?: number | null;
    rerank_tokens?: number | null;
  };
}

function requireThat(condition: unknown, message: string): asserts condition {
  if (!condition) throw new Error(message);
}

export const matches = (text: string, patterns: string[]) =>
  patterns.every((p) => new RegExp(p, "iu").test(text.replace(/\s+/g, " ")));

// A count/currency uses grouped thousands; decimals retain their decimal point.
// No global dot stripping: 1.65, 6.0 and 62.7 must remain decimals.
export function hasNumber(
  text: string,
  value: number,
  kind: "integer" | "decimal",
) {
  const tokens =
    text.match(
      /(?<![\p{L}\d])(?:\d{1,3}(?:[\u00a0 ]\d{3})+|\d+)(?:[.,]\d+)*(?=$|[^\p{L}\d]|m\b|đ\b)/gu,
    ) || [];
  return tokens.some((raw) => {
    const token = raw.trim();
    const grouped = /^\d{1,3}([.,\u00a0 ])\d{3}(?:\1\d{3})*$/.test(token);
    const normalized =
      kind === "integer" && grouped
        ? token.replace(/[.,\u00a0 ]/g, "")
        : token.replace(",", ".");
    return Number(normalized) === value;
  });
}

const valuesMatch = (text: string, fact: AdmissionFact) =>
  fact.values.every(({ value, kind }) => hasNumber(text, value, kind));

/** Text rules may span sentences, but only inside an identical citation group.
 * Never pool unrelated evidence, and never use this grouping for cell facts.
 */
function claimGroups(statements: Answer["statements"]): Answer["statements"] {
  const groups = new Map<string, Answer["statements"][number]>();
  for (const statement of statements) {
    const ids = [...new Set(statement.evidence_ids)].sort();
    const key = JSON.stringify(ids);
    const group = groups.get(key);
    if (group) group.text += ` ${statement.text}`;
    else groups.set(key, { text: statement.text, evidence_ids: ids });
  }
  return [...groups.values()];
}

/** Join only consecutive original blocks inside one cited published identity. */
function citedTextRuns(cited: Answer["sources"]): string[] {
  const texts: string[] = [];
  const buckets = new Map<
    string,
    Map<number, { citation: string; text: string }>
  >();
  for (const source of cited) {
    const passages = source.source_passages?.filter(
      (p) => p.citation in source.citations,
    );
    texts.push(
      passages?.length ? passages.map((p) => p.text).join(" ") : source.text,
    );
    for (const p of passages || []) {
      if (!p.position || !/^\d+$/.test(p.position)) continue;
      const key = JSON.stringify([
        source.document_id,
        source.version_id,
        source.publication_decision_id,
        p.citation.split(":", 1)[0],
      ]);
      const blocks =
        buckets.get(key) ||
        new Map<number, { citation: string; text: string }>();
      const index = Number(p.position);
      const old = blocks.get(index);
      if (old && (old.text !== p.text || old.citation !== p.citation))
        return texts;
      blocks.set(index, p);
      buckets.set(key, blocks);
    }
  }
  for (const blocks of buckets.values()) {
    let previous = -2;
    for (const [index, p] of [...blocks].sort(([a], [b]) => a - b)) {
      if (index === previous + 1) texts[texts.length - 1] += ` ${p.text}`;
      else texts.push(p.text);
      previous = index;
    }
  }
  return texts;
}

export function checkAdmissionAnswer(
  answer: Answer,
  item: AdmissionCase,
  state: Checkpoint,
  documents: Record<string, BenchmarkDoc>,
) {
  const scenario = state.admissions;
  requireThat(
    answer.index_run_id === scenario?.combinedIndex,
    "Sai index của cohort.",
  );
  const sources = new Map(answer.sources.map((s) => [s.evidence_id, s]));
  for (const source of answer.sources) {
    const key = Object.keys(documents).find(
      (k) =>
        scenario?.documents?.[k]?.publication?.document === source.document_id,
    );
    requireThat(
      key && (item.scope !== "single" || key === item.target_doc),
      "Trích dẫn ngoài phạm vi.",
    );
    const entry = scenario?.documents?.[key];
    requireThat(
      source.version_id === entry?.publication?.version,
      "Sai phiên bản xuất bản.",
    );
    requireThat(
      source.publication_decision_id ===
        scenario?.indexInputs?.find((i) => i.document_id === source.document_id)
          ?.publication_decision_id,
      "Sai quyết định xuất bản.",
    );
    requireThat(Object.keys(source.citations).length, "Thiếu citation.");
    const knownPages =
      documents[key].pages > 0 ? documents[key].pages : (entry?.pages ?? 0);
    for (const citation of Object.values(source.citations)) {
      requireThat(
        citation.source_sha256 === documents[key].sha256 &&
          citation.revision_id === entry?.source?.revision &&
          citation.page >= 1 &&
          (knownPages === 0 || citation.page <= knownPages),
        "Sai nguồn/hash/revision/page.",
      );
    }
  }
  if (item.kind === "unanswerable") {
    requireThat(
      answer.status === "insufficient_evidence",
      "Phải từ chối dữ kiện ngoài phạm vi.",
    );
    requireThat(
      answer.statements.length === 0 && !answer.answer,
      "Từ chối không được kèm dữ kiện.",
    );
    return;
  }
  requireThat(answer.status === "answered", "Model từ chối câu có căn cứ.");
  requireThat(
    answer.trace.provider_id === state.runtimeDefaults?.chat,
    "Sai provider chat.",
  );
  requireThat(
    answer.trace.retrieval.mode === "hybrid_rerank" &&
      answer.trace.retrieval.rerank_provider?.provider_id ===
        state.runtimeDefaults?.rerank,
    "Sai retrieval/provider rerank.",
  );
  requireThat(item.facts?.length, "BLOCKED: thiếu nhãn fact có nguồn.");
  for (const statement of answer.statements) {
    requireThat(
      statement.evidence_ids.length &&
        statement.evidence_ids.every((id) => sources.has(id)),
      "Statement có evidence không tồn tại.",
    );
  }
  requireThat(
    matches(answer.answer || "", item.expected_patterns),
    "Thiếu điều kiện/ngoại lệ của đáp án.",
  );
  for (const fact of item.facts) {
    requireThat(
      documents[fact.document],
      `Nhãn fact trỏ nguồn không có: ${fact.document}.`,
    );
    const entry = scenario?.documents?.[fact.document];
    // A fact may describe a year different from the document's main data year
    // (issuing date, previous-season row). Accept only years declared by this
    // item's labels, never an unrelated season.
    const allowedYears = new Set<number>([
      fact.data_year,
      documents[fact.document]?.data_year,
      ...(item.facts ?? []).map((f) => f.data_year),
    ]);
    const pageMatches = (page: number) =>
      fact.pages.length === 0 || fact.pages.includes(page);
    const claims =
      fact.support === "text"
        ? claimGroups(answer.statements)
        : answer.statements;
    const candidates = claims.filter(
      (s) =>
        valuesMatch(s.text, fact) &&
        matches(s.text, fact.subject_patterns) &&
        matches(s.text, fact.metric_patterns) &&
        // Source binding proves the year even when the backend's copied cell
        // statement omits it. An explicitly different year cannot pass.
        (s.text.match(/\b20\d{2}\b/g) || []).every((year) =>
          allowedYears.has(Number(year)),
        ),
    );
    const supported = candidates.some((statement) => {
      const cited = statement.evidence_ids
        .map((id) => sources.get(id))
        .filter(
          (s) =>
            !!s &&
            s.document_id === entry?.publication?.document &&
            Object.values(s.citations).some((c) => pageMatches(c.page)),
        );
      if (!cited.length) return false;
      if (fact.support === "text") {
        // Rule check only; semantic entailment remains a separate human gate.
        return citedTextRuns(
          cited.filter((s): s is Answer["sources"][number] => !!s),
        ).some(
          (text) =>
            valuesMatch(text, fact) &&
            matches(text, fact.subject_patterns) &&
            matches(text, fact.metric_patterns),
        );
      }
      return (answer.trace.grounding?.cell_proofs || []).some((proof) => {
        if (
          !proof.evidence_ids.every((id) =>
            statement.evidence_ids.includes(id),
          ) ||
          !proof.evidence_ids.some((id) =>
            cited.some((s) => s?.evidence_id === id),
          )
        )
          return false;
        const cells: string[] = [];
        let valuePageMatches = false;
        for (const ref of proof.source_cells) {
          const source = answer.sources.find(
            (s) =>
              ref in s.citations &&
              s.document_id === entry?.publication?.document,
          );
          if (!source) return false;
          const prefix = source.structure?.source_table_citation?.split(
            ":",
            1,
          )[0];
          const cell = source.structure?.rows
            ?.flat()
            .find((c) => `${prefix}:${c.evidence_id}` === ref);
          if (!cell) return false;
          // cells/v2 puts the selected value first, then subject and headers.
          // A matching number in a header/another page cannot prove the value.
          if (!cells.length) {
            if (!valuesMatch(cell.text, fact)) return false;
            valuePageMatches = pageMatches(source.citations[ref].page);
          }
          cells.push(cell.text);
        }
        const text = cells.join(" | ");
        return (
          valuePageMatches &&
          matches(text, fact.subject_patterns) &&
          matches(text, fact.metric_patterns)
        );
      });
    });
    requireThat(supported, `Không chứng minh được fact: ${fact.locator}.`);
  }
}
