import { QueryClient } from "@tanstack/react-query";
import { ApiError } from "@/lib/api/errors";

/**
 * A GitHub portfolio doesn't change minute to minute, so this avoids
 * refetching on every tab refocus/remount. Matches the architecture doc's
 * "API Integration Strategy" section.
 */
export const QUERY_STALE_TIME_MS = 5 * 60 * 1000;

/** Retry network/503 failures at most this many times before giving up. */
const MAX_RETRIES = 2;

/**
 * The retry policy required by Phase 1:
 * - Never retry 404 (a nonexistent GitHub user won't start existing on retry).
 * - Never retry 429, surface the rate limit immediately; retrying a rate
 *   limit only makes it worse.
 * - Do retry network failures and 503 (GitHub temporarily unavailable),
 *   up to MAX_RETRIES times.
 * - Anything that isn't an ApiError at all (a genuine bug, not an
 *   API-shaped failure) gets TanStack Query's ordinary default behavior:
 *   retried a couple of times, since we can't otherwise classify it.
 */
export function shouldRetryQuery(failureCount: number, error: unknown): boolean {
  if (failureCount >= MAX_RETRIES) {
    return false;
  }

  if (error instanceof ApiError) {
    if (error.isNotFound || error.isRateLimited) {
      return false;
    }
    return error.isRetryable;
  }

  return true;
}

/**
 * Creates a fresh QueryClient. Used both by QueryProvider (one per browser
 * session, per the Next.js App Router pattern, see
 * src/components/providers/query-provider.tsx) and directly by tests that
 * need a real QueryClient without rendering the full provider tree.
 */
export function createQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: QUERY_STALE_TIME_MS,
        retry: shouldRetryQuery,
        refetchOnWindowFocus: false,
      },
    },
  });
}
