"use client";

import * as React from "react";
import { usePathname } from "next/navigation";

interface NavigationProgressContextValue {
  /** Call before a programmatic navigation (router.push) that a real <a> click won't trigger automatically. */
  start: () => void;
}

const NavigationProgressContext =
  React.createContext<NavigationProgressContextValue | null>(null);

/** How often progress ticks upward while a navigation is in flight. */
const TICK_MS = 200;
/** Progress creeps toward this cap but never reaches it on its own — only finish() completes the bar. */
const PROGRESS_CAP = 90;
/** How long the bar stays visible at 100% before fading out, so the completion is perceptible. */
const FINISH_LINGER_MS = 250;

export function NavigationProgressProvider({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname();
  const [progress, setProgress] = React.useState(0);
  const [active, setActive] = React.useState(false);
  const intervalRef = React.useRef<ReturnType<typeof setInterval> | null>(null);
  const lingerTimeoutRef = React.useRef<ReturnType<typeof setTimeout> | null>(null);
  const previousPathname = React.useRef(pathname);

  const clearTimers = React.useCallback(() => {
    if (intervalRef.current !== null) clearInterval(intervalRef.current);
    if (lingerTimeoutRef.current !== null) clearTimeout(lingerTimeoutRef.current);
    intervalRef.current = null;
    lingerTimeoutRef.current = null;
  }, []);

  const start = React.useCallback(() => {
    clearTimers();
    setActive(true);
    // Jump to a small nonzero value immediately — a bar that starts at 0%
    // and creeps up from nothing reads as sluggish even when it isn't.
    setProgress(12);
    intervalRef.current = setInterval(() => {
      setProgress((current) => {
        const next = current + (PROGRESS_CAP - current) * 0.15;
        return next >= PROGRESS_CAP ? PROGRESS_CAP : next;
      });
    }, TICK_MS);
  }, [clearTimers]);

  const finish = React.useCallback(() => {
    clearTimers();
    setProgress(100);
    lingerTimeoutRef.current = setTimeout(() => {
      setActive(false);
      setProgress(0);
    }, FINISH_LINGER_MS);
  }, [clearTimers]);

  // The pathname is the one signal that reliably means "the new route has
  // actually rendered," regardless of whether the navigation was a <Link>
  // click or a programmatic router.push() from start().
  React.useEffect(() => {
    if (pathname !== previousPathname.current) {
      previousPathname.current = pathname;
      finish();
    }
    // finish() is stable (useCallback with a stable dep), but including it
    // would re-run this effect on every render for no reason; pathname is
    // the only thing that should trigger it.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pathname]);

  // Auto-detects same-tab internal <a> clicks (everything next/link
  // renders) without requiring every Link usage in the app to be wired up
  // manually. Programmatic navigations (UsernameForm's router.push on
  // submit) aren't real clicks on an <a>, so they call start() explicitly
  // via useNavigationProgress() instead.
  React.useEffect(() => {
    function handleClick(event: MouseEvent) {
      if (event.defaultPrevented || event.button !== 0) return;
      if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;

      const anchor = (event.target as HTMLElement | null)?.closest("a");
      if (!anchor) return;
      if (anchor.target && anchor.target !== "_self") return;
      if (anchor.hasAttribute("download")) return;

      const href = anchor.getAttribute("href");
      if (!href || href.startsWith("#")) return;

      let url: URL;
      try {
        url = new URL(href, window.location.href);
      } catch {
        return;
      }
      if (url.origin !== window.location.origin) return;
      if (`${url.pathname}${url.search}` === `${window.location.pathname}${window.location.search}`) {
        return;
      }

      start();
    }

    document.addEventListener("click", handleClick);
    return () => document.removeEventListener("click", handleClick);
  }, [start]);

  React.useEffect(() => clearTimers, [clearTimers]);

  const contextValue = React.useMemo(() => ({ start }), [start]);

  return (
    <NavigationProgressContext.Provider value={contextValue}>
      {active && <NavigationProgressBar progress={progress} />}
      {children}
    </NavigationProgressContext.Provider>
  );
}

export function useNavigationProgress(): NavigationProgressContextValue {
  const context = React.useContext(NavigationProgressContext);
  if (!context) {
    throw new Error(
      "useNavigationProgress must be used within a NavigationProgressProvider",
    );
  }
  return context;
}

function NavigationProgressBar({ progress }: { progress: number }) {
  return (
    <div
      role="progressbar"
      aria-label="Page loading"
      aria-valuenow={Math.round(progress)}
      aria-valuemin={0}
      aria-valuemax={100}
      className="fixed inset-x-0 top-0 z-50 h-[3px] overflow-hidden"
    >
      <div
        className="from-primary/60 via-primary to-primary/60 relative h-full bg-gradient-to-r shadow-[0_0_8px_var(--color-primary)] transition-[width] duration-200 ease-out"
        style={{ width: `${progress}%` }}
      >
        <div className="animate-[nav-progress-shimmer_1.1s_ease-in-out_infinite] absolute inset-y-0 left-0 w-16 mix-blend-difference bg-white/40 blur-[2px] motion-reduce:hidden" />
      </div>
    </div>
  );
}
