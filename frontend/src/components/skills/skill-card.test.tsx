import { describe, expect, it } from "vitest";
import { axe } from "jest-axe";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { SkillCard } from "@/components/skills/skill-card";
import {
  sampleCompositeSkill,
  sampleSkill,
} from "@/lib/api/__fixtures__/sampleResponses";

describe("SkillCard", () => {
  it("renders the skill's name", () => {
    render(<SkillCard skill={sampleSkill} />);
    expect(screen.getByText("Python")).toBeInTheDocument();
  });

  it("renders the human-readable category", () => {
    render(<SkillCard skill={sampleSkill} />);
    expect(screen.getByText("Language")).toBeInTheDocument();
  });

  it("renders the tier badge", () => {
    render(<SkillCard skill={sampleSkill} />);
    expect(screen.getByText("Expert")).toBeInTheDocument();
  });

  it("renders score / max_score", () => {
    render(<SkillCard skill={sampleSkill} />);
    expect(screen.getByText("42 / 50")).toBeInTheDocument();
  });

  it("renders the repository count", () => {
    render(<SkillCard skill={sampleSkill} />);
    expect(screen.getByText("Repositories")).toBeInTheDocument();
    expect(screen.getByText("4")).toBeInTheDocument();
  });

  it("renders confidence as a 0-100% bar", () => {
    render(<SkillCard skill={sampleSkill} />);
    expect(screen.getByRole("progressbar")).toHaveAttribute(
      "aria-valuenow",
      "95",
    );
  });

  it("renders the evidence list, initially collapsed", () => {
    render(<SkillCard skill={sampleSkill} />);
    const details = screen.getByText(/Evidence \(2\)/).closest("details");
    expect(details).not.toBeNull();
    expect(details).not.toHaveAttribute("open");
    // Content still exists in the DOM (native <details> semantics), just
    // visually hidden — assert every evidence item is present.
    for (const item of sampleSkill.evidence) {
      expect(screen.getByText(item)).toBeInTheDocument();
    }
  });

  it("expands the evidence list on click", async () => {
    const user = userEvent.setup();
    render(<SkillCard skill={sampleSkill} />);

    const summary = screen.getByText(/Evidence \(2\)/);
    await user.click(summary);

    const details = summary.closest("details");
    expect(details).toHaveAttribute("open");
  });

  it("does not render an evidence section when there is no evidence", () => {
    render(<SkillCard skill={{ ...sampleSkill, evidence: [] }} />);
    expect(screen.queryByText(/Evidence \(/)).not.toBeInTheDocument();
  });

  it("indicates composite skills without hiding the name", () => {
    render(<SkillCard skill={sampleCompositeSkill} />);
    expect(screen.getByText("ESP32")).toBeInTheDocument();
    expect(
      screen.getByText(/composite skill/i, { exact: false }),
    ).toBeInTheDocument();
  });

  it("does not show the composite indicator for a non-composite skill", () => {
    render(<SkillCard skill={sampleSkill} />);
    expect(screen.queryByText(/composite skill/i)).not.toBeInTheDocument();
  });

  describe("accessibility", () => {
    it("has no axe violations (collapsed)", async () => {
      const { container } = render(<SkillCard skill={sampleSkill} />);
      expect(await axe(container)).toHaveNoViolations();
    });

    it("has no axe violations (expanded evidence)", async () => {
      const user = userEvent.setup();
      const { container } = render(<SkillCard skill={sampleSkill} />);
      await user.click(screen.getByText(/Evidence \(2\)/));
      expect(await axe(container)).toHaveNoViolations();
    });
  });
});
