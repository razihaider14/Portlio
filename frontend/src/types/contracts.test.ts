import { describe, expect, it } from "vitest";
import type { SkillProfile, PortfolioSkillReport } from "@/types/skill";
import type { PortfolioWeakness, WeaknessKind } from "@/types/weakness";
import type { SkillRecommendation } from "@/types/recommendation";
import type {
  AnalyzeResponse,
  GithubReposResponse,
  RepositoryDetail,
  RepositorySummary,
} from "@/types/repository";
import type { RepositoryMetadata } from "@/types/metadata";
import {
  sampleAnalyzeResponse,
  sampleGithubReposResponse,
  sampleSkill,
  sampleSkillsResponse,
  sampleWeakness,
  sampleRecommendation,
} from "@/lib/api/__fixtures__/sampleResponses";

/**
 * These tests exist to catch a class of bug the TypeScript compiler alone
 * won't: a fixture (or, transitively, real API response) that has extra
 * keys beyond the interface, or a field whose runtime value silently
 * doesn't match one of a literal union. `tsc --noEmit` catches missing
 * required keys and wrong types on a *typed* literal, but won't flag
 * surplus keys on an object already inferred as that type, and can't check
 * a value that only exists at runtime (e.g. parsed JSON from a live
 * backend). This file is the "type correctness where possible" half of
 * that guarantee; the fixtures file itself (every export typed against
 * src/types/*) is the compile-time half.
 */

const SKILL_PROFILE_KEYS: (keyof SkillProfile)[] = [
  "name",
  "category",
  "repository_count",
  "repositories",
  "average_detector_confidence",
  "average_practice_score",
  "score",
  "max_score",
  "tier",
  "evidence",
  "is_composite",
];

const WEAKNESS_KEYS: (keyof PortfolioWeakness)[] = [
  "kind",
  "name",
  "category",
  "description",
  "evidence",
];

const RECOMMENDATION_KEYS: (keyof SkillRecommendation)[] = [
  "skill",
  "category",
  "reason",
  "based_on",
  "chain",
];

const PORTFOLIO_REPORT_KEYS: (keyof PortfolioSkillReport)[] = [
  "repository_count",
  "skills",
  "strengths",
  "weaknesses",
  "recommendations",
];

const METADATA_KEYS: (keyof RepositoryMetadata)[] = [
  "project_types",
  "hardware_platforms",
  "documentation",
  "has_tests",
  "has_ci_cd",
  "ci_providers",
  "has_docker",
  "has_docker_compose",
  "has_kubernetes_manifests",
  "package_managers",
  "build_systems",
  "license",
  "maturity",
  "size_metrics",
];

const REPOSITORY_DETAIL_KEYS: (keyof RepositoryDetail)[] = [
  "name",
  "language",
  "contents",
  "technologies",
  "metadata",
  "skills",
];

const REPOSITORY_SUMMARY_KEYS: (keyof RepositorySummary)[] = [
  "name",
  "description",
  "language",
  "stars",
  "forks",
  "url",
];

const ANALYZE_RESPONSE_KEYS: (keyof AnalyzeResponse)[] = [
  "username",
  "repository_count",
  "repositories",
  "portfolio",
];

const GITHUB_REPOS_RESPONSE_KEYS: (keyof GithubReposResponse)[] = [
  "username",
  "repository_count",
  "repositories",
];

const VALID_WEAKNESS_KINDS: WeaknessKind[] = [
  "shallow_skill",
  "limited_practice",
  "limited_breadth",
];

function sortedKeys(obj: object): string[] {
  return Object.keys(obj).sort();
}

describe("type contracts: exact key sets", () => {
  it("SkillProfile fixture has exactly the declared keys, no more, no less", () => {
    expect(sortedKeys(sampleSkill)).toEqual([...SKILL_PROFILE_KEYS].sort());
  });

  it("PortfolioWeakness fixture has exactly the declared keys", () => {
    expect(sortedKeys(sampleWeakness)).toEqual([...WEAKNESS_KEYS].sort());
  });

  it("SkillRecommendation fixture has exactly the declared keys", () => {
    expect(sortedKeys(sampleRecommendation)).toEqual(
      [...RECOMMENDATION_KEYS].sort(),
    );
  });

  it("PortfolioSkillReport (GET /skills/{username}) fixture has exactly the declared keys", () => {
    expect(sortedKeys(sampleSkillsResponse)).toEqual(
      [...PORTFOLIO_REPORT_KEYS].sort(),
    );
  });

  it("RepositoryMetadata fixture has exactly the declared keys", () => {
    const [repository] = sampleAnalyzeResponse.repositories;
    expect(sortedKeys(repository.metadata)).toEqual(
      [...METADATA_KEYS].sort(),
    );
  });

  it("RepositoryDetail fixture has exactly the declared keys", () => {
    const [repository] = sampleAnalyzeResponse.repositories;
    expect(sortedKeys(repository)).toEqual([...REPOSITORY_DETAIL_KEYS].sort());
  });

  it("RepositorySummary fixture has exactly the declared keys", () => {
    const [repository] = sampleGithubReposResponse.repositories;
    expect(sortedKeys(repository)).toEqual(
      [...REPOSITORY_SUMMARY_KEYS].sort(),
    );
  });

  it("AnalyzeResponse fixture has exactly the declared keys", () => {
    expect(sortedKeys(sampleAnalyzeResponse)).toEqual(
      [...ANALYZE_RESPONSE_KEYS].sort(),
    );
  });

  it("GithubReposResponse fixture has exactly the declared keys", () => {
    expect(sortedKeys(sampleGithubReposResponse)).toEqual(
      [...GITHUB_REPOS_RESPONSE_KEYS].sort(),
    );
  });
});

describe("type contracts: literal union values", () => {
  it("every WeaknessKind used in fixtures is one of the three valid kinds", () => {
    expect(VALID_WEAKNESS_KINDS).toContain(sampleWeakness.kind);
  });

  it("SkillProfile.tier is one of the four valid SkillTier values", () => {
    const validTiers = ["expert", "proficient", "developing", "exposure"];
    expect(validTiers).toContain(sampleSkill.tier);
  });

  it("a shallow_skill weakness never has a null category (per the backend contract)", () => {
    // Documented on PortfolioWeakness in src/types/weakness.ts: only
    // limited_practice is portfolio-wide (category: null). shallow_skill
    // and limited_breadth always carry a real RuleCategory.
    if (sampleWeakness.kind === "shallow_skill") {
      expect(sampleWeakness.category).not.toBeNull();
    }
  });

  it("a limited_practice weakness always has a null category (per the backend contract)", () => {
    if (sampleWeakness.kind === "limited_practice") {
      expect(sampleWeakness.category).toBeNull();
    }
  });
});
