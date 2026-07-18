import { ApiError } from "@/lib/api/errors";

/**
 * Base URL of the SkillForge FastAPI backend, e.g. "http://localhost:8000"
 * in dev. Must be NEXT_PUBLIC_-prefixed since query hooks call this from
 * the browser (see .env.example).
 *
 * Read lazily inside apiFetch (not at module scope) so tests can stub
 * process.env per-test without needing to reset a module-level constant.
 */
function getApiBaseUrl(): string {
  const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL;
  if (!baseUrl) {
    throw new Error(
      "NEXT_PUBLIC_API_BASE_URL is not set. Copy .env.example to .env.local " +
        "and point it at a running SkillForge backend.",
    );
  }
  // Normalize away a trailing slash so callers can write paths as "/skills/x"
  // without producing a double slash.
  return baseUrl.replace(/\/+$/, "");
}

/**
 * Attempts to extract a useful message from a non-2xx JSON error body.
 * FastAPI's default error shape is `{"detail": "..."}` (see
 * backend/app/main.py's HTTPException calls), this also tolerates a
 * non-JSON or differently-shaped body instead of throwing a second error
 * while already handling the first one.
 */
async function extractErrorMessage(
  response: Response,
  fallback: string,
): Promise<string> {
  try {
    const body: unknown = await response.json();
    if (
      body &&
      typeof body === "object" &&
      "detail" in body &&
      typeof (body as { detail: unknown }).detail === "string"
    ) {
      return (body as { detail: string }).detail;
    }
  } catch {
    // Body wasn't JSON (or was empty) — fall through to the fallback.
  }
  return fallback;
}

/**
 * GET a path from the SkillForge backend and parse the JSON response.
 * Every endpoint this app calls is a read, so this intentionally doesn't
 * support other HTTP methods, see the architecture doc's API Integration
 * Strategy and the backend's CORS setup, which only allows GET.
 *
 * Always throws ApiError on failure, never the raw fetch/DOMException or a
 * bare SyntaxError from JSON parsing, so every caller only needs to catch
 * one error type. See src/lib/api/errors.ts for how callers should branch
 * on the result (isNotFound / isRateLimited / isServiceUnavailable /
 * isRetryable).
 */
export async function apiGet<T>(
  path: string,
  searchParams?: Record<string, string | boolean | number | undefined>,
): Promise<T> {
  const url = new URL(`${getApiBaseUrl()}${path}`);
  if (searchParams) {
    for (const [key, value] of Object.entries(searchParams)) {
      if (value !== undefined) {
        url.searchParams.set(key, String(value));
      }
    }
  }

  let response: Response;
  try {
    response = await fetch(url.toString(), {
      method: "GET",
      headers: { Accept: "application/json" },
    });
  } catch {
    // fetch() throws for network-level failures: offline, DNS failure, the
    // backend not running, CORS rejection, etc. There is no HTTP status in
    // this case at all, so `status: 0` (never a real HTTP status) marks it
    // as a network error rather than any specific server response.
    throw new ApiError(
      "Could not reach the SkillForge API. Check your connection and that " +
        "the backend is running.",
      { status: 0, isNetworkError: true },
    );
  }

  if (!response.ok) {
    const message = await extractErrorMessage(
      response,
      `SkillForge API request failed with status ${response.status}.`,
    );
    throw new ApiError(message, { status: response.status });
  }

  return (await response.json()) as T;
}
