import { describe, expect, it, vi } from "vitest";
import { axe } from "jest-axe";
import { render, screen } from "@testing-library/react";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
}));
vi.mock("@/components/providers/navigation-progress", () => ({
  useNavigationProgress: () => ({ start: vi.fn() }),
}));

const AnalyzeEntryPage = (await import("@/app/analyze/page")).default;

describe("AnalyzeEntryPage", () => {
  it("renders the heading", () => {
    render(<AnalyzeEntryPage />);
    expect(
      screen.getByRole("heading", { name: "Analyze a GitHub portfolio" }),
    ).toBeInTheDocument();
  });

  it("renders the UsernameForm", () => {
    render(<AnalyzeEntryPage />);
    expect(screen.getByLabelText("GitHub username")).toBeInTheDocument();
  });

  describe("accessibility", () => {
    it("has no axe violations", async () => {
      const { container } = render(<AnalyzeEntryPage />);
      expect(await axe(container)).toHaveNoViolations();
    });
  });
});
