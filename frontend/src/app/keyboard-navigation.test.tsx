import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ThemeProvider } from "@/components/providers/theme-provider";
import { SkipLink } from "@/components/layout/skip-link";
import { Header } from "@/components/layout/header";
import { ProfileHeader } from "@/components/analyze/profile-header";
import { FAQSection } from "@/components/about/faq-section";

function renderWithTheme(node: React.ReactNode) {
  return render(
    <ThemeProvider attribute="class" defaultTheme="light" enableSystem={false}>
      {node}
    </ThemeProvider>,
  );
}

describe("Keyboard navigation", () => {
  it("reaches the skip link on the very first Tab press, before any other content", async () => {
    const user = userEvent.setup();
    renderWithTheme(
      <>
        <SkipLink />
        <Header />
      </>,
    );

    await user.tab();

    expect(screen.getByRole("link", { name: "Skip to main content" })).toHaveFocus();
  });

  it("tabs through Header's interactive elements in a sensible order (wordmark, nav links, theme toggle, Analyze)", async () => {
    const user = userEvent.setup();
    renderWithTheme(<Header />);
    await screen.findByRole("button", { name: /switch to/i });

    await user.tab(); // wordmark
    expect(screen.getByRole("link", { name: "Portlio" })).toHaveFocus();

    await user.tab(); // Home
    expect(screen.getByRole("link", { name: "Home" })).toHaveFocus();

    await user.tab(); // About
    expect(screen.getByRole("link", { name: "About" })).toHaveFocus();

    await user.tab(); // theme toggle
    expect(screen.getByRole("button", { name: /switch to/i })).toHaveFocus();

    await user.tab(); // Analyze CTA (desktop) — mobile nav toggle also exists but the
    // desktop Analyze link precedes it in DOM order.
    expect(screen.getAllByRole("link", { name: "Analyze" })[0]).toHaveFocus();
  });

  it("the Deep Scan switch can be toggled with the keyboard (Space), not just a click", async () => {
    const user = userEvent.setup();
    const onDeepScanChange = vi.fn();
    render(
      <ProfileHeader
        username="octocat"
        repositoryCount={8}
        deepScan={false}
        onDeepScanChange={onDeepScanChange}
      />,
    );

    const toggle = screen.getByRole("switch");
    toggle.focus();
    await user.keyboard(" ");

    expect(onDeepScanChange).toHaveBeenCalledWith(true);
  });

  it("uses a native <details>/<summary> disclosure, not a custom div — so Enter/Space activation is guaranteed by the HTML spec, not app code", () => {
    // jsdom implements <details> click-to-toggle (see faq-section.test.tsx's
    // "expands an answer on click" test) but not the browser's native
    // default action for activating a *focused* <summary> via Enter/Space —
    // that's a jsdom gap, not something reproducible here. What we can and
    // should verify is that this really is a native disclosure widget, since
    // real browsers guarantee keyboard operability for that element for free.
    render(<FAQSection />);
    const summary = document.querySelector("summary");
    expect(summary).not.toBeNull();
    expect(summary?.tagName).toBe("SUMMARY");
    expect(summary?.closest("details")?.tagName).toBe("DETAILS");
    // A custom clickable div wouldn't be in the default Tab order; a real
    // <summary> inside <details> always is.
    expect(summary?.tabIndex).not.toBe(-1);
  });
});
