/**
 * Single source of truth for the QNU AI v1 API surface.
 * Re-exports all domain endpoint path definitions and global configurations.
 *
 * Paths are grouped by domain under `frontendV2/src/api/<domain>/`.
 * `API_V1_PREFIX` matches `Settings.API_PREFIX` in `backendV1/qnu/platform/config.py`.
 */

export * from "./assistants";
export * from "./auth";
export * from "./compilation";
export * from "./config";
export * from "./conversations";
export * from "./documents";
export * from "./inbox";
export * from "./inbox";
export * from "./indexing";
export * from "./integrations";
export * from "./knowledge";
export * from "./lifecycle";
export * from "./modelops";
export * from "./ocr";
export * from "./operations";
export * from "./preparation";
export * from "./reviews";
export * from "./workspaces";
