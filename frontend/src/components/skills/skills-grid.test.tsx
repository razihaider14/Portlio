import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { SkillsGrid } from "@/components/skills/skills-grid";
import { sampleCompositeSkill, sampleSkill } from "@/lib/api/__fixtures__/sampleResponses";

describe("SkillsGrid", () => {
  it("renders one SkillCard per skill", () => {
    render(<SkillsGrid skills={[sampleSkill, sampleCompositeSkill]} />);
    expect(screen.getByText("Python")).toBeInTheDocument();
    expect(screen.getByText("ESP32")).toBeInTheDocument();
  });

  it("shows an unfiltered empty-state message when there are no skills at all", () => {
    render(<SkillsGrid skills={[]} />);
    expect(screen.getByText("No skills detected")).toBeInTheDocument();
  });

  it("shows a filtered empty-state message when isFiltered is true", () => {
    render(<SkillsGrid skills={[]} isFiltered />);
    expect(screen.getByText("No skills in this category")).toBeInTheDocument();
  });
});
