import { ArrowRight } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { categoryLabel } from "@/lib/category";
import { cn } from "@/lib/utils";
import type { SkillRecommendation } from "@/types/recommendation";

interface RecommendationCardProps {
  recommendation: SkillRecommendation;
  className?: string;
}

/**
 * Renders the based_on -> chain -> skill path as a breadcrumb, e.g.
 * "ESP32 -> FreeRTOS -> ESP-IDF" for a recommendation of "ESP-IDF" with
 * based_on: ["ESP32"] and chain: ["FreeRTOS"] (the exact example from
 * SkillRecommendation's backend docstring). A direct (chain: []) 1-hop
 * recommendation still gets a breadcrumb when based_on is non-empty, e.g.
 * "Python -> Django" — it's only omitted entirely when based_on is also
 * empty (nothing to attribute the suggestion to).
 */
function breadcrumbSegments(recommendation: SkillRecommendation): string[] {
  const { based_on, chain, skill } = recommendation;
  const segments: string[] = [];
  if (based_on.length > 0) {
    segments.push(based_on.join(" + "));
  }
  segments.push(...chain);
  segments.push(skill);
  return segments;
}

export function RecommendationCard({
  recommendation,
  className,
}: RecommendationCardProps) {
  const segments = breadcrumbSegments(recommendation);
  const isChained = recommendation.chain.length > 0;

  return (
    <Card className={cn("gap-3 py-5", className)}>
      <CardHeader className="px-5">
        <div className="flex items-start justify-between gap-2">
          <CardTitle className="min-w-0 text-base break-words">{recommendation.skill}</CardTitle>
          <Badge variant="secondary" className="shrink-0">
            {categoryLabel(recommendation.category)}
          </Badge>
        </div>
      </CardHeader>

      <CardContent className="flex flex-col gap-3 px-5">
        <p className="text-sm">{recommendation.reason}</p>

        {segments.length > 1 && (
          <div
            className="text-muted-foreground flex flex-wrap items-center gap-1.5 text-xs"
            aria-label={
              isChained
                ? `Multi-step recommendation path: ${segments.join(" leads to ")}`
                : `Based on: ${segments.slice(0, -1).join(", ")}`
            }
          >
            {segments.map((segment, index) => (
              <span key={`${segment}-${index}`} className="flex items-center gap-1.5">
                {index > 0 && (
                  <ArrowRight aria-hidden="true" className="size-3" />
                )}
                <span
                  className={cn(
                    "rounded border px-1.5 py-0.5",
                    index === segments.length - 1
                      ? "border-primary/30 text-foreground font-medium"
                      : "border-border",
                  )}
                >
                  {segment}
                </span>
              </span>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
