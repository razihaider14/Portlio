import { describe, expect, it } from "vitest";
import { axe } from "jest-axe";
import { render, screen } from "@testing-library/react";
import { RecommendationCard } from "@/components/skills/recommendation-card";
import type { SkillRecommendation } from "@/types/recommendation";

const directRecommendation: SkillRecommendation = {
  skill: "Django",
  category: "framework",
  reason: "Commonly paired with Python for web backends.",
  based_on: ["Python"],
  chain: [],
};

const chainedRecommendation: SkillRecommendation = {
  skill: "ESP-IDF",
  category: "embedded",
  reason: "The native SDK for ESP32 development beyond Arduino abstractions.",
  based_on: ["ESP32"],
  chain: ["FreeRTOS"],
};

const noAttributionRecommendation: SkillRecommendation = {
  skill: "Rust",
  category: "language",
  reason: "A popular systems language worth exploring.",
  based_on: [],
  chain: [],
};

describe("RecommendationCard", () => {
  it("renders the skill name, category, and reason", () => {
    render(<RecommendationCard recommendation={directRecommendation} />);
    expect(screen.getAllByText("Django").length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText("Framework")).toBeInTheDocument();
    expect(
      screen.getByText("Commonly paired with Python for web backends."),
    ).toBeInTheDocument();
  });

  it("renders a direct recommendation's based_on as a breadcrumb", () => {
    render(<RecommendationCard recommendation={directRecommendation} />);
    expect(screen.getByText("Python")).toBeInTheDocument();
    // "Django" legitimately appears twice: the card title and the final
    // breadcrumb segment.
    expect(screen.getAllByText("Django").length).toBeGreaterThanOrEqual(2);
  });

  it("renders a chained recommendation's full based_on -> chain -> skill path", () => {
    render(<RecommendationCard recommendation={chainedRecommendation} />);
    expect(screen.getByText("ESP32")).toBeInTheDocument();
    expect(screen.getByText("FreeRTOS")).toBeInTheDocument();
    expect(screen.getAllByText("ESP-IDF").length).toBeGreaterThanOrEqual(2);
  });

  it("renders no breadcrumb when there is nothing to attribute the suggestion to", () => {
    render(<RecommendationCard recommendation={noAttributionRecommendation} />);
    // Only "Rust" (the title) should appear — no separate breadcrumb chip.
    expect(screen.getAllByText("Rust")).toHaveLength(1);
  });

  describe("accessibility", () => {
    it("has no axe violations for a direct recommendation", async () => {
      const { container } = render(
        <RecommendationCard recommendation={directRecommendation} />,
      );
      expect(await axe(container)).toHaveNoViolations();
    });

    it("has no axe violations for a chained recommendation", async () => {
      const { container } = render(
        <RecommendationCard recommendation={chainedRecommendation} />,
      );
      expect(await axe(container)).toHaveNoViolations();
    });
  });
});
