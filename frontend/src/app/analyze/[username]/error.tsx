"use client";

import * as React from "react";
import { AnalyzeErrorState } from "@/components/analyze/analyze-error-state";
import { PageHeader } from "@/components/shared/page-header";

interface AnalyzeUserErrorProps {
  error: Error & { digest?: string };
  reset: () => void;
}

/**
 * Next.js requires error.tsx to be a Client Component and renders it in
 * place of the segment when a render-time exception propagates up
 * uncaught. In this route, expected API failures (429/503/network) never
 * reach here, SkillsDashboard handles those inline with its own
 * AnalyzeErrorState + retry button so the exact status can drive the
 * message. This boundary is the last-resort net for anything else: a
 * genuine bug, or a failure mode nobody anticipated. It's still built to
 * be useful rather than a bare "Something went wrong," since AnalyzeErrorState
 * already knows how to read an ApiError if one ends up here anyway.
 */
export default function AnalyzeUserError({
  error,
  reset,
}: AnalyzeUserErrorProps) {
  React.useEffect(() => {
    console.error("Unexpected error on /analyze/[username]:", error);
  }, [error]);

  return (
    <main className="mx-auto max-w-6xl px-6 py-10">
      <div className="flex flex-col gap-8">
        <PageHeader title="Something went wrong" />
        <AnalyzeErrorState error={error} onRetry={reset} />
      </div>
    </main>
  );
}
