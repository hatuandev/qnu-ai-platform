import type { Connection } from "./api";

export function connectionProtocol(connection: Pick<Connection, "api_type">) {
  switch (connection.api_type) {
    case "mineru":
      return "Dịch vụ OCR PDF";
    case "ollama":
      return "Ollama";
    case "llamacpp":
      return "llama.cpp";
    case "anthropic":
      return "Anthropic";
    case "gemini":
      return "Gemini";
    case "openai":
    case "openai_compatible":
    case "chat_completions":
      return "OpenAI Compatible";
    default:
      return "API mô hình";
  }
}

export function connectionEndpoint(
  connection: Pick<Connection, "api_type" | "base_url">,
) {
  const base = connection.base_url.replace(/\/+$/, "");
  return connection.api_type === "mineru"
    ? `${base.replace(/\/v1$/, "")}/v1/tasks`
    : base;
}
