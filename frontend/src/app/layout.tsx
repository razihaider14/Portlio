import type { Metadata, Viewport } from "next";
import { GeistSans } from "geist/font/sans";
import { GeistMono } from "geist/font/mono";
import "./globals.css";
import { Providers } from "@/components/providers";
import { Header } from "@/components/layout/header";
import { Footer } from "@/components/layout/footer";
import { SkipLink } from "@/components/layout/skip-link";

// GeistSans/GeistMono ship their font files inside the `geist` npm package
// itself, so this works without reaching Google Fonts' CDN (which this
// build environment's network policy blocks) — unlike next/font/google,
// there's no runtime or build-time fetch involved.

export const metadata: Metadata = {
  title: "Portlio",
  description:
    "Evidence-based GitHub portfolio analysis: detected skills, strengths, weaknesses, and recommendations.",
};

// Matches globals.css's --background token exactly (#ffffff light,
// #0a0a0a dark, oklch(1 0 0) / oklch(0.145 0 0) converted to sRGB hex),
// so a mobile browser's own chrome (status bar / URL bar) blends with the
// page instead of showing a mismatched color during a theme switch.
export const viewport: Viewport = {
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#ffffff" },
    { media: "(prefers-color-scheme: dark)", color: "#0a0a0a" },
  ],
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    // suppressHydrationWarning is required with next-themes: it sets the
    // `dark`/`light` class on <html> before React hydrates, which would
    // otherwise cause a (harmless but noisy) hydration warning.
    <html lang="en" suppressHydrationWarning>
      <body
        className={`${GeistSans.variable} ${GeistMono.variable} font-sans antialiased`}
      >
        <Providers>
          <SkipLink />
          <div className="flex min-h-svh flex-col">
            <Header />
            <div id="main-content" tabIndex={-1} className="flex-1 outline-none">
              {children}
            </div>
            <Footer />
          </div>
        </Providers>
      </body>
    </html>
  );
}
