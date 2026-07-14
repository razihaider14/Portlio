"""
Detects containerization and orchestration tooling from exclusive config
filenames.
"""

from app.metadata.models import AnalysisInput, Finding
from app.metadata.tree_utils import has_directory, has_filename


class ContainerizationAnalyzer:
    """Detects Docker, Docker Compose, and Kubernetes manifest usage."""

    def analyze(self, input: AnalysisInput) -> list[Finding]:
        findings = []

        has_docker = has_filename(input.entries, "Dockerfile")
        findings.append(
            Finding(
                "has_docker",
                has_docker,
                1.0,
                ("found Dockerfile",) if has_docker else (),
            )
        )

        has_compose = has_filename(
            input.entries,
            "docker-compose.yml",
            "docker-compose.yaml",
            "compose.yml",
            "compose.yaml",
        )
        findings.append(
            Finding(
                "has_docker_compose",
                has_compose,
                1.0,
                ("found docker-compose/compose config",) if has_compose else (),
            )
        )

        has_k8s_dir = has_directory(input.entries, "k8s", "kubernetes")
        has_helm = has_filename(input.entries, "Chart.yaml")
        has_k8s = has_k8s_dir or has_helm
        evidence = []
        if has_k8s_dir:
            evidence.append("found k8s/ or kubernetes/ directory")
        if has_helm:
            evidence.append("found Chart.yaml (Helm)")
        findings.append(
            Finding("has_kubernetes_manifests", has_k8s, 0.9, tuple(evidence))
        )

        return findings
