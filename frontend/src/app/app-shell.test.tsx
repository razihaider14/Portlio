import { describe, expect, it, vi } from "vitest";
import { axe } from "jest-axe";
import { render, screen } from "@testing-library/react";
import { ThemeProvider } from "@/components/providers/theme-provider";
import { SkipLink } from "@/components/layout/skip-link";
import { Header } from "@/components/layout/header";
import { Footer } from "@/components/layout/footer";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
}));
vi.mock("@/components/providers/navigation-progress", () => ({
  useNavigationProgress: () => ({ start: vi.fn() }),
}));

const LandingPage = (await import("@/app/page")).default;
const AboutPage = (await import("@/app/about/page")).default;

/**
 * Mirrors src/app/layout.tsx's actual JSX structure (minus <html>/<body>
 * and Providers, which RTL can't sensibly mount) — SkipLink, Header, page
 * content, Footer, all together in one tree, exactly as a real visit would
 * compose them. Isolated per-page tests (page.test.tsx, about/page.test.tsx)
 * never render Header/Footer alongside the page, so they can't catch
 * cross-boundary issues: two elements from different components sharing an
 * id, a landmark region appearing twice, or a heading level that's fine
 * within one component but wrong once a real page's own headings are
 * layered in above it.
 */
function renderAppShell(page: React.ReactNode) {
  return render(
    <ThemeProvider attribute="class" defaultTheme="light" enableSystem={false}>
      <SkipLink />
      <div className="flex min-h-svh flex-col">
        <Header />
        <div id="main-content" tabIndex={-1} className="flex-1 outline-none">
          {page}
        </div>
        <Footer />
      </div>
    </ThemeProvider>,
  );
}

describe("App shell composition (Header + page + Footer)", () => {
  describe("Landing page inside the shell", () => {
    it("has exactly one Primary navigation landmark and one banner/contentinfo", async () => {
      renderAppShell(<LandingPage />);
      await screen.findByRole("button", { name: /switch to/i }); // wait for ThemeToggle to mount

      expect(screen.getAllByRole("navigation", { name: "Primary" })).toHaveLength(1);
      expect(screen.getByRole("banner")).toBeInTheDocument(); // <header>
      expect(screen.getByRole("contentinfo")).toBeInTheDocument(); // <footer>
    });

    it("has no duplicate element ids across Header + page + Footer", () => {
      const { container } = renderAppShell(<LandingPage />);
      const ids = Array.from(container.querySelectorAll("[id]")).map((el) => el.id);
      const uniqueIds = new Set(ids);
      expect(ids.length).toBe(uniqueIds.size);
    });

    it("has no axe violations for the full shell + Landing page", async () => {
      const { container } = renderAppShell(<LandingPage />);
      await screen.findByRole("button", { name: /switch to/i });
      expect(await axe(container)).toHaveNoViolations();
    });
  });

  describe("About page inside the shell", () => {
    it("has no duplicate element ids across Header + page + Footer", () => {
      const { container } = renderAppShell(<AboutPage />);
      const ids = Array.from(container.querySelectorAll("[id]")).map((el) => el.id);
      const uniqueIds = new Set(ids);
      expect(ids.length).toBe(uniqueIds.size);
    });

    it("has no axe violations for the full shell + About page", async () => {
      const { container } = renderAppShell(<AboutPage />);
      await screen.findByRole("button", { name: /switch to/i });
      expect(await axe(container)).toHaveNoViolations();
    });
  });
});
