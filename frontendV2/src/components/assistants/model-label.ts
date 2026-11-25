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

export function modelNameLabel(item: CatalogItem): string {
  const model = item.model_name?.trim();
  return model || item.name;
}

export function modelWithProviderLabel(item: CatalogItem): string {
  const model = modelNameLabel(item);
  const provider = providerLabel(item).trim();
  if (!provider || provider.toLowerCase() === model.toLowerCase()) {
    return model;
  }
  return `${model} · ${provider}`;
}

export function localityLabel(providerType?: string | null): string {
  if (!providerType) return "";
  return ["local", "ollama", "llamacpp"].includes(providerType)
    ? "Cục bộ"
    : "Đám mây";
}
