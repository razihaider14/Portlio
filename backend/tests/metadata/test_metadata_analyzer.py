"""Tests for app.metadata.metadata_analyzer's public API."""

from app.metadata.metadata_analyzer import (
    _FIELD_DEFAULTS,
    analyze_repository_metadata,
    analyze_repository_metadata_detailed,
)


def f(path: str) -> dict:
    return {"path": path, "name": path.rsplit("/", 1)[-1], "type": "file"}


class TestStableOutputShape:
    def test_all_default_fields_always_present(self):
        result = analyze_repository_metadata({"contents": []})
        assert set(result.keys()) == set(_FIELD_DEFAULTS.keys())

    def test_empty_repository_returns_all_defaults(self):
        result = analyze_repository_metadata({"contents": []})
        assert result["project_types"] == []
        assert result["hardware_platforms"] == []
        assert result["has_tests"] is False
        assert result["has_ci_cd"] is False
        assert result["ci_providers"] == []
        assert result["has_docker"] is False
        assert result["package_managers"] == []
        assert result["build_systems"] == []
        assert result["license"] == {"detected": False, "spdx_id": None, "source": None}

    def test_missing_contents_key_does_not_raise(self):
        result = analyze_repository_metadata({})
        assert (
            result["total_files"] if False else True
        )  # no-op, just ensure no exception
        assert result["size_metrics"]["total_files"] == 0


class TestFoldingListFields:
    def test_multiple_project_types_fold_to_list(self):
        entries = [f("manage.py"), f("index.html")]
        result = analyze_repository_metadata({"contents": entries})
        assert set(result["project_types"]) >= {"api_backend", "website"}

    def test_multiple_package_managers_fold_to_list(self):
        entries = [f("poetry.lock"), f("yarn.lock")]
        result = analyze_repository_metadata({"contents": entries})
        assert set(result["package_managers"]) == {"Poetry", "Yarn"}

    def test_single_match_still_a_list(self):
        entries = [f("Makefile")]
        result = analyze_repository_metadata({"contents": entries})
        assert result["build_systems"] == ["Make"]


class TestFoldingScalarFields:
    def test_documentation_is_a_single_dict_not_a_list(self):
        result = analyze_repository_metadata({"contents": [f("README.md")]})
        assert isinstance(result["documentation"], dict)

    def test_license_is_a_single_dict(self):
        result = analyze_repository_metadata({"contents": []})
        assert isinstance(result["license"], dict)

    def test_maturity_is_a_single_dict(self):
        result = analyze_repository_metadata({"contents": []})
        assert isinstance(result["maturity"], dict)


class TestFileContentsIntegration:
    def test_richer_results_with_file_contents(self):
        repository = {
            "contents": [f("requirements.txt")],
            "file_contents": {"requirements.txt": "flask\npytest\n"},
        }
        result = analyze_repository_metadata(repository)
        assert "api_backend" in result["project_types"]
        assert result["has_tests"] is True

    def test_degrades_gracefully_without_file_contents(self):
        repository = {"contents": [f("requirements.txt")]}
        result = analyze_repository_metadata(repository)
        assert "api_backend" not in result["project_types"]
        assert result["has_tests"] is False


class TestRepoMetadataIntegration:
    def test_license_and_maturity_use_repo_metadata(self):
        repository = {
            "contents": [],
            "repo_metadata": {
                "license": {"spdx_id": "MIT"},
                "stargazers_count": 50,
                "archived": True,
            },
        }
        result = analyze_repository_metadata(repository)
        assert result["license"]["spdx_id"] == "MIT"
        assert result["maturity"]["stars"] == 50
        assert result["maturity"]["maturity_tier"] == "archived"

    def test_missing_repo_metadata_does_not_raise(self):
        result = analyze_repository_metadata({"contents": []})
        assert result["maturity"]["stars"] == 0


class TestDetailedAPI:
    def test_returns_finding_objects_with_confidence_and_evidence(self):
        repository = {"contents": [f("Dockerfile")]}
        findings = analyze_repository_metadata_detailed(repository)
        docker_findings = [x for x in findings if x.field == "has_docker"]
        assert len(docker_findings) == 1
        assert docker_findings[0].value is True
        assert 0.0 <= docker_findings[0].confidence <= 1.0
        assert docker_findings[0].evidence

    def test_detailed_and_simple_are_consistent(self):
        repository = {"contents": [f("Dockerfile"), f("Makefile")]}
        detailed = analyze_repository_metadata_detailed(repository)
        simple = analyze_repository_metadata(repository)
        has_docker_finding = [x for x in detailed if x.field == "has_docker"][0]
        assert has_docker_finding.value == simple["has_docker"]


class TestDefaultsAreNotSharedMutableState:
    def test_mutating_one_result_does_not_affect_another(self):
        result_a = analyze_repository_metadata({"contents": []})
        result_a["documentation"]["score"] = 999
        result_b = analyze_repository_metadata({"contents": []})
        assert result_b["documentation"]["score"] == 0

    def test_mutating_a_list_field_does_not_leak_across_calls(self):
        result_a = analyze_repository_metadata({"contents": []})
        result_a["project_types"].append("fake_type")
        result_b = analyze_repository_metadata({"contents": []})
        assert result_b["project_types"] == []
