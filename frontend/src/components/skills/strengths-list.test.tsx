import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { StrengthsList } from "@/components/skills/strengths-list";
import { sampleSkill } from "@/lib/api/__fixtures__/sampleResponses";

describe("StrengthsList", () => {
  it("renders one SkillCard per strength", () => {
    render(<StrengthsList strengths={[sampleSkill]} />);
    expect(screen.getByText("Python")).toBeInTheDocument();
  });

  it("shows an empty-state message when there are no strengths", () => {
    render(<StrengthsList strengths={[]} />);
    expect(screen.getByText("No standout strengths yet")).toBeInTheDocument();
  });
});
