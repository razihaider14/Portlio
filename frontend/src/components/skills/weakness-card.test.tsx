import { describe, expect, it } from "vitest";
import { axe } from "jest-axe";
import { render, screen } from "@testing-library/react";
import { WeaknessCard } from "@/components/skills/weakness-card";
import type { PortfolioWeakness } from "@/types/weakness";

const shallowSkillWeakness: PortfolioWeakness = {
  kind: "shallow_skill",
  name: "Cobol",
  category: "language",
  description: "Detected in only one repository with low confidence.",
  evidence: ["1 repository", "average detector confidence 0.4"],
};

const limitedPracticeWeakness: PortfolioWeakness = {
  kind: "limited_practice",
  name: "CI/CD",
  category: null,
  description: "Most repositories lack continuous integration configuration.",
  evidence: ["6 of 8 repositories have no CI/CD provider configured"],
};

const limitedBreadthWeakness: PortfolioWeakness = {
  kind: "limited_breadth",
  name: "Frontend Breadth",
  category: "frontend",
  description: "Only one frontend framework represented despite several UI repositories.",
  evidence: ["3 repositories tagged frontend, only React detected"],
};

describe("WeaknessCard", () => {
  it("renders a shallow_skill weakness with its category badge", () => {
    render(<WeaknessCard weakness={shallowSkillWeakness} />);
    expect(screen.getByText("Cobol")).toBeInTheDocument();
    expect(screen.getByText("Shallow skill")).toBeInTheDocument();
    expect(screen.getByText("Language")).toBeInTheDocument();
    expect(
      screen.getByText("Detected in only one repository with low confidence."),
    ).toBeInTheDocument();
  });

  it("renders a limited_practice weakness with no category badge (category is null)", () => {
    render(<WeaknessCard weakness={limitedPracticeWeakness} />);
    expect(screen.getByText("CI/CD")).toBeInTheDocument();
    expect(screen.getByText("Engineering practice gap")).toBeInTheDocument();
    // No RuleCategory label should be rendered for this weakness.
    expect(screen.queryByText("Language")).not.toBeInTheDocument();
    expect(screen.queryByText("Frontend")).not.toBeInTheDocument();
  });

  it("renders a limited_breadth weakness with its category badge", () => {
    render(<WeaknessCard weakness={limitedBreadthWeakness} />);
    expect(screen.getByText("Frontend Breadth")).toBeInTheDocument();
    expect(screen.getByText("Limited breadth")).toBeInTheDocument();
    expect(screen.getByText("Frontend")).toBeInTheDocument();
  });

  it("renders every evidence item", () => {
    render(<WeaknessCard weakness={shallowSkillWeakness} />);
    for (const item of shallowSkillWeakness.evidence) {
      expect(screen.getByText(item)).toBeInTheDocument();
    }
  });

  it("does not render a tier badge, score, or repository count (weaknesses are not SkillProfiles)", () => {
    render(<WeaknessCard weakness={shallowSkillWeakness} />);
    expect(
      screen.queryByText(/expert|proficient|developing|exposure/i),
    ).not.toBeInTheDocument();
    expect(screen.queryByText("Repositories")).not.toBeInTheDocument();
    expect(screen.queryByRole("progressbar")).not.toBeInTheDocument();
  });

  describe("accessibility", () => {
    it.each([
      ["shallow_skill", shallowSkillWeakness],
      ["limited_practice", limitedPracticeWeakness],
      ["limited_breadth", limitedBreadthWeakness],
    ] as const)("has no axe violations for kind=%s", async (_kind, weakness) => {
      const { container } = render(<WeaknessCard weakness={weakness} />);
      expect(await axe(container)).toHaveNoViolations();
    });
  });
});
