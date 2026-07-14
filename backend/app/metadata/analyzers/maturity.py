"""
Computes repository maturity indicators from the raw GitHub repository API
fields (stars, forks, open issues, timestamps, archived/fork status).

The individual metrics are exact facts pulled straight from the API
(confidence 1.0). The "maturity_tier" bucketing on top of them is a
transparent, documented rubric, not a universal truth, so it's reported
at a lower confidence. The rubric:

    "archived"     if repo_metadata["archived"] is True
    "fork"         if repo_metadata["fork"] is True (and not archived)
    "experimental" if age_days < 30
    "stale"        if days_since_last_push > 730 (2 years)
    "mature"       if age_days >= 365 and days_since_last_push <= 180
    "active"       otherwise (created >= 30 days ago, pushed within 2 years,
                   but doesn't meet the "mature" bar yet)

Checked in that order; the first matching rule wins.
"""

from datetime import datetime, timezone

from app.metadata.models import AnalysisInput, Finding

_MISSING_TIMESTAMP_EVIDENCE = "repo_metadata missing created_at/pushed_at timestamps"


def _parse_github_timestamp(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _tier(
    archived: bool, fork: bool, age_days: int | None, days_since_push: int | None
) -> str:
    if archived:
        return "archived"
    if fork:
        return "fork"
    if age_days is None or days_since_push is None:
        return "unknown"
    if age_days < 30:
        return "experimental"
    if days_since_push > 730:
        return "stale"
    if age_days >= 365 and days_since_push <= 180:
        return "mature"
    return "active"


class MaturityAnalyzer:
    """Computes maturity metrics and a documented tier from GitHub repo API fields."""

    def analyze(self, input: AnalysisInput) -> list[Finding]:
        meta = input.repo_metadata
        now = datetime.now(timezone.utc)

        created_at = _parse_github_timestamp(meta.get("created_at"))
        pushed_at = _parse_github_timestamp(meta.get("pushed_at"))
        age_days = (now - created_at).days if created_at else None
        days_since_push = (now - pushed_at).days if pushed_at else None

        archived = bool(meta.get("archived", False))
        fork = bool(meta.get("fork", False))

        value = {
            "stars": meta.get("stargazers_count", 0),
            "forks": meta.get("forks_count", 0),
            "open_issues": meta.get("open_issues_count", 0),
            "age_days": age_days,
            "days_since_last_push": days_since_push,
            "is_archived": archived,
            "is_fork": fork,
            "maturity_tier": _tier(archived, fork, age_days, days_since_push),
        }

        evidence = []
        if created_at is None or pushed_at is None:
            evidence.append(_MISSING_TIMESTAMP_EVIDENCE)
            confidence = 0.6
        else:
            evidence.append(
                f"created_at={meta.get('created_at')}, pushed_at={meta.get('pushed_at')}"
            )
            confidence = 0.85  # exact numbers, but the tier is a designed bucketing

        return [Finding("maturity", value, confidence, tuple(evidence))]
