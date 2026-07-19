import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { WeaknessesList } from "@/components/skills/weaknesses-list";
import { sampleWeakness } from "@/lib/api/__fixtures__/sampleResponses";

describe("WeaknessesList", () => {
  it("renders one WeaknessCard per weakness", () => {
    render(<WeaknessesList weaknesses={[sampleWeakness]} />);
    expect(screen.getByText("CI/CD")).toBeInTheDocument();
  });

  it("shows a positively-framed empty-state message when there are no weaknesses", () => {
    render(<WeaknessesList weaknesses={[]} />);
    expect(screen.getByText("No weaknesses detected")).toBeInTheDocument();
  });
});
