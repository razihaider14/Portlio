import { apiGet } from "@/lib/api/client";
import type {
  AnalyzeResponse,
  GithubReposResponse,
} from "@/types/repository";
import type { PortfolioSkillReport } from "@/types/skill";

/**
 * GET /skills/{username} : just the portfolio-level skill report (skills,
 * strengths, weaknesses, recommendations), without per-repository detail.
 * See backend/app/main.py's get_user_skills docstring for the authoritative
 * response shape this mirrors.
 *
 * @param includeContent Passed through as `include_content`. Defaults to
 *   false: opting in downloads manifest/README content for richer
 *   detection (see the architecture doc's API Integration Strategy on why
 *   this isn't the default) at the cost of more GitHub API requests.
 */
export function getSkills(
  username: string,
  includeContent = false,
): Promise<PortfolioSkillReport> {
  return apiGet<PortfolioSkillReport>(`/skills/${encodeURIComponent(username)}`, {
    include_content: includeContent,
  });
}

/**
 * GET /analyze/{username} : full analysis: every repository's own
 * technologies/metadata/skills, plus the portfolio-level report. See
 * backend/app/analyzer/analyzer.py's analyze_user_repositories docstring
 * for the authoritative response shape this mirrors.
 */
export function getAnalysis(
  username: string,
  includeContent = false,
): Promise<AnalyzeResponse> {
  return apiGet<AnalyzeResponse>(`/analyze/${encodeURIComponent(username)}`, {
    include_content: includeContent,
  });
}

/**
 * GET /github/{username} : the raw, minimal repository listing (no
 * technology detection or metadata analysis), sorted by stars descending
 * by the backend. See backend/app/main.py's get_github_user_repos.
 *
 * Unlike getSkills/getAnalysis, this endpoint has no `include_content`
 * parameter on the backend, so this function takes none either.
 */
export function getRepos(username: string): Promise<GithubReposResponse> {
  return apiGet<GithubReposResponse>(`/github/${encodeURIComponent(username)}`);
}
