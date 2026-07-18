import type { RuleCategory } from "@/types/category";

/**
 * Mirrors app.aggregator.models.SkillRecommendation (backend/app/aggregator/models.py).
 *
 * A suggested skill to learn next, based on a complementary-skill gap.
 * `chain` is empty for a direct, 1-hop recommendation; when non-empty it
 * lists the hypothetical intermediate skill(s) not yet detected in the
 * portfolio. Example from the backend docstring: a recommendation of
 * "ESP-IDF" reached via established "ESP32" -> "FreeRTOS" -> "ESP-IDF" has
 * `based_on: ["ESP32"]` and `chain: ["FreeRTOS"]`. UI should render chained
 * recommendations differently from direct ones (e.g. a breadcrumb), not
 * treat `chain` as incidental detail.
 */
export interface SkillRecommendation {
  skill: string;
  category: RuleCategory;
  reason: string;
  based_on: string[];
  chain: string[];
}
