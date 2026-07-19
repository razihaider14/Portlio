import { PartyPopper } from "lucide-react";
import { WeaknessCard } from "@/components/skills/weakness-card";
import { EmptyState } from "@/components/shared/empty-state";
import type { PortfolioWeakness } from "@/types/weakness";

interface WeaknessesListProps {
  weaknesses: PortfolioWeakness[];
}

export function WeaknessesList({ weaknesses }: WeaknessesListProps) {
  if (weaknesses.length === 0) {
    return (
      <EmptyState
        icon={PartyPopper}
        title="No weaknesses detected"
        description="Nothing shallow, no portfolio-wide practice gaps, and no under-represented categories found."
      />
    );
  }

  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {weaknesses.map((weakness) => (
        <WeaknessCard key={`${weakness.kind}-${weakness.name}`} weakness={weakness} />
      ))}
    </div>
  );
}
