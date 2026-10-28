import { useRouterState } from "@tanstack/react-router";
import {
  createContext,
  type ReactNode,
  useContext,
  useEffect,
  useState,
} from "react";
import { useV1Auth } from "@/app/auth/v1";
import { type FeatureScope, routeFeatureScope } from "./workspace-features";

const FeatureScopeContext = createContext<FeatureScope | undefined>(undefined);

/** The shell owns selection so closing the mobile sheet cannot discard it. */
export function FeatureScopeProvider({ children }: { children: ReactNode }) {
  const scope = useRouteFeatureScope();
  return (
    <FeatureScopeContext.Provider value={scope}>
      {children}
    </FeatureScopeContext.Provider>
  );
}

export function useFeatureScope(): FeatureScope {
  const scope = useContext(FeatureScopeContext);
  if (!scope) throw new Error("Feature navigation needs FeatureScopeProvider");
  return scope;
}

function useRouteFeatureScope(): FeatureScope {
  const { sessionId, isAuthenticated } = useV1Auth();
  const location = useRouterState({ select: (state) => state.location });
  const current = routeFeatureScope(location.pathname, location.search);
  const [last, setLast] = useState<{
    sessionId: number;
    scope: FeatureScope;
  }>();
  const previous = last?.sessionId === sessionId ? last.scope : {};
  const workspaceId = current?.workspaceId ?? previous.workspaceId;
  const collectionId = current
    ? (current.collectionId ??
      (!location.pathname.startsWith("/workspaces/choose/") &&
      current.workspaceId === previous.workspaceId
        ? previous.collectionId
        : undefined))
    : previous.collectionId;
  const selectedWorkspace =
    current !== undefined ? current.workspaceId : workspaceId;
  useEffect(() => {
    setLast(
      isAuthenticated
        ? {
            sessionId,
            scope: { workspaceId: selectedWorkspace, collectionId },
          }
        : undefined,
    );
  }, [sessionId, isAuthenticated, selectedWorkspace, collectionId]);
  if (!isAuthenticated) return {};
  return { workspaceId: selectedWorkspace, collectionId };
}
