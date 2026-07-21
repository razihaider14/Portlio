import { describe, expect, it, afterEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ThemeProvider } from "@/components/providers/theme-provider";
import { ThemeToggle } from "@/components/layout/theme-toggle";

afterEach(() => {
  document.documentElement.classList.remove("dark", "light");
});

describe("Dark mode class application", () => {
  it("applies the .dark class to <html> when defaultTheme is dark", async () => {
    render(
      <ThemeProvider attribute="class" defaultTheme="dark" enableSystem={false}>
        <div>content</div>
      </ThemeProvider>,
    );

    await waitFor(() =>
      expect(document.documentElement.classList.contains("dark")).toBe(true),
    );
  });

  it("does not apply the .dark class when defaultTheme is light", async () => {
    render(
      <ThemeProvider attribute="class" defaultTheme="light" enableSystem={false}>
        <div>content</div>
      </ThemeProvider>,
    );

    await waitFor(() =>
      expect(document.documentElement.classList.contains("light")).toBe(true),
    );
    expect(document.documentElement.classList.contains("dark")).toBe(false);
  });

  it("toggling ThemeToggle actually flips the .dark class on <html>, not just its own label", async () => {
    const user = userEvent.setup();
    render(
      <ThemeProvider attribute="class" defaultTheme="light" enableSystem={false}>
        <ThemeToggle />
      </ThemeProvider>,
    );

    await waitFor(() =>
      expect(document.documentElement.classList.contains("dark")).toBe(false),
    );

    await user.click(await screen.findByRole("button", { name: "Switch to dark theme" }));

    await waitFor(() =>
      expect(document.documentElement.classList.contains("dark")).toBe(true),
    );
  });
});
