import type { RuleCategory } from "@/types/category";
import type { PortfolioWeakness } from "@/types/weakness";
import type { SkillRecommendation } from "@/types/recommendation";

/**
 * Mirrors app.aggregator.models.SkillTier (backend/app/aggregator/models.py).
 * A bucketed depth rating derived from a SkillProfile's `score`; see
 * app.aggregator.rules.tier_for_score() on the backend for the thresholds.
 */
export type SkillTier = "expert" | "proficient" | "developing" | "exposure";

/**
 * Mirrors app.aggregator.models.SkillProfile (backend/app/aggregator/models.py).
 * Portfolio-level aggregation of one technology (or derived composite
 * skill, e.g. "ESP32", "IoT") across every repository it was detected in.
 * Returned as elements of "skills"/"strengths" by both
 * GET /skills/{username} and GET /analyze/{username} (in "portfolio"), and
 * also as each repository's own "skills" field in GET /analyze/{username}.
 *
 * All fields are required and always present, SkillProfile is a Python
 * dataclass with no server-side optional fields, and FastAPI here returns
 * the raw dict form of it directly (no pydantic response_model narrowing
 * fields further).
 */
export interface SkillProfile {
  name: string;
  category: RuleCategory;
  repository_count: number;
  repositories: string[];
  average_detector_confidence: number;
  average_practice_score: number;
  score: number;
  max_score: number;
  tier: SkillTier;
  evidence: string[];
  is_composite: boolean;
}

/**
 * Mirrors app.aggregator.models.PortfolioSkillReport (backend/app/aggregator/models.py).
 * This is the exact response shape of GET /skills/{username} (see that
 * endpoint's docstring in backend/app/main.py, which documents this same
 * shape field-by-field), and is also what GET /analyze/{username} returns
 * under its top-level "portfolio" key.
 */
export interface PortfolioSkillReport {
  repository_count: number;
  skills: SkillProfile[];
  strengths: SkillProfile[];
  weaknesses: PortfolioWeakness[];
  recommendations: SkillRecommendation[];
}
