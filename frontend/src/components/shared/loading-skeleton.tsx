import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";

type LoadingSkeletonVariant = "skill-card" | "stat" | "text-line";

interface LoadingSkeletonProps {
  variant: LoadingSkeletonVariant;
  className?: string;
}

/**
 * Shape-matched skeleton blocks for the pieces of UI that take a moment to
 * load. Each variant approximates the real component's layout (so the page
 * doesn't visibly "jump" once data arrives) rather than being one generic
 * gray box reused everywhere.
 */
export function LoadingSkeleton({ variant, className }: LoadingSkeletonProps) {
  if (variant === "skill-card") {
    return (
      <div
        className={cn("flex flex-col gap-4 rounded-xl border p-5", className)}
        aria-hidden="true"
      >
        <div className="flex items-start justify-between gap-2">
          <div className="flex flex-col gap-2">
            <Skeleton className="h-4 w-24" />
            <Skeleton className="h-3 w-16" />
          </div>
          <Skeleton className="h-5 w-20 rounded-md" />
        </div>
        <Skeleton className="h-3 w-full" />
        <Skeleton className="h-2 w-full rounded-full" />
      </div>
    );
  }

  if (variant === "stat") {
    return (
      <div
        className={cn("flex flex-col gap-2 rounded-xl border p-4", className)}
        aria-hidden="true"
      >
        <Skeleton className="h-3 w-16" />
        <Skeleton className="h-6 w-10" />
      </div>
    );
  }

  // "text-line"
  return <Skeleton className={cn("h-4 w-full", className)} aria-hidden="true" />;
}
