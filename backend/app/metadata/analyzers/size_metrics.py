"""
Computes repository size metrics from the tree entries and the GitHub API's
own reported repository size. Every value here is an exact count or a
directly-reported API field, no estimation, so confidence is always 1.0.
"""

from app.metadata.models import AnalysisInput, Finding

_TOP_N_EXTENSIONS = 10


def _extension_of(name: str) -> str | None:
    if "." not in name:
        return None
    return "." + name.rsplit(".", 1)[-1].lower()


def _max_depth(entries: list[dict]) -> int:
    max_depth = 0
    for entry in entries:
        depth = entry.get("path", "").count("/")
        if depth > max_depth:
            max_depth = depth
    return max_depth


class SizeMetricsAnalyzer:
    """Computes exact file/directory counts, extension breakdown, and repo size."""

    def analyze(self, input: AnalysisInput) -> list[Finding]:
        files = [e for e in input.entries if e.get("type") == "file"]
        directories = [e for e in input.entries if e.get("type") == "dir"]

        extension_counts: dict[str, int] = {}
        for entry in files:
            ext = _extension_of(entry.get("name", ""))
            if ext:
                extension_counts[ext] = extension_counts.get(ext, 0) + 1

        top_extensions = dict(
            sorted(extension_counts.items(), key=lambda kv: kv[1], reverse=True)[
                :_TOP_N_EXTENSIONS
            ]
        )

        value = {
            "total_files": len(files),
            "total_directories": len(directories),
            "file_count_by_extension": top_extensions,
            "max_directory_depth": _max_depth(input.entries),
            "repo_size_kb": input.repo_metadata.get("size"),
        }
        return [
            Finding(
                "size_metrics",
                value,
                1.0,
                (f"counted {len(files)} files across {len(directories)} directories",),
            )
        ]
