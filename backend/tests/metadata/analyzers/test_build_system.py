"""Tests for app.metadata.analyzers.build_system.BuildSystemAnalyzer."""

from app.metadata.analyzers.build_system import BuildSystemAnalyzer
from app.metadata.models import AnalysisInput

analyzer = BuildSystemAnalyzer()


def f(path: str) -> dict:
    return {"path": path, "name": path.rsplit("/", 1)[-1], "type": "file"}


def systems_of(input_: AnalysisInput) -> set[str]:
    return {finding.value for finding in analyzer.analyze(input_)}


class TestEachBuildSystem:
    def test_cmake(self):
        assert "CMake" in systems_of(AnalysisInput(entries=[f("CMakeLists.txt")]))

    def test_make(self):
        assert "Make" in systems_of(AnalysisInput(entries=[f("Makefile")]))

    def test_maven(self):
        assert "Maven" in systems_of(AnalysisInput(entries=[f("pom.xml")]))

    def test_gradle(self):
        assert "Gradle" in systems_of(AnalysisInput(entries=[f("build.gradle")]))

    def test_gradle_kotlin_dsl(self):
        assert "Gradle" in systems_of(AnalysisInput(entries=[f("build.gradle.kts")]))

    def test_bazel(self):
        assert "Bazel" in systems_of(AnalysisInput(entries=[f("WORKSPACE")]))

    def test_ninja(self):
        assert "Ninja" in systems_of(AnalysisInput(entries=[f("build.ninja")]))

    def test_meson(self):
        assert "Meson" in systems_of(AnalysisInput(entries=[f("meson.build")]))

    def test_webpack(self):
        assert "Webpack" in systems_of(AnalysisInput(entries=[f("webpack.config.js")]))

    def test_vite(self):
        assert "Vite" in systems_of(AnalysisInput(entries=[f("vite.config.ts")]))


class TestNoBuildSystem:
    def test_empty_when_no_markers_present(self):
        assert systems_of(AnalysisInput(entries=[f("main.py")])) == set()


class TestMultipleBuildSystems:
    def test_detects_several_simultaneously(self):
        entries = [f("CMakeLists.txt"), f("Makefile")]
        systems = systems_of(AnalysisInput(entries=entries))
        assert "CMake" in systems
        assert "Make" in systems
