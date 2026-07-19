"use client";

import { usePathname } from "next/navigation";
import { UserRoundX } from "lucide-react";
import { UsernameForm } from "@/components/analyze/username-form";
import { EmptyState } from "@/components/shared/empty-state";
import { PageHeader } from "@/components/shared/page-header";

/**
 * Next.js doesn't pass route params to not-found.tsx, so the username is
 * read back out of the URL instead, this file must be a Client Component
 * for usePathname() to work. Falls back to a generic message if parsing
 * somehow comes up empty rather than showing "undefined" to the person.
 */
function usernameFromPathname(pathname: string | null): string | null {
  if (!pathname) return null;
  const segments = pathname.split("/").filter(Boolean);
  const username = segments.at(-1);
  return username ? decodeURIComponent(username) : null;
}

export default function AnalyzeUserNotFound() {
  const pathname = usePathname();
  const username = usernameFromPathname(pathname);

  return (
    <main className="mx-auto max-w-6xl px-6 py-10">
      <div className="flex flex-col gap-8">
        <PageHeader title={username ?? "Not found"} />
        <EmptyState
          icon={UserRoundX}
          title="GitHub user not found"
          description={
            username
              ? `There's no GitHub account named "${username}" — check the spelling and try again.`
              : "That GitHub account doesn't exist — check the spelling and try again."
          }
          action={<UsernameForm defaultValue={username ?? ""} className="w-full max-w-xs" />}
        />
      </div>
    </main>
  );
}
