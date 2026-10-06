import type { ChatMessageItem } from "../hooks/use-rag-stream";

export interface ExportConversationOptions {
  assistantName: string;
  assistantCode: string;
  assistantDescription?: string;
  messages: ChatMessageItem[];
}

/**
 * Format a list of chat messages into a structured Markdown document.
 */
export function formatConversationToMarkdown(options: ExportConversationOptions): string {
  const { assistantName, assistantCode, assistantDescription, messages } = options;
  const now = new Date();
  const formattedDate = now.toLocaleString("vi-VN", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });

  const lines: string[] = [];

  // 1. Header Information
  lines.push(`# Lịch Sử Cuộc Trò Chuyện — ${assistantName}`);
  lines.push("");
  lines.push(`- **Trợ lý AI**: ${assistantName} (\`${assistantCode}\`)`);
  if (assistantDescription) {
    lines.push(`- **Mô tả**: ${assistantDescription}`);
  }
  lines.push(`- **Thời gian xuất**: ${formattedDate}`);
  lines.push(`- **Tổng số tin nhắn**: ${messages.length} lượt trao đổi`);
  lines.push("");
  lines.push("---");
  lines.push("");

  // 2. Chat Turns
  let turnNumber = 1;
  for (const msg of messages) {
    const timeLabel = msg.timestamp
      ? new Date(msg.timestamp).toLocaleTimeString("vi-VN", {
          hour: "2-digit",
          minute: "2-digit",
          second: "2-digit",
        })
      : "";

    if (msg.role === "user") {
      lines.push(`### [Lượt ${turnNumber}] 👤 Người dùng ${timeLabel ? `(${timeLabel})` : ""}`);
      lines.push("");
      lines.push(msg.content.trim());
      lines.push("");

      if (msg.attachments && msg.attachments.length > 0) {
        lines.push("**Tệp đính kèm:**");
        for (const att of msg.attachments) {
          const sizeKb = Math.round(att.size / 1024);
          lines.push(`- 📎 \`${att.name}\` (${sizeKb} KB)`);
        }
        lines.push("");
      }
    } else if (msg.role === "assistant") {
      lines.push(
        `### [Lượt ${turnNumber}] 🎓 Trợ lý ${assistantName} ${timeLabel ? `(${timeLabel})` : ""}`
      );
      lines.push("");
      lines.push(msg.content.trim());
      lines.push("");

      if (msg.citations && msg.citations.length > 0) {
        lines.push(`**Căn cứ minh chứng (${msg.citations.length} nguồn tài liệu):**`);
        msg.citations.forEach((c, idx) => {
          const pageStr = c.page ? ` — Trang ${c.page}` : "";
          const excerptStr = c.excerpt ? `\n  > Trích dẫn: "${c.excerpt.trim()}"` : "";
          lines.push(`- [${idx + 1}] **${c.title || c.document_name}**${pageStr}${excerptStr}`);
        });
        lines.push("");
      }

      if (msg.suggestedQuestions && msg.suggestedQuestions.length > 0) {
        lines.push("**Gợi ý câu hỏi tiếp theo:**");
        for (const q of msg.suggestedQuestions) {
          lines.push(`- 💡 ${q}`);
        }
        lines.push("");
      }

      turnNumber++;
    } else if (msg.role === "system") {
      lines.push(`### ⚙️ Hệ thống ${timeLabel ? `(${timeLabel})` : ""}`);
      lines.push("");
      lines.push(msg.content.trim());
      lines.push("");
    }

    lines.push("---");
    lines.push("");
  }

  // Footer note
  lines.push("> *Tệp được xuất tự động từ Nền tảng AI Trường Đại học Quy Nhơn (QNU AI Platform).*");
  lines.push("");

  return lines.join("\n");
}

/**
 * Trigger client-side download of a Markdown file.
 */
export function downloadMarkdownFile(filename: string, content: string): void {
  const blob = new Blob([content], { type: "text/markdown;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.setAttribute("download", filename);
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}
