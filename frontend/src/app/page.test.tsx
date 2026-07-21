import { describe, expect, it, vi } from "vitest";
import { axe } from "jest-axe";
import { render, screen } from "@testing-library/react";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
}));
vi.mock("@/components/providers/navigation-progress", () => ({
  useNavigationProgress: () => ({ start: vi.fn() }),
}));

const LandingPage = (await import("@/app/page")).default;

describe("LandingPage", () => {
  it("renders the hero heading", () => {
    render(<LandingPage />);
    expect(screen.getByRole("heading", { level: 1 })).toBeInTheDocument();
  });

  it("renders all four feature cards", () => {
    render(<LandingPage />);
    expect(screen.getByText("Technology detection")).toBeInTheDocument();
    expect(screen.getByText("Recommendations")).toBeInTheDocument();
  });

  it("renders the example analysis preview", () => {
    render(<LandingPage />);
    expect(screen.getByText("What an analysis looks like")).toBeInTheDocument();
  });

  it("renders two independent UsernameForm instances (Hero and CTASection)", () => {
    render(<LandingPage />);
    expect(screen.getAllByLabelText("GitHub username")).toHaveLength(2);
  });

  describe("accessibility", () => {
    it("has no axe violations across the full composed page", async () => {
      const { container } = render(<LandingPage />);
      expect(await axe(container)).toHaveNoViolations();
    });
  });
});
