"use client";

import * as React from "react";
import { QueryClientProvider } from "@tanstack/react-query";
import { ReactQueryDevtools } from "@tanstack/react-query-devtools";
import { createQueryClient } from "@/lib/query/queryClient";

/**
 * One QueryClient per browser session, created lazily inside useState so it
 * survives re-renders but isn't shared across requests on the server (which
 * would leak data between users). This is the standard Next.js App Router
 * pattern for TanStack Query.
 *
 * The actual staleTime/retry policy lives in src/lib/query/queryClient.ts
 * (createQueryClient), not here, so it's the single source of truth shared
 * with tests and any future non-React callers.
 */
export function QueryProvider({ children }: { children: React.ReactNode }) {
  const [queryClient] = React.useState(() => createQueryClient());

  return (
    <QueryClientProvider client={queryClient}>
      {children}
      {process.env.NODE_ENV === "development" ? (
        <ReactQueryDevtools initialIsOpen={false} />
      ) : null}
    </QueryClientProvider>
  );
}
