import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { PageHeader } from "@/components/shared/page-header";

describe("PageHeader", () => {
  it("renders the title as a heading", () => {
    render(<PageHeader title="octocat" />);
    expect(screen.getByRole("heading", { name: "octocat" })).toBeInTheDocument();
  });

  it("renders the description when provided", () => {
    render(<PageHeader title="octocat" description="8 repositories analyzed" />);
    expect(screen.getByText("8 repositories analyzed")).toBeInTheDocument();
  });

  it("renders actions when provided", () => {
    render(
      <PageHeader title="octocat" actions={<button type="button">Refresh</button>} />,
    );
    expect(screen.getByRole("button", { name: "Refresh" })).toBeInTheDocument();
  });
});
