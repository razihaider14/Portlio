"use client";

import * as React from "react";
import { ExternalLink } from "lucide-react";
import { Switch } from "@/components/ui/switch";
import { cn } from "@/lib/utils";

interface ProfileHeaderProps {
  username: string;
  repositoryCount: number;
  deepScan: boolean;
  onDeepScanChange: (value: boolean) => void;
  actions?: React.ReactNode;
  className?: string;
}

/**
 * GitHub serves a profile avatar at this URL for any username — a plain
 * <img>, not next/image, deliberately: next/image would require adding
 * github.com to next.config.ts's remote image allowlist for what's a
 * decorative, best-effort element, and a plain tag degrades gracefully
 * (onError below just hides it) without that config surface.
 */
function avatarUrl(username: string): string {
  return `https://github.com/${encodeURIComponent(username)}.png?size=80`;
}

export function ProfileHeader({
  username,
  repositoryCount,
  deepScan,
  onDeepScanChange,
  actions,
  className,
}: ProfileHeaderProps) {
  const [avatarFailed, setAvatarFailed] = React.useState(false);
  const deepScanId = React.useId();

  return (
    <div className={cn("flex flex-col gap-4", className)}>
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div className="flex items-center gap-3">
          {!avatarFailed && (
            // eslint-disable-next-line @next/next/no-img-element -- deliberate: see avatarUrl()'s docstring.
            <img
              src={avatarUrl(username)}
              alt=""
              width={56}
              height={56}
              className="size-14 shrink-0 rounded-full border"
              onError={() => setAvatarFailed(true)}
            />
          )}
          <div className="min-w-0">
            <h1 className="text-2xl font-semibold tracking-tight break-words">{username}</h1>
            <div className="text-muted-foreground mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-sm">
              <span>
                {repositoryCount} {repositoryCount === 1 ? "repository" : "repositories"}{" "}
                analyzed
              </span>
              <a
                href={`https://github.com/${encodeURIComponent(username)}`}
                target="_blank"
                rel="noopener noreferrer"
                className="hover:text-foreground inline-flex items-center gap-1 underline-offset-4 hover:underline"
              >
                View on GitHub
                <ExternalLink aria-hidden="true" className="size-3" />
              </a>
            </div>
          </div>
        </div>

        {actions && (
          <div className="flex shrink-0 items-center gap-2">{actions}</div>
        )}
      </div>

      <div className="flex items-start gap-3 rounded-lg border px-4 py-3">
        <Switch
          id={deepScanId}
          checked={deepScan}
          onCheckedChange={onDeepScanChange}
          className="mt-0.5"
        />
        <div>
          <label htmlFor={deepScanId} className="cursor-pointer text-sm font-medium">
            Deep scan
          </label>
          <p className="text-muted-foreground text-xs">
            Downloads README and manifest file contents for richer detection.
            Takes longer and uses more GitHub API requests.
          </p>
        </div>
      </div>
    </div>
  );
}
