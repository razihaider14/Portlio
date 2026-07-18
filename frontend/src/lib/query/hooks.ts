import { useQuery, type UseQueryResult } from "@tanstack/react-query";
import { getAnalysis, getRepos, getSkills } from "@/lib/api/endpoints";
import type { AnalyzeResponse, GithubReposResponse } from "@/types/repository";
import type { PortfolioSkillReport } from "@/types/skill";

/**
 * Query key factories, kept alongside the hooks so key shape and hook
 * behavior can never drift apart. `includeContent` is part of the key (not
 * just an argument passed to the fetcher) so that a default-mode result and
 * a "Deep scan" (include_content=true) result are cached side by side
 * instead of overwriting each other, see the architecture doc's API
 * Integration Strategy.
 */
export const queryKeys = {
  skills: (username: string, includeContent: boolean) =>
    ["skills", username, includeContent] as const,
  analysis: (username: string, includeContent: boolean) =>
    ["analysis", username, includeContent] as const,
  repos: (username: string) => ["repos", username] as const,
};

/**
 * GET /skills/{username} : the portfolio-level skill report.
 *
 * `username` may be undefined (e.g. before a form is submitted); the query
 * is simply disabled until it's a non-empty string, rather than making
 * every caller guard against calling this with `undefined`.
 */
export function useSkills(
  username: string | undefined,
  includeContent = false,
): UseQueryResult<PortfolioSkillReport> {
  return useQuery({
    queryKey: queryKeys.skills(username ?? "", includeContent),
    queryFn: () => getSkills(username as string, includeContent),
    enabled: Boolean(username),
  });
}

/**
 * GET /analyze/{username} : full analysis, including per-repository
 * detail. Prefer useSkills for the Skills Dashboard (Phase 2), which only
 * needs the portfolio report; use this for the Repository Explorer
 * (Phase 3), which needs each repository's own technologies/metadata/skills.
 */
export function useAnalysis(
  username: string | undefined,
  includeContent = false,
): UseQueryResult<AnalyzeResponse> {
  return useQuery({
    queryKey: queryKeys.analysis(username ?? "", includeContent),
    queryFn: () => getAnalysis(username as string, includeContent),
    enabled: Boolean(username),
  });
}

/**
 * GET /github/{username} : the raw, minimal repository listing. No
 * `includeContent` parameter: the backend endpoint doesn't accept one.
 */
export function useRepos(
  username: string | undefined,
): UseQueryResult<GithubReposResponse> {
  return useQuery({
    queryKey: queryKeys.repos(username ?? ""),
    queryFn: () => getRepos(username as string),
    enabled: Boolean(username),
  });
}
