import * as React from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ApiError } from "@/lib/api/errors";
import { shouldRetryQuery } from "@/lib/query/queryClient";
import {
  sampleAnalyzeResponse,
  sampleGithubReposResponse,
  sampleSkillsResponse,
} from "@/lib/api/__fixtures__/sampleResponses";

const getSkillsMock = vi.fn();
const getAnalysisMock = vi.fn();
const getReposMock = vi.fn();

vi.mock("@/lib/api/endpoints", () => ({
  getSkills: (...args: unknown[]) => getSkillsMock(...args),
  getAnalysis: (...args: unknown[]) => getAnalysisMock(...args),
  getRepos: (...args: unknown[]) => getReposMock(...args),
}));

const { useAnalysis, useRepos, useSkills } = await import(
  "@/lib/query/hooks"
);

/**
 * A real QueryClient using the app's actual retry policy (shouldRetryQuery),
 * but with retryDelay/gcTime zeroed out so retry tests don't sit through
 * real exponential backoff. This is deliberately NOT createQueryClient()
 * itself, so these tests exercise the same policy without inheriting its
 * production timing.
 */
function createTestQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: {
        retry: shouldRetryQuery,
        retryDelay: 0,
        gcTime: 0,
      },
    },
  });
}

function wrapper({ children }: { children: React.ReactNode }) {
  const client = createTestQueryClient();
  return (
    <QueryClientProvider client={client}>{children}</QueryClientProvider>
  );
}

beforeEach(() => {
  getSkillsMock.mockReset();
  getAnalysisMock.mockReset();
  getReposMock.mockReset();
});

describe("useSkills", () => {
  it("does not call getSkills when username is undefined", () => {
    renderHook(() => useSkills(undefined), { wrapper });
    expect(getSkillsMock).not.toHaveBeenCalled();
  });

  it("fetches and returns data for a given username", async () => {
    getSkillsMock.mockResolvedValue(sampleSkillsResponse);

    const { result } = renderHook(() => useSkills("octocat"), { wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toEqual(sampleSkillsResponse);
    expect(getSkillsMock).toHaveBeenCalledWith("octocat", false);
  });

  it("propagates includeContent=true through to getSkills", async () => {
    getSkillsMock.mockResolvedValue(sampleSkillsResponse);

    const { result } = renderHook(() => useSkills("octocat", true), {
      wrapper,
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(getSkillsMock).toHaveBeenCalledWith("octocat", true);
  });

  it("surfaces a 404 as an error without retrying", async () => {
    const notFound = new ApiError("GitHub user not found.", { status: 404 });
    getSkillsMock.mockRejectedValue(notFound);

    const { result } = renderHook(() => useSkills("nonexistent-user"), {
      wrapper,
    });

    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(result.current.error).toBe(notFound);
    expect(getSkillsMock).toHaveBeenCalledTimes(1);
  });

  it("surfaces a 429 as an error immediately, without retrying", async () => {
    const rateLimited = new ApiError("GitHub API rate limit exceeded.", {
      status: 429,
    });
    getSkillsMock.mockRejectedValue(rateLimited);

    const { result } = renderHook(() => useSkills("octocat"), { wrapper });

    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(result.current.error).toBe(rateLimited);
    expect(getSkillsMock).toHaveBeenCalledTimes(1);
  });

  it("retries a 503 before eventually failing", async () => {
    const unavailable = new ApiError(
      "GitHub service is temporarily unavailable.",
      { status: 503 },
    );
    getSkillsMock.mockRejectedValue(unavailable);

    const { result } = renderHook(() => useSkills("octocat"), { wrapper });

    await waitFor(() => expect(result.current.isError).toBe(true));
    // MAX_RETRIES is 2 in src/lib/query/queryClient.ts, so 1 initial
    // attempt + 2 retries = 3 total calls.
    expect(getSkillsMock).toHaveBeenCalledTimes(3);
  });
});

describe("useAnalysis", () => {
  it("does not call getAnalysis when username is undefined", () => {
    renderHook(() => useAnalysis(undefined), { wrapper });
    expect(getAnalysisMock).not.toHaveBeenCalled();
  });

  it("fetches and returns data, defaulting includeContent to false", async () => {
    getAnalysisMock.mockResolvedValue(sampleAnalyzeResponse);

    const { result } = renderHook(() => useAnalysis("octocat"), { wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toEqual(sampleAnalyzeResponse);
    expect(getAnalysisMock).toHaveBeenCalledWith("octocat", false);
  });

  it("propagates includeContent=true through to getAnalysis", async () => {
    getAnalysisMock.mockResolvedValue(sampleAnalyzeResponse);

    renderHook(() => useAnalysis("octocat", true), { wrapper });

    await waitFor(() =>
      expect(getAnalysisMock).toHaveBeenCalledWith("octocat", true),
    );
  });
});

describe("useRepos", () => {
  it("does not call getRepos when username is undefined", () => {
    renderHook(() => useRepos(undefined), { wrapper });
    expect(getReposMock).not.toHaveBeenCalled();
  });

  it("fetches and returns data for a given username", async () => {
    getReposMock.mockResolvedValue(sampleGithubReposResponse);

    const { result } = renderHook(() => useRepos("octocat"), { wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toEqual(sampleGithubReposResponse);
    expect(getReposMock).toHaveBeenCalledWith("octocat");
  });
});
