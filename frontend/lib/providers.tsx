"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useState } from "react";
import { AuthProvider } from "./auth";
import { ApiError } from "./api";

export function Providers({ children }: { children: React.ReactNode }) {
  const [client] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 60_000, 
            refetchOnWindowFocus: false, 
            refetchOnReconnect: false, // Prevents mass refetches when browser wakes from sleep
            retry: (failureCount, error) => {
              if (error instanceof ApiError && (error.status === 401 || error.status === 429)) {
                return false;
              }
              return failureCount < 1;
            },
          },
        },
      }),
  );
  return (
    <QueryClientProvider client={client}>
      <AuthProvider>{children}</AuthProvider>
    </QueryClientProvider>
  );
}