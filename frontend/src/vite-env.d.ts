/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_BASE_URL?: string;
  readonly VITE_BFF_BASE_URL?: string;
  readonly VITE_AUTH_MODE?: "bff" | "demo";
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
