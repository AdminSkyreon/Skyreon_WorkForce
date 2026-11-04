"use client";

import { useIsFetching } from "@tanstack/react-query";
import { useEffect, useState } from "react";

// Global custom event listeners so route clicks trigger the bar at 0ms
let navLoadingListeners: Array<(loading: boolean) => void> = [];

export function setNavigationLoading(loading: boolean) {
  navLoadingListeners.forEach((fn) => fn(loading));
}

export function GlobalLoadingIndicator() {
  const isFetching = useIsFetching();
  const [navLoading, setNavLoading] = useState(false);

  useEffect(() => {
    const handler = (state: boolean) => setNavLoading(state);
    navLoadingListeners.push(handler);
    return () => {
      navLoadingListeners = navLoadingListeners.filter((fn) => fn !== handler);
    };
  }, []);

  const isActive = navLoading || isFetching > 0;

  if (!isActive) return null;

  return (
    <div className="fixed top-0 left-0 right-0 z-[99999] h-1 overflow-hidden bg-forest/15 pointer-events-none">
      <div className="h-full w-full bg-forest animate-loading-bar origin-left shadow-[0_0_10px_#0060a8]" />
    </div>
  );
}
