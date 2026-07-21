import { ExternalLink, GitFork, Star } from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";

interface RepoDetailHeaderProps {
  repoName: string;
  username: string;
  language: string | null;
  stars: number;
  forks: number;
  /**
   * Best-effort only. GET /analyze/{username} (this page's primary data
   * source, per useAnalysis()) has no description field — see
   * src/types/repository.ts's docstring on RepositoryDetail. When
   * provided, it comes from the existing useRepos() hook (GET
   * /github/{username}), which SkillsDashboard doesn't need but this page
   * layers in specifically for this field. `undefined` means "not loaded
   * yet or unavailable"; this component never blocks or errors on it —
   * see RepoDetail's fetch policy for why.
   */
  description?: string | null;
  isDescriptionLoading?: boolean;
}

/**
 * GitHub repo URLs are fully deterministic from {owner}/{repo} — this is
 * synthesized directly rather than depending on any API response, so the
 * "GitHub link" requirement never depends on a second network call
 * succeeding.
 */
function githubUrl(username: string, repoName: string): string {
  return `https://github.com/${encodeURIComponent(username)}/${encodeURIComponent(repoName)}`;
}

export function RepoDetailHeader({
  repoName,
  username,
  language,
  stars,
  forks,
  description,
  isDescriptionLoading = false,
}: RepoDetailHeaderProps) {
  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <h1 className="text-2xl font-semibold tracking-tight break-words">{repoName}</h1>
          {language && (
            <p className="text-muted-foreground mt-1 text-sm">{language}</p>
          )}
        </div>
        <a
          href={githubUrl(username, repoName)}
          target="_blank"
          rel="noopener noreferrer"
          className="text-muted-foreground hover:text-foreground inline-flex items-center gap-1 text-sm underline-offset-4 hover:underline"
        >
          View on GitHub
          <ExternalLink aria-hidden="true" className="size-3.5" />
        </a>
      </div>

      {isDescriptionLoading ? (
        <Skeleton className="h-4 w-2/3" aria-hidden="true" />
      ) : (
        description && <p className="text-sm">{description}</p>
      )}

      <div className="text-muted-foreground flex items-center gap-4 text-sm">
        <span className="flex items-center gap-1">
          <Star aria-hidden="true" className="size-4" />
          {stars} {stars === 1 ? "star" : "stars"}
        </span>
        <span className="flex items-center gap-1">
          <GitFork aria-hidden="true" className="size-4" />
          {forks} {forks === 1 ? "fork" : "forks"}
        </span>
      </div>
    </div>
  );
}
