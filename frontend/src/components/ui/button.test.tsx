import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Button } from "@/components/ui/button";

describe("Button", () => {
  it("renders its children", () => {
    render(<Button>Analyze</Button>);
    expect(screen.getByRole("button", { name: "Analyze" })).toBeInTheDocument();
  });

  it("fires onClick", async () => {
    const onClick = vi.fn();
    const user = userEvent.setup();
    render(<Button onClick={onClick}>Analyze</Button>);

    await user.click(screen.getByRole("button", { name: "Analyze" }));

    expect(onClick).toHaveBeenCalledTimes(1);
  });

  it("is disabled when the disabled prop is set", () => {
    render(<Button disabled>Analyze</Button>);
    expect(screen.getByRole("button", { name: "Analyze" })).toBeDisabled();
  });

  it("applies variant-specific classes", () => {
    render(<Button variant="destructive">Delete</Button>);
    expect(screen.getByRole("button", { name: "Delete" })).toHaveClass(
      "bg-destructive",
    );
  });

  it("merges a caller-supplied className instead of dropping it", () => {
    render(<Button className="my-custom-class">Analyze</Button>);
    expect(screen.getByRole("button", { name: "Analyze" })).toHaveClass(
      "my-custom-class",
    );
  });

  it("renders as the child element when asChild is set, instead of a <button>", () => {
    render(
      <Button asChild>
        <a href="https://example.com/profile">Analyze</a>
      </Button>,
    );
    const link = screen.getByRole("link", { name: "Analyze" });
    expect(link).toBeInTheDocument();
    expect(link.tagName).toBe("A");
  });
});
