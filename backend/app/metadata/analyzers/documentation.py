"""
Assesses documentation completeness from the presence of standard project
docs and, when downloaded, the README's structure.

The "quality_tier" is a transparent point score, not a judgment call: each
point comes from an exact, checkable fact (a file exists; the README has a
certain number of Markdown headings). The rubric is documented in full below
so the result is reproducible and auditable, not a black box.
"""

import re

from app.metadata.models import AnalysisInput, Finding
from app.metadata.tree_utils import get_content, has_filename

_README_NAMES = ("README.md", "README", "README.rst", "README.txt")
_LICENSE_NAMES = ("LICENSE", "LICENSE.md", "LICENSE.txt", "COPYING", "COPYING.md")
_CHANGELOG_NAMES = ("CHANGELOG.md", "CHANGELOG", "CHANGELOG.rst", "HISTORY.md")
_CONTRIBUTING_NAMES = ("CONTRIBUTING.md", "CONTRIBUTING")
_CODE_OF_CONDUCT_NAMES = ("CODE_OF_CONDUCT.md",)

# Markdown ATX heading text (after stripping leading #'s) recognized as a
# "standard" README section, matched case-insensitively against the whole
# heading line. This is informational only (surfaced in readme_sections for
# callers who want it) and deliberately broad, covering both software and
# hardware/firmware project conventions, but it does NOT drive the score,
# since no fixed keyword list can cover every project's natural vocabulary
# without unfairly penalizing well-documented projects that just phrase
# their headings differently. See _heading_count() for what the score uses.
_RECOGNIZED_SECTIONS = (
    "installation",
    "install",
    "getting started",
    "quick start",
    "usage",
    "examples",
    "api",
    "contributing",
    "license",
    "configuration",
    "requirements",
    "prerequisites",
    "dependencies",
    "features",
    "overview",
    "about",
    "hardware",
    "wiring",
    "circuit",
    "schematic",
    "pinout",
    "components",
    "bill of materials",
    "bom",
    "how it works",
    "architecture",
    "demo",
    "screenshots",
    "faq",
    "troubleshooting",
    "testing",
    "deployment",
    "roadmap",
    "credits",
    "acknowledgments",
    "acknowledgements",
)

_HEADING_RE = re.compile(r"^#{1,6}\s+(.*)$", re.MULTILINE)

# Scoring rubric (each worth 1 point unless noted):
#   +1  has_readme
#   +1  has_license_file
#   +1  has_changelog
#   +1  has_contributing
#   +1  has_code_of_conduct
#   +1  README has >= 2 Markdown headings (any heading text counts, this
#       measures *structure*, not whether the author happened to use one of
#       a fixed set of English keywords)
#   +1  README has >= 4 Markdown headings (a second point, so a very
#       thorough README can outscore one that just clears the bar)
#   +1  README length >= 500 characters (long enough to say something)
# Max score: 8. Tiers: 0 -> "none", 1-2 -> "minimal", 3-4 -> "moderate",
# 5-6 -> "good", 7-8 -> "excellent".
_TIER_THRESHOLDS = (
    (7, "excellent"),
    (5, "good"),
    (3, "moderate"),
    (1, "minimal"),
    (0, "none"),
)


def _tier_for_score(score: int) -> str:
    for threshold, tier in _TIER_THRESHOLDS:
        if score >= threshold:
            return tier
    return "none"  # pragma: no cover - unreachable, thresholds start at 0


def _heading_texts(readme_text: str) -> list[str]:
    """Every Markdown ATX heading's text, in document order, as written."""
    return [match.group(1).strip() for match in _HEADING_RE.finditer(readme_text)]


def _recognized_sections(headings: list[str]) -> list[str]:
    found = []
    for heading in headings:
        lowered = heading.lower()
        for section in _RECOGNIZED_SECTIONS:
            if section in lowered and section not in found:
                found.append(section)
    return found


class DocumentationQualityAnalyzer:
    """
    Computes documentation presence/quality from standard project doc files
    and README structure, using the point rubric documented above.
    """

    def analyze(self, input: AnalysisInput) -> list[Finding]:
        has_readme = has_filename(input.entries, *_README_NAMES)
        has_license_file = has_filename(input.entries, *_LICENSE_NAMES)
        has_changelog = has_filename(input.entries, *_CHANGELOG_NAMES)
        has_contributing = has_filename(input.entries, *_CONTRIBUTING_NAMES)
        has_code_of_conduct = has_filename(input.entries, *_CODE_OF_CONDUCT_NAMES)

        readme_text = get_content(input.file_contents, input.entries, *_README_NAMES)
        readme_length = len(readme_text) if readme_text else None
        headings = _heading_texts(readme_text) if readme_text else []
        sections = _recognized_sections(headings)

        score = 0
        evidence = []
        if has_readme:
            score += 1
            evidence.append("has README")
        if has_license_file:
            score += 1
            evidence.append("has LICENSE file")
        if has_changelog:
            score += 1
            evidence.append("has CHANGELOG")
        if has_contributing:
            score += 1
            evidence.append("has CONTRIBUTING guide")
        if has_code_of_conduct:
            score += 1
            evidence.append("has CODE_OF_CONDUCT")
        if len(headings) >= 2:
            score += 1
            evidence.append(f"README has {len(headings)} heading(s)")
        if len(headings) >= 4:
            score += 1
            evidence.append("README has 4+ headings")
        if readme_length is not None and readme_length >= 500:
            score += 1
            evidence.append(f"README is {readme_length} characters")

        value = {
            "has_readme": has_readme,
            "has_license_file": has_license_file,
            "has_changelog": has_changelog,
            "has_contributing": has_contributing,
            "has_code_of_conduct": has_code_of_conduct,
            "readme_length_chars": readme_length,
            "readme_heading_count": len(headings),
            "readme_sections": sections,
            "score": score,
            "quality_tier": _tier_for_score(score),
        }
        # Presence facts (has_readme etc.) and the heading count are exact;
        # the tier is a documented-but-designed bucketing of them, so
        # overall confidence is high but not 1.0.
        return [Finding("documentation", value, 0.9, tuple(evidence))]
