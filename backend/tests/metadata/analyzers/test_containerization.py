"""Tests for app.metadata.analyzers.containerization.ContainerizationAnalyzer."""

from app.metadata.analyzers.containerization import ContainerizationAnalyzer
from app.metadata.models import AnalysisInput

analyzer = ContainerizationAnalyzer()


def f(path: str) -> dict:
    return {"path": path, "name": path.rsplit("/", 1)[-1], "type": "file"}


def d(path: str) -> dict:
    return {"path": path, "name": path.rsplit("/", 1)[-1], "type": "dir"}


def field_value(input_: AnalysisInput, field: str):
    findings = {x.field: x.value for x in analyzer.analyze(input_)}
    return findings[field]


class TestDocker:
    def test_detected_by_dockerfile(self):
        assert (
            field_value(AnalysisInput(entries=[f("Dockerfile")]), "has_docker") is True
        )

    def test_not_detected_without_dockerfile(self):
        assert field_value(AnalysisInput(entries=[f("main.py")]), "has_docker") is False


class TestDockerCompose:
    def test_detected_by_docker_compose_yml(self):
        input_ = AnalysisInput(entries=[f("docker-compose.yml")])
        assert field_value(input_, "has_docker_compose") is True

    def test_detected_by_compose_yaml(self):
        input_ = AnalysisInput(entries=[f("compose.yaml")])
        assert field_value(input_, "has_docker_compose") is True

    def test_not_detected_otherwise(self):
        input_ = AnalysisInput(entries=[f("Dockerfile")])
        assert field_value(input_, "has_docker_compose") is False


class TestKubernetesManifests:
    def test_detected_by_k8s_directory(self):
        input_ = AnalysisInput(entries=[d("k8s")])
        assert field_value(input_, "has_kubernetes_manifests") is True

    def test_detected_by_kubernetes_directory(self):
        input_ = AnalysisInput(entries=[d("kubernetes")])
        assert field_value(input_, "has_kubernetes_manifests") is True

    def test_detected_by_helm_chart(self):
        input_ = AnalysisInput(entries=[f("Chart.yaml")])
        assert field_value(input_, "has_kubernetes_manifests") is True

    def test_not_detected_otherwise(self):
        input_ = AnalysisInput(entries=[f("Dockerfile")])
        assert field_value(input_, "has_kubernetes_manifests") is False


class TestAllFieldsAlwaysPresent:
    def test_all_three_fields_present_even_when_nothing_found(self):
        findings = {x.field for x in analyzer.analyze(AnalysisInput(entries=[]))}
        assert findings == {
            "has_docker",
            "has_docker_compose",
            "has_kubernetes_manifests",
        }
