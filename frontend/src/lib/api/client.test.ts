import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { apiGet } from "@/lib/api/client";
import { ApiError } from "@/lib/api/errors";

function jsonResponse(body: unknown, init?: ResponseInit): Response {
  return new Response(JSON.stringify(body), {
    status: 200,
    headers: { "Content-Type": "application/json" },
    ...init,
  });
}

describe("apiGet", () => {
  const originalBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL;
  let fetchSpy: ReturnType<typeof vi.spyOn>;

  beforeEach(() => {
    process.env.NEXT_PUBLIC_API_BASE_URL = "http://localhost:8000";
    fetchSpy = vi.spyOn(global, "fetch");
  });

  afterEach(() => {
    process.env.NEXT_PUBLIC_API_BASE_URL = originalBaseUrl;
    fetchSpy.mockRestore();
  });

  it("throws a clear error if NEXT_PUBLIC_API_BASE_URL is unset", async () => {
    delete process.env.NEXT_PUBLIC_API_BASE_URL;
    await expect(apiGet("/skills/octocat")).rejects.toThrow(
      /NEXT_PUBLIC_API_BASE_URL is not set/,
    );
  });

  it("builds the request URL from the base URL and path", async () => {
    fetchSpy.mockResolvedValue(jsonResponse({ ok: true }));

    await apiGet("/skills/octocat");

    expect(fetchSpy).toHaveBeenCalledWith(
      "http://localhost:8000/skills/octocat",
      expect.objectContaining({ method: "GET" }),
    );
  });

  it("strips a trailing slash from the base URL before joining the path", async () => {
    process.env.NEXT_PUBLIC_API_BASE_URL = "http://localhost:8000/";
    fetchSpy.mockResolvedValue(jsonResponse({ ok: true }));

    await apiGet("/skills/octocat");

    expect(fetchSpy).toHaveBeenCalledWith(
      "http://localhost:8000/skills/octocat",
      expect.anything(),
    );
  });

  it("serializes search params, including booleans, and omits undefined values", async () => {
    fetchSpy.mockResolvedValue(jsonResponse({ ok: true }));

    await apiGet("/skills/octocat", {
      include_content: true,
      unused: undefined,
    });

    const calledUrl = new URL(fetchSpy.mock.calls[0][0] as string);
    expect(calledUrl.searchParams.get("include_content")).toBe("true");
    expect(calledUrl.searchParams.has("unused")).toBe(false);
  });

  it("returns the parsed JSON body on a 2xx response", async () => {
    fetchSpy.mockResolvedValue(jsonResponse({ repository_count: 3 }));

    const result = await apiGet<{ repository_count: number }>(
      "/skills/octocat",
    );

    expect(result).toEqual({ repository_count: 3 });
  });

  it("throws ApiError with status 404 and the backend's detail message", async () => {
    fetchSpy.mockResolvedValue(
      jsonResponse(
        { detail: "GitHub user not found." },
        { status: 404 },
      ),
    );

    const error = await apiGet("/skills/nonexistent-user").catch((e) => e);

    expect(error).toBeInstanceOf(ApiError);
    expect((error as ApiError).status).toBe(404);
    expect((error as ApiError).isNotFound).toBe(true);
    expect((error as ApiError).message).toBe("GitHub user not found.");
  });

  it("throws ApiError with status 429 for a rate-limit response", async () => {
    fetchSpy.mockResolvedValue(
      jsonResponse(
        { detail: "GitHub API rate limit exceeded." },
        { status: 429 },
      ),
    );

    const error = await apiGet("/skills/octocat").catch((e) => e);

    expect(error).toBeInstanceOf(ApiError);
    expect((error as ApiError).isRateLimited).toBe(true);
  });

  it("throws ApiError with status 503 for a service-unavailable response", async () => {
    fetchSpy.mockResolvedValue(
      jsonResponse(
        { detail: "GitHub service is temporarily unavailable." },
        { status: 503 },
      ),
    );

    const error = await apiGet("/skills/octocat").catch((e) => e);

    expect(error).toBeInstanceOf(ApiError);
    expect((error as ApiError).isServiceUnavailable).toBe(true);
  });

  it("falls back to a generic message when the error body isn't the expected shape", async () => {
    fetchSpy.mockResolvedValue(
      new Response("not json", { status: 500 }),
    );

    const error = await apiGet("/skills/octocat").catch((e) => e);

    expect(error).toBeInstanceOf(ApiError);
    expect((error as ApiError).status).toBe(500);
    expect((error as ApiError).message).toMatch(/status 500/);
  });

  it("normalizes a network-level failure (fetch throwing) into a non-network-error-status ApiError", async () => {
    fetchSpy.mockRejectedValue(new TypeError("Failed to fetch"));

    const error = await apiGet("/skills/octocat").catch((e) => e);

    expect(error).toBeInstanceOf(ApiError);
    expect((error as ApiError).isNetworkError).toBe(true);
    expect((error as ApiError).status).toBe(0);
    expect((error as ApiError).isRetryable).toBe(true);
  });
});
