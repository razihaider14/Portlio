/**
 * The three HTTP status codes the backend's GitHub-facing endpoints
 * (/github/{username}, /analyze/{username}, /skills/{username}) actually
 * produce — see backend/app/main.py's _handle_github_exceptions():
 *
 *   404 -> GitHubUserNotFoundError ("GitHub user not found.")
 *   429 -> GitHubRateLimitError ("GitHub API rate limit exceeded.")
 *   503 -> GitHubAPIError ("GitHub service is temporarily unavailable.")
 *
 * Any other status is unexpected and treated as a generic API error by
 * ApiError below (status is `number`, not restricted to this union, so a
 * genuinely unexpected code doesn't fail to construct, it's just not one
 * of the codes callers have a specific branch for).
 */
export type KnownApiErrorStatus = 404 | 429 | 503;

/**
 * Thrown by src/lib/api/client.ts for both HTTP error responses and
 * network-level failures (fetch throwing, e.g. offline/DNS/CORS), so every
 * caller can catch one error type instead of two.
 *
 * - HTTP error response: `status` is the real HTTP status code (e.g. 404),
 *   `isNetworkError` is false.
 * - Network failure (no response at all): `status` is 0 (never a real HTTP
 *   status), `isNetworkError` is true. This distinction is what
 *   src/lib/query/hooks.ts's retry policy is keyed on: network failures
 *   and 503s should retry, 404 should never retry, 429 should surface
 *   immediately.
 */
export class ApiError extends Error {
  readonly status: number;
  readonly isNetworkError: boolean;

  constructor(
    message: string,
    options: { status: number; isNetworkError?: boolean },
  ) {
    super(message);
    this.name = "ApiError";
    this.status = options.status;
    this.isNetworkError = options.isNetworkError ?? false;

    // Restores `instanceof ApiError` when compiled targets/tooling that
    // break native Error subclassing are in play (older TS/JS targets).
    Object.setPrototypeOf(this, ApiError.prototype);
  }

  get isNotFound(): boolean {
    return this.status === 404;
  }

  get isRateLimited(): boolean {
    return this.status === 429;
  }

  get isServiceUnavailable(): boolean {
    return this.status === 503;
  }

  /** True for errors it's reasonable to retry: network failures and 503s. */
  get isRetryable(): boolean {
    return this.isNetworkError || this.isServiceUnavailable;
  }
}
