import type { CatalogItem } from "@/api/modelops";

export function providerLabel(item: CatalogItem): string {
  const parts = item.name.split("·").map((part) => part.trim());
  if (
    parts.length > 1 &&
    parts[parts.length - 1].toLowerCase() === item.model_name.toLowerCase()
  ) {
    return parts.slice(0, -1).join(" · ");
  }
  return item.name;
}

export function localityLabel(providerType?: string | null): string {
  if (!providerType) return "";
  return ["local", "ollama", "llamacpp"].includes(providerType)
    ? "Cục bộ"
    : "Đám mây";
}
