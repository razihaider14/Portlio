import { describe, expect, it } from "vitest";
import { axe } from "jest-axe";
import { render, screen } from "@testing-library/react";
import { TierBadge } from "@/components/skills/tier-badge";
import { TIER_META } from "@/lib/tier";
import type { SkillTier } from "@/types/skill";

const ALL_TIERS: SkillTier[] = ["expert", "proficient", "developing", "exposure"];

describe("TierBadge", () => {
  it.each(ALL_TIERS)("renders the correct label for tier=%s", (tier) => {
    render(<TierBadge tier={tier} />);
    expect(screen.getByText(TIER_META[tier].label)).toBeInTheDocument();
  });

  it("exposes the tier's description as a title (tooltip) attribute", () => {
    render(<TierBadge tier="expert" />);
    expect(screen.getByText("Expert").closest("[title]")).toHaveAttribute(
      "title",
      TIER_META.expert.description,
    );
  });

  it.each(ALL_TIERS)(
    "applies a distinct className per tier (not just relying on the label)",
    (tier) => {
      const { container } = render(<TierBadge tier={tier} />);
      const badge = container.firstElementChild;
      expect(badge?.className).toContain(`tier-${tier}`);
    },
  );

  describe("accessibility", () => {
    it.each(ALL_TIERS)("has no axe violations for tier=%s", async (tier) => {
      const { container } = render(<TierBadge tier={tier} />);
      expect(await axe(container)).toHaveNoViolations();
    });
  });
});
