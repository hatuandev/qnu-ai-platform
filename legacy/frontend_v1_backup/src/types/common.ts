/** Common system & node types */

export interface BackendHealth {
  status: "ok" | "degraded" | "offline";
  service: string;
  version: string;
  dependencies?: {
    database: string;
    redis: string;
  };
}

export interface NodeManifest {
  api_version: string;
  type: string;
  version: string;
  display_name: string;
  description: string;
  category: string;
  status: string;
  input_schema: Record<string, unknown>;
  output_schema: Record<string, unknown>;
  config_schema: Record<string, unknown>;
}
