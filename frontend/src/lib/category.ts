import type { RuleCategory } from "@/types/category";

export const CATEGORY_LABELS: Record<RuleCategory, string> = {
  language: "Language",
  framework: "Framework",
  build_system: "Build System",
  package_manager: "Package Manager",
  frontend: "Frontend",
  mobile: "Mobile",
  embedded: "Embedded",
  container: "Container",
  orchestration: "Orchestration",
  ci_cd: "CI/CD",
  devops: "DevOps",
  cloud: "Cloud",
  database: "Database",
  data_science: "Data Science",
  ml_ai: "ML/AI",
  testing: "Testing",
  documentation: "Documentation",
  static_analysis: "Static Analysis",
};

export const ALL_CATEGORIES: RuleCategory[] = Object.keys(
  CATEGORY_LABELS,
) as RuleCategory[];

export function categoryLabel(category: RuleCategory): string {
  return CATEGORY_LABELS[category] ?? category;
}
