"""Tests for app.metadata.analyzers.ci_cd.CICDPresenceAnalyzer."""

from app.metadata.analyzers.ci_cd import CICDPresenceAnalyzer
from app.metadata.models import AnalysisInput

analyzer = CICDPresenceAnalyzer()


def f(path: str) -> dict:
    return {"path": path, "name": path.rsplit("/", 1)[-1], "type": "file"}


def d(path: str) -> dict:
    return {"path": path, "name": path.rsplit("/", 1)[-1], "type": "dir"}


def result(input_: AnalysisInput) -> tuple[bool, set[str]]:
    findings = analyzer.analyze(input_)
    has_ci = [x for x in findings if x.field == "has_ci_cd"][0].value
    providers = {x.value for x in findings if x.field == "ci_providers"}
    return has_ci, providers


class TestGitHubActions:
    def test_detected_by_workflows_directory(self):
        entries = [d(".github"), d(".github/workflows")]
        has_ci, providers = result(AnalysisInput(entries=entries))
        assert has_ci is True
        assert "GitHub Actions" in providers

    def test_not_detected_by_github_dir_alone(self):
        entries = [d(".github")]
        has_ci, providers = result(AnalysisInput(entries=entries))
        assert "GitHub Actions" not in providers


class TestOtherProviders:
    def test_gitlab_ci(self):
        _, providers = result(AnalysisInput(entries=[f(".gitlab-ci.yml")]))
        assert "GitLab CI" in providers

    def test_circleci(self):
        _, providers = result(AnalysisInput(entries=[d(".circleci")]))
        assert "CircleCI" in providers

    def test_travis_ci(self):
        _, providers = result(AnalysisInput(entries=[f(".travis.yml")]))
        assert "Travis CI" in providers

    def test_jenkins(self):
        _, providers = result(AnalysisInput(entries=[f("Jenkinsfile")]))
        assert "Jenkins" in providers

    def test_azure_pipelines(self):
        _, providers = result(AnalysisInput(entries=[f("azure-pipelines.yml")]))
        assert "Azure Pipelines" in providers

    def test_drone_ci(self):
        _, providers = result(AnalysisInput(entries=[f(".drone.yml")]))
        assert "Drone CI" in providers

    def test_bitbucket_pipelines(self):
        _, providers = result(AnalysisInput(entries=[f("bitbucket-pipelines.yml")]))
        assert "Bitbucket Pipelines" in providers

    def test_buildkite(self):
        _, providers = result(AnalysisInput(entries=[d(".buildkite")]))
        assert "Buildkite" in providers


class TestNoProvider:
    def test_has_ci_false_without_evidence(self):
        has_ci, providers = result(AnalysisInput(entries=[f("main.py")]))
        assert has_ci is False
        assert providers == set()


class TestMultipleProviders:
    def test_detects_multiple_simultaneously(self):
        entries = [d(".github"), d(".github/workflows"), f(".travis.yml")]
        has_ci, providers = result(AnalysisInput(entries=entries))
        assert has_ci is True
        assert providers == {"GitHub Actions", "Travis CI"}
