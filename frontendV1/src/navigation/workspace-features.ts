import {
  Archive,
  Bot,
  ClipboardList,
  Database,
  FileClock,
  FileSearch,
  Gauge,
  MessageSquare,
  Settings2,
  UsersRound,
} from "lucide-react";

/** Shared by sidebar, command menu, breadcrumbs and the resource selector. */
export const workspaceFeatures = {
  collections: {
    title: "Kho tri thức",
    group: "Tri thức",
    icon: Database,
    kind: "workspace",
    to: "/workspaces/$workspaceId/knowledge",
  },
  ocr: {
    title: "OCR & chính tả",
    group: "Tri thức",
    icon: FileClock,
    kind: "collection",
    tab: "sources",
  },
  compiler: {
    title: "Biên soạn",
    group: "Tri thức",
    icon: ClipboardList,
    kind: "collection",
    tab: "compilations",
  },
  documents: {
    title: "Xuất bản",
    group: "Tri thức",
    icon: FileClock,
    kind: "collection",
    tab: "documents",
  },
  search: {
    title: "Tìm kiếm",
    group: "Tri thức",
    icon: FileSearch,
    kind: "collection",
    tab: "index",
  },
  answers: {
    title: "Hỏi đáp",
    group: "Tri thức",
    icon: MessageSquare,
    kind: "collection",
    page: "answers",
  },
  evaluation: {
    title: "Đánh giá RAG",
    group: "Tri thức",
    icon: Gauge,
    kind: "collection",
    page: "evaluations",
  },
  assistants: {
    title: "Trợ lý AI",
    group: "Trợ lý",
    icon: Bot,
    kind: "workspace",
    to: "/workspaces/$workspaceId/assistants",
  },
  conversations: {
    title: "Hội thoại",
    group: "Trợ lý",
    icon: MessageSquare,
    kind: "workspace",
    to: "/workspaces/$workspaceId/conversations",
  },
  members: {
    title: "Thành viên",
    group: "Cấu hình đơn vị",
    icon: UsersRound,
    kind: "workspace",
    to: "/workspaces/$workspaceId/members",
  },
  models: {
    title: "Model được phép dùng",
    group: "Cấu hình đơn vị",
    icon: Settings2,
    kind: "workspace",
    to: "/workspaces/$workspaceId/models",
  },
  quota: {
    title: "Hạn mức",
    group: "Cấu hình đơn vị",
    icon: Gauge,
    kind: "workspace",
    to: "/workspaces/$workspaceId/quota",
  },
  audit: {
    title: "Nhật ký",
    group: "Cấu hình đơn vị",
    icon: FileClock,
    kind: "workspace",
    to: "/workspaces/$workspaceId/audit",
  },
  resources: {
    title: "Tài nguyên",
    group: "Vận hành",
    icon: Archive,
    kind: "workspace",
    to: "/workspaces/$workspaceId/resources",
  },
  jobs: {
    title: "Tác vụ",
    group: "Vận hành",
    icon: ClipboardList,
    kind: "workspace",
    to: "/workspaces/$workspaceId/operations",
    view: "jobs",
  },
  backups: {
    title: "Sao lưu",
    group: "Cấu hình đơn vị",
    icon: Archive,
    kind: "workspace",
    to: "/workspaces/$workspaceId/operations",
    view: "backups",
  },
  storage: {
    title: "Dọn dữ liệu",
    group: "Cấu hình đơn vị",
    icon: Database,
    kind: "workspace",
    to: "/workspaces/$workspaceId/operations",
    view: "storage",
  },
} as const;

export type WorkspaceFeature = keyof typeof workspaceFeatures;
/** The 4 workspace-scoped items among the 6 primary sidebar entries. */
export const primaryWorkspaceFeatureKeys: WorkspaceFeature[] = [
  "collections",
  "assistants",
  "conversations",
  "jobs",
];
export const workspaceFeatureKeys: WorkspaceFeature[] = [
  "ocr",
  "compiler",
  "documents",
  "search",
  "answers",
  "evaluation",
  "collections",
  "assistants",
  "conversations",
  "jobs",
  "members",
  "models",
  "quota",
  "audit",
  "backups",
  "storage",
];
export const workspaceFeatureGroups = [
  "Tri thức",
  "Trợ lý",
  "Vận hành",
  "Cấu hình đơn vị",
] as const;
export type FeatureScope = { workspaceId?: string; collectionId?: string };

export function isWorkspaceFeature(value: string): value is WorkspaceFeature {
  return Object.hasOwn(workspaceFeatures, value);
}

export function featureTarget(feature: WorkspaceFeature, scope: FeatureScope) {
  const destination = workspaceFeatures[feature];
  const { workspaceId, collectionId } = scope;
  if (!workspaceId || (destination.kind === "collection" && !collectionId)) {
    return {
      to: "/workspaces/choose/$feature",
      params: { feature },
      search: { workspaceId, page: 1 },
    } as const;
  }
  if (destination.kind === "workspace") {
    return {
      to: destination.to,
      params: { workspaceId },
      search: {
        page: 1,
        pageSize: 20,
        limit: 20,
        offset: 0,
        view: "view" in destination ? destination.view : undefined,
      },
    } as const;
  }
  const params = { workspaceId, collectionId: collectionId as string };
  if ("tab" in destination) {
    return {
      to: "/workspaces/$workspaceId/collections/$collectionId",
      params,
      search: {
        page: 1,
        pageSize: 20,
        tab: destination.tab,
        sourceAction: feature === "ocr" ? "ocr" : undefined,
      },
    } as const;
  }
  if (destination.page === "answers")
    return {
      to: "/workspaces/$workspaceId/collections/$collectionId/answers",
      params,
    } as const;
  return {
    to: "/workspaces/$workspaceId/collections/$collectionId/evaluations",
    params,
    search: { page: 1 },
  } as const;
}

function id(value: unknown): string | undefined {
  return typeof value === "string" && value.length > 0 && value.length <= 64
    ? value
    : undefined;
}

/** URL scope is a selection, never authorization. Undefined means no scope change. */
export function routeFeatureScope(
  pathname: string,
  search: Record<string, unknown>,
): FeatureScope | undefined {
  if (pathname.startsWith("/workspaces/choose/"))
    return { workspaceId: id(search.workspaceId) };
  if (pathname === "/dashboard" && id(search.workspaceId))
    return { workspaceId: id(search.workspaceId) };
  const match =
    /^\/workspaces\/([^/]+)(?:\/(?:collections|knowledge)\/([^/]+))?/.exec(
      pathname,
    );
  if (!match) return undefined;
  try {
    return {
      workspaceId: id(decodeURIComponent(match[1])),
      collectionId: match[2] ? id(decodeURIComponent(match[2])) : undefined,
    };
  } catch {
    return {};
  }
}

export function isFeatureActive(
  feature: WorkspaceFeature,
  pathname: string,
  search: Record<string, unknown>,
): boolean {
  if (pathname.startsWith("/workspaces/choose/"))
    return pathname === `/workspaces/choose/${feature}`;
  const destination = workspaceFeatures[feature];
  const match = /^\/workspaces\/[^/]+(.*)/.exec(pathname);
  if (!match) return false;
  const suffix = match[1].replace(/\/$/, "");
  if (destination.kind === "workspace") {
    const target = destination.to.replace("/workspaces/$workspaceId", "");
    if (feature === "collections")
      return (
        suffix === "/collections" ||
        suffix === "/knowledge" ||
        /^\/(?:collections|knowledge)\/[^/]+\/sources\/[^/]+$/.test(suffix) ||
        (/^\/knowledge\/[^/]+$/.test(suffix) &&
          (!search.stage || search.stage === "files"))
      );
    if ("view" in destination)
      return suffix === target && (search.view ?? "jobs") === destination.view;
    return suffix === target || suffix.startsWith(`${target}/`);
  }
  if (feature === "ocr") {
    if (
      /^\/(?:collections|knowledge)\/[^/]+\/sources\/[^/]+\/ocr/.test(suffix) ||
      /^\/knowledge\/[^/]+\/ocr/.test(suffix) ||
      (/^\/(?:collections|knowledge)\/[^/]+$/.test(suffix) &&
        (search.stage === "ocr" ||
          search.sourceAction === "ocr" ||
          search.tab === "sources"))
    )
      return true;
    return false;
  }
  if (feature === "compiler") {
    if (
      /^\/(?:collections|knowledge)\/[^/]+\/compilations/.test(suffix) ||
      (/^\/(?:collections|knowledge)\/[^/]+$/.test(suffix) &&
        (search.stage === "compiler" || search.tab === "compilations"))
    )
      return true;
    return false;
  }
  if (feature === "documents") {
    if (
      /^\/(?:collections|knowledge)\/[^/]+\/documents/.test(suffix) ||
      (/^\/(?:collections|knowledge)\/[^/]+$/.test(suffix) &&
        (search.stage === "publication" || search.tab === "documents"))
    )
      return true;
    return false;
  }
  if (feature === "search") {
    if (
      /^\/(?:collections|knowledge)\/[^/]+\/search/.test(suffix) ||
      (/^\/(?:collections|knowledge)\/[^/]+$/.test(suffix) &&
        (search.stage === "serving" || search.tab === "index"))
    )
      return true;
    return false;
  }
  if ("tab" in destination) {
    return (
      /^\/(?:collections|knowledge)\/[^/]+$/.test(suffix) &&
      (search.tab ?? "sources") === destination.tab
    );
  }
  return new RegExp(
    `^/(?:collections|knowledge)/[^/]+/${destination.page}$`,
  ).test(suffix);
}

export function isPrimarySidebarFeatureActive(
  feature: WorkspaceFeature,
  pathname: string,
  search: Record<string, unknown>,
): boolean {
  if (feature === "collections") {
    if (
      pathname.startsWith("/workspaces/choose/") &&
      [
        "collections",
        "ocr",
        "compiler",
        "documents",
        "search",
        "answers",
        "evaluation",
      ].includes(pathname.replace("/workspaces/choose/", ""))
    ) {
      return true;
    }
    const match = /^\/workspaces\/[^/]+(.*)/.exec(pathname);
    if (!match) return false;
    const suffix = match[1].replace(/\/$/, "");
    return (
      suffix === "/collections" ||
      suffix === "/knowledge" ||
      suffix.startsWith("/collections/") ||
      suffix.startsWith("/knowledge/")
    );
  }
  return isFeatureActive(feature, pathname, search);
}

export function isSettingsRouteActive(
  pathname: string,
  search: Record<string, unknown>,
): boolean {
  if (
    pathname === "/settings" ||
    pathname.startsWith("/settings/") ||
    pathname === "/providers" ||
    pathname.startsWith("/modelops/") ||
    pathname === "/workspaces"
  ) {
    return true;
  }
  if (
    pathname.startsWith("/workspaces/choose/") &&
    ["members", "models", "quota", "audit", "backups", "storage"].includes(
      pathname.replace("/workspaces/choose/", ""),
    )
  ) {
    return true;
  }
  const match = /^\/workspaces\/[^/]+(.*)/.exec(pathname);
  if (!match) return false;
  const suffix = match[1].replace(/\/$/, "");
  if (
    suffix === "/members" ||
    suffix === "/models" ||
    suffix === "/quota" ||
    suffix === "/audit" ||
    suffix === "/resources"
  ) {
    return true;
  }
  if (
    suffix === "/operations" &&
    (search.view === "backups" || search.view === "storage")
  ) {
    return true;
  }
  return false;
}
