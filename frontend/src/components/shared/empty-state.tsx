import type { LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";

interface EmptyStateProps {
  icon: LucideIcon;
  title: string;
  description?: string;
  action?: React.ReactNode;
  className?: string;
}

/**
 * A generic empty-state block, used wherever a list from the API can
 * legitimately be empty (no skills detected, no weaknesses found, no
 * recommendations, no repositories). Per the frontend-design guidance this
 * project follows: emptiness is a moment for direction, not mood — every
 * usage should say plainly what's missing and, where there's something
 * useful to do about it, offer an action rather than just a blank state.
 */
export function EmptyState({
  icon: Icon,
  title,
  description,
  action,
  className,
}: EmptyStateProps) {
  return (
    <div
      className={cn(
        "border-border flex flex-col items-center gap-2 rounded-lg border border-dashed px-6 py-10 text-center",
        className,
      )}
    >
      <Icon aria-hidden="true" className="text-muted-foreground size-6" />
      <p className="font-medium">{title}</p>
      {description && (
        <p className="text-muted-foreground max-w-sm text-sm">
          {description}
        </p>
      )}
      {action && <div className="mt-2">{action}</div>}
    </div>
  );
}
