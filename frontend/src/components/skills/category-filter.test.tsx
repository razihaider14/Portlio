import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { CategoryFilter } from "@/components/skills/category-filter";

describe("CategoryFilter", () => {
  it("renders 'All' plus one button per offered category", () => {
    render(
      <CategoryFilter
        categories={["language", "framework"]}
        selected={null}
        onChange={vi.fn()}
      />,
    );
    expect(screen.getByRole("button", { name: "All" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Language" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Framework" })).toBeInTheDocument();
  });

  it("does not render categories that weren't offered", () => {
    render(
      <CategoryFilter categories={["language"]} selected={null} onChange={vi.fn()} />,
    );
    expect(screen.queryByRole("button", { name: "Framework" })).not.toBeInTheDocument();
  });

  it("renders nothing when no categories are offered", () => {
    const { container } = render(
      <CategoryFilter categories={[]} selected={null} onChange={vi.fn()} />,
    );
    expect(container).toBeEmptyDOMElement();
  });

  it("marks 'All' as pressed when selected is null", () => {
    render(
      <CategoryFilter categories={["language"]} selected={null} onChange={vi.fn()} />,
    );
    expect(screen.getByRole("button", { name: "All" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
  });

  it("marks the selected category as pressed", () => {
    render(
      <CategoryFilter
        categories={["language", "framework"]}
        selected="framework"
        onChange={vi.fn()}
      />,
    );
    expect(screen.getByRole("button", { name: "Framework" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
    expect(screen.getByRole("button", { name: "Language" })).toHaveAttribute(
      "aria-pressed",
      "false",
    );
  });

  it("calls onChange with the category when an unselected category is clicked", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(
      <CategoryFilter categories={["language"]} selected={null} onChange={onChange} />,
    );

    await user.click(screen.getByRole("button", { name: "Language" }));
    expect(onChange).toHaveBeenCalledWith("language");
  });

  it("calls onChange with null when the already-selected category is clicked again (toggle off)", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(
      <CategoryFilter categories={["language"]} selected="language" onChange={onChange} />,
    );

    await user.click(screen.getByRole("button", { name: "Language" }));
    expect(onChange).toHaveBeenCalledWith(null);
  });

  it("calls onChange with null when 'All' is clicked", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(
      <CategoryFilter categories={["language"]} selected="language" onChange={onChange} />,
    );

    await user.click(screen.getByRole("button", { name: "All" }));
    expect(onChange).toHaveBeenCalledWith(null);
  });
});
