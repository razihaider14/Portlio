import Link from "next/link";
import { GitFork, ListChecks, Star } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { TechBadgeList } from "@/components/repos/tech-badge-list";
import { withDeepScan } from "@/lib/with-deep-scan";
import type { RepositoryDetail } from "@/types/repository";

interface RepoListItemProps {
  repo: RepositoryDetail;
  username: string;
  deepScan?: boolean;
}

const TECH_BADGE_LIMIT = 5;

export function RepoListItem({ repo, username, deepScan = false }: RepoListItemProps) {
  const { stars, forks } = repo.metadata.maturity;

  return (
    <Card className="gap-3 py-5">
      <CardHeader className="px-5">
        <CardTitle className="text-base break-words">
          <Link
            href={withDeepScan(
              `/analyze/${encodeURIComponent(username)}/repos/${encodeURIComponent(repo.name)}`,
              deepScan,
            )}
            className="hover:text-primary underline-offset-4 hover:underline"
          >
            {repo.name}
          </Link>
        </CardTitle>
        {repo.language && (
          <p className="text-muted-foreground text-xs">{repo.language}</p>
        )}
      </CardHeader>

      <CardContent className="flex flex-col gap-3 px-5">
        <TechBadgeList technologies={repo.technologies} limit={TECH_BADGE_LIMIT} />

        <div className="text-muted-foreground flex items-center gap-4 text-xs">
          <span className="flex items-center gap-1" title={`${stars} stars`}>
            <Star aria-hidden="true" className="size-3.5" />
            {stars}
          </span>
          <span className="flex items-center gap-1" title={`${forks} forks`}>
            <GitFork aria-hidden="true" className="size-3.5" />
            {forks}
          </span>
          <span className="flex items-center gap-1" title={`${repo.skills.length} skills detected`}>
            <ListChecks aria-hidden="true" className="size-3.5" />
            {repo.skills.length} {repo.skills.length === 1 ? "skill" : "skills"}
          </span>
        </div>
      </CardContent>
    </Card>
  );
}
