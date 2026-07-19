import { SearchX } from "lucide-react";
import { SkillCard } from "@/components/skills/skill-card";
import { EmptyState } from "@/components/shared/empty-state";
import type { SkillProfile } from "@/types/skill";

interface SkillsGridProps {
  skills: SkillProfile[];
  /** True when the portfolio has skills overall, but the current filter matched none. */
  isFiltered?: boolean;
}

export function SkillsGrid({ skills, isFiltered = false }: SkillsGridProps) {
  if (skills.length === 0) {
    return (
      <EmptyState
        icon={SearchX}
        title={isFiltered ? "No skills in this category" : "No skills detected"}
        description={
          isFiltered
            ? "Try a different category, or clear the filter to see everything."
            : "SkillForge didn't detect any technologies in this portfolio's repositories."
        }
      />
    );
  }

  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {skills.map((skill) => (
        <SkillCard key={skill.name} skill={skill} />
      ))}
    </div>
  );
}
