export interface MarkdownBlock {
  id: string;
  type:
    | "h1"
    | "h2"
    | "h3"
    | "h4"
    | "p"
    | "ul"
    | "ol"
    | "table"
    | "quote"
    | "divider";
  content: string;
  items?: Array<{ id: string; text: string }>;
  tableData?: {
    headers: Array<{ id: string; text: string }>;
    rows: Array<{ id: string; cells: Array<{ id: string; text: string }> }>;
  };
}

/**
 * Parses markdown text into structural blocks (headings, lists, tables, paragraphs, quotes).
 * Supports standard table formats, bulleted lists, and structured documents.
 */
export function parseMarkdownBlocks(
  content: string,
  options?: { skipPreamble?: boolean },
): MarkdownBlock[] {
  if (!content) return [];

  const lines = content.split(/\r?\n/);
  const blocks: MarkdownBlock[] = [];

  let currentList: {
    type: "ul" | "ol";
    items: Array<{ id: string; text: string }>;
  } | null = null;
  let tableLines: string[] = [];

  const flushList = () => {
    if (currentList) {
      blocks.push({
        id: `list_${blocks.length}_${currentList.type}`,
        type: currentList.type,
        content: "",
        items: currentList.items,
      });
      currentList = null;
    }
  };

  const flushTable = () => {
    if (tableLines.length >= 1) {
      const parseRow = (line: string) =>
        line
          .replace(/^\|/, "")
          .replace(/\|$/, "")
          .split("|")
          .map((c) => c.trim());

      const isSeparator =
        tableLines.length > 1 &&
        /^(\s*:?-+:?\s*\|?)+$/.test(
          tableLines[1].replace(/^\|/, "").replace(/\|$/, ""),
        );

      const rawHeaders = parseRow(tableLines[0]);
      const headers = rawHeaders.map((h, i) => ({
        id: `th_${blocks.length}_${i}`,
        text: h,
      }));

      const rows: Array<{
        id: string;
        cells: Array<{ id: string; text: string }>;
      }> = [];

      const startIndex = isSeparator ? 2 : 1;
      for (let i = startIndex; i < tableLines.length; i++) {
        if (tableLines[i].includes("|")) {
          const rawCells = parseRow(tableLines[i]);
          rows.push({
            id: `tr_${blocks.length}_${i}`,
            cells: rawCells.map((c, cellIdx) => ({
              id: `td_${blocks.length}_${i}_${cellIdx}`,
              text: c,
            })),
          });
        }
      }

      blocks.push({
        id: `tbl_${blocks.length}`,
        type: "table",
        content: "",
        tableData: { headers, rows },
      });
    }
    tableLines = [];
  };

  const preamble = lines.findIndex(
    (line, index) => index > 0 && line.trim().length > 0,
  );

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i].trimEnd();
    const trimmed = line.trim();

    if (
      options?.skipPreamble &&
      i === preamble &&
      trimmed === "> Bản nháp chưa duyệt."
    ) {
      continue;
    }

    // Check table row
    if (
      trimmed.startsWith("|") ||
      (trimmed.includes("|") &&
        tableLines.length > 0 &&
        !trimmed.startsWith("#"))
    ) {
      flushList();
      tableLines.push(trimmed);
      continue;
    }

    if (tableLines.length > 0) {
      flushTable();
    }

    if (!trimmed) {
      flushList();
      continue;
    }

    // Check headings
    if (trimmed.startsWith("# ")) {
      flushList();
      blocks.push({
        id: `h1_${blocks.length}`,
        type: "h1",
        content: trimmed.replace(/^#\s+/, ""),
      });
    } else if (trimmed.startsWith("## ")) {
      flushList();
      blocks.push({
        id: `h2_${blocks.length}`,
        type: "h2",
        content: trimmed.replace(/^##\s+/, ""),
      });
    } else if (trimmed.startsWith("### ")) {
      flushList();
      blocks.push({
        id: `h3_${blocks.length}`,
        type: "h3",
        content: trimmed.replace(/^###\s+/, ""),
      });
    } else if (trimmed.startsWith("#### ")) {
      flushList();
      blocks.push({
        id: `h4_${blocks.length}`,
        type: "h4",
        content: trimmed.replace(/^####\s+/, ""),
      });
    } else if (
      trimmed.startsWith("---") ||
      trimmed.startsWith("***") ||
      trimmed.startsWith("___")
    ) {
      flushList();
      blocks.push({
        id: `div_${blocks.length}`,
        type: "divider",
        content: "",
      });
    } else if (trimmed.startsWith("> ")) {
      flushList();
      blocks.push({
        id: `quote_${blocks.length}`,
        type: "quote",
        content: trimmed.replace(/^>\s+/, ""),
      });
    } else if (
      trimmed.startsWith("- ") ||
      trimmed.startsWith("* ") ||
      trimmed.startsWith("+ ")
    ) {
      const itemText = trimmed.replace(/^[-*+]\s+/, "");
      if (currentList && currentList.type === "ul") {
        currentList.items.push({
          id: `ul_item_${blocks.length}_${currentList.items.length}`,
          text: itemText,
        });
      } else {
        flushList();
        currentList = {
          type: "ul",
          items: [{ id: `ul_item_${blocks.length}_0`, text: itemText }],
        };
      }
    } else if (/^\d+[.)]\s+/.test(trimmed)) {
      const itemText = trimmed.replace(/^\d+[.)]\s+/, "");
      if (currentList && currentList.type === "ol") {
        currentList.items.push({
          id: `ol_item_${blocks.length}_${currentList.items.length}`,
          text: itemText,
        });
      } else {
        flushList();
        currentList = {
          type: "ol",
          items: [{ id: `ol_item_${blocks.length}_0`, text: itemText }],
        };
      }
    } else {
      flushList();
      // Join continuous lines with newline if the previous block is already a paragraph
      const lastBlock = blocks[blocks.length - 1];
      if (lastBlock && lastBlock.type === "p" && i > 0 && lines[i - 1].trim()) {
        lastBlock.content += `\n${trimmed}`;
      } else {
        blocks.push({
          id: `p_${blocks.length}`,
          type: "p",
          content: trimmed,
        });
      }
    }
  }

  flushList();
  flushTable();

  return blocks;
}
