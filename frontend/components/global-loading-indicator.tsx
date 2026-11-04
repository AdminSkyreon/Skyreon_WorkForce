"use client";

import { useIsFetching } from "@tanstack/react-query";
import { useEffect, useState } from "react";

export function GlobalLoadingIndicator() {
  const isFetching = useIsFetching();
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    let timeout: NodeJS.Timeout;
    if (isFetching > 0) {
      // Reveal immediately if query takes more than 50ms
      timeout = setTimeout(() => setVisible(true), 50);
    } else {
      setVisible(false);
    }
    return () => clearTimeout(timeout);
  }, [isFetching]);

  if (!visible) return null;

  return (
    <div className="fixed top-0 left-0 right-0 z-[99999] h-1 overflow-hidden bg-forest/10 pointer-events-none">
      <div className="h-full w-full bg-forest animate-loading-bar origin-left shadow-[0_0_8px_#0060a8]" />
    </div>
  );
}
