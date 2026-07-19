import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { Ghost } from "lucide-react";
import { EmptyState } from "@/components/shared/empty-state";

describe("EmptyState", () => {
  it("renders the title", () => {
    render(<EmptyState icon={Ghost} title="Nothing here" />);
    expect(screen.getByText("Nothing here")).toBeInTheDocument();
  });

  it("renders the description when provided", () => {
    render(
      <EmptyState icon={Ghost} title="Nothing here" description="Try again later." />,
    );
    expect(screen.getByText("Try again later.")).toBeInTheDocument();
  });

  it("omits the description when not provided", () => {
    render(<EmptyState icon={Ghost} title="Nothing here" />);
    expect(screen.queryByText("Try again later.")).not.toBeInTheDocument();
  });

  it("renders an action when provided", () => {
    render(
      <EmptyState
        icon={Ghost}
        title="Nothing here"
        action={<button type="button">Retry</button>}
      />,
    );
    expect(screen.getByRole("button", { name: "Retry" })).toBeInTheDocument();
  });
});
