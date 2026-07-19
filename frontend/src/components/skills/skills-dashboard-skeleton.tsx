import { LoadingSkeleton } from "@/components/shared/loading-skeleton";
import { Skeleton } from "@/components/ui/skeleton";

/**
 * The full Skills Dashboard skeleton. Used in two places for two different
 * reasons — see src/app/analyze/[username]/loading.tsx and page.tsx:
 *
 * - loading.tsx: Next.js's route-segment Suspense fallback, shown while
 *   this segment's JS/RSC payload is streaming in.
 * - page.tsx: rendered inline while useSkills().isLoading is true, since
 *   that's a client-side fetch that happens after the route has already
 *   loaded and isn't something Next's file-based loading.tsx can see —
 *   this is the skeleton people actually spend the most time looking at.
 *
 * Kept as one shared component specifically so those two moments render
 * identically instead of drifting apart.
 */
export function SkillsDashboardSkeleton() {
  return (
    <div className="flex flex-col gap-8" aria-busy="true" aria-live="polite">
      <div className="flex flex-col gap-2">
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-4 w-40" />
      </div>

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <LoadingSkeleton key={i} variant="stat" />
        ))}
      </div>

      <div className="flex flex-col gap-3">
        <Skeleton className="h-5 w-32" />
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <LoadingSkeleton key={i} variant="skill-card" />
          ))}
        </div>
      </div>

      <span className="sr-only">Loading skill analysis…</span>
    </div>
  );
}
