/**
 * QNU AI Platform Typed API Client (Facade Entrypoint)
 *
 * Re-exports all domain types, constants, and aggregates individual domain services
 * (System, Assistants, Knowledge, Jobs, ModelOps, Evaluation, Tools, Workflows, OCR Studio)
 * to provide 100% backward compatibility for all existing components and pages.
 */

// 1. Re-export all domain types
export * from "@/types";

// 2. Re-export static constants
export * from "@/constants";

// 3. Import domain API services
import { assistantsApi } from "./assistants-api";
import { evaluationApi } from "./evaluation-api";
import { isJsonObject } from "./http-client";
import { jobsApi, mapJobToIngestionTask } from "./jobs-api";
import { knowledgeApi } from "./knowledge-api";
import { modelopsApi } from "./modelops-api";
import { ocrStudioApi } from "./ocr-studio-api";
import { isNodeManifest, systemApi } from "./system-api";
import { toolsApi } from "./tools-api";
import { workflowRunsApi } from "./workflow-runs-api";
import { workflowsApi } from "./workflows-api";

// 4. Re-export domain services and helpers for modern modular usage
export {
  assistantsApi,
  evaluationApi,
  isJsonObject,
  isNodeManifest,
  jobsApi,
  knowledgeApi,
  mapJobToIngestionTask,
  modelopsApi,
  ocrStudioApi,
  systemApi,
  toolsApi,
  workflowRunsApi,
  workflowsApi,
};

// 5. Facade apiClient object preserving all method signatures for backward compatibility
export const apiClient = {
  ...systemApi,
  ...assistantsApi,
  ...knowledgeApi,
  ...jobsApi,
  ...modelopsApi,
  ...evaluationApi,
  ...toolsApi,
  ...workflowRunsApi,
  ...workflowsApi,
  ...ocrStudioApi,
};
