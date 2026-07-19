import { Compass } from "lucide-react";
import { RecommendationCard } from "@/components/skills/recommendation-card";
import { EmptyState } from "@/components/shared/empty-state";
import type { SkillRecommendation } from "@/types/recommendation";

interface RecommendationsListProps {
  recommendations: SkillRecommendation[];
}

export function RecommendationsList({
  recommendations,
}: RecommendationsListProps) {
  if (recommendations.length === 0) {
    return (
      <EmptyState
        icon={Compass}
        title="No recommendations right now"
        description="Recommendations come from complementary-skill gaps in the portfolio. Check back as the portfolio grows."
      />
    );
  }

  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {recommendations.map((recommendation) => (
        <RecommendationCard
          key={recommendation.skill}
          recommendation={recommendation}
        />
      ))}
    </div>
  );
}
