export function SkipLink() {
  return (
    <a
      href="#main-content"
      className="bg-background text-foreground focus-visible:ring-ring sr-only z-50 rounded-md border px-4 py-2 text-sm font-medium focus:not-sr-only focus:fixed focus:top-4 focus:left-4 focus-visible:ring-2 focus-visible:outline-none"
    >
      Skip to main content
    </a>
  );
}
