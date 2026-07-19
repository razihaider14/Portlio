import { Clock, ServerCrash, WifiOff, XCircle } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ApiError } from "@/lib/api/errors";

interface AnalyzeErrorStateProps {
  error: unknown;
  onRetry?: () => void;
  className?: string;
}

interface ErrorPresentation {
  icon: LucideIcon;
  title: string;
  description: string;
}

/**
 * Maps an error to what the interface should say, in the interface's own
 * voice, plain about what happened, no apology, no vague "something went
 * wrong" when we actually know the cause.
 *
 * 404 is deliberately NOT one of the cases handled here: a nonexistent
 * GitHub user is routed to Next's notFound() / not-found.tsx instead (see
 * src/app/analyze/[username]/page.tsx), since that's a distinct, common,
 * "the thing you asked for doesn't exist" outcome rather than a failure of
 * the request itself.
 */
function presentationFor(error: unknown): ErrorPresentation {
  if (error instanceof ApiError) {
    if (error.isRateLimited) {
      return {
        icon: Clock,
        title: "GitHub rate limit exceeded",
        description:
          "SkillForge has hit GitHub's API rate limit. This usually clears within an hour — try again shortly.",
      };
    }
    if (error.isServiceUnavailable) {
      return {
        icon: ServerCrash,
        title: "Backend unavailable",
        description:
          "GitHub's API is temporarily unreachable from the SkillForge backend. Try again in a moment.",
      };
    }
    if (error.isNetworkError) {
      return {
        icon: WifiOff,
        title: "Can't reach SkillForge",
        description:
          "Check your connection and that the SkillForge backend is running.",
      };
    }
  }

  return {
    icon: XCircle,
    title: "Something went wrong",
    description:
      error instanceof Error
        ? error.message
        : "An unexpected error occurred while analyzing this portfolio.",
  };
}

export function AnalyzeErrorState({
  error,
  onRetry,
  className,
}: AnalyzeErrorStateProps) {
  const { icon: Icon, title, description } = presentationFor(error);

  return (
    <div
      role="alert"
      className={
        "border-destructive/30 bg-destructive/5 flex flex-col items-center gap-3 rounded-lg border px-6 py-10 text-center " +
        (className ?? "")
      }
    >
      <Icon aria-hidden="true" className="text-destructive size-6" />
      <div>
        <p className="font-medium">{title}</p>
        <p className="text-muted-foreground mt-1 max-w-sm text-sm">
          {description}
        </p>
      </div>
      {onRetry && (
        <Button type="button" variant="outline" size="sm" onClick={onRetry}>
          Try again
        </Button>
      )}
    </div>
  );
}
