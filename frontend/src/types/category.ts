/**
 * Mirrors app.detector.models.RuleCategory (backend/app/detector/models.py).
 * A `str, Enum` in Python, so FastAPI/pydantic-free plain-dict responses
 * serialize each member to its `.value` string, these are exactly those
 * string values, not the Python member names.
 *
 * This is a closed, deliberately small set the backend docstring says is
 * chosen per-technology ("choose the most specific one that applies"), so
 * a literal union is safe here, unlike the free-form string tag lists in
 * src/types/metadata.ts (project_types, hardware_platforms, etc.), which
 * are open sets and typed as `string[]` instead.
 */
export type RuleCategory =
  | "language"
  | "framework"
  | "build_system"
  | "package_manager"
  | "frontend"
  | "mobile"
  | "embedded"
  | "container"
  | "orchestration"
  | "ci_cd"
  | "devops"
  | "cloud"
  | "database"
  | "data_science"
  | "ml_ai"
  | "testing"
  | "documentation"
  | "static_analysis";
