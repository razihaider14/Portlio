import type { RepositoryMetadata } from "@/types/metadata";
import type { SkillProfile, PortfolioSkillReport } from "@/types/skill";

/**
 * Mirrors app.detector.models.Entry (backend/app/detector/models.py), as
 * returned by app.github.client.get_repository_tree() and surfaced
 * verbatim as `repositories[].contents` in GET /analyze/{username}. `size`
 * is only present on file entries returned by GitHub's tree API, not
 * every entry, hence optional.
 */
export interface RepositoryTreeEntry {
  path: string;
  name: string;
  type: "file" | "dir";
  size?: number;
}

/**
 * One item of GET /github/{username}'s `repositories` array (see
 * backend/app/main.py's get_github_user_repos). This is the raw, minimal
 * repo listing, NOT the richer per-repository shape GET /analyze/{username}
 * returns (that's RepositoryDetail below). Sorted by `stars` descending by
 * the backend.
 */
export interface RepositorySummary {
  name: string;
  description: string | null;
  language: string | null;
  stars: number;
  forks: number;
  url: string;
}

/** GET /github/{username}'s full response shape. */
export interface GithubReposResponse {
  username: string;
  repository_count: number;
  repositories: RepositorySummary[];
}

/**
 * One item of GET /analyze/{username}'s `repositories` array (see
 * backend/app/analyzer/analyzer.py's analyze_user_repositories docstring).
 * Every field is a derived, JSON-safe result, the raw GitHub repo object
 * and any downloaded file content are internal analysis inputs and are
 * never included here.
 *
 * `skills` is this repository's own technologies scored in isolation, as
 * if it were the user's entire portfolio, NOT a slice of the portfolio-
 * level `skills` in PortfolioSkillReport. Two repositories can each show
 * "Python" at a high tier here even if, portfolio-wide, breadth across
 * many repos would push the aggregate tier differently.
 */
export interface RepositoryDetail {
  name: string;
  language: string | null;
  contents: RepositoryTreeEntry[];
  technologies: string[];
  metadata: RepositoryMetadata;
  skills: SkillProfile[];
}

/** GET /analyze/{username}'s full response shape. */
export interface AnalyzeResponse {
  username: string;
  repository_count: number;
  repositories: RepositoryDetail[];
  portfolio: PortfolioSkillReport;
}
