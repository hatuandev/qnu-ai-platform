import { useRouterState } from "@tanstack/react-router";
import {
  createContext,
  type ReactNode,
  useCallback,
  useContext,
  useEffect,
  useState,
} from "react";
import { useV1Auth } from "@/app/auth/v1";
import { useWorkspacesQuery } from "@/features/workspaces/queries";
import { type FeatureScope, routeFeatureScope } from "./workspace-features";

type FeatureScopeContextValue = FeatureScope & {
  setWorkspaceId?: (workspaceId: string) => void;
};

const FeatureScopeContext = createContext<FeatureScopeContextValue | undefined>(
  undefined,
);

/** The shell owns selection so closing the mobile sheet cannot discard it. */
export function FeatureScopeProvider({ children }: { children: ReactNode }) {
  const scope = useRouteFeatureScope();
  return (
    <FeatureScopeContext.Provider value={scope}>
      {children}
    </FeatureScopeContext.Provider>
  );
}

export function useFeatureScope(): FeatureScopeContextValue {
  const scope = useContext(FeatureScopeContext);
  if (!scope) throw new Error("Feature navigation needs FeatureScopeProvider");
  return scope;
}

function useRouteFeatureScope(): FeatureScopeContextValue {
  const { sessionId, isAuthenticated } = useV1Auth();
  const location = useRouterState({ select: (state) => state.location });
  const current = routeFeatureScope(location.pathname, location.search);
  const workspacesQuery = useWorkspacesQuery(
    { page: 1, pageSize: 50 },
    isAuthenticated,
  );
  const firstAvailableWorkspaceId = workspacesQuery.data?.items?.[0]?.id;
  const [last, setLast] = useState<{
    sessionId: number;
    scope: FeatureScope;
  }>();
  const previous = last?.sessionId === sessionId ? last.scope : {};
  const isChooser = location.pathname.startsWith("/workspaces/choose/");
  const selectedWorkspace = isChooser
    ? current?.workspaceId
    : (current?.workspaceId ??
      previous.workspaceId ??
      firstAvailableWorkspaceId);
  const collectionId = current
    ? (current.collectionId ??
      (!isChooser && current.workspaceId === previous.workspaceId
        ? previous.collectionId
        : undefined))
    : previous.collectionId;

  const setWorkspaceId = useCallback(
    (nextWorkspaceId: string) => {
      if (!isAuthenticated) return;
      setLast((prev) => ({
        sessionId,
        scope: {
          workspaceId: nextWorkspaceId,
          collectionId:
            prev?.scope.workspaceId === nextWorkspaceId
              ? prev.scope.collectionId
              : undefined,
        },
      }));
    },
    [isAuthenticated, sessionId],
  );

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
  if (!isAuthenticated) return { setWorkspaceId };
  return { workspaceId: selectedWorkspace, collectionId, setWorkspaceId };
}
