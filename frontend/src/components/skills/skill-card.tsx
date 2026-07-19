import { Layers } from "lucide-react";
import {
  Card,
  CardAction,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { ConfidenceBar } from "@/components/skills/confidence-bar";
import { TierBadge } from "@/components/skills/tier-badge";
import { categoryLabel } from "@/lib/category";
import { cn } from "@/lib/utils";
import type { SkillProfile } from "@/types/skill";

interface SkillCardProps {
  skill: SkillProfile;
  className?: string;
}

export function SkillCard({ skill, className }: SkillCardProps) {
  return (
    <Card className={cn("gap-4 py-5", className)}>
      <CardHeader className="gap-1 px-5">
        <CardTitle className="flex items-center gap-1.5 text-base">
          {skill.name}
          {skill.is_composite && (
            <Layers
              aria-hidden="true"
              className="text-muted-foreground size-3.5"
            />
          )}
          {skill.is_composite && (
            <span className="sr-only">
              (composite skill, derived from related evidence)
            </span>
          )}
        </CardTitle>
        <CardDescription>{categoryLabel(skill.category)}</CardDescription>
        <CardAction>
          <TierBadge tier={skill.tier} />
        </CardAction>
      </CardHeader>

      <CardContent className="flex flex-col gap-4 px-5">
        <dl className="text-sm">
          <div className="flex items-center justify-between">
            <dt className="text-muted-foreground">Score</dt>
            <dd className="font-medium tabular-nums">
              {skill.score} / {skill.max_score}
            </dd>
          </div>
          <div className="flex items-center justify-between">
            <dt className="text-muted-foreground">Repositories</dt>
            <dd className="font-medium tabular-nums">
              {skill.repository_count}
            </dd>
          </div>
        </dl>

        <ConfidenceBar
          value={skill.average_detector_confidence}
          label={`${skill.name} detector confidence`}
        />

        {skill.evidence.length > 0 && (
          <details className="group text-sm">
            <summary className="text-muted-foreground hover:text-foreground cursor-pointer list-none font-medium select-none">
              <span className="inline-flex items-center gap-1">
                Evidence ({skill.evidence.length})
                <span
                  aria-hidden="true"
                  className="transition-transform group-open:rotate-90"
                >
                  &rsaquo;
                </span>
              </span>
            </summary>
            <ul className="text-muted-foreground mt-2 list-disc space-y-1 pl-4">
              {skill.evidence.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </details>
        )}
      </CardContent>
    </Card>
  );
}
