export type RouteViewType =
  | "dashboard"
  | "assistants_list"
  | "assistant_create"
  | "assistant_detail"
  | "knowledge"
  | "knowledge_ocr_lab"
  | "document_types_list"
  | "document_type_detail"
  | "models"
  | "conversations"
  | "quality"
  | "operations_runs"
  | "settings_integrations"
  | "advanced_workflows"
  | "dag_canvas"
  | "advanced_nodes"
  | "advanced_tools"
  | "design_system"
  | "not_found";

export interface ResolvedRoute {
  viewType: RouteViewType;
  canonicalPath: string;
  searchParams: URLSearchParams;
  params: Record<string, string>;
  shouldRedirect: boolean;
}

/**
 * Phân giải pathname và search params thành ResolvedRoute có kiểu dữ liệu rõ ràng,
 * tự động kích hoạt redirect cho các URL cũ để bảo toàn 100% khả năng tương thích ngược.
 */
export function resolveRoute(pathname: string, searchStr = ""): ResolvedRoute {
  const searchParams = new URLSearchParams(searchStr);
  const cleanPath = pathname.replace(/\/+$/, "") || "/";

  // 1. Dashboard
  if (cleanPath === "/") {
    return {
      viewType: "dashboard",
      canonicalPath: "/",
      searchParams,
      params: {},
      shouldRedirect: false,
    };
  }

  // 2. Assistants Workspace
  if (cleanPath === "/assistants") {
    return {
      viewType: "assistants_list",
      canonicalPath: "/assistants",
      searchParams,
      params: {},
      shouldRedirect: false,
    };
  }
  if (cleanPath === "/assistants/new") {
    return {
      viewType: "assistant_create",
      canonicalPath: "/assistants/new",
      searchParams,
      params: {},
      shouldRedirect: false,
    };
  }

  // /assistants/:ref/*
  if (cleanPath.startsWith("/assistants/")) {
    const parts = cleanPath.split("/").filter(Boolean); // ["assistants", ":ref", ...sub]
    const assistantId = decodeURIComponent(parts[1] || "");
    const subRoute = parts[2] || "overview";

    const validSubViews = ["overview", "playground", "workflow", "channels", "quality", "runs"];
    const subView = validSubViews.includes(subRoute) ? subRoute : "overview";

    return {
      viewType: "assistant_detail",
      canonicalPath: `/assistants/${encodeURIComponent(assistantId)}${subRoute !== "overview" ? `/${subRoute}` : ""}`,
      searchParams,
      params: { assistantId, subView },
      shouldRedirect: false,
    };
  }

  // 3. Legacy /chat -> Redirect sang Assistant Playground
  if (cleanPath === "/chat") {
    const assistantCode = searchParams.get("assistant");
    const targetAssistant = assistantCode || "ast_admissions";
    return {
      viewType: "assistant_detail",
      canonicalPath: `/assistants/${encodeURIComponent(targetAssistant)}/playground`,
      searchParams,
      params: { assistantId: targetAssistant, subView: "playground" },
      shouldRedirect: true,
    };
  }

  // 4. Knowledge Workspace
  if (cleanPath === "/knowledge/ocr-lab") {
    return {
      viewType: "knowledge_ocr_lab",
      canonicalPath: "/knowledge/ocr-lab",
      searchParams,
      params: {},
      shouldRedirect: false,
    };
  }
  // OCR Verification for specific document
  if (cleanPath.startsWith("/knowledge/documents/") && cleanPath.endsWith("/ocr")) {
    const docId = decodeURIComponent(
      cleanPath.replace("/knowledge/documents/", "").replace(/\/ocr$/, "")
    );
    return {
      viewType: "knowledge_ocr_lab",
      canonicalPath: `/knowledge/documents/${encodeURIComponent(docId)}/ocr`,
      searchParams,
      params: { documentId: docId },
      shouldRedirect: false,
    };
  }

  if (cleanPath.startsWith("/ocr/") && cleanPath !== "/ocr/") {
    const docId = decodeURIComponent(cleanPath.replace("/ocr/", ""));
    return {
      viewType: "knowledge_ocr_lab",
      canonicalPath: `/knowledge/documents/${encodeURIComponent(docId)}/ocr`,
      searchParams,
      params: { documentId: docId },
      shouldRedirect: true,
    };
  }
  if (cleanPath === "/ocr") {
    return {
      viewType: "knowledge_ocr_lab",
      canonicalPath: "/knowledge/ocr-lab",
      searchParams,
      params: {},
      shouldRedirect: true,
    };
  }

  // Document Types under Knowledge Settings
  if (cleanPath === "/knowledge/settings/document-types") {
    return {
      viewType: "document_types_list",
      canonicalPath: "/knowledge/settings/document-types",
      searchParams,
      params: {},
      shouldRedirect: false,
    };
  }
  if (cleanPath.startsWith("/knowledge/settings/document-types/")) {
    const docTypeCode = decodeURIComponent(
      cleanPath.replace("/knowledge/settings/document-types/", "")
    );
    return {
      viewType: "document_type_detail",
      canonicalPath: `/knowledge/settings/document-types/${encodeURIComponent(docTypeCode)}`,
      searchParams,
      params: { docTypeCode },
      shouldRedirect: false,
    };
  }
  if (cleanPath === "/document-types") {
    return {
      viewType: "document_types_list",
      canonicalPath: "/knowledge/settings/document-types",
      searchParams,
      params: {},
      shouldRedirect: true,
    };
  }
  if (cleanPath.startsWith("/document-types/")) {
    const docTypeCode = decodeURIComponent(cleanPath.replace("/document-types/", ""));
    return {
      viewType: "document_type_detail",
      canonicalPath: `/knowledge/settings/document-types/${encodeURIComponent(docTypeCode)}`,
      searchParams,
      params: { docTypeCode },
      shouldRedirect: true,
    };
  }

  // Core Knowledge
  if (cleanPath === "/knowledge" || cleanPath.startsWith("/knowledge/")) {
    return {
      viewType: "knowledge",
      canonicalPath: cleanPath,
      searchParams,
      params: {},
      shouldRedirect: false,
    };
  }

  // 5. ModelOps
  if (cleanPath === "/models" || cleanPath.startsWith("/models/")) {
    return {
      viewType: "models",
      canonicalPath: cleanPath,
      searchParams,
      params: {},
      shouldRedirect: false,
    };
  }

  // 6. Conversations
  if (cleanPath === "/conversations" || cleanPath.startsWith("/conversations/")) {
    return {
      viewType: "conversations",
      canonicalPath: cleanPath,
      searchParams,
      params: {},
      shouldRedirect: false,
    };
  }

  // 7. Quality & Evaluation
  if (cleanPath === "/quality" || cleanPath.startsWith("/quality/")) {
    return {
      viewType: "quality",
      canonicalPath: "/quality",
      searchParams,
      params: {},
      shouldRedirect: false,
    };
  }
  if (cleanPath === "/evaluation" || cleanPath.startsWith("/evaluation/")) {
    return {
      viewType: "quality",
      canonicalPath: "/quality",
      searchParams,
      params: {},
      shouldRedirect: true,
    };
  }

  // 8. Operations Runs
  if (cleanPath === "/operations/runs" || cleanPath.startsWith("/operations/runs/")) {
    return {
      viewType: "operations_runs",
      canonicalPath: cleanPath,
      searchParams,
      params: {},
      shouldRedirect: false,
    };
  }
  if (cleanPath === "/runs" || cleanPath.startsWith("/runs/")) {
    const remainder = cleanPath.replace(/^\/runs/, "");
    const targetPath = `/operations/runs${remainder}`;
    return {
      viewType: "operations_runs",
      canonicalPath: targetPath,
      searchParams,
      params: {},
      shouldRedirect: true,
    };
  }

  // 9. Settings & Integrations
  if (cleanPath === "/settings/integrations") {
    return {
      viewType: "settings_integrations",
      canonicalPath: "/settings/integrations",
      searchParams,
      params: {},
      shouldRedirect: false,
    };
  }
  if (cleanPath === "/channels" || cleanPath.startsWith("/channels/")) {
    searchParams.set("tab", "channels");
    return {
      viewType: "settings_integrations",
      canonicalPath: "/settings/integrations",
      searchParams,
      params: { tab: "channels" },
      shouldRedirect: true,
    };
  }
  if (cleanPath === "/developer" || cleanPath.startsWith("/developer/")) {
    searchParams.set("tab", "api-keys");
    return {
      viewType: "settings_integrations",
      canonicalPath: "/settings/integrations",
      searchParams,
      params: { tab: "api-keys" },
      shouldRedirect: true,
    };
  }

  // 10. Advanced Workflows & DAG
  if (cleanPath === "/advanced/workflows") {
    return {
      viewType: "advanced_workflows",
      canonicalPath: "/advanced/workflows",
      searchParams,
      params: {},
      shouldRedirect: false,
    };
  }
  if (cleanPath === "/workflows") {
    return {
      viewType: "advanced_workflows",
      canonicalPath: "/advanced/workflows",
      searchParams,
      params: {},
      shouldRedirect: true,
    };
  }
  if (
    cleanPath.startsWith("/workflows/") ||
    cleanPath === "/canvas" ||
    cleanPath.startsWith("/canvas/")
  ) {
    return {
      viewType: "dag_canvas",
      canonicalPath: cleanPath,
      searchParams,
      params: {},
      shouldRedirect: false,
    };
  }

  // 11. Advanced Capabilities: Nodes & Tools
  if (cleanPath === "/advanced/capabilities/nodes") {
    return {
      viewType: "advanced_nodes",
      canonicalPath: "/advanced/capabilities/nodes",
      searchParams,
      params: {},
      shouldRedirect: false,
    };
  }
  if (cleanPath === "/nodes") {
    return {
      viewType: "advanced_nodes",
      canonicalPath: "/advanced/capabilities/nodes",
      searchParams,
      params: {},
      shouldRedirect: true,
    };
  }
  if (cleanPath === "/advanced/capabilities/tools") {
    return {
      viewType: "advanced_tools",
      canonicalPath: "/advanced/capabilities/tools",
      searchParams,
      params: {},
      shouldRedirect: false,
    };
  }
  if (cleanPath === "/tools") {
    return {
      viewType: "advanced_tools",
      canonicalPath: "/advanced/capabilities/tools",
      searchParams,
      params: {},
      shouldRedirect: true,
    };
  }

  // 12. Design System (Dev only)
  if (cleanPath === "/design-system") {
    return {
      viewType: "design_system",
      canonicalPath: "/design-system",
      searchParams,
      params: {},
      shouldRedirect: false,
    };
  }

  // Fallback
  return {
    viewType: "not_found",
    canonicalPath: cleanPath,
    searchParams,
    params: {},
    shouldRedirect: false,
  };
}
