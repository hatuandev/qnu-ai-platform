import { createContext, type ReactNode, useContext, useState } from "react";
import { useV1Auth } from "@/app/auth/v1";
import type { CompilationRunResponse } from "./compilation-types";

type CompilationActivity = {
  runs: CompilationRunResponse[];
  isExpanded: boolean;
  setExpanded: (expanded: boolean) => void;
  track: (run: CompilationRunResponse) => void;
  dismiss: (runId: string) => void;
  dismissAll: () => void;
};

const ActivityContext = createContext<CompilationActivity | null>(null);

export function useCompilationActivity() {
  return useContext(ActivityContext);
}

// Keep monitoring across route changes, but never across authenticated sessions.
export function CompilationActivityProvider({
  children,
}: {
  children: ReactNode;
}) {
  const { sessionId, actor, isAuthenticated } = useV1Auth();
  return (
    <SessionActivity
      key={`${sessionId}:${actor?.actor_id ?? "anonymous"}:${isAuthenticated}`}
    >
      {children}
    </SessionActivity>
  );
}

function SessionActivity({ children }: { children: ReactNode }) {
  const [runs, setRuns] = useState<CompilationRunResponse[]>([]);
  const [isExpanded, setExpanded] = useState(true);
  return (
    <ActivityContext.Provider
      value={{
        runs,
        isExpanded,
        setExpanded,
        track: (run) => {
          setRuns((current) => [
            run,
            ...current.filter((item) => item.id !== run.id),
          ]);
          setExpanded(true);
        },
        dismiss: (runId) => {
          setRuns((current) => current.filter((item) => item.id !== runId));
        },
        dismissAll: () => setRuns([]),
      }}
    >
      {children}
    </ActivityContext.Provider>
  );
}
