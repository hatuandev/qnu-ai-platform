import { useEffect, useState } from "react";

export function usePlatformShortcut() {
  const [isMac, setIsMac] = useState(false);

  useEffect(() => {
    setIsMac(/Mac|iPhone|iPad|iPod/i.test(navigator.platform));
  }, []);

  return isMac ? "⌘ K" : "Ctrl K";
}
