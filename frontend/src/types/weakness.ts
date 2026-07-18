import type { RuleCategory } from "@/types/category";

/**
 * Mirrors app.aggregator.models.WeaknessKind (backend/app/aggregator/models.py).
 *
 * - shallow_skill: a specific detected skill with minimal supporting
 *   evidence (SkillTier.EXPOSURE), usually one repository, low detector
 *   confidence, and/or no engineering-practice signals.
 * - limited_practice: a portfolio-wide engineering-practice gap (e.g. most
 *   repositories lack CI/CD or tests). Not tied to any one skill.
 * - limited_breadth: a whole ecosystem category represented by only a
 *   single technology despite a meaningful repository footprint.
 */
export type WeaknessKind =
  | "shallow_skill"
  | "limited_practice"
  | "limited_breadth";

/**
 * Mirrors app.aggregator.models.PortfolioWeakness (backend/app/aggregator/models.py).
 *
 * IMPORTANT: this is NOT the same shape as SkillProfile (src/types/skill.ts).
 * It has no `tier`, `score`, or `repositories`; components rendering
 * "weaknesses" must not assume SkillCard-shaped data. See PortfolioWeakness's
 * backend docstring for exactly what `name`/`category` mean per `kind`:
 *   - shallow_skill: `name` is the skill's name (e.g. "Cobol"), `category`
 *     is that skill's RuleCategory.
 *   - limited_practice: `name` is a human-readable label (e.g. "CI/CD"),
 *     `category` is always null (portfolio-wide, not category-specific).
 *   - limited_breadth: `name` is a human-readable label (e.g.
 *     "Frontend Breadth"), `category` is the under-represented RuleCategory.
 */
export interface PortfolioWeakness {
  kind: WeaknessKind;
  name: string;
  category: RuleCategory | null;
  description: string;
  evidence: string[];
}
