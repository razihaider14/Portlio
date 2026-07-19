import { describe, expect, it } from "vitest";
import { axe } from "jest-axe";
import { render, screen } from "@testing-library/react";
import { ConfidenceBar } from "@/components/skills/confidence-bar";

describe("ConfidenceBar", () => {
  it("renders a 0-1 float as a rounded percentage", () => {
    render(<ConfidenceBar value={0.923} />);
    expect(screen.getByText("92%")).toBeInTheDocument();
  });

  it("renders 0% and 100% at the extremes", () => {
    const { rerender } = render(<ConfidenceBar value={0} />);
    expect(screen.getByText("0%")).toBeInTheDocument();

    rerender(<ConfidenceBar value={1} />);
    expect(screen.getByText("100%")).toBeInTheDocument();
  });

  it("clamps a value above 1 to 100%", () => {
    render(<ConfidenceBar value={1.4} />);
    expect(screen.getByRole("progressbar")).toHaveAttribute(
      "aria-valuenow",
      "100",
    );
  });

  it("clamps a negative value to 0%", () => {
    render(<ConfidenceBar value={-0.2} />);
    expect(screen.getByRole("progressbar")).toHaveAttribute(
      "aria-valuenow",
      "0",
    );
  });

  it("sets the visual bar width from the value", () => {
    render(<ConfidenceBar value={0.5} />);
    const fill = screen.getByRole("progressbar").firstElementChild as HTMLElement;
    expect(fill.style.width).toBe("50%");
  });

  describe("accessibility", () => {
    it("exposes role=progressbar with numeric aria-value bounds", () => {
      render(<ConfidenceBar value={0.75} />);
      const bar = screen.getByRole("progressbar");
      expect(bar).toHaveAttribute("aria-valuemin", "0");
      expect(bar).toHaveAttribute("aria-valuemax", "100");
      expect(bar).toHaveAttribute("aria-valuenow", "75");
    });

    it("includes a descriptive aria-label, not just a bare percentage", () => {
      render(<ConfidenceBar value={0.75} label="Python detector confidence" />);
      expect(screen.getByRole("progressbar")).toHaveAttribute(
        "aria-label",
        "Python detector confidence: 75%",
      );
    });

    it("has no axe violations", async () => {
      const { container } = render(<ConfidenceBar value={0.6} />);
      expect(await axe(container)).toHaveNoViolations();
    });
  });
});
