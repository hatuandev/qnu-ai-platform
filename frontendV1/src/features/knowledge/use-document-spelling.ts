import { useEffect, useRef, useState } from "react";
import {
  checkWholeDocument,
  type DetectCall,
  type DocumentSpellingReport,
} from "./ocr-spelling-batch";
import type { ReviewDocument } from "./ocr-types";

export function useDocumentSpelling(
  scope: string,
  isCurrent: () => boolean,
  detect: DetectCall,
) {
  const [report, setReport] = useState<DocumentSpellingReport | null>(null);
  const [reportScope, setReportScope] = useState(scope);
  const [running, setRunning] = useState(false);
  const [stopping, setStopping] = useState(false);
  const liveScope = useRef(scope);
  liveScope.current = scope;
  const active = useRef(false);
  const stopRequested = useRef(false);
  const mounted = useRef(true);
  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
    };
  }, []);
  useEffect(() => {
    if (!running) return;
    const warn = (event: BeforeUnloadEvent) => {
      event.preventDefault();
      event.returnValue = "";
    };
    window.addEventListener("beforeunload", warn);
    return () => window.removeEventListener("beforeunload", warn);
  }, [running]);
  const start = async (
    doc: ReviewDocument,
    key: string,
    providerId: string | null,
    sourceVersion: number | null,
  ) => {
    if (active.current || !mounted.current || !isCurrent()) return;
    active.current = true;
    setReportScope(scope);
    setReport(null);
    stopRequested.current = false;
    setRunning(true);
    setStopping(false);
    const valid = () =>
      mounted.current && isCurrent() && liveScope.current === scope;
    try {
      const result = await checkWholeDocument({
        doc,
        key,
        providerId,
        sourceVersion,
        detect,
        shouldStop: () => stopRequested.current || !valid(),
        onUpdate: (r) => {
          if (valid()) setReport(r);
        },
      });
      return valid() ? result : undefined;
    } finally {
      active.current = false;
      if (mounted.current && isCurrent()) setRunning(false);
    }
  };
  return {
    report: reportScope === scope ? report : null,
    running,
    stopping,
    start,
    stop: () => {
      stopRequested.current = true;
      setStopping(true);
    },
  };
}
