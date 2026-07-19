import { Badge } from "@/components/ui/badge";
import { TIER_META } from "@/lib/tier";
import { cn } from "@/lib/utils";
import type { SkillTier } from "@/types/skill";

interface TierBadgeProps {
  tier: SkillTier;
  className?: string;
}

/**
 * Renders a SkillTier ("expert" | "proficient" | "developing" | "exposure")
 * as a labeled badge with a tier-specific icon and color, so the tier is
 * distinguishable by shape/icon as well as color (not color alone — see
 * TIER_META in src/lib/tier.ts for the full rationale).
 */
export function TierBadge({ tier, className }: TierBadgeProps) {
  const meta = TIER_META[tier];
  const Icon = meta.icon;

  return (
    <Badge
      variant="outline"
      className={cn("gap-1 border", meta.className, className)}
      title={meta.description}
    >
      <Icon aria-hidden="true" />
      {meta.label}
    </Badge>
  );
}
