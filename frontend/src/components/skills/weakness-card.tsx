import { AlertTriangle, ShieldAlert, Waves } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { categoryLabel } from "@/lib/category";
import { cn } from "@/lib/utils";
import type { PortfolioWeakness, WeaknessKind } from "@/types/weakness";

interface WeaknessCardProps {
  weakness: PortfolioWeakness;
  className?: string;
}

const KIND_META: Record<
  WeaknessKind,
  { icon: LucideIcon; label: string }
> = {
  shallow_skill: {
    icon: AlertTriangle,
    label: "Shallow skill",
  },
  limited_practice: {
    icon: ShieldAlert,
    label: "Engineering practice gap",
  },
  limited_breadth: {
    icon: Waves,
    label: "Limited breadth",
  },
};

/**
 * PortfolioWeakness has no `tier`, `score`, or `repositories` — it is not a
 * SkillProfile, and this deliberately does not reuse SkillCard. See
 * src/types/weakness.ts for exactly what `name`/`category` mean per kind:
 * only shallow_skill and limited_breadth carry a real category;
 * limited_practice is portfolio-wide and its category is always null.
 */
export function WeaknessCard({ weakness, className }: WeaknessCardProps) {
  const meta = KIND_META[weakness.kind];
  const Icon = meta.icon;

  return (
    <Card className={cn("gap-3 py-5", className)}>
      <CardHeader className="px-5">
        <div className="flex items-start justify-between gap-2">
          <div className="flex min-w-0 items-start gap-2">
            <Icon
              aria-hidden="true"
              className="text-muted-foreground mt-0.5 size-4 shrink-0"
            />
            <div className="min-w-0">
              <CardTitle className="text-base break-words">{weakness.name}</CardTitle>
              <p className="text-muted-foreground mt-0.5 text-xs">
                {meta.label}
              </p>
            </div>
          </div>
          {weakness.category && (
            <Badge variant="secondary" className="shrink-0">
              {categoryLabel(weakness.category)}
            </Badge>
          )}
        </div>
      </CardHeader>

      <CardContent className="px-5">
        <p className="text-sm">{weakness.description}</p>

        {weakness.evidence.length > 0 && (
          <ul className="text-muted-foreground mt-3 list-disc space-y-1 pl-4 text-sm">
            {weakness.evidence.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}
