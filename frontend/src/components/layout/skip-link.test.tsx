import { describe, expect, it } from "vitest";
import { axe } from "jest-axe";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { SkipLink } from "@/components/layout/skip-link";

describe("SkipLink", () => {
  it("links to #main-content", () => {
    render(<SkipLink />);
    expect(screen.getByRole("link", { name: "Skip to main content" })).toHaveAttribute(
      "href",
      "#main-content",
    );
  });

  it("is visually hidden until focused", () => {
    render(<SkipLink />);
    expect(screen.getByRole("link", { name: "Skip to main content" })).toHaveClass(
      "sr-only",
    );
  });

  it("becomes focusable via keyboard (Tab reaches it first)", async () => {
    const user = userEvent.setup();
    render(<SkipLink />);

    await user.tab();

    expect(screen.getByRole("link", { name: "Skip to main content" })).toHaveFocus();
  });

  describe("accessibility", () => {
    it("has no axe violations", async () => {
      const { container } = render(<SkipLink />);
      expect(await axe(container)).toHaveNoViolations();
    });
  });
});
