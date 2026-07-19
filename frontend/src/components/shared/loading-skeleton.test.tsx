import { describe, expect, it } from "vitest";
import { render } from "@testing-library/react";
import { LoadingSkeleton } from "@/components/shared/loading-skeleton";

describe("LoadingSkeleton", () => {
  it.each(["skill-card", "stat", "text-line"] as const)(
    "renders the %s variant as decorative (aria-hidden)",
    (variant) => {
      const { container } = render(<LoadingSkeleton variant={variant} />);
      expect(container.firstElementChild).toHaveAttribute("aria-hidden", "true");
    },
  );

  it("applies a custom className", () => {
    const { container } = render(
      <LoadingSkeleton variant="text-line" className="w-1/2" />,
    );
    expect(container.firstElementChild).toHaveClass("w-1/2");
  });
});
