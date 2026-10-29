const features =
  "knowledge|files|collections|assistants|conversations|members|models|quota|operations|resources|audit|overview";
const shortPattern = new RegExp(
  `^/([a-z0-9]+(?:[-_][a-z0-9]+)*)/(${features})(/.*)?$`,
);
const reserved = new Set([
  "workspaces",
  "providers",
  "modelops",
  "dashboard",
  "settings",
  "users",
  "roles",
  "permissions",
  "sign-in",
  "access-denied",
]);

export function parseWorkspaceLink(pathname: string) {
  const match = shortPattern.exec(pathname);
  if (!match || reserved.has(match[1])) return undefined;
  const [, code, feature, tail = ""] = match;
  if (feature === "files" && !/^\/[^/]+(?:\/ocr)?$/.test(tail))
    return undefined;
  return {
    code,
    feature,
    tail,
    sourceId: feature === "files" ? tail.split("/")[1] : undefined,
  };
}

export function publicWorkspacePath(pathname: string, code: string) {
  if (reserved.has(code)) return undefined;
  const match = /^\/workspaces\/[^/]+(?:\/(.*))?$/.exec(pathname);
  if (!match || pathname.startsWith("/workspaces/choose/")) return undefined;
  const suffix = (match[1] || "overview").replace(
    /^collections\/[^/]+\/sources\/([^/]+)(\/ocr)?$/,
    "files/$1$2",
  );
  const path = `/${code}/${suffix}`;
  return parseWorkspaceLink(path) ? path : undefined;
}

export function internalWorkspacePath(
  link: NonNullable<ReturnType<typeof parseWorkspaceLink>>,
  scope: { workspace_id: string; collection_id: string | null },
) {
  const root = `/workspaces/${encodeURIComponent(scope.workspace_id)}`;
  if (link.feature === "files") {
    if (!scope.collection_id)
      throw new Error("Không tìm thấy kho chứa tài liệu.");
    return `${root}/collections/${encodeURIComponent(scope.collection_id)}/sources${link.tail}`;
  }
  return link.feature === "overview"
    ? root
    : `${root}/${link.feature}${link.tail}`;
}
