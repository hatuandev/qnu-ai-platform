import type { BackendHealth, NodeManifest } from "@/types/common";
import { BASE_URL, isJsonObject } from "./http-client";

export function isNodeManifest(value: unknown): value is NodeManifest {
  if (!isJsonObject(value)) {
    return false;
  }

  const stringFields = [
    "api_version",
    "type",
    "version",
    "display_name",
    "description",
    "category",
    "status",
  ];
  return (
    stringFields.every((field) => typeof value[field] === "string") &&
    isJsonObject(value.input_schema) &&
    isJsonObject(value.output_schema) &&
    isJsonObject(value.config_schema)
  );
}

export const systemApi = {
  async getHealth(): Promise<BackendHealth> {
    try {
      const res = await fetch("/health/live");
      if (res.ok) {
        const data = await res.json();
        return {
          status: "ok",
          service: data.service || "qnu-ai-platform",
          version: data.version || "0.1.0",
          dependencies: { database: "connected", redis: "connected" },
        };
      }
    } catch {
      // Fallback
    }
    return {
      status: "offline",
      service: "qnu-ai-platform (Simulation)",
      version: "0.1.0",
    };
  },

  async getNodeCatalog(): Promise<NodeManifest[]> {
    const res = await fetch(`${BASE_URL}/nodes`);
    if (!res.ok) {
      throw new Error(`Không tải được danh mục Node (HTTP ${res.status}).`);
    }

    const data: unknown = await res.json();
    if (!isJsonObject(data) || !Array.isArray(data.items)) {
      throw new Error("Backend trả về danh mục Node không đúng định dạng.");
    }

    const manifests = data.items.filter(isNodeManifest);
    if (manifests.length !== data.items.length) {
      throw new Error("Backend trả về NodeManifest không hợp lệ.");
    }
    return manifests;
  },
};
