import { BadgeCheck, Eye, Sparkles, TrendingUp } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import type { SkillTier } from "@/types/skill";

interface TierMeta {
  label: string;
  /** One-line description of what the tier means, for tooltips/aria-labels. */
  description: string;
  icon: LucideIcon;
  /** Tailwind classes for the soft-tint badge treatment (see globals.css tier tokens). */
  className: string;
}

export const TIER_META: Record<SkillTier, TierMeta> = {
  expert: {
    label: "Expert",
    description:
      "Deep, well-evidenced experience: high detector confidence, strong engineering practices, across multiple repositories.",
    icon: Sparkles,
    className:
      "bg-tier-expert-bg text-tier-expert-fg border-tier-expert-border",
  },
  proficient: {
    label: "Proficient",
    description:
      "Solid, demonstrated experience with good supporting evidence.",
    icon: BadgeCheck,
    className:
      "bg-tier-proficient-bg text-tier-proficient-fg border-tier-proficient-border",
  },
  developing: {
    label: "Developing",
    description:
      "Real but limited experience — fewer repositories or lighter supporting evidence than a proficient rating.",
    icon: TrendingUp,
    className:
      "bg-tier-developing-bg text-tier-developing-fg border-tier-developing-border",
  },
  exposure: {
    label: "Exposure",
    description:
      "Detected, but with minimal supporting evidence — often a single repository with low detector confidence.",
    icon: Eye,
    className:
      "bg-tier-exposure-bg text-tier-exposure-fg border-tier-exposure-border",
  },
};

/** Ranked highest to lowest, for sorting skill collections by tier. */
export const TIER_ORDER: SkillTier[] = [
  "expert",
  "proficient",
  "developing",
  "exposure",
];
