/**
 * Mirrors the stable output shape of
 * app.metadata.metadata_analyzer.analyze_repository_metadata()
 * (backend/app/metadata/metadata_analyzer.py), specifically its
 * `_FIELD_DEFAULTS` dict, the backend's own docstring guarantees "the
 * return value always has exactly the keys in _FIELD_DEFAULTS", so typing
 * every field as required (never optional) here is accurate, not
 * optimistic: repositories with no signal for a field get its documented
 * empty/default value (`[]`, `false`, `0`, `null`, ...), never a missing
 * key.
 *
 * Fields typed as `string[]` (project_types, hardware_platforms,
 * ci_providers, package_managers, build_systems, readme_sections) are
 * open/extensible tag sets on the backend, individual analyzers can add
 * new tag values over time (see backend/app/metadata/analyzers/), so a
 * literal union here would silently go stale. `quality_tier` and
 * `maturity_tier` are different: they come from small, fixed point-rubric
 * thresholds (see documentation.py's _TIER_THRESHOLDS and maturity.py's
 * _tier()), so a literal union is both safe and more useful.
 */

export type DocumentationQualityTier =
  | "excellent"
  | "good"
  | "moderate"
  | "minimal"
  | "none";

export interface RepositoryDocumentation {
  has_readme: boolean;
  has_license_file: boolean;
  has_changelog: boolean;
  has_contributing: boolean;
  has_code_of_conduct: boolean;
  readme_length_chars: number | null;
  readme_heading_count: number;
  readme_sections: string[];
  score: number;
  quality_tier: DocumentationQualityTier;
}

export type LicenseSource =
  | "github_api"
  | "file_content_match"
  | "file_presence_only"
  | null;

export interface RepositoryLicense {
  detected: boolean;
  spdx_id: string | null;
  source: LicenseSource;
}

export type MaturityTier =
  | "archived"
  | "fork"
  | "unknown"
  | "experimental"
  | "stale"
  | "mature"
  | "active";

export interface RepositoryMaturity {
  stars: number;
  forks: number;
  open_issues: number;
  age_days: number | null;
  days_since_last_push: number | null;
  is_archived: boolean;
  is_fork: boolean;
  maturity_tier: MaturityTier;
}

export interface RepositorySizeMetrics {
  total_files: number;
  total_directories: number;
  file_count_by_extension: Record<string, number>;
  max_directory_depth: number;
  repo_size_kb: number | null;
}

/**
 * The full, always-complete metadata object for one repository. Matches
 * `repositories[].metadata` in GET /analyze/{username}'s response.
 */
export interface RepositoryMetadata {
  project_types: string[];
  hardware_platforms: string[];
  documentation: RepositoryDocumentation;
  has_tests: boolean;
  has_ci_cd: boolean;
  ci_providers: string[];
  has_docker: boolean;
  has_docker_compose: boolean;
  has_kubernetes_manifests: boolean;
  package_managers: string[];
  build_systems: string[];
  license: RepositoryLicense;
  maturity: RepositoryMaturity;
  size_metrics: RepositorySizeMetrics;
}
