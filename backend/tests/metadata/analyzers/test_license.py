"""Tests for app.metadata.analyzers.license.LicenseAnalyzer."""

from app.metadata.analyzers.license import LicenseAnalyzer
from app.metadata.models import AnalysisInput

analyzer = LicenseAnalyzer()


def f(path: str) -> dict:
    return {"path": path, "name": path.rsplit("/", 1)[-1], "type": "file"}


def license_value(input_: AnalysisInput) -> dict:
    findings = analyzer.analyze(input_)
    assert len(findings) == 1
    assert findings[0].field == "license"
    return findings[0].value


class TestGitHubAPISource:
    def test_trusts_github_api_spdx_id(self):
        input_ = AnalysisInput(
            entries=[],
            repo_metadata={"license": {"spdx_id": "MIT", "name": "MIT License"}},
        )
        value = license_value(input_)
        assert value == {"detected": True, "spdx_id": "MIT", "source": "github_api"}

    def test_full_confidence_from_api(self):
        input_ = AnalysisInput(
            entries=[], repo_metadata={"license": {"spdx_id": "Apache-2.0"}}
        )
        findings = analyzer.analyze(input_)
        assert findings[0].confidence == 1.0

    def test_ignores_noassertion(self):
        # GitHub reports NOASSERTION when it detected *a* license file but
        # couldn't confidently identify which one -- treat as "not detected
        # via API" and fall through to the file-based path.
        input_ = AnalysisInput(
            entries=[f("LICENSE")],
            repo_metadata={"license": {"spdx_id": "NOASSERTION"}},
        )
        value = license_value(input_)
        assert value["source"] != "github_api"

    def test_ignores_null_license(self):
        input_ = AnalysisInput(entries=[], repo_metadata={"license": None})
        value = license_value(input_)
        assert value["detected"] is False


class TestContentFallback:
    def test_identifies_mit_from_content(self):
        content = "MIT License\n\nPermission is hereby granted, free of charge, to any person...\n"
        input_ = AnalysisInput(
            entries=[f("LICENSE")], file_contents={"LICENSE": content}
        )
        value = license_value(input_)
        assert value == {
            "detected": True,
            "spdx_id": "MIT",
            "source": "file_content_match",
        }

    def test_identifies_apache_from_content(self):
        content = "Apache License, Version 2.0\n\n..."
        input_ = AnalysisInput(
            entries=[f("LICENSE")], file_contents={"LICENSE": content}
        )
        value = license_value(input_)
        assert value["spdx_id"] == "Apache-2.0"

    def test_identifies_gpl_from_content(self):
        content = "                    GNU GENERAL PUBLIC LICENSE\n                       Version 3\n"
        input_ = AnalysisInput(
            entries=[f("LICENSE")], file_contents={"LICENSE": content}
        )
        value = license_value(input_)
        assert value["spdx_id"] == "GPL-3.0"

    def test_case_insensitive_matching(self):
        content = "mit license\n\npermission is hereby granted, free of charge...\n"
        input_ = AnalysisInput(
            entries=[f("LICENSE")], file_contents={"LICENSE": content}
        )
        value = license_value(input_)
        assert value["spdx_id"] == "MIT"

    def test_readme_mentioning_license_name_is_not_matched(self):
        # Only the LICENSE file itself is scanned, never the README, so a
        # passing mention there can't cause a false match.
        input_ = AnalysisInput(
            entries=[f("LICENSE"), f("README.md")],
            file_contents={
                "LICENSE": "unrecognized custom license text",
                "README.md": "This project is MIT licensed. Permission is hereby granted...",
            },
        )
        value = license_value(input_)
        assert value["spdx_id"] is None


class TestFilePresenceOnlyFallback:
    def test_file_exists_but_content_not_downloaded(self):
        input_ = AnalysisInput(entries=[f("LICENSE")])
        value = license_value(input_)
        assert value == {
            "detected": True,
            "spdx_id": None,
            "source": "file_presence_only",
        }

    def test_file_exists_but_text_unrecognized(self):
        input_ = AnalysisInput(
            entries=[f("LICENSE")],
            file_contents={"LICENSE": "Some custom proprietary license text."},
        )
        value = license_value(input_)
        assert value["detected"] is True
        assert value["spdx_id"] is None
        assert value["source"] == "file_presence_only"

    def test_lower_confidence_than_content_match(self):
        input_ = AnalysisInput(entries=[f("LICENSE")])
        findings = analyzer.analyze(input_)
        assert findings[0].confidence < 0.9


class TestNoLicense:
    def test_no_api_data_and_no_file(self):
        input_ = AnalysisInput(entries=[f("main.py")])
        value = license_value(input_)
        assert value == {"detected": False, "spdx_id": None, "source": None}

    def test_full_confidence_in_absence(self):
        input_ = AnalysisInput(entries=[f("main.py")])
        findings = analyzer.analyze(input_)
        assert findings[0].confidence == 1.0

    def test_recognizes_copying_as_license_file(self):
        input_ = AnalysisInput(entries=[f("COPYING")])
        value = license_value(input_)
        assert value["detected"] is True
