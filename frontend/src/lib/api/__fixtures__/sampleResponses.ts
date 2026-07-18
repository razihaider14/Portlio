import type { PortfolioSkillReport, SkillProfile } from "@/types/skill";
import type { PortfolioWeakness } from "@/types/weakness";
import type { SkillRecommendation } from "@/types/recommendation";
import type { AnalyzeResponse, GithubReposResponse } from "@/types/repository";

export const sampleSkill: SkillProfile = {
  name: "Python",
  category: "language",
  repository_count: 4,
  repositories: ["api", "cli", "worker", "scripts"],
  average_detector_confidence: 0.95,
  average_practice_score: 6,
  score: 42,
  max_score: 50,
  tier: "expert",
  evidence: ["detected in 4 repositories", "average practice score 6/10"],
  is_composite: false,
};

export const sampleCompositeSkill: SkillProfile = {
  name: "ESP32",
  category: "embedded",
  repository_count: 2,
  repositories: ["firmware", "sensor-node"],
  average_detector_confidence: 0.8,
  average_practice_score: 3,
  score: 18,
  max_score: 50,
  tier: "developing",
  evidence: ["derived from Arduino + PlatformIO evidence"],
  is_composite: true,
};

export const sampleWeakness: PortfolioWeakness = {
  kind: "limited_practice",
  name: "CI/CD",
  category: null,
  description: "Most repositories lack continuous integration configuration.",
  evidence: ["6 of 8 repositories have no CI/CD provider configured"],
};

export const sampleRecommendation: SkillRecommendation = {
  skill: "FreeRTOS",
  category: "embedded",
  reason: "Commonly paired with ESP32 for real-time task scheduling.",
  based_on: ["ESP32"],
  chain: [],
};

export const sampleSkillsResponse: PortfolioSkillReport = {
  repository_count: 8,
  skills: [sampleSkill, sampleCompositeSkill],
  strengths: [sampleSkill],
  weaknesses: [sampleWeakness],
  recommendations: [sampleRecommendation],
};

export const sampleAnalyzeResponse: AnalyzeResponse = {
  username: "octocat",
  repository_count: 1,
  repositories: [
    {
      name: "api",
      language: "Python",
      contents: [
        { path: "requirements.txt", name: "requirements.txt", type: "file", size: 42 },
        { path: "src", name: "src", type: "dir" },
      ],
      technologies: ["Python", "FastAPI"],
      metadata: {
        project_types: ["api_backend"],
        hardware_platforms: [],
        documentation: {
          has_readme: true,
          has_license_file: true,
          has_changelog: false,
          has_contributing: false,
          has_code_of_conduct: false,
          readme_length_chars: 1200,
          readme_heading_count: 5,
          readme_sections: ["installation", "usage"],
          score: 5,
          quality_tier: "good",
        },
        has_tests: true,
        has_ci_cd: true,
        ci_providers: ["github_actions"],
        has_docker: false,
        has_docker_compose: false,
        has_kubernetes_manifests: false,
        package_managers: ["pip"],
        build_systems: [],
        license: { detected: true, spdx_id: "MIT", source: "github_api" },
        maturity: {
          stars: 12,
          forks: 2,
          open_issues: 1,
          age_days: 400,
          days_since_last_push: 10,
          is_archived: false,
          is_fork: false,
          maturity_tier: "mature",
        },
        size_metrics: {
          total_files: 30,
          total_directories: 6,
          file_count_by_extension: { ".py": 25, ".md": 2 },
          max_directory_depth: 3,
          repo_size_kb: 512,
        },
      },
      skills: [sampleSkill],
    },
  ],
  portfolio: sampleSkillsResponse,
};

export const sampleGithubReposResponse: GithubReposResponse = {
  username: "octocat",
  repository_count: 1,
  repositories: [
    {
      name: "api",
      description: "A sample API.",
      language: "Python",
      stars: 12,
      forks: 2,
      url: "https://github.com/octocat/api",
    },
  ],
};
