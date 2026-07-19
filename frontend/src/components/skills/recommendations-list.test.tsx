import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { RecommendationsList } from "@/components/skills/recommendations-list";
import { sampleRecommendation } from "@/lib/api/__fixtures__/sampleResponses";

describe("RecommendationsList", () => {
  it("renders one RecommendationCard per recommendation", () => {
    render(<RecommendationsList recommendations={[sampleRecommendation]} />);
    expect(screen.getAllByText("FreeRTOS").length).toBeGreaterThanOrEqual(1);
  });

  it("shows an empty-state message when there are no recommendations", () => {
    render(<RecommendationsList recommendations={[]} />);
    expect(
      screen.getByText("No recommendations right now"),
    ).toBeInTheDocument();
  });
});
