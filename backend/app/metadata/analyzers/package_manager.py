"""
Detects package manager(s) in use from exclusive lockfile or manifest
filenames, each of the files below is written or consumed by exactly one
tool, which is what makes this fully deterministic (unlike, say,
package.json, which many JS package managers share).
"""

from app.metadata.models import AnalysisInput, Finding
from app.metadata.tree_utils import has_filename

# (package manager name, filenames that exclusively indicate it)
_MARKERS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("Poetry", ("poetry.lock",)),
    ("Pipenv", ("Pipfile.lock",)),
    ("uv", ("uv.lock",)),
    ("pip", ("requirements.txt",)),
    ("npm", ("package-lock.json",)),
    ("Yarn", ("yarn.lock",)),
    ("pnpm", ("pnpm-lock.yaml",)),
    ("Bun", ("bun.lockb", "bun.lock")),
    ("Cargo", ("Cargo.lock",)),
    ("Go Modules", ("go.sum",)),
    ("Composer", ("composer.lock",)),
    ("Bundler", ("Gemfile.lock",)),
    ("CocoaPods", ("Podfile.lock",)),
    ("NuGet", ("nuget.config", "packages.config")),
    ("Conan", ("conanfile.txt", "conanfile.py")),
    ("vcpkg", ("vcpkg.json",)),
)


class PackageManagerAnalyzer:
    """Detects package manager(s) from exclusive lockfile/manifest filenames."""

    def analyze(self, input: AnalysisInput) -> list[Finding]:
        findings = []
        for name, filenames in _MARKERS:
            matched = [f for f in filenames if has_filename(input.entries, f)]
            if matched:
                findings.append(
                    Finding(
                        "package_managers",
                        name,
                        1.0,
                        tuple(f"found {f}" for f in matched),
                    )
                )
        return findings
