"""
Detects CI/CD provider usage from exclusive, well-known config filenames and
directories. Every marker here is written by exactly one provider.
"""

from app.metadata.models import AnalysisInput, Finding
from app.metadata.tree_utils import has_directory, has_filename

# (provider name, check) pairs. Each check is a zero-arg predicate closed
# over `entries`, built per-call in analyze() to keep this table declarative.
_PROVIDER_MARKERS: tuple[tuple[str, tuple[str, ...], tuple[str, ...]], ...] = (
    # (provider, directory names, filenames)
    ("GitHub Actions", (".github/workflows",), ()),
    ("GitLab CI", (), (".gitlab-ci.yml",)),
    ("CircleCI", (".circleci",), ()),
    ("Travis CI", (), (".travis.yml",)),
    ("Jenkins", (), ("Jenkinsfile",)),
    ("Azure Pipelines", (), ("azure-pipelines.yml",)),
    ("Drone CI", (), (".drone.yml",)),
    ("Bitbucket Pipelines", (), ("bitbucket-pipelines.yml",)),
    ("Buildkite", (".buildkite",), ()),
)


class CICDPresenceAnalyzer:
    """Detects CI/CD configuration and which provider(s) are configured."""

    def analyze(self, input: AnalysisInput) -> list[Finding]:
        providers = []
        evidence = []

        # .github/workflows is a nested path; check its final segment as a
        # directory name since tree entries carry only path/name/type.
        github_workflows = any(
            e.get("type") == "dir"
            and e["path"].strip("/").lower() == ".github/workflows"
            for e in input.entries
        )
        if github_workflows:
            providers.append("GitHub Actions")
            evidence.append("found .github/workflows/ directory")

        for provider, dirs, files in _PROVIDER_MARKERS:
            if provider == "GitHub Actions":
                continue  # handled above (nested path)
            if dirs and has_directory(input.entries, *dirs):
                providers.append(provider)
                evidence.append(f"found {dirs[0]}/ directory")
            elif files and has_filename(input.entries, *files):
                providers.append(provider)
                evidence.append(f"found {files[0]}")

        has_ci = bool(providers)
        findings = [Finding("has_ci_cd", has_ci, 1.0, tuple(evidence))]
        findings.extend(
            Finding("ci_providers", provider, 1.0, (ev,))
            for provider, ev in zip(providers, evidence)
        )
        return findings
