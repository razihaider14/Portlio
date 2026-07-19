import { Trophy } from "lucide-react";
import { SkillCard } from "@/components/skills/skill-card";
import { EmptyState } from "@/components/shared/empty-state";
import type { SkillProfile } from "@/types/skill";

interface StrengthsListProps {
  strengths: SkillProfile[];
}

export function StrengthsList({ strengths }: StrengthsListProps) {
  if (strengths.length === 0) {
    return (
      <EmptyState
        icon={Trophy}
        title="No standout strengths yet"
        description="Strengths need enough evidence across repositories to earn a top tier. Keep building — this list grows with the portfolio."
      />
    );
  }

  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {strengths.map((skill) => (
        <SkillCard key={skill.name} skill={skill} />
      ))}
    </div>
  );
}
