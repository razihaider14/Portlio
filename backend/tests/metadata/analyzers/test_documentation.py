"""Tests for app.metadata.analyzers.documentation.DocumentationQualityAnalyzer."""

from app.metadata.analyzers.documentation import DocumentationQualityAnalyzer
from app.metadata.models import AnalysisInput

analyzer = DocumentationQualityAnalyzer()


def f(path: str) -> dict:
    return {"path": path, "name": path.rsplit("/", 1)[-1], "type": "file"}


def doc_value(input_: AnalysisInput) -> dict:
    findings = analyzer.analyze(input_)
    assert len(findings) == 1
    assert findings[0].field == "documentation"
    return findings[0].value


class TestPresenceFlags:
    def test_no_docs_at_all(self):
        value = doc_value(AnalysisInput(entries=[f("main.py")]))
        assert value["has_readme"] is False
        assert value["has_license_file"] is False
        assert value["has_changelog"] is False
        assert value["has_contributing"] is False
        assert value["has_code_of_conduct"] is False
        assert value["quality_tier"] == "none"
        assert value["score"] == 0

    def test_all_standard_docs_present(self):
        entries = [
            f("README.md"),
            f("LICENSE"),
            f("CHANGELOG.md"),
            f("CONTRIBUTING.md"),
            f("CODE_OF_CONDUCT.md"),
        ]
        value = doc_value(AnalysisInput(entries=entries))
        assert value["has_readme"] is True
        assert value["has_license_file"] is True
        assert value["has_changelog"] is True
        assert value["has_contributing"] is True
        assert value["has_code_of_conduct"] is True
        assert value["score"] == 5

    def test_recognizes_alternate_readme_names(self):
        value = doc_value(AnalysisInput(entries=[f("README.rst")]))
        assert value["has_readme"] is True

    def test_recognizes_alternate_license_names(self):
        value = doc_value(AnalysisInput(entries=[f("COPYING")]))
        assert value["has_license_file"] is True


class TestReadmeStructureScan:
    def test_counts_recognized_sections(self):
        content = "# Title\n## Installation\ntext\n## Usage\ntext\n"
        input_ = AnalysisInput(
            entries=[f("README.md")], file_contents={"README.md": content}
        )
        value = doc_value(input_)
        assert "installation" in value["readme_sections"]
        assert "usage" in value["readme_sections"]

    def test_ignores_unrecognized_headings_in_sections_list(self):
        # readme_sections is informational/keyword-based and legitimately
        # narrower than the actual heading count.
        content = "# Title\n## Motivation\ntext\n"
        input_ = AnalysisInput(
            entries=[f("README.md")], file_contents={"README.md": content}
        )
        value = doc_value(input_)
        assert value["readme_sections"] == []

    def test_unrecognized_headings_still_count_toward_heading_count(self):
        # This is the actual fix: a README using non-standard-but-real
        # section names (common in hardware/firmware projects: "Wiring",
        # "Circuit Diagram", "Components") must not be penalized just for
        # not matching the recognized-keyword vocabulary.
        content = "# Title\n## Motivation\ntext\n## Random Section\ntext\n"
        input_ = AnalysisInput(
            entries=[f("README.md")], file_contents={"README.md": content}
        )
        value = doc_value(input_)
        assert value["readme_heading_count"] == 3
        assert value["readme_sections"] == []

    def test_hardware_specific_headings_are_recognized(self):
        content = (
            "# Sensor Node\n"
            "## Hardware\ntext\n"
            "## Wiring\ntext\n"
            "## Components\ntext\n"
            "## Bill of Materials\ntext\n"
        )
        input_ = AnalysisInput(
            entries=[f("README.md")], file_contents={"README.md": content}
        )
        value = doc_value(input_)
        assert "hardware" in value["readme_sections"]
        assert "wiring" in value["readme_sections"]
        assert "components" in value["readme_sections"]

    def test_score_driven_by_heading_count_not_keyword_matches(self):
        # Two headings, neither in the recognized vocabulary, should
        # still earn the ">=2 headings" score point.
        content = "# Title\n## Foo\ntext\n## Bar\ntext\n"
        input_ = AnalysisInput(
            entries=[f("README.md")], file_contents={"README.md": content}
        )
        value = doc_value(input_)
        assert value["readme_sections"] == []
        assert value["readme_heading_count"] == 3
        # +1 for README, +1 for >=2 headings = 2
        assert value["score"] == 2

    def test_records_readme_length(self):
        content = "# Hello\n" + ("x" * 100)
        input_ = AnalysisInput(
            entries=[f("README.md")], file_contents={"README.md": content}
        )
        value = doc_value(input_)
        assert value["readme_length_chars"] == len(content)

    def test_readme_length_none_without_content(self):
        value = doc_value(AnalysisInput(entries=[f("README.md")]))
        assert value["readme_length_chars"] is None
        assert value["readme_sections"] == []
        assert value["readme_heading_count"] == 0


class TestScoringRubricAndTiers:
    def test_none_tier_with_zero_score(self):
        value = doc_value(AnalysisInput(entries=[f("main.py")]))
        assert value["quality_tier"] == "none"

    def test_minimal_tier(self):
        # Only README present -> score 1
        value = doc_value(AnalysisInput(entries=[f("README.md")]))
        assert value["score"] == 1
        assert value["quality_tier"] == "minimal"

    def test_excellent_tier_with_full_marks(self):
        content = (
            "# Title\n"
            "## Installation\ntext\n"
            "## Usage\ntext\n"
            "## Configuration\ntext\n"
            "## Contributing\ntext\n" + ("padding " * 100)
        )
        entries = [
            f("README.md"),
            f("LICENSE"),
            f("CHANGELOG.md"),
            f("CONTRIBUTING.md"),
            f("CODE_OF_CONDUCT.md"),
        ]
        input_ = AnalysisInput(entries=entries, file_contents={"README.md": content})
        value = doc_value(input_)
        assert value["score"] == 8
        assert value["quality_tier"] == "excellent"

    def test_evidence_is_populated(self):
        input_ = AnalysisInput(entries=[f("README.md"), f("LICENSE")])
        findings = analyzer.analyze(input_)
        assert findings[0].evidence
        assert any("README" in e for e in findings[0].evidence)
